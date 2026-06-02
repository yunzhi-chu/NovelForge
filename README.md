<p align="center">
  <img src="https://img.shields.io/badge/NovelForge-v0.1-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.11%2B-green?style=for-the-badge" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B?style=for-the-badge" alt="Streamlit">
  <img src="https://img.shields.io/badge/LM%20Studio-Ready-8A2BE2?style=for-the-badge" alt="LM Studio">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge" alt="License">
</p>

<h1 align="center">NovelForge · 小说写作助手</h1>

<p align="center">
  <b>本地优先 · 三模型驱动 · 全流程小说创作工具</b><br>
  <sub>支持本地 LLM + DeepSeek + Claude 混合调用，离线创作不受限</sub>
</p>

<p align="center">
  <a href="#-功能一览">功能</a> ·
  <a href="#-架构设计">架构</a> ·
  <a href="#-快速开始">快速开始</a> ·
  <a href="#-模型配置">模型配置</a> ·
  <a href="#-项目结构">项目结构</a> ·
  <a href="#-开发日志">开发日志</a>
</p>

---

## 📖 简介

**NovelForge** 是一款面向中文小说作者的 AI 写作辅助工具。它采用 **本地优先、云端增强** 的策略，让你在离线环境下也能借助 AI 进行创作，同时按需接入 DeepSeek、Claude 等云端模型完成更复杂的任务。

> 你不需要为每个创意付费。NovelForge 的设计哲学是：**日常写作用本地模型，关键节点用云端模型**。

### 适用场景

- ✍️ **网文作者** — 日更高强度，本地模型保证隐私和零延迟
- 🎨 **世界观构建** — 从零搭建完整的力量体系、势力分布、历史时间线
- 📐 **大纲设计** — 结构化的章节大纲，AI 辅助生成与迭代
- 🧩 **角色管理** — 角色卡系统，含外貌、性格、背景、弧光
- 📚 **长篇小说管理** — 多项目管理，每章独立保存，衔接优化

---

## ✨ 功能一览

```
项目管理 ── 创建 / 打开 / 删除项目，自动统计章节字数
世界观设定 ── Markdown 编辑 + AI 一键生成
角色管理 ── 角色卡增删改 + AI 批量生成
大纲设计 ── 自定义章节数 + DeepSeek 一键生成
章节写作 ── AI 续写 / 生成下一章，字数自动调整
知识图谱 ── Mermaid 可视化角色关系
模型设置 ── 本地模型状态监控 + API 密钥配置
```

### 核心亮点：章节智能生成

```
┌─ 前文回顾 ─────────────────────────────┐
│  自动提取上一章结尾 500 字作为上下文     │
│  确保情节连贯，转折有过渡                 │
├─ 字数控制 ──────────────────────────────┤
│  目标字数滑块（2000-4000 字）            │
│  自动扩写 / 精简，3 轮内逼近目标         │
├─ 模型选择 ──────────────────────────────┤
│  本地 Gemma / DeepSeek / Claude 一键切换 │
│  根据任务复杂度自由选择                   │
└──────────────────────────────────────────┘
```

---

## 🏗 架构设计

```
┌─────────────────────────────────────────────────┐
│                  用户浏览器                        │
│              Streamlit Web UI (port 8501)          │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│                 app.py (路由层)                    │
│  项目管理 · 世界观 · 角色 · 大纲 · 章节 · 图谱   │
└──────┬──────────────────────────────┬───────────┘
       │                              │
┌──────▼──────────┐    ┌──────────────▼────────────┐
│  ProjectManager  │    │       LLMClient            │
│  (文件系统存储)   │    │    (多模型路由器)          │
│  projects/       │    │                            │
│  ├ metadata.json │    │  ┌──────────────────────┐  │
│  ├ world.md      │    │  │  _call_lms()         │  │
│  ├ characters.json│   │  │  ├ 本地 Gemma 4 26B  │  │
│  ├ outline.md    │    │  │  └ LM Studio CLI lms  │  │
│  ├ chapters/*.md │    │  ├ _call_openai()       │  │
│  └ exports/      │    │  │  └ DeepSeek API      │  │
└──────────────────┘    │  └ _call_claude()       │  │
                         │     └ Anthropic SDK      │  │
                         └──────────────────────────┘
```

### 三模型路由策略

| 模型 | 调用方式 | 推荐场景 | 成本 |
|------|----------|----------|------|
| **本地 (Gemma 4 26B)** | `lms.exe chat` CLI | 日常写作、章节生成、角色批量生成 | 免费（本地 GPU） |
| **DeepSeek** | OpenAI 兼容 API | 大纲设计、逻辑结构、世界观构建 | API 按量计费 |
| **Claude** | Anthropic SDK | 角色深度刻画、最终润色 | API 按量计费 |

### 为什么选择本地优先？

```
▸ 隐私保护 — 所有章节数据保存在本地，不上传云端
▸ 零成本迭代 — 日更 6000 字，API 成本为零
▸ 离线可用 — 无网络环境下正常创作
▸ 隐私 + 云智能 — 复杂任务一键切换到最强云端模型
```

---

## 🚀 快速开始

### 前置条件

- **Python 3.11+**
- **LM Studio** (推荐) — 用于本地模型推理
  - 推荐模型: `google/gemma-4-26b-a4b` (17.99 GB VRAM)
  - 下载后通过 `lms load` 加载

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/yunzhi-chu/NovelForge.git
cd NovelForge

# 2. 安装依赖
pip install streamlit openai anthropic

# 3. 启动应用
streamlit run app.py
```

浏览器打开 `http://localhost:8501` 即可使用。

### 环境变量（可选）

如需使用云端模型，设置：

```bash
export DEEPSEEK_API_KEY=sk-your-deepseek-key
export ANTHROPIC_API_KEY=sk-your-anthropic-key
```

---

## 🔧 模型配置

### 本地模型

NovelForge 通过 `lms.exe` CLI 与 LM Studio 交互，无需 HTTP API 认证：

```python
# 后台自动处理，无需手动配置
lms load "google/gemma-4-26b-a4b" --ttl 600
```

### 模型参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `temperature` | 0.78 (local) / 0.85 (章节) | 创造力控制 |
| `max_tokens` | 6000 | 最大生成长度 |
| `top_p` | 1.0 | 采样策略 |

---

## 📁 项目结构

```
NovelForge/
├── app.py                 # Streamlit 主应用（7 个页面）
├── llm_client.py          # 多模型客户端（本地 / DeepSeek / Claude）
├── project_manager.py     # 文件系统项目管理器
├── prompts/               # 提示词模板目录
├── projects/              # 项目数据（已 gitignore）
│   └── 项目名称/
│       ├── metadata.json
│       ├── world.md
│       ├── characters.json
│       ├── outline.md
│       ├── knowledge_graph.json
│       ├── chapters/
│       │   ├── 1.md
│       │   ├── 2.md
│       │   └── ...
│       └── exports/
├── .gitignore
├── 开发日志.md             # 完整开发手册 v1.3
└── README.md              # 本文件
```

---

## 🧪 测试

项目自带测试作品"测试作品"（5 章，约 1 万字），安装后直接在项目管理页打开即可查看。

```bash
# 手动生成测试章节（需 LM Studio 运行本地模型）
python app.py  # 然后通过 UI 操作
```

---

## 🗺 路线图

- [x] 项目管理（创建 / 打开 / 删除）
- [x] 世界观设定（编辑 + AI 生成）
- [x] 角色管理（角色卡 + 批量生成）
- [x] 大纲设计（自定义 + AI 生成）
- [x] 章节写作（AI 生成 + 字数控制 + 上下文衔接）
- [x] 知识图谱（Mermaid 可视化）
- [ ] 导出功能（ZIP / EPUB / TXT）
- [ ] 章节版本历史
- [ ] 多语言支持
- [ ] 插件系统（自定义提示词模板）

---

## 🤝 贡献

欢迎提交 Issue 和 PR！如果你有好的想法或发现了 bug，请先开 issue 讨论。

---

## 📄 License

MIT License © 2026 yunzhi-chu

---

<p align="center">
  <b>如果这个项目对你有帮助，请给它一个 ⭐️</b><br>
  <sub>你的 star 是开发者最大的动力</sub>
</p>
