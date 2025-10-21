"""
Performance Monitoring - New feature not in original 2.py
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict
from pathlib import Path

class ScrapingMonitor:
    """Monitor scraping performance and generate reports"""
    
    def __init__(self, db_path: str = "logs/scraping_metrics.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                company TEXT NOT NULL,
                jobs_found INTEGER DEFAULT 0,
                valid_jobs INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0,
                rate_limit_hits INTEGER DEFAULT 0,
                quality_score REAL DEFAULT 0.0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_company_session(self, company: str, result: Dict):
        """Record company scraping session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        avg_quality = 0
        if result.get('jobs'):
            scores = [job.get('quality_score', 0) for job in result['jobs']]
            avg_quality = sum(scores) / len(scores) if scores else 0
        
        cursor.execute("""
            INSERT INTO company_sessions 
            (timestamp, company, jobs_found, valid_jobs, errors, rate_limit_hits, quality_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            company,
            result.get('jobs_found', 0),
            result.get('valid_jobs', 0),
            result.get('errors', 0),
            result.get('rate_limit_hits', 0),
            avg_quality
        ))
        
        conn.commit()
        conn.close()

def generate_performance_report():
    """Generate performance report"""
    monitor = ScrapingMonitor()
    conn = sqlite3.connect(monitor.db_path)
    
    # Get recent performance data
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            company,
            SUM(jobs_found) as total_jobs,
            SUM(valid_jobs) as total_valid,
            AVG(quality_score) as avg_quality,
            SUM(errors) as total_errors
        FROM company_sessions 
        WHERE timestamp >= date('now', '-7 days')
        GROUP BY company
        ORDER BY total_valid DESC
    """)
    
    results = cursor.fetchall()
    conn.close()
    
    # Generate report
    report_path = f"reports/performance_report_{datetime.now().strftime('%Y%m%d')}.txt"
    
    with open(report_path, 'w') as f:
        f.write("Enhanced Job Scraper Performance Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("Company Performance (Last 7 Days):\n")
        f.write("-" * 40 + "\n")
        
        for company, total_jobs, valid_jobs, avg_quality, errors in results:
            f.write(f"{company}:\n")
            f.write(f"  Jobs Found: {total_jobs}\n")
            f.write(f"  Valid Jobs: {valid_jobs}\n")
            f.write(f"  Quality Score: {avg_quality:.1f}/100\n")
            f.write(f"  Errors: {errors}\n\n")
    
    print(f"📊 Performance report saved to {report_path}")