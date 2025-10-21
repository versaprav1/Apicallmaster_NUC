"""
Monitoring and analytics dashboard for job scraping operations
"""

import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

@dataclass
class ScrapingMetrics:
    """Metrics for a scraping session"""
    timestamp: str
    company: str
    jobs_found: int
    jobs_valid: int
    avg_quality_score: float
    errors_count: int
    rate_limit_hits: int
    execution_time_seconds: float
    success_rate: float

class ScrapingMonitor:
    """Monitor and track scraping performance"""
    
    def __init__(self, db_path: str = "scraping_metrics.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraping_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                company TEXT NOT NULL,
                jobs_found INTEGER DEFAULT 0,
                jobs_valid INTEGER DEFAULT 0,
                avg_quality_score REAL DEFAULT 0.0,
                errors_count INTEGER DEFAULT 0,
                rate_limit_hits INTEGER DEFAULT 0,
                execution_time_seconds REAL DEFAULT 0.0,
                success_rate REAL DEFAULT 0.0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT,
                location TEXT,
                quality_score REAL DEFAULT 0.0,
                is_valid BOOLEAN DEFAULT 0,
                skills_count INTEGER DEFAULT 0,
                description_length INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_session_metrics(self, metrics: ScrapingMetrics):
        """Record metrics for a scraping session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scraping_metrics 
            (timestamp, company, jobs_found, jobs_valid, avg_quality_score, 
             errors_count, rate_limit_hits, execution_time_seconds, success_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.timestamp, metrics.company, metrics.jobs_found, metrics.jobs_valid,
            metrics.avg_quality_score, metrics.errors_count, metrics.rate_limit_hits,
            metrics.execution_time_seconds, metrics.success_rate
        ))
        
        conn.commit()
        conn.close()
    
    def record_job_data(self, job_data: Dict):
        """Record individual job data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO job_records 
            (timestamp, company, title, link, location, quality_score, 
             is_valid, skills_count, description_length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            job_data.get('company', ''),
            job_data.get('title', ''),
            job_data.get('link', ''),
            job_data.get('location', ''),
            job_data.get('validation_score', 0.0),
            job_data.get('is_valid', False),
            len(job_data.get('skills', '').split(',')) if job_data.get('skills') else 0,
            len(job_data.get('description', ''))
        ))
        
        conn.commit()
        conn.close()
    
    def get_performance_summary(self, days: int = 7) -> Dict:
        """Get performance summary for the last N days"""
        conn = sqlite3.connect(self.db_path)
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Overall metrics
        query = """
            SELECT 
                COUNT(*) as total_sessions,
                SUM(jobs_found) as total_jobs_found,
                SUM(jobs_valid) as total_jobs_valid,
                AVG(avg_quality_score) as avg_quality,
                SUM(errors_count) as total_errors,
                SUM(rate_limit_hits) as total_rate_limits,
                AVG(execution_time_seconds) as avg_execution_time,
                AVG(success_rate) as avg_success_rate
            FROM scraping_metrics 
            WHERE timestamp >= ?
        """
        
        overall_df = pd.read_sql_query(query, conn, params=[cutoff_date])
        
        # Company performance
        company_query = """
            SELECT 
                company,
                COUNT(*) as sessions,
                SUM(jobs_found) as jobs_found,
                SUM(jobs_valid) as jobs_valid,
                AVG(avg_quality_score) as avg_quality,
                SUM(rate_limit_hits) as rate_limit_hits,
                AVG(success_rate) as success_rate
            FROM scraping_metrics 
            WHERE timestamp >= ?
            GROUP BY company
            ORDER BY jobs_valid DESC
        """
        
        company_df = pd.read_sql_query(company_query, conn, params=[cutoff_date])
        
        conn.close()
        
        return {
            'overall': overall_df.to_dict('records')[0] if not overall_df.empty else {},
            'by_company': company_df.to_dict('records')
        }
    
    def generate_performance_report(self, days: int = 7) -> str:
        """Generate a comprehensive performance report"""
        summary = self.get_performance_summary(days)
        overall = summary['overall']
        by_company = summary['by_company']
        
        report = f"""
# Job Scraping Performance Report
## Period: Last {days} days
## Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Overall Performance
- **Total Sessions**: {overall.get('total_sessions', 0)}
- **Jobs Found**: {overall.get('total_jobs_found', 0)}
- **Valid Jobs**: {overall.get('total_jobs_valid', 0)}
- **Average Quality Score**: {overall.get('avg_quality', 0):.1f}/100
- **Success Rate**: {overall.get('avg_success_rate', 0):.1f}%
- **Total Errors**: {overall.get('total_errors', 0)}
- **Rate Limit Hits**: {overall.get('total_rate_limits', 0)}
- **Average Execution Time**: {overall.get('avg_execution_time', 0):.1f} seconds

### Company Performance
"""
        
        for company in by_company:
            report += f"""
#### {company['company']}
- Sessions: {company['sessions']}
- Jobs Found: {company['jobs_found']} (Valid: {company['jobs_valid']})
- Quality Score: {company['avg_quality']:.1f}/100
- Success Rate: {company['success_rate']:.1f}%
- Rate Limits: {company['rate_limit_hits']}
"""
        
        return report
    
    def create_visualizations(self, output_dir: str = "reports"):
        """Create performance visualization charts"""
        Path(output_dir).mkdir(exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        
        # Set style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # 1. Jobs found by company
        company_jobs_df = pd.read_sql_query("""
            SELECT company, SUM(jobs_found) as total_jobs, SUM(jobs_valid) as valid_jobs
            FROM scraping_metrics 
            WHERE timestamp >= date('now', '-7 days')
            GROUP BY company
            ORDER BY total_jobs DESC
        """, conn)
        
        if not company_jobs_df.empty:
            fig, ax = plt.subplots(figsize=(12, 6))
            x = range(len(company_jobs_df))
            width = 0.35
            
            ax.bar([i - width/2 for i in x], company_jobs_df['total_jobs'], 
                   width, label='Total Jobs', alpha=0.8)
            ax.bar([i + width/2 for i in x], company_jobs_df['valid_jobs'], 
                   width, label='Valid Jobs', alpha=0.8)
            
            ax.set_xlabel('Company')
            ax.set_ylabel('Number of Jobs')
            ax.set_title('Jobs Found by Company (Last 7 Days)')
            ax.set_xticks(x)
            ax.set_xticklabels(company_jobs_df['company'], rotation=45, ha='right')
            ax.legend()
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/jobs_by_company.png", dpi=300, bbox_inches='tight')
            plt.close()
        
        # 2. Quality scores over time
        quality_df = pd.read_sql_query("""
            SELECT DATE(timestamp) as date, AVG(avg_quality_score) as avg_quality
            FROM scraping_metrics 
            WHERE timestamp >= date('now', '-30 days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, conn)
        
        if not quality_df.empty:
            fig, ax = plt.subplots(figsize=(12, 6))
            quality_df['date'] = pd.to_datetime(quality_df['date'])
            ax.plot(quality_df['date'], quality_df['avg_quality'], marker='o', linewidth=2)
            ax.set_xlabel('Date')
            ax.set_ylabel('Average Quality Score')
            ax.set_title('Data Quality Trend (Last 30 Days)')
            ax.grid(True, alpha=0.3)
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(f"{output_dir}/quality_trend.png", dpi=300, bbox_inches='tight')
            plt.close()
        
        # 3. Error analysis
        error_df = pd.read_sql_query("""
            SELECT company, SUM(errors_count) as total_errors, SUM(rate_limit_hits) as rate_limits
            FROM scraping_metrics 
            WHERE timestamp >= date('now', '-7 days')
            GROUP BY company
            HAVING total_errors > 0 OR rate_limits > 0
            ORDER BY total_errors DESC
        """, conn)
        
        if not error_df.empty:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Errors
            ax1.bar(error_df['company'], error_df['total_errors'], alpha=0.8, color='red')
            ax1.set_xlabel('Company')
            ax1.set_ylabel('Total Errors')
            ax1.set_title('Errors by Company')
            ax1.tick_params(axis='x', rotation=45)
            
            # Rate limits
            ax2.bar(error_df['company'], error_df['rate_limits'], alpha=0.8, color='orange')
            ax2.set_xlabel('Company')
            ax2.set_ylabel('Rate Limit Hits')
            ax2.set_title('Rate Limits by Company')
            ax2.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/error_analysis.png", dpi=300, bbox_inches='tight')
            plt.close()
        
        conn.close()
        print(f"Visualizations saved to {output_dir}/")

class AlertSystem:
    """Alert system for monitoring scraping operations"""
    
    def __init__(self, monitor: ScrapingMonitor):
        self.monitor = monitor
        self.thresholds = {
            'min_success_rate': 70.0,
            'max_error_rate': 20.0,
            'min_quality_score': 60.0,
            'max_rate_limit_hits': 5
        }
    
    def check_alerts(self) -> List[str]:
        """Check for alert conditions"""
        alerts = []
        summary = self.monitor.get_performance_summary(days=1)  # Last 24 hours
        overall = summary['overall']
        
        if overall.get('avg_success_rate', 0) < self.thresholds['min_success_rate']:
            alerts.append(f"⚠️ Low success rate: {overall.get('avg_success_rate', 0):.1f}% (threshold: {self.thresholds['min_success_rate']}%)")
        
        if overall.get('avg_quality', 0) < self.thresholds['min_quality_score']:
            alerts.append(f"⚠️ Low quality score: {overall.get('avg_quality', 0):.1f} (threshold: {self.thresholds['min_quality_score']})")
        
        if overall.get('total_rate_limits', 0) > self.thresholds['max_rate_limit_hits']:
            alerts.append(f"⚠️ High rate limit hits: {overall.get('total_rate_limits', 0)} (threshold: {self.thresholds['max_rate_limit_hits']})")
        
        # Company-specific alerts
        for company in summary['by_company']:
            if company['success_rate'] < 50:
                alerts.append(f"🚨 {company['company']}: Very low success rate ({company['success_rate']:.1f}%)")
            
            if company['rate_limit_hits'] > 3:
                alerts.append(f"⚠️ {company['company']}: High rate limit hits ({company['rate_limit_hits']})")
        
        return alerts

# Usage example
def setup_monitoring():
    """Set up monitoring for job scraping"""
    monitor = ScrapingMonitor()
    alert_system = AlertSystem(monitor)
    
    return monitor, alert_system

def generate_daily_report():
    """Generate and save daily performance report"""
    monitor = ScrapingMonitor()
    
    # Generate text report
    report = monitor.generate_performance_report(days=1)
    
    # Save report
    report_path = f"reports/daily_report_{datetime.now().strftime('%Y%m%d')}.md"
    Path("reports").mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    # Generate visualizations
    monitor.create_visualizations()
    
    # Check for alerts
    alert_system = AlertSystem(monitor)
    alerts = alert_system.check_alerts()
    
    if alerts:
        print("🚨 ALERTS DETECTED:")
        for alert in alerts:
            print(f"  {alert}")
    else:
        print("✅ No alerts - system performing normally")
    
    print(f"📊 Daily report saved to {report_path}")

if __name__ == "__main__":
    generate_daily_report()