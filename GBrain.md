# GBrain

GBrain 是MOYAG架构的语义记忆引擎，负责向量搜索和图谱遍历。

## 核心能力
- **向量搜索**: 基于Chroma的语义检索
- **关键词搜索**: 全文grep回退
- **图谱遍历**: WikiLink双向链接图
- **自动索引**: Cron Job每30分钟同步

## MCP工具 (11个)
1. `gbrain_search` — 语义搜索
2. `gbrain_keyword` — 关键词搜索
3. `gbrain_traverse` — 图谱遍历
4. `gbrain_index` — 索引管理
5. `gbrain_backlinks` — 反向链接
6. `gbrain_stats` — 统计信息
7. `gbrain_recent` — 最近修改
8. `gbrain_orphans` — 孤立笔记
9. `gbrain_content` — 读取全文
10. `gbrain_links` — 出链列表
11. `gbrain_broken_links` — 断链检测

## 关联
- 通过 [[Hermes Agent]] MCP协议暴露工具
- 被 [[Claude Code]] 查询知识
- 数据存储在 [[Obsidian KB]]

## 技术栈
- Chroma (向量数据库)
- MCP Protocol (stdio传输)
- Python 3.11+

---

*路径: `C:/Users/EDY/Documents/GBrain Vault/`*
