# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from BaseModule import Crawler


class SimpleCrawler(Crawler):
    def fetch_content(self, url: str) -> str:
        response = requests.get(url)
        return response.text

    def extract_title(self, content: str) -> str:
        soup = BeautifulSoup(content, 'html.parser')
        title = soup.title.string if soup.title else ''
        return title.strip()

    def extract_text(self, content: str) -> str:
        soup = BeautifulSoup(content, 'html.parser')
        # 首先尝试查找<p>标签
        paragraphs = soup.find_all('p')
        text = ''
        if paragraphs:
            text = ' '.join(p.get_text() for p in paragraphs)
        else:
            # 如果没有找到<p>标签,尝试提取其他元素的文本内容
            # 按照优先级顺序查找:  <a>, <button>, <h1>-<h6>, <div>, <span>
            elements = soup.find_all(['a', 'button', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'span'])
            if elements:
                text = ' '.join(elem.get_text() for elem in elements)
        return text.strip()

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
        links = []

        # 提取<a>标签中的href属性值
        for link in soup.find_all('a', href=True):
            links.append(link['href'])

        if not len(links):
            # 提取<link>标签中的href属性值
            for link in soup.find_all('link', href=True):
                links.append(link['href'])
            # 提取<script>标签中的src属性值
            for script in soup.find_all('script', src=True):
                links.append(script['src'])
            # 提取<img>标签中的src属性值
            for img in soup.find_all('img', src=True):
                links.append(img['src'])
            # 提取<iframe>标签中的src属性值
            for iframe in soup.find_all('iframe', src=True):
                links.append(iframe['src'])

        return links

    def is_valid_url(self, url: str) -> bool:
        return url.startswith('http://') or url.startswith('https://')

    def normalize_url(self, url: str, base_url: str) -> str:
        return urljoin(base_url, url)


if __name__ == '__main__':
    crawler = SimpleCrawler('https://www.bilibili.com/', 3, 3)
    result = crawler.crawl()
    for url in result:
        print('-' * 20)
        print(url)
        print(result[url])
