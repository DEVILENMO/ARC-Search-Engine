# -*- coding: utf-8 -*-
import numpy as np
from transformers import GPT2Tokenizer

from BaseModule import SearchEngineTokenizer


class SearchEngineTokenizerGPT2(SearchEngineTokenizer):
    def __init__(self):
        # 初始化GPT-2 tokenizer
        self.char_tokenizer = GPT2Tokenizer.from_pretrained('gpt2')

        self.blank_token = self.tokenize(' ')

        # load stopwords
        try:
            stopwords_file = 'stopwords.txt'
            stopwords_list = self.load_stopwords(stopwords_file)
            # print(stopwords_list)
            # print(f'Loaded {len(stopwords_list)} stopwords.')
        except:
            stopwords_list = ['a', 'about', 'above', 'across', 'after', 'again', 'against', 'all', 'almost', 'alone',
                              'along',
                              'already', 'also',
                              'although', 'always', 'among', 'an', 'and', 'another', 'any', 'anybody', 'anyone',
                              'anything',
                              'anywhere', 'are',
                              'area', 'areas', 'around', 'as', 'ask', 'asked', 'asking', 'asks', 'at', 'away', 'b',
                              'back',
                              'backed', 'backing',
                              'backs', 'be', 'became', 'because', 'become', 'becomes', 'been', 'before', 'began',
                              'behind',
                              'being', 'beings',
                              'best', 'better', 'between', 'big', 'both', 'but', 'by', 'c', 'came', 'can', 'cannot',
                              'case',
                              'cases', 'certain',
                              'certainly', 'clear', 'clearly', 'come', 'could', 'd', 'did', 'differ', 'different',
                              'differently', 'do', 'does',
                              'done', 'down', 'down', 'downed', 'downing', 'downs', 'during', 'e', 'each', 'early',
                              'either',
                              'end', 'ended',
                              'ending', 'ends', 'enough', 'even', 'evenly', 'ever', 'every', 'everybody', 'everyone',
                              'everything', 'everywhere',
                              'f', 'face', 'faces', 'fact', 'facts', 'far', 'felt', 'few', 'find', 'finds', 'first',
                              'for',
                              'four', 'from',
                              'full', 'fully', 'further', 'furthered', 'furthering', 'furthers', 'g', 'gave', 'general',
                              'generally', 'get',
                              'gets', 'give', 'given', 'gives', 'go', 'going', 'good', 'goods', 'got', 'great',
                              'greater',
                              'greatest', 'group',
                              'grouped', 'grouping', 'groups', 'h', 'had', 'has', 'have', 'having', 'he', 'her', 'here',
                              'herself', 'high',
                              'high', 'high', 'higher', 'highest', 'him', 'himself', 'his', 'how', 'however', 'i', 'if',
                              'important', 'in',
                              'interest', 'interested', 'interesting', 'interests', 'into', 'is', 'it', 'its', 'itself',
                              'j',
                              'just', 'k',
                              'keep', 'keeps', 'kind', 'knew', 'know', 'known', 'knows', 'l', 'large', 'largely',
                              'last',
                              'later', 'latest',
                              'least', 'less', 'let', 'lets', 'like', 'likely', 'long', 'longer', 'longest', 'm',
                              'made',
                              'make', 'making',
                              'man', 'many', 'may', 'me', 'member', 'members', 'men', 'might', 'more', 'most', 'mostly',
                              'mr',
                              'mrs', 'much',
                              'must', 'my', 'myself', 'n', 'necessary', 'need', 'needed', 'needing', 'needs', 'never',
                              'new',
                              'new', 'newer',
                              'newest', 'next', 'no', 'nobody', 'non', 'noone', 'not', 'nothing', 'now', 'nowhere',
                              'number',
                              'numbers', 'o',
                              'of', 'off', 'often', 'old', 'older', 'oldest', 'on', 'once', 'one', 'only', 'open',
                              'opened',
                              'opening', 'opens',
                              'or', 'order', 'ordered', 'ordering', 'orders', 'other', 'others', 'our', 'out', 'over',
                              'p',
                              'part', 'parted',
                              'parting', 'parts', 'per', 'perhaps', 'place', 'places', 'point', 'pointed', 'pointing',
                              'points',
                              'possible',
                              'present', 'presented', 'presenting', 'presents', 'problem', 'problems', 'put', 'puts',
                              'q',
                              'quite', 'r',
                              'rather', 'really', 'right', 'right', 'room', 'rooms', 's', 'said', 'same', 'saw', 'say',
                              'says',
                              'second',
                              'seconds', 'see', 'seem', 'seemed', 'seeming', 'seems', 'sees', 'several', 'shall', 'she',
                              'should', 'show',
                              'showed', 'showing', 'shows', 'side', 'sides', 'since', 'small', 'smaller', 'smallest',
                              'so',
                              'some', 'somebody',
                              'someone', 'something', 'somewhere', 'state', 'states', 'still', 'still', 'such', 'sure',
                              't',
                              'take', 'taken',
                              'than', 'that', 'the', 'their', 'them', 'then', 'there', 'therefore', 'these', 'they',
                              'thing',
                              'things', 'think',
                              'thinks', 'this', 'those', 'though', 'thought', 'thoughts', 'three', 'through', 'thus',
                              'to',
                              'today', 'together',
                              'too', 'took', 'toward', 'turn', 'turned', 'turning', 'turns', 'two', 'u', 'under',
                              'until', 'up',
                              'upon', 'us',
                              'use', 'used', 'uses', 'v', 'very', 'w', 'want', 'wanted', 'wanting', 'wants', 'was',
                              'way',
                              'ways', 'we', 'well',
                              'wells', 'went', 'were', 'what', 'when', 'where', 'whether', 'which', 'while', 'who',
                              'whole',
                              'whose', 'why',
                              'will', 'with', 'within', 'without', 'work', 'worked', 'working', 'works', 'would', 'x',
                              'y',
                              'year', 'years',
                              'yet', 'you', 'young', 'younger', 'youngest', 'your', 'yours', 'z']
            # print(f'Loaded {len(stopwords_list)} stopwords.')
        stop_word_token_id_list = []
        for stopword in stopwords_list:
            token_ids = self.tokenize(stopword)
            str_token_ids = '-'.join([str(_) for _ in token_ids])
            stop_word_token_id_list.append(str_token_ids)
        stop_word_token_id_list.append('-'.join([str(_) for _ in self.blank_token]))
        # print('stop word token id list:', stop_word_token_id_list)
        self.stop_word_token_id_list = list(set(stop_word_token_id_list))

    def tokenize(self, text: str) -> np.ndarray:
        # 对传入的文本进行tokenize
        token_ids = self.char_tokenizer.encode(text)
        # 将token ids转换为numpy数组
        token_ids = np.array(token_ids, dtype=np.int32)
        return token_ids

    @staticmethod
    def load_stopwords(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            stopwords = file.read().splitlines()
        return stopwords

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

    def tokenize_disordered_with_word_couont_and_parse_search(self, input_str_list: list[str]) -> dict[str: str | int]:
        # 在这里处理传入的参数
        token_id_num_dict = {}
        token_ids_list = []
        connected_token_ids_dict = {}
        extra_search_token_ids_dict = {}
        to_add_token_ids_num_dict = {}
        # print('转化为token_id...')
        token_num = 0
        for s in input_str_list:
            s = s.strip(' ')
            seg_s = s.split(' ')
            token_ids = []
            for segment_s in seg_s:
                segment_s_token_ids = self.tokenize(segment_s)
                token_ids.extend(segment_s_token_ids)
            token_num += len(token_ids)
            print(f'{s} -> {token_ids}')
            token_ids_list.append(token_ids)
            for token_id in token_ids:
                # 跳过stop word
                if token_id not in token_id_num_dict:
                    token_id_num_dict[token_id] = 1
                else:
                    token_id_num_dict[token_id] += 1
        # print(token_id_num_dict)
        # Apriori
        threshold = 2 + max(int(token_num / 250) - 1, 0)
        print(f'Parse threshold: {threshold}')
        for token_id in token_id_num_dict:
            if token_id_num_dict[token_id] >= threshold:
                extra_search_token_ids_dict[token_id] = token_id_num_dict[token_id]
        # print('额外搜索范围：', extra_search_token_ids_dict)
        extra_search_length = 1
        while True:
            if_continued = False
            # print('-' * 30)
            # print(f'根据以下高频token_id进行连词搜索：{extra_search_token_ids_dict}')
            # print(f'额外搜索长度{extra_search_length}')
            # 依次获取之前每一个str转化为的token_ids
            for token_ids in token_ids_list:
                # 对每一个进行遍历
                # print(f'正在{token_ids}中查询是否可以延长')
                for index, token_id in enumerate(token_ids):
                    # 如果已经到底，结束
                    if index + extra_search_length >= len(token_ids):
                        break
                    # 先获取旧的连词，判断是否存在
                    cut_token_ids = tuple(token_ids[index:index + extra_search_length])
                    # print('取出词判断是否需要扩展：', cut_token_ids)
                    if cut_token_ids in list(extra_search_token_ids_dict.keys()):
                        # 加入下一个token_id并且形成新的连词列表
                        cut_token_ids = tuple(token_ids[index:index + extra_search_length + 1])
                        # print('添加新连词：', cut_token_ids)
                        if cut_token_ids not in to_add_token_ids_num_dict:
                            to_add_token_ids_num_dict[cut_token_ids] = 1
                        else:
                            to_add_token_ids_num_dict[cut_token_ids] += 1
            # 把数量大于1的新连词保存起来
            new_extra_search_token_ids_dict = {}
            for token_ids in to_add_token_ids_num_dict:
                if to_add_token_ids_num_dict[token_ids] >= threshold:
                    if not if_continued:
                        if_continued = True
                    new_extra_search_token_ids_dict[token_ids] = to_add_token_ids_num_dict[token_ids]
                    # print('找到高频新连词：', token_ids)
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
        # print('connected_token_ids_dict:')
        # for key in connected_token_ids_dict:
        #     print(key, connected_token_ids_dict[key])
        to_remove_key_list = []
        repeat_check_list = list(connected_token_ids_dict.keys())
        repeat_check_list = sorted(repeat_check_list, key=lambda k: len(k), reverse=True)
        for index, token_ids in enumerate(repeat_check_list):
            for token_ids_ in repeat_check_list[index + 1:]:
                if len(token_ids_) < len(token_ids):
                    if self.is_subsequence(token_ids_, token_ids):
                        connected_token_ids_dict[token_ids_] -= connected_token_ids_dict[token_ids]
                        if connected_token_ids_dict[token_ids_] <= 0:
                            to_remove_key_list.append(token_ids_)
        for token_ids in set(to_remove_key_list):
            del connected_token_ids_dict[token_ids]

        # 整理结果
        to_remove_key_list.clear()
        for token_ids in connected_token_ids_dict:
            # print(token_ids, connected_token_ids_dict[token_ids])
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
        # 找到频率最高的几个词
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
        result_dict = {"TOKEN_ID": input_str_token_id_list}
        return result_dict


if __name__ == '__main__':
    tokenizer = SearchEngineTokenizerGPT2()
    print(tokenizer.tokenize_disordered_with_word_couont_and_parse_search([
        ' 赛博朋克2077真好玩',
        ' 赛博朋克 怎么赚钱',
        '我想下载赛博 朋克 ',
        'steam赛博朋克售价',
        '赛博朋克 鬼畜',
        '赛 博 朋 克 真 好 玩',
        '【赛博朋克2077】这游戏bug真多'
    ]))
    print(tokenizer.tokenize_disordered_with_word_couont_and_parse_search([
        'How to play Overwatch2',
        'How to download Overwatch2',
        'What\'s overwatch',
        'Overwatch2 Ana',
        'Overwatch2 DV.A',
        'Overwatch Reaper'
    ]))
