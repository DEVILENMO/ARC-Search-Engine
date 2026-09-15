# -*- coding: utf-8 -*-
"""GPT-2 tokenizer based tokenization for the search engine.

Why a GPT-2 tokenizer? The engine must support *any* UTF-8 language without
language-specific word segmentation: sub-word BPE ids act as language
independent "terms" for the inverted index, and contiguous BPE pieces can be
joined back into phrase tokens (see the Apriori-style mining below).
"""
import logging
from pathlib import Path

import numpy as np
from transformers import GPT2Tokenizer

from BaseModule import SearchEngineTokenizer

logger = logging.getLogger(__name__)

# Fallback used only when stopwords.txt is missing.
FALLBACK_STOPWORDS = [
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'but', 'by', 'for', 'from',
    'has', 'have', 'he', 'her', 'his', 'how', 'i', 'if', 'in', 'is', 'it',
    'its', 'of', 'on', 'or', 'she', 'that', 'the', 'their', 'them', 'then',
    'there', 'these', 'they', 'this', 'to', 'was', 'we', 'were', 'what',
    'when', 'where', 'which', 'who', 'why', 'will', 'with', 'you', 'your',
]


class SearchEngineTokenizerGPT2(SearchEngineTokenizer):
    def __init__(self):
        # 初始化GPT-2 tokenizer (下载/读取本地HF缓存)
        self.char_tokenizer = GPT2Tokenizer.from_pretrained('gpt2')

        self.blank_token = self.tokenize(' ')

        stopwords_list = self._load_stopwords(Path(__file__).parent / 'stopwords.txt')
        logger.info('Loaded %d stopwords.', len(stopwords_list))
        stop_word_token_id_list = []
        for stopword in stopwords_list:
            token_ids = self.tokenize(stopword)
            str_token_ids = '-'.join([str(_) for _ in token_ids])
            stop_word_token_id_list.append(str_token_ids)
        stop_word_token_id_list.append('-'.join([str(_) for _ in self.blank_token]))
        self.stop_word_token_id_list = list(set(stop_word_token_id_list))

    @staticmethod
    def _load_stopwords(file_path: Path) -> list[str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                stopwords = [line.strip() for line in file if line.strip()]
            if stopwords:
                return stopwords
        except OSError:
            logger.warning('stopwords.txt not found, using built-in fallback list.')
        return FALLBACK_STOPWORDS

    def tokenize(self, text: str) -> np.ndarray:
        # 对传入的文本进行tokenize
        token_ids = self.char_tokenizer.encode(text)
        # 将token ids转换为numpy数组
        token_ids = np.array(token_ids, dtype=np.int32)
        return token_ids

    @staticmethod
    def is_subsequence(short_tuple: tuple, long_tuple: tuple) -> bool:
        """判断short_tuple是否为long_tuple的顺序相等的子集"""
        if len(short_tuple) > len(long_tuple):
            return False

        i = 0
        for item in long_tuple:
            if i < len(short_tuple) and item == short_tuple[i]:
                i += 1

        return i == len(short_tuple)

    def tokenize_disordered_with_word_count_and_parse_search(self, input_str_list: list[str]) -> dict[str: str | int]:
        # 在这里处理传入的参数
        token_id_num_dict = {}
        token_ids_list = []
        connected_token_ids_dict = {}
        extra_search_token_ids_dict = {}
        to_add_token_ids_num_dict = {}
        token_num = 0
        for s in input_str_list:
            s = s.strip(' ')
            seg_s = s.split(' ')
            token_ids = []
            for segment_s in seg_s:
                segment_s_token_ids = self.tokenize(segment_s)
                token_ids.extend(segment_s_token_ids)
            token_num += len(token_ids)
            logger.debug('%s -> %s', s, token_ids)
            token_ids_list.append(token_ids)
            for token_id in token_ids:
                # 统计单token频次（跳过stop word在最后统一处理）
                token_id_num_dict[token_id] = token_id_num_dict.get(token_id, 0) + 1

        # -------------------------------------------------------------
        # Apriori风格的高频连词（短语）挖掘：
        # 1. 频次超过threshold的单token作为种子
        # 2. 逐轮尝试将种子延长一个token，只有延长后的连词同样高频才保留
        # 3. 循环直到没有更长的连词产生（类似Apriori的逐层搜索）
        # -------------------------------------------------------------
        threshold = 2 + max(int(token_num / 250) - 1, 0)
        logger.debug('Parse threshold: %d', threshold)
        for token_id in token_id_num_dict:
            if token_id_num_dict[token_id] >= threshold:
                extra_search_token_ids_dict[token_id] = token_id_num_dict[token_id]
        extra_search_length = 1
        while True:
            if_continued = False
            # 依次获取之前每一个str转化为的token_ids
            for token_ids in token_ids_list:
                # 对每一个进行遍历
                for index, token_id in enumerate(token_ids):
                    # 如果已经到底，结束
                    if index + extra_search_length >= len(token_ids):
                        break
                    # 先获取旧的连词，判断是否存在
                    cut_token_ids = tuple(token_ids[index:index + extra_search_length])
                    if cut_token_ids in extra_search_token_ids_dict:
                        # 加入下一个token_id并且形成新的连词列表
                        cut_token_ids = tuple(token_ids[index:index + extra_search_length + 1])
                        to_add_token_ids_num_dict[cut_token_ids] = to_add_token_ids_num_dict.get(cut_token_ids, 0) + 1
            # 把数量大于threshold的新连词保存起来
            new_extra_search_token_ids_dict = {}
            for token_ids in to_add_token_ids_num_dict:
                if to_add_token_ids_num_dict[token_ids] >= threshold:
                    if_continued = True
                    new_extra_search_token_ids_dict[token_ids] = to_add_token_ids_num_dict[token_ids]
            # 把旧的没有被续接的给存起来，续接的删除掉
            if extra_search_length > 1:
                for token_ids in extra_search_token_ids_dict:
                    connected_token_ids_dict[token_ids] = extra_search_token_ids_dict[token_ids]
            extra_search_token_ids_dict = new_extra_search_token_ids_dict
            to_add_token_ids_num_dict.clear()
            if if_continued:
                extra_search_length += 1
            else:
                break

        # 去除被包含的连词
        to_remove_key_list = []
        repeat_check_list = sorted(connected_token_ids_dict.keys(), key=lambda k: len(k), reverse=True)
        for index, token_ids in enumerate(repeat_check_list):
            for token_ids_ in repeat_check_list[index + 1:]:
                if len(token_ids_) < len(token_ids):
                    if self.is_subsequence(token_ids_, token_ids):
                        connected_token_ids_dict[token_ids_] -= connected_token_ids_dict[token_ids]
                        if connected_token_ids_dict[token_ids_] <= 0:
                            to_remove_key_list.append(token_ids_)
        for token_ids in set(to_remove_key_list):
            del connected_token_ids_dict[token_ids]

        # 整理结果：把连词的计数从组成它的单token计数中扣除
        to_remove_key_list.clear()
        for token_ids in connected_token_ids_dict:
            for token_id in token_ids:
                token_id_num_dict[token_id] -= connected_token_ids_dict[token_ids]
                if token_id_num_dict[token_id] <= 0:
                    to_remove_key_list.append(token_id)
            token_id_num_dict[token_ids] = connected_token_ids_dict[token_ids]
        for token_id in set(to_remove_key_list):
            del token_id_num_dict[token_id]
        result_dict = {}
        for token_ids in token_id_num_dict:
            if isinstance(token_ids, np.int32):
                if token_ids in self.stop_word_token_id_list:
                    continue
                result_dict[str(token_ids)] = token_id_num_dict[token_ids]
            else:
                str_token_ids = '-'.join(str(item) for item in token_ids)
                if str_token_ids in self.stop_word_token_id_list:
                    continue
                result_dict[str_token_ids] = token_id_num_dict[token_ids]
        # 找到频率最高的几个词，拼接为ARTICLE_ID（正排表的文章唯一标识）
        sorted_key_world_list = sorted(list(result_dict.keys()), key=lambda k: (result_dict[k], len(k)), reverse=True)
        if len(sorted_key_world_list) > 10:
            sorted_key_world_list = sorted_key_world_list[:10]
        result_dict['ARTICLE_ID'] = '='.join(sorted_key_world_list)
        return result_dict

    def tokenize_in_order(self, input_str: str) -> dict[str, list[str]]:
        input_str = input_str.strip()
        seg_input = input_str.split(' ')
        input_str_token_id_list = []
        for seg_str in seg_input:
            token_ids = [str(_) for _ in self.tokenize(seg_str)]
            input_str_token_id_list.extend(token_ids)
        result_dict = {'TOKEN_ID': input_str_token_id_list}
        return result_dict


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    tokenizer = SearchEngineTokenizerGPT2()
    print(tokenizer.tokenize_disordered_with_word_count_and_parse_search([
        ' 赛博朋克2077真好玩',
        ' 赛博朋克 怎么赚钱',
        '我想下载赛博 朋克 ',
        'steam赛博朋克售价',
        '赛博朋克 鬼畜',
        '赛 博 朋 克 真 好 玩',
        '【赛博朋克2077】这游戏bug真多'
    ]))
    print(tokenizer.tokenize_disordered_with_word_count_and_parse_search([
        'How to play Overwatch2',
        'How to download Overwatch2',
        'What\'s overwatch',
        'Overwatch2 Ana',
        'Overwatch2 DV.A',
        'Overwatch Reaper'
    ]))
