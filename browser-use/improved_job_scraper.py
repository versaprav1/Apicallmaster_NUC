import asyncio
import csv
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv
load_dotenv()

from browser_use import Agent
from browser_use.llm import ChatGoogle, ChatOpenAI
from rate_limiter import SmartRateLimiter, RateLimitConfig

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class JobData:
    """Structured job data with validation"""
    company: str
    title: str
    link: str
    skills: str = ""
    description: str = ""
    posting_date: str = ""
    location: str = ""
    remote_onsite: str = ""
    salary_range: str = ""
    experience_level: str = ""
    
    def is_valid(self) -> bool:
        """Check if job has minimum required fields"""
        return bool(self.title and (self.link or self.description))
    
    def matches_criteria(self, keywords: List[str]) -> bool:
        """Check if job matches search criteria"""
        text = f"{self.title} {self.skills} {self.description}".lower()
        return any(keyword.lower() in text for keyword in keywords)

class EnhancedJobScraper:
    def __init__(self):
        self.rate_limiter = SmartRateLimiter(RateLimitConfig(
            requests_per_minute=8,  # More conservative
            requests_per_hour=80,
            backoff_multiplier=1.5,
            max_backoff_seconds=600  # 10 minutes max
        ))
        
        # Company-specific configurations
        self.company_configs = self._load_company_configs()
        
        # Session tracking
        self.session_stats = {
            'start_time': datetime.now(),
            'companies_processed': 0,
            'jobs_found': 0,
            'errors_encountered': 0,
            'rate_limit_hits': 0,
            'successful_extractions': 0
        }
        
        # Keywords for filtering
        self.target_keywords = [
            "ai", "artificial intelligence", "machine learning", "ml", 
            "data science", "automation", "cloud", "aws", "azure", "gcp",
            "no-code", "low-code", "junior", "entry-level", "associate"
        ]
    
    def _load_company_configs(self) -> Dict:
        """Load company-specific scraping configurations"""
        return {
            "default": {
                "max_retries": 3,
                "timeout_seconds": 120,
                "wait_between_actions": 2,
                "custom_prompt_additions": ""
            },
            "capgemini": {
                "max_retries": 2,
                "timeout_seconds": 180,
                "custom_prompt_additions": "Focus on Capgemini Invent roles and consulting positions."
            },
            "siemens": {
                "max_retries": 3,
                "timeout_seconds": 150,
                "custom_prompt_additions": "Look for digital transformation and Industry 4.0 roles."
            },
            "sap": {
                "max_retries": 2,
                "timeout_seconds": 200,
                "custom_prompt_additions": "Focus on cloud platform and enterprise software roles."
            }
        }
    
    async def scrape_company_jobs(self, company: str, max_jobs: int = 3) -> Tuple[List[JobData], List[str]]:
        """Enhanced job scraping with better error handling"""
        domain = self._extract_domain(company)
        config = self.company_configs.get(domain, self.company_configs["default"])
        
        # Wait for rate limiting
        await self.rate_limiter.wait_if_needed(domain)
        
        try:
            # Create enhanced prompt
            prompt = self._create_enhanced_prompt(company, config)
            
            # Initialize agent with timeout
            agent = Agent(
                task=prompt,
                llm=self._get_optimal_llm(company),
                # Add browser configuration for better reliability
                browser_config={
                    'headless': True,
                    'timeout': config['timeout_seconds'] * 1000,
                    'wait_between_actions': config['wait_between_actions']
                }
            )
            
            logger.info(f"Starting job search for {company}")
            
            # Run with timeout
            history = await asyncio.wait_for(
                agent.run(), 
                timeout=config['timeout_seconds']
            )
            
            # Extract and validate jobs
            jobs, errors = self._extract_jobs_from_history(history, company, max_jobs)
            
            # Filter jobs by criteria
            valid_jobs = [job for job in jobs if job.is_valid() and job.matches_criteria(self.target_keywords)]
            
            self.rate_limiter.record_success(domain)
            self.session_stats['successful_extractions'] += 1
            
            logger.info(f"Successfully extracted {len(valid_jobs)} valid jobs for {company}")
            return valid_jobs, errors
            
        except asyncio.TimeoutError:
            error_msg = f"Timeout after {config['timeout_seconds']} seconds for {company}"
            logger.warning(error_msg)
            self.rate_limiter.record_failure(domain)
            return [], [error_msg]
            
        except Exception as e:
            error_msg = f"Error scraping {company}: {str(e)}"
            logger.error(error_msg)
            
            # Handle specific error types
            if '429' in str(e) or 'rate limit' in str(e).lower():
                self.session_stats['rate_limit_hits'] += 1
                self.rate_limiter.record_failure(domain)
            else:
                self.session_stats['errors_encountered'] += 1
            
            return [], [error_msg]
    
    def _create_enhanced_prompt(self, company: str, config: Dict) -> str:
        """Create more specific and effective prompts"""
        base_prompt = f"""
        Search for AI/ML/Data Science/Automation/Cloud/No-Code jobs at {company} in Germany.
        
        SPECIFIC REQUIREMENTS:
        1. Focus on jobs posted within the last 30 days
        2. Prioritize roles mentioning: AI agents, machine learning, data science, cloud platforms (AWS/Azure/GCP), automation, no-code/low-code
        3. Include junior/entry-level and associate positions
        4. Extract COMPLETE information for each job:
           - Exact job title
           - Direct job application link
           - Required skills (as detailed list)
           - Full job description summary
           - Posting date (exact date if available)
           - Location (city, state/region)
           - Remote/hybrid/onsite status
           - Salary range (if mentioned)
           - Experience level required
        
        SEARCH STRATEGY:
        1. Start with the company's main careers page
        2. Use search filters for location (Germany) and job categories (Technology, IT, Data, AI)
        3. If initial search yields few results, try broader terms like "digital", "technology", "consultant"
        4. Click into individual job postings to get complete details
        5. Verify job locations are in Germany or remote-friendly for Germany
        
        OUTPUT FORMAT:
        For each job found, provide a JSON object with all fields, even if some are empty.
        
        {config.get('custom_prompt_additions', '')}
        """
        return base_prompt.strip()
    
    def _get_optimal_llm(self, company: str):
        """Choose optimal LLM based on company and availability"""
        # Use different models to distribute load and avoid rate limits
        company_hash = hash(company) % 3
        
        if company_hash == 0 and os.getenv('OPENAI_API_KEY'):
            return ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        elif company_hash == 1 and os.getenv('GOOGLE_API_KEY'):
            return ChatGoogle(model="gemini-2.0-flash", temperature=0.3)
        else:
            # Fallback to available model
            if os.getenv('GOOGLE_API_KEY'):
                return ChatGoogle(model="gemini-2.0-flash", temperature=0.3)
            else:
                return ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    
    def _extract_jobs_from_history(self, history, company: str, max_jobs: int) -> Tuple[List[JobData], List[str]]:
        """Enhanced job extraction with better parsing"""
        jobs = []
        errors = []
        
        for step in history.history:
            if not step.result:
                continue
                
            for result in step.result:
                if not result.extracted_content:
                    continue
                
                try:
                    # Try to parse as JSON first
                    if result.extracted_content.strip().startswith('{'):
                        data = json.loads(result.extracted_content)
                        job = self._parse_job_json(data, company)
                        if job:
                            jobs.append(job)
                    else:
                        # Parse as text
                        job = self._parse_job_text(result.extracted_content, company)
                        if job:
                            jobs.append(job)
                            
                except json.JSONDecodeError:
                    # Try text parsing
                    job = self._parse_job_text(result.extracted_content, company)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    errors.append(f"Error parsing job data: {str(e)}")
                
                if len(jobs) >= max_jobs:
                    break
        
        return jobs[:max_jobs], errors
    
    def _parse_job_json(self, data: Dict, company: str) -> Optional[JobData]:
        """Parse job data from JSON format"""
        try:
            return JobData(
                company=company,
                title=data.get('job_title', data.get('title', '')),
                link=data.get('job_link', data.get('link', data.get('url', ''))),
                skills=self._format_skills(data.get('required_skills', data.get('skills', ''))),
                description=data.get('job_description', data.get('description', '')),
                posting_date=data.get('posting_date', data.get('date', '')),
                location=data.get('location', ''),
                remote_onsite=data.get('remote_onsite', data.get('work_type', '')),
                salary_range=data.get('salary_range', data.get('salary', '')),
                experience_level=data.get('experience_level', data.get('level', ''))
            )
        except Exception:
            return None
    
    def _parse_job_text(self, text: str, company: str) -> Optional[JobData]:
        """Parse job data from text format"""
        lines = text.split('\n')
        job_data = {'company': company}
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'title' in key:
                    job_data['title'] = value
                elif 'link' in key or 'url' in key:
                    job_data['link'] = value
                elif 'skill' in key:
                    job_data['skills'] = value
                elif 'description' in key:
                    job_data['description'] = value
                elif 'date' in key:
                    job_data['posting_date'] = value
                elif 'location' in key:
                    job_data['location'] = value
                elif 'remote' in key or 'onsite' in key:
                    job_data['remote_onsite'] = value
                elif 'salary' in key:
                    job_data['salary_range'] = value
                elif 'experience' in key or 'level' in key:
                    job_data['experience_level'] = value
        
        if job_data.get('title'):
            return JobData(**job_data)
        return None
    
    def _format_skills(self, skills) -> str:
        """Format skills consistently"""
        if isinstance(skills, list):
            return ', '.join(skills)
        return str(skills) if skills else ""
    
    def _extract_domain(self, company: str) -> str:
        """Extract domain identifier from company name"""
        return company.lower().replace(' ', '_').replace('germany', '').strip('_')
    
    def save_progress(self, jobs: List[JobData], filename: str = "enhanced_job_findings.csv"):
        """Save jobs with enhanced data structure"""
        fieldnames = [
            'Serial No', 'Company Name', 'Job Title', 'Job Link', 'Skills Required',
            'Job Description', 'Posting Date', 'Location', 'Remote/Onsite',
            'Salary Range', 'Experience Level', 'Extraction Timestamp'
        ]
        
        file_exists = os.path.exists(filename)
        
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            for i, job in enumerate(jobs, 1):
                writer.writerow({
                    'Serial No': i,
                    'Company Name': job.company,
                    'Job Title': job.title,
                    'Job Link': job.link,
                    'Skills Required': job.skills,
                    'Job Description': job.description,
                    'Posting Date': job.posting_date,
                    'Location': job.location,
                    'Remote/Onsite': job.remote_onsite,
                    'Salary Range': job.salary_range,
                    'Experience Level': job.experience_level,
                    'Extraction Timestamp': datetime.now().isoformat()
                })
    
    def print_session_stats(self):
        """Print comprehensive session statistics"""
        duration = datetime.now() - self.session_stats['start_time']
        
        print(f"\n{'='*50}")
        print(f"SESSION STATISTICS")
        print(f"{'='*50}")
        print(f"Duration: {duration}")
        print(f"Companies Processed: {self.session_stats['companies_processed']}")
        print(f"Jobs Found: {self.session_stats['jobs_found']}")
        print(f"Successful Extractions: {self.session_stats['successful_extractions']}")
        print(f"Rate Limit Hits: {self.session_stats['rate_limit_hits']}")
        print(f"Errors Encountered: {self.session_stats['errors_encountered']}")
        
        if self.session_stats['companies_processed'] > 0:
            success_rate = (self.session_stats['successful_extractions'] / 
                          self.session_stats['companies_processed']) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        print(f"{'='*50}\n")

# Example usage
async def main():
    scraper = EnhancedJobScraper()
    
    # Priority companies for testing
    test_companies = [
        "Capgemini Germany", "Siemens", "SAP", "IBM Germany", 
        "Accenture Germany", "KPMG Germany"
    ]
    
    all_jobs = []
    
    for company in test_companies:
        try:
            jobs, errors = await scraper.scrape_company_jobs(company, max_jobs=2)
            
            if jobs:
                all_jobs.extend(jobs)
                scraper.session_stats['jobs_found'] += len(jobs)
                print(f"✅ {company}: Found {len(jobs)} jobs")
            else:
                print(f"❌ {company}: No jobs found")
            
            if errors:
                for error in errors:
                    logger.warning(f"{company}: {error}")
            
            scraper.session_stats['companies_processed'] += 1
            
            # Wait between companies
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Failed to process {company}: {e}")
    
    # Save results
    if all_jobs:
        scraper.save_progress(all_jobs)
        print(f"\n💾 Saved {len(all_jobs)} jobs to enhanced_job_findings.csv")
    
    # Print statistics
    scraper.print_session_stats()

if __name__ == "__main__":
    asyncio.run(main())