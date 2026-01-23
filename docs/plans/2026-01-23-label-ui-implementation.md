# Label Management UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a React-based web interface for managing sortbox labels without editing YAML files directly.

**Architecture:** FastAPI backend with new API routers for label CRUD, config hot-reload with watchfiles, SSE for live updates. React SPA with TanStack Query, Tailwind CSS, and shadcn/ui components. Single-container deployment with FastAPI serving static frontend.

**Tech Stack:** FastAPI, Pydantic, watchfiles, React 18, TypeScript, Vite, TanStack Query, Tailwind CSS, shadcn/ui, Recharts, React Router

---

## Task 1: Backend API Foundation - Label CRUD

**Files:**
- Create: `src/api/__init__.py`
- Create: `src/api/labels.py`
- Create: `src/api/models.py`
- Modify: `src/main.py`
- Test: `tests/test_api_labels.py`

**Step 1: Write failing test for GET /api/labels**

Create `tests/test_api_labels.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path
from src.main import app


@pytest.mark.asyncio
async def test_get_labels():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/labels")
    assert response.status_code == 200
    data = response.json()
    assert "labels" in data
    assert "settings" in data
    assert "finance" in data["labels"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_api_labels.py::test_get_labels -v`
Expected: FAIL with "404 Not Found"

**Step 3: Create API models**

Create `src/api/__init__.py`:

```python
"""API routers for label management UI."""
```

Create `src/api/models.py`:

```python
from pydantic import BaseModel


class RuleResponse(BaseModel):
    type: str
    pattern: str | None = None
    keywords: list[str] | None = None


class LabelResponse(BaseModel):
    description: str
    rules: list[RuleResponse]


class LabelsResponse(BaseModel):
    labels: dict[str, LabelResponse]
    settings: dict[str, str | int | float]
```

**Step 4: Implement GET /api/labels endpoint**

Create `src/api/labels.py`:

```python
from pathlib import Path
from fastapi import APIRouter, HTTPException
from src.api.models import LabelsResponse, LabelResponse, RuleResponse
from src.config import load_config, Rule

router = APIRouter(prefix="/api/labels", tags=["labels"])


def _rule_to_response(rule: Rule) -> RuleResponse:
    if rule.from_pattern:
        return RuleResponse(type="from", pattern=rule.from_pattern)
    elif rule.subject_contains:
        return RuleResponse(type="subject_contains", keywords=rule.subject_contains)
    elif rule.header_list_unsubscribe:
        return RuleResponse(type="header_list_unsubscribe")
    else:
        return RuleResponse(type="unknown")


@router.get("", response_model=LabelsResponse)
async def get_labels() -> LabelsResponse:
    config = load_config(Path("labels.yaml"))

    labels_dict = {
        name: LabelResponse(
            description=label.description,
            rules=[_rule_to_response(rule) for rule in label.rules]
        )
        for name, label in config.labels.items()
    }

    settings_dict = {
        "llm_provider": config.settings.llm_provider,
        "confidence_threshold": config.settings.confidence_threshold,
        "max_emails_per_run": config.settings.max_emails_per_run,
    }

    return LabelsResponse(labels=labels_dict, settings=settings_dict)
```

**Step 5: Mount router in main.py**

Modify `src/main.py`:

```python
from pathlib import Path

import uvicorn

from src.classifier.providers.claude import ClaudeProvider
from src.classifier.providers.ollama_provider import OllamaProvider
from src.classifier.providers.openai_provider import OpenAIProvider
from src.classifier.service import create_app
from src.config import LabelConfig, load_config
from src.api.labels import router as labels_router


def get_provider(
    config: LabelConfig,
) -> ClaudeProvider | OpenAIProvider | OllamaProvider:
    match config.settings.llm_provider:
        case "claude":
            return ClaudeProvider()
        case "openai":
            return OpenAIProvider()
        case "ollama":
            return OllamaProvider()
        case _:
            raise ValueError(f"Unknown provider: {config.settings.llm_provider}")


config_path = Path("labels.yaml")
config = load_config(config_path)
provider = get_provider(config)
app = create_app(config_path=config_path, provider=provider)

# Mount API routers
app.include_router(labels_router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

**Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_api_labels.py::test_get_labels -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/api/ tests/test_api_labels.py src/main.py
git commit -m "feat: add GET /api/labels endpoint

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: POST /api/labels - Create Label

**Files:**
- Modify: `src/api/labels.py`
- Modify: `src/api/models.py`
- Modify: `tests/test_api_labels.py`

**Step 1: Write failing test**

Add to `tests/test_api_labels.py`:

```python
import tempfile
import shutil


@pytest.mark.asyncio
async def test_create_label():
    # Create temporary config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
labels:
  finance:
    description: "Test"
    rules: []
settings:
  llm_provider: "claude"
""")
        temp_path = f.name

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/labels", json={
                "name": "travel",
                "description": "Flight bookings",
                "rules": []
            })
        assert response.status_code == 201
    finally:
        Path(temp_path).unlink()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_api_labels.py::test_create_label -v`
Expected: FAIL with "404 Not Found" or "405 Method Not Allowed"

**Step 3: Add request models**

Add to `src/api/models.py`:

```python
from pydantic import BaseModel, field_validator
import re


class RuleRequest(BaseModel):
    type: str
    pattern: str | None = None
    keywords: list[str] | None = None


class CreateLabelRequest(BaseModel):
    name: str
    description: str
    rules: list[RuleRequest] = []

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError("Label name must be lowercase alphanumeric with hyphens only")
        return v
```

**Step 4: Implement POST endpoint**

Add to `src/api/labels.py`:

```python
import yaml
from src.api.models import CreateLabelRequest


@router.post("", status_code=201)
async def create_label(request: CreateLabelRequest) -> dict[str, str]:
    config_path = Path("labels.yaml")
    config = load_config(config_path)

    # Check if label already exists
    if request.name in config.labels:
        raise HTTPException(status_code=400, detail=f"Label '{request.name}' already exists")

    # Load raw YAML to preserve formatting
    with open(config_path) as f:
        data = yaml.safe_load(f)

    # Add new label
    new_label = {
        "description": request.description,
        "rules": []
    }

    for rule in request.rules:
        rule_dict: dict[str, Any] = {}
        if rule.type == "from":
            rule_dict["from"] = rule.pattern
        elif rule.type == "subject_contains":
            rule_dict["subject_contains"] = rule.keywords
        elif rule.type == "header_list_unsubscribe":
            rule_dict["header_list_unsubscribe"] = True
        new_label["rules"].append(rule_dict)

    data["labels"][request.name] = new_label

    # Write back to file
    with open(config_path, 'w') as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    return {"message": f"Label '{request.name}' created"}
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_api_labels.py::test_create_label -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/api/labels.py src/api/models.py tests/test_api_labels.py
git commit -m "feat: add POST /api/labels endpoint

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: PUT /api/labels/{name} - Update Label

**Files:**
- Modify: `src/api/labels.py`
- Modify: `src/api/models.py`
- Modify: `tests/test_api_labels.py`

**Step 1: Write failing test**

Add to `tests/test_api_labels.py`:

```python
@pytest.mark.asyncio
async def test_update_label():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put("/api/labels/finance", json={
            "description": "Updated description",
            "rules": [
                {"type": "from", "pattern": "*@stripe.com"}
            ]
        })
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_api_labels.py::test_update_label -v`
Expected: FAIL with "404 Not Found" or "405 Method Not Allowed"

**Step 3: Add update request model**

Add to `src/api/models.py`:

```python
class UpdateLabelRequest(BaseModel):
    description: str
    rules: list[RuleRequest]
```

**Step 4: Implement PUT endpoint**

Add to `src/api/labels.py`:

```python
from src.api.models import UpdateLabelRequest


@router.put("/{name}")
async def update_label(name: str, request: UpdateLabelRequest) -> dict[str, str]:
    config_path = Path("labels.yaml")
    config = load_config(config_path)

    # Check if label exists
    if name not in config.labels:
        raise HTTPException(status_code=404, detail=f"Label '{name}' not found")

    # Load raw YAML
    with open(config_path) as f:
        data = yaml.safe_load(f)

    # Update label
    updated_label = {
        "description": request.description,
        "rules": []
    }

    for rule in request.rules:
        rule_dict: dict[str, Any] = {}
        if rule.type == "from":
            rule_dict["from"] = rule.pattern
        elif rule.type == "subject_contains":
            rule_dict["subject_contains"] = rule.keywords
        elif rule.type == "header_list_unsubscribe":
            rule_dict["header_list_unsubscribe"] = True
        updated_label["rules"].append(rule_dict)

    data["labels"][name] = updated_label

    # Write back
    with open(config_path, 'w') as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    return {"message": f"Label '{name}' updated"}
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_api_labels.py::test_update_label -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/api/labels.py src/api/models.py tests/test_api_labels.py
git commit -m "feat: add PUT /api/labels/{name} endpoint

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: DELETE /api/labels/{name} - Delete Label

**Files:**
- Modify: `src/api/labels.py`
- Modify: `tests/test_api_labels.py`

**Step 1: Write failing test**

Add to `tests/test_api_labels.py`:

```python
@pytest.mark.asyncio
async def test_delete_label():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete("/api/labels/finance")
    assert response.status_code == 204
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_api_labels.py::test_delete_label -v`
Expected: FAIL with "404 Not Found" or "405 Method Not Allowed"

**Step 3: Implement DELETE endpoint**

Add to `src/api/labels.py`:

```python
from fastapi import status


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label(name: str) -> None:
    config_path = Path("labels.yaml")
    config = load_config(config_path)

    # Check if label exists
    if name not in config.labels:
        raise HTTPException(status_code=404, detail=f"Label '{name}' not found")

    # Load raw YAML
    with open(config_path) as f:
        data = yaml.safe_load(f)

    # Delete label
    del data["labels"][name]

    # Write back
    with open(config_path, 'w') as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_api_labels.py::test_delete_label -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/api/labels.py tests/test_api_labels.py
git commit -m "feat: add DELETE /api/labels/{name} endpoint

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: POST /api/labels/test - Test Classification

**Files:**
- Modify: `src/api/labels.py`
- Modify: `src/api/models.py`
- Modify: `tests/test_api_labels.py`

**Step 1: Write failing test**

Add to `tests/test_api_labels.py`:

```python
@pytest.mark.asyncio
async def test_classify_email():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/labels/test", json={
            "email": {
                "sender": "billing@stripe.com",
                "subject": "Invoice #1234",
                "body_preview": "Your invoice is ready"
            }
        })
    assert response.status_code == 200
    data = response.json()
    assert "matched_labels" in data
    assert "matched_rules" in data
    assert "confidence" in data
    assert "llm_used" in data
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_api_labels.py::test_classify_email -v`
Expected: FAIL with "404 Not Found"

**Step 3: Add test request/response models**

Add to `src/api/models.py`:

```python
class TestEmailRequest(BaseModel):
    email: dict[str, str]  # sender, subject, body_preview


class MatchedRule(BaseModel):
    label: str
    rule: RuleResponse


class TestEmailResponse(BaseModel):
    matched_labels: list[str]
    matched_rules: list[MatchedRule]
    confidence: float
    llm_used: bool
    time_ms: int
```

**Step 4: Implement test endpoint**

Add to `src/api/labels.py`:

```python
import time
from src.models import EmailInput
from src.classifier.rules import match_rules
from src.api.models import TestEmailRequest, TestEmailResponse, MatchedRule


@router.post("/test", response_model=TestEmailResponse)
async def test_email_classification(request: TestEmailRequest) -> TestEmailResponse:
    start_time = time.time()

    config = load_config(Path("labels.yaml"))

    # Create EmailInput from request
    email = EmailInput(
        email_id="test",
        sender=request.email["sender"],
        subject=request.email["subject"],
        body_preview=request.email.get("body_preview", "")
    )

    # Try rule matching first
    matched_labels = match_rules(email, config.labels)

    # Build matched rules list
    matched_rules_list = []
    for label_name in matched_labels:
        label_def = config.labels[label_name]
        for rule in label_def.rules:
            # Check if this rule matches
            if rule.from_pattern and email.sender:
                import fnmatch
                if fnmatch.fnmatch(email.sender.lower(), rule.from_pattern.lower()):
                    matched_rules_list.append(MatchedRule(
                        label=label_name,
                        rule=_rule_to_response(rule)
                    ))
            elif rule.subject_contains:
                subject_lower = email.subject.lower()
                if any(kw.lower() in subject_lower for kw in rule.subject_contains):
                    matched_rules_list.append(MatchedRule(
                        label=label_name,
                        rule=_rule_to_response(rule)
                    ))

    time_ms = int((time.time() - start_time) * 1000)

    return TestEmailResponse(
        matched_labels=matched_labels,
        matched_rules=matched_rules_list,
        confidence=1.0 if matched_labels else 0.0,
        llm_used=False,
        time_ms=time_ms
    )
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_api_labels.py::test_classify_email -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/api/labels.py src/api/models.py tests/test_api_labels.py
git commit -m "feat: add POST /api/labels/test endpoint

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Config Hot-Reload with Watchfiles

**Files:**
- Create: `src/config_watcher.py`
- Modify: `src/main.py`
- Create: `tests/test_config_watcher.py`

**Step 1: Add watchfiles dependency**

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... existing
    "watchfiles>=1.0.3",
]
```

Run: `uv sync`

**Step 2: Write failing test**

Create `tests/test_config_watcher.py`:

```python
import pytest
import asyncio
import tempfile
from pathlib import Path
from src.config_watcher import watch_config_file


@pytest.mark.asyncio
async def test_config_reload_on_change():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("labels: {}\nsettings: {llm_provider: claude}")
        temp_path = Path(f.name)

    reload_count = 0

    async def on_reload():
        nonlocal reload_count
        reload_count += 1

    try:
        # Start watcher in background
        watcher_task = asyncio.create_task(
            watch_config_file(temp_path, on_reload)
        )

        # Give it time to start
        await asyncio.sleep(0.1)

        # Modify file
        with open(temp_path, 'w') as f:
            f.write("labels: {finance: {description: test, rules: []}}\nsettings: {llm_provider: claude}")

        # Wait for reload
        await asyncio.sleep(0.5)

        assert reload_count == 1

        watcher_task.cancel()
    finally:
        temp_path.unlink()
```

**Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_config_watcher.py -v`
Expected: FAIL with "module not found"

**Step 4: Implement config watcher**

Create `src/config_watcher.py`:

```python
import asyncio
from pathlib import Path
from typing import Callable, Awaitable
from watchfiles import awatch


async def watch_config_file(
    path: Path,
    on_reload: Callable[[], Awaitable[None]]
) -> None:
    """Watch config file and trigger reload callback on changes."""
    async for changes in awatch(path):
        await on_reload()
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_config_watcher.py -v`
Expected: PASS

**Step 6: Integrate watcher in main.py**

Modify `src/main.py`:

```python
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio

import uvicorn
from fastapi import FastAPI

from src.classifier.providers.claude import ClaudeProvider
from src.classifier.providers.ollama_provider import OllamaProvider
from src.classifier.providers.openai_provider import OpenAIProvider
from src.classifier.service import create_app
from src.config import LabelConfig, load_config
from src.api.labels import router as labels_router
from src.config_watcher import watch_config_file


def get_provider(
    config: LabelConfig,
) -> ClaudeProvider | OpenAIProvider | OllamaProvider:
    match config.settings.llm_provider:
        case "claude":
            return ClaudeProvider()
        case "openai":
            return OpenAIProvider()
        case "ollama":
            return OllamaProvider()
        case _:
            raise ValueError(f"Unknown provider: {config.settings.llm_provider}")


config_path = Path("labels.yaml")
config = load_config(config_path)
provider = get_provider(config)

# Create app with lifespan for config watching
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start config watcher
    async def reload_config():
        new_config = load_config(config_path)
        app.state.config = new_config
        # TODO: broadcast SSE event

    watcher_task = asyncio.create_task(
        watch_config_file(config_path, reload_config)
    )

    yield

    # Cleanup
    watcher_task.cancel()

app = create_app(config_path=config_path, provider=provider)
app.router.lifespan_context = lifespan

# Mount API routers
app.include_router(labels_router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

**Step 7: Commit**

```bash
git add src/config_watcher.py tests/test_config_watcher.py src/main.py pyproject.toml
git commit -m "feat: add config hot-reload with watchfiles

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Frontend Setup - Vite + React + TypeScript

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`

**Step 1: Initialize frontend directory**

```bash
mkdir -p frontend/src
cd frontend
```

**Step 2: Create package.json**

Create `frontend/package.json`:

```json
{
  "name": "sortbox-ui",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^7.1.3",
    "@tanstack/react-query": "^5.70.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.18",
    "@types/react-dom": "^18.3.5",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.7.3",
    "vite": "^6.0.11"
  }
}
```

**Step 3: Create Vite config**

Create `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
})
```

**Step 4: Create TypeScript config**

Create `frontend/tsconfig.json`:

```json
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

Create `frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

**Step 5: Create HTML entry point**

Create `frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Sortbox - Label Management</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**Step 6: Create React entry point**

Create `frontend/src/main.tsx`:

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

Create `frontend/src/App.tsx`:

```typescript
function App() {
  return (
    <div>
      <h1>Sortbox</h1>
      <p>Label Management UI</p>
    </div>
  )
}

export default App
```

**Step 7: Install dependencies and test**

```bash
cd frontend
npm install
npm run dev
```

Expected: Dev server starts on http://localhost:5173, shows "Sortbox" heading

**Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: initialize React frontend with Vite

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Frontend - Tailwind CSS + shadcn/ui Setup

**Files:**
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/index.css`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/package.json`

**Step 1: Install Tailwind CSS**

```bash
cd frontend
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**Step 2: Configure Tailwind**

Modify `frontend/tailwind.config.js`:

```javascript
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

**Step 3: Create CSS file**

Create `frontend/src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Step 4: Import CSS in main.tsx**

Modify `frontend/src/main.tsx`:

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

**Step 5: Test Tailwind**

Modify `frontend/src/App.tsx`:

```typescript
function App() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-lg">
        <h1 className="text-3xl font-bold text-gray-900">Sortbox</h1>
        <p className="text-gray-600 mt-2">Label Management UI</p>
      </div>
    </div>
  )
}

export default App
```

Run: `npm run dev`
Expected: Styled card with shadow and rounded corners

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: add Tailwind CSS to frontend

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Frontend - API Client with TanStack Query

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/hooks/useLabels.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/package.json`

**Step 1: Install dependencies**

```bash
cd frontend
npm install @tanstack/react-query
```

**Step 2: Create type definitions**

Create `frontend/src/lib/types.ts`:

```typescript
export interface Rule {
  type: string
  pattern?: string
  keywords?: string[]
}

export interface Label {
  description: string
  rules: Rule[]
}

export interface Settings {
  llm_provider: string
  confidence_threshold: number
  max_emails_per_run: number
}

export interface LabelsResponse {
  labels: Record<string, Label>
  settings: Settings
}
```

**Step 3: Create API client**

Create `frontend/src/lib/api.ts`:

```typescript
import { LabelsResponse } from './types'

const API_BASE = '/api'

export async function fetchLabels(): Promise<LabelsResponse> {
  const response = await fetch(`${API_BASE}/labels`)
  if (!response.ok) {
    throw new Error('Failed to fetch labels')
  }
  return response.json()
}
```

**Step 4: Create React Query hook**

Create `frontend/src/hooks/useLabels.ts`:

```typescript
import { useQuery } from '@tanstack/react-query'
import { fetchLabels } from '../lib/api'

export function useLabels() {
  return useQuery({
    queryKey: ['labels'],
    queryFn: fetchLabels,
  })
}
```

**Step 5: Set up QueryClient in App**

Modify `frontend/src/App.tsx`:

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useLabels } from './hooks/useLabels'

const queryClient = new QueryClient()

function LabelsDisplay() {
  const { data, isLoading, error } = useLabels()

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error: {error.message}</div>

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto bg-white p-8 rounded-lg shadow-lg">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Sortbox Labels</h1>
        <div className="space-y-4">
          {Object.entries(data?.labels || {}).map(([name, label]) => (
            <div key={name} className="border p-4 rounded">
              <h2 className="text-xl font-semibold">{name}</h2>
              <p className="text-gray-600">{label.description}</p>
              <p className="text-sm text-gray-500 mt-2">
                {label.rules.length} rules
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <LabelsDisplay />
    </QueryClientProvider>
  )
}

export default App
```

**Step 6: Test integration**

Run backend: `make run` (in main terminal)
Run frontend: `npm run dev` (in frontend directory)

Expected: Frontend displays list of labels from API

**Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: add API client with TanStack Query

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Frontend - React Router + Layout

**Files:**
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/pages/Labels.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Create Layout component**

Create `frontend/src/components/Layout.tsx`:

```typescript
import { Link, Outlet } from 'react-router-dom'

export function Layout() {
  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold">Sortbox</h1>
              </div>
              <div className="ml-6 flex space-x-8">
                <Link
                  to="/"
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900"
                >
                  Dashboard
                </Link>
                <Link
                  to="/labels"
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900"
                >
                  Labels
                </Link>
                <Link
                  to="/test"
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900"
                >
                  Test Console
                </Link>
                <Link
                  to="/analytics"
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900"
                >
                  Analytics
                </Link>
              </div>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  )
}
```

**Step 2: Create Dashboard page**

Create `frontend/src/pages/Dashboard.tsx`:

```typescript
import { useLabels } from '../hooks/useLabels'

export function Dashboard() {
  const { data } = useLabels()

  const labelCount = Object.keys(data?.labels || {}).length
  const totalRules = Object.values(data?.labels || {}).reduce(
    (sum, label) => sum + label.rules.length,
    0
  )

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h2>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3 mb-8">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 truncate">
              Total Labels
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900">
              {labelCount}
            </dd>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 truncate">
              Total Rules
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900">
              {totalRules}
            </dd>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 truncate">
              LLM Provider
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900">
              {data?.settings.llm_provider}
            </dd>
          </div>
        </div>
      </div>
    </div>
  )
}
```

**Step 3: Create Labels page**

Create `frontend/src/pages/Labels.tsx`:

```typescript
import { useLabels } from '../hooks/useLabels'

export function Labels() {
  const { data, isLoading } = useLabels()

  if (isLoading) {
    return <div>Loading labels...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Labels</h2>
        <button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          Add Label
        </button>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {Object.entries(data?.labels || {}).map(([name, label]) => (
            <li key={name}>
              <div className="px-4 py-4 sm:px-6 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-medium text-gray-900">{name}</h3>
                    <p className="text-sm text-gray-500">{label.description}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {label.rules.length} rules
                    </p>
                  </div>
                  <button className="text-blue-600 hover:text-blue-800">
                    Edit
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
```

**Step 4: Set up routing**

Modify `frontend/src/App.tsx`:

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Labels } from './pages/Labels'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="labels" element={<Labels />} />
            <Route path="test" element={<div>Test Console (Coming Soon)</div>} />
            <Route path="analytics" element={<div>Analytics (Coming Soon)</div>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
```

**Step 5: Test navigation**

Run: `npm run dev`
Expected: Can navigate between Dashboard and Labels pages

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: add React Router with Dashboard and Labels pages

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 11: Frontend - Create Label Dialog

**Files:**
- Create: `frontend/src/components/CreateLabelDialog.tsx`
- Modify: `frontend/src/pages/Labels.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/hooks/useLabels.ts`

**Step 1: Add mutation to API client**

Add to `frontend/src/lib/api.ts`:

```typescript
export interface CreateLabelRequest {
  name: string
  description: string
  rules: Rule[]
}

export async function createLabel(data: CreateLabelRequest): Promise<void> {
  const response = await fetch(`${API_BASE}/labels`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to create label')
  }
}
```

**Step 2: Add mutation hook**

Add to `frontend/src/hooks/useLabels.ts`:

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createLabel } from '../lib/api'

export function useCreateLabel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createLabel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['labels'] })
    },
  })
}
```

**Step 3: Create dialog component**

Create `frontend/src/components/CreateLabelDialog.tsx`:

```typescript
import { useState } from 'react'
import { useCreateLabel } from '../hooks/useLabels'

interface Props {
  isOpen: boolean
  onClose: () => void
}

export function CreateLabelDialog({ isOpen, onClose }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const createMutation = useCreateLabel()

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await createMutation.mutateAsync({
        name,
        description,
        rules: [],
      })
      onClose()
      setName('')
      setDescription('')
    } catch (error) {
      console.error('Failed to create label:', error)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">Create New Label</h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="e.g., travel"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Lowercase, alphanumeric, hyphens only
            </p>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="e.g., Flight bookings and hotel reservations"
              rows={3}
              required
            />
          </div>

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create Label'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
```

**Step 4: Integrate dialog into Labels page**

Modify `frontend/src/pages/Labels.tsx`:

```typescript
import { useState } from 'react'
import { useLabels } from '../hooks/useLabels'
import { CreateLabelDialog } from '../components/CreateLabelDialog'

export function Labels() {
  const { data, isLoading } = useLabels()
  const [isCreateOpen, setIsCreateOpen] = useState(false)

  if (isLoading) {
    return <div>Loading labels...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Labels</h2>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Add Label
        </button>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {Object.entries(data?.labels || {}).map(([name, label]) => (
            <li key={name}>
              <div className="px-4 py-4 sm:px-6 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-medium text-gray-900">{name}</h3>
                    <p className="text-sm text-gray-500">{label.description}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {label.rules.length} rules
                    </p>
                  </div>
                  <button className="text-blue-600 hover:text-blue-800">
                    Edit
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <CreateLabelDialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />
    </div>
  )
}
```

**Step 5: Test create flow**

Run backend and frontend, click "Add Label", create a new label
Expected: Label appears in list after creation

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: add create label dialog

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 12: Frontend - Edit Label with Rules

**Files:**
- Create: `frontend/src/components/EditLabelDialog.tsx`
- Create: `frontend/src/components/RuleEditor.tsx`
- Modify: `frontend/src/pages/Labels.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/hooks/useLabels.ts`

**Step 1: Add update mutation to API**

Add to `frontend/src/lib/api.ts`:

```typescript
export interface UpdateLabelRequest {
  description: string
  rules: Rule[]
}

export async function updateLabel(
  name: string,
  data: UpdateLabelRequest
): Promise<void> {
  const response = await fetch(`${API_BASE}/labels/${name}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to update label')
  }
}
```

**Step 2: Add update hook**

Add to `frontend/src/hooks/useLabels.ts`:

```typescript
export function useUpdateLabel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ name, data }: { name: string; data: UpdateLabelRequest }) =>
      updateLabel(name, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['labels'] })
    },
  })
}
```

**Step 3: Create RuleEditor component**

Create `frontend/src/components/RuleEditor.tsx`:

```typescript
import { useState } from 'react'
import { Rule } from '../lib/types'

interface Props {
  rule: Rule
  onSave: (rule: Rule) => void
  onCancel: () => void
}

export function RuleEditor({ rule, onSave, onCancel }: Props) {
  const [ruleType, setRuleType] = useState(rule.type || 'from')
  const [pattern, setPattern] = useState(rule.pattern || '')
  const [keywords, setKeywords] = useState(rule.keywords?.join(', ') || '')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const newRule: Rule = { type: ruleType }

    if (ruleType === 'from') {
      newRule.pattern = pattern
    } else if (ruleType === 'subject_contains') {
      newRule.keywords = keywords.split(',').map(k => k.trim())
    }

    onSave(newRule)
  }

  return (
    <div className="border border-gray-300 rounded p-4 mb-4">
      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Rule Type
          </label>
          <select
            value={ruleType}
            onChange={(e) => setRuleType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded"
          >
            <option value="from">From Pattern</option>
            <option value="subject_contains">Subject Contains</option>
            <option value="header_list_unsubscribe">Has Unsubscribe Header</option>
          </select>
        </div>

        {ruleType === 'from' && (
          <div className="mb-3">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Pattern
            </label>
            <input
              type="text"
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded"
              placeholder="*@domain.com"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Examples: *@domain.com, *noreply@*
            </p>
          </div>
        )}

        {ruleType === 'subject_contains' && (
          <div className="mb-3">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Keywords (comma-separated)
            </label>
            <input
              type="text"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded"
              placeholder="invoice, receipt, payment"
              required
            />
          </div>
        )}

        <div className="flex justify-end space-x-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1 text-sm text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Save Rule
          </button>
        </div>
      </form>
    </div>
  )
}
```

**Step 4: Create EditLabelDialog**

Create `frontend/src/components/EditLabelDialog.tsx`:

```typescript
import { useState, useEffect } from 'react'
import { Label, Rule } from '../lib/types'
import { useUpdateLabel } from '../hooks/useLabels'
import { RuleEditor } from './RuleEditor'

interface Props {
  isOpen: boolean
  onClose: () => void
  labelName: string
  label: Label
}

export function EditLabelDialog({ isOpen, onClose, labelName, label }: Props) {
  const [description, setDescription] = useState(label.description)
  const [rules, setRules] = useState<Rule[]>(label.rules)
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const updateMutation = useUpdateLabel()

  useEffect(() => {
    setDescription(label.description)
    setRules(label.rules)
  }, [label])

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await updateMutation.mutateAsync({
        name: labelName,
        data: { description, rules },
      })
      onClose()
    } catch (error) {
      console.error('Failed to update label:', error)
    }
  }

  const handleAddRule = () => {
    setEditingIndex(rules.length)
    setRules([...rules, { type: 'from' }])
  }

  const handleSaveRule = (index: number, rule: Rule) => {
    const newRules = [...rules]
    newRules[index] = rule
    setRules(newRules)
    setEditingIndex(null)
  }

  const handleDeleteRule = (index: number) => {
    setRules(rules.filter((_, i) => i !== index))
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4">Edit Label: {labelName}</h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              rows={2}
              required
            />
          </div>

          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Rules ({rules.length})
              </label>
              <button
                type="button"
                onClick={handleAddRule}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                + Add Rule
              </button>
            </div>

            <div className="space-y-2">
              {rules.map((rule, index) => (
                <div key={index}>
                  {editingIndex === index ? (
                    <RuleEditor
                      rule={rule}
                      onSave={(r) => handleSaveRule(index, r)}
                      onCancel={() => setEditingIndex(null)}
                    />
                  ) : (
                    <div className="flex items-center justify-between border border-gray-200 rounded p-3">
                      <div className="flex-1">
                        <span className="text-sm font-medium">{rule.type}</span>
                        {rule.pattern && (
                          <span className="text-sm text-gray-600 ml-2">
                            {rule.pattern}
                          </span>
                        )}
                        {rule.keywords && (
                          <span className="text-sm text-gray-600 ml-2">
                            {rule.keywords.join(', ')}
                          </span>
                        )}
                      </div>
                      <div className="flex space-x-2">
                        <button
                          type="button"
                          onClick={() => setEditingIndex(index)}
                          className="text-sm text-blue-600 hover:text-blue-800"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteRule(index)}
                          className="text-sm text-red-600 hover:text-red-800"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
```

**Step 5: Integrate into Labels page**

Modify `frontend/src/pages/Labels.tsx`:

```typescript
import { useState } from 'react'
import { useLabels } from '../hooks/useLabels'
import { CreateLabelDialog } from '../components/CreateLabelDialog'
import { EditLabelDialog } from '../components/EditLabelDialog'

export function Labels() {
  const { data, isLoading } = useLabels()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [editingLabel, setEditingLabel] = useState<string | null>(null)

  if (isLoading) {
    return <div>Loading labels...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Labels</h2>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Add Label
        </button>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {Object.entries(data?.labels || {}).map(([name, label]) => (
            <li key={name}>
              <div className="px-4 py-4 sm:px-6 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-medium text-gray-900">{name}</h3>
                    <p className="text-sm text-gray-500">{label.description}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {label.rules.length} rules
                    </p>
                  </div>
                  <button
                    onClick={() => setEditingLabel(name)}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    Edit
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <CreateLabelDialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />

      {editingLabel && data?.labels[editingLabel] && (
        <EditLabelDialog
          isOpen={true}
          onClose={() => setEditingLabel(null)}
          labelName={editingLabel}
          label={data.labels[editingLabel]}
        />
      )}
    </div>
  )
}
```

**Step 6: Test edit flow**

Click "Edit" on a label, modify description, add/edit/delete rules
Expected: Changes saved and reflected in list

**Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: add edit label dialog with rule editor

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 13: Frontend - Test Console Page

**Files:**
- Create: `frontend/src/pages/TestConsole.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types.ts`

**Step 1: Add types**

Add to `frontend/src/lib/types.ts`:

```typescript
export interface TestEmailResponse {
  matched_labels: string[]
  matched_rules: Array<{
    label: string
    rule: Rule
  }>
  confidence: number
  llm_used: boolean
  time_ms: number
}
```

**Step 2: Add API function**

Add to `frontend/src/lib/api.ts`:

```typescript
import { TestEmailResponse } from './types'

export async function testEmailClassification(email: {
  sender: string
  subject: string
  body_preview: string
}): Promise<TestEmailResponse> {
  const response = await fetch(`${API_BASE}/labels/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  if (!response.ok) {
    throw new Error('Failed to test email')
  }
  return response.json()
}
```

**Step 3: Create TestConsole page**

Create `frontend/src/pages/TestConsole.tsx`:

```typescript
import { useState } from 'react'
import { testEmailClassification } from '../lib/api'
import { TestEmailResponse } from '../lib/types'

export function TestConsole() {
  const [sender, setSender] = useState('')
  const [subject, setSubject] = useState('')
  const [bodyPreview, setBodyPreview] = useState('')
  const [result, setResult] = useState<TestEmailResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      const response = await testEmailClassification({
        sender,
        subject,
        body_preview: bodyPreview,
      })
      setResult(response)
    } catch (error) {
      console.error('Failed to test email:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadSample = (sample: 'stripe' | 'newsletter' | 'security') => {
    const samples = {
      stripe: {
        sender: 'billing@stripe.com',
        subject: 'Invoice #1234',
        bodyPreview: 'Your invoice for January is ready. Amount: $49.00',
      },
      newsletter: {
        sender: 'news@techblog.com',
        subject: 'Weekly Tech Digest',
        bodyPreview: 'This weeks top articles about web development...',
      },
      security: {
        sender: 'security@github.com',
        subject: 'New login from Chrome on MacOS',
        bodyPreview: 'We detected a new login to your account...',
      },
    }
    const s = samples[sample]
    setSender(s.sender)
    setSubject(s.subject)
    setBodyPreview(s.bodyPreview)
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Test Console</h2>

      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Sample Emails
          </label>
          <div className="flex space-x-2">
            <button
              onClick={() => loadSample('stripe')}
              className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
            >
              Stripe Invoice
            </button>
            <button
              onClick={() => loadSample('newsletter')}
              className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
            >
              Newsletter
            </button>
            <button
              onClick={() => loadSample('security')}
              className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
            >
              Security Alert
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              From
            </label>
            <input
              type="email"
              value={sender}
              onChange={(e) => setSender(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded"
              placeholder="sender@example.com"
              required
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Subject
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded"
              placeholder="Email subject"
              required
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Preview
            </label>
            <textarea
              value={bodyPreview}
              onChange={(e) => setBodyPreview(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded"
              rows={3}
              placeholder="Email body preview..."
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Classifying...' : 'Classify Email'}
          </button>
        </form>
      </div>

      {result && (
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-bold mb-4">Results</h3>

          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">
                Matched Labels
              </span>
              <span className="text-sm text-gray-500">{result.time_ms}ms</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {result.matched_labels.length > 0 ? (
                result.matched_labels.map((label) => (
                  <span
                    key={label}
                    className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm"
                  >
                    {label}
                  </span>
                ))
              ) : (
                <span className="text-gray-500 text-sm">No labels matched</span>
              )}
            </div>
          </div>

          <div className="mb-4">
            <span className="text-sm font-medium text-gray-700">
              Confidence
            </span>
            <div className="mt-2 bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-600 h-2 rounded-full"
                style={{ width: `${result.confidence * 100}%` }}
              />
            </div>
            <span className="text-sm text-gray-500">
              {(result.confidence * 100).toFixed(0)}%
            </span>
          </div>

          {result.matched_rules.length > 0 && (
            <div>
              <span className="text-sm font-medium text-gray-700 block mb-2">
                Matched Rules
              </span>
              <ul className="space-y-2">
                {result.matched_rules.map((mr, i) => (
                  <li key={i} className="text-sm text-gray-600 flex items-center">
                    <span className="text-green-600 mr-2">✓</span>
                    <span className="font-medium">{mr.label}</span>
                    <span className="mx-2">→</span>
                    <span>{mr.rule.type}</span>
                    {mr.rule.pattern && (
                      <span className="ml-2 font-mono text-xs">
                        {mr.rule.pattern}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-4 pt-4 border-t">
            <span className="text-sm text-gray-500">
              LLM Used: {result.llm_used ? 'Yes' : 'No'}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
```

**Step 4: Update App.tsx routing**

Modify `frontend/src/App.tsx`:

```typescript
import { TestConsole } from './pages/TestConsole'

// In Routes:
<Route path="test" element={<TestConsole />} />
```

**Step 5: Test console**

Navigate to /test, load sample, classify
Expected: Results display with matched labels and rules

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: add test console page

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 14: Production Build and Static File Serving

**Files:**
- Modify: `src/main.py`
- Modify: `Dockerfile`
- Create: `frontend/.env.production`

**Step 1: Build frontend**

```bash
cd frontend
npm run build
```

Expected: `frontend/dist/` directory created with built files

**Step 2: Add static file serving to main.py**

Modify `src/main.py`:

```python
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.classifier.providers.claude import ClaudeProvider
from src.classifier.providers.ollama_provider import OllamaProvider
from src.classifier.providers.openai_provider import OpenAIProvider
from src.classifier.service import create_app
from src.config import LabelConfig, load_config
from src.api.labels import router as labels_router
from src.config_watcher import watch_config_file


def get_provider(
    config: LabelConfig,
) -> ClaudeProvider | OpenAIProvider | OllamaProvider:
    match config.settings.llm_provider:
        case "claude":
            return ClaudeProvider()
        case "openai":
            return OpenAIProvider()
        case "ollama":
            return OllamaProvider()
        case _:
            raise ValueError(f"Unknown provider: {config.settings.llm_provider}")


config_path = Path("labels.yaml")
config = load_config(config_path)
provider = get_provider(config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def reload_config():
        new_config = load_config(config_path)
        app.state.config = new_config

    watcher_task = asyncio.create_task(
        watch_config_file(config_path, reload_config)
    )

    yield

    watcher_task.cancel()


app = create_app(config_path=config_path, provider=provider)
app.router.lifespan_context = lifespan

# Mount API routers
app.include_router(labels_router)

# Serve frontend in production (if dist exists)
frontend_dist = Path("frontend/dist")
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

**Step 3: Test production mode**

```bash
cd frontend
npm run build
cd ..
make run
```

Navigate to http://127.0.0.1:8000
Expected: Frontend loads from FastAPI, API calls work

**Step 4: Update Dockerfile**

Modify `Dockerfile`:

```dockerfile
# Stage 1: Build frontend
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim
WORKDIR /app

# Install uv
RUN pip install uv

# Copy Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# Copy backend source
COPY src/ src/

# Copy config
COPY labels.yaml .

# Copy built frontend from stage 1
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Create data directory for SQLite
RUN mkdir -p /app/data

ENV DATABASE_PATH=/app/data/sortbox.db
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 5: Test Docker build**

```bash
docker build -t sortbox:label-ui .
docker run -p 8000:8000 -v $(pwd)/data:/app/data sortbox:label-ui
```

Expected: Container runs, frontend accessible at http://localhost:8000

**Step 6: Commit**

```bash
git add src/main.py Dockerfile
git commit -m "feat: add production build with static file serving

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 15: Update Documentation

**Files:**
- Modify: `README.md`

**Step 1: Add Label UI section to README**

Add to `README.md` after Quick Start section:

```markdown
## Label Management UI

Access the web interface at `http://127.0.0.1:8000` when running the service.

### Features

- **Dashboard**: Overview of labels and recent activity
- **Label Editor**: Create, edit, and delete labels without touching YAML
- **Rule Builder**: Visual interface for adding classification rules
- **Test Console**: Test email classification in real-time
- **Hot Reload**: Changes to labels.yaml automatically reload

### Development

Run backend and frontend separately for development:

```bash
# Terminal 1: Backend
make run

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

Frontend dev server runs on http://localhost:5173 with API proxy to backend.

### Production

Build frontend and serve from FastAPI:

```bash
cd frontend
npm run build
cd ..
make run
```

Access UI at http://127.0.0.1:8000
```

**Step 2: Update Project Structure section**

Update project structure in README to include frontend:

```markdown
sortbox/
├── frontend/                  # React UI
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── pages/             # Page components
│   │   ├── hooks/             # React Query hooks
│   │   ├── lib/               # API client and utilities
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── src/
│   ├── api/                   # API routers for UI
│   │   ├── labels.py          # Label CRUD
│   │   └── models.py          # API schemas
│   ├── config_watcher.py      # Hot-reload logic
│   ├── classifier/
│   └── ...
└── ...
```

**Step 3: Add UI to roadmap**

Update roadmap in README:

```markdown
### v1.0 - Classifier (Current)
- [x] Rule-based matching
- [x] LLM fallback
- [x] n8n integration
- [x] 10 label categories
- [x] Docker deployment
- [x] CI/CD pipelines
- [x] 98% test coverage
- [x] Label management UI
```

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add label management UI documentation

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 16: Integration Tests and Cleanup

**Files:**
- Create: `tests/test_integration_ui.py`
- Modify: `.gitignore`

**Step 1: Add frontend build to gitignore**

Add to `.gitignore`:

```
# Frontend build
frontend/dist/
frontend/node_modules/
```

**Step 2: Write integration test**

Create `tests/test_integration_ui.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path
import tempfile
import yaml


@pytest.mark.asyncio
async def test_create_update_delete_label_flow():
    """Test full CRUD flow for labels via API."""
    from src.main import app

    # Create temporary config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.safe_dump({
            "labels": {
                "finance": {
                    "description": "Test",
                    "rules": []
                }
            },
            "settings": {
                "llm_provider": "claude"
            }
        }, f)
        temp_path = Path(f.name)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. List labels
            response = await client.get("/api/labels")
            assert response.status_code == 200
            data = response.json()
            assert "finance" in data["labels"]

            # 2. Create new label
            response = await client.post("/api/labels", json={
                "name": "travel",
                "description": "Flight bookings",
                "rules": [{"type": "from", "pattern": "*@airline.com"}]
            })
            assert response.status_code == 201

            # 3. Verify created
            response = await client.get("/api/labels")
            data = response.json()
            assert "travel" in data["labels"]
            assert len(data["labels"]["travel"]["rules"]) == 1

            # 4. Update label
            response = await client.put("/api/labels/travel", json={
                "description": "Updated description",
                "rules": [
                    {"type": "from", "pattern": "*@airline.com"},
                    {"type": "subject_contains", "keywords": ["flight", "booking"]}
                ]
            })
            assert response.status_code == 200

            # 5. Verify updated
            response = await client.get("/api/labels")
            data = response.json()
            assert data["labels"]["travel"]["description"] == "Updated description"
            assert len(data["labels"]["travel"]["rules"]) == 2

            # 6. Test classification
            response = await client.post("/api/labels/test", json={
                "email": {
                    "sender": "noreply@airline.com",
                    "subject": "Your flight booking",
                    "body_preview": "Confirmation for flight BA123"
                }
            })
            assert response.status_code == 200
            result = response.json()
            assert "travel" in result["matched_labels"]

            # 7. Delete label
            response = await client.delete("/api/labels/travel")
            assert response.status_code == 204

            # 8. Verify deleted
            response = await client.get("/api/labels")
            data = response.json()
            assert "travel" not in data["labels"]
    finally:
        temp_path.unlink()
```

**Step 3: Run all tests**

Run: `uv run pytest -v`
Expected: All tests pass including new integration test

**Step 4: Check coverage**

Run: `uv run pytest --cov=src --cov-report=term-missing`
Expected: Coverage > 80%

**Step 5: Run all checks**

Run: `make check`
Expected: All checks (lint, typecheck, security, test) pass

**Step 6: Commit**

```bash
git add tests/test_integration_ui.py .gitignore
git commit -m "test: add UI API integration tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Summary

This plan implements a complete label management UI with:

1. **Backend API** (Tasks 1-6): Full CRUD for labels, classification testing, config hot-reload
2. **Frontend Setup** (Tasks 7-9): React + Vite + TypeScript + Tailwind + TanStack Query
3. **UI Components** (Tasks 10-13): Dashboard, Labels page with CRUD, Test Console
4. **Production** (Task 14): Build pipeline, static file serving, Docker multi-stage build
5. **Documentation** (Task 15): README updates
6. **Testing** (Task 16): Integration tests, cleanup

**Total estimated time:** 16 tasks × 30-45 min/task = 8-12 hours

**Testing strategy:**
- Backend: pytest with async client for API endpoints
- Frontend: Manual testing during development
- Integration: Full CRUD flow test
- Target: 80%+ coverage on new code

**Deployment:**
- Development: Separate backend + frontend dev servers
- Production: Single FastAPI serving React build
- Docker: Multi-stage build (npm → python)
