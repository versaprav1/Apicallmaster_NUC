import asyncio
import time
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 10
    requests_per_hour: int = 100
    backoff_multiplier: float = 2.0
    max_backoff_seconds: int = 300
    
class SmartRateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.request_times: List[datetime] = []
        self.failed_attempts: Dict[str, int] = {}
        self.last_request_time: Dict[str, datetime] = {}
        
    async def wait_if_needed(self, domain: str = "default"):
        """Smart rate limiting with exponential backoff"""
        now = datetime.now()
        
        # Clean old request times
        cutoff = now - timedelta(hours=1)
        self.request_times = [t for t in self.request_times if t > cutoff]
        
        # Check hourly limit
        if len(self.request_times) >= self.config.requests_per_hour:
            wait_time = 3600 - (now - self.request_times[0]).total_seconds()
            if wait_time > 0:
                print(f"Hourly rate limit reached. Waiting {wait_time:.0f} seconds...")
                await asyncio.sleep(wait_time)
        
        # Check per-minute limit
        minute_cutoff = now - timedelta(minutes=1)
        recent_requests = [t for t in self.request_times if t > minute_cutoff]
        
        if len(recent_requests) >= self.config.requests_per_minute:
            wait_time = 60 - (now - recent_requests[0]).total_seconds()
            if wait_time > 0:
                print(f"Per-minute rate limit reached. Waiting {wait_time:.0f} seconds...")
                await asyncio.sleep(wait_time)
        
        # Domain-specific backoff for failed attempts
        if domain in self.failed_attempts:
            backoff_time = min(
                self.config.backoff_multiplier ** self.failed_attempts[domain],
                self.config.max_backoff_seconds
            )
            if domain in self.last_request_time:
                time_since_last = (now - self.last_request_time[domain]).total_seconds()
                if time_since_last < backoff_time:
                    wait_time = backoff_time - time_since_last
                    print(f"Backing off for {domain}: waiting {wait_time:.0f} seconds...")
                    await asyncio.sleep(wait_time)
        
        # Record this request
        self.request_times.append(now)
        self.last_request_time[domain] = now
    
    def record_success(self, domain: str = "default"):
        """Reset failure count on success"""
        if domain in self.failed_attempts:
            del self.failed_attempts[domain]
    
    def record_failure(self, domain: str = "default"):
        """Increment failure count for exponential backoff"""
        self.failed_attempts[domain] = self.failed_attempts.get(domain, 0) + 1

class EnhancedJobScraper:
    def __init__(self):
        self.rate_limiter = SmartRateLimiter(RateLimitConfig())
        self.session_stats = {
            'companies_processed': 0,
            'jobs_found': 0,
            'errors_encountered': 0,
            'rate_limit_hits': 0
        }
    
    async def scrape_with_resilience(self, company: str, max_retries: int = 3):
        """Scrape with smart rate limiting and error recovery"""
        domain = self.extract_domain(company)
        
        for attempt in range(max_retries):
            try:
                # Wait based on rate limiting rules
                await self.rate_limiter.wait_if_needed(domain)
                
                # Attempt scraping
                jobs = await self.scrape_company_jobs(company)
                
                # Record success
                self.rate_limiter.record_success(domain)
                self.session_stats['companies_processed'] += 1
                self.session_stats['jobs_found'] += len(jobs)
                
                return jobs
                
            except Exception as e:
                error_msg = str(e).lower()
                
                if '429' in error_msg or 'rate limit' in error_msg:
                    self.session_stats['rate_limit_hits'] += 1
                    self.rate_limiter.record_failure(domain)
                    print(f"Rate limited by {company}. Attempt {attempt + 1}/{max_retries}")
                    
                    if attempt < max_retries - 1:
                        # Exponential backoff for rate limits
                        wait_time = min(300, 60 * (2 ** attempt))
                        print(f"Waiting {wait_time} seconds before retry...")
                        await asyncio.sleep(wait_time)
                        continue
                
                elif 'timeout' in error_msg or 'connection' in error_msg:
                    print(f"Connection issue with {company}. Attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(30)  # Short wait for connection issues
                        continue
                
                else:
                    print(f"Unexpected error with {company}: {e}")
                    self.session_stats['errors_encountered'] += 1
                    break
        
        return []  # Return empty list if all retries failed
    
    def extract_domain(self, company: str) -> str:
        """Extract domain identifier from company name"""
        # Simple domain extraction - could be enhanced
        return company.lower().replace(' ', '_').replace('germany', '').strip('_')
    
    async def scrape_company_jobs(self, company: str):
        """Placeholder for actual scraping logic"""
        # This would contain your actual Agent-based scraping logic
        pass