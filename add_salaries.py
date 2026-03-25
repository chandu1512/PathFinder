"""
Adds salary_min, salary_max, and demand to every job in all_jobs.json.
Salary data based on BLS, LinkedIn Salary, Glassdoor, and Levels.fyi (2024-2025).
Demand: "High" / "Medium" / "Low"
"""
import json

SALARY = {
    # ── COMPUTER SCIENCE ──
    "Software Engineer":              (110000, 175000, "High"),
    "Full Stack Developer":           (100000, 160000, "High"),
    "Backend Developer":              (105000, 165000, "High"),
    "Frontend Developer":             (90000,  145000, "High"),
    "Systems Programmer":             (105000, 160000, "Medium"),
    "Cloud Engineer":                 (120000, 185000, "High"),
    "DevOps Engineer":                (115000, 175000, "High"),
    "Database Engineer":              (100000, 155000, "Medium"),
    "Mobile App Developer":           (95000,  155000, "High"),
    "Game Developer":                 (80000,  140000, "Medium"),
    "Embedded Software Engineer":     (95000,  150000, "Medium"),
    "Compiler Engineer":              (120000, 185000, "Low"),
    "Computer Graphics Engineer":     (100000, 165000, "Medium"),
    "AI Software Engineer":           (130000, 200000, "High"),
    "Security Software Engineer":     (115000, 175000, "High"),
    "Site Reliability Engineer (SRE)":(120000, 185000, "High"),
    "Platform Engineer":              (115000, 175000, "High"),
    "Open Source Engineer":           (100000, 160000, "Medium"),

    # ── AI / ML ──
    "AI/ML Engineer":                 (135000, 210000, "High"),
    "Deep Learning Researcher":       (130000, 220000, "High"),
    "Natural Language Processing Engineer": (125000, 200000, "High"),
    "Computer Vision Engineer":       (120000, 195000, "High"),
    "AI Research Scientist":          (140000, 230000, "High"),
    "Robotics Engineer":              (100000, 165000, "Medium"),
    "MLOps Engineer":                 (120000, 185000, "High"),
    "Algorithm Engineer":             (120000, 190000, "Medium"),
    "Autonomous Systems Engineer":    (115000, 185000, "Medium"),
    "Generative AI Engineer":         (140000, 220000, "High"),
    "AI Product Manager":             (130000, 200000, "High"),
    "Prompt Engineer":                (100000, 165000, "Medium"),

    # ── CYBERSECURITY ──
    "Penetration Tester":             (95000,  160000, "High"),
    "SOC Analyst":                    (70000,  120000, "High"),
    "Application Security Engineer":  (110000, 170000, "High"),
    "Digital Forensics Investigator": (75000,  130000, "Medium"),
    "Cryptography Engineer":          (115000, 180000, "Medium"),
    "Cloud Security Architect":       (130000, 200000, "High"),
    "IAM Engineer":                   (100000, 160000, "High"),
    "Incident Responder":             (85000,  140000, "High"),
    "Network Security Engineer":      (100000, 160000, "High"),
    "Malware Analyst":                (85000,  145000, "Medium"),
    "IoT Security Engineer":          (100000, 160000, "Medium"),
    "Security Architect":             (130000, 200000, "High"),
    "Threat Intelligence Analyst":    (90000,  145000, "Medium"),

    # ── DATA SCIENCE ──
    "Data Scientist":                 (105000, 170000, "High"),
    "Data Engineer":                  (110000, 175000, "High"),
    "Machine Learning Engineer":      (120000, 190000, "High"),
    "Data Analyst":                   (70000,  115000, "High"),
    "Business Intelligence Developer":(85000,  135000, "High"),
    "Bioinformatics Scientist":       (80000,  130000, "Medium"),
    "Quantitative Analyst":           (120000, 200000, "Medium"),
    "Big Data Engineer":              (115000, 175000, "High"),
    "Statistician":                   (80000,  130000, "Medium"),
    "Research Data Scientist":        (95000,  155000, "Medium"),
    "Data Architect":                 (120000, 180000, "Medium"),

    # ── COMPUTER ENGINEERING ──
    "Hardware Engineer":              (95000,  155000, "Medium"),
    "FPGA/VLSI Engineer":             (100000, 165000, "Medium"),
    "Firmware Engineer":              (95000,  155000, "Medium"),
    "IoT Systems Engineer":           (90000,  150000, "Medium"),
    "Computer Architecture Engineer": (115000, 180000, "Medium"),
    "Network Systems Engineer":       (100000, 160000, "Medium"),

    # ── ELECTRICAL ENGINEERING ──
    "Electrical Design Engineer":     (85000,  140000, "Medium"),
    "Power Systems Engineer":         (90000,  145000, "Medium"),
    "Control Systems Engineer":       (90000,  145000, "Medium"),
    "Signal Processing Engineer":     (95000,  155000, "Medium"),
    "Telecommunications Engineer":    (85000,  140000, "Medium"),
    "Biomedical Electronics Engineer":(85000,  140000, "Medium"),

    # ── MECHANICAL ENGINEERING ──
    "Mechanical Design Engineer":     (80000,  130000, "Medium"),
    "Aerospace Engineer":             (90000,  150000, "Medium"),
    "Manufacturing Engineer":         (75000,  125000, "Medium"),
    "Robotics Mechanical Engineer":   (90000,  150000, "Medium"),
    "Thermal Systems Engineer":       (80000,  130000, "Medium"),
    "Product Development Engineer":   (80000,  135000, "Medium"),

    # ── CIVIL ENGINEERING ──
    "Structural Engineer":            (75000,  125000, "Medium"),
    "Transportation Engineer":        (72000,  120000, "Medium"),
    "Geotechnical Engineer":          (72000,  120000, "Medium"),
    "Water Resources Engineer":       (70000,  115000, "Medium"),
    "Construction Project Manager":   (80000,  135000, "Medium"),
    "Environmental Engineer":         (70000,  115000, "Medium"),

    # ── CHEMICAL ENGINEERING ──
    "Process Engineer":               (80000,  130000, "Medium"),
    "Pharmaceutical Process Engineer":(85000,  140000, "Medium"),
    "Materials Scientist":            (80000,  130000, "Medium"),
    "Environmental Process Engineer": (72000,  115000, "Medium"),
    "Biochemical Engineer":           (80000,  135000, "Medium"),

    # ── BIOMEDICAL ENGINEERING ──
    "Biomedical Device Engineer":     (80000,  135000, "Medium"),
    "Clinical Engineer":              (75000,  120000, "Medium"),
    "Tissue Engineering Scientist":   (75000,  125000, "Low"),
    "Imaging Systems Engineer":       (85000,  140000, "Medium"),

    # ── MIS ──
    "IT Project Manager":             (90000,  145000, "High"),
    "Systems Analyst":                (75000,  120000, "High"),
    "ERP Consultant":                 (85000,  140000, "Medium"),
    "IT Auditor":                     (80000,  130000, "High"),
    "Technology Product Manager":     (110000, 175000, "High"),
    "IT Consultant":                  (90000,  150000, "High"),
    "Network Administrator":          (65000,  110000, "Medium"),
    "CIO / IT Director":              (150000, 250000, "Medium"),

    # ── FINANCE ──
    "Investment Banking Analyst":     (100000, 180000, "Medium"),
    "Financial Analyst":              (75000,  125000, "High"),
    "Portfolio Manager":              (100000, 180000, "Medium"),
    "Risk Analyst":                   (80000,  130000, "High"),
    "FinTech Developer":              (110000, 170000, "High"),
    "Actuary":                        (90000,  155000, "Medium"),
    "Compliance Officer":             (75000,  125000, "High"),

    # ── ACCOUNTING ──
    "Certified Public Accountant (CPA)": (70000, 120000, "High"),
    "Forensic Accountant":            (75000,  130000, "Medium"),
    "Tax Specialist":                 (65000,  110000, "High"),
    "Internal Auditor":               (70000,  115000, "High"),
    "Management Accountant":          (70000,  115000, "High"),

    # ── BUSINESS ──
    "Management Consultant":          (90000,  160000, "High"),
    "Operations Manager":             (75000,  125000, "High"),
    "Supply Chain Manager":           (80000,  130000, "High"),
    "Human Resources Manager":        (65000,  110000, "Medium"),
    "Entrepreneur / Startup Founder": (0,      0,      "High"),

    # ── MARKETING ──
    "Digital Marketing Manager":      (65000,  110000, "High"),
    "Market Research Analyst":        (60000,  100000, "Medium"),
    "Brand Manager":                  (70000,  115000, "Medium"),
    "Growth Analyst":                 (70000,  115000, "High"),

    # ── ECONOMICS ──
    "Economist":                      (80000,  140000, "Medium"),
    "Economic Research Analyst":      (70000,  115000, "Medium"),
    "Financial Data Analyst":         (75000,  120000, "High"),
    "Quantitative Economist":         (90000,  155000, "Medium"),

    # ── HEALTH SCIENCES ──
    "Registered Nurse (RN)":          (65000,  100000, "High"),
    "Nurse Practitioner":             (100000, 140000, "High"),
    "Healthcare Administrator":       (75000,  130000, "High"),
    "Public Health Analyst":          (60000,  100000, "Medium"),
    "Health Informatics Specialist":  (75000,  120000, "High"),
    "Clinical Research Coordinator":  (55000,  90000,  "Medium"),
    "Pharmacist":                     (115000, 145000, "High"),

    # ── BIOLOGICAL SCIENCES ──
    "Research Scientist (Biology)":   (65000,  110000, "Medium"),
    "Geneticist":                     (70000,  120000, "Medium"),
    "Microbiologist":                 (65000,  105000, "Medium"),
    "Biotechnology Scientist":        (75000,  130000, "Medium"),
    "Ecologist":                      (55000,  90000,  "Medium"),

    # ── CHEMISTRY ──
    "Research Chemist":               (65000,  110000, "Medium"),
    "Analytical Chemist":             (65000,  110000, "Medium"),
    "Pharmaceutical Chemist":         (75000,  130000, "Medium"),
    "Quality Control Chemist":        (60000,  100000, "Medium"),

    # ── EDUCATION ──
    "K-12 Teacher":                   (45000,  75000,  "High"),
    "Instructional Designer":         (60000,  100000, "Medium"),
    "EdTech Developer":               (80000,  130000, "Medium"),
    "Special Education Teacher":      (45000,  75000,  "High"),

    # ── COMMUNICATION ──
    "Journalist / Reporter":          (40000,  80000,  "Medium"),
    "Technical Writer":               (65000,  110000, "High"),
    "Social Media Manager":           (50000,  90000,  "High"),
    "UX Writer":                      (75000,  125000, "Medium"),

    # ── POLITICAL SCIENCE ──
    "Policy Analyst":                 (60000,  100000, "Medium"),
    "Legislative Aide":               (40000,  75000,  "Medium"),
    "Nonprofit Program Manager":      (50000,  85000,  "Medium"),

    # ── PSYCHOLOGY ──
    "Human Factors / UX Researcher":  (80000,  130000, "High"),
    "Industrial-Organizational Psychologist": (80000, 130000, "Medium"),
    "Behavioral Data Analyst":        (75000,  120000, "Medium"),

    # ── ENVIRONMENTAL SCIENCE ──
    "Environmental Consultant":       (60000,  100000, "Medium"),
    "Climate / Data Scientist":       (80000,  130000, "Medium"),
    "Sustainability Manager":         (75000,  120000, "High"),

    # ── AGRICULTURE ──
    "Agricultural Engineer":          (65000,  105000, "Medium"),
    "Food Scientist":                 (65000,  105000, "Medium"),
    "Agricultural Data Analyst":      (65000,  105000, "Medium"),

    # ── CRIMINAL JUSTICE ──
    "Law Enforcement Officer":        (55000,  90000,  "High"),
    "Cybercrime Investigator":        (75000,  125000, "High"),
    "Paralegal":                      (50000,  85000,  "Medium"),
    "Criminologist":                  (55000,  90000,  "Medium"),
}

if __name__ == "__main__":
    with open("all_jobs.json") as f:
        jobs = json.load(f)

    patched = 0
    missing = []
    for program, job_list in jobs.items():
        for job in job_list:
            title = job["title"]
            if title in SALARY:
                lo, hi, demand = SALARY[title]
                job["salary_min"] = lo
                job["salary_max"] = hi
                job["demand"] = demand
                patched += 1
            else:
                missing.append(title)

    with open("all_jobs.json", "w") as f:
        json.dump(jobs, f, indent=2)

    print(f"Patched: {patched} jobs")
    if missing:
        print(f"Missing salary for: {missing}")
