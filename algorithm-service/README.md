# ARC Algorithm Service（Python 算法服务）

搜索引擎的"大脑"，基于 Tornado 的独立微服务（默认端口 `8888`），负责四类与语言/智能相关的核心工作：

| 能力 | 说明 |
| --- | --- |
| 子词分词 | 基于 GPT-2 BPE tokenizer，天然支持任意 UTF-8 语言，无需按语言定制分词器 |
| 短语挖掘 | Apriori 风格的逐层连词挖掘，从语料中发现高频短语（如"赛博朋克2077"），短语作为整体参与检索与加权 |
| LLM 查询扩展 | 调用 LLM 为用户查询生成同义词/相关词，提升召回 |
| LLM 摘要与对话 | 基于搜索结果的 AI 摘要（RAG 雏形）+ 带人设的多轮对话 |

## 服务接口

Java 后端是本服务的唯一调用方：

| 端点 | 方法 | 请求体 | 响应 |
| --- | --- | --- | --- |
| `/ordered_tokenize` | POST | `{"content": "some query"}` | `{"TOKEN_ID": ["257", "330", ...]}`（按顺序的 GPT-2 token id） |
| `/disordered_tokenize` | POST | `{"content": ["doc1", "doc2", ...]}` | `{tokenId: 词频, ..., "ARTICLE_ID": "最高频10词"}`（含短语挖掘） |
| `/get_related_words` | POST | `{"content": "查询词"}` | `{"扩展词": "token-ids", ...}` |
| `/chat_with_AI` | POST | `[{"role": "user", "content": "..."}]` | `{"role": "assistant", "content": "..."}` |
| `/crawler` | POST | `{"start_url": "...", "max_depth": 3, "max_suburl": 100}` | `{url: {title, content, icon, main_image, sublinks}}` |
| `/health` | GET | - | `{"status": "ok"}` |

## 配置

全部通过环境变量注入，**不要**把 API Key 提交进仓库：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LLM_API_KEY` | （空） | OpenAI 兼容 API 的密钥，**必填**（不填则只能走本地 Ollama 兜底） |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | 任何实现 `/v1/chat/completions` 的服务均可（Azure 代理、vLLM、one-api 等） |
| `LLM_MODEL` | `gpt-3.5-turbo` | 模型名 |
| `OLLAMA_MODEL` | `llama2-chinese` | 本地兜底模型（通过 [Ollama](https://ollama.com) 提供） |
| `SERVICE_PORT` | `8888` | 服务端口 |
| `CRAWLER_RESPECT_ROBOTS` | `true` | 是否遵守 robots.txt（君子协议） |
| `CRAWLER_USER_AGENT` | `ARC-Search-Engine-Crawler/1.0` | 爬虫 UA |
| `CRAWLER_TIMEOUT_SECONDS` | `10` | 单次抓取超时 |

## 运行

```bash
pip install -r requirements.txt
export LLM_API_KEY=sk-xxx        # Windows: set LLM_API_KEY=sk-xxx
python app.py
```

首次启动会从 HuggingFace 下载 GPT-2 tokenizer（约 3MB，之后走本地缓存）。

LLM 调用采用**双通道降级**设计：优先请求远程 API，失败（无 Key、限流、断网）时自动切换到 Ollama 本地模型推理。

## 模块结构

```
app.py            Tornado 服务入口与路由
config.py         环境变量配置
Tokenizer.py      GPT-2 分词 + Apriori 短语挖掘（核心算法）
GetRelatedWords.py  LLM 查询扩展
ChatWithAi.py     AI 助手（人设 + 多轮）
AIModule.py       LLM 双通道：OpenAI 兼容 API → Ollama 本地兜底
Crawler.py        BFS 爬虫实现（requests + BeautifulSoup）
BaseModule.py     抽象基类（Tokenizer / AI / Crawler 契约）
WebLoader.py      起始站点列表读取工具
```
