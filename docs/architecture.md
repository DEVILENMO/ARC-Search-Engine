# 架构与数据模型

## 组件拓扑

单进程 Python 后端（FastAPI / uvicorn，端口 8899）承载全部服务端逻辑；MongoDB 为唯一必需的存储依赖，Redis 可选。

```mermaid
flowchart TB
    subgraph Client
        FE["Vue 前端 (:8080)"]
    end
    subgraph Server["FastAPI 进程 (:8899)"]
        direction TB
        REST["REST 路由层<br/>POST /search/get · /AIChat/getReply · /PageLink/Parse"]
        WSH["WS /websocket<br/>广播器 ConnectionManager"]
        POOL["ThreadPoolExecutor<br/>爬虫任务 · LLM 异步任务"]
        SE["SearchEngine<br/>检索 → 打分 → 重排"]
        IDX["Indexer<br/>爬取结果 → 倒排/正排/短语/链接图"]
        PR["pagerank.py<br/>幂迭代"]
        TK["SearchEngineTokenizer<br/>GPT-2 BPE + Apriori 短语"]
        AIM["ai.py<br/>OpenAI ⇄ Ollama 双通道"]
    end
    MG[("MongoDB")]
    RD[("Redis (可选)")]

    FE -->|JSON| REST
    FE <-->|type 0/1/2 推送| WSH
    REST --> SE
    REST --> IDX
    IDX --> POOL
    SE --> TK
    IDX --> TK
    SE --> AIM
    IDX --> PR
    SE --> MG
    IDX --> MG
    PR --> MG
    SE -.-> RD
```

## 数据模型（MongoDB 集合）

历史版本沿用下来的六张表。倒排表的 key 约定：token id 为十进制字符串，**短语**（连词）用 `-` 连接各 token id（如 `"233-164-113"`）；URL 在倒排表内以 `$` 代替 `.` 存储（规避 MongoDB 旧版字段名限制）。

| 集合 | 类型 | Schema | 说明 |
| --- | --- | --- | --- |
| `title_index` | 倒排 | `{_id: tokenId, indexMap: {url$: {url, tf}}}` | 标题词 → 文档列表 |
| `content_index` | 倒排 | 同上 | 正文词 → 文档列表 |
| `stem_df` | 统计 | `{_id: tokenId, df}` | 文档频率，IDF 计算输入 |
| `phrases` | 统计 | `{_id: phraseId, df}` | 短语表，查询侧短语识别的字典 |
| `forward_index` | 正排 | `{url, title, content, title_tf, content_tf, icon, img, articleId, childrenLink[], parentLink[], pagerank}` | 摘要/展示/链接图来源 |
| `doc_stats` | 统计 | `{url, title_len, content_len}` | BM25 的文档长度与平均长度 |

## 搜索时序

```mermaid
sequenceDiagram
    participant U as 浏览器
    participant A as FastAPI /search/get
    participant S as SearchEngine
    participant M as MongoDB
    participant L as LLM (异步线程)
    participant W as WebSocket 广播

    U->>A: POST {keywords}
    A->>S: search(keywords)
    S->>S: 预处理 + GPT-2 有序分词
    S->>M: 查 phrases 表 → 识别查询中的短语
    S->>M: 查 title/content 倒排表 → 候选文档
    S->>M: DF 表(缓存) + 语料规模(缓存)
    S->>S: BM25 或 TF-IDF+余弦 打分
    S->>M: 取候选文档 pagerank
    S->>S: final = score × (1 + w × pr)，取 Top N
    S->>M: 正排表取摘要/链接/词频 → 结果 DTO
    S--)L: 查询扩展 + Top5 摘要（不阻塞响应）
    A-->>U: {results, keywordsTokenId}（立即返回）
    L--)W: type 0 相关词 / type 1 AI 摘要
    W--)U: 实时推送渲染
```

关键设计：

- **LLM 调用不阻塞搜索响应**。相关词与摘要在线程池中执行，经 WebSocket 异步推送（前端在结果页独立渲染这两个区域）。
- **DF 表与短语表整表缓存**，只在索引变更时失效。原 Java 实现每次搜索全表扫描 `stem_df`，是明显的性能热点。

## 爬虫与索引时序

```mermaid
sequenceDiagram
    participant U as 浏览器
    participant A as /PageLink/Parse
    participant I as Indexer (线程池)
    participant C as SimpleCrawler
    participant M as MongoDB
    participant W as WebSocket

    U->>A: POST {urls: "url1 20, url2 50"}
    A->>I: 每个起始站点提交一个任务
    I->>C: BFS 抓取（robots.txt 检查 → 抓取 → 解析标题/正文/图标/外链）
    C-->>I: {url: {title, content, icon, img, sublinks}}
    loop 每个页面
        I->>I: 正文分词（Apriori 短语挖掘）→ content_index
        I->>I: 标题分词（短语识别）→ title_index
        I->>M: upsert 倒排表 + DF 表 + 正排表 + doc_stats
        I--)W: type 2 进度 {taskNum, finishNum, startUrl}
    end
    I->>M: 汇总短语表 → 反转父子链接 → PageRank 幂迭代
    I->>M: 存储 pagerank（相对最大值归一化）+ 失效语料缓存
```

## 与课程原版的差异

| 维度 | 原版 | 现在 |
| --- | --- | --- |
| 后端 | Java Spring Boot + Python Tornado 双服务 | Python 单进程 |
| 排序 | TF-IDF + 余弦 | BM25（默认）/ TF-IDF 可切换，均叠加 PageRank |
| 链接分析 | 仅存链接图，不参与排序 | PageRank 幂迭代参与排序 |
| DF/短语查询 | 每次搜索全表扫描 | 整表缓存 + 索引变更时失效 |
| 内部调用 | Java → Tornado HTTP | 同进程函数调用 |
| 配置 | 外部地址硬编码在代码里 | 全部环境变量 |
| 会话记忆 | Redis 无过期 | 缓存 + TTL |
| 已修复 bug | `updateParent` 写错父链接 + NPE；排序分数错位；`eval()` RCE；爬虫无超时；爬虫进度/搜索无隔离 | 全部修复 |
