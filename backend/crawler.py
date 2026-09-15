# -*- coding: utf-8 -*-
"""BFS web crawler with robots.txt (gentleman's agreement) support."""
import logging
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from config import CRAWLER_RESPECT_ROBOTS, CRAWLER_TIMEOUT_SECONDS, CRAWLER_USER_AGENT

logger = logging.getLogger(__name__)


class SimpleCrawler:
    """Breadth-first crawler extracting title / text / icon / og:image / links."""

    def __init__(self, start_url: str, max_depth: int, max_sublinks: int):
        # When in China, you are supposed to follow the law of government.
        # 当在中国时，你需要遵守政府法律规定使用爬虫。
        # 网络爬虫的法律规制：https://www.cac.gov.cn/2019-06/16/c_1124630015.htm
        self.start_url = start_url
        self.max_depth = max_depth
        self.max_sublinks = max_sublinks
        self.timeout = CRAWLER_TIMEOUT_SECONDS
        self.user_agent = CRAWLER_USER_AGENT
        self.respect_robots = CRAWLER_RESPECT_ROBOTS
        # 记录已经解析好的君子协议Robots.txt（按站点缓存）
        self.robots_dict: dict[str, RobotFileParser | None] = {}

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------
    def crawl(self) -> dict[str, dict]:
        result: dict[str, dict] = {}
        visited_urls: set[str] = set()
        queue: list[tuple[str, int]] = [(self.start_url, 0)]

        logger.info('Starting crawling from: %s', self.start_url)

        while queue:
            url, depth = queue.pop(0)

            if depth >= self.max_depth:
                logger.debug('Skipping URL: %s (reached maximum depth %d)', url, self.max_depth)
                continue
            if len(result) >= self.max_sublinks:
                logger.debug('Skipping URL: %s (reached maximum sublinks %d)', url, self.max_sublinks)
                continue
            if url in visited_urls:
                logger.debug('Skipping URL: %s (already visited)', url)
                continue

            if self.respect_robots and not self._is_allowed_by_robots(url):
                logger.info('Skipping URL: %s (disallowed by robots.txt)', url)
                continue

            logger.info("Processing %d'th URL: %s (depth %d)", len(result) + 1, url, depth)
            visited_urls.add(url)

            try:
                content = self.fetch_content(url)
            except Exception as e:
                logger.warning('Failed to fetch %s: %s', url, e)
                continue

            result[url] = {
                'title': self.extract_title(content),
                'content': self.extract_text(content),
                'icon': self.extract_icon(content),
                'main_image': self.extract_main_image(content),
                'sublinks': [],
            }

            for link in self.extract_links(content):
                normalized_link = self.normalize_url(link, url)
                if self.is_valid_url(normalized_link):
                    queue.append((normalized_link, depth + 1))
                    result[url]['sublinks'].append(normalized_link)

        logger.info('Crawling completed, %d pages fetched.', len(result))
        return result

    # ------------------------------------------------------------------
    # fetching & extraction
    # ------------------------------------------------------------------
    def fetch_content(self, url: str) -> str:
        response = requests.get(
            url,
            timeout=self.timeout,
            headers={'User-Agent': self.user_agent},
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding
        return response.text

    def extract_title(self, content: str) -> str:
        soup = BeautifulSoup(content, 'html.parser')
        title = soup.title.string if soup.title else ''
        return title.strip()

    def extract_text(self, content: str) -> str:
        soup = BeautifulSoup(content, 'html.parser')
        # 优先提取<p>标签；没有<p>时按优先级兜底提取其他元素文本
        paragraphs = soup.find_all('p')
        if paragraphs:
            return ' '.join(p.get_text() for p in paragraphs).strip()
        elements = soup.find_all(['a', 'button', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'span'])
        if elements:
            return ' '.join(elem.get_text() for elem in elements).strip()
        return ''

    def extract_icon(self, content: str) -> str:
        soup = BeautifulSoup(content, 'html.parser')
        icon_link = soup.find('link', rel='icon')
        return icon_link['href'] if icon_link else ''

    def extract_main_image(self, content: str) -> str:
        soup = BeautifulSoup(content, 'html.parser')
        main_image = soup.find('meta', property='og:image')
        return main_image['content'] if main_image else ''

    def extract_links(self, content: str) -> list[str]:
        soup = BeautifulSoup(content, 'html.parser')
        links = [link['href'] for link in soup.find_all('a', href=True)]
        if not links:
            # 没有<a>时提取静态资源链接
            for tag, attr in (('link', 'href'), ('script', 'src'), ('img', 'src'), ('iframe', 'src')):
                links.extend(el[attr] for el in soup.find_all(tag) if el.get(attr))
        return links

    def is_valid_url(self, url: str) -> bool:
        return url.startswith('http://') or url.startswith('https://')

    def normalize_url(self, url: str, base_url: str) -> str:
        return urljoin(base_url, url)

    # ------------------------------------------------------------------
    # robots.txt helpers
    # ------------------------------------------------------------------
    def _is_allowed_by_robots(self, url: str) -> bool:
        root_url = f'{urlparse(url).scheme}://{urlparse(url).netloc}'
        if root_url not in self.robots_dict:
            robots_txt_url = f'{root_url}/robots.txt'
            logger.info('Parsing robots.txt from %s ...', robots_txt_url)
            rp = RobotFileParser()
            rp.set_url(robots_txt_url)
            try:
                rp.read()
            except Exception as e:
                logger.warning('Failed to read robots.txt from %s: %s', robots_txt_url, e)
            self.robots_dict[root_url] = rp
        parser = self.robots_dict[root_url]
        return parser is None or parser.can_fetch('*', url)
