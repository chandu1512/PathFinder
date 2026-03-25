"""
PathFinder Comprehensive Jobs Database - v2
Skills are precise phrases that appear in actual UDel course TITLES
so the matching engine finds real, relevant courses.
"""
import json

ALL_JOBS = {

    # ── COMPUTER SCIENCE ──────────────────────────────────────
    "Computer Science": [
        {"title": "Software Engineer",
         "description": "Design, build, and maintain scalable software systems.",
         "skills": ["software engineering", "algorithms", "data structures", "introduction to computer science", "object-oriented"]},

        {"title": "Full Stack Developer",
         "description": "Build both frontend user interfaces and backend server logic.",
         "skills": ["web applications security", "advanced web technologies", "database systems", "introduction to computer science", "software engineering"]},

        {"title": "Backend Developer",
         "description": "Design APIs, databases, and server-side application logic.",
         "skills": ["database systems", "computer networks", "software engineering", "operating systems", "introduction to algorithms"]},

        {"title": "Frontend Developer",
         "description": "Create responsive and accessible user interfaces.",
         "skills": ["introduction to computer science with web applications", "advanced web technologies", "human-computer interaction", "introduction to game development"]},

        {"title": "Systems Programmer",
         "description": "Write low-level code that interacts directly with hardware.",
         "skills": ["operating systems", "machine organization and assembly language", "introduction to systems programming", "computer architecture", "compiler design"]},

        {"title": "Cloud Engineer",
         "description": "Design and manage cloud infrastructure and services.",
         "skills": ["cloud computing and big data", "computer networks", "distributed computing", "parallel computing", "operating systems"]},

        {"title": "DevOps Engineer",
         "description": "Automate software deployment and infrastructure management.",
         "skills": ["devops", "software testing and maintenance", "computer networks", "operating systems", "introduction to algorithms"]},

        {"title": "Database Engineer",
         "description": "Design and optimize large-scale data storage systems.",
         "skills": ["database systems", "data mining", "introduction to algorithms", "data structures", "computational mathematics"]},

        {"title": "Mobile App Developer",
         "description": "Build applications for iOS and Android platforms.",
         "skills": ["introduction to computer science", "user interface", "human-computer interaction", "software engineering", "introduction to computer science ii"]},

        {"title": "Game Developer",
         "description": "Build interactive 2D and 3D gaming experiences.",
         "skills": ["introduction to game development", "educational game development", "computer graphics", "introduction to programming in games", "game development"]},

        {"title": "Embedded Software Engineer",
         "description": "Write firmware for specialized hardware devices.",
         "skills": ["embedded systems", "microprocessor systems", "introduction to computer systems engineering", "machine organization and assembly language", "computer systems design"]},

        {"title": "Compiler Engineer",
         "description": "Design and build programming language compilers.",
         "skills": ["compiler design", "automata theory", "logic for programming", "theory of computation", "programming languages"]},

        {"title": "Computer Graphics Engineer",
         "description": "Develop rendering engines, shaders, and visual effects.",
         "skills": ["computer graphics", "introduction to computer vision", "parallel computing", "introduction to game development"]},

        {"title": "AI Software Engineer",
         "description": "Build AI-powered features into software products.",
         "skills": ["artificial intelligence", "machine learning", "introduction to algorithms", "software engineering", "data mining"]},

        {"title": "Security Software Engineer",
         "description": "Build security-focused software systems and tools.",
         "skills": ["computer security principles and practice", "secure software design", "web applications security", "network security", "software engineering"]},
    ],

    # ── ARTIFICIAL INTELLIGENCE ───────────────────────────────
    "Artificial Intelligence": [
        {"title": "AI/ML Engineer",
         "description": "Build and deploy machine learning models at scale.",
         "skills": ["machine learning", "artificial intelligence", "introduction to algorithms", "computational mathematics", "data mining"]},

        {"title": "Deep Learning Researcher",
         "description": "Research and develop neural network architectures.",
         "skills": ["machine learning", "artificial intelligence", "computational mathematics", "introduction to algorithms", "computational biology"]},

        {"title": "Natural Language Processing Engineer",
         "description": "Build systems that understand and generate human language.",
         "skills": ["natural language processing", "artificial intelligence", "machine learning", "logic for programming", "introduction to algorithms"]},

        {"title": "Computer Vision Engineer",
         "description": "Develop AI systems that process images and video.",
         "skills": ["introduction to computer vision", "computer graphics", "machine learning", "artificial intelligence", "introduction to algorithms"]},

        {"title": "AI Research Scientist",
         "description": "Advance the state of AI through research.",
         "skills": ["introduction to multi-agent systems", "theory of computation", "artificial intelligence", "machine learning", "logic in computer science"]},

        {"title": "Robotics Engineer",
         "description": "Program autonomous robots using AI and control systems.",
         "skills": ["introduction to computer vision", "machine learning", "introduction to multi-agent systems", "embedded systems", "artificial intelligence"]},

        {"title": "MLOps Engineer",
         "description": "Manage machine learning pipelines and model deployments.",
         "skills": ["machine learning", "devops", "cloud computing and big data", "software engineering", "operating systems"]},

        {"title": "Algorithm Engineer",
         "description": "Design highly efficient algorithms for AI applications.",
         "skills": ["introduction to algorithms", "computational mathematics", "automata theory", "theory of computation", "discrete mathematics"]},

        {"title": "Autonomous Systems Engineer",
         "description": "Build self-driving and autonomous vehicle software.",
         "skills": ["introduction to multi-agent systems", "introduction to computer vision", "parallel computing", "machine learning", "artificial intelligence"]},

        {"title": "Generative AI Engineer",
         "description": "Build applications using large language models.",
         "skills": ["artificial intelligence", "natural language processing", "machine learning", "introduction to algorithms", "software engineering"]},
    ],

    # ── CYBERSECURITY ENGINEERING ─────────────────────────────
    "Cybersecurity Engineering": [
        {"title": "Penetration Tester",
         "description": "Simulate cyberattacks to discover vulnerabilities before attackers.",
         "skills": ["pen test and reverse engineering", "introduction to cybersecurity", "web applications security", "advanced cybersecurity", "network security"]},

        {"title": "SOC Analyst",
         "description": "Monitor and respond to security incidents in real time.",
         "skills": ["introduction to cybersecurity", "introduction to network security", "topics in cybersecurity", "computer networks", "advanced cybersecurity"]},

        {"title": "Application Security Engineer",
         "description": "Integrate security throughout the software development lifecycle.",
         "skills": ["web applications security", "secure software design", "introduction to cybersecurity", "computer security principles and practice", "software testing"]},

        {"title": "Digital Forensics Investigator",
         "description": "Recover and analyze digital evidence from devices for cybercrime cases.",
         "skills": ["digital forensics", "operating systems", "introduction to cybersecurity", "pen test and reverse engineering", "computer networks"]},

        {"title": "Cryptography Engineer",
         "description": "Develop encryption algorithms and security protocols.",
         "skills": ["applied cryptography", "introduction to cybersecurity", "computational mathematics", "discrete mathematics", "advanced cybersecurity"]},

        {"title": "Cloud Security Architect",
         "description": "Design and enforce security in cloud environments.",
         "skills": ["cloud computing and security", "introduction to cybersecurity", "computer networks", "advanced cybersecurity", "network security"]},

        {"title": "IAM Engineer",
         "description": "Build identity and access management systems.",
         "skills": ["introduction to cybersecurity", "system hardening and protection", "computer networks", "operating systems", "cybersecurity management"]},

        {"title": "Incident Responder",
         "description": "Lead rapid response to contain and recover from cyber breaches.",
         "skills": ["system hardening and protection", "digital forensics", "topics in cybersecurity", "advanced cybersecurity", "introduction to cybersecurity"]},

        {"title": "Network Security Engineer",
         "description": "Design secure network architecture and firewalls.",
         "skills": ["introduction to network security", "computer networks", "introduction to cybersecurity engineering", "pen test and reverse engineering", "introduction to cybersecurity"]},

        {"title": "Malware Analyst",
         "description": "Reverse engineer malicious software to understand threats.",
         "skills": ["pen test and reverse engineering", "digital forensics", "introduction to cybersecurity", "operating systems", "machine organization and assembly language"]},

        {"title": "IoT Security Engineer",
         "description": "Secure connected devices and embedded systems.",
         "skills": ["iot and embedded systems security", "embedded systems", "introduction to cybersecurity", "computer networks", "microprocessor systems"]},

        {"title": "Security Architect",
         "description": "Design enterprise-wide security frameworks.",
         "skills": ["advanced cybersecurity", "introduction to cybersecurity engineering", "cloud computing and security", "system hardening and protection", "network security"]},
    ],

    # ── DATA SCIENCE ──────────────────────────────────────────
    "Data Science": [
        {"title": "Data Scientist",
         "description": "Extract insights from complex datasets using statistics and ML.",
         "skills": ["introduction to data mining", "machine learning", "introduction to statistical methods", "computational biology and bioinformatics", "introduction to algorithms"]},

        {"title": "Data Engineer",
         "description": "Build data pipelines and infrastructure for analytics teams.",
         "skills": ["database systems", "cloud computing and big data", "introduction to algorithms", "computer networks", "data mining"]},

        {"title": "Machine Learning Engineer",
         "description": "Build and optimize ML models for production systems.",
         "skills": ["machine learning", "introduction to algorithms", "data mining", "computational mathematics", "software engineering"]},

        {"title": "Data Analyst",
         "description": "Translate raw data into actionable business insights.",
         "skills": ["introduction to data mining", "introduction to statistical methods", "database systems", "computational mathematics", "business computing fundamentals"]},

        {"title": "Business Intelligence Developer",
         "description": "Design dashboards and reporting infrastructure.",
         "skills": ["database systems", "database management", "introduction to data mining", "introduction to statistical methods", "business computing fundamentals"]},

        {"title": "Bioinformatics Scientist",
         "description": "Apply computational methods to solve biology problems.",
         "skills": ["computational biology and bioinformatics", "introduction to data mining", "machine learning", "introduction to statistical methods", "algorithms"]},

        {"title": "Quantitative Analyst",
         "description": "Use math and data to build financial models.",
         "skills": ["computational mathematics", "introduction to statistical methods", "regression and experimental design", "probability theory", "mathematical statistics"]},

        {"title": "Big Data Engineer",
         "description": "Process and manage large-scale unstructured datasets.",
         "skills": ["cloud computing and big data", "search and data mining", "parallel computing", "database systems", "computer networks"]},

        {"title": "Statistician",
         "description": "Apply statistical theory to study design and data analysis.",
         "skills": ["introduction to statistical methods", "regression and experimental design", "mathematical statistics", "probability theory", "computational mathematics"]},

        {"title": "Research Data Scientist",
         "description": "Support scientific research with advanced data analysis.",
         "skills": ["introduction to statistical methods", "machine learning", "introduction to data mining", "computational biology and bioinformatics", "regression and experimental design"]},
    ],

    # ── COMPUTER ENGINEERING ──────────────────────────────────
    "Computer Engineering": [
        {"title": "Hardware Engineer",
         "description": "Design computer chips, circuits, and electronic systems.",
         "skills": ["introduction to digital systems", "computer systems design", "introduction to vlsi systems", "introduction to computer systems engineering", "pcb"]},

        {"title": "FPGA/VLSI Engineer",
         "description": "Program reconfigurable hardware and design integrated circuits.",
         "skills": ["introduction to vlsi systems", "introduction to digital systems", "pcb", "computer systems design", "embedded systems"]},

        {"title": "Firmware Engineer",
         "description": "Develop low-level software for hardware devices.",
         "skills": ["embedded systems hardware", "microprocessor systems", "machine organization and assembly language", "computer systems design", "introduction to computer systems engineering"]},

        {"title": "IoT Systems Engineer",
         "description": "Build connected device ecosystems and smart systems.",
         "skills": ["iot and embedded systems security", "embedded systems", "computer networks", "microprocessor systems", "introduction to computer systems engineering"]},

        {"title": "Computer Architecture Engineer",
         "description": "Design processor and memory system architectures.",
         "skills": ["computer architecture", "computer systems design", "high-performance computing", "parallel computing", "microprocessor systems"]},

        {"title": "Network Systems Engineer",
         "description": "Design and implement high-performance network systems.",
         "skills": ["computer networks", "introduction to computer systems engineering", "computer architecture", "cloud computing and big data", "high-performance computing"]},
    ],

    # ── ELECTRICAL ENGINEERING ────────────────────────────────
    "Electrical Engineering": [
        {"title": "Electrical Design Engineer",
         "description": "Design electrical systems and components.",
         "skills": ["introduction to digital systems", "computer systems design", "analog integrated circuit design", "introduction to vlsi systems", "pcb"]},

        {"title": "Power Systems Engineer",
         "description": "Design and analyze electrical power systems.",
         "skills": ["field theory", "communication systems engineering", "digital control systems", "opto-electronics", "antenna theory"]},

        {"title": "Control Systems Engineer",
         "description": "Design feedback and automation control systems.",
         "skills": ["digital control systems", "communication systems engineering", "dynamics", "advanced biomedical and pharmaceutical modeling", "field theory"]},

        {"title": "Signal Processing Engineer",
         "description": "Process and analyze digital and analog signals.",
         "skills": ["communication systems engineering", "digital control systems", "quantum mechanics", "opto-electronics", "field theory"]},

        {"title": "Telecommunications Engineer",
         "description": "Design and maintain wireless and wired communication networks.",
         "skills": ["communication systems engineering", "computer networks", "antenna theory", "business telecommunication networks", "digital control systems"]},

        {"title": "Biomedical Electronics Engineer",
         "description": "Design electronic systems for medical applications.",
         "skills": ["advanced biomedical and pharmaceutical modeling", "digital forensics", "introduction to digital systems", "opto-electronics", "computer systems design"]},
    ],

    # ── MECHANICAL ENGINEERING ────────────────────────────────
    "Mechanical Engineering": [
        {"title": "Mechanical Design Engineer",
         "description": "Design mechanical components, assemblies, and products.",
         "skills": ["machine design", "statics", "solid mechanics", "introduction to mechanical engineering design", "dynamics"]},

        {"title": "Aerospace Engineer",
         "description": "Design aircraft, spacecraft, and propulsion systems.",
         "skills": ["dynamics", "statics", "solid mechanics", "control systems", "thermodynamics"]},

        {"title": "Manufacturing Engineer",
         "description": "Optimize manufacturing processes for efficiency and quality.",
         "skills": ["machine design", "statics", "solid mechanics", "introduction to mechanical engineering design", "dynamics"]},

        {"title": "Robotics Mechanical Engineer",
         "description": "Design physical structures and actuators for robots.",
         "skills": ["control systems", "dynamics", "statics", "machine design", "solid mechanics"]},

        {"title": "Thermal Systems Engineer",
         "description": "Design heat transfer and energy conversion systems.",
         "skills": ["dynamics", "solid mechanics", "statics", "control systems", "machine design"]},

        {"title": "Product Development Engineer",
         "description": "Lead end-to-end physical product development from concept to launch.",
         "skills": ["introduction to mechanical engineering design", "machine design", "statics", "solid mechanics", "dynamics"]},
    ],

    # ── CIVIL ENGINEERING ─────────────────────────────────────
    "Civil Engineering": [
        {"title": "Structural Engineer",
         "description": "Design safe and efficient buildings, bridges, and infrastructure.",
         "skills": ["structural design", "solid mechanics", "statics", "civil engineering materials", "introduction to civil engineering design"]},

        {"title": "Transportation Engineer",
         "description": "Plan and design roads, highways, and transit systems.",
         "skills": ["introduction to civil engineering design", "statics", "environmental engineering processes", "civil engineering materials", "solid mechanics"]},

        {"title": "Geotechnical Engineer",
         "description": "Analyze soil and rock properties for construction safety.",
         "skills": ["civil engineering materials", "solid mechanics", "statics", "environmental engineering processes", "introduction to civil engineering design"]},

        {"title": "Water Resources Engineer",
         "description": "Design systems for water supply, drainage, and flood control.",
         "skills": ["environmental engineering processes", "introduction to civil engineering design", "statics", "civil engineering materials", "solid mechanics"]},

        {"title": "Construction Project Manager",
         "description": "Manage construction projects from design to completion.",
         "skills": ["introduction to civil engineering design", "structural design", "civil engineering materials", "solid mechanics", "statics"]},

        {"title": "Environmental Engineer",
         "description": "Design solutions for water, air, and land contamination.",
         "skills": ["environmental engineering processes", "introduction to civil engineering design", "civil engineering materials", "statics", "solid mechanics"]},
    ],

    # ── CHEMICAL ENGINEERING ──────────────────────────────────
    "Chemical Engineering": [
        {"title": "Process Engineer",
         "description": "Design and optimize chemical manufacturing processes.",
         "skills": ["organic chemistry", "introduction to biochemistry", "thermodynamics", "instrumental methods", "analytical chemistry"]},

        {"title": "Pharmaceutical Process Engineer",
         "description": "Scale up drug manufacturing processes.",
         "skills": ["introduction to biochemistry", "organic chemistry", "pharmacology", "instrumental methods", "principles of biology"]},

        {"title": "Materials Scientist",
         "description": "Develop new materials with targeted chemical properties.",
         "skills": ["organic chemistry", "instrumental methods", "introduction to biochemistry", "thermodynamics", "analytical chemistry"]},

        {"title": "Environmental Process Engineer",
         "description": "Design clean processes that minimize industrial waste.",
         "skills": ["environmental engineering processes", "organic chemistry", "thermodynamics", "principles of biology", "analytical chemistry"]},

        {"title": "Biochemical Engineer",
         "description": "Design processes using biological organisms and enzymes.",
         "skills": ["introduction to biochemistry", "organic chemistry", "principles of biology", "computational biology", "instrumental methods"]},
    ],

    # ── BIOMEDICAL ENGINEERING ────────────────────────────────
    "Biomedical Engineering": [
        {"title": "Biomedical Device Engineer",
         "description": "Design medical devices such as pacemakers and diagnostic tools.",
         "skills": ["advanced biomedical and pharmaceutical modeling", "introduction to digital systems", "principles of biology", "organic chemistry", "introduction to computer vision"]},

        {"title": "Clinical Engineer",
         "description": "Manage and maintain medical equipment in hospital settings.",
         "skills": ["advanced biomedical and pharmaceutical modeling", "principles of biology", "pharmacology", "introduction to digital systems", "pathophysiology"]},

        {"title": "Tissue Engineering Scientist",
         "description": "Develop biological scaffolds for regenerative medicine.",
         "skills": ["computational biology and bioinformatics", "introduction to biochemistry", "principles of biology", "organic chemistry", "microbiology"]},

        {"title": "Imaging Systems Engineer",
         "description": "Develop MRI, CT, and ultrasound imaging technology.",
         "skills": ["introduction to computer vision", "advanced biomedical and pharmaceutical modeling", "introduction to digital systems", "digital control systems", "opto-electronics"]},
    ],

    # ── MANAGEMENT INFORMATION SYSTEMS ───────────────────────
    "Management Information Systems": [
        {"title": "IT Project Manager",
         "description": "Lead technology projects using agile and project management methods.",
         "skills": ["it project management", "information technology and organizational effectiveness", "analyzing and designing it solutions", "mis capstone", "database management"]},

        {"title": "Systems Analyst",
         "description": "Analyze and design IT solutions for business problems.",
         "skills": ["analyzing and designing it solutions", "introduction to management information systems", "database management", "business computing fundamentals", "mis capstone"]},

        {"title": "ERP Consultant",
         "description": "Implement and configure enterprise resource planning systems.",
         "skills": ["analyzing and designing it solutions", "database management", "introduction to management information systems", "information technology", "business computing fundamentals"]},

        {"title": "IT Auditor",
         "description": "Evaluate IT controls and compliance posture.",
         "skills": ["cybersecurity management", "introduction to management information systems", "analyzing and designing it solutions", "information security", "database management"]},

        {"title": "Technology Product Manager",
         "description": "Define product vision and roadmap for technology products.",
         "skills": ["information technology and organizational effectiveness", "analyzing and designing it solutions", "introduction to management information systems", "mis capstone", "database management"]},

        {"title": "IT Consultant",
         "description": "Advise organizations on digital transformation strategy.",
         "skills": ["analyzing and designing it solutions", "information technology and organizational effectiveness", "introduction to management information systems", "cybersecurity management", "database management"]},

        {"title": "Network Administrator",
         "description": "Manage and maintain organizational network infrastructure.",
         "skills": ["business telecommunication networks", "introduction to management information systems", "database management", "introduction to cybersecurity", "information technology"]},

        {"title": "CIO / IT Director",
         "description": "Executive leadership of an organization's technology strategy.",
         "skills": ["information technology and organizational effectiveness", "analyzing and designing it solutions", "cybersecurity management", "mis capstone", "introduction to management information systems"]},
    ],

    # ── FINANCE ───────────────────────────────────────────────
    "Finance": [
        {"title": "Investment Banking Analyst",
         "description": "Advise companies on mergers, acquisitions, and capital raising.",
         "skills": ["principles of finance", "advanced corporate finance", "fixed income securities", "fundamentals of finance", "corporate governance"]},

        {"title": "Financial Analyst",
         "description": "Analyze financial data to support investment decisions.",
         "skills": ["principles of finance", "fundamentals of finance", "advanced corporate finance", "fixed income securities", "accounting"]},

        {"title": "Portfolio Manager",
         "description": "Manage investment portfolios for individuals and institutions.",
         "skills": ["fixed income securities", "principles of finance", "advanced corporate finance", "fundamentals of finance", "financial modeling"]},

        {"title": "Risk Analyst",
         "description": "Identify and quantify financial and operational risks.",
         "skills": ["principles of finance", "fundamentals of finance", "advanced corporate finance", "accounting", "regression and experimental design"]},

        {"title": "FinTech Developer",
         "description": "Build software for banking and financial services.",
         "skills": ["principles of finance", "fundamentals of finance", "database systems", "software engineering", "algorithms"]},

        {"title": "Actuary",
         "description": "Use mathematics and statistics to assess financial risk.",
         "skills": ["probability theory", "mathematical statistics", "regression and experimental design", "principles of finance", "computational mathematics"]},

        {"title": "Compliance Officer",
         "description": "Ensure financial institutions meet all regulatory requirements.",
         "skills": ["law and social issues in business", "principles of finance", "fundamentals of finance", "accounting", "corporate governance"]},
    ],

    # ── ACCOUNTING ────────────────────────────────────────────
    "Accounting": [
        {"title": "Certified Public Accountant (CPA)",
         "description": "Provide tax, audit, and financial advisory services.",
         "skills": ["accounting", "auditing", "cost accounting", "accounting information systems", "law and social issues in business"]},

        {"title": "Forensic Accountant",
         "description": "Investigate financial fraud and white-collar crime.",
         "skills": ["auditing", "internal auditing", "accounting", "law and social issues in business", "cost accounting"]},

        {"title": "Tax Specialist",
         "description": "Prepare and optimize individual and corporate tax strategies.",
         "skills": ["accounting", "auditing", "law and social issues in business", "cost accounting", "accounting information systems"]},

        {"title": "Internal Auditor",
         "description": "Evaluate internal controls and financial processes.",
         "skills": ["internal auditing", "auditing", "accounting", "cost accounting", "accounting information systems"]},

        {"title": "Management Accountant",
         "description": "Provide financial insights to guide business strategy.",
         "skills": ["cost accounting", "accounting", "principles of finance", "accounting information systems", "survey of accounting"]},
    ],

    # ── BUSINESS ADMINISTRATION ───────────────────────────────
    "Business Administration & Management": [
        {"title": "Management Consultant",
         "description": "Help organizations improve performance and strategy.",
         "skills": ["analyzing and designing it solutions", "information technology and organizational effectiveness", "accounting", "principles of finance", "introduction to management information systems"]},

        {"title": "Operations Manager",
         "description": "Oversee day-to-day business operations.",
         "skills": ["information technology and organizational effectiveness", "accounting", "principles of finance", "database management", "business computing fundamentals"]},

        {"title": "Supply Chain Manager",
         "description": "Optimize the flow of goods from suppliers to customers.",
         "skills": ["analyzing and designing it solutions", "database management", "information technology and organizational effectiveness", "accounting", "business computing fundamentals"]},

        {"title": "Human Resources Manager",
         "description": "Recruit, develop, and retain organizational talent.",
         "skills": ["information technology and organizational effectiveness", "accounting", "introduction to management information systems", "business computing fundamentals", "organizational effectiveness"]},

        {"title": "Entrepreneur / Startup Founder",
         "description": "Build and scale a new business venture.",
         "skills": ["principles of finance", "fundamentals of finance", "accounting", "information technology and organizational effectiveness", "introduction to management information systems"]},
    ],

    # ── MARKETING ─────────────────────────────────────────────
    "Marketing": [
        {"title": "Digital Marketing Manager",
         "description": "Manage online marketing campaigns across SEO, SEM, and social.",
         "skills": ["introduction to computer science with web applications", "advanced web technologies", "introduction to data mining", "introduction to statistical methods", "business computing fundamentals"]},

        {"title": "Market Research Analyst",
         "description": "Gather and analyze data on consumer preferences and markets.",
         "skills": ["introduction to statistical methods", "introduction to data mining", "regression and experimental design", "business computing fundamentals", "introduction to algorithms"]},

        {"title": "Brand Manager",
         "description": "Develop and protect a company's brand identity.",
         "skills": ["information technology and organizational effectiveness", "introduction to management information systems", "business computing fundamentals", "introduction to statistical methods", "accounting"]},

        {"title": "Growth Analyst",
         "description": "Use data-driven tactics to grow user acquisition.",
         "skills": ["introduction to data mining", "introduction to statistical methods", "database systems", "machine learning", "business computing fundamentals"]},
    ],

    # ── ECONOMICS ────────────────────────────────────────────
    "Economics": [
        {"title": "Economist",
         "description": "Analyze markets, policy impacts, and economic trends.",
         "skills": ["introduction to statistical methods", "regression and experimental design", "probability theory", "computational mathematics", "mathematical statistics"]},

        {"title": "Economic Research Analyst",
         "description": "Conduct economic research for governments or think tanks.",
         "skills": ["introduction to statistical methods", "regression and experimental design", "mathematical statistics", "computational mathematics", "introduction to algorithms"]},

        {"title": "Financial Data Analyst",
         "description": "Analyze economic and financial datasets.",
         "skills": ["introduction to statistical methods", "regression and experimental design", "introduction to data mining", "database systems", "principles of finance"]},

        {"title": "Quantitative Economist",
         "description": "Apply quantitative methods to economic modeling.",
         "skills": ["mathematical statistics", "probability theory", "regression and experimental design", "computational mathematics", "introduction to statistical methods"]},
    ],

    # ── HEALTH SCIENCES ───────────────────────────────────────
    "Health Sciences": [
        {"title": "Registered Nurse (RN)",
         "description": "Provide direct patient care in hospital and clinical settings.",
         "skills": ["pharmacology across the lifespan", "pathophysiology", "clinical decision making", "human anatomy", "women's health"]},

        {"title": "Nurse Practitioner",
         "description": "Provide advanced clinical care including diagnoses.",
         "skills": ["pharmacology across the lifespan", "pathophysiology", "clinical decision making", "healthcare research", "human anatomy"]},

        {"title": "Healthcare Administrator",
         "description": "Manage hospital departments and healthcare operations.",
         "skills": ["clinical decision making", "healthcare research", "information technology and organizational effectiveness", "accounting", "management"]},

        {"title": "Public Health Analyst",
         "description": "Analyze population health data to guide public policy.",
         "skills": ["introduction to statistical methods", "healthcare research", "regression and experimental design", "pathophysiology", "epidemiology"]},

        {"title": "Health Informatics Specialist",
         "description": "Bridge healthcare and IT to manage medical data systems.",
         "skills": ["database management", "introduction to management information systems", "healthcare research", "clinical decision making", "analyzing and designing it solutions"]},

        {"title": "Clinical Research Coordinator",
         "description": "Manage clinical trials and research protocols.",
         "skills": ["healthcare research", "pathophysiology", "pharmacology across the lifespan", "clinical decision making", "principles of biology"]},

        {"title": "Pharmacist",
         "description": "Dispense medications and advise patients on drug therapy.",
         "skills": ["pharmacology across the lifespan", "pathophysiology", "introduction to biochemistry", "organic chemistry", "principles of biology"]},
    ],

    # ── BIOLOGICAL SCIENCES ───────────────────────────────────
    "Biological Sciences": [
        {"title": "Research Scientist (Biology)",
         "description": "Conduct laboratory research in biology and life sciences.",
         "skills": ["principles of biology", "microbiology", "genetics", "computational biology", "human heredity and development"]},

        {"title": "Geneticist",
         "description": "Study genes and heredity in organisms.",
         "skills": ["human heredity and development", "principles of biology", "computational biology and bioinformatics", "microbiology", "introduction to biochemistry"]},

        {"title": "Microbiologist",
         "description": "Study microorganisms including bacteria and viruses.",
         "skills": ["microbiology", "viruses, genes and cancer", "principles of biology", "introduction to biochemistry", "human heredity and development"]},

        {"title": "Biotechnology Scientist",
         "description": "Develop biological products and processes for industry.",
         "skills": ["computational biology and bioinformatics", "introduction to biochemistry", "principles of biology", "microbiology", "organic chemistry"]},

        {"title": "Ecologist",
         "description": "Study organisms and their interactions with ecosystems.",
         "skills": ["elementary evolutionary ecology", "principles of biology", "human heredity and development", "microbiology", "computational biology"]},
    ],

    # ── CHEMISTRY ────────────────────────────────────────────
    "Chemistry": [
        {"title": "Research Chemist",
         "description": "Perform basic and applied research in chemistry.",
         "skills": ["organic chemistry", "instrumental methods", "introduction to biochemistry", "organic chemistry majors laboratory", "analytical chemistry"]},

        {"title": "Analytical Chemist",
         "description": "Develop methods to identify and quantify chemical compounds.",
         "skills": ["instrumental methods", "organic chemistry", "organic chemistry majors laboratory", "introduction to biochemistry", "analytical chemistry"]},

        {"title": "Pharmaceutical Chemist",
         "description": "Develop and test drug compounds for medical use.",
         "skills": ["organic chemistry", "introduction to biochemistry", "pharmacology", "instrumental methods", "principles of biology"]},

        {"title": "Quality Control Chemist",
         "description": "Ensure product quality through chemical testing.",
         "skills": ["instrumental methods", "organic chemistry", "introduction to biochemistry", "analytical chemistry", "principles of biology"]},
    ],

    # ── EDUCATION ─────────────────────────────────────────────
    "Education": [
        {"title": "K-12 Teacher",
         "description": "Teach students in elementary, middle, or high school.",
         "skills": ["methods for teaching", "introduction to computer science", "educational game development", "engaging youth in computing", "principles of computing"]},

        {"title": "Instructional Designer",
         "description": "Design learning experiences and digital curricula.",
         "skills": ["educational game development", "introduction to computer science with web applications", "methods for teaching", "human-computer interaction", "engaging youth in computing"]},

        {"title": "EdTech Developer",
         "description": "Build educational software and online learning platforms.",
         "skills": ["educational game development", "development of assistive technology", "introduction to computer science with web applications", "software engineering", "human-computer interaction"]},

        {"title": "Special Education Teacher",
         "description": "Work with students who have learning disabilities.",
         "skills": ["development of assistive technology", "methods for teaching", "human-computer interaction", "educational game development", "principles of computing"]},
    ],

    # ── COMMUNICATION ────────────────────────────────────────
    "Communication": [
        {"title": "Journalist / Reporter",
         "description": "Research and report news stories for media outlets.",
         "skills": ["introduction to computer science with web applications", "logic for programming", "advanced web technologies", "computers, ethics and society", "principles of computing"]},

        {"title": "Technical Writer",
         "description": "Create clear documentation for complex technical products.",
         "skills": ["software engineering", "computers, ethics and society", "introduction to computer science", "advanced web technologies", "human-computer interaction"]},

        {"title": "Social Media Manager",
         "description": "Grow and manage an organization's social media presence.",
         "skills": ["introduction to computer science with web applications", "advanced web technologies", "introduction to data mining", "human-computer interaction", "principles of computing"]},

        {"title": "UX Writer",
         "description": "Write interface copy that guides users through digital products.",
         "skills": ["human-computer interaction", "introduction to computer science with web applications", "advanced web technologies", "software engineering", "development of assistive technology"]},
    ],

    # ── POLITICAL SCIENCE & PUBLIC POLICY ────────────────────
    "Political Science & Public Policy": [
        {"title": "Policy Analyst",
         "description": "Research and evaluate government policies and regulations.",
         "skills": ["introduction to statistical methods", "regression and experimental design", "computers, ethics and society", "logic for programming", "introduction to data mining"]},

        {"title": "Legislative Aide",
         "description": "Assist elected officials with research and policy work.",
         "skills": ["computers, ethics and society", "intellectual property in the digital age", "introduction to statistical methods", "logic for programming", "research"]},

        {"title": "Nonprofit Program Manager",
         "description": "Manage programs and measure impact for nonprofits.",
         "skills": ["information technology and organizational effectiveness", "introduction to statistical methods", "computers, ethics and society", "introduction to management information systems", "database management"]},
    ],

    # ── PSYCHOLOGY ───────────────────────────────────────────
    "Psychology": [
        {"title": "Human Factors / UX Researcher",
         "description": "Study how people interact with technology and design.",
         "skills": ["introduction to human-computer interaction", "development of assistive technology", "introduction to data mining", "introduction to statistical methods", "regression and experimental design"]},

        {"title": "Industrial-Organizational Psychologist",
         "description": "Apply psychology to workplace productivity and culture.",
         "skills": ["information technology and organizational effectiveness", "introduction to statistical methods", "regression and experimental design", "introduction to data mining", "human-computer interaction"]},

        {"title": "Behavioral Data Analyst",
         "description": "Analyze user behavior data for product improvement.",
         "skills": ["introduction to data mining", "introduction to statistical methods", "machine learning", "regression and experimental design", "introduction to human-computer interaction"]},
    ],

    # ── ENVIRONMENTAL SCIENCE ─────────────────────────────────
    "Environmental Science": [
        {"title": "Environmental Consultant",
         "description": "Advise clients on environmental compliance and sustainability.",
         "skills": ["environmental engineering processes", "principles of biology", "elementary evolutionary ecology", "introduction to statistical methods", "organic chemistry"]},

        {"title": "Climate / Data Scientist",
         "description": "Study climate systems and apply data science to environmental monitoring.",
         "skills": ["introduction to statistical methods", "regression and experimental design", "introduction to data mining", "machine learning", "environmental engineering processes"]},

        {"title": "Sustainability Manager",
         "description": "Lead corporate sustainability programs and reporting.",
         "skills": ["environmental engineering processes", "computers, ethics and society", "information technology and organizational effectiveness", "introduction to statistical methods", "principles of biology"]},
    ],

    # ── AGRICULTURAL SCIENCES ────────────────────────────────
    "Agricultural Sciences": [
        {"title": "Agricultural Engineer",
         "description": "Design farming equipment and irrigation systems.",
         "skills": ["principles of biology", "organic chemistry", "statics", "introduction to statistical methods", "environmental engineering processes"]},

        {"title": "Food Scientist",
         "description": "Develop and improve food products and safety standards.",
         "skills": ["introduction to biochemistry", "organic chemistry", "principles of biology", "instrumental methods", "microbiology"]},

        {"title": "Agricultural Data Analyst",
         "description": "Use data science to optimize farming operations.",
         "skills": ["introduction to statistical methods", "introduction to data mining", "regression and experimental design", "machine learning", "principles of biology"]},
    ],

    # ── CRIMINAL JUSTICE ─────────────────────────────────────
    "Criminal Justice": [
        {"title": "Law Enforcement Officer",
         "description": "Enforce laws and protect communities.",
         "skills": ["criminology", "introduction to legal studies", "social deviance", "juvenile delinquency", "law and society"]},

        {"title": "Cybercrime Investigator",
         "description": "Investigate digital crimes and gather electronic evidence.",
         "skills": ["digital forensics", "introduction to cybersecurity", "criminology", "pen test and reverse engineering", "introduction to legal studies"]},

        {"title": "Paralegal",
         "description": "Assist lawyers with legal research and case preparation.",
         "skills": ["introduction to legal studies", "law and society", "criminology", "law and social issues in business", "intellectual property in the digital age"]},

        {"title": "Criminologist",
         "description": "Study crime patterns and prevention strategies.",
         "skills": ["criminology", "social deviance", "juvenile delinquency", "introduction to statistical methods", "law and society"]},
    ],
}

if __name__ == "__main__":
    with open("all_jobs.json", "w") as f:
        json.dump(ALL_JOBS, f, indent=2)
    total = sum(len(v) for v in ALL_JOBS.values())
    print(f"Saved all_jobs.json: {len(ALL_JOBS)} programs, {total} total job roles")
