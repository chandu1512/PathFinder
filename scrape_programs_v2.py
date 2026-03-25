"""
Scrapes real required courses for each program from UDel's Major Finder.
Targets only the year-by-year course plan accordion (div.accordian.section),
avoiding sidebar, navigation, and footer noise.
Outputs: program_courses.json
"""
import requests
from bs4 import BeautifulSoup
import json
import re
import time

HEADERS = {"User-Agent": "Mozilla/5.0 (PathFinder/3.0)"}

# Map our internal program names → UDel major finder slugs
PROGRAM_SLUGS = {
    "Computer Science":                  "computer-science",
    "Artificial Intelligence":           "artificial-intelligence-engineering",
    "Cybersecurity Engineering":         "cybersecurity-engineering",
    "Data Science":                      "mathematics-and-data-science",
    "Computer Engineering":              "computer-engineering",
    "Electrical Engineering":            "electrical-engineering",
    "Mechanical Engineering":            "mechanical-engineering",
    "Civil Engineering":                 "civil-engineering",
    "Chemical Engineering":              "chemical-engineering",
    "Biomedical Engineering":            "biomedical-engineering",
    "Management Information Systems":    "management-information-systems",
    "Finance":                           "finance",
    "Accounting":                        "accounting",
    "Business Administration & Management": "management",
    "Marketing":                         "marketing",
    "Economics":                         "economics",
    "Health Sciences":                   "integrated-health-sciences",
    "Biological Sciences":               "biological-sciences",
    "Chemistry":                         "chemistry",
    "Education":                         "elementary-teacher-education",
    "Communication":                     "communication",
    "Political Science & Public Policy": "political-science",
    "Psychology":                        "psychology",
    "Environmental Science":             "environmental-science",
    "Agricultural Sciences":             "animal-science",
    "Criminal Justice":                  "criminal-justice",
}

# Noise dept codes that aren't real course prefixes
NOISE_DEPTS = {
    "HTTP", "HTTPS", "HTML", "CSS", "GPA", "USA", "THE", "AND", "FOR",
    "ARE", "NOT", "ALL", "ITS", "NEW", "BUT", "ONE", "HAS", "WITH",
    "UNIV",  # UNIV 101/401/402 are orientation, not major courses
    "GTM",   # Google Tag Manager
    "FFD",   # UI color codes
}

# Matches both "CISC108" and "CISC 108" and "MATH 210 - Title"
COURSE_CODE_RE = re.compile(r'\b([A-Z]{2,6})\s*(\d{3,4}[A-Z]?)\b')


def get(url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"  Attempt {i+1} failed: {e}")
            time.sleep(2)
    return ""


def normalize_code(dept, num):
    """Return 'DEPT NNN' with exactly one space."""
    return f"{dept} {num}"


def extract_codes_from_accordion(html):
    """
    Extract course codes ONLY from the year-by-year course plan accordion.
    Targets div.accordian.section (intentional UDel typo) to avoid
    picking up codes from navigation, sidebar filters, or footers.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Primary target: the course plan accordion section (UDel uses "accordian" not "accordion")
    accordion = soup.select_one("div.accordian.section")

    if not accordion:
        # Fallback: try the panel-group directly
        accordion = soup.select_one(".panel-group")

    if not accordion:
        # Last resort: full page (old behavior, less accurate)
        print("  WARNING: Could not find accordion — scanning full page")
        accordion = soup

    codes = []
    seen = set()

    # Get all text from panel bodies (one per year: Freshman/Sophomore/Junior/Senior)
    panel_bodies = accordion.select(".panel-body")
    if panel_bodies:
        target_text = " ".join(pb.get_text(" ", strip=True) for pb in panel_bodies)
    else:
        target_text = accordion.get_text(" ", strip=True)

    for m in COURSE_CODE_RE.finditer(target_text):
        dept, num = m.group(1), m.group(2)
        if dept in NOISE_DEPTS:
            continue
        num_int = int(re.sub(r'[A-Z]', '', num))
        if num_int < 100 or num_int > 900:
            continue
        code = normalize_code(dept, num)
        if code not in seen:
            seen.add(code)
            codes.append(code)

    return codes


def get_major_finder_page(slug):
    url = f"https://www.udel.edu/apply/undergraduate-admissions/major-finder/{slug}/"
    print(f"  Fetching: {url}")
    html = get(url)
    if not html:
        return [], url
    return extract_codes_from_accordion(html), url


def build_program_courses():
    result = {}

    for prog_name, slug in PROGRAM_SLUGS.items():
        print(f"\n[{prog_name}]")
        codes, source_url = get_major_finder_page(slug)

        if len(codes) < 3:
            print(f"  WARNING: Only {len(codes)} courses found — check page structure manually")

        # Separate into undergrad (100-499) and grad (500+)
        undergrad = []
        grad = []
        for code in codes:
            m = re.search(r'(\d{3,4})', code)
            if m:
                n = int(m.group(1))
                if n >= 500:
                    grad.append(code)
                else:
                    undergrad.append(code)

        result[prog_name] = {
            "undergrad": undergrad,
            "grad": grad,
            "source": source_url,
        }
        print(f"  → {len(undergrad)} undergrad + {len(grad)} grad courses found")
        time.sleep(0.8)

    return result


if __name__ == "__main__":
    print("=== UDel Program Course Scraper v3 ===\n")
    data = build_program_courses()

    with open("program_courses.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n✓ Saved program_courses.json")
    print(f"  Programs: {len(data)}")
    for prog, d in data.items():
        print(f"  {prog}: {len(d['undergrad'])} UG + {len(d['grad'])} grad")
