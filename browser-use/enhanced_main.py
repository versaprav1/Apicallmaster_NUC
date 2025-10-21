"""
Enhanced main script integrating all improvements
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import List, Dict
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Import our enhanced modules
from improved_job_scraper import EnhancedJobScraper, JobData
from company_strategies import CompanyNavigationStrategies
from data_quality import validate_and_clean_jobs, JobDataValidator
from monitoring_dashboard import ScrapingMonitor, ScrapingMetrics, AlertSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class EnhancedJobScrapingOrchestrator:
    """Main orchestrator for enhanced job scraping"""
    
    def __init__(self):
        self.scraper = EnhancedJobScraper()
        self.strategies = CompanyNavigationStrategies()
        self.validator = JobDataValidator()
        self.monitor = ScrapingMonitor()
        self.alert_system = AlertSystem(self.monitor)
        
        # Priority companies (start with these for testing)
        self.priority_companies = [
            "Capgemini Germany", "Siemens", "SAP", "IBM Germany",
            "Accenture Germany", "KPMG Germany", "Deloitte Germany"
        ]
        
        # Extended company list
        self.all_companies = [
            "TCS Germany", "Capgemini Germany", "Accenture Germany", "IBM Germany", 
            "Deloitte Germany", "PwC Germany", "KPMG Germany", "EY Germany",
            "Siemens", "SAP", "Bosch", "Allianz", "Deutsche Telekom", "Bayer", 
            "BMW", "Volkswagen", "Mercedes-Benz", "Infineon", "Zalando",
            "Amazon", "Google", "Microsoft", "Oracle", "Salesforce", "NVIDIA"
        ]
    
    async def run_enhanced_scraping(self, 
                                  companies: List[str] = None, 
                                  max_jobs_per_company: int = 3,
                                  test_mode: bool = False) -> Dict:
        """Run enhanced scraping with all improvements"""
        
        if companies is None:
            companies = self.priority_companies if test_mode else self.all_companies
        
        logger.info(f"🚀 Starting enhanced job scraping for {len(companies)} companies")
        logger.info(f"📊 Test mode: {test_mode}, Max jobs per company: {max_jobs_per_company}")
        
        session_start = datetime.now()
        results = {
            'companies_processed': 0,
            'total_jobs_found': 0,
            'valid_jobs': 0,
            'companies_with_jobs': 0,
            'total_errors': 0,
            'rate_limit_hits': 0,
            'jobs_by_company': {},
            'session_duration': 0
        }
        
        all_valid_jobs = []
        
        for i, company in enumerate(companies, 1):
            logger.info(f"📍 Processing {company} ({i}/{len(companies)})")
            
            company_start = datetime.now()
            
            try:
                # Get company-specific strategy
                strategy_config = self.strategies.get_strategy(company)
                
                # Scrape jobs with enhanced error handling
                jobs, errors = await self.scraper.scrape_company_jobs(
                    company, max_jobs=max_jobs_per_company
                )
                
                company_duration = (datetime.now() - company_start).total_seconds()
                
                # Convert to dict format for validation
                job_dicts = []
                for job in jobs:
                    if isinstance(job, JobData):
                        job_dict = {
                            'company': job.company,
                            'title': job.title,
                            'link': job.link,
                            'skills': job.skills,
                            'description': job.description,
                            'posting_date': job.posting_date,
                            'location': job.location,
                            'remote_onsite': job.remote_onsite,
                            'salary_range': job.salary_range,
                            'experience_level': job.experience_level
                        }
                        job_dicts.append(job_dict)
                
                # Validate and clean jobs
                valid_jobs, invalid_jobs = validate_and_clean_jobs(job_dicts)
                
                # Record metrics
                avg_quality = sum(job.get('validation_score', 0) for job in valid_jobs) / len(valid_jobs) if valid_jobs else 0
                success_rate = (len(valid_jobs) / len(job_dicts)) * 100 if job_dicts else 0
                
                metrics = ScrapingMetrics(
                    timestamp=datetime.now().isoformat(),
                    company=company,
                    jobs_found=len(job_dicts),
                    jobs_valid=len(valid_jobs),
                    avg_quality_score=avg_quality,
                    errors_count=len(errors),
                    rate_limit_hits=1 if any('429' in str(e) for e in errors) else 0,
                    execution_time_seconds=company_duration,
                    success_rate=success_rate
                )
                
                self.monitor.record_session_metrics(metrics)
                
                # Record individual jobs
                for job in valid_jobs:
                    self.monitor.record_job_data(job)
                
                # Update results
                results['companies_processed'] += 1
                results['total_jobs_found'] += len(job_dicts)
                results['valid_jobs'] += len(valid_jobs)
                results['total_errors'] += len(errors)
                results['rate_limit_hits'] += metrics.rate_limit_hits
                
                if valid_jobs:
                    results['companies_with_jobs'] += 1
                    all_valid_jobs.extend(valid_jobs)
                
                results['jobs_by_company'][company] = {
                    'total': len(job_dicts),
                    'valid': len(valid_jobs),
                    'quality_score': avg_quality,
                    'errors': len(errors)
                }
                
                # Log results
                if valid_jobs:
                    logger.info(f"✅ {company}: {len(valid_jobs)} valid jobs (avg quality: {avg_quality:.1f})")
                    for job in valid_jobs[:2]:  # Show first 2 jobs
                        logger.info(f"   📋 {job['title']} - {job.get('location', 'Unknown location')}")
                else:
                    logger.warning(f"❌ {company}: No valid jobs found")
                
                if errors:
                    logger.warning(f"⚠️ {company}: {len(errors)} errors encountered")
                
                # Wait between companies (respect rate limits)
                if i < len(companies):  # Don't wait after last company
                    wait_time = 45 if test_mode else 90  # Shorter wait in test mode
                    logger.info(f"⏳ Waiting {wait_time} seconds before next company...")
                    await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"💥 Failed to process {company}: {str(e)}")
                results['total_errors'] += 1
                
                # Record failed attempt
                failed_metrics = ScrapingMetrics(
                    timestamp=datetime.now().isoformat(),
                    company=company,
                    jobs_found=0,
                    jobs_valid=0,
                    avg_quality_score=0,
                    errors_count=1,
                    rate_limit_hits=0,
                    execution_time_seconds=(datetime.now() - company_start).total_seconds(),
                    success_rate=0
                )
                self.monitor.record_session_metrics(failed_metrics)
        
        # Calculate session duration
        results['session_duration'] = (datetime.now() - session_start).total_seconds()
        
        # Save all valid jobs
        if all_valid_jobs:
            self.save_enhanced_results(all_valid_jobs)
        
        # Generate session report
        self.print_session_summary(results)
        
        # Check for alerts
        alerts = self.alert_system.check_alerts()
        if alerts:
            logger.warning("🚨 ALERTS DETECTED:")
            for alert in alerts:
                logger.warning(f"  {alert}")
        
        return results
    
    def save_enhanced_results(self, jobs: List[Dict], filename: str = None):
        """Save results with enhanced format"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"enhanced_jobs_{timestamp}.csv"
        
        # Use the scraper's save method
        job_data_objects = []
        for job in jobs:
            job_obj = JobData(
                company=job.get('company', ''),
                title=job.get('title', ''),
                link=job.get('link', ''),
                skills=job.get('skills', ''),
                description=job.get('description', ''),
                posting_date=job.get('posting_date', ''),
                location=job.get('location', ''),
                remote_onsite=job.get('remote_onsite', ''),
                salary_range=job.get('salary_range', ''),
                experience_level=job.get('experience_level', '')
            )
            job_data_objects.append(job_obj)
        
        self.scraper.save_progress(job_data_objects, filename)
        logger.info(f"💾 Saved {len(jobs)} jobs to {filename}")
    
    def print_session_summary(self, results: Dict):
        """Print comprehensive session summary"""
        duration_minutes = results['session_duration'] / 60
        
        print(f"\n{'='*60}")
        print(f"🎯 ENHANCED JOB SCRAPING SESSION COMPLETE")
        print(f"{'='*60}")
        print(f"⏱️  Duration: {duration_minutes:.1f} minutes")
        print(f"🏢 Companies Processed: {results['companies_processed']}")
        print(f"📊 Total Jobs Found: {results['total_jobs_found']}")
        print(f"✅ Valid Jobs: {results['valid_jobs']}")
        print(f"🎯 Companies with Jobs: {results['companies_with_jobs']}")
        print(f"❌ Total Errors: {results['total_errors']}")
        print(f"⚠️  Rate Limit Hits: {results['rate_limit_hits']}")
        
        if results['companies_processed'] > 0:
            success_rate = (results['companies_with_jobs'] / results['companies_processed']) * 100
            print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if results['total_jobs_found'] > 0:
            quality_rate = (results['valid_jobs'] / results['total_jobs_found']) * 100
            print(f"🏆 Quality Rate: {quality_rate:.1f}%")
        
        print(f"\n📋 TOP PERFORMING COMPANIES:")
        sorted_companies = sorted(
            results['jobs_by_company'].items(),
            key=lambda x: x[1]['valid'],
            reverse=True
        )
        
        for company, stats in sorted_companies[:5]:
            print(f"  {company}: {stats['valid']} valid jobs (quality: {stats['quality_score']:.1f})")
        
        print(f"{'='*60}\n")

async def main():
    """Main entry point"""
    orchestrator = EnhancedJobScrapingOrchestrator()
    
    # Parse command line arguments
    test_mode = '--test' in sys.argv
    priority_only = '--priority' in sys.argv
    
    if test_mode:
        logger.info("🧪 Running in TEST MODE - limited companies and faster execution")
        companies = orchestrator.priority_companies[:3]  # Only first 3 companies
        max_jobs = 2
    elif priority_only:
        logger.info("⭐ Running PRIORITY companies only")
        companies = orchestrator.priority_companies
        max_jobs = 3
    else:
        logger.info("🚀 Running FULL scraping operation")
        companies = orchestrator.all_companies
        max_jobs = 3
    
    try:
        results = await orchestrator.run_enhanced_scraping(
            companies=companies,
            max_jobs_per_company=max_jobs,
            test_mode=test_mode
        )
        
        logger.info("✅ Scraping session completed successfully")
        
        # Generate daily report if not in test mode
        if not test_mode:
            from monitoring_dashboard import generate_daily_report
            generate_daily_report()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Scraping interrupted by user")
    except Exception as e:
        logger.error(f"💥 Scraping failed with error: {str(e)}")
        raise

if __name__ == "__main__":
    print("""
🤖 Enhanced Job Scraping System
================================

Usage:
  python enhanced_main.py           # Full scraping (all companies)
  python enhanced_main.py --priority # Priority companies only
  python enhanced_main.py --test     # Test mode (3 companies, faster)

Features:
✅ Smart rate limiting with exponential backoff
✅ Company-specific navigation strategies  
✅ Data quality validation and scoring
✅ Real-time monitoring and alerts
✅ Comprehensive error handling
✅ Performance analytics and reporting

Starting in 3 seconds...
    """)
    
    import time
    time.sleep(3)
    
    asyncio.run(main())