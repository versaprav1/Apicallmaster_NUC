"""
Smart Rate Limiter - Improvement over original 2.py's simple delays
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 6
    requests_per_hour: int = 60
    backoff_multiplier: float = 1.5
    max_backoff_seconds: int = 300

class SmartRateLimiter:
    """Smart rate limiter with exponential backoff (vs original 2.py's fixed 5min delays)"""
    
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
                print(f"⏳ Hourly rate limit reached. Waiting {wait_time:.0f} seconds...")
                await asyncio.sleep(wait_time)
        
        # Check per-minute limit
        minute_cutoff = now - timedelta(minutes=1)
        recent_requests = [t for t in self.request_times if t > minute_cutoff]
        
        if len(recent_requests) >= self.config.requests_per_minute:
            wait_time = 60 - (now - recent_requests[0]).total_seconds()
            if wait_time > 0:
                print(f"⏳ Per-minute rate limit reached. Waiting {wait_time:.0f} seconds...")
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
                    print(f"⏳ Backing off for {domain}: waiting {wait_time:.0f} seconds...")
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