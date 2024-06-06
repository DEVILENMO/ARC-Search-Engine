import json
from tornado.web import Application, RequestHandler
from tornado.ioloop import IOLoop
from Tokenizer import *
from GetRelatedWords import get_related_word
from ChatWithAi import get_ai_response
from Crawler import SimpleCrawler

tokenizer = SearchEngineTokenizerGPT2()


class DisorderedTokenizer(RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        content = eval(data.get('content', ''))

        if len(content):
            result = tokenizer.tokenize_disordered_with_word_couont_and_parse_search(content)
            self.write(json.dumps(result))
        else:
            self.set_status(400)
            self.write(json.dumps({'error': '\'content\' keyword not found.'}))


class OrderedTokenizer(RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        content = data.get('content', '')

        if content:
            result = tokenizer.tokenize_in_order(content)
            self.write(json.dumps(result))
        else:
            self.set_status(400)
            self.write(json.dumps({'error': '\'content\' keyword not found.'}))


class KeywordExpander(RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        content = data.get('content', '')

        if content:
            result = get_related_word(content, tokenizer)
            self.write(json.dumps(result))
        else:
            self.set_status(400)
            self.write(json.dumps({'error': '\'content\' keyword not found.'}))


class AIAssistant(RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        if len(data):
            result = get_ai_response(data)
            self.write(json.dumps({'role': 'assistant', 'content': result}))
        else:
            self.set_status(400)
            self.write(json.dumps({'error': 'History data not found.'}))


class CrawlerAgent(RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        start_url = data.get('start_url', '')
        max_depth = data.get('max_depth', 3)
        max_suburl = data.get('max_suburl', 100)
        try:
            max_depth = int(max_depth)
            max_suburl = int(max_suburl)
        except ValueError:
            self.set_status(400)
            self.write(json.dumps({'error': '"max_depth" and "max_suburl" parameters must be integers."'}))
        crawler = SimpleCrawler(start_url, max_depth, max_suburl)
        self.write(json.dumps(crawler.crawl()))


def make_app():
    return Application([
        (r'/disordered_tokenize', DisorderedTokenizer),
        (r'/ordered_tokenize', OrderedTokenizer),
        (r'/get_related_words', KeywordExpander),
        (r'/chat_with_AI', AIAssistant),
        (r'/crawler', CrawlerAgent)
    ])


if __name__ == "__main__":
    app = make_app()
    port = 8888
    app.listen(port)
    print(f'Tornado server is running on port {port}.')
    IOLoop.current().start()
