# -*- coding: utf-8 -*-
"""ARC algorithm service (Tornado).

Endpoints consumed by the Java backend:
  POST /disordered_tokenize  {content: [str, ...] | "['a','b']"} -> {tokenId: count, ..., ARTICLE_ID: str}
  POST /ordered_tokenize     {content: str}                      -> {TOKEN_ID: [str, ...]}
  POST /get_related_words    {content: str}                      -> {word: tokenIds, ...}
  POST /chat_with_AI         [{role, content}, ...]              -> {role, content}
  POST /crawler              {start_url, max_depth, max_suburl}  -> {url: {title, content, ...}}
  GET  /health                                                   -> liveness probe
"""
import ast
import json
import logging

from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler

from ChatWithAi import get_ai_response
from Crawler import SimpleCrawler
from GetRelatedWords import get_related_word
from Tokenizer import SearchEngineTokenizerGPT2
from config import SERVICE_PORT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

tokenizer = SearchEngineTokenizerGPT2()


def parse_content_list(raw) -> list[str]:
    """Accept either a native JSON array or a string-encoded Python/JSON list.

    The legacy Java client sent a stringified Python list; the historical
    implementation parsed it with eval(), which allowed arbitrary code
    execution. json.loads + ast.literal_eval are safe for both formats.
    """
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = ast.literal_eval(raw)
        if isinstance(parsed, list):
            return parsed
    raise ValueError('"content" must be a list of strings.')


class BaseHandler(RequestHandler):
    def write_error_payload(self, status: int, message: str):
        self.set_status(status)
        self.write(json.dumps({'error': message}))

    def read_json_body(self) -> dict:
        try:
            return json.loads(self.request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.write_error_payload(400, 'Request body must be valid JSON.')
            return None


class HealthCheck(RequestHandler):
    def get(self):
        self.write(json.dumps({'status': 'ok'}))


class DisorderedTokenizer(BaseHandler):
    def post(self):
        data = self.read_json_body()
        if data is None:
            return
        try:
            content = parse_content_list(data.get('content', ''))
        except (ValueError, SyntaxError, TypeError) as e:
            self.write_error_payload(400, f'Invalid "content": {e}')
            return
        if not content:
            self.write_error_payload(400, '"content" is empty.')
            return
        result = tokenizer.tokenize_disordered_with_word_count_and_parse_search(content)
        self.write(json.dumps(result))


class OrderedTokenizer(BaseHandler):
    def post(self):
        data = self.read_json_body()
        if data is None:
            return
        content = data.get('content', '')
        if not content:
            self.write_error_payload(400, '"content" keyword not found.')
            return
        result = tokenizer.tokenize_in_order(content)
        self.write(json.dumps(result))


class KeywordExpander(BaseHandler):
    def post(self):
        data = self.read_json_body()
        if data is None:
            return
        content = data.get('content', '')
        if not content:
            self.write_error_payload(400, '"content" keyword not found.')
            return
        result = get_related_word(content, tokenizer)
        self.write(json.dumps(result))


class AIAssistant(BaseHandler):
    def post(self):
        data = self.read_json_body()
        if data is None:
            return
        if isinstance(data, dict):
            data = [data]
        if not data:
            self.write_error_payload(400, 'History data not found.')
            return
        try:
            result = get_ai_response(data)
        except Exception as e:
            logger.exception('All LLM backends failed.')
            self.write_error_payload(502, f'LLM backends unavailable: {e}')
            return
        self.write(json.dumps({'role': 'assistant', 'content': result}))


class CrawlerAgent(BaseHandler):
    def post(self):
        data = self.read_json_body()
        if data is None:
            return
        start_url = data.get('start_url', '')
        max_depth = data.get('max_depth', 3)
        max_suburl = data.get('max_suburl', 100)
        if not start_url:
            self.write_error_payload(400, '"start_url" is required.')
            return
        try:
            max_depth = int(max_depth)
            max_suburl = int(max_suburl)
        except (ValueError, TypeError):
            self.write_error_payload(400, '"max_depth" and "max_suburl" parameters must be integers.')
            return
        crawler = SimpleCrawler(start_url, max_depth, max_suburl)
        self.write(json.dumps(crawler.crawl()))


def make_app():
    return Application([
        (r'/health', HealthCheck),
        (r'/disordered_tokenize', DisorderedTokenizer),
        (r'/ordered_tokenize', OrderedTokenizer),
        (r'/get_related_words', KeywordExpander),
        (r'/chat_with_AI', AIAssistant),
        (r'/crawler', CrawlerAgent),
    ])


if __name__ == '__main__':
    app = make_app()
    app.listen(SERVICE_PORT)
    logger.info('Tornado server is running on port %d.', SERVICE_PORT)
    IOLoop.current().start()
