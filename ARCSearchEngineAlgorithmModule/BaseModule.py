# -*- coding: utf-8 -*-
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from config import FOLLOW_GENTLEMANS_AGREEMENT


class SearchEngineTokenizer:
    def __init__(self):
        raise NotImplementedError('Subclass must implement this method.')

    def tokenize_disordered_with_word_couont_and_parse_search(self, input_str_list: list[str]) -> dict[str: str | int]:
        """
           将输入的字符串列表进行分词,返回一个字典,其中键为词ID或短语ID,值为对应的频次。
           同时,字典中还包含一个特殊的键'ARTICLE_ID',其值为频次最高的十个词的ID,用等号连接。

           Tokenizes the input list of strings and returns a dictionary where the keys are word IDs or phrase IDs,
           and the values are their corresponding frequencies.
           The dictionary also includes a special key 'ARTICLE_ID', whose value is the concatenation of the IDs
           of the ten most frequent words, connected by equals signs.

           :param input_str_list: 输入的字符串列表,每个元素为一个句子 / Input list of strings, each element is a sentence
           :return: 分词结果字典 / Dictionary of tokenization results
       """
        raise NotImplementedError('Subclass must implement this method.')

    def tokenize_in_order(self, input_str: str) -> dict[str, list[str]]:
        """
           将输入的字符串按照空格分割,并将每个词转化为对应的词ID,按照原始顺序返回一个字典,
           其中键为固定字符串'TOKEN_ID',值为词ID的列表。

           Splits the input string by spaces and converts each word into its corresponding word ID.
           Returns a dictionary where the key is the fixed string 'TOKENS',
           and the value is the list of word IDs in their original order.

           :param input_str: 输入的字符串 / Input string
           :return: 分词结果字典 / Dictionary of tokenization results
        """
        raise NotImplementedError('Subclass must implement this method.')


class AIModule:
    def __init__(self):
        raise NotImplementedError('Subclass must implement this method.')

    def get_response(self, input: object) -> str:
        raise NotImplementedError('Subclass must implement this method.')


class Crawler:
    def __init__(self, start_url: str, max_depth: int, max_sublinks: int):
        """
        初始化爬虫,设置起始URL、最大爬取深度和最大子链接数量
        Initialize the crawler with a starting URL, maximum crawling depth, and maximum number of sublinks

        :param start_url: 起始URL / Starting URL
        :param max_depth: 最大爬取深度 / Maximum crawling depth
        :param max_sublinks: 最大子链接数量 / Maximum number of sublinks
        """
        # When in China, you are supposed to follow the law of government.
        # 当在中国时，你需要遵守政府法律规定使用爬虫。
        # 网络爬虫的法律规制：https://www.cac.gov.cn/2019-06/16/c_1124630015.htm
        self.start_url = start_url
        self.max_depth = max_depth
        self.max_sublinks = max_sublinks
        # 记录已经解析好的君子协议Robots.txt
        self.robots_dict = {}

    def crawl(self) -> dict[str, dict]:
        """
        执行爬虫主逻辑,遍历页面并提取信息
        Main crawling logic, traverse pages and extract information

        :return: 爬取结果字典,键为URL,值为包含标题、正文、图标、主图和子链接的字典 /
                 Dictionary of crawling results, keys are URLs and values are dictionaries containing title, content, icon, main image, and sublinks
        """
        result = {}
        visited_urls = set()
        queue = [(self.start_url, 0)]

        print(f"Starting crawling from: {self.start_url}")

        while queue:
            url, depth = queue.pop(0)

            if depth >= self.max_depth:
                print(f"Skipping URL: {url} due to reaching maximum depth: {self.max_depth}")
                continue

            if len(result) >= self.max_sublinks:
                print(f"Skipping URL: {url} due to reaching maximum sublinks: {self.max_sublinks}")
                continue

            if url in visited_urls:
                print(f"Skipping URL: {url} as it has already been visited")
                continue

            # Robots.txt
            # 默认需要遵守Robots.txt
            if FOLLOW_GENTLEMANS_AGREEMENT:
                root_url = self.get_root_url(url)
                if root_url not in self.robots_dict:
                    robots_txt_url = f"{root_url}/robots.txt"
                    print(f'Parsing robots.txt from {robots_txt_url}...')
                    self.robots_dict[root_url] = self.parse_robots_txt(robots_txt_url)
                    print('-' * 10, 'Robots.txt', '-' * 10)
                    print('Robots.txt result:', self.robots_dict[root_url])
                    print('-' * 10, 'Robots.txt', '-' * 10)
                else:
                    print('This website\'s Robots.txt file has already been parsed.')
                if not self.is_allowed_by_robots_txt(url, self.robots_dict[root_url]):
                    print(f"Skipping URL: {url} as it is not allowed by robots.txt")
                    continue

            print('-' * 10, f"Processing {len(result) + 1}\'th URL: {url} at depth: {depth}", '-' * 10)
            visited_urls.add(url)

            print(f"Fetching content for URL: {url}")
            content = self.fetch_content(url)

            print(f"Extracting information for URL: {url}")
            title = self.extract_title(content)
            text = self.extract_text(content)
            icon = self.extract_icon(content)
            main_image = self.extract_main_image(content)

            result[url] = {
                'title': title,
                'content': text,
                'icon': icon,
                'main_image': main_image,
                'sublinks': []
            }

            print(f"Extracting links for URL: {url}")
            links = self.extract_links(content)
            for link in links:
                normalized_link = self.normalize_url(link, url)
                if self.is_valid_url(normalized_link):
                    print(f"Adding valid sublink: {normalized_link} for URL: {url}")
                    queue.append((normalized_link, depth + 1))
                    result[url]['sublinks'].append(normalized_link)
                else:
                    print(f"Skipping invalid sublink: {link} for URL: {url}")
        print("Crawling completed")
        return result

    def extract_title(self, content: str) -> str:
        """
        从页面内容中提取标题
        Extract the title from the webpage content

        :param content: 页面内容 / Webpage content
        :return: 页面标题 / Title of the webpage
        """
        raise NotImplementedError('Subclass must implement this method.')

    def fetch_content(self, url: str) -> str:
        """
        根据URL获取页面内容
        Fetch the content of a webpage given its URL

        :param url: 要获取内容的URL / URL of the webpage to fetch
        :return: 页面内容 / Content of the webpage
        """
        raise NotImplementedError('Subclass must implement this method.')

    def extract_text(self, content: str) -> str:
        """
        从页面内容中提取正文
        Extract the main text content from the webpage content

        :param content: 页面内容 / Webpage content
        :return: 页面正文 / Main text content of the webpage
        """
        raise NotImplementedError('Subclass must implement this method.')

    def extract_icon(self, content: str) -> str:
        """
        从页面内容中提取图标的URL
        Extract the URL of the icon from the webpage content

        :param content: 页面内容 / Webpage content
        :return: 图标的URL / URL of the icon
        """
        raise NotImplementedError('Subclass must implement this method.')

    def extract_main_image(self, content: str) -> str:
        """
        从页面内容中提取主图的URL
        Extract the URL of the main image from the webpage content

        :param content: 页面内容 / Webpage content
        :return: 主图的URL / URL of the main image
        """
        raise NotImplementedError('Subclass must implement this method.')

    def extract_links(self, content: str) -> list[str]:
        """
        从页面内容中提取链接的URL列表
        Extract the URLs of links from the webpage content

        :param content: 页面内容 / Webpage content
        :return: 链接URL列表 / List of link URLs
        """
        raise NotImplementedError('Subclass must implement this method.')

    def is_valid_url(self, url: str) -> bool:
        """
        判断URL是否合法
        Check if a URL is valid

        :param url: 要判断的URL / URL to check
        :return: URL是否合法 / Whether the URL is valid
        """
        raise NotImplementedError('Subclass must implement this method.')

    def normalize_url(self, url: str, base_url: str) -> str:
        """
        规范化URL,将相对URL转换为绝对URL
        Normalize a URL by converting a relative URL to an absolute URL

        :param url: 要规范化的URL / URL to normalize
        :param base_url: 基准URL,用于解析相对URL / Base URL for resolving relative URLs
        :return: 规范化后的URL / Normalized URL
        """
        raise NotImplementedError('Subclass must implement this method.')

    # Robots.txt
    @staticmethod
    def get_root_url(url: str) -> str:
        """
        获取URL的根目录
        Get the root directory of a URL

        :param url: URL
        :return: 根目录URL / Root directory URL
        """
        parsed_url = urlparse(url)
        root_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        return root_url

    @staticmethod
    def parse_robots_txt(robots_txt_url: str) -> RobotFileParser:
        """
        解析robots.txt文件
        Parse the robots.txt file

        :param robots_txt_url: robots.txt文件的URL / URL of the robots.txt file
        :return: 解析后的RobotFileParser对象 / Parsed RobotFileParser object
        """
        rp = RobotFileParser()
        rp.set_url(robots_txt_url)
        rp.read()
        return rp

    @staticmethod
    def is_allowed_by_robots_txt(url: str, rp: RobotFileParser) -> bool:
        """
        检查URL是否被robots.txt允许爬取
        Check if a URL is allowed to be crawled according to robots.txt

        :param url: 要检查的URL / URL to check
        :param rp: 解析后的RobotFileParser对象 / Parsed RobotFileParser object
        :return: 是否允许爬取 / Whether crawling is allowed
        """
        return rp.can_fetch("*", url)
