"""
Scrapes official UDel program requirements from both undergrad (catoid=94)
and grad (catoid=93) catalogs. Saves to program_requirements.json.
"""
import requests
from bs4 import BeautifulSoup
import json, time, re
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE    = "https://catalog.udel.edu"
HEADERS = {"User-Agent": "Mozilla/5.0 (PathFinder/3.0)"}

COLLEGE_PAGES = {
    # Graduate colleges
    "grad": [
        "/content.php?catoid=93&navoid=30531",  # Agriculture
        "/content.php?catoid=93&navoid=30532",  # Arts & Sciences
        "/content.php?catoid=93&navoid=30533",  # Business
        "/content.php?catoid=93&navoid=30537",  # Earth/Ocean/Env
        "/content.php?catoid=93&navoid=30536",  # Education
        "/content.php?catoid=93&navoid=30534",  # Engineering
        "/content.php?catoid=93&navoid=30535",  # Health Sciences
        "/content.php?catoid=93&navoid=30558",  # Biden School
    ],
    # Undergrad colleges
    "undergrad": [
        "/content.php?catoid=94&navoid=34379",  # Agriculture
        "/content.php?catoid=94&navoid=34380",  # Arts & Sciences
        "/content.php?catoid=94&navoid=34381",  # Business
        "/content.php?catoid=94&navoid=34386",  # Earth/Ocean/Env
        "/content.php?catoid=94&navoid=34385",  # Education
        "/content.php?catoid=94&navoid=34382",  # Engineering
        "/content.php?catoid=94&navoid=34383",  # Health Sciences
        "/content.php?catoid=94&navoid=34387",  # Biden School
    ]
}

def get(url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(BASE + url if url.startswith('/') else url,
                           headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.text
        except:
            if i == retries - 1: return ""
            time.sleep(1 + i)

def get_program_links(college_url):
    html = get(college_url)
    if not html: return []
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=re.compile(r"preview_program\.php")):
        href = a.get("href", "")
        name = a.get_text(strip=True)
        if name and href:
            links.append({"name": name, "url": href if href.startswith("http") else BASE + "/" + href.lstrip("/")})
    return links

def scrape_program(prog):
    html = get(prog["url"])
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    block = soup.find("td", class_="block_content") or soup.find("div", class_="block_content_outer")
    if not block:
        return None

    text = block.get_text(" ", strip=True)
    text = re.sub(r'\s+', ' ', text).strip()

    # Extract course codes mentioned (e.g. CPEG 665, CISC 481)
    courses_mentioned = list(dict.fromkeys(re.findall(r'\b([A-Z]{2,5}\s+\d{3,4}[A-Z]?)\b', text)))

    # Extract credit info
    credits_match = re.search(r'(\d+)\s+credit\s+hours?', text, re.IGNORECASE)
    total_credits = int(credits_match.group(1)) if credits_match else None

    return {
        "name": prog["name"],
        "url": prog["url"],
        "total_credits": total_credits,
        "requirements_text": text[:4000],
        "courses_mentioned": courses_mentioned[:60]
    }

if __name__ == "__main__":
    all_programs = {}

    for level, pages in COLLEGE_PAGES.items():
        print(f"\n=== {level.upper()} ===")
        all_links = []
        for page in pages:
            links = get_program_links(page)
            all_links.extend(links)
            print(f"  {page[-20:]} → {len(links)} programs")
            time.sleep(0.3)

        # Deduplicate by URL
        seen = set()
        unique = []
        for l in all_links:
            if l["url"] not in seen:
                seen.add(l["url"])
                unique.append(l)

        print(f"  Scraping {len(unique)} unique programs...")
        results = []
        batch = 10
        for i in range(0, len(unique), batch):
            chunk = unique[i:i+batch]
            with ThreadPoolExecutor(max_workers=6) as ex:
                futs = {ex.submit(scrape_program, p): p for p in chunk}
                for f in as_completed(futs):
                    r = f.result()
                    if r:
                        results.append(r)
            print(f"  {min(i+batch, len(unique))}/{len(unique)}")
            time.sleep(0.5)

        all_programs[level] = results
        print(f"  ✓ {len(results)} programs scraped for {level}")

    with open("program_requirements.json", "w") as f:
        json.dump(all_programs, f, indent=2)

    total = sum(len(v) for v in all_programs.values())
    print(f"\nDone! {total} programs saved to program_requirements.json")
    for level, progs in all_programs.items():
        print(f"  {level}: {len(progs)}")
