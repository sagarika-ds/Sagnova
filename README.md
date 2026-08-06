# AI News Intelligence Hub — Step-by-Step Setup (macOS + VS Code)

This is a working MVP: a FastAPI backend that pulls news, deduplicates it,
and asks Claude to summarize + score it, plus a simple frontend to view it.
No database, no Next.js build step — you can be running this in ~15 minutes,
then extend it from there.

---

## 0. What you'll need (all free)

- **VS Code** — https://code.visualstudio.com
- **Python 3.11+** — check with `python3 --version` in Terminal
- **An Anthropic API key** — https://console.anthropic.com → Settings → API Keys
- **A GNews API key** (free tier, 100 requests/day) — https://gnews.io/register

---

## 1. Open the project in VS Code

1. Unzip / place the `ai-news-hub` folder somewhere like `~/Projects/`
2. Open VS Code → File → Open Folder → select `ai-news-hub`
3. Install the **Python extension** in VS Code if prompted (Microsoft's official one)

---

## 2. Set up the backend

Open VS Code's built-in terminal (`Terminal → New Terminal`) and run:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

You'll now see `(venv)` at the start of your terminal prompt — that means
you're inside an isolated Python environment for this project.

---

## 3. Add your API keys

```bash
cp .env.example .env
```

Open the new `.env` file in VS Code and paste in your real keys:

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
GNEWS_API_KEY=xxxxxxxxxxxxxxxxxxxxx
```

Save the file. **Never commit `.env` to git** — it's already excluded via
the pattern below (add a `.gitignore` if you plan to push this to GitHub):

```
venv/
.env
__pycache__/
```

---

## 4. Run the backend

Still inside `backend/` with `(venv)` active:

```bash
uvicorn main:app --reload --port 8000
```

You should see something like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Test it's alive by opening **http://localhost:8000/health** in your browser
— you should see `{"status":"ok"}`.

Try the real endpoint (this one takes 10-30 seconds, it's calling Claude):
**http://localhost:8000/briefing?name=Sagarika&categories=AI,Tech,India**

---

## 5. Run the frontend

You don't need Node.js for this MVP — it's a plain HTML file.

1. In VS Code, right-click `frontend/index.html`
2. Choose **"Open with Live Server"** (install the "Live Server" extension
   by Ritwick Dey if you don't have it — Extensions panel → search "Live Server")
   — or just double-click `index.html` in Finder to open it in your browser.
3. Make sure your backend (step 4) is still running in the other terminal tab.

You should now see your personalized briefing render in the browser, with
tappable "Ask" boxes under each story ("explain like I'm 10", etc.)

---

## 6. Folder structure

```
ai-news-hub/
├── backend/
│   ├── main.py           ← FastAPI app: fetch → dedupe → summarize → score
│   ├── requirements.txt
│   ├── .env               ← your real keys (gitignored)
│   └── .env.example
├── frontend/
│   └── index.html         ← single-file UI, no build step
└── README.md
```

---

## 7. How it works, end to end

1. `GET /briefing?categories=AI,Tech,India` hits the backend
2. For each category, `fetch_articles_for_category()` calls the GNews API
3. `dedupe_articles()` does a cheap title-similarity pass (no LLM cost) to
   drop obvious duplicates before they're even sent to Claude
4. `summarize_category()` sends the remaining articles to Claude
   (`claude-sonnet-5`) with a system prompt that forces structured JSON:
   headline, summary, why-it-matters, and the 5 impact scores
5. The frontend renders each story as a card with score badges
6. The "Ask" box on each card hits `POST /ask` — same story context,
   your custom question, one more Claude call

---

## 8. Extending it (in order of effort)

**Easy — do these next:**
- Add more categories to `CATEGORY_QUERIES` in `main.py` (Cybersecurity,
  Startups, Space, Health…)
- Add a "1-minute / 5-minute / 10-minute" toggle: pass a `length` param
  through to the system prompt to control summary verbosity
- Cache results for the day in a local SQLite file so you're not re-calling
  GNews + Claude every time you refresh (add `aiosqlite`, one new table)

**Medium:**
- Swap the plain HTML frontend for Next.js once you want routing, auth,
  or a nicer component structure — the API contract (`/briefing`, `/ask`)
  doesn't need to change
- Add a "Biggest news of the week" endpoint that stores each day's stories
  and asks Claude to pick the top 5 across the last 7 days
- Add the bias-comparison feature: fetch the *same* story from 2-3 sources
  and ask Claude to diff the framing, not just summarize one version

**Bigger:**
- **Telegram bot** for the "AI News Agent" idea — `python-telegram-bot`,
  a scheduled job (APScheduler or a cron `curl` to a `/send-digest`
  endpoint) that posts your briefing to a chat every morning
- **Vector DB (ChromaDB)** for "ask questions about anything from the last
  30 days" — embed each story on ingest, do retrieval before calling Claude
- **Text-to-speech** for the podcast-style briefing — feed the day's
  summaries to a TTS API (e.g. ElevenLabs, or macOS's built-in `say`
  command for a free local prototype) and serve the audio file

---

## 9. Common issues

- **`RuntimeError: Missing ANTHROPIC_API_KEY`** → your `.env` wasn't
  created/saved, or you're running `uvicorn` from the wrong folder
- **CORS error in browser console** → make sure the backend is running on
  port 8000 and `frontend/index.html`'s `API_BASE` matches
- **GNews returns very few articles** → free tier is capped at 100
  requests/day and sometimes returns thin results for narrow queries —
  broaden the query in `CATEGORY_QUERIES` if a category looks empty
- **Slow response on `/briefing`** → this is normal for the MVP: each
  category is one sequential GNews call + one sequential Claude call.
  Easy speed win: switch the `for category in selected` loop to
  `asyncio.gather()` so categories fetch in parallel
