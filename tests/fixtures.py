"""
Shared test fixtures for extraction pipeline tests.

Contains realistic sample texts and the expected LLM JSON responses
that the mock Bedrock client returns.
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Sample input texts (these come from Task 1's OCR pipeline)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SAMPLE_JOB_DESCRIPTION = """
Software Engineer - Cloud Infrastructure
Acme Corp - San Francisco, CA (Hybrid)

About the Role:
We are looking for a Software Engineer to join our Cloud Infrastructure team.
You will design, build, and maintain scalable cloud services that power our
platform serving 10M+ users.

Requirements:
- 5+ years of software engineering experience
- Strong proficiency in Python and Go
- Deep experience with AWS services (EC2, S3, Lambda, ECS)
- Kubernetes and container orchestration
- CI/CD pipeline design and implementation
- Strong understanding of distributed systems
- BS in Computer Science or equivalent

Preferred Qualifications:
- Experience with Terraform or CloudFormation for IaC
- Background in site reliability engineering (SRE)
- Familiarity with observability tools (Datadog, Prometheus, Grafana)
- Experience with gRPC and protocol buffers
- MS in Computer Science

Key Responsibilities:
- Design and implement cloud-native microservices
- Manage Kubernetes clusters across multiple regions
- Build and optimize CI/CD pipelines
- Participate in on-call rotation for production systems
- Mentor junior engineers on cloud best practices

Employment Type: Full-time
Salary Range: $180,000 - $240,000 + equity
"""

SAMPLE_RESUME = """
Jane Doe
jane.doe@email.com | (555) 019-9000 | linkedin.com/in/janedoe | San Francisco, CA

SUMMARY
Senior Software Engineer with 7 years of experience building scalable backend
systems and cloud infrastructure. Passionate about distributed systems,
developer tooling, and engineering best practices.

EXPERIENCE

Senior Software Engineer | TechCorp Inc. | Mar 2021 - Present
- Led migration of monolithic application to microservices architecture on AWS ECS
- Designed and implemented event-driven data pipeline processing 2M+ events/day using Python and Kafka
- Reduced deployment time by 60% by building automated CI/CD pipelines with GitHub Actions
- Mentored team of 4 junior engineers on cloud architecture patterns

Software Engineer | DataFlow Systems | Jun 2018 - Feb 2021
- Built RESTful APIs in Python (FastAPI) serving 500K daily requests
- Managed Kubernetes clusters on AWS EKS with Terraform for infrastructure as code
- Implemented distributed caching layer with Redis, improving response times by 40%
- Contributed to open-source monitoring tools used by 200+ companies

Junior Developer | StartupXYZ | Jan 2017 - May 2018
- Developed web application features using React and Node.js
- Wrote unit and integration tests achieving 90% code coverage
- Participated in agile ceremonies and code reviews

PROJECTS

Cloud Cost Optimizer
Automated AWS cost analysis tool using Python and Boto3 that identifies
underutilized resources. Reduced cloud spend by 25% for 3 client organizations.
Technologies: Python, Boto3, AWS Cost Explorer API, Lambda, DynamoDB

Distributed Task Queue
Open-source task scheduling system for Python applications with Redis backend.
800+ GitHub stars. Technologies: Python, Redis, Docker, GitHub Actions

EDUCATION
BS Computer Science | Stanford University | 2016

CERTIFICATIONS
- AWS Solutions Architect - Professional (2023)
- Certified Kubernetes Administrator (CKA) (2022)

SKILLS
Python, Go, JavaScript, SQL, AWS (EC2, S3, Lambda, ECS, EKS),
Kubernetes, Docker, Terraform, Redis, Kafka, PostgreSQL, FastAPI,
React, Node.js, CI/CD, Git, Linux, Datadog, Prometheus
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Expected LLM JSON responses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MOCK_JOB_EXTRACTION_RESPONSE = {
    "job_title": "Software Engineer - Cloud Infrastructure",
    "company_name": "Acme Corp",
    "location": "San Francisco, CA (Hybrid)",
    "required_skills": [
        "Python",
        "Go",
        "AWS",
        "Kubernetes",
        "CI/CD",
        "Distributed Systems",
    ],
    "preferred_skills": [
        "Terraform",
        "CloudFormation",
        "SRE",
        "Datadog",
        "Prometheus",
        "Grafana",
        "gRPC",
        "Protocol Buffers",
    ],
    "years_experience_required": 5,
    "education_requirements": [
        "BS in Computer Science or equivalent",
    ],
    "tools_and_technologies": [
        "AWS EC2",
        "AWS S3",
        "AWS Lambda",
        "AWS ECS",
        "Kubernetes",
        "Terraform",
        "CloudFormation",
        "Datadog",
        "Prometheus",
        "Grafana",
        "gRPC",
    ],
    "key_responsibilities": [
        "Design and implement cloud-native microservices",
        "Manage Kubernetes clusters across multiple regions",
        "Build and optimize CI/CD pipelines",
        "Participate in on-call rotation for production systems",
        "Mentor junior engineers on cloud best practices",
    ],
    "employment_type": "Full-time",
    "salary_range": "$180,000 - $240,000 + equity",
}

MOCK_RESUME_EXTRACTION_RESPONSE = {
    "candidate_name": "Jane Doe",
    "contact_info": "jane.doe@email.com | (555) 019-9000 | linkedin.com/in/janedoe",
    "resume_skills": [
        "Python",
        "Go",
        "JavaScript",
        "SQL",
        "AWS",
        "Kubernetes",
        "Docker",
        "Terraform",
        "Redis",
        "Kafka",
        "PostgreSQL",
        "FastAPI",
        "React",
        "Node.js",
        "CI/CD",
        "Git",
        "Linux",
        "Datadog",
        "Prometheus",
    ],
    "resume_experience": [
        {
            "title": "Senior Software Engineer",
            "company": "TechCorp Inc.",
            "duration": "Mar 2021 - Present",
            "highlights": [
                "Led migration of monolithic application to microservices on AWS ECS",
                "Designed event-driven data pipeline processing 2M+ events/day",
                "Reduced deployment time by 60% with automated CI/CD pipelines",
                "Mentored team of 4 junior engineers",
            ],
        },
        {
            "title": "Software Engineer",
            "company": "DataFlow Systems",
            "duration": "Jun 2018 - Feb 2021",
            "highlights": [
                "Built RESTful APIs in Python (FastAPI) serving 500K daily requests",
                "Managed Kubernetes clusters on AWS EKS with Terraform",
                "Implemented distributed caching with Redis, improving response times by 40%",
            ],
        },
        {
            "title": "Junior Developer",
            "company": "StartupXYZ",
            "duration": "Jan 2017 - May 2018",
            "highlights": [
                "Developed web application features using React and Node.js",
                "Wrote unit and integration tests achieving 90% code coverage",
            ],
        },
    ],
    "total_years_experience": 7,
    "resume_experience_summary": (
        "Senior Software Engineer with 7 years of progressive experience in "
        "backend development and cloud infrastructure. Career trajectory shows "
        "growth from junior web development to leading microservices migrations "
        "and mentoring teams. Core strengths include Python, AWS, Kubernetes, "
        "and building scalable distributed systems."
    ),
    "resume_projects": [
        {
            "name": "Cloud Cost Optimizer",
            "description": "Automated AWS cost analysis tool that identifies underutilized resources",
            "technologies": ["Python", "Boto3", "AWS Cost Explorer API", "Lambda", "DynamoDB"],
        },
        {
            "name": "Distributed Task Queue",
            "description": "Open-source task scheduling system for Python applications",
            "technologies": ["Python", "Redis", "Docker", "GitHub Actions"],
        },
    ],
    "education": [
        "BS Computer Science, Stanford University, 2016",
    ],
    "certifications": [
        "AWS Solutions Architect - Professional (2023)",
        "Certified Kubernetes Administrator (CKA) (2022)",
    ],
}