"""
AI News Intelligence Hub — Backend (v2, Gemini)
--------------------------------------------------
Fetches raw news from GNews, deduplicates near-identical stories,
then asks Gemini to summarize, categorize, score, and link each one.

Run with:  uvicorn main:app --reload --port 8001
"""

import os
import json
import time
from pathlib import Path
from difflib import SequenceMatcher
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY in .env")
if not GNEWS_API_KEY:
    raise RuntimeError("Missing GNEWS_API_KEY in .env")

genai.configure(api_key=GEMINI_API_KEY)
# Flash-Lite has a noticeably higher free-tier request quota than the
# newest flagship Flash model, which matters a lot for a hobby project
# that fires several category calls per click.
MODEL = genai.GenerativeModel("gemini-flash-lite-latest")

# ---------- Simple file-based cache ----------
# Avoids re-calling Gemini for a category you already fetched recently.
# Cached results expire after CACHE_TTL_SECONDS and get refetched.

CACHE_FILE = Path(__file__).parent / "cache.json"
CACHE_TTL_SECONDS = 3 * 60 * 60  # 3 hours


def load_cache() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_cache(cache: dict) -> None:
    try:
        CACHE_FILE.write_text(json.dumps(cache))
    except OSError:
        pass  # cache is a nice-to-have, never fail the request over it


def get_cached_stories(category: str) -> Optional[List[dict]]:
    cache = load_cache()
    entry = cache.get(category)
    if not entry:
        return None
    if time.time() - entry["fetched_at"] > CACHE_TTL_SECONDS:
        return None  # expired
    return entry["stories"]


def set_cached_stories(category: str, stories: List[dict]) -> None:
    cache = load_cache()
    cache[category] = {"fetched_at": time.time(), "stories": stories}
    save_cache(cache)

app = FastAPI(title="AI News Intelligence Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sagnova.netlify.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every topic pill the frontend can show. Add more here any time —
# the frontend reads this list automatically via /categories.
CATEGORY_QUERIES = {
    "AI":            "artificial intelligence OR large language model OR AI model release",
    "Tech":          "technology OR smartphone OR Apple OR Google OR software",
    "Finance":       "stock market OR Sensex OR Nifty OR economy India",
    "World":         "world news OR international relations OR geopolitics",
    "India":         "India news OR India policy OR India government",
    "Sports":        "cricket OR football match result OR sports",
    "Entertainment": "movie release OR box office OR bollywood OR hollywood",
    "Science":       "science discovery OR research breakthrough",
    "Space":         "space exploration OR NASA OR ISRO OR satellite",
    "Health":        "health news OR medical breakthrough OR public health",
    "Cybersecurity": "cybersecurity OR data breach OR hacking",
    "Startups":      "startup funding OR venture capital OR unicorn",
    "Programming":   "programming language OR software engineering OR developer tools",
    "Career":        "job market OR hiring trends OR career India",
    "K-Pop":         '"K-pop" OR "HYBE" OR "BTS" OR "BLACKPINK"',
    "Music":         '"Grammys" OR "music charts" OR "album release"',
    "Dance":         "dance performance OR choreography OR dance competition",
    "Pop Culture":   '"celebrity news" OR "viral trend" OR "pop culture"',
    "Awards Shows":  '"award show" OR "Oscars" OR "Grammys" OR "Emmys" OR "Met Gala"',
    "Intl Travel":   '"international travel" OR "tourism" OR "travel destination"',
    "India Travel":  '"India tourism" OR "India travel" OR "Incredible India"',
    "Mountains":     '"Himalayas" OR "mountain trekking" OR "hill station"',
    "Beaches":       '"beach destination" OR "island getaway" OR "coastal tourism"',
}

CATEGORY_EMOJI = {
    "AI": "🔥", "Tech": "💻", "Finance": "📈", "World": "🌍", "India": "🇮🇳",
    "Sports": "⚽", "Entertainment": "🎬", "Science": "🔬", "Space": "🚀",
    "Health": "🩺", "Cybersecurity": "🛡️", "Startups": "🚀", "Programming": "👨‍💻",
    "Career": "💼", "K-Pop": "💜", "Music": "🎵", "Dance": "💃",
    "Pop Culture": "✨", "Awards Shows": "🏆",
    "Intl Travel": "✈️", "India Travel": "🛺", "Mountains": "🏔️", "Beaches": "🏖️",
}


# ---------- Data models ----------

class Story(BaseModel):
    category: str
    headline: str
    summary: str
    why_it_matters: str
    importance: int
    india_impact: int
    career_relevance: int
    financial_impact: int
    ai_relevance: int
    source_name: str
    source_url: str


class BriefingResponse(BaseModel):
    greeting: str
    stories: List[Story]


class AskRequest(BaseModel):
    headline: str
    summary: str
    question: str


# ---------- Step 1: fetch raw articles ----------

async def fetch_articles_for_category(category: str, max_results: int = 10) -> List[dict]:
    query = CATEGORY_QUERIES.get(category, category)
    url = "https://gnews.io/api/v4/search"
    params = {
        "q": query,
        "lang": "en",
        "max": max_results,
        "sortby": "publishedAt",
        "apikey": GNEWS_API_KEY,
    }
    async with httpx.AsyncClient(timeout=20) as http:
        resp = await http.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    return data.get("articles", [])


# ---------- Step 2: cheap dedup before we even call Gemini (saves quota) ----------

def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def dedupe_articles(articles: List[dict], threshold: float = 0.6) -> List[dict]:
    unique: List[dict] = []
    for article in articles:
        title = article.get("title", "")
        if not title:
            continue
        is_dupe = any(title_similarity(title, u.get("title", "")) > threshold for u in unique)
        if not is_dupe:
            unique.append(article)
    return unique


# ---------- Step 3: ask Gemini to summarize + score ----------
# We pass each article an index number and ask Gemini to reference it back,
# so we can attach the REAL article URL ourselves afterwards — this avoids
# the LLM ever having to (mis)type a URL from scratch.

SYSTEM_INSTRUCTIONS = """You are a news analyst producing a personalized morning briefing.
You will be given a numbered list of raw articles for one category.

Select the 5 most important DISTINCT stories (merge near-duplicates yourself).
Always return exactly 5 stories if at least 5 distinct articles exist — do not under-select.

For each selected story return:
- source_index: the number of the article you based this on (integer, required)
- headline: short, punchy, no clickbait
- summary: 2-3 sentences, factual, no editorializing
- why_it_matters: 1 sentence, plain language
- importance: 1-10
- india_impact: 1-10 (0 if genuinely irrelevant to India)
- career_relevance: 1-10 (0 if not relevant to general knowledge workers)
- financial_impact: 1-10 (0 if none)
- ai_relevance: 1-10 (0 if none)

Respond ONLY with valid JSON: a list of objects with exactly those fields.
No markdown fences, no preamble, no commentary."""


def summarize_category(category: str, articles: List[dict]) -> List[dict]:
    if not articles:
        return []

    numbered = list(enumerate(articles))
    raw_text = "\n\n".join(
        f"[{i}] Title: {a.get('title')}\nSource: {a.get('source', {}).get('name')}\n"
        f"Description: {a.get('description')}"
        for i, a in numbered
    )

    prompt = f"{SYSTEM_INSTRUCTIONS}\n\nCategory: {category}\n\nArticles:\n{raw_text}"

    response = MODEL.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(max_output_tokens=2000),
    )

    text = response.text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        picks = json.loads(text)
    except json.JSONDecodeError:
        return []

    stories = []
    for pick in picks:
        idx = pick.pop("source_index", None)
        if idx is None or idx >= len(articles):
            continue
        article = articles[idx]
        pick["category"] = category
        pick["source_name"] = article.get("source", {}).get("name", "Unknown")
        pick["source_url"] = article.get("url", "")
        stories.append(pick)

    return stories


# ---------- Routes ----------

@app.get("/categories")
def get_categories():
    """Lets the frontend build topic pills without hardcoding the list."""
    return [{"name": c, "emoji": CATEGORY_EMOJI.get(c, "📰")} for c in CATEGORY_QUERIES]


@app.get("/briefing", response_model=BriefingResponse)
async def get_briefing(
    categories: Optional[str] = "AI,Tech,Finance,World,India,Sports,Entertainment",
    name: str = "there",
):
    """Main endpoint: returns the full briefing for the requested categories."""
    selected = [c.strip() for c in categories.split(",") if c.strip() in CATEGORY_QUERIES]
    if not selected:
        raise HTTPException(400, "No valid categories selected")

    all_stories: List[dict] = []
    for category in selected:
        cached = get_cached_stories(category)
        if cached is not None:
            all_stories.extend(cached)
            continue

        raw = await fetch_articles_for_category(category)
        deduped = dedupe_articles(raw)
        stories = summarize_category(category, deduped)
        set_cached_stories(category, stories)
        all_stories.extend(stories)

    return BriefingResponse(
        greeting=f"Hello, {name}!",
        stories=[Story(**s) for s in all_stories],
    )


@app.post("/ask")
async def ask_followup(req: AskRequest):
    """Lets the user ask 'explain like I'm 10' / 'more technical' / 'India impact' etc."""
    prompt = (
        f"Story headline: {req.headline}\n"
        f"Story summary: {req.summary}\n\n"
        f"User question: {req.question}\n\n"
        "Answer directly and concisely."
    )
    response = MODEL.generate_content(prompt)
    return {"answer": response.text.strip()}


@app.get("/health")
def health():
    return {"status": "ok"}
