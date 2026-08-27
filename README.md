# Mail Intelligence — Local Gmail Analyzer + LM Studio

A local-first Gmail intelligence app. Gmail is the source of truth; the app keeps a local analysis/cache database and uses LM Studio for optional classification and mailbox-aware chat.

## V1 features

- Gmail OAuth (read-only)
- Full and incremental Gmail sync
- SQLite local cache
- Sender and domain analytics
- Subscription/newsletter detection
- Heuristic usefulness + priority scoring
- Optional LM Studio semantic classification
- Optional local embeddings and semantic search
- Hybrid keyword + semantic search
- Review Later queue
- Explicit useful/not-useful feedback
- Mailbox-aware chatbot with evidence/source emails
- No Gmail delete/archive/send operations in V1

## Architecture

```text
Gmail API (source of truth)
        | OAuth read-only
        v
FastAPI Gmail gateway -> parser -> SQLite + FTS
                            |
                  rules / analytics / feedback
                            |
           +----------------+----------------+
           |                                 |
           v                                 v
      LM Studio LLM                 LM Studio embeddings
           |                                 |
           +--------------+------------------+
                          v
                 Chat / Hybrid retrieval
                          |
                          v
                    React + Vite UI
```

## 1. Prerequisites

- macOS, Linux, or Windows
- Python 3.9+
- Node.js 20.19+ (or a current Node 22 release)
- LM Studio installed
- A Google account

## 2. Google Cloud / Gmail API setup

1. Open Google Cloud Console.
2. Create or select a project.
3. Enable **Gmail API** for that project.
4. Configure the OAuth consent screen. For personal development, add your Gmail address as a test user if Google asks for one.
5. Create OAuth credentials of type **Desktop app**.
6. Download the JSON file.
7. Rename it to `credentials.json`.
8. Put it here:

```text
backend/secrets/credentials.json
```

Do not commit this file.

The app requests only:

```text
https://www.googleapis.com/auth/gmail.readonly
```

## 3. LM Studio

1. Open LM Studio.
2. Load a chat/instruct model.
3. Start the local API server (default port 1234).
4. Optional: load an embedding model as well.
5. Copy `backend/.env.example` to `backend/.env` and set model IDs exactly as LM Studio reports them.

Example:

```env
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
LMSTUDIO_CHAT_MODEL=mistral-7b-instruct-v0.1
LMSTUDIO_EMBEDDING_MODEL=
```

Leave `LMSTUDIO_EMBEDDING_MODEL` blank to disable semantic embeddings initially. Keyword/FTS search still works.

## 4. Start the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend docs:

```text
http://127.0.0.1:8000/docs
```

## 5. Start the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally:

```text
http://127.0.0.1:5173
```

## 6. First use

1. Open **Settings**.
2. Click **Connect Gmail**.
3. Google opens in your browser; grant read-only Gmail permission.
4. Back in the app, choose a history window (30/90/365 days or all).
5. Click **Full Sync**.
6. Wait for the job card to reach `done`.
7. Dashboard, Senders, Subscriptions, and Inbox will immediately work from local SQLite.
8. If LM Studio is running, use **AI classify** to enrich uncertain messages.
9. If an embedding model is configured, click **Index embeddings**.
10. Open **Chat** and ask questions about your mailbox.

## Sync behavior

- Full sync stores Gmail's latest `historyId`.
- Incremental sync asks Gmail History API what changed after that ID.
- Changed messages are re-fetched so labels/read state stay current.
- If Gmail reports that a history ID is too old/invalid, run Full Sync again.

## Privacy model

- OAuth tokens stay under `backend/secrets/`.
- Mail content stays in local SQLite.
- Embeddings stay local.
- LM Studio receives only the messages/evidence needed for classification/chat.
- The LLM never receives OAuth credentials.
- V1 cannot modify Gmail.

## Important limitation

Gmail exposes current labels such as `UNREAD`; it does not provide historical email-open analytics. This app begins observing read/unread changes from the time it starts syncing.

## Useful API endpoints

```text
GET  /api/status
POST /api/auth/connect
POST /api/sync/full
POST /api/sync/incremental
GET  /api/jobs/{job_id}
GET  /api/dashboard
GET  /api/messages
GET  /api/senders
GET  /api/subscriptions
GET  /api/review-later
POST /api/messages/{id}/review-later
POST /api/messages/{id}/feedback
POST /api/ai/classify-pending
POST /api/embeddings/index-pending
POST /api/chat
```

## Development notes

This is deliberately a safe V1. Do not add `gmail.modify` until the product has an explicit approval layer for archive/delete/label/unsubscribe actions.
