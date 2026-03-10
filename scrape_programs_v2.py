"""
Scrapes real required courses for each program from UDel's Major Finder.
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
    "Data Science":                      "data-science",
    "Computer Engineering":              "computer-engineering",
    "Electrical Engineering":            "electrical-engineering",
    "Mechanical Engineering":            "mechanical-engineering",
    "Civil Engineering":                 "civil-engineering",
    "Chemical Engineering":              "chemical-engineering",
    "Biomedical Engineering":            "biomedical-engineering",
    "Management Information Systems":    "management-information-systems",
    "Finance":                           "finance",
    "Accounting":                        "accounting",
    "Business Administration & Management": "business-administration",
    "Marketing":                         "marketing",
    "Economics":                         "economics",
    "Health Sciences":                   "health-sciences",
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

CATALOG_FALLBACKS = {
    # catoid=94 is the undergrad catalog
    "Artificial Intelligence":           "https://catalog.udel.edu/preview_program.php?catoid=94&poid=90157",
    "Cybersecurity Engineering":         "https://catalog.udel.edu/preview_program.php?catoid=94&poid=90136",
    "Data Science":                      "https://catalog.udel.edu/preview_program.php?catoid=94&poid=90146",
    "Computer Engineering":              "https://catalog.udel.edu/preview_program.php?catoid=94&poid=90092",
    "Management Information Systems":    "https://catalog.udel.edu/preview_program.php?catoid=94&poid=90196",
    "Health Sciences":                   "https://catalog.udel.edu/preview_program.php?catoid=94&poid=90175",
    "Education":                         "https://catalog.udel.edu/preview_program.php?catoid=94&poid=90161",
    "Agricultural Sciences":             "https://catalog.udel.edu/preview_program.php?catoid=94&poid=90063",
    "Criminal Justice":                  "https://catalog.udel.edu/preview_program.php?catoid=94&poid=90142",
}

COURSE_CODE_RE = re.compile(r'\b([A-Z]{2,5})\s*(\d{3,4}[A-Z]?)\b')

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

def extract_codes_from_html(html):
    """Extract all DEPT NNN course codes from page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ")
    codes = []
    seen = set()
    for m in COURSE_CODE_RE.finditer(text):
        dept, num = m.group(1), m.group(2)
        # Filter out noise (years, ZIP codes, etc.)
        if dept in ("HTTP", "HTTPS", "HTML", "CSS", "GPA", "USA", "THE", "AND", "FOR", "ARE"):
            continue
        num_int = int(re.sub(r'[A-Z]', '', num))
        if num_int < 100 or num_int > 900:
            continue
        code = f"{dept} {num}"
        if code not in seen:
            seen.add(code)
            codes.append(code)
    return codes

def get_major_finder_page(slug):
    url = f"https://www.udel.edu/apply/undergraduate-admissions/major-finder/{slug}/"
    print(f"  Fetching: {url}")
    html = get(url)
    if not html:
        return []
    return extract_codes_from_html(html)

def get_catalog_page(url):
    print(f"  Fetching catalog: {url}")
    html = get(url)
    if not html:
        return []
    return extract_codes_from_html(html)

def build_program_courses():
    result = {}

    for prog_name, slug in PROGRAM_SLUGS.items():
        print(f"\n[{prog_name}]")
        codes = get_major_finder_page(slug)

        # If major finder fails or returns too few, try catalog fallback
        if len(codes) < 5 and prog_name in CATALOG_FALLBACKS:
            print(f"  → Trying catalog fallback...")
            codes = get_catalog_page(CATALOG_FALLBACKS[prog_name])

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
            "source": f"https://www.udel.edu/apply/undergraduate-admissions/major-finder/{slug}/"
        }
        print(f"  → {len(undergrad)} undergrad + {len(grad)} grad courses found")
        time.sleep(0.8)

    return result

if __name__ == "__main__":
    print("=== UDel Program Course Scraper v2 ===\n")
    data = build_program_courses()

    with open("program_courses.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n✓ Saved program_courses.json")
    print(f"  Programs: {len(data)}")
    for prog, d in data.items():
        print(f"  {prog}: {len(d['undergrad'])} UG + {len(d['grad'])} grad")
