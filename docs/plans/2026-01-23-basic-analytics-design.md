# Basic Analytics Design

**Goal:** Track email classification patterns and display insights in the Analytics dashboard.

**Date:** 2026-01-23

## Overview

Add lightweight analytics to track classification events and visualize key metrics in the existing Analytics page placeholder. Focus on classification patterns, rule vs LLM usage, and label distribution.

## Architecture

```
Classification Flow:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Classify   │ --> │   Insert     │     │   SQLite     │
│   Email      │     │   Event      │ --> │   Database   │
└──────────────┘     └──────────────┘     └──────────────┘

Analytics Flow:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Analytics  │ --> │   GET        │     │   Query      │
│   Page       │     │   /analytics │ --> │   Events     │
└──────────────┘     └──────────────┘     └──────────────┘
```

**Design Principle:** Keep it simple. One table, one endpoint, one dashboard. No complex queries or heavy processing.

---

## 1. Database Schema

**File:** `src/database.py` (new file)

**Schema:**

```sql
CREATE TABLE classification_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    label TEXT NOT NULL,
    method TEXT NOT NULL,  -- 'rule' or 'llm'
    confidence REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_timestamp ON classification_events(timestamp);
CREATE INDEX idx_label ON classification_events(label);
```

**Fields:**
- `id` - Auto-incrementing primary key
- `timestamp` - When the email was classified
- `label` - Label assigned (e.g., "finance", "newsletters")
- `method` - Classification method: 'rule' or 'llm'
- `confidence` - Confidence score (0.0 to 1.0)
- `created_at` - Record creation time (for auditing)

**Storage Location:**
- Database file: `data/sortbox.db`
- Already gitignored in `.gitignore`
- Created automatically on first run
- Same database planned for orchestrator features

**Indexes:**
- `idx_timestamp` - Fast filtering by date ranges
- `idx_label` - Fast label aggregation queries

---

## 2. Database Layer

**File:** `src/database.py`

**Core Functions:**

```python
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

**Design Notes:**
- Simple, synchronous SQLite operations
- Connection pooling via context manager
- Fire-and-forget inserts (no error blocking)
- Read operations aggregate on-the-fly (no caching needed)

---

## 3. Data Capture Integration

**File:** `src/classifier/service.py`

**Modification:**

Add event tracking after successful classification:

```python
from src.database import insert_classification_event

@app.post("/classify", response_model=ClassifyResponse)
async def classify_emails(request: ClassifyRequest) -> ClassifyResponse:
    # ... existing classification logic ...

    results = []
    for email in request.emails:
        result = classify_single_email(email, config, provider)
        results.append(result)

        # NEW: Track classification event
        if result.labels:
            insert_classification_event(
                label=result.labels[0],  # Primary label
                method='rule' if result.matched_by_rule else 'llm',
                confidence=result.confidence
            )

    return ClassifyResponse(results=results)
```

**Error Handling:**
- Wrap insert in try/except to prevent classification failures
- Log errors but don't block response
- Analytics is supplementary, not critical path

---

## 4. Backend API

**File:** `src/api/analytics.py` (new file)

**Endpoint:**

```python
from datetime import datetime, timedelta
from fastapi import APIRouter
from src.api.models import AnalyticsResponse
from src.database import (
    count_classifications,
    get_label_counts,
    count_by_method,
    get_average_confidence
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
        rule_classifications=count_by_method('rule'),
        llm_classifications=count_by_method('llm'),
        avg_confidence=get_average_confidence()
    )
```

**File:** `src/api/models.py` (add model)

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

**File:** `src/main.py` (mount router)

```python
from src.api.analytics import router as analytics_router

app.include_router(analytics_router)
```

---

## 5. Frontend API Client

**File:** `frontend/src/lib/types.ts` (add type)

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

**File:** `frontend/src/lib/api.ts` (add function)

```typescript
export async function fetchAnalytics(): Promise<AnalyticsData> {
  const response = await fetch(`${API_BASE}/analytics`)
  if (!response.ok) {
    throw new Error('Failed to fetch analytics')
  }
  return response.json()
}
```

**File:** `frontend/src/hooks/useAnalytics.ts` (new file)

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

---

## 6. Frontend Analytics Dashboard

**File:** `frontend/src/pages/Analytics.tsx`

**Component Structure:**

```typescript
import { useAnalytics } from '../hooks/useAnalytics'

export function Analytics() {
  const { data, isLoading } = useAnalytics()

  if (isLoading) return <div>Loading analytics...</div>
  if (!data) return <div>No data available</div>

  // Calculate percentages
  const totalMethod = data.rule_classifications + data.llm_classifications
  const rulePercent = totalMethod > 0 ? (data.rule_classifications / totalMethod) * 100 : 0
  const llmPercent = totalMethod > 0 ? (data.llm_classifications / totalMethod) * 100 : 0

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Analytics</h1>

      {/* Stats Cards */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard title="All Time" value={data.total_all_time} />
        <StatCard title="Today" value={data.total_today} />
        <StatCard title="This Week" value={data.total_this_week} />
      </div>

      {/* Classification Method */}
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <h2 className="font-semibold mb-4">Classification Method</h2>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex justify-between mb-2">
              <span>🎯 Rule: {rulePercent.toFixed(0)}%</span>
              <span>🤖 LLM: {llmPercent.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div
                className="bg-green-500 h-4 rounded-full"
                style={{ width: `${rulePercent}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Label Distribution */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="font-semibold mb-4">Label Distribution</h2>
        <LabelPieChart data={data.by_label} />
      </div>

      {/* Average Confidence */}
      <div className="mt-4">
        <ConfidenceBadge confidence={data.avg_confidence} />
      </div>
    </div>
  )
}
```

**Sub-components:**

1. **StatCard** - Reusable stat display
2. **LabelPieChart** - Pie chart using Recharts
3. **ConfidenceBadge** - Colored badge for confidence score

**Recharts Integration:**

```typescript
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

function LabelPieChart({ data }: { data: Record<string, number> }) {
  const chartData = Object.entries(data).map(([label, count]) => ({
    name: label,
    value: count
  }))

  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']

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
          label
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
```

---

## 7. Dependencies

**Backend:**
- No new dependencies (uses stdlib sqlite3)

**Frontend:**

Add to `frontend/package.json`:

```json
{
  "dependencies": {
    "recharts": "^2.12.0"
  }
}
```

Install:
```bash
cd frontend && npm install recharts
```

---

## 8. Database Initialization

**File:** `src/main.py` (add startup)

```python
from src.database import init_database

# Initialize database on startup
init_database()

app = create_app(config_path=config_path, provider=provider)
```

**File:** `Dockerfile` (already has data directory)

```dockerfile
# Create data directory for SQLite (already exists)
RUN mkdir -p /app/data
```

---

## 9. Testing Strategy

**Backend Tests:**

```python
# tests/test_database.py
def test_insert_and_count_events():
    # Insert test events
    insert_classification_event("finance", "rule", 1.0)
    insert_classification_event("newsletters", "llm", 0.8)

    # Verify counts
    assert count_classifications() == 2
    assert count_by_method("rule") == 1
    assert count_by_method("llm") == 1

def test_label_distribution():
    insert_classification_event("finance", "rule", 1.0)
    insert_classification_event("finance", "rule", 1.0)
    insert_classification_event("newsletters", "llm", 0.8)

    counts = get_label_counts()
    assert counts["finance"] == 2
    assert counts["newsletters"] == 1

# tests/test_api_analytics.py
@pytest.mark.asyncio
async def test_analytics_endpoint():
    async with AsyncClient(...) as client:
        response = await client.get("/api/analytics")

    assert response.status_code == 200
    data = response.json()
    assert "total_all_time" in data
    assert "by_label" in data
```

**Frontend:**
- Manual testing in browser
- Verify charts render correctly
- Check auto-refresh works

**Target Coverage:** 80%+ on new backend code

---

## 10. Implementation Order

1. **Database layer** (`src/database.py`)
2. **API models** (add to `src/api/models.py`)
3. **API endpoint** (`src/api/analytics.py`)
4. **Data capture** (modify `src/classifier/service.py`)
5. **Database initialization** (modify `src/main.py`)
6. **Frontend types** (modify `frontend/src/lib/types.ts`)
7. **Frontend API client** (modify `frontend/src/lib/api.ts`)
8. **Frontend hook** (`frontend/src/hooks/useAnalytics.ts`)
9. **Analytics page** (replace `frontend/src/pages/Analytics.tsx`)
10. **Dependencies** (install recharts)
11. **Tests** (database and API tests)

**Estimated Time:** 3-4 hours

---

## 11. Future Enhancements (Out of Scope)

**Not included in this basic version:**

- Time-series trend charts (line/area charts over time)
- Sender frequency analysis
- Export to CSV
- Configurable date ranges
- Performance metrics (response times)
- LLM cost tracking
- Email volume predictions

These can be added later if needed, but keeping the initial version simple and focused.

---

## Summary

**What we're building:**
- Lightweight event tracking in SQLite
- Single analytics API endpoint
- Clean dashboard with key metrics
- Auto-refreshing UI

**What makes it "basic":**
- One table, simple queries
- No complex aggregations
- Static time ranges (today, week, all)
- No drill-down or filtering
- Read-only (no exports or reports)

**Value delivered:**
- See classification patterns at a glance
- Monitor rule vs LLM usage
- Track label distribution
- Verify system is working as expected

This design prioritizes simplicity and speed of implementation while providing immediate value.
