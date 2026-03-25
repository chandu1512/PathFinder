"""
PathFinder Full Catalog Scraper
Scrapes ALL UDel undergraduate courses from every department.
Output: all_courses.json
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://catalog.udel.edu"
CATOID = 94
HEADERS = {"User-Agent": "Mozilla/5.0 (PathFinder/2.0)"}

def get(url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r.text
        except Exception as e:
            if i == retries - 1:
                print(f"  FAILED: {url} -> {e}")
                return ""
            time.sleep(1 + i)

# ── Step 1: Find total pages in the course search ──
def get_total_pages():
    url = f"{BASE}/search_advanced.php?catoid={CATOID}&search_database=Search&search_db=Search&cpage=1&ecpage=1&ppage=1&spage=1&tpage=1&location=33&filter%5Bkeyword%5D=&filter%5Bcpage%5D=1"
    html = get(url)
    if not html:
        return 1
    soup = BeautifulSoup(html, "html.parser")
    total = 1
    for a in soup.find_all("a", href=re.compile(r"cpage=\d+")):
        m = re.search(r"cpage=(\d+)", a["href"])
        if m:
            total = max(total, int(m.group(1)))
    return total

# ── Step 2: Get course list from one page ──
def fetch_course_page(page):
    url = (f"{BASE}/search_advanced.php?catoid={CATOID}"
           f"&search_database=Search&search_db=Search"
           f"&cpage={page}&ecpage=1&ppage=1&spage=1&tpage=1"
           f"&location=33&filter%5Bkeyword%5D=&filter%5Bcpage%5D={page}")
    html = get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    courses = []
    for a in soup.find_all("a", href=re.compile(r"preview_course_nopop\.php")):
        text = a.get_text(strip=True)
        href = a.get("href", "")
        m = re.search(r"coid=(\d+)", href)
        if not text or not m:
            continue
        # Parse "DEPT 101 - Course Title" format
        match = re.match(r"^([A-Z]+)\s+(\d+[A-Z]?)\s*[-–]\s*(.+)$", text)
        if match:
            dept = match.group(1)
            num  = match.group(2)
            title = match.group(3).strip()
        else:
            parts = text.split(" - ", 1)
            dept_num = parts[0].strip().split()
            dept  = dept_num[0] if dept_num else ""
            num   = dept_num[1] if len(dept_num) > 1 else ""
            title = parts[1].strip() if len(parts) > 1 else text
        courses.append({
            "code":  f"{dept} {num}".strip(),
            "dept":  dept,
            "number": num,
            "title": f"{dept} {num} - {title}".strip(" -"),
            "coid":  m.group(1),
            "url":   f"{BASE}/{href.lstrip('/')}"
        })
    return courses

# ── Step 3: Get description for one course ──
def fetch_description(course):
    html = get(course["url"])
    if not html:
        course["description"] = ""
        return course
    soup = BeautifulSoup(html, "html.parser")
    block = soup.find("td", class_="block_content")
    if block:
        raw = block.get_text(" ", strip=True)
        # Find where the course name starts
        idx = raw.find(course["code"])
        if idx != -1:
            raw = raw[idx:]
        raw = re.sub(r'\s+', ' ', raw).strip()
        course["description"] = raw[:2000]
    else:
        course["description"] = ""
    return course

# ── MAIN ──
if __name__ == "__main__":
    print("=== PathFinder Full Course Scraper ===\n")

    # 1. Total pages
    total_pages = get_total_pages()
    print(f"Total catalog pages: {total_pages}")

    # 2. Collect all course listings
    print("Fetching course list...")
    all_courses = []
    seen_coids = set()

    batch = 25
    for start in range(1, total_pages + 1, batch):
        end = min(start + batch, total_pages + 1)
        with ThreadPoolExecutor(max_workers=12) as ex:
            futs = [ex.submit(fetch_course_page, p) for p in range(start, end)]
            for f in as_completed(futs):
                for c in f.result():
                    if c["coid"] not in seen_coids:
                        seen_coids.add(c["coid"])
                        all_courses.append(c)
        print(f"  Pages {start}-{end-1} done | {len(all_courses)} courses collected")
        time.sleep(0.4)

    print(f"\nTotal unique courses found: {len(all_courses)}")

    # 3. Fetch descriptions
    print("\nFetching descriptions (this takes a few minutes)...")
    results = []
    batch = 30
    for i in range(0, len(all_courses), batch):
        chunk = all_courses[i:i+batch]
        with ThreadPoolExecutor(max_workers=15) as ex:
            futs = [ex.submit(fetch_description, c) for c in chunk]
            for f in as_completed(futs):
                results.append(f.result())
        done = min(i + batch, len(all_courses))
        print(f"  Descriptions: {done}/{len(all_courses)}")
        time.sleep(0.3)

    # 4. Save
    with open("all_courses.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n Done! Saved {len(results)} courses to all_courses.json")
