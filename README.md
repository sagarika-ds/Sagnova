📰 Sags News

AI-powered, personalized news briefing app — pulls live news across 20+ categories, deduplicates similar stories, and uses Google Gemini to summarize, score, and explain why each story matters.

✨ Features
20+ live topic categories — AI, Tech, Finance, World, India, Sports, Entertainment, Science, Space, Health, Cybersecurity, Startups, Programming, K-Pop, Music, Dance, Pop Culture, Awards Shows, Travel, Mountains, Beaches
AI-generated summaries — every story gets a 2-3 line summary, a "why it matters" line, and a 5-dimension relevance score (importance, India impact, career relevance, financial impact, AI relevance)
Smart deduplication — near-identical stories from different publishers are merged before hitting the AI, saving quota and avoiding repeat reads
Time-based caching — results are cached for 3 hours per category to protect free-tier API limits
Real source links — every card links to the original article; AI never invents URLs, only picks from real fetched articles
Cinematic UI — hero landing page with a personal photo background, live clock, glassmorphic floating topic list, and a game-style "burst" transition into each topic page

 How the Project Actually Runs (Data Flow)

User clicks a topic 
        │
        ▼
Frontend (Netlify) sends a request to:
        │
        ▼
Backend (Render) checks cache.json
   │                              │
   │ cached & <3hrs old           │ not cached / stale
   ▼                              ▼
Return cached JSON        Call GNews API → raw articles
   instantly                     │
                                  ▼
                          Cheap dedup (difflib)
                                  │
                                  ▼
                     Call Gemini API → summarize,
                     score, categorize each story
                                  │
                                  ▼
                       Save result to cache.json
                                  │
                                  ▼
                        Return JSON to frontend
        │
        ▼
Frontend renders story cards with the
themed background + burst animation


Project Folder Structure

Sagnova/                        (GitHub repo root)
│
├── index.html                  ← entire frontend: HTML + CSS + JS in one file
├── Sg.jpg                      ← hero background photo
├── netlify.toml                ← tells Netlify: no build step, serve as-is
├── package.json                ← minimal file, helps Netlify detect this
│                                  as a static site (not a Python project)
├── README.md
├── .gitignore                  ← excludes .env, venv/, cache.json, __pycache__
│
└── backend/                    ← everything Render needs, isolated
    ├── main.py                 ← the FastAPI app: all backend logic
    ├── requirements.txt        ← Python package list
    ├── .python-version         ← pins Python 3.11 for this folder
    ├── .env                    ← real API keys (NEVER committed)
    ├── .env.example            ← template showing what keys are needed
    └── cache.json              ← auto-generated at runtime (gitignored)

    
🧰 Tech Stack
Layer	Technology
Backend	Python 3.11, FastAPI, Uvicorn
AI	Google Gemini (gemini-flash-lite-latest)
News Source	GNews API
Frontend	Vanilla HTML, CSS, JavaScript (no framework, no build step)
Fonts	Playfair Display, Space Grotesk (Google Fonts)
Backend Hosting	Render (free tier)
Frontend Hosting	Netlify (free tier)
Version Control	Git + GitHub


📄 License
Personal project — all rights reserved.
