"""
Enhanced Job Scraper - Main Entry Point
Replaces your original 2.py script with significant improvements
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from core.scraper import EnhancedJobScraper
from core.monitoring import ScrapingMonitor, generate_performance_report
from config.settings import load_config, COMPANIES
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Main function - replaces your original 2.py logic"""
    
    # Ensure directories exist
    Path("outputs").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)
    
    # Parse command line arguments
    test_mode = '--test' in sys.argv
    priority_only = '--priority' in sys.argv
    
    # Load configuration
    config = load_config()
    
    # Select companies based on mode
    if test_mode:
        companies = COMPANIES['priority'][:3]  # First 3 for testing
        max_jobs = 2
        logger.info("🧪 Running in TEST MODE")
    elif priority_only:
        companies = COMPANIES['priority']
        max_jobs = 3
        logger.info("⭐ Running PRIORITY companies")
    else:
        companies = COMPANIES['all']
        max_jobs = 3
        logger.info("🚀 Running FULL scraping")
    
    logger.info(f"📊 Processing {len(companies)} companies, max {max_jobs} jobs each")
    
    # Initialize enhanced scraper (uses browser-use internally)
    scraper = EnhancedJobScraper(config)
    monitor = ScrapingMonitor()
    
    # Track session statistics
    session_stats = {
        'companies_processed': 0,
        'total_jobs_found': 0,
        'valid_jobs_saved': 0,
        'errors_encountered': 0,
        'rate_limit_hits': 0
    }
    
    try:
        logger.info("🤖 Starting enhanced job scraping with browser-use...")
        
        for i, company in enumerate(companies, 1):
            logger.info(f"📍 [{i}/{len(companies)}] Processing {company}")
            
            try:
                # This uses browser-use Agent internally with enhanced configuration
                result = await scraper.scrape_company_jobs(company, max_jobs)
                
                # Update statistics
                session_stats['companies_processed'] += 1
                session_stats['total_jobs_found'] += result['jobs_found']
                session_stats['valid_jobs_saved'] += result['valid_jobs']
                session_stats['errors_encountered'] += result['errors']
                session_stats['rate_limit_hits'] += result['rate_limit_hits']
                
                # Log results
                if result['valid_jobs'] > 0:
                    logger.info(f"✅ {company}: {result['valid_jobs']} valid jobs found")
                else:
                    logger.warning(f"❌ {company}: No valid jobs found")
                
                # Record metrics for monitoring
                monitor.record_company_session(company, result)
                
                # Wait between companies (smart rate limiting)
                if i < len(companies):
                    wait_time = 30 if test_mode else 60
                    logger.info(f"⏳ Waiting {wait_time}s before next company...")
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"💥 Error processing {company}: {str(e)}")
                session_stats['errors_encountered'] += 1
                continue
        
        # Print final statistics (similar to your original 2.py output)
        print_session_summary(session_stats)
        
        # Generate performance report
        if not test_mode:
            generate_performance_report()
            logger.info("📊 Performance report generated in reports/")
        
        logger.info("✅ Enhanced job scraping completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("⏹️ Scraping interrupted by user")
    except Exception as e:
        logger.error(f"💥 Critical error: {str(e)}")
        raise

def print_session_summary(stats):
    """Print session summary similar to your original 2.py format"""
    print(f"\n{'='*60}")
    print(f"📊 ENHANCED JOB SCRAPING SESSION COMPLETE")
    print(f"{'='*60}")
    print(f"🏢 Companies Processed: {stats['companies_processed']}")
    print(f"📋 Total Jobs Found: {stats['total_jobs_found']}")
    print(f"✅ Valid Jobs Saved: {stats['valid_jobs_saved']}")
    print(f"❌ Errors Encountered: {stats['errors_encountered']}")
    print(f"⚠️  Rate Limit Hits: {stats['rate_limit_hits']}")
    
    if stats['companies_processed'] > 0:
        success_rate = (stats['valid_jobs_saved'] / max(1, stats['total_jobs_found'])) * 100
        print(f"📈 Success Rate: {success_rate:.1f}%")
    
    print(f"💾 Results saved to: outputs/enhanced_job_findings.csv")
    print(f"📝 Logs saved to: logs/scraper.log")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    print("""
🤖 Enhanced Job Scraper (Browser-Use Powered)
==============================================
Replaces your original 2.py with improvements:

✅ Smart rate limiting with exponential backoff
✅ Company-specific navigation strategies  
✅ Data quality validation (100-point scoring)
✅ Real-time monitoring and performance tracking
✅ Enhanced error handling and recovery
✅ Same browser-use integration as original

Usage:
  python main.py           # Full scraping (all companies)
  python main.py --priority # Priority companies only  
  python main.py --test     # Test mode (3 companies)

Starting in 3 seconds...
    """)
    
    import time
    time.sleep(3)
    
    asyncio.run(main())