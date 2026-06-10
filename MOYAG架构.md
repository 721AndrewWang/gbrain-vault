# MOYAG 架构
MOYAG 是一个多 Agent 视觉营销资产生成系统。

## 核心组件
- [[Hermes Agent]] 负责任务编排
- [[Claude Code]] 负责代码生成
- [[GBrain]] 负责语义记忆
- [[Obsidian KB]] 负责知识存储

## 工作流
1. 用户输入 Brief
2. Hermes 拆解任务
3. Claude Code 生成代码
4. 结果存入 Obsidian
