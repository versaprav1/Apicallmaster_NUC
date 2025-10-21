"""
Data Quality Validator - New feature not in original 2.py
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class JobDataValidator:
    """Validate and score job data quality"""
    
    def __init__(self):
        self.german_cities = [
            "Berlin", "Hamburg", "München", "Munich", "Köln", "Cologne", "Frankfurt",
            "Stuttgart", "Düsseldorf", "Dortmund", "Essen", "Leipzig", "Bremen",
            "Dresden", "Hannover", "Nürnberg", "Nuremberg", "Duisburg", "Bochum"
        ]
        
        self.tech_keywords = [
            "ai", "artificial intelligence", "machine learning", "ml", "data science",
            "cloud", "aws", "azure", "gcp", "automation", "no-code", "low-code",
            "python", "java", "javascript", "react", "node", "docker", "kubernetes"
        ]
    
    def validate_job(self, job: Dict) -> Tuple[bool, float, List[str]]:
        """Validate job and return (is_valid, quality_score, issues)"""
        score = 0
        issues = []
        
        # Title validation (25 points)
        title = job.get('title', '').strip()
        if not title:
            issues.append("Missing job title")
        elif len(title) < 10:
            issues.append("Job title too short")
            score += 10
        else:
            score += 25
        
        # Link validation (20 points)
        link = job.get('link', '').strip()
        if not link:
            issues.append("Missing job link")
        elif not link.startswith('http'):
            issues.append("Invalid job link format")
            score += 5
        else:
            score += 20
        
        # Location validation (20 points)
        location = job.get('location', '').strip().lower()
        if not location:
            issues.append("Missing location")
            score += 5
        elif any(city.lower() in location for city in self.german_cities) or 'germany' in location:
            score += 20
        elif 'remote' in location:
            score += 15
            issues.append("Remote position - verify Germany eligibility")
        else:
            issues.append("Location may not be in Germany")
            score += 5
        
        # Skills validation (20 points)
        skills = job.get('skills', '').strip().lower()
        if not skills:
            issues.append("Missing skills information")
            score += 5
        else:
            relevant_skills = sum(1 for keyword in self.tech_keywords if keyword in skills)
            if relevant_skills >= 3:
                score += 20
            elif relevant_skills >= 1:
                score += 15
            else:
                issues.append("No relevant tech skills found")
                score += 5
        
        # Description validation (15 points)
        description = job.get('description', '').strip()
        if not description:
            issues.append("Missing job description")
            score += 3
        elif len(description) < 50:
            issues.append("Job description too short")
            score += 8
        else:
            score += 15
        
        is_valid = score >= 60 and not any('Missing job title' in issue or 'Missing job link' in issue for issue in issues)
        
        return is_valid, score, issues

def validate_and_clean_jobs(jobs: List[Dict], keywords: List[str]) -> Tuple[List[Dict], List[Dict]]:
    """Validate and clean job list"""
    validator = JobDataValidator()
    valid_jobs = []
    invalid_jobs = []
    
    for job in jobs:
        is_valid, quality_score, issues = validator.validate_job(job)
        
        # Add quality score to job
        job['quality_score'] = quality_score
        job['validation_issues'] = issues
        
        if is_valid:
            valid_jobs.append(job)
        else:
            invalid_jobs.append(job)
    
    return valid_jobs, invalid_jobs