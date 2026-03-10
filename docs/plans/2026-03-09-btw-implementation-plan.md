# BTW Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 用最短链路打通"上传书籍 → AI解析 → 生成交互组件 → 前端渲染"全流程，所有17个Agent骨架可独立运行

**Architecture:** Python后端(FastAPI) + React前端(Vite)，17个Agent独立进程/模块，通过Director协调，SQLite+ChromaDB+文件系统存储

**Tech Stack:** Python 3.12 + FastAPI + React 18 + Vite + Tailwind + ECharts + ChromaDB + SQLite

**Strategy:** 方案A纵向穿透 - 先搭骨架跑通全流程，再横向增强各Agent

---

## Phase 0: 项目基础设施（骨架层）

### Task 0.1: 创建项目目录结构

**Files:**
- Create: `btw/README.md`
- Create: `btw/pyproject.toml`
- Create: `btw/.gitignore`
- Create: `btw/agents/` (空目录)
- Create: `btw/skills/` (空目录)
- Create: `btw/models/` (空目录)
- Create: `btw/storage/` (空目录)
- Create: `btw/api/` (空目录)
- Create: `btw/data/` (空目录，.gitignore)
- Create: `btw/config/` (空目录)
- Create: `btw/frontend/` (空目录)

**Step 1: 创建 Python 项目配置**

```toml
# pyproject.toml
[project]
name = "btw"
version = "0.1.0"
description = "Book To Web - Multi-Agent System"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.6.0",
    "python-multipart>=0.0.9",
    "aiofiles>=23.2.1",
    "anthropic>=0.18.0",
    "openai>=1.12.0",
    "chromadb>=0.4.22",
    "numpy>=1.26.0",
    "tiktoken>=0.6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-asyncio>=0.23.0", "ruff>=0.2.0", "mypy>=1.8.0"]
```

**Step 2: 创建 .gitignore**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/
.venv/
venv/

# Data
data/books/*
!data/books/.gitkeep
data/*.db
!data/.gitkeep

# IDE
.vscode/
.idea/
*.swp
*.swo

# Frontend
frontend/node_modules/
frontend/dist/
frontend/.env.local
```

**Step 3: 初始化目录**

```bash
cd btw
mkdir -p agents skills models storage api config data/books
mkdir -p frontend/src/agents frontend/src/components frontend/src/renderer
touch data/.gitkeep data/books/.gitkeep
```

**Step 4: Commit**

```bash
git add .
git commit -m "chore: initialize BTW project structure"
```

---

### Task 0.2: 创建 Agent 基类与注册机制

**Files:**
- Create: `btw/agents/base.py`
- Test: `btw/tests/agents/test_base.py`

**Step 1: 写失败测试**

```python
# tests/agents/test_base.py
import pytest
from agents.base import Agent, AgentRegistry

class TestAgent(Agent):
    name = "test_agent"

    async def process(self, input_data: dict) -> dict:
        return {"result": "test", "input": input_data}

def test_agent_registry():
    registry = AgentRegistry()
    registry.register(TestAgent)

    assert "test_agent" in registry.agents
    agent_class = registry.get("test_agent")
    assert agent_class == TestAgent

def test_agent_instance_creation():
    registry = AgentRegistry()
    registry.register(TestAgent)

    agent = registry.create("test_agent", config={"key": "value"})
    assert isinstance(agent, TestAgent)
    assert agent.config == {"key": "value"}

@pytest.mark.asyncio
async def test_agent_process():
    agent = TestAgent(config={})
    result = await agent.process({"test": "data"})
    assert result["result"] == "test"
    assert result["input"]["test"] == "data"
```

**Step 2: 运行测试，确认失败**

```bash
cd btw
pytest tests/agents/test_base.py -v
# Expected: 3 FAIL (Agent, AgentRegistry not defined)
```

**Step 3: 实现基类**

```python
# agents/base.py
from abc import ABC, abstractmethod
from typing import Any, Type
from dataclasses import dataclass
import asyncio


@dataclass
class AgentContext:
    """Agent执行上下文"""
    task_id: str
    book_id: str | None = None
    chapter_id: str | None = None
    retry_count: int = 0


class Agent(ABC):
    """所有Agent的基类"""

    name: str = "base_agent"
    description: str = "Base agent class"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.context: AgentContext | None = None

    def set_context(self, context: AgentContext) -> None:
        """设置执行上下文"""
        self.context = context

    @abstractmethod
    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """处理输入，返回输出"""
        pass

    async def on_error(self, error: Exception, input_data: dict) -> dict:
        """错误处理，子类可覆盖"""
        raise error


class AgentRegistry:
    """Agent注册表 - 管理所有Agent"""

    def __init__(self):
        self.agents: dict[str, Type[Agent]] = {}

    def register(self, agent_class: Type[Agent]) -> None:
        """注册一个Agent类"""
        self.agents[agent_class.name] = agent_class

    def get(self, name: str) -> Type[Agent]:
        """获取Agent类"""
        if name not in self.agents:
            raise KeyError(f"Agent '{name}' not registered")
        return self.agents[name]

    def create(self, name: str, config: dict | None = None) -> Agent:
        """创建Agent实例"""
        agent_class = self.get(name)
        return agent_class(config=config)

    def list_agents(self) -> list[str]:
        """列出所有已注册Agent"""
        return list(self.agents.keys())


# 全局注册表单例
_registry: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    """获取全局Agent注册表"""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
```

**Step 4: 运行测试，确认通过**

```bash
pytest tests/agents/test_base.py -v
# Expected: 3 PASS
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add Agent base class and registry"
```

---

### Task 0.3: 创建 Skill 基类与注册机制

**Files:**
- Create: `btw/skills/base.py`
- Test: `btw/tests/skills/test_base.py`

**Step 1: 写失败测试**

```python
# tests/skills/test_base.py
import pytest
from skills.base import Skill, SkillRegistry

class TestSkill(Skill):
    name = "test_skill"
    description = "A test skill"

    async def execute(self, **kwargs) -> dict:
        return {"executed": True, **kwargs}

def test_skill_registry():
    registry = SkillRegistry()
    registry.register(TestSkill)

    assert "test_skill" in registry.skills
    skill_class = registry.get("test_skill")
    assert skill_class == TestSkill

@pytest.mark.asyncio
async def test_skill_execute():
    skill = TestSkill()
    result = await skill.execute(foo="bar")
    assert result["executed"] is True
    assert result["foo"] == "bar"
```

**Step 2: 运行测试，确认失败**

```bash
pytest tests/skills/test_base.py -v
# Expected: 2 FAIL
```

**Step 3: 实现基类**

```python
# skills/base.py
from abc import ABC, abstractmethod
from typing import Any, Type, Callable
from functools import wraps


class Skill(ABC):
    """所有Skill的基类"""

    name: str = "base_skill"
    description: str = "Base skill class"
    parameters: dict[str, dict] = {}  # JSON Schema for parameters

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行skill"""
        pass


class SkillRegistry:
    """Skill注册表"""

    def __init__(self):
        self.skills: dict[str, Type[Skill]] = {}

    def register(self, skill_class: Type[Skill]) -> None:
        self.skills[skill_class.name] = skill_class

    def get(self, name: str) -> Type[Skill]:
        if name not in self.skills:
            raise KeyError(f"Skill '{name}' not registered")
        return self.skills[name]

    def create(self, name: str) -> Skill:
        skill_class = self.get(name)
        return skill_class()

    def list_skills(self) -> list[str]:
        return list(self.skills.keys())


# 全局注册表
_skill_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
    return _skill_registry
```

**Step 4: 运行测试，确认通过**

```bash
pytest tests/skills/test_base.py -v
# Expected: 2 PASS
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add Skill base class and registry"
```

---

### Task 0.4: 创建多模型抽象层（LLM Adapter）

**Files:**
- Create: `btw/models/base.py`
- Create: `btw/models/claude_adapter.py`
- Create: `btw/models/openai_adapter.py`
- Create: `btw/models/ollama_adapter.py`
- Test: `btw/tests/models/test_base.py`

**Step 1: 写失败测试**

```python
# tests/models/test_base.py
import pytest
from models.base import LLMAdapter, AdapterRegistry

class MockAdapter(LLMAdapter):
    name = "mock"

    async def chat(self, messages: list, **kwargs) -> str:
        return "mock response"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

def test_adapter_registry():
    registry = AdapterRegistry()
    registry.register(MockAdapter)

    adapter = registry.create("mock", {"api_key": "test"})
    assert isinstance(adapter, MockAdapter)

@pytest.mark.asyncio
async def test_adapter_chat():
    adapter = MockAdapter(config={"api_key": "test"})
    result = await adapter.chat([{"role": "user", "content": "hello"}])
    assert result == "mock response"

@pytest.mark.asyncio
async def test_adapter_embed():
    adapter = MockAdapter(config={})
    embeddings = await adapter.embed(["text1", "text2"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 3
```

**Step 2: 运行测试，确认失败**

```bash
pytest tests/models/test_base.py -v
# Expected: 3 FAIL
```

**Step 3: 实现基类**

```python
# models/base.py
from abc import ABC, abstractmethod
from typing import Any, Type
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # system, user, assistant
    content: str


class LLMAdapter(ABC):
    """LLM适配器基类"""

    name: str = "base"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", None)
        self.model = config.get("model", self.default_model())

    @abstractmethod
    def default_model(self) -> str:
        pass

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        """聊天接口，返回文本"""
        pass

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """嵌入接口，返回向量列表"""
        pass


class AdapterRegistry:
    """适配器注册表"""

    def __init__(self):
        self.adapters: dict[str, Type[LLMAdapter]] = {}

    def register(self, adapter_class: Type[LLMAdapter]) -> None:
        self.adapters[adapter_class.name] = adapter_class

    def get(self, name: str) -> Type[LLMAdapter]:
        if name not in self.adapters:
            raise KeyError(f"Adapter '{name}' not registered")
        return self.adapters[name]

    def create(self, name: str, config: dict) -> LLMAdapter:
        adapter_class = self.get(name)
        return adapter_class(config)

    def list_adapters(self) -> list[str]:
        return list(self.adapters.keys())


_adapter_registry: AdapterRegistry | None = None


def get_adapter_registry() -> AdapterRegistry:
    global _adapter_registry
    if _adapter_registry is None:
        _adapter_registry = AdapterRegistry()
    return _adapter_registry
```

**Step 4: 实现 Claude Adapter（骨架）**

```python
# models/claude_adapter.py
from models.base import LLMAdapter


class ClaudeAdapter(LLMAdapter):
    """Anthropic Claude 适配器"""

    name = "claude"

    def default_model(self) -> str:
        return "claude-3-opus-20240229"

    async def chat(self, messages: list[dict], **kwargs) -> str:
        # TODO: 实现实际调用
        # import anthropic
        # client = anthropic.AsyncAnthropic(api_key=self.api_key)
        # ...
        return f"[Claude response placeholder for {len(messages)} messages]"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Claude 不提供 embedding，用其他方式
        # TODO: fallback 到 OpenAI 或其他
        return [[0.0] * 1536 for _ in texts]
```

**Step 5: 实现 OpenAI Adapter（骨架）**

```python
# models/openai_adapter.py
from models.base import LLMAdapter


class OpenAIAdapter(LLMAdapter):
    """OpenAI 适配器"""

    name = "openai"

    def default_model(self) -> str:
        return "gpt-4-turbo-preview"

    async def chat(self, messages: list[dict], **kwargs) -> str:
        # TODO: 实现实际调用
        return f"[OpenAI response placeholder for {len(messages)} messages]"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # TODO: 实现 embedding
        return [[0.0] * 1536 for _ in texts]
```

**Step 6: 实现 Ollama Adapter（骨架）**

```python
# models/ollama_adapter.py
from models.base import LLMAdapter


class OllamaAdapter(LLMAdapter):
    """Ollama 本地模型适配器"""

    name = "ollama"

    def default_model(self) -> str:
        return "llama2"

    async def chat(self, messages: list[dict], **kwargs) -> str:
        # TODO: 实现实际调用
        return f"[Ollama response placeholder for {len(messages)} messages]"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # TODO: 实现 embedding
        return [[0.0] * 4096 for _ in texts]
```

**Step 7: 运行测试，确认通过**

```bash
pytest tests/models/test_base.py -v
# Expected: 3 PASS
```

**Step 8: Commit**

```bash
git add .
git commit -m "feat: add LLM adapter base and skeleton implementations"
```

---

### Task 0.5: 创建存储层基础设施

**Files:**
- Create: `btw/storage/db.py`
- Create: `btw/storage/book_store.py`
- Create: `btw/storage/vector_store.py`
- Test: `btw/tests/storage/test_db.py`

**Step 1: 创建数据库连接和表结构**

```python
# storage/db.py
import sqlite3
from contextlib import contextmanager
from pathlib import Path
import json

DB_PATH = Path("data/btw.db")


def init_db():
    """初始化数据库表结构"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        cursor = conn.cursor()

        # 书籍表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT,
                status TEXT DEFAULT 'pending',
                meta_json TEXT
            )
        """)

        # 章节表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                id TEXT PRIMARY KEY,
                book_id TEXT NOT NULL,
                index_num INTEGER NOT NULL,
                title TEXT,
                type_tag TEXT,
                content_path TEXT,
                summary_path TEXT,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (book_id) REFERENCES books(id)
            )
        """)

        # 段落表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paragraphs (
                id TEXT PRIMARY KEY,
                chapter_id TEXT NOT NULL,
                index_num INTEGER NOT NULL,
                type TEXT,
                text TEXT,
                context TEXT,
                entities_json TEXT,
                concepts_json TEXT,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id)
            )
        """)

        # 概念索引表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id TEXT NOT NULL,
                name TEXT NOT NULL,
                paragraph_ids_json TEXT,
                UNIQUE(book_id, name)
            )
        """)

        # Agent执行日志
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                book_id TEXT,
                chapter_id TEXT,
                input_summary TEXT,
                output_summary TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # AI结果缓存
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT UNIQUE NOT NULL,
                model TEXT,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()


@contextmanager
def get_connection():
    """获取数据库连接上下文"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class BookRepository:
    """书籍数据访问"""

    @staticmethod
    def create_book(book_id: str, title: str, author: str | None, file_path: str) -> None:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO books (id, title, author, file_path) VALUES (?, ?, ?, ?)",
                (book_id, title, author, file_path)
            )
            conn.commit()

    @staticmethod
    def get_book(book_id: str) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_status(book_id: str, status: str) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE books SET status = ? WHERE id = ?",
                (status, book_id)
            )
            conn.commit()
```

**Step 2: 创建文件存储**

```python
# storage/book_store.py
import shutil
from pathlib import Path
import hashlib

DATA_DIR = Path("data/books")


def ensure_book_dir(book_id: str) -> Path:
    """确保书籍目录存在"""
    book_dir = DATA_DIR / book_id
    book_dir.mkdir(parents=True, exist_ok=True)
    return book_dir


def save_uploaded_file(book_id: str, file_path: Path) -> Path:
    """保存上传的原始文件"""
    book_dir = ensure_book_dir(book_id)
    dest = book_dir / "raw.txt"
    shutil.copy(file_path, dest)
    return dest


def save_chapter(book_id: str, chapter_index: int, content: str) -> Path:
    """保存章节内容"""
    book_dir = ensure_book_dir(book_id)
    chapter_dir = book_dir / "chapters" / f"{chapter_index:02d}"
    chapter_dir.mkdir(parents=True, exist_ok=True)

    content_path = chapter_dir / "content.md"
    content_path.write_text(content, encoding="utf-8")
    return content_path


def save_component(book_id: str, chapter_index: int, jsx_code: str, js_code: str | None = None) -> tuple[Path, Path | None]:
    """保存生成的组件代码"""
    book_dir = ensure_book_dir(book_id)
    chapter_dir = book_dir / "chapters" / f"{chapter_index:02d}"
    chapter_dir.mkdir(parents=True, exist_ok=True)

    jsx_path = chapter_dir / "component.jsx"
    jsx_path.write_text(jsx_code, encoding="utf-8")

    js_path = None
    if js_code:
        js_path = chapter_dir / "component.js"
        js_path.write_text(js_code, encoding="utf-8")

    return jsx_path, js_path


def get_component_path(book_id: str, chapter_index: int) -> Path:
    """获取组件路径"""
    return DATA_DIR / book_id / "chapters" / f"{chapter_index:02d}" / "component.js"
```

**Step 3: 创建向量存储（ChromaDB骨架）**

```python
# storage/vector_store.py
import chromadb
from chromadb.config import Settings
from pathlib import Path

CHROMA_DIR = Path("data/chroma")


class VectorStore:
    """向量存储封装"""

    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False)
        )

    def get_or_create_collection(self, book_id: str):
        """获取或创建书籍的集合"""
        return self.client.get_or_create_collection(
            name=f"book_{book_id}",
            metadata={"book_id": book_id}
        )

    def add_paragraphs(self, book_id: str, paragraphs: list[dict]):
        """添加段落到向量库"""
        collection = self.get_or_create_collection(book_id)

        ids = [p["id"] for p in paragraphs]
        texts = [p["text"] for p in paragraphs]
        metadatas = [{"chapter_id": p.get("chapter_id"), "index": p.get("index_num")} for p in paragraphs]

        # TODO: 调用 embedding adapter 获取向量
        # embeddings = await adapter.embed(texts)

        collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas
        )

    def search(self, book_id: str, query: str, n_results: int = 5):
        """语义搜索"""
        collection = self.get_or_create_collection(book_id)

        # TODO: 将 query 转为 embedding 再搜索
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )

        return results
```

**Step 4: 写简单测试验证表创建**

```python
# tests/storage/test_db.py
import pytest
from storage.db import init_db, get_connection, BookRepository
from pathlib import Path

def test_init_db():
    init_db()
    assert Path("data/btw.db").exists()

def test_book_repository():
    init_db()

    # 创建
    BookRepository.create_book("test-001", "Test Book", "Test Author", "/path/to/file.txt")

    # 读取
    book = BookRepository.get_book("test-001")
    assert book is not None
    assert book["title"] == "Test Book"
    assert book["author"] == "Test Author"

    # 更新状态
    BookRepository.update_status("test-001", "processing")
    book = BookRepository.get_book("test-001")
    assert book["status"] == "processing"
```

**Step 5: 运行测试**

```bash
pytest tests/storage/test_db.py -v
# Expected: 2 PASS
```

**Step 6: Commit**

```bash
git add .
git commit -m "feat: add storage layer (SQLite + FileSystem + ChromaDB skeleton)"
```

---

### Task 0.6: 初始化前端项目

**Files:**
- Create: `btw/frontend/package.json`
- Create: `btw/frontend/vite.config.ts`
- Create: `btw/frontend/tsconfig.json`
- Create: `btw/frontend/tailwind.config.js`
- Create: `btw/frontend/index.html`
- Create: `btw/frontend/src/main.tsx`
- Create: `btw/frontend/src/App.tsx`

**Step 1: 创建 package.json**

```json
{
  "name": "btw-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "echarts": "^5.4.3",
    "echarts-for-react": "^3.0.2",
    "katex": "^0.16.9",
    "framer-motion": "^11.0.0",
    "@monaco-editor/react": "^4.6.0",
    "@babel/standalone": "^7.23.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.55",
    "@types/react-dom": "^18.2.19",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.1",
    "typescript": "^5.3.3",
    "vite": "^5.1.0"
  }
}
```

**Step 2: 创建配置文件**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

```json
// frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

```javascript
// frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

```css
/* frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Step 3: 创建入口文件**

```html
<!-- frontend/index.html -->
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>BTW - Book To Web</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

```typescript
// frontend/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

```typescript
// frontend/src/App.tsx
function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm p-4">
        <h1 className="text-2xl font-bold text-gray-900">BTW - Book To Web</h1>
      </header>
      <main className="p-4">
        <p className="text-gray-600">Frontend ready.</p>
      </main>
    </div>
  )
}

export default App
```

**Step 4: 安装依赖并启动验证**

```bash
cd btw/frontend
npm install
npm run dev
# Expected: Vite dev server starts at http://localhost:3000
# 浏览器访问确认页面显示 "BTW - Book To Web" 和 "Frontend ready."
```

**Step 5: Commit**

```bash
# 在 btw 目录外，添加 frontend
# 注意: node_modules 已被 .gitignore 忽略
cd btw
git add frontend/
git commit -m "feat: initialize React frontend with Vite + Tailwind"
```

---

## Phase 1: 核心链路打通（端到端）

### Task 1.1: 实现 Director Agent（总指挥）

**Files:**
- Create: `btw/agents/director.py`
- Modify: `btw/agents/__init__.py` (注册所有Agent)
- Test: `btw/tests/agents/test_director.py`

**Step 1: 实现 Director**

```python
# agents/director.py
import asyncio
from typing import Any
from agents.base import Agent, AgentContext, get_registry
import uuid


class DirectorAgent(Agent):
    """总指挥Agent - 协调所有其他Agent"""

    name = "director"
    description = "协调所有Agent，分配任务"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.registry = get_registry()
        self.active_tasks: dict[str, dict] = {}

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        处理顶层请求

        input_data 格式:
        {
            "action": "upload_book" | "generate_component" | "get_component",
            "book_id": "...",
            "chapter_index": 0,  # 可选
            "file_path": "...",  # upload_book时需要
            ...
        }
        """
        action = input_data.get("action")
        task_id = str(uuid.uuid4())

        if action == "upload_book":
            return await self._handle_upload(task_id, input_data)
        elif action == "generate_component":
            return await self._handle_generate(task_id, input_data)
        elif action == "get_component":
            return await self._handle_get_component(task_id, input_data)
        else:
            return {"error": f"Unknown action: {action}"}

    async def _handle_upload(self, task_id: str, data: dict) -> dict:
        """处理上传书籍"""
        file_path = data.get("file_path")
        book_id = data.get("book_id")

        # 1. Parser 解析
        parser = self.registry.create("parser")
        parser.set_context(AgentContext(task_id=task_id, book_id=book_id))
        parse_result = await parser.process({
            "file_path": file_path,
            "book_id": book_id
        })

        # 2. Reader 理解
        reader = self.registry.create("reader")
        reader.set_context(AgentContext(task_id=task_id, book_id=book_id))
        read_result = await reader.process({
            "book_id": book_id,
            "chapters": parse_result.get("chapters", [])
        })

        return {
            "task_id": task_id,
            "book_id": book_id,
            "chapters_count": len(parse_result.get("chapters", [])),
            "concepts": read_result.get("concepts", []),
            "status": "completed"
        }

    async def _handle_generate(self, task_id: str, data: dict) -> dict:
        """处理生成组件"""
        book_id = data.get("book_id")
        chapter_index = data.get("chapter_index")

        # 1. 获取章节内容（通过存储层）
        from storage.db import BookRepository
        from storage.book_store import DATA_DIR

        chapter_dir = DATA_DIR / book_id / "chapters" / f"{chapter_index:02d}"
        content_path = chapter_dir / "content.md"

        if not content_path.exists():
            return {"error": "Chapter not found"}

        content = content_path.read_text(encoding="utf-8")

        # 2. Creator 生成代码
        creator = self.registry.create("creator")
        creator.set_context(AgentContext(task_id=task_id, book_id=book_id))
        create_result = await creator.process({
            "book_id": book_id,
            "chapter_index": chapter_index,
            "content": content
        })

        jsx_code = create_result.get("jsx_code")

        # 3. Engineer 编译
        engineer = self.registry.create("engineer")
        engineer.set_context(AgentContext(task_id=task_id, book_id=book_id))
        engineer_result = await engineer.process({
            "jsx_code": jsx_code,
            "book_id": book_id,
            "chapter_index": chapter_index
        })

        return {
            "task_id": task_id,
            "book_id": book_id,
            "chapter_index": chapter_index,
            "component_path": str(engineer_result.get("js_path")),
            "status": "completed"
        }

    async def _handle_get_component(self, task_id: str, data: dict) -> dict:
        """获取组件给前端"""
        book_id = data.get("book_id")
        chapter_index = data.get("chapter_index")

        from storage.book_store import get_component_path

        js_path = get_component_path(book_id, chapter_index)
        jsx_path = js_path.parent / "component.jsx"

        # 如果还没生成，返回错误
        if not js_path.exists() and not jsx_path.exists():
            return {
                "exists": False,
                "message": "Component not generated yet"
            }

        # 优先返回编译后的JS
        if js_path.exists():
            return {
                "exists": True,
                "type": "js",
                "code": js_path.read_text(encoding="utf-8")
            }
        else:
            return {
                "exists": True,
                "type": "jsx",
                "code": jsx_path.read_text(encoding="utf-8")
            }
```

**Step 2: 注册 Director**

```python
# agents/__init__.py
from agents.base import get_registry
from agents.director import DirectorAgent
# 先注册基础Agent框架，具体实现后续添加

_registry = get_registry()
_registry.register(DirectorAgent)

__all__ = ["get_registry", "DirectorAgent"]
```

**Step 3: 测试 Director 骨架**

```python
# tests/agents/test_director.py
import pytest
from agents.director import DirectorAgent
from agents.base import AgentContext

@pytest.mark.asyncio
async def test_director_skeleton():
    director = DirectorAgent(config={})

    # 测试空action
    result = await director.process({"action": "unknown"})
    assert "error" in result
```

**Step 4: Commit**

```bash
git add .
git commit -m "feat: add Director Agent skeleton with workflow orchestration"
```

---

### Task 1.2: 实现 Parser Agent（解析器）

**Files:**
- Create: `btw/agents/parser.py`
- Test: `btw/tests/agents/test_parser.py`

**Step 1: 实现 Parser**

```python
# agents/parser.py
from pathlib import Path
from agents.base import Agent
from storage.db import BookRepository
from storage.book_store import ensure_book_dir


class ParserAgent(Agent):
    """解析器Agent - 处理上传的文件"""

    name = "parser"
    description = "解析上传的书籍文件"

    async def process(self, input_data: dict) -> dict:
        """
        input: { "file_path": "...", "book_id": "..." }
        output: { "book_id": "...", "chapters": [...] }
        """
        file_path = Path(input_data.get("file_path"))
        book_id = input_data.get("book_id")

        # 读取文件
        text = file_path.read_text(encoding="utf-8")

        # 简单分章（按 # 或 ## 分隔）
        chapters = self._split_chapters(text)

        # 保存每章到文件
        book_dir = ensure_book_dir(book_id)
        for i, chapter in enumerate(chapters):
            chapter_dir = book_dir / "chapters" / f"{i:02d}"
            chapter_dir.mkdir(parents=True, exist_ok=True)

            (chapter_dir / "content.md").write_text(
                chapter["content"], encoding="utf-8"
            )

        # 更新数据库状态
        BookRepository.update_status(book_id, "parsed")

        return {
            "book_id": book_id,
            "chapters": chapters,
            "total_chapters": len(chapters)
        }

    def _split_chapters(self, text: str) -> list[dict]:
        """简单分章逻辑"""
        import re

        # 按 ## 或 # 开头分割
        pattern = r'^(#{1,2}\s+.+)$'
        parts = re.split(pattern, text, flags=re.MULTILINE)

        chapters = []
        current_title = "Chapter 1"
        current_content = ""

        for part in parts[1:]:  # 跳过第一个空部分
            if part.startswith('#'):
                # 如果有累积的内容，保存上一章
                if current_content.strip():
                    chapters.append({
                        "title": current_title,
                        "content": current_content.strip(),
                        "index": len(chapters)
                    })
                current_title = part.lstrip('#').strip()
                current_content = ""
            else:
                current_content += part

        # 最后一章
        if current_content.strip():
            chapters.append({
                "title": current_title,
                "content": current_content.strip(),
                "index": len(chapters)
            })

        # 如果没分出来，按段落分
        if not chapters:
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            # 每10个段落一章
            chunk_size = 10
            for i in range(0, len(paragraphs), chunk_size):
                chunk = paragraphs[i:i+chunk_size]
                chapters.append({
                    "title": f"Section {len(chapters)+1}",
                    "content": '\n\n'.join(chunk),
                    "index": len(chapters)
                })

        return chapters
```

**Step 2: 注册并测试**

```python
# tests/agents/test_parser.py
import pytest
from agents.parser import ParserAgent
from pathlib import Path
import tempfile

@pytest.mark.asyncio
async def test_parser_split_chapters():
    parser = ParserAgent(config={})

    text = """
# Introduction
This is intro.

## Chapter 1
First chapter content.
More content here.

## Chapter 2
Second chapter content.
"""

    chapters = parser._split_chapters(text)
    assert len(chapters) >= 2
    assert "Chapter 1" in str(chapters)
```

**Step 3: 注册到 agents/__init__.py**

```python
# agents/__init__.py
from agents.parser import ParserAgent
# ...
_registry.register(ParserAgent)
```

**Step 4: Commit**

```bash
git add .
git commit -m "feat: add Parser Agent with chapter splitting"
```

---

### Task 1.3: 实现 Reader Agent（理解者）

**Files:**
- Create: `btw/agents/reader.py`
- Test: `btw/tests/agents/test_reader.py`

**Step 1: 实现 Reader（骨架）**

```python
# agents/reader.py
from pathlib import Path
from agents.base import Agent
from storage.db import BookRepository
from storage.book_store import DATA_DIR
from storage.vector_store import VectorStore


class ReaderAgent(Agent):
    """理解者Agent - 深度阅读书籍"""

    name = "reader"
    description = "深度阅读书籍，生成分层摘要和概念索引"

    async def process(self, input_data: dict) -> dict:
        """
        input: { "book_id": "...", "chapters": [...] }
        output: { "book_id": "...", "summary": "...", "concepts": [...] }
        """
        book_id = input_data.get("book_id")
        chapters = input_data.get("chapters", [])

        # TODO: 真正的AI分析（现在用placeholder）
        # 1. 为每章生成摘要
        chapter_summaries = []
        for ch in chapters:
            summary = await self._summarize_chapter(ch)
            chapter_summaries.append(summary)

        # 2. 生成全书摘要
        book_summary = await self._summarize_book(chapter_summaries)

        # 3. 提取概念
        concepts = await self._extract_concepts(chapters)

        # 4. 保存到向量库
        await self._index_chapters(book_id, chapters)

        # 保存全书摘要
        book_dir = DATA_DIR / book_id
        (book_dir / "book_summary.md").write_text(book_summary, encoding="utf-8")

        # 保存概念索引
        import json
        (book_dir / "concept_index.json").write_text(
            json.dumps(concepts, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return {
            "book_id": book_id,
            "summary": book_summary,
            "concepts": concepts,
            "chapters_analyzed": len(chapters)
        }

    async def _summarize_chapter(self, chapter: dict) -> str:
        """为章节生成摘要（placeholder）"""
        title = chapter.get("title", "Untitled")
        content = chapter.get("content", "")[:500]  # 前500字符

        # TODO: 调用LLM生成真正摘要
        return f"【{title}】\n{content[:200]}..."

    async def _summarize_book(self, chapter_summaries: list) -> str:
        """生成全书摘要（placeholder）"""
        if not chapter_summaries:
            return "No content"

        # TODO: 调用LLM生成真正摘要
        return "\n\n".join(chapter_summaries[:3]) + "\n\n[本书共{}章]".format(len(chapter_summaries))

    async def _extract_concepts(self, chapters: list) -> list[dict]:
        """提取概念（placeholder）"""
        # TODO: 真正的概念提取
        concepts = []
        for ch in chapters:
            content = ch.get("content", "")
            # 简单提取：找引号内容作为概念
            import re
            found = re.findall(r'"([^"]+)"', content)
            for f in found[:3]:  # 每章最多3个
                concepts.append({
                    "name": f,
                    "chapter": ch.get("title"),
                    "source": "extracted"
                })
        return concepts

    async def _index_chapters(self, book_id: str, chapters: list) -> None:
        """索引到向量库"""
        # TODO: 真正的embedding和索引
        # vector_store = VectorStore()
        # ...
        pass
```

**Step 2: 注册并测试**

```python
# tests/agents/test_reader.py
import pytest
from agents.reader import ReaderAgent

@pytest.mark.asyncio
async def test_reader_skeleton():
    reader = ReaderAgent(config={})

    result = await reader.process({
        "book_id": "test-001",
        "chapters": [
            {"title": "Ch1", "content": "This is chapter 1 about \"Supply\" and \"Demand\"."}
        ]
    })

    assert result["book_id"] == "test-001"
    assert "summary" in result
    assert "concepts" in result
```

**Step 3: Commit**

```bash
git add .
git commit -m "feat: add Reader Agent skeleton with summarization placeholders"
```

---

### Task 1.4: 实现 Creator Agent（创造者）

**Files:**
- Create: `btw/agents/creator.py`
- Create: `btw/config/prompts/creator_system.txt`
- Test: `btw/tests/agents/test_creator.py`

**Step 1: 创建 System Prompt**

```
# config/prompts/creator_system.txt
你是一位资深前端工程师，专注于创建高质量的交互式数据可视化组件。

你的任务是将书籍章节内容转化为一个可交互的 React 组件。

可用依赖：
- React (useState, useEffect, useRef)
- ECharts (echarts, echarts-for-react)
- KaTeX (数学公式)
- Framer Motion (动画)

输出格式要求：
1. 严格输出标准 React 函数组件
2. 使用 export default function ComponentName(props) 格式
3. 组件名使用 PascalCase
4. 不要包含任何导入语句（依赖会自动注入）
5. 代码必须可以直接执行，不要 placeholder

组件应该：
- 根据内容判断适合的交互类型（图表/公式/代码/叙事）
- 使用滑块、按钮等让用户可以交互
- 响应式适配不同屏幕
- 添加适当的注释说明
```

**Step 2: 实现 Creator**

```python
# agents/creator.py
from pathlib import Path
from agents.base import Agent
from skills.base import get_skill_registry


class CreatorAgent(Agent):
    """创造者Agent - 生成交互组件"""

    name = "creator"
    description = "根据章节内容生成交互式 React 组件"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.llm_config = config.get("llm", {"provider": "claude", "model": "claude-3-opus"})

    async def process(self, input_data: dict) -> dict:
        """
        input: { "book_id": "...", "chapter_index": 0, "content": "..." }
        output: { "jsx_code": "...", "component_type": "...", "dependencies": [...] }
        """
        book_id = input_data.get("book_id")
        chapter_index = input_data.get("chapter_index")
        content = input_data.get("content", "")

        # 1. 分析内容类型（简单规则判断）
        content_type = self._analyze_content_type(content)

        # 2. 构建 prompt
        prompt = self._build_prompt(content, content_type)

        # 3. 调用 LLM 生成代码
        llm_skill = get_skill_registry().create("llm_call")
        result = await llm_skill.execute(
            messages=[
                {"role": "system", "content": self._load_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            **self.llm_config
        )

        jsx_code = result.get("content", "")

        # 4. 清理代码（提取 JSX 部分）
        jsx_code = self._extract_jsx(jsx_code)

        return {
            "book_id": book_id,
            "chapter_index": chapter_index,
            "jsx_code": jsx_code,
            "component_type": content_type,
            "dependencies": self._extract_dependencies(jsx_code)
        }

    def _analyze_content_type(self, content: str) -> str:
        """判断内容类型"""
        content_lower = content.lower()

        if any(x in content_lower for x in ["formula", "equation", "=", "function", "variable"]):
            return "formula"
        elif any(x in content_lower for x in ["chart", "graph", "data", "percent", "statistics"]):
            return "chart"
        elif "```" in content or "code" in content_lower:
            return "code"
        else:
            return "narrative"

    def _build_prompt(self, content: str, content_type: str) -> str:
        """构建生成 prompt"""
        return f"""请为以下内容创建一个交互式 React 组件。

内容类型: {content_type}

章节内容:
{content[:2000]}  # 限制长度，避免token过多

要求:
1. 如果是数据内容，使用 ECharts 创建可交互图表
2. 如果是公式，使用 KaTeX 渲染并可调节参数
3. 代码简洁，组件名使用 Chapter{hash(content[:50])[:8]}Component
4. 添加交互元素（滑块/按钮等）
"""

    def _load_system_prompt(self) -> str:
        """加载 system prompt"""
        prompt_path = Path("config/prompts/creator_system.txt")
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return "You are a frontend developer. Generate React components."

    def _extract_jsx(self, response: str) -> str:
        """从 LLM 响应中提取 JSX 代码"""
        # 查找代码块
        import re

        # 尝试找 ```jsx ... ```
        match = re.search(r'```(?:jsx?|javascript)?\s*\n(.*?)\n```', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 否则返回整个响应
        return response.strip()

    def _extract_dependencies(self, jsx_code: str) -> list[str]:
        """提取依赖"""
        deps = ["react"]

        if "echarts" in jsx_code.lower():
            deps.append("echarts")
            deps.append("echarts-for-react")
        if "katex" in jsx_code.lower():
            deps.append("katex")
        if "framer" in jsx_code.lower():
            deps.append("framer-motion")

        return deps
```

**Step 3: 实现 llm_call Skill**

```python
# skills/llm_call.py
from skills.base import Skill
from models.base import get_adapter_registry


class LLMCallSkill(Skill):
    """调用LLM的Skill"""

    name = "llm_call"
    description = "调用大语言模型"
    parameters = {
        "messages": {"type": "array", "description": "对话消息列表"},
        "provider": {"type": "string", "description": "模型提供商"},
        "model": {"type": "string", "description": "模型名称"}
    }

    async def execute(self, **kwargs) -> dict:
        messages = kwargs.get("messages", [])
        provider = kwargs.get("provider", "claude")
        model = kwargs.get("model")

        # 获取适配器
        adapter_registry = get_adapter_registry()

        # 确保适配器已注册
        try:
            adapter = adapter_registry.create(provider, {
                "api_key": "",  # TODO: 从配置读取
                "model": model
            })
        except KeyError:
            # 未注册，注册骨架
            if provider == "claude":
                from models.claude_adapter import ClaudeAdapter
                adapter_registry.register(ClaudeAdapter)
            elif provider == "openai":
                from models.openai_adapter import OpenAIAdapter
                adapter_registry.register(OpenAIAdapter)
            else:
                from models.ollama_adapter import OllamaAdapter
                adapter_registry.register(OllamaAdapter)

            adapter = adapter_registry.create(provider, {"api_key": "", "model": model})

        # 调用
        content = await adapter.chat(messages)

        return {
            "content": content,
            "provider": provider,
            "model": model
        }
```

**Step 4: 注册并测试**

```python
# tests/agents/test_creator.py
import pytest
from agents.creator import CreatorAgent

@pytest.mark.asyncio
async def test_creator_analyze_type():
    creator = CreatorAgent(config={})

    # 测试公式识别
    text1 = "The supply and demand formula is P = F/A"
    assert creator._analyze_content_type(text1) == "formula"

    # 测试图表识别
    text2 = "Look at the chart showing data from 2020 to 2024"
    assert creator._analyze_content_type(text2) == "chart"

    # 测试叙事识别
    text3 = "Once upon a time in a land far away"
    assert creator._analyze_content_type(text3) == "narrative"

@pytest.mark.asyncio
async def test_creator_skeleton():
    creator = CreatorAgent(config={})

    # 用 mock 测试骨架
    result = await creator.process({
        "book_id": "test-001",
        "chapter_index": 0,
        "content": "This is a test chapter about supply and demand."
    })

    assert "jsx_code" in result
    assert "component_type" in result
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add Creator Agent with LLM call skill (skeleton)"
```

---

### Task 1.5: 实现 Engineer Agent（工程师）

**Files:**
- Create: `btw/agents/engineer.py`
- Create: `btw/skills/code_validate.py`
- Create: `btw/skills/code_compile.py`
- Test: `btw/tests/agents/test_engineer.py`

**Step 1: 实现代码安检 Skill**

```python
# skills/code_validate.py
import ast
from skills.base import Skill


class CodeValidateSkill(Skill):
    """代码安全验证"""

    name = "code_validate"
    description = "验证JSX代码安全性"

    DANGEROUS_NAMES = {
        'eval', 'exec', 'compile', '__import__', 'open', 'input',
        'raw_input', 'reload', 'exit', 'quit'
    }

    async def execute(self, **kwargs) -> dict:
        code = kwargs.get("code", "")

        try:
            # 尝试解析为 Python AST
            # 注意：JSX不是Python，但我们可以做一些基本检查
            # 真正的安全检查应该在编译阶段由 esbuild 做

            issues = []

            # 简单字符串检查危险函数
            for name in self.DANGEROUS_NAMES:
                if name in code:
                    issues.append(f"Potentially dangerous: {name}")

            # 检查网络请求
            if 'fetch(' in code or 'axios' in code:
                issues.append("Network request detected - review carefully")

            # 检查 localStorage/cookie
            if 'localStorage' in code or 'document.cookie' in code:
                issues.append("Storage access detected - review carefully")

            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "code_length": len(code)
            }
        except Exception as e:
            return {
                "valid": False,
                "issues": [f"Parse error: {str(e)}"],
                "code_length": len(code)
            }
```

**Step 2: 实现代码编译 Skill**

```python
# skills/code_compile.py
import subprocess
import tempfile
from pathlib import Path
from skills.base import Skill


class CodeCompileSkill(Skill):
    """代码编译 - 使用 esbuild"""

    name = "code_compile"
    description = "将JSX编译为JS"

    async def execute(self, **kwargs) -> dict:
        jsx_code = kwargs.get("jsx_code", "")
        output_path = kwargs.get("output_path")

        if not jsx_code:
            return {"success": False, "error": "Empty code"}

        # 1. 添加 React 导入包装
        wrapped_code = self._wrap_code(jsx_code)

        # 2. 写入临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsx', delete=False) as f:
            f.write(wrapped_code)
            temp_path = f.name

        try:
            # 3. 调用 esbuild
            cmd = [
                'npx', 'esbuild',
                temp_path,
                '--bundle',
                '--platform=browser',
                '--format=esm',
                '--external:react',
                '--external:react-dom',
                '--external:echarts',
                '--external:echarts-for-react',
                '--external:katex',
                '--external:framer-motion',
                '--outfile=' + str(output_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd='frontend'  # 在 frontend 目录执行
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr,
                    "stdout": result.stdout
                }

            return {
                "success": True,
                "output_path": output_path,
                "bundle_size": Path(output_path).stat().st_size
            }

        finally:
            # 清理临时文件
            Path(temp_path).unlink(missing_ok=True)

    def _wrap_code(self, jsx_code: str) -> str:
        """包装为可编译的模块"""
        # 添加默认导出包装
        return f"""import React from 'react';

{jsx_code}
"""
```

**Step 3: 实现 Engineer Agent**

```python
# agents/engineer.py
from pathlib import Path
from agents.base import Agent
from skills.base import get_skill_registry
from storage.book_store import save_component


class EngineerAgent(Agent):
    """工程师Agent - 代码安检和编译"""

    name = "engineer"
    description = "安检、编译、构建组件"

    async def process(self, input_data: dict) -> dict:
        """
        input: { "jsx_code": "...", "book_id": "...", "chapter_index": 0 }
        output: { "js_path": "...", "bundle_size": 1234, "status": "success" }
        """
        jsx_code = input_data.get("jsx_code", "")
        book_id = input_data.get("book_id")
        chapter_index = input_data.get("chapter_index")

        # 1. 安检
        validator = get_skill_registry().create("code_validate")
        validation = await validator.execute(code=jsx_code)

        if not validation.get("valid"):
            return {
                "success": False,
                "error": "Validation failed",
                "issues": validation.get("issues", [])
            }

        # 2. 保存原始 JSX
        from storage.book_store import ensure_book_dir
        chapter_dir = ensure_book_dir(book_id) / "chapters" / f"{chapter_index:02d}"
        chapter_dir.mkdir(parents=True, exist_ok=True)

        jsx_path = chapter_dir / "component.jsx"
        jsx_path.write_text(jsx_code, encoding="utf-8")

        # 3. 编译
        js_path = chapter_dir / "component.js"

        compiler = get_skill_registry().create("code_compile")
        compile_result = await compiler.execute(
            jsx_code=jsx_code,
            output_path=str(js_path)
        )

        if not compile_result.get("success"):
            return {
                "success": False,
                "error": compile_result.get("error"),
                "stage": "compilation"
            }

        return {
            "success": True,
            "jsx_path": str(jsx_path),
            "js_path": str(js_path),
            "bundle_size": compile_result.get("bundle_size", 0),
            "validation_issues": validation.get("issues", [])
        }
```

**Step 4: 注册并测试**

```python
# tests/agents/test_engineer.py
import pytest
from agents.engineer import EngineerAgent

@pytest.mark.asyncio
async def test_engineer_validation():
    engineer = EngineerAgent(config={})

    # 测试含危险内容的代码
    result = await engineer.process({
        "jsx_code": "function Evil() { eval('bad'); return <div>test</div>; }",
        "book_id": "test-001",
        "chapter_index": 0
    })

    # 应该失败（有eval）
    assert result.get("success") is False or len(result.get("validation_issues", [])) > 0
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add Engineer Agent with code validation and compilation"
```

---

### Task 1.6: 实现 FastAPI 路由

**Files:**
- Create: `btw/api/routes.py`
- Create: `btw/main.py` (FastAPI入口)

**Step 1: 实现 API 路由**

```python
# api/routes.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import shutil
from pathlib import Path
import uuid

from agents.director import DirectorAgent
from agents.base import get_registry
from storage.db import BookRepository
from storage.book_store import DATA_DIR

router = APIRouter()


@router.post("/books/upload")
async def upload_book(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form(None)
):
    """上传书籍并触发解析流程"""

    # 生成ID
    book_id = str(uuid.uuid4())[:8]

    # 保存上传文件
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{book_id}_{file.filename}"

    with file_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # 创建数据库记录
    BookRepository.create_book(book_id, title, author, str(file_path))

    # 异步触发 Director 处理
    registry = get_registry()
    director = registry.create("director")

    result = await director.process({
        "action": "upload_book",
        "book_id": book_id,
        "file_path": str(file_path)
    })

    return {
        "book_id": book_id,
        "title": title,
        "status": result.get("status"),
        "chapters_count": result.get("chapters_count")
    }


@router.get("/books/{book_id}")
async def get_book(book_id: str):
    """获取书籍信息"""
    book = BookRepository.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return dict(book)


@router.get("/books/{book_id}/chapters")
async def get_chapters(book_id: str):
    """获取书籍章节列表"""
    from storage.db import get_connection

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, index_num, title, type_tag, status FROM chapters WHERE book_id = ? ORDER BY index_num",
            (book_id,)
        ).fetchall()

        return {"chapters": [dict(row) for row in rows]}


@router.post("/books/{book_id}/chapters/{chapter_index}/generate")
async def generate_component(book_id: str, chapter_index: int):
    """生成章节交互组件"""

    registry = get_registry()
    director = registry.create("director")

    result = await director.process({
        "action": "generate_component",
        "book_id": book_id,
        "chapter_index": chapter_index
    })

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/books/{book_id}/chapters/{chapter_index}/component")
async def get_component(book_id: str, chapter_index: int):
    """获取组件代码给前端"""

    registry = get_registry()
    director = registry.create("director")

    result = await director.process({
        "action": "get_component",
        "book_id": book_id,
        "chapter_index": chapter_index
    })

    if not result.get("exists"):
        raise HTTPException(status_code=404, detail=result.get("message", "Component not found"))

    return result
```

**Step 2: 创建 FastAPI 主入口**

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from agents import register_all_agents
from skills import register_all_skills
from storage.db import init_db

# 初始化
init_db()
register_all_agents()
register_all_skills()

app = FastAPI(title="BTW API", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 3: 更新 agents/__init__.py 添加注册函数**

```python
# agents/__init__.py
from agents.base import get_registry, Agent, AgentContext
from agents.director import DirectorAgent
from agents.parser import ParserAgent
from agents.reader import ReaderAgent
from agents.creator import CreatorAgent
from agents.engineer import EngineerAgent

_registry = get_registry()

# 立即注册的核心Agent
_registry.register(DirectorAgent)
_registry.register(ParserAgent)
_registry.register(ReaderAgent)
_registry.register(CreatorAgent)
_registry.register(EngineerAgent)


def register_all_agents():
    """注册所有Agent（在main.py中调用）"""
    # 骨架Agent已注册，后续在此处添加其他Agent
    from agents.critic import CriticAgent  # 后续实现
    from agents.stylist import StylistAgent
    # ... 其他Agent
    pass


__all__ = [
    "get_registry", "Agent", "AgentContext",
    "DirectorAgent", "ParserAgent", "ReaderAgent",
    "CreatorAgent", "EngineerAgent"
]
```

**Step 4: 创建 skills/__init__.py**

```python
# skills/__init__.py
from skills.base import get_skill_registry, Skill
from skills.llm_call import LLMCallSkill
from skills.code_validate import CodeValidateSkill
from skills.code_compile import CodeCompileSkill

_registry = get_skill_registry()

# 注册核心skills
_registry.register(LLMCallSkill)
_registry.register(CodeValidateSkill)
_registry.register(CodeCompileSkill)


def register_all_skills():
    """注册所有skills"""
    # 骨架skills已注册，后续添加其他
    pass


__all__ = ["get_skill_registry", "Skill"]
```

**Step 5: 启动后端并测试**

```bash
cd btw
# 安装依赖
pip install -e .

# 启动后端
python main.py

# 在另一个终端测试
# Expected: curl http://localhost:8000/health
# Response: {"status": "ok", "version": "0.1.0"}
```

**Step 6: Commit**

```bash
git add .
git commit -m "feat: add FastAPI routes for book upload and component generation"
```

---

### Task 1.7: 前端动态组件渲染器

**Files:**
- Create: `btw/frontend/src/renderer/DynamicLoader.tsx`
- Create: `btw/frontend/src/renderer/BabelCompiler.ts`
- Modify: `btw/frontend/src/App.tsx` (添加完整UI)

**Step 1: 创建 Babel 编译器**

```typescript
// frontend/src/renderer/BabelCompiler.ts
// @ts-ignore
import Babel from '@babel/standalone';

export async function compileJSX(jsxCode: string): Promise<string> {
  try {
    const result = Babel.transform(jsxCode, {
      presets: ['react'],
      plugins: [],
    });
    return result.code || '';
  } catch (error: any) {
    throw new Error(`Compilation error: ${error.message}`);
  }
}
```

**Step 2: 创建动态加载器**

```typescript
// frontend/src/renderer/DynamicLoader.tsx
import { useEffect, useState, lazy, Suspense } from 'react';
import { compileJSX } from './BabelCompiler';

interface DynamicComponentProps {
  bookId: string;
  chapterIndex: number;
}

const FallbackComponent = () => (
  <div className="p-8 bg-gray-100 rounded-lg">
    <p className="text-gray-500">Loading interactive component...</p>
  </div>
);

export function DynamicComponent({ bookId, chapterIndex }: DynamicComponentProps) {
  const [Component, setComponent] = useState<React.ComponentType | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadComponent = async () => {
      try {
        // 获取组件代码
        const response = await fetch(
          `/api/books/${bookId}/chapters/${chapterIndex}/component`
        );

        if (!response.ok) {
          if (response.status === 404) {
            setError('Component not generated yet. Please generate first.');
            return;
          }
          throw new Error(`Failed to load component: ${response.status}`);
        }

        const data = await response.json();

        let jsCode: string;

        if (data.type === 'js') {
          // 后端已编译，直接用
          jsCode = data.code;
        } else {
          // 前端编译
          jsCode = await compileJSX(data.code);
        }

        // 创建 blob URL 并动态导入
        const blob = new Blob([jsCode], { type: 'application/javascript' });
        const url = URL.createObjectURL(blob);

        try {
          const module = await import(/* @vite-ignore */ url);
          setComponent(() => module.default || module.Component || (() => null));
        } finally {
          URL.revokeObjectURL(url);
        }

      } catch (err: any) {
        setError(err.message);
      }
    };

    loadComponent();
  }, [bookId, chapterIndex]);

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-600">Error: {error}</p>
      </div>
    );
  }

  if (!Component) {
    return <FallbackComponent />;
  }

  return (
    <Suspense fallback={<FallbackComponent />}>
      <Component />
    </Suspense>
  );
}
```

**Step 3: 更新 App.tsx**

```typescript
// frontend/src/App.tsx
import { useState } from 'react';
import { DynamicComponent } from './renderer/DynamicLoader';

function App() {
  const [bookId, setBookId] = useState('');
  const [chapterIndex, setChapterIndex] = useState(0);
  const [showComponent, setShowComponent] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm p-4">
        <h1 className="text-2xl font-bold text-gray-900">BTW - Book To Web</h1>
        <p className="text-sm text-gray-500">MVP - Core Flow (Phase 1)</p>
      </header>

      <main className="p-4 max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Load Component</h2>

          <div className="flex gap-4 mb-4">
            <input
              type="text"
              placeholder="Book ID"
              value={bookId}
              onChange={(e) => setBookId(e.target.value)}
              className="flex-1 px-3 py-2 border rounded"
            />
            <input
              type="number"
              placeholder="Chapter Index"
              value={chapterIndex}
              onChange={(e) => setChapterIndex(parseInt(e.target.value))}
              className="w-32 px-3 py-2 border rounded"
            />
            <button
              onClick={() => setShowComponent(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Load
            </button>
          </div>

          {showComponent && bookId && (
            <DynamicComponent bookId={bookId} chapterIndex={chapterIndex} />
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">API Status</h2>
          <a
            href="/api/books"
            className="text-blue-600 hover:underline"
            target="_blank"
          >
            Check API
          </a>
        </div>
      </main>
    </div>
  );
}

export default App
```

**Step 4: 安装前端缺失依赖**

```bash
cd btw/frontend
npm install
# esbuild 已全局安装用于后端编译
```

**Step 5: 启动前后端并测试完整链路**

```bash
# 终端1: 启动后端
cd btw
python main.py

# 终端2: 启动前端
cd btw/frontend
npm run dev

# 浏览器访问 http://localhost:3000
# 测试上传书籍、查看章节、生成组件
```

**Step 6: Commit Phase 1**

```bash
git add .
git commit -m "feat(phase1): complete core flow - upload → parse → generate → render"
```

---

## Phase 2-4: 后续迭代（概要）

### Phase 2: 补齐其余 12 个 Agent

按优先级逐个实现：
1. **Critic** - 质量评审
2. **Stylist** - 风格统一
3. **Retriever** - 智能检索（替换Reader中的placeholder）
4. **Planner** - 交互蓝图
5. **Illustrator** - 配图生成
6. **Conductor** - 前端编排
7. **Companion** - 伴读交互
8. **Persona** - 角色扮演
9. **Translator** - 多语言
10. **Guardian** - 系统安全
11. **Evolver** - 经验沉淀
12. **Curator** - 知识管理

### Phase 3: 强化核心 Agent

- 真正的AI调用（替换placeholders）
- 更好的prompt工程
- Agent间协商机制
- 错误处理和重试

### Phase 4: 完善和优化

- 性能优化
- 错误边界
- 测试覆盖
- 文档完善

---

**当前阶段目标：完成 Phase 0 + Phase 1**（所有基础设施 + 核心5个Agent + 端到端打通）

实施优先级已按依赖排序，建议逐Task执行。
