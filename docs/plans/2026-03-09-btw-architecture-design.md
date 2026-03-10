# BTW (Book To Web) — 架构设计文档

> 将书籍转化为沉浸式交互 Web 应用的 Multi-Agent 系统

## 1. 项目愿景

BTW 将任意书籍（小说、教材、历史、科技...）转化为可交互的 Web 体验：
- 参数化公式与可操作图表
- 滚动驱动的动态叙事
- 可执行代码沙盒
- 人物关系图谱与角色对话
- What-If 剧情分支（未来）

## 2. 核心设计理念

### 2.1 全 Agent 化

整个系统是一个 Multi-Agent 系统，而非传统的固定管线。每个 Agent 有独立的职责、system prompt 和可用工具集。随着 AI 模型能力增强，Agent 自动变强，无需改架构。

### 2.2 AI 直出代码（方案 B）

AI 直接为每个章节生成完整的 React 组件代码，而非从预定义组件库中拣选。最大灵活性，未来模型越强，生成的组件越丰富。

### 2.3 前后端彻底分离

- 前端：纯 React SPA (Vite)
- 后端：Python (FastAPI)
- 通信：REST API + WebSocket

### 2.4 多模型抽象层

支持 Claude / OpenAI / Ollama 等多种模型接入，适配器模式统一接口。

### 2.5 Agent 体系可扩展

Agent 注册机制保持开放，可随时新增 Agent 而不影响已有架构。

## 3. 系统全景

```
┌─────────────────────────────────────────────────────────────────┐
│                      BTW Multi-Agent System                      │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │                 Director (总指挥)                        │     │
│  │        接收请求 → 分配任务 → 协调全局 → 监控状态         │     │
│  └─────────────────────────┬───────────────────────────────┘     │
│                            │                                      │
│  ┌─────────────────────────▼───────────────────────────────┐     │
│  │                     Agent 层 (17+)                       │     │
│  │                                                          │     │
│  │  输入层:   Parser, Guardian                              │     │
│  │  理解层:   Reader, Retriever                             │     │
│  │  规划层:   Planner, Stylist                              │     │
│  │  生成层:   Creator, Illustrator, Engineer, Critic        │     │
│  │  适配层:   Translator                                    │     │
│  │  前端层:   Conductor, Companion, Persona                 │     │
│  │  进化层:   Evolver, Curator                              │     │
│  │  (持续扩展中...)                                         │     │
│  └─────────────────────────┬───────────────────────────────┘     │
│                            │                                      │
│  ┌─────────────────────────▼───────────────────────────────┐     │
│  │                  Skills 共享工具层                        │     │
│  └─────────────────────────┬───────────────────────────────┘     │
│                            │                                      │
│  ┌─────────────────────────▼───────────────────────────────┐     │
│  │                  Storage 共享存储层                       │     │
│  │            SQLite + ChromaDB + 文件系统                   │     │
│  └─────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
```

## 4. Agent 详细定义

> 以下为当前已定义的 17 个 Agent。系统设计为可扩展，未来可随时新增。

### 4.1 全局层

#### Director（总指挥）

| 属性 | 说明 |
|---|---|
| 职责 | 接收所有外部请求，拆解任务，分配给对应 Agent，监控状态，处理失败和重试 |
| 输入 | 用户请求（API 调用、用户操作） |
| 输出 | 任务分配指令 |
| 调用 | 所有其他 Agent |
| 原则 | 不做具体工作，只做调度和协调 |

### 4.2 输入层

#### Parser（解析器）

| 属性 | 说明 |
|---|---|
| 职责 | 处理各种输入格式的解析和清洗，输出干净的结构化文本 |
| 输入 | 原始文件（PDF / EPUB / 扫描件 / 纯文本 / Markdown / URL） |
| 输出 | 干净的结构化文本（分章分段） |
| 调用 | Skills: file_parse, ocr_extract |
| MVP 范围 | 先支持纯文本 / Markdown，后续扩展 PDF / EPUB |

#### Guardian（守护者）

| 属性 | 说明 |
|---|---|
| 职责 | 系统级安全和异常处理。监控所有 Agent 运行状态，检测异常，用户输入内容安全审查 |
| 输入 | 所有 Agent 的运行日志、用户上传内容 |
| 输出 | 安全审查结果、异常告警、拦截指令 |
| 调用 | Skills: content_filter, resource_monitor |
| 与 Engineer 的区别 | Engineer 关注代码质量，Guardian 关注系统级安全和资源保护 |

### 4.3 理解层

#### Reader（理解者）

| 属性 | 说明 |
|---|---|
| 职责 | 深度阅读书籍，生成分层摘要链、段落标注、概念图谱 |
| 输入 | Parser 输出的结构化文本 |
| 输出 | 全书摘要、章节摘要、段落标注（类型/实体/概念）、概念索引 |
| 调用 | Skills: llm_call, entity_extract, formula_extract |
| 策略 | 自主决定分析深度（简单小册子 vs 厚教材策略不同） |

**Reader 的分层摘要链：**

```
第1遍：结构解析
  全书文本 → 分章分段 → 每段标记位置ID (ch3.p2)

第2遍：分层摘要（自底向上）
  每段 → AI标注: 类型(概念/公式/叙事/代码/数据) + 核心实体 + contextual前缀
  每章 → AI生成: 章节摘要(~200字) + 关键概念列表
  全书 → AI生成: 全书摘要(~500字) + 全书概念图谱

第3遍：概念索引构建
  AI提取语义概念 + 规则提取硬实体(公式/人名/年份)
  → 合并为倒排索引
```

#### Retriever（检索者）

| 属性 | 说明 |
|---|---|
| 职责 | 为其他 Agent 按需提供书籍上下文。自主决定检索策略 |
| 输入 | 上下文查询请求（来自其他 Agent） |
| 输出 | 组装好的、相关的上下文片段 |
| 调用 | Skills: concept_search, semantic_search, cross_reference |
| 策略 | 自主决定用精确匹配、语义检索、还是混合策略 |

**Retriever 可用的检索手段：**

| 手段 | 实现 | 适用场景 |
|---|---|---|
| 概念精确检索 | SQLite 倒排索引 | "找所有提到'供需曲线'的段落" |
| 语义检索 | ChromaDB 向量库 | "找与'市场自调节'语义相关的内容" |
| 跨章引用 | 概念索引 + 段落关联 | "这个概念在哪些章节被引用过" |
| 全书概览 | 摘要链直接读取 | "这本书整体在讲什么" |

### 4.4 规划层

#### Planner（规划师）

| 属性 | 说明 |
|---|---|
| 职责 | 为整本书设计交互策略蓝图。决定每章用什么交互范式、整体叙事节奏 |
| 输入 | Reader 的分析结果（摘要链 + 概念图谱） |
| 输出 | 全书交互策略蓝图 JSON |
| 调用 | Retriever, Skills: llm_call |
| 示例输出 | "第1-3章:渐进引导, 第4-6章:沙盒实验, 第7-12章:案例对比" |

#### Stylist（风格师）

| 属性 | 说明 |
|---|---|
| 职责 | 维护全书视觉风格、交互范式的一致性。为 Creator 提供风格约束 |
| 输入 | Planner 的蓝图 + 书籍类型/主题 |
| 输出 | 视觉/交互规范（色调、字体、图表风格、动画节制度、交互模式） |
| 调用 | Skills: llm_call |
| 意义 | 确保第1章和第12章看起来是同一本书的 |

### 4.5 生成层

#### Creator（创造者）

| 属性 | 说明 |
|---|---|
| 职责 | 根据蓝图和风格约束，为每个章节生成完整的 React 交互组件代码 |
| 输入 | 章节内容 + Retriever 提供的上下文 + Planner 蓝图 + Stylist 规范 |
| 输出 | React 组件代码（JSX） |
| 调用 | Retriever, Skills: llm_call |
| 关键约束 | 输出严格的 `export default function Component(props)` 格式，只用白名单依赖 |

**Creator 的 Prompt 策略：**
- 角色约束：资深前端工程师
- 可用库白名单：React, ECharts, D3, KaTeX, Framer Motion, Monaco Editor
- 输出格式锁定：标准 React 函数组件
- 分类 prompt 模板：不同内容类型各有优化模板

#### Illustrator（插画师）

| 属性 | 说明 |
|---|---|
| 职责 | 为章节生成配图、背景视觉、氛围图 |
| 输入 | 章节内容 + Stylist 视觉规范 |
| 输出 | 图片资源（PNG/SVG） |
| 调用 | Skills: image_generate (DALL-E / Midjourney API 等) |
| 与 Creator 的区别 | Creator 生成交互代码，Illustrator 生成静态视觉资产 |

#### Engineer（工程师）

| 属性 | 说明 |
|---|---|
| 职责 | 代码安检、编译、依赖注入、性能检查 |
| 输入 | Creator 生成的原始 JSX 代码 |
| 输出 | 编译后的安全可执行 JS bundle |
| 调用 | Skills: code_validate, code_compile, ast_analyze |
| 失败处理 | 不自己修代码，反馈给 Creator 重新生成 |

**双端编译策略：**
- 后端编译（默认）：Python 调用 esbuild CLI → 返回编译后 bundle
- 前端编译（备选）：返回原始 JSX → 前端用 Babel standalone 浏览器端编译

**安检流程：**
- Python ast 模块做 AST 静态分析
- 检测危险调用：eval, fetch, document.cookie, localStorage 等
- 白名单机制：只允许声明的依赖

#### Critic（评审官）

| 属性 | 说明 |
|---|---|
| 职责 | 独立评判组件质量，收集用户反馈，驱动 Creator 迭代改进 |
| 输入 | 组件代码 + 原始章节内容 + 用户反馈 |
| 输出 | 质量评分 + 具体修改建议 |
| 调用 | Skills: llm_call |
| 闭环 | 不满意 → 反馈给 Creator 附修改建议 → 重新生成 → 再评审 |

### 4.6 适配层

#### Translator（翻译官）

| 属性 | 说明 |
|---|---|
| 职责 | 多语言适配 + 无障碍支持 |
| 输入 | 任意 Agent 的输出 + 目标语言/无障碍需求 |
| 输出 | 适配后的内容 |
| 调用 | Skills: llm_call, aria_generate |
| 范围 | 不是简单翻译——让所有 Agent 输出适配目标语言，为视障用户生成音频描述，添加 ARIA 标签 |

### 4.7 前端层

#### Conductor（前端指挥）

| 属性 | 说明 |
|---|---|
| 职责 | 编排所有章节组件的联动关系、页面过渡动画、全局状态协调 |
| 输入 | 所有章节的组件列表 + Planner 蓝图 |
| 输出 | 联动规则 + 过渡配置 JSON |
| 调用 | Skills: llm_call |
| 示例 | "ch3的图表滚动到视口时, 侧栏概念图高亮'供需'节点" |

#### Companion（伴读者）

| 属性 | 说明 |
|---|---|
| 职责 | 前端侧，以第三人称客观视角与用户实时交互。解释概念、回答问题、触发新组件生成 |
| 输入 | 用户的实时交互（问题、点击、请求） |
| 输出 | 回答 / 解释 / 新生成的组件 |
| 调用 | Retriever, Creator |
| 通信 | WebSocket 实时双向通信 |

#### Persona（角色扮演者）

| 属性 | 说明 |
|---|---|
| 职责 | 扮演书中任意人物，以第一人称角色视角与用户对话 |
| 输入 | 用户指定的角色 + 对话内容 |
| 输出 | 角色口吻的回复 |
| 调用 | Retriever, Skills: llm_call |
| 与 Companion 的区别 | Companion 是客观导读者，Persona 是角色本人 |

**Persona 的特殊能力：**

| 能力 | 说明 |
|---|---|
| 人物建模 | 从全书提取角色性格、说话风格、价值观、经历 |
| 口吻模拟 | 用角色的语气、用词习惯、思维方式对话 |
| 知识边界 | 只知道角色在当前时间点应该知道的事（不剧透） |
| 立场一致 | 从角色立场出发，而非上帝视角 |
| 多角色切换 | 用户可随时切换和不同角色对话 |
| 跨角色对话 | 两个 Persona 实例可互相对话，用户旁观 |

**适用范围（不止小说）：**

| 书籍类型 | Persona 可扮演 |
|---|---|
| 小说 | 书中人物（诸葛亮、曹操...） |
| 经济学 | 经济学家（亚当·斯密、凯恩斯...） |
| 历史 | 历史人物、作者本人 |
| 物理学 | 科学家（牛顿、爱因斯坦、费曼...） |
| 编程书 | 语言创造者（Guido van Rossum...） |

### 4.8 进化层

#### Evolver（进化者）

| 属性 | 说明 |
|---|---|
| 职责 | 跨书籍、跨用户的长期学习。持续优化 prompt 模板、组件策略、质量标准 |
| 输入 | 全流程日志 + Critic 的评审记录 + 用户反馈 |
| 输出 | 优化后的 prompt 模板 / 策略配置 |
| 调用 | Skills: llm_call, db_write |
| 意义 | 系统的"经验沉淀"——处理物理教材的经验帮助处理化学教材 |

#### Curator（策展人）

| 属性 | 说明 |
|---|---|
| 职责 | 用户个人知识管理。阅读报告、跨书籍知识图谱整合、推荐 |
| 输入 | 用户的阅读行为数据 + 所有已处理书籍的概念图谱 |
| 输出 | 阅读报告 / 推荐 / 个人知识图谱 |
| 调用 | Retriever, Skills: llm_call, db_read |

## 5. Agent 间协作流

### 5.1 一本书的完整旅程

```
用户上传《经济学原理》.pdf
│
▼ Director 接收，启动流水线
│
▼ ① Guardian: 内容安全审查 → 通过
│
▼ ② Parser: PDF → 干净的结构化文本（12章）
│
▼ ③ Reader: 深度阅读
│    → 分层摘要链（全书摘要 + 12个章节摘要）
│    → 段落标注（每段带 contextual 前缀 + 类型 + 实体）
│    → 概念索引（47个核心概念的倒排索引）
│    → 向量化存入 ChromaDB
│
▼ ④ Planner: 设计交互蓝图
│    "第1-3章:渐进引导, 第4-6章:沙盒实验, 第7-12章:案例对比"
│
▼ ⑤ Stylist: 确定视觉体系
│    "色调:学术蓝, 图表:ECharts简洁风, 动画:克制, 交互:滑块为主"
│
▼ ⑥ Creator (逐章, 可并行):
│    ← 向 Retriever 要上下文（Retriever 自主决定检索策略）
│    ← 遵循 Planner 蓝图 + Stylist 规范
│    → 生成 React 组件 JSX
│
▼ ⑦ Illustrator (与 Creator 并行):
│    → 为需要配图的章节生成视觉资产
│
▼ ⑧ Engineer: 安检 + 编译
│    × 不通过 → 反馈给 Creator 重生成
│    ✓ 通过 → 输出 bundle
│
▼ ⑨ Critic: 评审质量
│    × 不满意 → 反馈给 Creator (附修改建议)
│    ✓ 满意 → 放行
│
▼ ⑩ Translator (如需): 适配目标语言 + 无障碍标签
│
▼ ⑪ Conductor: 编排组件联动规则
│    "ch3的图表滚动到视口时, 侧栏概念图高亮'供需'节点"
│
▼ ⑫ 前端渲染 → 用户开始阅读
│
▼ ⑬ Companion + Persona: 实时响应用户交互
│    用户问 "解释这个概念" → Companion 回答
│    用户问 "亚当·斯密你怎么看" → Persona 角色扮演
│
▼ ⑭ Curator: 记录阅读轨迹，更新个人知识图谱
│
▼ ⑮ Evolver: 收集本次经验，优化下次处理
```

### 5.2 Agent 通信机制

Agent 间通过 Director 协调，不直接互调（解耦）：

```
Creator 需要上下文:
  Creator → Director: "我需要第3章的上下文"
  Director → Retriever: "为 Creator 提供 ch3 上下文"
  Retriever → Director: {context_data}
  Director → Creator: {context_data}
```

例外：Retriever 作为公共服务，可被其他 Agent 直接调用（减少延迟）。

## 6. 存储层设计

### 6.1 AI 理解策略：分层摘要链 + Contextual Retrieval + 概念索引

核心原则：**不是我们替 AI 做检索决策，而是给 AI 留足自主查询的能力。** 存储层提供全面的查询接口，让 Agent（尤其是 Retriever）自己决定怎么查。

### 6.2 存储结构：SQLite + ChromaDB + 文件系统

```
data/books/{book-id}/
├── raw.txt                          # 原始文件
├── meta.json                        # 元信息
├── book_summary.md                  # 全书摘要 (AI生成, ~500字)
├── concept_index.json               # 全书概念倒排索引
├── vectors.db                       # ChromaDB 本地向量库
│
├── chapters/
│   ├── 01/
│   │   ├── content.md               # 章节原文
│   │   ├── summary.md               # 章节摘要 (AI生成, ~200字)
│   │   ├── paragraphs.json          # 段落列表 + 标注 + contextual前缀
│   │   ├── component.jsx            # AI生成的交互组件源码
│   │   └── component.js             # 编译后的 bundle
│   ├── 02/
│   │   └── ...
```

**段落存储格式（带 Contextual Retrieval 前缀）：**

```json
{
  "id": "ch3.p2",
  "context": "本段来自《经济学原理》第3章'供给与需求'，前文刚介绍了需求曲线的定义，本段开始推导供给曲线与需求曲线的交点如何决定市场均衡价格",
  "text": "当供给量等于需求量时，市场达到均衡状态...",
  "type": "formula",
  "entities": ["均衡价格", "供给量", "需求量"],
  "concepts": ["市场均衡", "供需曲线"]
}
```

**SQLite 表结构：**

```sql
books(id, title, author, upload_time, file_path, status)
chapters(id, book_id, index, title, type_tag, summary_path)
paragraphs(id, chapter_id, index, type, text, context, entities_json, concepts_json)
concepts(id, book_id, name, paragraph_ids_json)
ai_cache(id, prompt_hash, model, result, created_at)
agent_logs(id, agent_name, task_id, input_summary, output_summary, status, created_at)
```

## 7. 技术栈

| 层 | 技术 |
|---|---|
| **前端** | Vite + React 18 + Tailwind CSS |
| 图表 | ECharts + KaTeX (数学公式) |
| 代码沙盒 | Monaco Editor + Pyodide (浏览器端 Python) |
| 动画 | Framer Motion + Intersection Observer |
| 前端编译 | Babel standalone (浏览器端 JSX → JS) |
| **后端** | Python 3.12 + FastAPI + Uvicorn |
| AI 抽象层 | 自建适配器 (anthropic / openai / ollama Python SDK) |
| 后端编译 | esbuild CLI (subprocess 调用) |
| 代码安检 | Python ast 模块 + 自定义白名单规则 |
| 结构化存储 | SQLite |
| 向量存储 | ChromaDB |
| 文件存储 | 本地文件系统 |
| 实时通信 | WebSocket (Companion / Persona) |

## 8. 项目目录结构

```
btw/
├── agents/                          # Agent 层
│   ├── base.py                      # Agent 基类 / 注册机制
│   ├── director.py                  # 总指挥
│   ├── parser.py                    # 解析器
│   ├── guardian.py                  # 守护者
│   ├── reader.py                    # 理解者
│   ├── retriever.py                 # 检索者
│   ├── planner.py                   # 规划师
│   ├── stylist.py                   # 风格师
│   ├── creator.py                   # 创造者
│   ├── illustrator.py               # 插画师
│   ├── engineer.py                  # 工程师
│   ├── critic.py                    # 评审官
│   ├── translator.py                # 翻译官
│   ├── conductor.py                 # 前端指挥
│   ├── companion.py                 # 伴读者
│   ├── persona.py                   # 角色扮演者
│   ├── evolver.py                   # 进化者
│   └── curator.py                   # 策展人
│
├── skills/                          # Skills 共享工具层
│   ├── base.py                      # Skill 基类 / 注册器
│   ├── book_read.py
│   ├── concept_search.py
│   ├── semantic_search.py
│   ├── cross_reference.py
│   ├── content_classify.py
│   ├── formula_extract.py
│   ├── entity_extract.py
│   ├── code_validate.py
│   ├── code_compile.py
│   ├── image_generate.py
│   ├── content_filter.py
│   ├── resource_monitor.py
│   ├── aria_generate.py
│   └── llm_call.py
│
├── models/                          # 多模型抽象层
│   ├── base.py                      # 统一接口
│   ├── claude_adapter.py
│   ├── openai_adapter.py
│   └── ollama_adapter.py
│
├── storage/                         # 存储层
│   ├── book_store.py                # 书籍文件管理
│   ├── db.py                        # SQLite
│   └── vector_store.py              # ChromaDB
│
├── api/                             # FastAPI 路由
│   ├── routes.py                    # REST API
│   └── websocket.py                 # WebSocket (Companion / Persona)
│
├── frontend/                        # 前端 (Vite + React)
│   ├── src/
│   │   ├── agents/
│   │   │   ├── companion.ts         # Companion 前端部分
│   │   │   ├── persona.ts           # Persona 前端部分
│   │   │   └── conductor.ts         # Conductor 前端部分
│   │   ├── components/              # UI 组件
│   │   ├── renderer/                # 动态组件渲染器
│   │   │   ├── DynamicLoader.tsx    # 动态加载 AI 生成的组件
│   │   │   └── BabelCompiler.ts     # 前端 JSX 编译
│   │   └── ...
│   └── ...
│
├── data/                            # 数据存储
│   ├── btw.db                       # SQLite 数据库
│   └── books/                       # 书籍文件
│
└── config/                          # 配置
    ├── prompts/                     # Agent system prompts
    └── settings.yaml                # 全局配置
```

## 9. MVP 范围

| 做 | 不做（后续迭代） |
|---|---|
| 纯文本 / Markdown 上传 | PDF / EPUB / 扫描件 |
| 4种交互：图表、公式、代码沙盒、滚动叙事 | 3D 场景、地图、What-If 分支 |
| 17 个 Agent 基础框架 | Agent 间复杂协商 |
| 单用户本地体验 | 多用户、协作、分享 |
| 服务端安检 + 直注入 | iframe 沙盒隔离 |
| 3 个 AI 适配器 (Claude/OpenAI/Ollama) | 模型自动选择 / fallback |
| Companion + Persona 基础对话 | 多角色同时对话、跨书对话 |
| SQLite + ChromaDB | PostgreSQL / 云存储 |

## 10. 面向未来的扩展性

### 10.1 模型增强时

| 现在 (MVP) | 未来 (模型增强后) |
|---|---|
| Reader 按固定步骤分析 | Reader 自主决定分析深度和策略 |
| Creator 生成基础交互组件 | Creator 自由创造全新交互形式 |
| Retriever 用索引+向量双路 | Retriever 多跳推理检索 |
| Companion 回答简单问题 | Companion 支持 What-If 分支、POV 切换 |
| Persona 基础角色扮演 | Persona 深度人物模拟、跨角色对话 |
| Planner 从几种模板选择 | Planner 为每本书创造独特的叙事策略 |

### 10.2 新增 Agent

系统保持开放，随时可新增 Agent。只需：
1. 继承 Agent 基类
2. 定义 system prompt + 可用 skills
3. 在 Director 中注册
4. 无需修改其他 Agent

---

*文档版本: v0.1 — 初始设计*
*日期: 2026-03-09*
*状态: 设计讨论中，Agent 体系持续扩展*
