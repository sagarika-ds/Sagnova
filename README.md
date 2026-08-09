📰 Sags News

AI-powered, personalized news briefing app — pulls live news across 20+ categories, deduplicates similar stories, and uses Google Gemini to summarize, score, and explain why each story matters.

✨ Features
20+ live topic categories — AI, Tech, Finance, World, India, Sports, Entertainment, Science, Space, Health, Cybersecurity, Startups, Programming, K-Pop, Music, Dance, Pop Culture, Awards Shows, Travel, Mountains, Beaches
AI-generated summaries — every story gets a 2-3 line summary, a "why it matters" line, and a 5-dimension relevance score (importance, India impact, career relevance, financial impact, AI relevance)
Smart deduplication — near-identical stories from different publishers are merged before hitting the AI, saving quota and avoiding repeat reads
Time-based caching — results are cached for 3 hours per category to protect free-tier API limits
Real source links — every card links to the original article; AI never invents URLs, only picks from real fetched articles
Cinematic UI — hero landing page with a personal photo background, live clock, glassmorphic floating topic list, and a game-style "burst" transition into each topic page

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

