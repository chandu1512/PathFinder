import json, anthropic, os

try:
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())
except FileNotFoundError:
    pass

client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))

with open('all_jobs.json') as f:
    jobs = json.load(f)

missing = []
for prog, job_list in jobs.items():
    for job in job_list:
        if not job.get('salary_min'):
            missing.append(job)

print(f'Jobs missing salary: {len(missing)}')

titles = [j['title'] for j in missing]
prompt = (
    "For each job title below, provide salary_min, salary_max (annual USD 2024-2025), "
    "and demand (High/Medium/Low) based on BLS, Glassdoor, LinkedIn data.\n\n"
    "Titles: " + json.dumps(titles) + "\n\n"
    'Respond ONLY with a JSON object: {"Job Title": [salary_min, salary_max, "demand"], ...}'
)

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8000,
    messages=[{"role": "user", "content": prompt}]
)
text = response.content[0].text.strip()
if text.startswith("```"):
    parts = text.split("```")
    text = parts[1]
    if text.startswith("json"):
        text = text[4:]
text = text.strip()

salary_map = json.loads(text)
patched = 0
for job in missing:
    if job['title'] in salary_map:
        lo, hi, demand = salary_map[job['title']]
        job['salary_min'] = lo
        job['salary_max'] = hi
        job['demand'] = demand
        patched += 1

with open('all_jobs.json', 'w') as f:
    json.dump(jobs, f, indent=2)

print(f'Patched {patched}/{len(missing)} jobs with salary data')
