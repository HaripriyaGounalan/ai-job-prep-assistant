""" 
Schema definitions for job and resume data. 
Defines the expected structure of extracted information from job descriptions and resumes,
including fields for skills, experience, education, and more."""

JOB_SCHEMA = {
    "job_title": "",
    "company": "",
    "location": "",
    "salary_range": "",
    "required_skills": [],
    "preferred_skills": [],
    "years_experience_required": "",
    "education_required": [],
    "tools_and_technologies": [],
    "responsibilities": [],
    "soft_skills": [],
    "domain_knowledge": [],
    "certifications_preferred": [],
    "keywords": [],
    "job_description_summary": ""
}

RESUME_SCHEMA = {
    "candidate_name": "",
    "current_title": "",
    "location": "",
    "contact_info": {
        "phone": "",
        "email": ""
    },
    "profile_summary": "",
    "resume_skills": [],
    "tools_and_technologies": [],
    "work_experience": [],
    "education": [],
    "projects": [],
    "certifications": [],
    "awards": [],
    "coursework": [],
    "soft_skills": [],
    "domain_knowledge": [],
    "keywords": [],
    "years_of_experience": "",
    "resume_experience_summary": ""
}
