# Sortbox Orchestrator - Complete Email Automation System

## Overview

Transform sortbox from a simple classifier into a full email intelligence and automation system. The Python service becomes a stateful API handling classification, follow-up tracking, digest generation, draft creation, and archive policies. A single n8n orchestrator workflow runs on multiple schedules (real-time, daily, weekly) to coordinate all features.

## Goals

1. **Auto-classify and label** incoming emails (existing)
2. **Auto-draft replies** for action-required emails
3. **Generate digests** (daily summaries, weekly reports)
4. **Escalate urgent** emails to Telegram
5. **Track follow-ups** and remind when overdue
6. **Manage promotions** and suggest unsubscribes
7. **Approve label suggestions** via Telegram
8. **Auto-archive** old emails per policy

## Architecture

### Core Components

1. **Python Service (FastAPI)** - Stateful email intelligence API
2. **SQLite Database** - Tracks follow-ups, promotions, suggestions, metadata
3. **n8n Orchestrator** - Single workflow with multiple trigger paths
4. **Notification Router** - Multi-channel alerts by priority

### Technology Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy, SQLite
- **Workflow**: n8n (self-hosted or cloud)
- **LLM**: Claude/OpenAI/Ollama (configurable)
- **Notifications**: Telegram (urgent), Email (digests)
- **Email**: Gmail API via n8n

---

## Python API Design

### New Endpoints

**State Management:**
- `POST /follow-ups/track` - Record sent email for follow-up tracking
- `GET /follow-ups/pending?days_overdue=3` - List overdue threads
- `POST /follow-ups/resolve` - Mark thread as resolved

**Promotions/Unsubscribe:**
- `POST /promotions/track` - Increment sender counter
- `GET /promotions/offenders?threshold=5` - List frequent offenders

**Digests:**
- `GET /digest/daily` - Past 24h aggregate stats
- `GET /digest/weekly` - Past 7d trends and summaries

**Draft Generation:**
- `POST /drafts/generate` - LLM-generated reply draft

**Archive Policies:**
- `GET /archive/candidates?policy=default` - List archivable emails

**Suggestions:**
- `POST /suggestions/approve` - Add label to labels.yaml
- `GET /suggestions/pending` - List pending suggestions

### Request/Response Examples

**Track Follow-up:**
```json
POST /follow-ups/track
{
  "thread_id": "thread_abc123",
  "recipient": "client@company.com",
  "subject": "Re: Q1 Proposal",
  "sent_at": "2026-01-23T10:30:00Z"
}
→ 201 Created
```

**Generate Draft:**
```json
POST /drafts/generate
{
  "email_id": "msg001",
  "sender": "inquiry@startup.com",
  "subject": "Partnership opportunity",
  "body_preview": "We'd love to discuss..."
}
→ 200 OK
{
  "draft_text": "Thanks for reaching out. I'll review your proposal and get back to you by next week.",
  "tone": "professional",
  "confidence": 0.85
}
```

**Daily Digest:**
```json
GET /digest/daily
→ 200 OK
{
  "period": "2026-01-23",
  "total_emails": 47,
  "by_label": {
    "notifications": 18,
    "newsletters": 12,
    "action-required": 5,
    "finance": 3,
    "social": 9
  },
  "top_senders": [
    {"sender": "notifications@github.com", "count": 12},
    {"sender": "noreply@linkedin.com", "count": 8}
  ],
  "unread_count": 5,
  "needs_review": 2
}
```

---

## Database Schema

**SQLite Database:** `sortbox.db` (gitignored)

### Tables

```sql
-- Tracks sent emails awaiting replies
CREATE TABLE follow_ups (
    id INTEGER PRIMARY KEY,
    thread_id TEXT UNIQUE NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT,
    sent_at TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'awaiting_reply',  -- awaiting_reply | resolved | expired
    reminded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tracks promotion email frequency by sender
CREATE TABLE promotion_counters (
    id INTEGER PRIMARY KEY,
    sender TEXT UNIQUE NOT NULL,
    count INTEGER DEFAULT 1,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    unsubscribe_link TEXT,
    status TEXT DEFAULT 'tracking'  -- tracking | unsubscribed | ignored
);

-- Pending label suggestions from LLM
CREATE TABLE label_suggestions (
    id INTEGER PRIMARY KEY,
    suggested_label TEXT NOT NULL,
    confidence FLOAT,
    example_email_ids TEXT,  -- JSON array of email IDs
    reason TEXT,  -- LLM's explanation
    status TEXT DEFAULT 'pending',  -- pending | approved | rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP
);

-- Email metadata for archive policies
CREATE TABLE email_metadata (
    email_id TEXT PRIMARY KEY,
    labeled_at TIMESTAMP,
    labels TEXT,  -- JSON array
    read BOOLEAN DEFAULT FALSE,
    archived BOOLEAN DEFAULT FALSE
);
```

### SQLAlchemy Models

New file: `src/database.py`

```python
from sqlalchemy import Column, Integer, String, Float, Boolean, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class FollowUp(Base):
    __tablename__ = 'follow_ups'
    id = Column(Integer, primary_key=True)
    thread_id = Column(String, unique=True, nullable=False)
    recipient = Column(String, nullable=False)
    subject = Column(String)
    sent_at = Column(TIMESTAMP, nullable=False)
    status = Column(String, default='awaiting_reply')
    reminded_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP)

# ... similar for PromotionCounter, LabelSuggestion, EmailMetadata
```

Pydantic models added to `src/models.py` for API validation.

---

## n8n Orchestrator Workflow

**Single workflow, 4 trigger paths:**

### Triggers

1. **Schedule: Every 15 minutes** - Real-time classification
2. **Webhook: /trigger** - Manual invoke
3. **Schedule: Daily 8am** - Digest and follow-up check
4. **Telegram: Callback queries** - Suggestion approval

### Workflow Structure

```
[Triggers] → [Router Switch by trigger_source]
```

### Path 1: Real-time Classification (Every 15 min)

```
1. Gmail Fetch (label:inbox -label:processed, limit 100)
2. POST /classify
3. POST /email_metadata (bulk insert with labeled_at)
4. Split Results
5. For each result:
   a. Gmail Apply Labels
   b. IF label=action-required AND from_me=false:
      → POST /drafts/generate
      → Gmail Create Draft
   c. IF label=security:
      → Telegram Alert (instant)
   d. IF label contains promotions:
      → POST /promotions/track
6. Gmail Add Label: processed
```

### Path 2: Daily Digest (8am)

```
1. GET /digest/daily
2. Format as markdown:
   📊 Daily Email Summary - Jan 23

   Total: 47 emails

   By Label:
   - 🔔 Notifications: 18
   - 📰 Newsletters: 12
   - ⚡ Action Required: 5
   - 💰 Finance: 3
   - 👥 Social: 9

   Top Senders:
   - notifications@github.com (12)
   - noreply@linkedin.com (8)

   ⚠️ Needs Review: 2 emails
3. Email to user
4. GET /follow-ups/pending?days_overdue=3
5. IF any overdue:
   → Format: "⏰ Follow-up needed:\n- [subject] sent to [recipient] [X] days ago"
   → Telegram reminder with Gmail thread links
6. GET /promotions/offenders?threshold=5
7. IF any offenders:
   → Format unsubscribe list
   → Email to user
```

### Path 3: Weekly Maintenance (Sunday 9am)

```
1. GET /digest/weekly
2. Format weekly report with trends
3. Email to user
4. GET /archive/candidates
5. Split into batches (100 per batch)
6. Gmail Archive (bulk)
7. POST /email_metadata/mark_archived
8. Count archived, include in weekly report
9. GET /suggestions/pending
10. IF any pending:
    → For each suggestion:
      → Telegram message: "New label suggestion: [label_name]\nExample: [email_subject]\nReason: [llm_reason]"
      → Inline buttons: [Approve] [Reject]
```

### Path 4: Telegram Callbacks (Instant)

```
1. Parse callback_data (e.g., "approve_suggestion:travel")
2. IF action=approve_suggestion:
   → POST /suggestions/approve
   → Response: "✅ Added 'travel' to labels.yaml"
   → Trigger real-time classification to reclassify with new label
3. IF action=reject_suggestion:
   → POST /suggestions/reject
   → Response: "❌ Rejected suggestion"
```

---

## Notification Router

Multi-channel routing by priority:

| Event | Channel | Format |
|-------|---------|--------|
| Security alert | Telegram | Instant alert with email preview |
| Follow-up overdue | Telegram | Reminder with thread link |
| Label suggestion ready | Telegram | Message with approve/reject buttons |
| Daily digest | Email | Markdown summary |
| Weekly report | Email | Markdown with archive stats |
| Promotion offenders | Email | Unsubscribe suggestions |

**Telegram bot setup:**
- Bot token stored in n8n credentials
- Chat ID configured per user
- Inline keyboard for approvals

**Email formatting:**
- Plain markdown for compatibility
- Gmail thread links: `https://mail.google.com/mail/u/0/#inbox/[thread_id]`

---

## Draft Reply Generation

**Feature:** Auto-generate reply drafts for `action-required` emails.

**Endpoint:** `POST /drafts/generate`

**LLM Prompt Strategy:**

```
You are drafting a reply to an email.

From: {sender}
Subject: {subject}
Preview: {body_preview}

Generate a professional reply that:
1. Acknowledges the email
2. Is brief and to the point
3. Matches a {tone} tone (professional/casual/formal)
4. If uncertain, suggest you'll review and respond by [reasonable date]

Return only the draft text, no preamble.
```

**Tone Detection:**
- `@company.com` → professional
- `@gmail.com`, `@yahoo.com` → casual
- `.edu`, `.gov` → formal

**n8n Integration:**
```
→ IF label=action-required:
  → POST /drafts/generate
  → Gmail Create Draft
  → Store draft_id in email_metadata
```

**Configuration** (labels.yaml):
```yaml
settings:
  auto_draft_enabled: true
  auto_draft_labels: ["action-required"]
  draft_tone: "professional"
```

Drafts saved to Gmail but never auto-sent. User reviews manually.

---

## Archive Policies

**Feature:** Auto-archive old emails based on label, age, and read status.

**Endpoint:** `GET /archive/candidates?policy=default`

**Configuration** (labels.yaml):
```yaml
archive_policies:
  notifications:
    age_days: 7
    read_required: false

  newsletters:
    age_days: 3
    read_required: true

  finance:
    age_days: 90
    read_required: false

  promotions:
    age_days: 1
    read_required: false

  # Safety: never archive these
  exclude_labels: ["action-required", "security", "needs-review"]
```

**Logic:**
1. Query email_metadata for emails older than `age_days`
2. Filter by label
3. If `read_required=true`, only include read emails
4. Exclude any email with excluded labels
5. Return list of email_ids

**n8n Weekly Path:**
```
→ GET /archive/candidates
→ Gmail Archive (bulk, 100 per batch)
→ POST /email_metadata/mark_archived
→ Include count in weekly digest
```

---

## Configuration Extensions

**labels.yaml additions:**

```yaml
settings:
  # Existing
  llm_provider: "claude"
  confidence_threshold: 0.7
  max_emails_per_run: 100
  suggestion_file: "suggestions.json"

  # New
  auto_draft_enabled: true
  auto_draft_labels: ["action-required"]
  draft_tone: "professional"

  follow_up_overdue_days: 3
  promotion_threshold: 5

  telegram_bot_token: "${TELEGRAM_BOT_TOKEN}"
  telegram_chat_id: "${TELEGRAM_CHAT_ID}"

archive_policies:
  notifications:
    age_days: 7
    read_required: false
  newsletters:
    age_days: 3
    read_required: true
  finance:
    age_days: 90
    read_required: false
  promotions:
    age_days: 1
    read_required: false
  exclude_labels: ["action-required", "security", "needs-review"]
```

---

## Project Structure Updates

```
sortbox/
├── src/
│   ├── main.py
│   ├── models.py              # Add: FollowUp, PromotionCounter, etc.
│   ├── config.py
│   ├── database.py            # NEW: SQLAlchemy models + session
│   ├── classifier/
│   │   ├── rules.py
│   │   ├── llm_classifier.py
│   │   ├── service.py
│   │   └── providers/
│   ├── follow_ups.py          # NEW: Follow-up tracking logic
│   ├── promotions.py          # NEW: Promotion counter logic
│   ├── digests.py             # NEW: Digest generation
│   ├── drafts.py              # NEW: Draft reply generation
│   ├── archive.py             # NEW: Archive policy evaluation
│   └── suggestions.py         # NEW: Label suggestion approval
├── n8n/
│   ├── workflow.json          # Basic classify workflow
│   └── orchestrator.json      # NEW: Full orchestrator workflow
├── sortbox.db                 # NEW: SQLite database (gitignored)
├── labels.yaml
├── Makefile
├── Dockerfile
└── README.md
```

---

## Implementation Order

1. **Database setup** - SQLite schema, SQLAlchemy models
2. **Follow-ups API** - Track, pending, resolve endpoints
3. **Promotions API** - Track, offenders endpoints
4. **Digests API** - Daily, weekly endpoints
5. **Draft generation** - LLM-based reply drafting
6. **Archive policies** - Candidate selection logic
7. **Suggestions API** - Approve, pending, auto-update labels.yaml
8. **n8n orchestrator** - Build unified workflow with all paths
9. **Telegram integration** - Bot setup, callback handlers
10. **Testing** - Integration tests for each feature

---

## Testing Strategy

**Unit tests:**
- Archive policy logic with mock email_metadata
- Digest aggregation with fixture data
- Draft generation with mocked LLM

**Integration tests:**
- Follow-up tracking → pending → resolve flow
- Promotion counter increments
- Suggestion approval → labels.yaml update

**E2E test:**
- Mock Gmail API
- Trigger orchestrator
- Verify state changes in SQLite
- Verify notification calls

Target: 80%+ coverage on new code.

---

## Deployment

**Docker updates:**
- Mount sortbox.db volume for persistence
- Add Telegram env vars

**Dockerfile:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev
COPY src/ src/
COPY labels.yaml .
VOLUME /app/data
ENV DATABASE_PATH=/app/data/sortbox.db
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**n8n setup:**
1. Import `n8n/orchestrator.json`
2. Configure Gmail OAuth2 credentials
3. Configure Telegram bot credentials
4. Set environment variables
5. Activate workflow

---

## Security Considerations

- SQLite database contains sensitive email metadata → restrict file permissions
- Telegram bot token → store in n8n credentials, never commit
- Gmail API scopes → request minimal permissions (read, modify labels, create drafts)
- Draft generation → never auto-send, only save as draft
- Archive policies → exclude critical labels to prevent data loss

---

## Future Enhancements

- **Multi-account support** - Handle multiple Gmail accounts
- **Analytics dashboard** - Web UI for stats and trends
- **Smart threading** - Group related emails into conversations
- **VIP senders** - Priority routing for specific contacts
- **Scheduled send** - Queue drafts for later sending
- **AI summarization** - Summarize long email threads
