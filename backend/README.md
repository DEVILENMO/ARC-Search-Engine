# ARC Backend（Python 单体后端）

FastAPI 实现的搜索引擎后端：REST + WebSocket + 索引流水线 + LLM 调度，单进程运行。

详细设计文档见仓库根目录 [docs/](../docs/)。

## 运行

```bash
# 前置：MongoDB（docker compose up -d）
pip install -r requirements.txt
python main.py            # 或 start.bat / start.sh
```

端口 8899。所有配置项见 `config.py`（环境变量注入）。

## 测试

```bash
pip install mongomock httpx
python test_integration.py
```

37 项断言，mongomock 内存数据库，不需要 MongoDB / Redis / LLM Key：
分词、Apriori 短语挖掘、PageRank、索引流水线、BM25/TF-IDF 排序、REST 路由、WebSocket、会话记忆、LLM 降级路径。
