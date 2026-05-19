# PathFinder — UDel Career Mapper

**PathFinder** is an AI-powered career exploration platform built exclusively for University of Delaware students. It connects **8,354 UDel courses** across **46 academic programs** to **920+ real-world career paths**, helping students make data-driven decisions about their academic journey.

**Live App:** Deployed on Railway
**University:** University of Delaware
**Course:** CPEG 657 (Search & Data Mining) — Spring 2026 Final Project
**Data:** Scraped directly from the official UDel Course Catalog (2025–2026)

---

## What It Does

PathFinder answers the question every student asks: *"What can I actually do with my degree?"*

- **Explore 920+ career paths** across 46 programs — from Software Engineer to Forensic Accountant — each with salary ranges and demand levels
- **Browse 8,354 courses** (5,014 undergrad + 3,340 grad) with full descriptions, searchable by department, level, and keyword
- **AI-powered course matching** uses FAISS semantic search to map each career to the exact UDel courses that build job-relevant skills
- **Smart semester roadmaps** generate personalized 2-semester plans based on your major, career goal, and current year
- **PathFinder AI chatbot** answers any question about UDel programs, courses, elective strategy, and career planning — with real program data and RAG-retrieved context injected into every response
- **Cross-program exploration** shows students how to use their elective slots to pivot toward a different career field without switching majors

---

## Architecture

```
+---------------------------------------------+
|              Frontend (index.html)           |
|  Vanilla JS · Fuse.js search · Dark mode    |
|  Font Awesome · Inter font · CSS Grid       |
+------------------+---------------------------+
                   | REST API
+------------------v---------------------------+
|            Backend (app.py - Flask)          |
|                                             |
|  /api/courses      -> Browse & search       |
|  /api/career-paths -> Job <-> course mapping|
|  /api/ai-match     -> FAISS course suggest  |
|  /api/roadmap      -> Semester plan (RAG)   |
|  /api/chat         -> AI chatbot (RAG)      |
|  /api/search       -> Semantic career search|
|  /api/program-info -> Program requirements  |
|  /api/stats        -> Dashboard counters    |
|                                             |
|  Groq llama-3.3-70b  -> Chat & roadmaps     |
|  Groq llama-3.1-8b   -> Fallback model      |
+------------------+---------------------------+
                   |
+------------------v---------------------------+
|              RAG Layer (rag/)                |
|                                             |
|  retriever.py  -> FAISS semantic search     |
|  pipeline.py   -> RAG orchestration         |
|  llm_client.py -> Groq API client           |
|  build_index.py-> Index builder             |
|                                             |
|  BAAI/bge-small-en-v1.5  -> Embeddings      |
|  FAISS IVF index          -> Vector search  |
|  indices/courses.faiss    -> 8,354 courses  |
|  indices/careers.faiss    -> 920 careers    |
+------------------+---------------------------+
                   |
+------------------v---------------------------+
|              Data Layer (JSON files)         |
|                                             |
|  all_courses.json          -> 8,354 courses |
|  all_jobs.json             -> 920 career roles|
|  program_courses.json      -> Curricula maps|
|  program_requirements.json -> Degree reqs   |
|  curated_jobs.json         -> Seed careers  |
+---------------------------------------------+
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla HTML/CSS/JS, Fuse.js (fuzzy search), Font Awesome, Google Fonts (Inter) |
| Backend | Python 3.11, Flask, Flask-CORS, Flask-Compress, Gunicorn |
| AI / LLM | Groq API — llama-3.3-70b-versatile (chat & roadmaps), llama-3.1-8b-instant (fallback) |
| Embeddings | sentence-transformers — BAAI/bge-small-en-v1.5 |
| Vector Search | FAISS (Facebook AI Similarity Search) |
| Data Collection | BeautifulSoup4, Requests, concurrent.futures (ThreadPoolExecutor) |
| Deployment | Railway (backend), Gunicorn with gthread workers |

---

## Data Pipeline

All data is scraped from official University of Delaware sources — no manual entry.

### 1. Course Scraping (`scraper.py` + `scrape_grad_courses.py`)

Crawls the UDel Advanced Course Search (catoid 94 for undergrad, 93 for grad). Paginates through every results page, extracts course code, department, title, and catalog URL. Fetches individual course pages for full descriptions (2,000 char limit). Deduplicates by course ID (coid) and tags each as `undergrad` or `grad`.

**Output:** `all_courses.json` — 8,354 courses with code, dept, number, title, description, URL, and level

### 2. Program Requirements (`scrape_programs.py`)

Scrapes every college page in both undergrad and grad catalogs (8 colleges × 2 levels). For each program: extracts requirements text, total credits, and all mentioned course codes. Uses proximity-based NLP to classify courses as core vs. elective by scanning backward from each course code to the nearest section header.

**Output:** `program_requirements.json` — 481 programs with full requirements text and course classifications

### 3. Curriculum Mapping (`scrape_programs_v2.py`)

Scrapes the UDel Major Finder year-by-year accordion panels. Targets `div.accordian.section` (UDel's intentional typo) to avoid sidebar/footer noise. Extracts real course codes with regex, filters noise departments (HTTP, GPA, GTM, etc.). Separates undergrad (100–499) from grad (500+) courses per program.

**Output:** `program_courses.json` — 44 programs with official curriculum course codes

### 4. Career Database (`build_careers.py` -> `expand_jobs.py` -> `add_salaries.py`)

- **Seed:** `build_careers.py` creates 60 hand-curated career paths across 6 core programs
- **Expand:** `expand_jobs.py` uses an LLM to generate up to 20 jobs per program, matching skills to real UDel course titles
- **Salaries:** `add_salaries.py` enriches every job with salary ranges and demand levels sourced from BLS, Glassdoor, and LinkedIn Salary data (2024–2025)
- **Patch:** `patch_salaries.py` catches any remaining jobs missing salary data and fills them via LLM

**Output:** `all_jobs.json` — 920 career roles across 46 programs, each with title, description, skills, salary_min/max, and demand

### 5. Description Repair (`fix_descriptions.py`)

Re-fetches descriptions for any courses with empty descriptions. Uses smaller batches (15) with polite delays to avoid rate limiting. Threaded execution (8 workers) for speed.

### 6. FAISS Index Building (`rag/build_index.py`)

Embeds all courses and career roles using `BAAI/bge-small-en-v1.5` and stores them in two FAISS indices for fast semantic retrieval at query time.

**Output:** `rag/indices/courses.faiss` + `rag/indices/careers.faiss` (+ `*_meta.json` sidecar files)

---

## RAG Architecture

PathFinder v2 uses a **Retrieval-Augmented Generation (RAG)** pipeline for all AI features:

```
User Query
    |
    v
FAISS Semantic Search  (BAAI/bge-small-en-v1.5 embeddings)
    |
    +-- Top-k relevant courses  (from courses.faiss)
    +-- Top-k relevant careers  (from careers.faiss)
    |
    v
Augmented Prompt  (retrieved context injected into system prompt)
    |
    v
Groq LLM  (llama-3.3-70b-versatile)
    |
    v
Response
```

**Retrieval** is handled by `rag/retriever.py` — a lazy-loading singleton that keeps the BGE model and FAISS indices in memory across requests. **Orchestration** lives in `rag/pipeline.py`, which builds the augmented prompts and calls the Groq client. **Generation** is handled by `rag/llm_client.py`, which implements automatic fallback from `llama-3.3-70b` to `llama-3.1-8b-instant` on any API error.

---

## How Course Matching Works

PathFinder uses a **weighted scoring system** to connect careers to relevant courses:

| Signal | Points | Why |
|--------|--------|-----|
| Skill keyword in course title | +4 per match | Titles are the strongest relevance signal |
| Primary skill (first listed) in title | +6 bonus | The most important skill gets extra weight |
| Skill keyword in description | +1 per match | Descriptions add context but are noisy |
| Preferred department match | +2 | Ensures CISC courses rank higher for CS jobs |

Minimum score threshold: **4 points** (at least one title match or strong description + dept match). Results are deduplicated by normalized title and separated into undergrad vs. grad buckets.

For deeper matching, the **AI Match endpoint** uses FAISS to semantically retrieve the 8 best undergraduate and 8 best graduate courses, filtered by preferred departments for the program.

---

## Core vs. Elective Classification

The app parses program requirements text using **proximity-based NLP**:

1. Identifies all section headers in the requirements text (e.g., "Core Courses:", "Restricted Electives:", "Choose from:")
2. For each course code found in the text, scans backward to find the nearest section header
3. Classifies based on header keywords: `required`, `core`, `must complete` -> Core; `elective`, `choose from`, `select` -> Elective
4. Courses near no header default to Core (conservative approach)
5. Any courses in `courses_mentioned` but not classified as core are treated as electives

This powers the Core and Elective badges throughout the UI and the AI chatbot's elective strategy advice.

---

## Key Features

### AI Chatbot (RAG-powered)

The chatbot uses Groq (llama-3.3-70b) with a detailed system prompt containing all program data. On each request, FAISS retrieves the top-5 semantically relevant courses and top-3 careers, which are injected as a "RETRIEVED CONTEXT" block. It detects the student's enrolled program from natural language, injects that program's core and elective course lists, and enforces a strict rule: **only recommend courses from the student's approved elective list**.

### Smart Search

Handles typos, natural language, and vague queries. "high paying jobs" -> filters by salary + demand. "I like helping people" -> surfaces healthcare, education, and social work roles. "data engneer" -> correctly maps to Data Engineer. Powered by FAISS semantic search — over-fetches 40 results and deduplicates by title to return the top 10.

### Semester Roadmaps

Generates a 2-semester plan (Fall + Spring) tailored to the student's current year, using only real course codes from their program. FAISS retrieves supplementary course options to prevent hallucinated course codes. Auto-marks lower-level courses as completed based on year standing. Each course includes a one-sentence explanation of how it builds skills for the target career.

### Dark Mode

Full dark mode support with CSS custom properties. Toggles via nav button with state persistence.

---

## Project Structure

```
PathFinder/
|-- app.py                      # Flask backend — all API endpoints
|-- index.html                  # Single-page frontend
|-- style.css                   # Stylesheet with dark mode
|-- Procfile                    # Railway deployment config
|-- requirements.txt            # Python dependencies
|-- package.json                # Node dependencies
|
|-- rag/                        # RAG pipeline
|   |-- __init__.py
|   |-- build_index.py          # FAISS index builder (run once)
|   |-- retriever.py            # FAISS semantic search
|   |-- pipeline.py             # RAG orchestration (chat + roadmap)
|   |-- llm_client.py           # Groq LLM client with fallback
|   +-- indices/
|       |-- courses.faiss       # Course vector index
|       |-- courses_meta.json   # Course metadata sidecar
|       |-- careers.faiss       # Career vector index
|       +-- careers_meta.json   # Career metadata sidecar
|
|-- evaluation/                 # Retrieval evaluation
|   |-- test_set.json           # 50 hand-labeled student queries
|   +-- run_eval.py             # Scores retrieval@5 and retrieval@10
|
|-- all_courses.json            # 8,354 UDel courses (undergrad + grad)
|-- all_jobs.json               # 920 career roles across 46 programs
|-- program_courses.json        # Official curriculum course codes
|-- program_requirements.json   # Full program requirements (481 programs)
|-- courses.json                # Legacy course set (148 courses)
|-- curated_jobs.json           # Seed career database (60 jobs)
|
|-- scraper.py                  # Undergrad course catalog scraper
|-- scrape_grad_courses.py      # Graduate course catalog scraper
|-- scrape_programs.py          # Program requirements scraper
|-- scrape_programs_v2.py       # Major Finder curriculum scraper
|
|-- build_careers.py            # Seed career database builder
|-- build_jobs.py               # Job generation orchestrator
|-- expand_jobs.py              # AI-powered job expansion
|-- add_salaries.py             # Salary + demand enrichment
|-- patch_salaries.py           # AI salary gap-filler
|-- fix_descriptions.py         # Course description repair
+-- .gitignore
```

---

## Setup & Run Locally

```bash
# Clone
git clone https://github.com/chandu1512/PathFinder.git
cd PathFinder

# Install dependencies
pip install -r requirements.txt

# Set your Groq API key
echo "GROQ_API_KEY=your-key-here" > .env

# Build FAISS indices (run once — or after updating course/career data)
python -m rag.build_index

# Run
python app.py
```

Open `http://localhost:5000` in your browser.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Powers AI chat, roadmaps, and all LLM features (free tier available) |
| `CHAT_MODEL` | No | Groq model for chat (default: `llama-3.3-70b-versatile`) |
| `ROADMAP_MODEL` | No | Groq model for roadmaps (default: `llama-3.3-70b-versatile`) |
| `FALLBACK_MODEL` | No | Fallback model on errors (default: `llama-3.1-8b-instant`) |
| `PORT` | No | Server port (default: 5000) |

---

## Evaluation

A hand-labeled test set of 50 student-style queries with expected courses lives in `evaluation/test_set.json`. To reproduce our retrieval numbers:

```bash
python evaluation/run_eval.py
```

The script embeds each query with `BAAI/bge-small-en-v1.5`, searches the FAISS course index, and computes:

- **retrieval@5** — percentage of queries where at least one expected course appears in the top 5 results
- **retrieval@10** — same metric at top 10
- A failure-case breakdown grouped by query type (precise, vague, multi-intent)

Reported result on our 50-query test set: **86% retrieval@5 (43 of 50)**, with most failures concentrated in very short (1–2 word) queries and queries that mention multiple intents at once.

---

## Deployment

Deployed on **Railway** using Gunicorn:

```
web: gunicorn app:app --worker-class gthread --workers 2 --threads 4 --timeout 120
```

The app loads all JSON data into memory at startup and pre-computes career path mappings, program info caches, and course indexes for fast API responses. The FAISS indices and BGE embedding model are loaded lazily on the first AI request.

---

## AI Tool Usage

In accordance with the CPEG 657 generative-AI policy, this project used Anthropic's Claude as a technical assistant during development (RAG pipeline debugging, FAISS index migration from ChromaDB, prompt engineering iterations, and Railway deployment troubleshooting). All architecture decisions, scraper logic, evaluation methodology, and final code were written and reviewed by the authors. See the accompanying `AI_Disclosure.docx` submitted with this project for full details.

---

## Built By

- **Chandra Chowdary Darapaneni** — M.S. Cybersecurity, University of Delaware
- **Lakshmi Nagendra Neelakantam** — M.S. Cybersecurity, University of Delaware
