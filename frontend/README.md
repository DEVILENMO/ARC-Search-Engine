# ARC Frontend（Vue 2 + Element UI）

搜索引擎前端：搜索首页（含爬虫控制抽屉 + WebSocket 爬虫进度）与结果页（结果卡片、相关搜索、AI 摘要聊天面板）。

## 运行

```bash
npm install     # Node 14–16（老 webpack3 工具链；Node 18+ 需自行迁移 Vite）
npm run dev     # http://localhost:8080
```

后端地址集中在 `src/main.js`：`axios.defaults.baseURL = 'http://localhost:8899'`，WebSocket 地址由它派生。

## 结构

```
src/
├── main.js               全局配置：axios baseURL、WebSocket 地址、ElementUI
├── view/page/mainPage.vue  搜索首页 + 爬虫控制台（进度条）
├── view/page/resPage.vue   结果页：结果列表 / 相关搜索 / AI 摘要与对话
└── components/
    ├── LinkCard.vue        单条搜索结果卡片
    └── ChatBubble.vue      AI 聊天气泡
```
