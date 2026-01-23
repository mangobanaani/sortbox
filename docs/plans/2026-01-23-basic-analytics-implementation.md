# Basic Analytics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add lightweight analytics tracking and dashboard to monitor email classification patterns.

**Architecture:** SQLite database to track classification events, backend API endpoint to query aggregated data, React frontend dashboard with charts and stats.

**Tech Stack:** Python 3.12, SQLite3, FastAPI, React 18, TypeScript, Recharts, TanStack Query, Tailwind CSS

---

## Task 1: Database Layer - Schema and Basic Functions

**Files:**
- Create: `src/database.py`
- Create: `tests/test_database.py`

**Step 1: Write failing test for database initialization**

Create `tests/test_database.py`:

```python
import pytest
import tempfile
from pathlib import Path
from src.database import init_database, get_connection


def test_init_database_creates_table():
    """Test that database initialization creates the classification_events table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Override DATABASE_PATH for test
        import src.database
        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Verify table exists
            with get_connection() as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='classification_events'"
                )
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == "classification_events"
        finally:
            src.database.DATABASE_PATH = original_path
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_database.py::test_init_database_creates_table -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.database'"

**Step 3: Create database module with init function**

Create `src/database.py`:

```python
"""Database layer for analytics tracking."""
from pathlib import Path
from datetime import datetime
import sqlite3
from contextlib import contextmanager

DATABASE_PATH = Path("data/sortbox.db")


def init_database() -> None:
    """Initialize database and create tables if needed."""
    DATABASE_PATH.parent.mkdir(exist_ok=True)

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS classification_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                label TEXT NOT NULL,
                method TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON classification_events(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_label ON classification_events(label)")
        conn.commit()


@contextmanager
def get_connection():
    """Get database connection with context manager."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_database.py::test_init_database_creates_table -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/database.py tests/test_database.py
git commit -m "feat: add database schema and initialization

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Database Layer - Insert Classification Events

**Files:**
- Modify: `src/database.py`
- Modify: `tests/test_database.py`

**Step 1: Write failing test for inserting events**

Add to `tests/test_database.py`:

```python
from src.database import insert_classification_event


def test_insert_classification_event():
    """Test inserting a classification event."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database
        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Insert event
            insert_classification_event("finance", "rule", 1.0)

            # Verify it was inserted
            with get_connection() as conn:
                cursor = conn.execute("SELECT * FROM classification_events")
                row = cursor.fetchone()
                assert row is not None
                assert row["label"] == "finance"
                assert row["method"] == "rule"
                assert row["confidence"] == 1.0
        finally:
            src.database.DATABASE_PATH = original_path
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_database.py::test_insert_classification_event -v`
Expected: FAIL with "ImportError: cannot import name 'insert_classification_event'"

**Step 3: Implement insert function**

Add to `src/database.py`:

```python
def insert_classification_event(
    label: str,
    method: str,
    confidence: float
) -> None:
    """Insert a classification event."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO classification_events (label, method, confidence) VALUES (?, ?, ?)",
            (label, method, confidence)
        )
        conn.commit()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_database.py::test_insert_classification_event -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/database.py tests/test_database.py
git commit -m "feat: add insert_classification_event function

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Database Layer - Query Functions

**Files:**
- Modify: `src/database.py`
- Modify: `tests/test_database.py`

**Step 1: Write failing tests for query functions**

Add to `tests/test_database.py`:

```python
from src.database import count_classifications, get_label_counts, count_by_method, get_average_confidence
from datetime import datetime, timedelta


def test_count_classifications():
    """Test counting total classifications."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database
        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("newsletters", "llm", 0.8)

            total = count_classifications()
            assert total == 2
        finally:
            src.database.DATABASE_PATH = original_path


def test_count_classifications_with_date_filter():
    """Test counting classifications since a specific date."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database
        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()
            insert_classification_event("finance", "rule", 1.0)

            # Count since yesterday (should include the event)
            yesterday = datetime.now() - timedelta(days=1)
            count = count_classifications(since=yesterday)
            assert count == 1

            # Count since tomorrow (should be 0)
            tomorrow = datetime.now() + timedelta(days=1)
            count = count_classifications(since=tomorrow)
            assert count == 0
        finally:
            src.database.DATABASE_PATH = original_path


def test_get_label_counts():
    """Test getting classification counts per label."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database
        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("newsletters", "llm", 0.8)

            counts = get_label_counts()
            assert counts["finance"] == 2
            assert counts["newsletters"] == 1
        finally:
            src.database.DATABASE_PATH = original_path


def test_count_by_method():
    """Test counting classifications by method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database
        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("newsletters", "llm", 0.8)

            rule_count = count_by_method("rule")
            llm_count = count_by_method("llm")
            assert rule_count == 2
            assert llm_count == 1
        finally:
            src.database.DATABASE_PATH = original_path


def test_get_average_confidence():
    """Test calculating average confidence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database
        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("newsletters", "llm", 0.8)

            avg = get_average_confidence()
            assert avg == 0.9  # (1.0 + 0.8) / 2
        finally:
            src.database.DATABASE_PATH = original_path
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_database.py -v -k "test_count or test_get_average"`
Expected: FAIL with import errors

**Step 3: Implement query functions**

Add to `src/database.py`:

```python
def count_classifications(since: datetime | None = None) -> int:
    """Count total classifications, optionally since a date."""
    with get_connection() as conn:
        if since:
            result = conn.execute(
                "SELECT COUNT(*) FROM classification_events WHERE timestamp >= ?",
                (since,)
            ).fetchone()
        else:
            result = conn.execute("SELECT COUNT(*) FROM classification_events").fetchone()
        return result[0]


def get_label_counts() -> dict[str, int]:
    """Get classification count per label."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT label, COUNT(*) as count FROM classification_events GROUP BY label"
        ).fetchall()
        return {row["label"]: row["count"] for row in rows}


def count_by_method(method: str) -> int:
    """Count classifications by method (rule/llm)."""
    with get_connection() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM classification_events WHERE method = ?",
            (method,)
        ).fetchone()
        return result[0]


def get_average_confidence() -> float:
    """Get average confidence across all classifications."""
    with get_connection() as conn:
        result = conn.execute(
            "SELECT AVG(confidence) FROM classification_events"
        ).fetchone()
        return result[0] if result[0] is not None else 0.0
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_database.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/database.py tests/test_database.py
git commit -m "feat: add database query functions for analytics

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Backend API - Analytics Models and Endpoint

**Files:**
- Modify: `src/api/models.py`
- Create: `src/api/analytics.py`
- Create: `tests/test_api_analytics.py`

**Step 1: Write failing test for analytics endpoint**

Create `tests/test_api_analytics.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import init_database, insert_classification_event
import tempfile
from pathlib import Path


@pytest.mark.asyncio
async def test_get_analytics():
    """Test GET /api/analytics endpoint."""
    # Setup test database
    with tempfile.TemporaryDirectory() as tmpdir:
        import src.database
        original_path = src.database.DATABASE_PATH
        src.database.DATABASE_PATH = Path(tmpdir) / "test.db"

        try:
            init_database()

            # Insert test data
            insert_classification_event("finance", "rule", 1.0)
            insert_classification_event("newsletters", "llm", 0.8)

            # Test endpoint
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/analytics")

            assert response.status_code == 200
            data = response.json()
            assert data["total_all_time"] == 2
            assert data["rule_classifications"] == 1
            assert data["llm_classifications"] == 1
            assert data["avg_confidence"] == 0.9
            assert "finance" in data["by_label"]
            assert data["by_label"]["finance"] == 1
        finally:
            src.database.DATABASE_PATH = original_path
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_api_analytics.py::test_get_analytics -v`
Expected: FAIL with 404 Not Found

**Step 3: Add AnalyticsResponse model**

Add to `src/api/models.py`:

```python
class AnalyticsResponse(BaseModel):
    total_all_time: int
    total_today: int
    total_this_week: int
    by_label: dict[str, int]
    rule_classifications: int
    llm_classifications: int
    avg_confidence: float
```

**Step 4: Create analytics router**

Create `src/api/analytics.py`:

```python
"""Analytics API endpoints."""
from datetime import datetime, timedelta
from fastapi import APIRouter

from src.api.models import AnalyticsResponse
from src.database import (
    count_classifications,
    get_label_counts,
    count_by_method,
    get_average_confidence,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsResponse)
async def get_analytics() -> AnalyticsResponse:
    """Get classification analytics summary."""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    return AnalyticsResponse(
        total_all_time=count_classifications(),
        total_today=count_classifications(since=today_start),
        total_this_week=count_classifications(since=week_start),
        by_label=get_label_counts(),
        rule_classifications=count_by_method("rule"),
        llm_classifications=count_by_method("llm"),
        avg_confidence=get_average_confidence(),
    )
```

**Step 5: Mount router in main.py**

Modify `src/main.py`:

```python
# Add import
from src.api.analytics import router as analytics_router

# Add after labels_router mount
app.include_router(analytics_router)
```

**Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_api_analytics.py::test_get_analytics -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/api/models.py src/api/analytics.py tests/test_api_analytics.py src/main.py
git commit -m "feat: add analytics API endpoint

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Initialize Database on Startup

**Files:**
- Modify: `src/main.py`

**Step 1: Add database initialization to startup**

Modify `src/main.py`:

```python
# Add import at top
from src.database import init_database

# Add before app creation
init_database()

app = create_app(config_path=config_path, provider=provider)
```

**Step 2: Test manually**

Run: `make run`
Expected: Server starts, data/ directory created with sortbox.db

**Step 3: Verify database file exists**

Run: `ls -la data/`
Expected: See `sortbox.db` file

**Step 4: Commit**

```bash
git add src/main.py
git commit -m "feat: initialize database on startup

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Track Classification Events

**Files:**
- Modify: `src/classifier/service.py`

**Step 1: Add event tracking after classification**

Modify `src/classifier/service.py`:

Find the `classify_emails` function and add event tracking after each successful classification:

```python
# Add import at top
from src.database import insert_classification_event

# In classify_emails function, after result is created:
@app.post("/classify", response_model=ClassifyResponse)
async def classify_emails(request: ClassifyRequest) -> ClassifyResponse:
    # ... existing code ...

    results = []
    for email in request.emails:
        result = classify_single(email, config, provider)
        results.append(result)

        # NEW: Track classification event
        if result.labels:
            try:
                insert_classification_event(
                    label=result.labels[0],
                    method="rule" if any(config.labels[label].rules for label in result.labels) else "llm",
                    confidence=result.confidence
                )
            except Exception as e:
                # Log but don't fail classification
                print(f"Warning: Failed to track event: {e}")

    return ClassifyResponse(results=results)
```

**Step 2: Test manually**

Run: `make run`
Then: Use Test Console in UI or POST to /classify
Expected: Events appear in database

**Step 3: Verify events in database**

Run: `sqlite3 data/sortbox.db "SELECT * FROM classification_events;"`
Expected: See inserted events

**Step 4: Commit**

```bash
git add src/classifier/service.py
git commit -m "feat: track classification events in database

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Frontend - Install Recharts

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install recharts dependency**

Run:
```bash
cd frontend
npm install recharts
cd ..
```

**Step 2: Verify installation**

Run: `cat frontend/package.json | grep recharts`
Expected: See "recharts" in dependencies

**Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat: add recharts dependency for analytics charts

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Frontend - Analytics Types and API Client

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/hooks/useAnalytics.ts`

**Step 1: Add AnalyticsData type**

Add to `frontend/src/lib/types.ts`:

```typescript
export interface AnalyticsData {
  total_all_time: number
  total_today: number
  total_this_week: number
  by_label: Record<string, number>
  rule_classifications: number
  llm_classifications: number
  avg_confidence: number
}
```

**Step 2: Add fetchAnalytics function**

Add to `frontend/src/lib/api.ts`:

```typescript
import { AnalyticsData } from './types'

export async function fetchAnalytics(): Promise<AnalyticsData> {
  const response = await fetch(`${API_BASE}/analytics`)
  if (!response.ok) {
    throw new Error('Failed to fetch analytics')
  }
  return response.json()
}
```

**Step 3: Create useAnalytics hook**

Create `frontend/src/hooks/useAnalytics.ts`:

```typescript
import { useQuery } from '@tanstack/react-query'
import { fetchAnalytics } from '../lib/api'

export function useAnalytics() {
  return useQuery({
    queryKey: ['analytics'],
    queryFn: fetchAnalytics,
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  })
}
```

**Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/hooks/useAnalytics.ts
git commit -m "feat: add analytics API client and hook

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Frontend - Analytics Dashboard Components

**Files:**
- Modify: `frontend/src/pages/Analytics.tsx`

**Step 1: Replace Analytics page with full implementation**

Replace `frontend/src/pages/Analytics.tsx`:

```typescript
import { useAnalytics } from '../hooks/useAnalytics'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16']

function StatCard({ title, value }: { title: string; value: number }) {
  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="px-4 py-5 sm:p-6">
        <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
        <dd className="mt-1 text-3xl font-semibold text-gray-900">{value}</dd>
      </div>
    </div>
  )
}

function LabelPieChart({ data }: { data: Record<string, number> }) {
  if (Object.keys(data).length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No classification data yet
      </div>
    )
  }

  const chartData = Object.entries(data).map(([label, count]) => ({
    name: label,
    value: count,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={80}
          label={(entry) => `${entry.name}: ${entry.value}`}
        >
          {chartData.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const percent = (confidence * 100).toFixed(1)
  const colorClass = confidence >= 0.9 ? 'bg-green-100 text-green-800' :
                      confidence >= 0.7 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'

  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${colorClass}`}>
      Average Confidence: {percent}%
    </span>
  )
}

export function Analytics() {
  const { data, isLoading } = useAnalytics()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading analytics...</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">No analytics data available</div>
      </div>
    )
  }

  const totalMethod = data.rule_classifications + data.llm_classifications
  const rulePercent = totalMethod > 0 ? (data.rule_classifications / totalMethod) * 100 : 0
  const llmPercent = totalMethod > 0 ? (data.llm_classifications / totalMethod) * 100 : 0

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Analytics</h2>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3 mb-8">
        <StatCard title="All Time" value={data.total_all_time} />
        <StatCard title="Today" value={data.total_today} />
        <StatCard title="This Week" value={data.total_this_week} />
      </div>

      {/* Classification Method */}
      <div className="bg-white shadow rounded-lg p-6 mb-8">
        <h3 className="text-lg font-semibold mb-4">Classification Method</h3>
        {totalMethod > 0 ? (
          <div>
            <div className="flex justify-between mb-2 text-sm">
              <span>🎯 Rule: {rulePercent.toFixed(0)}%</span>
              <span>🤖 LLM: {llmPercent.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-green-500 h-4 rounded-full transition-all duration-300"
                style={{ width: `${rulePercent}%` }}
              />
            </div>
            <div className="flex justify-between mt-2 text-xs text-gray-600">
              <span>{data.rule_classifications} classifications</span>
              <span>{data.llm_classifications} classifications</span>
            </div>
          </div>
        ) : (
          <div className="text-gray-500 text-center py-4">No classifications yet</div>
        )}
      </div>

      {/* Label Distribution */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h3 className="text-lg font-semibold mb-4">Label Distribution</h3>
        <LabelPieChart data={data.by_label} />
      </div>

      {/* Average Confidence */}
      <div className="flex justify-center">
        <ConfidenceBadge confidence={data.avg_confidence} />
      </div>
    </div>
  )
}
```

**Step 2: Test manually**

Run: `cd frontend && npm run dev`
Navigate to: http://localhost:5173/analytics
Expected: See analytics dashboard with charts

**Step 3: Commit**

```bash
git add frontend/src/pages/Analytics.tsx
git commit -m "feat: implement analytics dashboard with charts

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Testing and Verification

**Files:**
- Run all tests

**Step 1: Run all backend tests**

Run: `uv run pytest -v`
Expected: All tests pass

**Step 2: Build frontend**

Run: `cd frontend && npm run build && cd ..`
Expected: Build succeeds

**Step 3: Start server and test full flow**

Run: `make run`

Then test:
1. Navigate to http://127.0.0.1:8000
2. Go to Test Console
3. Test a few sample emails
4. Navigate to Analytics
5. Verify stats update in real-time

**Step 4: Verify database has events**

Run: `sqlite3 data/sortbox.db "SELECT COUNT(*) FROM classification_events;"`
Expected: See count of events

**Step 5: Test API endpoint directly**

Run: `curl http://127.0.0.1:8000/api/analytics | python3 -m json.tool`
Expected: See JSON analytics data

**Step 6: Final commit**

```bash
git add .
git commit -m "test: verify analytics implementation complete

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Summary

This plan implements basic analytics in 10 tasks:

1. **Database schema** - SQLite table for classification events
2. **Insert events** - Track each classification
3. **Query functions** - Aggregate analytics data
4. **API endpoint** - Serve analytics to frontend
5. **Database init** - Auto-create database on startup
6. **Event tracking** - Integrate with classifier
7. **Frontend deps** - Install Recharts
8. **Frontend API** - Types, client, hooks
9. **Dashboard UI** - Stats cards, charts, badges
10. **Testing** - Full integration verification

**Estimated Time:** 3-4 hours

**Testing Strategy:**
- TDD for all backend code
- Manual testing for frontend
- Integration test with full flow

**Key Features:**
- ✅ Lightweight SQLite tracking
- ✅ Single analytics endpoint
- ✅ Auto-refreshing dashboard
- ✅ Pie chart for label distribution
- ✅ Rule vs LLM method tracking
- ✅ Confidence scoring
