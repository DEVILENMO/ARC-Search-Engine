# LLM 应用：搜索引擎里的三个落地点

后端所有 LLM 调用收敛到 `ai.py` 的一个路由函数 `chat()`，上层三个功能各自构造消息。模型通道为**双通道降级**：

```
远程通道:  OpenAI 兼容 API（LLM_BASE_URL / LLM_MODEL / LLM_API_KEY 可配）
    │ 失败（无 Key / 限流 / 断网）自动回落
本地通道:  Ollama（OLLAMA_MODEL，默认 llama2-chinese，首次调用时惰性 pull）
    │ 双双失败
    └→ LLMUnavailableError → 相关接口返回 502，搜索主流程不受影响
```

## 1. 查询扩展（召回增强）

**问题**：用户查"番茄炒蛋怎么做"，库里文档写的是"食谱/教程"，字面不匹配就召不回。

**做法**（`ai.expand_query`）：few-shot prompt 强约束输出格式，让 LLM 只输出同义词列表：

```
system:  Task: Given the user's search query, expand the keyword list by
         adding synonyms... The answer must be in the same language as the
         input. （三个中/英 few-shot 示例，要求严格按格式回答）
user:    This is the query you should deal with: User query: {query}
```

输出按 `Expanded keywords: a, b, c` 正则解析；解析失败或为空自动重试，三次失败则放弃扩展（**扩展是增益项，不能成为搜索的依赖项**）。扩展词再经 GPT-2 tokenizer 转成 token id，与原查询走同一张倒排索引。

## 2. RAG 式搜索摘要

**问题**：用户搜完还要点开多条结果自己归纳。

**做法**（`search_engine._push_summary`）：检索完成后，把 query 和 Top-5 结果的 title+snippet 拼进 prompt：

```
This is the search query given by the user: {query}. Please generate a
concise summary within 100 words based on both the query and the search
results, focusing on the key information most relevant to the user's query...
```

这是检索增强生成（RAG）的最小实现：**检索结果即上下文**，不引入额外的向量库。与标准 RAG 的差异与取舍：

- 上下文来自本轮检索的 Top-5 而非向量召回——BM25/TF-IDF 已经是相关性的来源；
- 摘要在**后台线程**生成、经 WebSocket（type 1）推送，不阻塞搜索响应——搜索引擎的延迟预算永远优先给检索。

## 3. 多轮 AI 助手（带会话记忆）

**做法**（`main.ai_chat`）：

- 以 `sessionId → 消息历史` 维护会话，存缓存（Redis 或进程内），**TTL 1 小时**防止无限增长；
- 每轮把完整历史发给 LLM；历史缺 system prompt 时自动注入人设：

```
你需要扮演ARC搜索引擎的人工智能助手弧光天星，
根据用户输入的语言和任务要求给出对应语言的反馈。
```

- 响应为纯文本，前端以气泡形式渲染。

## 工程细节

| 关注点 | 处理 |
| --- | --- |
| 密钥安全 | API Key 只从环境变量读取，仓库中只有占位符 |
| 客户端复用 | OpenAI / Ollama 客户端惰性单例化，不随请求重建 |
| 可用性 | 双通道降级；LLM 不可用时相关词/摘要静默跳过，聊天返回 502 |
| 延迟 | 所有 LLM 调用都在线程池中，绝不阻塞事件循环与检索响应 |
| 可替换 | OpenAI 兼容协议意味着可无缝换 gpt-4o、DeepSeek、Qwen 或私有 vLLM 部署 |
