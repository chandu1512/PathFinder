"""
Expands all_jobs.json to ~20 jobs per program using Claude AI.
Preserves existing jobs and fills each program up to 20.
"""
import json
import os
import anthropic
import time

# Load .env
try:
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())
except FileNotFoundError:
    pass

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

# Load existing jobs
with open('all_jobs.json') as f:
    jobs = json.load(f)

# Load course titles for context (sample per dept)
with open('all_courses.json') as f:
    courses = json.load(f)

# Build a dept -> course titles index
dept_courses = {}
for c in courses:
    dept = c.get('dept', '')
    if dept not in dept_courses:
        dept_courses[dept] = []
    if len(dept_courses[dept]) < 40:
        dept_courses[dept].append(c.get('title', ''))

PROG_DEPTS = {
    "Computer Science":              ["CISC", "CPEG", "ELEG", "MATH"],
    "Artificial Intelligence":       ["CISC", "CPEG", "ELEG", "MATH", "COGN"],
    "Cybersecurity Engineering":     ["CPEG", "CISC", "ELEG", "MISY"],
    "Data Science":                  ["CISC", "MATH", "STAT", "ECON", "DSCC"],
    "Computer Engineering":          ["CPEG", "ELEG", "CISC"],
    "Electrical Engineering":        ["ELEG", "CPEG", "PHYS", "MATH"],
    "Mechanical Engineering":        ["MEEG", "PHYS", "MATH", "CIEG"],
    "Civil Engineering":             ["CIEG", "GEOL", "MEEG", "ENVE"],
    "Chemical Engineering":          ["CHEG", "CHEM", "BISC", "MATH"],
    "Biomedical Engineering":        ["BMES", "BISC", "CHEM", "ELEG", "MEEG"],
    "Management Information Systems":["MISY", "CISC", "ACCT", "BUAD"],
    "Finance":                       ["FINC", "ACCT", "ECON", "MATH", "BUAD"],
    "Accounting":                    ["ACCT", "FINC", "BUAD", "LEST"],
    "Business Administration & Management": ["BUAD", "MISY", "ACCT", "FINC", "MKTG"],
    "Marketing":                     ["MKTG", "BUAD", "COMM", "ECON"],
    "Economics":                     ["ECON", "FINC", "MATH", "STAT", "BUAD"],
    "Health Sciences":               ["NURS", "HLTH", "BISC", "CHEM", "HBNS"],
    "Biological Sciences":           ["BISC", "CHEM", "BIOL", "MMSC", "BIOC"],
    "Chemistry":                     ["CHEM", "BISC", "PHYS", "MATH"],
    "Education":                     ["EDUC", "HDFS", "PSYC", "COMM"],
    "Communication":                 ["COMM", "JOUR", "ENGL", "ARTC"],
    "Political Science & Public Policy": ["POSC", "PLSC", "ECON", "SOCI", "HIST"],
    "Psychology":                    ["PSYC", "CGSC", "HDFS", "SOCI"],
    "Environmental Science":         ["ENSC", "ENVE", "GEOL", "MAST", "BISC"],
    "Agricultural Sciences":         ["ANFS", "PLSC", "ENTM", "AGRI", "FOOD"],
    "Criminal Justice":              ["CRJU", "SOCI", "PSYC", "LEST"],
}

TARGET = 20

def get_course_sample(depts):
    titles = []
    for d in depts:
        titles.extend(dept_courses.get(d, [])[:15])
    return titles[:60]

def generate_jobs(program, existing_jobs, needed):
    existing_titles = [j['title'] for j in existing_jobs]
    depts = PROG_DEPTS.get(program, [])
    sample_courses = get_course_sample(depts)

    prompt = f"""You are building a career database for University of Delaware's PathFinder tool.

Program: {program}
Already have these jobs (DO NOT repeat): {json.dumps(existing_titles)}

Sample UDel course titles for this program:
{chr(10).join(sample_courses)}

Generate EXACTLY {needed} NEW job roles that a {program} graduate could realistically pursue.
Include both common AND niche/emerging roles. Be diverse — include industry, academia, government, nonprofit, startup roles.

For each job, the "skills" must be SHORT PHRASES (2-4 words) that appear verbatim or very close to actual course titles shown above. Pick 5 skills per job.

Respond with ONLY a valid JSON array, no markdown, no explanation:
[
  {{
    "title": "Job Title",
    "description": "One sentence describing what this professional does day-to-day.",
    "skills": ["phrase from course title", "phrase from course title", "phrase from course title", "phrase from course title", "phrase from course title"]
  }}
]"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    # Strip markdown code blocks if present
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
    text = text.strip()

    return json.loads(text)


total_added = 0
for program in jobs:
    existing = jobs[program]
    current_count = len(existing)
    needed = max(0, TARGET - current_count)

    if needed == 0:
        print(f"  {program}: already has {current_count} jobs, skipping")
        continue

    print(f"  {program}: has {current_count}, generating {needed} more...")
    try:
        new_jobs = generate_jobs(program, existing, needed)
        jobs[program].extend(new_jobs)
        total_added += len(new_jobs)
        print(f"    -> added {len(new_jobs)} jobs (total: {len(jobs[program])})")
        time.sleep(1)  # avoid rate limiting
    except Exception as e:
        print(f"    ERROR: {e}")
        time.sleep(3)

# Save
with open('all_jobs.json', 'w') as f:
    json.dump(jobs, f, indent=2)

total = sum(len(v) for v in jobs.values())
print(f"\nDone! Added {total_added} new jobs. Total: {total} across {len(jobs)} programs.")
