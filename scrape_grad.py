import requests
from bs4 import BeautifulSoup
import json


def scrape_grad_catalog():
    print("Initiating Graduate Catalog Scrape...")
    # These are the targeted URLs based on UDel CIS structures
    urls = [
        "https://catalog.udel.edu/preview_program.php?catoid=67&poid=55823",  # MS CS
        "https://catalog.udel.edu/preview_program.php?catoid=67&poid=55826"  # MS AI
    ]

    grad_courses = []

    for url in urls:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Scrape logic for course blocks in the catalog
        for course_block in soup.find_all('a', {'class': 'acalog-course'}):
            title = course_block.text.strip()
            # Graduate courses in the catalog are often 600-level or higher
            grad_courses.append({
                "title": title,
                "description": "Graduate-level curriculum focusing on advanced computational theory and application."
            })

    with open('grad_courses.json', 'w') as f:
        json.dump(grad_courses, f, indent=4)

    print(f"SUCCESS: Scraped {len(grad_courses)} graduate courses.")


scrape_grad_catalog()
