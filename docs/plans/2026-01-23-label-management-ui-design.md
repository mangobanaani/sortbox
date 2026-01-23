# Label Management UI - Design Document

## Overview

A React-based web interface for managing sortbox labels, testing classification rules, and viewing analytics. Replaces manual YAML editing with a user-friendly dashboard that provides real-time feedback and visualization.

## Goals

1. **Quick label editing** - Create, edit, delete labels and rules without editing YAML files
2. **Rule testing** - Test classification against sample emails before deploying changes
3. **Analytics** - Visualize label usage, rule effectiveness, and classification patterns
4. **Hot reload** - Changes take effect immediately without service restart

## Architecture

### Tech Stack

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- TanStack Query (server state)
- Tailwind CSS + shadcn/ui (styling)
- Recharts (analytics charts)
- React Router (routing)

**Backend:**
- FastAPI (existing + new endpoints)
- Watchfiles (config hot-reload)
- Server-Sent Events (live updates)

**Deployment:**
- Single Docker container
- FastAPI serves React build as static files
- Same-origin deployment (no CORS)

### System Diagram

```
┌─────────────────────────────────────────────────┐
│                  Browser                        │
│  ┌───────────────────────────────────────────┐ │
│  │         React SPA                         │ │
│  │  - Dashboard                              │ │
│  │  - Label Editor                           │ │
│  │  - Test Console                           │ │
│  │  - Analytics                              │ │
│  └─────────────┬─────────────────────────────┘ │
└────────────────┼───────────────────────────────┘
                 │ HTTP/REST + SSE
                 ▼
┌─────────────────────────────────────────────────┐
│           FastAPI Backend                       │
│  ┌───────────────────────────────────────────┐ │
│  │  /api/labels          (CRUD)              │ │
│  │  /api/labels/test     (testing)           │ │
│  │  /api/stats/*         (analytics)         │ │
│  │  /api/config/*        (settings)          │ │
│  │  /api/events          (SSE live updates)  │ │
│  └─────────────┬─────────────────────────────┘ │
│                │                                │
│  ┌─────────────▼─────────────────────────────┐ │
│  │  Config Hot-Reload (watchfiles)          │ │
│  │  - Watch labels.yaml                      │ │
│  │  - Reload on change                       │ │
│  │  - Emit SSE event                         │ │
│  └─────────────┬─────────────────────────────┘ │
└────────────────┼───────────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │  labels.yaml  │
         └───────────────┘
```

---

## Frontend Design

### Pages

#### 1. Dashboard (/)

**Purpose:** Overview of classification activity and quick actions.

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  sortbox                            [User Menu]      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐      │
│  │  12 Labels │ │ 87% Rules  │ │ 234 Emails │      │
│  │            │ │   Coverage │ │    Today   │      │
│  └────────────┘ └────────────┘ └────────────┘      │
│                                                      │
│  Recent Classifications                              │
│  ┌────────────────────────────────────────────┐    │
│  │ billing@stripe.com  │ Invoice │ finance ✓  │    │
│  │ news@tech.com       │ Digest  │ newsletters│    │
│  │ ...                                         │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  [+ Add Label]  [Test Email]                        │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Components:**
- `StatCard` - Metric display with icon
- `RecentTable` - Recent classifications with labels
- Quick action buttons

---

#### 2. Labels (/labels)

**Purpose:** Main interface for managing labels and rules.

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  Labels                                              │
├──────────────┬──────────────────────────────────────┤
│              │                                       │
│ [Search...]  │  finance                             │
│              │  ┌─────────────────────────────────┐ │
│ finance (45) │  │ Description                     │ │
│ newsletters  │  │ [Invoices, receipts, payments]  │ │
│ travel       │  │                                 │ │
│ security     │  │ Rules (3)                       │ │
│ ...          │  │ ✓ from: *@stripe.com            │ │
│              │  │ ✓ from: *@paypal.com            │ │
│ [+ New]      │  │ ✓ subject: invoice, receipt     │ │
│              │  │                                 │ │
│              │  │ [+ Add Rule]                    │ │
│              │  │                                 │ │
│              │  │ [Test] [Save] [Delete]          │ │
│              │  └─────────────────────────────────┘ │
│              │                                       │
└──────────────┴──────────────────────────────────────┘
```

**Features:**
- Sidebar label list with search/filter
- Editor panel for selected label
- Visual rule builder
- Save/delete/test actions
- Validation feedback

**Rule Editor Modal:**
```
┌─────────────────────────────────────┐
│  Add Rule                      [X]  │
├─────────────────────────────────────┤
│                                     │
│  Rule Type:                         │
│  ● From pattern                     │
│  ○ Subject contains                 │
│  ○ Header (unsubscribe)             │
│                                     │
│  Pattern:                           │
│  [*@stripe.com____________]         │
│                                     │
│  Examples:                          │
│  • *@domain.com - exact domain      │
│  • *@*.domain.com - subdomains      │
│  • *noreply@* - contains noreply    │
│                                     │
│         [Cancel]  [Add Rule]        │
│                                     │
└─────────────────────────────────────┘
```

---

#### 3. Test Console (/test)

**Purpose:** Test classification against sample or custom emails.

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  Test Console                                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Sample Emails: [Select...] or enter custom         │
│                                                      │
│  From:    [billing@stripe.com_________________]     │
│  Subject: [Invoice #1234______________________]     │
│  Preview: [Your invoice is ready. Amount...___]     │
│           [___________________________________|     │
│                                                      │
│  [Classify Email]                                   │
│                                                      │
│  Results:                                            │
│  ┌──────────────────────────────────────────────┐  │
│  │ Matched: [finance] 1.0 ✓                     │  │
│  │                                               │  │
│  │ Rules Matched:                                │  │
│  │  ✓ from: *@stripe.com                        │  │
│  │                                               │  │
│  │ LLM Used: No                                  │  │
│  │ Time: 23ms                                    │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  Test History:                                       │
│  • billing@stripe.com → finance                     │
│  • news@blog.com → newsletters                      │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Features:**
- Load sample emails from fixtures
- Manual email entry
- Real-time classification
- Rule match breakdown
- Test history (local storage)

---

#### 4. Analytics (/analytics)

**Purpose:** Visualize label usage and classification patterns.

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  Analytics                     [7d ▼] [Export]      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌────────────────────┐  ┌────────────────────┐    │
│  │  Label Distribution│  │  Rule vs LLM       │    │
│  │                    │  │                    │    │
│  │   (Pie Chart)      │  │  (Stacked Bar)     │    │
│  │                    │  │                    │    │
│  └────────────────────┘  └────────────────────┘    │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  Classifications Over Time                   │  │
│  │                                               │  │
│  │  (Line Chart)                                 │  │
│  │                                               │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  Label Performance                                   │
│  ┌──────────────────────────────────────────────┐  │
│  │ Label      │ Count │ Rule % │ LLM % │ Avg    │  │
│  │ finance    │   45  │  89%   │  11%  │ 0.92   │  │
│  │ newsletters│   32  │ 100%   │   0%  │ 1.00   │  │
│  │ ...                                           │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Charts:**
- Pie: Label distribution by volume
- Stacked bar: Rule hits vs LLM usage per label
- Line: Classifications over time (daily)
- Table: Label performance metrics

**Date Ranges:** 7d, 30d, 90d, custom

**Export:** Download stats as JSON or CSV

---

### Component Library

**Core Components:**

1. **`<LabelCard>`**
   - Props: `label`, `description`, `ruleCount`, `onClick`
   - Shows label badge with rule count
   - Click to edit

2. **`<RuleEditor>`**
   - Props: `rule`, `onSave`, `onCancel`
   - Modal form for rule creation/editing
   - Validates rule syntax
   - Shows examples for selected type

3. **`<EmailPreview>`**
   - Props: `email` (sender, subject, body_preview)
   - Formatted display of email metadata
   - Used in test console and recent activity

4. **`<ConfidenceBadge>`**
   - Props: `confidence` (0-1)
   - Visual indicator: green (>0.8), yellow (0.5-0.8), red (<0.5)
   - Shows percentage

5. **`<StatCard>`**
   - Props: `title`, `value`, `icon`, `trend`
   - Dashboard metric display
   - Optional trend indicator (↑↓)

6. **`<RuleList>`**
   - Props: `rules`, `onEdit`, `onDelete`
   - Displays rules with type icons
   - Edit/delete actions per rule

**Layout Components:**
- `<Layout>` - Main app shell with nav
- `<Sidebar>` - Collapsible sidebar for labels page
- `<PageHeader>` - Page title with actions

---

## Backend API Design

### Endpoints

#### Label Management

**GET /api/labels**

List all labels with rules and settings.

Response:
```json
{
  "labels": {
    "finance": {
      "description": "Invoices, receipts, payments",
      "rules": [
        { "type": "from", "pattern": "*@stripe.com" },
        { "type": "subject_contains", "keywords": ["invoice", "receipt"] }
      ]
    }
  },
  "settings": {
    "llm_provider": "claude",
    "confidence_threshold": 0.7
  }
}
```

**POST /api/labels**

Create a new label.

Request:
```json
{
  "name": "travel",
  "description": "Flight confirmations, hotel bookings",
  "rules": []
}
```

Response: `201 Created`

Validation:
- Name must be unique
- Name must be lowercase, alphanumeric, hyphens only
- Description required

**PUT /api/labels/{name}**

Update existing label.

Request:
```json
{
  "description": "Updated description",
  "rules": [
    { "type": "from", "pattern": "*@booking.com" }
  ]
}
```

Response: `200 OK`

**DELETE /api/labels/{name}**

Delete a label.

Response: `204 No Content`

Safety check: Confirm no emails currently use this label (or offer cascade delete).

**POST /api/labels/reorder**

Change label display order (for UI sorting).

Request:
```json
{
  "order": ["finance", "travel", "newsletters", "security"]
}
```

Response: `200 OK`

Note: Stored in metadata, doesn't affect labels.yaml structure.

---

#### Testing

**POST /api/labels/test**

Test classification against a sample email.

Request:
```json
{
  "email": {
    "sender": "billing@stripe.com",
    "subject": "Invoice #1234",
    "body_preview": "Your invoice is ready"
  }
}
```

Response:
```json
{
  "matched_labels": ["finance"],
  "matched_rules": [
    {
      "label": "finance",
      "rule": { "type": "from", "pattern": "*@stripe.com" }
    }
  ],
  "confidence": 1.0,
  "llm_used": false,
  "time_ms": 23
}
```

Uses existing classification logic, returns detailed breakdown.

---

#### Analytics

**GET /api/stats/labels?days=7**

Label usage statistics for the past N days.

Response:
```json
{
  "finance": {
    "count": 45,
    "rule_hits": 40,
    "llm_hits": 5,
    "avg_confidence": 0.92
  },
  "newsletters": {
    "count": 32,
    "rule_hits": 32,
    "llm_hits": 0,
    "avg_confidence": 1.0
  }
}
```

Queries `email_metadata` table (requires orchestrator to be implemented).

**GET /api/stats/recent?limit=50**

Recent classifications.

Response:
```json
[
  {
    "email_id": "msg001",
    "sender": "billing@stripe.com",
    "subject": "Invoice #1234",
    "labels": ["finance"],
    "confidence": 1.0,
    "timestamp": "2026-01-23T14:30:00Z"
  }
]
```

**GET /api/stats/timeline?days=30**

Classification volume over time.

Response:
```json
{
  "2026-01-23": { "finance": 12, "newsletters": 8, "travel": 3 },
  "2026-01-22": { "finance": 15, "newsletters": 5, "travel": 0 }
}
```

---

#### Config Management

**GET /api/config/settings**

Get current settings.

Response:
```json
{
  "llm_provider": "claude",
  "confidence_threshold": 0.7,
  "max_emails_per_run": 100
}
```

**PUT /api/config/settings**

Update settings.

Request:
```json
{
  "llm_provider": "openai",
  "confidence_threshold": 0.8
}
```

Response: `200 OK`

Writes to labels.yaml, triggers hot-reload.

**POST /api/config/validate**

Validate a config before saving.

Request:
```json
{
  "labels": { ... },
  "settings": { ... }
}
```

Response:
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Label 'finance' has no rules, will rely on LLM"]
}
```

Checks:
- No duplicate label names
- Valid rule syntax
- Valid settings values
- Provider credentials available

---

#### Live Updates

**GET /api/events (SSE)**

Server-Sent Events stream for live updates.

Events:
- `config_reloaded` - labels.yaml was reloaded
- `classification` - new email classified (for dashboard live updates)

Client subscribes on mount, updates UI when events received.

---

### Config Hot-Reload

**Implementation:**

1. Use `watchfiles` library to watch labels.yaml
2. On file change:
   - Reload config with `load_config()`
   - Update in-memory config in FastAPI app
   - Emit SSE event to connected clients
3. Frontend receives event, refetches labels

**Code structure:**
```python
# src/config_watcher.py
from watchfiles import awatch

async def watch_config(app):
    async for changes in awatch('labels.yaml'):
        new_config = load_config(Path('labels.yaml'))
        app.state.config = new_config
        await broadcast_sse('config_reloaded')
```

Start watcher in FastAPI lifespan event.

---

## Project Structure

```
sortbox/
├── frontend/                  # React app
│   ├── src/
│   │   ├── components/
│   │   │   ├── LabelCard.tsx
│   │   │   ├── RuleEditor.tsx
│   │   │   ├── EmailPreview.tsx
│   │   │   ├── ConfidenceBadge.tsx
│   │   │   └── ...
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Labels.tsx
│   │   │   ├── TestConsole.tsx
│   │   │   └── Analytics.tsx
│   │   ├── hooks/
│   │   │   ├── useLabels.ts
│   │   │   ├── useStats.ts
│   │   │   └── useSSE.ts
│   │   ├── lib/
│   │   │   ├── api.ts          # API client
│   │   │   └── utils.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── src/                       # Backend (existing + new)
│   ├── api/                   # New API routers
│   │   ├── labels.py          # Label CRUD
│   │   ├── stats.py           # Analytics
│   │   ├── config.py          # Settings
│   │   └── events.py          # SSE
│   ├── config_watcher.py      # Hot-reload
│   └── ... (existing)
│
└── ... (existing)
```

---

## Data Flow

### Label Edit Flow

```
User edits label in UI
  → PUT /api/labels/{name}
  → Update labels.yaml on disk
  → Watchfiles detects change
  → Reload config in memory
  → Broadcast SSE event
  → Frontend receives event
  → Refetch labels
  → UI updates
```

### Classification Test Flow

```
User enters email in test console
  → POST /api/labels/test
  → Run classification (rules + LLM if needed)
  → Return matched labels + rule breakdown
  → Display results in UI
  → Store in test history (localStorage)
```

### Analytics Flow

```
Page load
  → GET /api/stats/labels?days=7
  → Query email_metadata table
  → Aggregate by label
  → Return stats
  → Render charts
```

---

## Deployment

### Development

```bash
# Terminal 1: Backend
cd sortbox
make run

# Terminal 2: Frontend
cd sortbox/frontend
npm run dev
```

Frontend dev server proxies `/api/*` to backend.

### Production

**Build:**
```bash
cd frontend
npm run build
# Output: dist/
```

**Serve:**
```python
# src/main.py
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

FastAPI serves React build. All routes go to index.html (SPA routing).

**Docker:**
```dockerfile
FROM node:20 AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY --from=frontend /app/frontend/dist ./frontend/dist
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev
COPY src/ src/
COPY labels.yaml .
ENV DATABASE_PATH=/app/data/sortbox.db
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Multi-stage build: npm build → copy to Python image.

---

## Security Considerations

**No authentication:** Designed for localhost/internal network only.

**Protection strategies:**
1. Bind to 127.0.0.1 by default (not 0.0.0.0)
2. Document security warning in README
3. Add `--allow-remote` flag to explicitly enable external access
4. Rate limiting on API endpoints (prevent abuse)
5. Input validation on all POST/PUT endpoints
6. CSRF protection (SameSite cookies, even without auth)

**Future:** Add simple API key auth if deployed on network.

---

## Error Handling

**Frontend:**
- TanStack Query handles loading/error states
- Toast notifications for API errors
- Form validation feedback
- Graceful degradation (offline detection)

**Backend:**
- Pydantic validation errors → 422 Unprocessable Entity
- Config validation errors → 400 Bad Request with details
- File I/O errors → 500 Internal Server Error (logged)
- SSE connection errors → auto-reconnect with backoff

---

## Testing Strategy

**Frontend:**
- Vitest for unit tests
- React Testing Library for component tests
- MSW (Mock Service Worker) for API mocking
- Playwright for E2E tests (optional)

**Backend:**
- pytest for new API endpoints
- Test config hot-reload with temporary files
- Test SSE event emission
- Integration tests: API → YAML → reload

**Coverage target:** 80% minimum

---

## Performance

**Frontend:**
- Code splitting (React.lazy for pages)
- TanStack Query caching (reduce API calls)
- Debounce search inputs
- Virtual scrolling for large label lists (react-window)

**Backend:**
- Config hot-reload is async (doesn't block requests)
- SSE uses async generators (low overhead)
- Analytics queries cached (5 min TTL)

---

## Migration Plan

**Phase 1:** Backend API (no UI yet)
- Add label CRUD endpoints
- Add config hot-reload
- Test with curl/Postman

**Phase 2:** Basic UI
- Dashboard + Labels pages
- CRUD operations working
- Deploy alongside existing API

**Phase 3:** Advanced Features
- Test console
- Analytics
- SSE live updates

**Phase 4:** Polish
- Error handling
- Loading states
- Animations
- Mobile responsive

---

## Open Questions

1. **Email metadata:** Analytics requires `email_metadata` table from orchestrator. Either:
   - Mock data for now
   - Basic logging (store classifications in SQLite)
   - Wait for orchestrator implementation

2. **Rule validation:** Should we validate glob patterns before saving? (Test against sample emails?)

3. **Undo/redo:** Should label changes be reversible? (Git history, or in-app undo stack?)

4. **Import/export:** Should users be able to export labels as JSON? Import from other sources?

---

## Success Criteria

1. Can create/edit/delete labels without touching YAML
2. Changes take effect immediately (hot-reload working)
3. Test console accurately shows classification results
4. Analytics display label usage over time
5. UI is responsive and intuitive
6. 80%+ test coverage on new code
7. Documented in README with screenshots

---

## Timeline Estimate

- Backend API: 3-5 days
- Basic UI (Dashboard + Labels): 5-7 days
- Test Console: 2-3 days
- Analytics: 3-4 days
- Polish + Testing: 3-5 days

**Total:** 2-3 weeks for full implementation
