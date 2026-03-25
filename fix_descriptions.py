"""
Re-fetch descriptions only for courses that have empty descriptions.
Uses smaller batches and better rate limiting to avoid being blocked.
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {"User-Agent": "Mozilla/5.0 (PathFinder/2.0 Academic Research Tool)"}

def fetch_desc(course):
    try:
        r = requests.get(course["url"], headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        block = soup.find("td", class_="block_content")
        if block:
            text = block.get_text(" ", strip=True)
            # Clean up nav/boilerplate at start
            code = course.get("code", "")
            if code:
                idx = text.find(code)
                if idx != -1:
                    text = text[idx:]
            text = re.sub(r'\s+', ' ', text).strip()
            course["description"] = text[:2000]
        else:
            course["description"] = ""
    except Exception as e:
        course["description"] = ""
    return course

if __name__ == "__main__":
    with open("all_courses.json") as f:
        courses = json.load(f)

    empty = [c for c in courses if not c.get("description", "").strip()]
    filled = [c for c in courses if c.get("description", "").strip()]
    print(f"Total: {len(courses)} | Has desc: {len(filled)} | Empty: {len(empty)}")
    print(f"Re-fetching {len(empty)} courses...\n")

    results = list(filled)  # start with already-good ones
    batch_size = 15         # smaller batch to avoid rate limiting
    workers = 8             # fewer workers

    for i in range(0, len(empty), batch_size):
        chunk = empty[i:i+batch_size]
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(fetch_desc, c) for c in chunk]
            for f in as_completed(futs):
                results.append(f.result())
        done = min(i + batch_size, len(empty))
        has_desc = sum(1 for c in results if c.get("description","").strip())
        print(f"  [{done}/{len(empty)}] Courses with descriptions so far: {has_desc}")
        time.sleep(0.8)  # be polite to the server

    # Save
    with open("all_courses.json", "w") as f:
        json.dump(results, f, indent=2)

    final_filled = sum(1 for c in results if c.get("description","").strip())
    print(f"\nDone! {final_filled}/{len(results)} courses now have descriptions.")
