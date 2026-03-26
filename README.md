# PathFinder — UDel Career Mapper

**PathFinder** is an AI-powered career exploration platform built exclusively for University of Delaware students. It connects **8,354 UDel courses** across **46 academic programs** to **920+ real-world career paths**, helping students make data-driven decisions about their academic journey.

 **Live App:** Deployed on Railway
 **University:** University of Delaware
 **Data:** Scraped directly from the official UDel Course Catalog (2025–2026)

---

## What It Does

PathFinder answers the question every student asks: *"What can I actually do with my degree?"*

- **Explore 920+ career paths** across 46 programs — from Software Engineer to Forensic Accountant — each with salary ranges and demand levels
- **Browse 8,354 courses** (5,014 undergrad + 3,340 grad) with full descriptions, searchable by department, level, and keyword
- **AI-powered course matching** maps each career to the exact UDel courses that build job-relevant skills
- **Smart semester roadmaps** generate personalized 2-semester plans based on your major, career goal, and current year
- **PathFinder AI chatbot** answers any question about UDel programs, courses, elective strategy, and career planning — with real program data injected into every response
- **Cross-program exploration** shows students how to use their elective slots to pivot toward a different career field without switching majors

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              Frontend (index.html)           │
│  Vanilla JS · Fuse.js search · Dark mode    │
│  Font Awesome · Inter font · CSS Grid       │
└──────────────────┬──────────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────────┐
│            Backend (app.py - Flask)          │
│                                             │
│  /api/courses      → Browse & search        │
│  /api/career-paths → Job ↔ course mapping   │
│  /api/ai-match     → AI course suggestions  │
│  /api/roadmap      → Semester plan generator │
│  /api/chat         → AI chatbot             │
│  /api/search       → Smart career search    │
│  /api/program-info → Program requirements   │
│  /api/stats        → Dashboard counters     │
│                                             │
│  Claude Sonnet 4.6  → Chat & roadmaps       │
│  Claude Haiku 4.5   → Search & matching     │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│              Data Layer (JSON files)         │
│                                             │
│  all_courses.json         → 8,354 courses   │
│  all_jobs.json            → 920 career roles │
│  program_courses.json     → Curricula maps  │
│  program_requirements.json→ Degree reqs     │
│  curated_jobs.json        → Seed careers    │
└─────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla HTML/CSS/JS, Fuse.js (fuzzy search), Font Awesome, Google Fonts (Inter) |
| Backend | Python 3.11, Flask, Flask-CORS, Flask-Compress, Gunicorn |
| AI | Anthropic Claude API (Sonnet 4.6 for chat, Haiku 4.5 for search/matching) |
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

### 4. Career Database (`build_careers.py` → `expand_jobs.py` → `add_salaries.py`)

- **Seed:** `build_careers.py` creates 60 hand-curated career paths across 6 core programs
- **Expand:** `expand_jobs.py` uses Claude AI to generate up to 20 jobs per program, matching skills to real UDel course titles
- **Salaries:** `add_salaries.py` enriches every job with salary ranges and demand levels sourced from BLS, Glassdoor, and LinkedIn Salary data (2024–2025)
- **Patch:** `patch_salaries.py` catches any remaining jobs missing salary data and fills them via Claude

**Output:** `all_jobs.json` — 920 career roles across 46 programs, each with title, description, skills, salary_min/max, and demand

### 5. Description Repair (`fix_descriptions.py`)

Re-fetches descriptions for any courses with empty descriptions. Uses smaller batches (15) with polite delays to avoid rate limiting. Threaded execution (8 workers) for speed.

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

For deeper matching, the **AI Match endpoint** sends the full course pool from relevant departments to Claude Haiku, which selects the 8 best undergraduate and 8 best graduate courses with human-level judgment.

---

## Core vs. Elective Classification

The app parses program requirements text using **proximity-based NLP**:

1. Identifies all section headers in the requirements text (e.g., "Core Courses:", "Restricted Electives:", "Choose from:")
2. For each course code found in the text, scans backward to find the nearest section header
3. Classifies based on header keywords: `required`, `core`, `must complete` → Core; `elective`, `choose from`, `select` → Elective
4. Courses near no header default to Core (conservative approach)
5. Any courses in `courses_mentioned` but not classified as core are treated as electives

This powers the ★ Core and ○ Elective badges throughout the UI and the AI chatbot's elective strategy advice.

---

## Key Features

### AI Chatbot

The chatbot uses Claude Sonnet 4.6 with a detailed system prompt containing all program data. It detects the student's enrolled program from natural language ("I'm doing my masters in cybersecurity"), injects that program's core and elective course lists, and enforces a strict rule: **only recommend courses from the student's approved elective list** — never suggest courses they can't actually enroll in.

### Smart Search

Handles typos, natural language, and vague queries. "high paying jobs" → filters by salary + demand. "I like helping people" → surfaces healthcare, education, and social work roles. "data engneer" → correctly maps to Data Engineer. Powered by Claude Haiku for fast intent parsing.

### Semester Roadmaps

Generates a 2-semester plan (Fall + Spring) tailored to the student's current year, using only real course codes from their program. Auto-marks lower-level courses as completed based on year standing. Each course includes a one-sentence explanation of how it builds skills for the target career.

### Dark Mode

Full dark mode support with CSS custom properties. Toggles via nav button with state persistence.

---

## Project Structure

```
PathFinder/
├── app.py                      # Flask backend — all API endpoints
├── index.html                  # Single-page frontend
├── style.css                   # Stylesheet with dark mode
├── Procfile                    # Railway deployment config
├── requirements.txt            # Python dependencies
├── package.json                # Node dependencies
│
├── all_courses.json            # 8,354 UDel courses (undergrad + grad)
├── all_jobs.json               # 920 career roles across 46 programs
├── program_courses.json        # Official curriculum course codes
├── program_requirements.json   # Full program requirements (481 programs)
├── courses.json                # Legacy course set (148 courses)
├── curated_jobs.json           # Seed career database (60 jobs)
│
├── scraper.py                  # Undergrad course catalog scraper
├── scrape_grad_courses.py      # Graduate course catalog scraper
├── scrape_programs.py          # Program requirements scraper
├── scrape_programs_v2.py       # Major Finder curriculum scraper
│
├── build_careers.py            # Seed career database builder
├── build_jobs.py               # Job generation orchestrator
├── expand_jobs.py              # AI-powered job expansion
├── add_salaries.py             # Salary + demand enrichment
├── patch_salaries.py           # AI salary gap-filler
├── fix_descriptions.py         # Course description repair
├── build_db.py                 # ChromaDB vector database builder
└── .gitignore
```

---

## Setup & Run Locally

```bash
# Clone
git clone https://github.com/chandu1512/PathFinder.git
cd PathFinder

# Install dependencies
pip install -r requirements.txt

# Set your Anthropic API key
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# Run
python app.py
```

Open `http://localhost:5000` in your browser.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Powers AI chat, search, matching, and roadmaps |
| `PORT` | No | Server port (default: 5000) |

---

## Deployment

Deployed on **Railway** using Gunicorn:

```
web: gunicorn app:app --worker-class gthread --workers 2 --threads 4 --timeout 120
```

The app loads all JSON data into memory at startup and pre-computes career path mappings, program info caches, and course indexes for fast API responses.

---

## Built By

**Chandu Darapaneni** — Graduate student at the University of Delaware
