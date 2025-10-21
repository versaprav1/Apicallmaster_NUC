"""
Data quality and validation system for job scraping
"""

import re
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    score: float  # 0-100 quality score
    issues: List[str]
    suggestions: List[str]

class JobDataValidator:
    """Comprehensive job data validation and quality scoring"""
    
    def __init__(self):
        self.german_cities = self._load_german_cities()
        self.tech_keywords = self._load_tech_keywords()
        self.company_domains = self._load_company_domains()
    
    def _load_german_cities(self) -> List[str]:
        """Load list of German cities for location validation"""
        return [
            "Berlin", "Hamburg", "München", "Munich", "Köln", "Cologne", "Frankfurt",
            "Stuttgart", "Düsseldorf", "Dortmund", "Essen", "Leipzig", "Bremen",
            "Dresden", "Hannover", "Nürnberg", "Nuremberg", "Duisburg", "Bochum",
            "Wuppertal", "Bielefeld", "Bonn", "Münster", "Karlsruhe", "Mannheim",
            "Augsburg", "Wiesbaden", "Gelsenkirchen", "Mönchengladbach", "Braunschweig",
            "Chemnitz", "Kiel", "Aachen", "Halle", "Magdeburg", "Freiburg", "Krefeld",
            "Lübeck", "Oberhausen", "Erfurt", "Mainz", "Rostock", "Kassel", "Hagen",
            "Potsdam", "Saarbrücken", "Hamm", "Mülheim", "Ludwigshafen", "Leverkusen"
        ]
    
    def _load_tech_keywords(self) -> Dict[str, List[str]]:
        """Load technology keywords by category"""
        return {
            "ai_ml": [
                "artificial intelligence", "machine learning", "deep learning", "neural networks",
                "natural language processing", "nlp", "computer vision", "ai", "ml", "data science",
                "predictive analytics", "tensorflow", "pytorch", "scikit-learn", "pandas"
            ],
            "cloud": [
                "aws", "azure", "gcp", "google cloud", "cloud computing", "kubernetes", "docker",
                "serverless", "microservices", "devops", "ci/cd", "terraform", "ansible"
            ],
            "automation": [
                "automation", "rpa", "robotic process automation", "workflow automation",
                "process automation", "test automation", "deployment automation"
            ],
            "no_code": [
                "no-code", "low-code", "no code", "low code", "citizen developer",
                "visual programming", "drag and drop", "workflow builder"
            ],
            "data": [
                "data engineering", "data pipeline", "etl", "data warehouse", "big data",
                "analytics", "business intelligence", "bi", "sql", "nosql", "hadoop", "spark"
            ]
        }
    
    def _load_company_domains(self) -> Dict[str, str]:
        """Load known company domains for link validation"""
        return {
            "capgemini": "capgemini.com",
            "siemens": "siemens.com",
            "sap": "sap.com",
            "ibm": "ibm.com",
            "accenture": "accenture.com",
            "deloitte": "deloitte.com",
            "pwc": "pwc.com",
            "kpmg": "kpmg.com",
            "ey": "ey.com"
        }
    
    def validate_job(self, job_data: Dict) -> ValidationResult:
        """Comprehensive job validation with quality scoring"""
        issues = []
        suggestions = []
        score = 0
        
        # Title validation (20 points)
        title_score, title_issues, title_suggestions = self._validate_title(job_data.get('title', ''))
        score += title_score
        issues.extend(title_issues)
        suggestions.extend(title_suggestions)
        
        # Link validation (15 points)
        link_score, link_issues, link_suggestions = self._validate_link(
            job_data.get('link', ''), job_data.get('company', '')
        )
        score += link_score
        issues.extend(link_issues)
        suggestions.extend(link_suggestions)
        
        # Location validation (15 points)
        location_score, location_issues, location_suggestions = self._validate_location(
            job_data.get('location', '')
        )
        score += location_score
        issues.extend(location_issues)
        suggestions.extend(location_suggestions)
        
        # Skills validation (20 points)
        skills_score, skills_issues, skills_suggestions = self._validate_skills(
            job_data.get('skills', '')
        )
        score += skills_score
        issues.extend(skills_issues)
        suggestions.extend(skills_suggestions)
        
        # Description validation (15 points)
        desc_score, desc_issues, desc_suggestions = self._validate_description(
            job_data.get('description', '')
        )
        score += desc_score
        issues.extend(desc_issues)
        suggestions.extend(desc_suggestions)
        
        # Date validation (10 points)
        date_score, date_issues, date_suggestions = self._validate_date(
            job_data.get('posting_date', '')
        )
        score += date_score
        issues.extend(date_issues)
        suggestions.extend(date_suggestions)
        
        # Remote/onsite validation (5 points)
        remote_score, remote_issues, remote_suggestions = self._validate_remote_status(
            job_data.get('remote_onsite', '')
        )
        score += remote_score
        issues.extend(remote_issues)
        suggestions.extend(remote_suggestions)
        
        is_valid = score >= 60 and len([i for i in issues if 'Critical' in i]) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            score=score,
            issues=issues,
            suggestions=suggestions
        )
    
    def _validate_title(self, title: str) -> Tuple[float, List[str], List[str]]:
        """Validate job title"""
        issues = []
        suggestions = []
        score = 0
        
        if not title:
            issues.append("Critical: Missing job title")
            return 0, issues, suggestions
        
        if len(title) < 10:
            issues.append("Warning: Job title seems too short")
            suggestions.append("Verify title extraction is complete")
            score += 10
        elif len(title) > 100:
            issues.append("Warning: Job title seems too long")
            suggestions.append("Check if title includes extra information")
            score += 15
        else:
            score += 20
        
        # Check for relevant keywords
        title_lower = title.lower()
        relevant_keywords = 0
        for category, keywords in self.tech_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                relevant_keywords += 1
        
        if relevant_keywords == 0:
            issues.append("Warning: No relevant tech keywords in title")
            suggestions.append("Verify this is a tech/AI/ML related position")
        
        return score, issues, suggestions
    
    def _validate_link(self, link: str, company: str) -> Tuple[float, List[str], List[str]]:
        """Validate job link"""
        issues = []
        suggestions = []
        score = 0
        
        if not link:
            issues.append("Critical: Missing job link")
            return 0, issues, suggestions
        
        # Basic URL validation
        try:
            parsed = urlparse(link)
            if not parsed.scheme or not parsed.netloc:
                issues.append("Critical: Invalid URL format")
                return 0, issues, suggestions
        except Exception:
            issues.append("Critical: Malformed URL")
            return 0, issues, suggestions
        
        score += 10
        
        # Check if link matches company domain
        company_key = company.lower().replace(' ', '').replace('germany', '')
        expected_domain = self.company_domains.get(company_key)
        
        if expected_domain and expected_domain not in link.lower():
            issues.append(f"Warning: Link domain doesn't match expected {expected_domain}")
            suggestions.append("Verify link leads to correct company job posting")
        else:
            score += 5
        
        return score, issues, suggestions
    
    def _validate_location(self, location: str) -> Tuple[float, List[str], List[str]]:
        """Validate job location"""
        issues = []
        suggestions = []
        score = 0
        
        if not location:
            issues.append("Warning: Missing location information")
            suggestions.append("Try to extract location from job posting")
            return 5, issues, suggestions
        
        location_lower = location.lower()
        
        # Check for German cities
        german_city_found = any(city.lower() in location_lower for city in self.german_cities)
        
        if german_city_found or 'germany' in location_lower or 'deutschland' in location_lower:
            score += 15
        elif 'remote' in location_lower or 'hybrid' in location_lower:
            score += 10
            suggestions.append("Verify remote position is available for Germany")
        else:
            issues.append("Warning: Location may not be in Germany")
            suggestions.append("Confirm job is available for German candidates")
            score += 5
        
        return score, issues, suggestions
    
    def _validate_skills(self, skills: str) -> Tuple[float, List[str], List[str]]:
        """Validate required skills"""
        issues = []
        suggestions = []
        score = 0
        
        if not skills:
            issues.append("Warning: Missing skills information")
            suggestions.append("Try to extract required skills from job description")
            return 5, issues, suggestions
        
        skills_lower = skills.lower()
        
        # Count relevant skill categories
        relevant_categories = 0
        for category, keywords in self.tech_keywords.items():
            if any(keyword in skills_lower for keyword in keywords):
                relevant_categories += 1
        
        if relevant_categories >= 3:
            score += 20
        elif relevant_categories >= 2:
            score += 15
        elif relevant_categories >= 1:
            score += 10
        else:
            issues.append("Warning: No relevant tech skills found")
            suggestions.append("Verify this is a technical position")
            score += 5
        
        return score, issues, suggestions
    
    def _validate_description(self, description: str) -> Tuple[float, List[str], List[str]]:
        """Validate job description"""
        issues = []
        suggestions = []
        score = 0
        
        if not description:
            issues.append("Warning: Missing job description")
            suggestions.append("Try to extract full job description")
            return 5, issues, suggestions
        
        if len(description) < 100:
            issues.append("Warning: Job description seems too short")
            suggestions.append("Try to get complete job description")
            score += 8
        elif len(description) > 2000:
            score += 15
        else:
            score += 12
        
        # Check for key sections
        desc_lower = description.lower()
        if 'responsibilities' in desc_lower or 'duties' in desc_lower:
            score += 2
        if 'requirements' in desc_lower or 'qualifications' in desc_lower:
            score += 1
        
        return score, issues, suggestions
    
    def _validate_date(self, posting_date: str) -> Tuple[float, List[str], List[str]]:
        """Validate posting date"""
        issues = []
        suggestions = []
        score = 0
        
        if not posting_date:
            issues.append("Info: Missing posting date")
            suggestions.append("Try to extract posting date if available")
            return 5, issues, suggestions
        
        # Try to parse date
        try:
            # Common date formats
            date_formats = [
                "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
                "%b %d, %Y", "%d %b %Y", "%B %d, %Y"
            ]
            
            parsed_date = None
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(posting_date.strip(), fmt)
                    break
                except ValueError:
                    continue
            
            if parsed_date:
                days_ago = (datetime.now() - parsed_date).days
                if days_ago <= 30:
                    score += 10
                elif days_ago <= 60:
                    score += 7
                    issues.append("Info: Job posting is older than 30 days")
                else:
                    score += 3
                    issues.append("Warning: Job posting is quite old")
            else:
                issues.append("Warning: Could not parse posting date")
                score += 3
                
        except Exception:
            issues.append("Warning: Invalid date format")
            score += 3
        
        return score, issues, suggestions
    
    def _validate_remote_status(self, remote_status: str) -> Tuple[float, List[str], List[str]]:
        """Validate remote/onsite status"""
        issues = []
        suggestions = []
        score = 0
        
        if not remote_status:
            issues.append("Info: Missing remote/onsite information")
            return 2, issues, suggestions
        
        status_lower = remote_status.lower()
        if any(word in status_lower for word in ['remote', 'hybrid', 'onsite', 'office']):
            score += 5
        else:
            score += 2
            suggestions.append("Clarify work arrangement (remote/hybrid/onsite)")
        
        return score, issues, suggestions

class JobDeduplicator:
    """Remove duplicate jobs based on multiple criteria"""
    
    def __init__(self):
        self.seen_jobs = set()
    
    def is_duplicate(self, job_data: Dict) -> bool:
        """Check if job is a duplicate"""
        # Create signature based on title, company, and link
        title = job_data.get('title', '').lower().strip()
        company = job_data.get('company', '').lower().strip()
        link = job_data.get('link', '').strip()
        
        # Normalize title (remove common variations)
        title = re.sub(r'\s*\([^)]*\)\s*', '', title)  # Remove parentheses
        title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
        
        signature = f"{company}|{title}|{link}"
        
        if signature in self.seen_jobs:
            return True
        
        self.seen_jobs.add(signature)
        return False
    
    def find_similar_jobs(self, job_data: Dict, threshold: float = 0.8) -> List[str]:
        """Find similar jobs that might be duplicates"""
        # This could be enhanced with fuzzy matching
        # For now, just check for very similar titles
        similar = []
        current_title = job_data.get('title', '').lower()
        
        for seen_signature in self.seen_jobs:
            _, seen_title, _ = seen_signature.split('|')
            
            # Simple similarity check
            if len(current_title) > 0 and len(seen_title) > 0:
                common_words = set(current_title.split()) & set(seen_title.split())
                similarity = len(common_words) / max(len(current_title.split()), len(seen_title.split()))
                
                if similarity >= threshold:
                    similar.append(seen_signature)
        
        return similar

# Usage example
def validate_and_clean_jobs(jobs: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Validate and clean job data"""
    validator = JobDataValidator()
    deduplicator = JobDeduplicator()
    
    valid_jobs = []
    invalid_jobs = []
    
    for job in jobs:
        # Check for duplicates
        if deduplicator.is_duplicate(job):
            logger.info(f"Skipping duplicate job: {job.get('title', 'Unknown')}")
            continue
        
        # Validate job data
        validation = validator.validate_job(job)
        
        job['validation_score'] = validation.score
        job['validation_issues'] = validation.issues
        job['validation_suggestions'] = validation.suggestions
        
        if validation.is_valid:
            valid_jobs.append(job)
            logger.info(f"Valid job (score: {validation.score:.1f}): {job.get('title', 'Unknown')}")
        else:
            invalid_jobs.append(job)
            logger.warning(f"Invalid job (score: {validation.score:.1f}): {job.get('title', 'Unknown')}")
            for issue in validation.issues:
                logger.warning(f"  - {issue}")
    
    return valid_jobs, invalid_jobs