import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse

@dataclass
class JobData:
    job_title: str
    job_link: str
    company: str
    location: str
    remote_type: str
    posting_date: str
    required_skills: List[str]
    job_description: str
    experience_level: str
    salary_range: Optional[str] = None
    application_deadline: Optional[str] = None

class JobDataValidator:
    def __init__(self):
        self.german_cities = {
            'berlin', 'hamburg', 'münchen', 'munich', 'köln', 'cologne', 'frankfurt',
            'stuttgart', 'düsseldorf', 'dortmund', 'essen', 'leipzig', 'bremen',
            'dresden', 'hannover', 'nürnberg', 'nuremberg', 'duisburg', 'bochum',
            'wuppertal', 'bielefeld', 'bonn', 'münster', 'karlsruhe', 'mannheim'
        }
        
        self.ai_ml_keywords = {
            'artificial intelligence', 'ai', 'machine learning', 'ml', 'deep learning',
            'neural networks', 'data science', 'data scientist', 'data analyst',
            'automation', 'rpa', 'cloud', 'aws', 'azure', 'gcp', 'google cloud',
            'no-code', 'low-code', 'chatbot', 'nlp', 'computer vision', 'tensorflow',
            'pytorch', 'python', 'r', 'sql', 'kubernetes', 'docker', 'devops'
        }
    
    def validate_job(self, job_data: Dict) -> Tuple[bool, List[str], JobData]:
        """Validate and clean job data"""
        errors = []
        warnings = []
        
        # Clean and validate job title
        job_title = self.clean_text(job_data.get('job_title', ''))
        if not job_title or len(job_title) < 5:
            errors.append("Job title is missing or too short")
        
        # Validate job link
        job_link = job_data.get('job_link', '').strip()
        if not self.is_valid_url(job_link):
            errors.append("Invalid or missing job link")
        
        # Validate location (must be Germany-related)
        location = self.clean_text(job_data.get('location', ''))
        if not self.is_german_location(location):
            warnings.append(f"Location '{location}' may not be in Germany")
        
        # Validate posting date
        posting_date = job_data.get('posting_date', '')
        if not self.is_recent_date(posting_date):
            warnings.append(f"Posting date '{posting_date}' is not recent or invalid")
        
        # Validate skills relevance
        skills = job_data.get('required_skills', [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(',')]
        
        if not self.has_relevant_skills(skills, job_title, job_data.get('job_description', '')):
            warnings.append("Job may not be relevant to AI/ML/Data Science/Cloud")
        
        # Create validated JobData object
        validated_job = JobData(
            job_title=job_title,
            job_link=job_link,
            company=self.clean_text(job_data.get('company', '')),
            location=location,
            remote_type=self.standardize_remote_type(job_data.get('remote_type', '')),
            posting_date=self.standardize_date(posting_date),
            required_skills=skills,
            job_description=self.clean_text(job_data.get('job_description', ''))[:500],  # Limit length
            experience_level=self.standardize_experience_level(job_data.get('experience_level', '')),
            salary_range=job_data.get('salary_range'),
            application_deadline=job_data.get('application_deadline')
        )
        
        is_valid = len(errors) == 0
        return is_valid, errors + warnings, validated_job
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common artifacts from web scraping
        text = re.sub(r'<[^>]+>', '', text)  # HTML tags
        text = re.sub(r'\n+', ' ', text)     # Multiple newlines
        
        return text
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def is_german_location(self, location: str) -> bool:
        """Check if location is in Germany"""
        location_lower = location.lower()
        
        # Check for explicit Germany mentions
        if any(term in location_lower for term in ['germany', 'deutschland', 'german']):
            return True
        
        # Check for German cities
        if any(city in location_lower for city in self.german_cities):
            return True
        
        # Check for remote work that allows Germany
        if 'remote' in location_lower and any(term in location_lower for term in ['eu', 'europe', 'emea']):
            return True
        
        return False
    
    def is_recent_date(self, date_str: str, days_threshold: int = 60) -> bool:
        """Check if date is within threshold"""
        if not date_str or date_str.lower() in ['n/a', 'not available']:
            return False
        
        try:
            # Try multiple date formats
            for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%b %d, %Y', '%d %b %Y']:
                try:
                    job_date = datetime.strptime(date_str.strip(), fmt)
                    return job_date >= datetime.now() - timedelta(days=days_threshold)
                except ValueError:
                    continue
            return False
        except:
            return False
    
    def has_relevant_skills(self, skills: List[str], job_title: str, job_description: str) -> bool:
        """Check if job is relevant to target skills"""
        all_text = f"{' '.join(skills)} {job_title} {job_description}".lower()
        
        # Check for AI/ML keywords
        return any(keyword in all_text for keyword in self.ai_ml_keywords)
    
    def standardize_remote_type(self, remote_type: str) -> str:
        """Standardize remote work type"""
        remote_lower = remote_type.lower()
        
        if any(term in remote_lower for term in ['remote', 'home', 'telecommute']):
            return 'Remote'
        elif any(term in remote_lower for term in ['hybrid', 'flexible']):
            return 'Hybrid'
        elif any(term in remote_lower for term in ['onsite', 'office', 'on-site']):
            return 'Onsite'
        else:
            return 'Not Specified'
    
    def standardize_date(self, date_str: str) -> str:
        """Standardize date format to YYYY-MM-DD"""
        if not date_str or date_str.lower() in ['n/a', 'not available']:
            return 'N/A'
        
        try:
            for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%b %d, %Y', '%d %b %Y']:
                try:
                    job_date = datetime.strptime(date_str.strip(), fmt)
                    return job_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            return date_str  # Return original if can't parse
        except:
            return date_str
    
    def standardize_experience_level(self, level: str) -> str:
        """Standardize experience level"""
        level_lower = level.lower()
        
        if any(term in level_lower for term in ['entry', 'junior', 'graduate', 'trainee', '0-2']):
            return 'Entry/Junior'
        elif any(term in level_lower for term in ['mid', 'intermediate', '2-5', '3-7']):
            return 'Mid-level'
        elif any(term in level_lower for term in ['senior', 'lead', '5+', '7+']):
            return 'Senior'
        else:
            return 'Not Specified'

# Usage example
def validate_and_save_jobs(raw_jobs: List[Dict], output_file: str):
    """Validate jobs and save only high-quality ones"""
    validator = JobDataValidator()
    validated_jobs = []
    validation_report = []
    
    for i, job in enumerate(raw_jobs):
        is_valid, messages, validated_job = validator.validate_job(job)
        
        if is_valid:
            validated_jobs.append(validated_job)
        
        validation_report.append({
            'job_index': i,
            'is_valid': is_valid,
            'messages': messages,
            'job_title': job.get('job_title', 'Unknown')
        })
    
    # Save validated jobs to CSV
    import csv
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if validated_jobs:
            fieldnames = [
                'job_title', 'job_link', 'company', 'location', 'remote_type',
                'posting_date', 'required_skills', 'job_description', 'experience_level',
                'salary_range', 'application_deadline'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for job in validated_jobs:
                writer.writerow({
                    'job_title': job.job_title,
                    'job_link': job.job_link,
                    'company': job.company,
                    'location': job.location,
                    'remote_type': job.remote_type,
                    'posting_date': job.posting_date,
                    'required_skills': ', '.join(job.required_skills),
                    'job_description': job.job_description,
                    'experience_level': job.experience_level,
                    'salary_range': job.salary_range or 'N/A',
                    'application_deadline': job.application_deadline or 'N/A'
                })
    
    return validated_jobs, validation_report