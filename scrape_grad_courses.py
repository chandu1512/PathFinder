"""
Scrapes ALL graduate courses from UDel's Graduate Catalog (catoid=96).
Appends them to all_courses.json, tagged with level="grad".
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE    = "https://catalog.udel.edu"
CATOID  = 93
HEADERS = {"User-Agent": "Mozilla/5.0 (PathFinder/2.0)"}

def get(url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r.text
        except Exception as e:
            if i == retries - 1:
                return ""
            time.sleep(1 + i)

def get_total_pages():
    url = (f"{BASE}/search_advanced.php?catoid={CATOID}"
           f"&search_database=Search&search_db=Search"
           f"&cpage=1&ecpage=1&ppage=1&spage=1&tpage=1"
           f"&location=33&filter%5Bkeyword%5D=&filter%5Bcpage%5D=1")
    html = get(url)
    if not html: return 1
    soup = BeautifulSoup(html, "html.parser")
    total = 1
    for a in soup.find_all("a", href=re.compile(r"cpage=\d+")):
        m = re.search(r"cpage=(\d+)", a["href"])
        if m: total = max(total, int(m.group(1)))
    return total

def fetch_page(page):
    url = (f"{BASE}/search_advanced.php?catoid={CATOID}"
           f"&search_database=Search&search_db=Search"
           f"&cpage={page}&ecpage=1&ppage=1&spage=1&tpage=1"
           f"&location=33&filter%5Bkeyword%5D=&filter%5Bcpage%5D={page}")
    html = get(url)
    if not html: return []
    soup = BeautifulSoup(html, "html.parser")
    courses = []
    for a in soup.find_all("a", href=re.compile(r"preview_course_nopop\.php")):
        text = a.get_text(strip=True)
        href = a.get("href", "")
        m = re.search(r"coid=(\d+)", href)
        if not text or not m: continue
        match = re.match(r"^([A-Z]+)\s+(\d+[A-Z]?)\s*[-–]\s*(.+)$", text)
        if match:
            dept, num, title = match.group(1), match.group(2), match.group(3).strip()
        else:
            parts = text.split(" - ", 1)
            dn = parts[0].strip().split()
            dept = dn[0] if dn else ""
            num  = dn[1] if len(dn) > 1 else ""
            title = parts[1].strip() if len(parts) > 1 else text
        courses.append({
            "code":   f"{dept} {num}".strip(),
            "dept":   dept,
            "number": num,
            "title":  f"{dept} {num} - {title}".strip(" -"),
            "coid":   m.group(1),
            "url":    f"{BASE}/{href.lstrip('/')}",
            "level":  "grad"
        })
    return courses

def fetch_desc(course):
    html = get(course["url"])
    if not html:
        course["description"] = ""
        return course
    soup = BeautifulSoup(html, "html.parser")
    block = soup.find("td", class_="block_content")
    if block:
        raw = block.get_text(" ", strip=True)
        idx = raw.find(course.get("code", ""))
        if idx != -1: raw = raw[idx:]
        course["description"] = re.sub(r'\s+', ' ', raw).strip()[:2000]
    else:
        course["description"] = ""
    return course

if __name__ == "__main__":
    print("=== Graduate Catalog Scraper ===")

    total_pages = get_total_pages()
    print(f"Total pages: {total_pages}")

    all_courses, seen = [], set()
    batch = 25
    for start in range(1, total_pages + 1, batch):
        end = min(start + batch, total_pages + 1)
        with ThreadPoolExecutor(max_workers=12) as ex:
            futs = [ex.submit(fetch_page, p) for p in range(start, end)]
            for f in as_completed(futs):
                for c in f.result():
                    if c["coid"] not in seen:
                        seen.add(c["coid"])
                        all_courses.append(c)
        print(f"  Pages {start}-{end-1} | {len(all_courses)} grad courses")
        time.sleep(0.4)

    print(f"\nFetching descriptions for {len(all_courses)} grad courses...")
    results = []
    batch = 15
    for i in range(0, len(all_courses), batch):
        chunk = all_courses[i:i+batch]
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(fetch_desc, c) for c in chunk]
            for f in as_completed(futs): results.append(f.result())
        print(f"  {min(i+batch, len(all_courses))}/{len(all_courses)}")
        time.sleep(0.8)

    # Load existing undergrad courses and append grad ones
    with open("all_courses.json") as f:
        existing = json.load(f)

    # Mark existing as undergrad if not already tagged
    for c in existing:
        if "level" not in c:
            c["level"] = "undergrad"

    # Deduplicate by coid
    existing_coids = {c["coid"] for c in existing}
    new_grad = [c for c in results if c["coid"] not in existing_coids]

    combined = existing + new_grad
    with open("all_courses.json", "w") as f:
        json.dump(combined, f, indent=2)

    print(f"\nDone!")
    print(f"  Undergrad courses: {len(existing)}")
    print(f"  New grad courses added: {len(new_grad)}")
    print(f"  Total: {len(combined)}")
