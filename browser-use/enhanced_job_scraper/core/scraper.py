"""
Enhanced Job Scraper Core - Uses browser-use with improvements
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass

# Import browser-use (same as your original 2.py)
from browser_use import Agent
from browser_use.llm import ChatGoogle, ChatOpenAI

from .rate_limiter import SmartRateLimiter, RateLimitConfig
from .data_validator import JobDataValidator, validate_and_clean_jobs
from ..strategies.company_configs import get_company_strategy

logger = logging.getLogger(__name__)

@dataclass
class JobResult:
    """Job extraction result"""
    company: str
    title: str
    link: str
    skills: str = ""
    description: str = ""
    posting_date: str = ""
    location: str = ""
    remote_onsite: str = ""
    quality_score: float = 0.0

class EnhancedJobScraper:
    """Enhanced job scraper using browser-use with improvements"""
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Smart rate limiter (improvement over original 2.py)
        self.rate_limiter = SmartRateLimiter(RateLimitConfig(
            requests_per_minute=6,  # More conservative than original
            requests_per_hour=60,
            backoff_multiplier=1.5,
            max_backoff_seconds=300
        ))
        
        # Data validator (new feature)
        self.validator = JobDataValidator()
        
        # Keywords for filtering (same as original 2.py)
        self.keywords = [
            "ai", "artificial intelligence", "machine learning", "ml", 
            "data science", "automation", "cloud", "aws", "azure", "gcp",
            "no-code", "low-code", "junior", "entry-level", "associate"
        ]
    
    async def scrape_company_jobs(self, company: str, max_jobs: int = 3) -> Dict:
        """
        Scrape jobs for a company using browser-use (enhanced version of your original logic)
        """
        logger.info(f"🔍 Starting job search for {company}")
        
        # Apply smart rate limiting
        domain = self._get_domain(company)
        await self.rate_limiter.wait_if_needed(domain)
        
        result = {
            'company': company,
            'jobs_found': 0,
            'valid_jobs': 0,
            'errors': 0,
            'rate_limit_hits': 0,
            'jobs': []
        }
        
        try:
            # Get company-specific strategy (improvement over generic approach)
            strategy = get_company_strategy(company)
            
            # Create enhanced prompt (better than original 2.py)
            prompt = self._create_enhanced_prompt(company, strategy)
            
            # Initialize browser-use Agent (same library as original)
            agent = Agent(
                task=prompt,
                llm=self._get_optimal_llm(company),
                # Enhanced browser configuration
                browser_config={
                    'headless': True,
                    'timeout': 120000,  # 2 minutes
                    'wait_between_actions': 2.0
                }
            )
            
            # Run the agent (same as original 2.py but with timeout)
            logger.info(f"🤖 Running browser-use agent for {company}")
            history = await asyncio.wait_for(agent.run(), timeout=180)  # 3 minute timeout
            
            # Extract jobs from agent history (enhanced extraction)
            raw_jobs = self._extract_jobs_from_history(history, company)
            result['jobs_found'] = len(raw_jobs)
            
            if raw_jobs:
                # Validate and clean jobs (new feature)
                valid_jobs, invalid_jobs = validate_and_clean_jobs(raw_jobs, self.keywords)
                result['valid_jobs'] = len(valid_jobs)
                result['jobs'] = valid_jobs
                
                # Save valid jobs (enhanced format)
                if valid_jobs:
                    self._save_jobs_to_csv(valid_jobs)
                    logger.info(f"💾 Saved {len(valid_jobs)} valid jobs for {company}")
                
                # Record success
                self.rate_limiter.record_success(domain)
            else:
                logger.warning(f"❌ No jobs extracted for {company}")
                
        except asyncio.TimeoutError:
            error_msg = f"Timeout after 3 minutes for {company}"
            logger.warning(error_msg)
            result['errors'] = 1
            self.rate_limiter.record_failure(domain)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"💥 Error scraping {company}: {error_msg}")
            result['errors'] = 1
            
            # Handle rate limiting (same as original 2.py but smarter)
            if '429' in error_msg or 'rate limit' in error_msg.lower():
                result['rate_limit_hits'] = 1
                self.rate_limiter.record_failure(domain)
            
        return result
    
    def _create_enhanced_prompt(self, company: str, strategy: Dict) -> str:
        """Create enhanced prompt (better than original 2.py)"""
        base_prompt = f"""
        Search for AI/ML/Data Science/Automation/Cloud/No-Code jobs at {company} in Germany.
        
        ENHANCED REQUIREMENTS:
        1. Focus on jobs posted within the last 30 days
        2. Target keywords: {', '.join(self.keywords)}
        3. Prioritize German locations or remote positions available in Germany
        4. Extract COMPLETE information for each job
        
        COMPANY-SPECIFIC STRATEGY:
        {strategy.get('navigation_instructions', 'Use standard job search approach')}
        
        EXTRACTION FORMAT:
        For each job, provide JSON with these fields:
        {{
            "job_title": "exact title",
            "job_link": "direct application URL", 
            "required_skills": "comma-separated skills",
            "job_description": "brief summary",
            "posting_date": "YYYY-MM-DD format if available",
            "location": "city, country",
            "remote_onsite": "Remote/Hybrid/Onsite"
        }}
        
        Find up to 3 most relevant positions. Verify all links are functional.
        """
        
        return base_prompt.strip()
    
    def _get_optimal_llm(self, company: str):
        """Get optimal LLM (distributes load better than original 2.py)"""
        # Distribute companies across different LLM providers to avoid rate limits
        company_hash = hash(company) % 3
        
        if company_hash == 0 and self.config.get('openai_api_key'):
            return ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        elif company_hash == 1 and self.config.get('google_api_key'):
            return ChatGoogle(model="gemini-2.0-flash", temperature=0.3)
        else:
            # Fallback to available provider
            if self.config.get('google_api_key'):
                return ChatGoogle(model="gemini-2.0-flash", temperature=0.3)
            else:
                return ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    
    def _extract_jobs_from_history(self, history, company: str) -> List[Dict]:
        """Extract jobs from browser-use agent history (enhanced version)"""
        jobs = []
        
        for step in history.history:
            if not step.result:
                continue
                
            for result in step.result:
                if not result.extracted_content:
                    continue
                
                try:
                    # Try JSON parsing first
                    if result.extracted_content.strip().startswith('{'):
                        data = json.loads(result.extracted_content)
                        job = self._parse_job_json(data, company)
                        if job:
                            jobs.append(job)
                    else:
                        # Parse as text (same logic as original 2.py but enhanced)
                        job = self._parse_job_text(result.extracted_content, company)
                        if job:
                            jobs.append(job)
                            
                except json.JSONDecodeError:
                    # Fallback to text parsing
                    job = self._parse_job_text(result.extracted_content, company)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Error parsing job data: {str(e)}")
                    continue
        
        return jobs
    
    def _parse_job_json(self, data: Dict, company: str) -> Dict:
        """Parse job from JSON format"""
        return {
            'company': company,
            'title': data.get('job_title', data.get('title', '')),
            'link': data.get('job_link', data.get('link', '')),
            'skills': data.get('required_skills', data.get('skills', '')),
            'description': data.get('job_description', data.get('description', '')),
            'posting_date': data.get('posting_date', ''),
            'location': data.get('location', ''),
            'remote_onsite': data.get('remote_onsite', data.get('work_type', ''))
        }
    
    def _parse_job_text(self, text: str, company: str) -> Dict:
        """Parse job from text format (similar to original 2.py but enhanced)"""
        lines = text.split('\n')
        job = {'company': company}
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'title' in key:
                    job['title'] = value
                elif 'link' in key or 'url' in key:
                    job['link'] = value
                elif 'skill' in key:
                    job['skills'] = value
                elif 'description' in key:
                    job['description'] = value
                elif 'date' in key:
                    job['posting_date'] = value
                elif 'location' in key:
                    job['location'] = value
                elif 'remote' in key or 'onsite' in key:
                    job['remote_onsite'] = value
        
        return job if job.get('title') else None
    
    def _save_jobs_to_csv(self, jobs: List[Dict]):
        """Save jobs to CSV (enhanced format compared to original 2.py)"""
        import csv
        import os
        
        filename = "outputs/enhanced_job_findings.csv"
        file_exists = os.path.exists(filename)
        
        # Enhanced fieldnames (more than original 2.py)
        fieldnames = [
            'Serial No', 'Company Name', 'Job Title', 'Job Link', 'Skills Required',
            'Job Description', 'Posting Date', 'Location', 'Remote/Onsite',
            'Quality Score', 'Extraction Timestamp'
        ]
        
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            for i, job in enumerate(jobs, 1):
                writer.writerow({
                    'Serial No': i,
                    'Company Name': job.get('company', ''),
                    'Job Title': job.get('title', ''),
                    'Job Link': job.get('link', ''),
                    'Skills Required': job.get('skills', ''),
                    'Job Description': job.get('description', ''),
                    'Posting Date': job.get('posting_date', ''),
                    'Location': job.get('location', ''),
                    'Remote/Onsite': job.get('remote_onsite', ''),
                    'Quality Score': job.get('quality_score', 0),
                    'Extraction Timestamp': datetime.now().isoformat()
                })
    
    def _get_domain(self, company: str) -> str:
        """Get domain identifier for rate limiting"""
        return company.lower().replace(' ', '_').replace('germany', '').strip('_')