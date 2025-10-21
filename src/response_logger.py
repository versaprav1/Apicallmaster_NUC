"""
Response Logger for ApiCallMaster

Logs ALL responses (successful and failed) with comprehensive metadata including:
- Question, answer, model used, method used
- Routing information, intent analysis
- Error details for failed responses
- Timestamps, execution time, token counts
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import traceback


@dataclass
class ResponseLog:
    """Structured response log entry"""
    # Core fields
    log_id: str
    timestamp: str
    question: str
    answer: str
    status: str  # 'success', 'error', 'partial'
    
    # Method and routing
    method_used: str  # 'graph_rag', 'vector_rag', 'api', 'db_lookup', etc.
    model_used: Optional[str] = None
    data_source: Optional[str] = None  # 'duckdb', 'api', 'local_json'
    
    # Intent and routing
    intent: Optional[str] = None
    requires_graph: bool = False
    query_type: Optional[str] = None
    graph_seeds: Optional[List[str]] = None
    
    # Query details
    api_query: Optional[Dict[str, Any]] = None
    endpoint: Optional[str] = None
    sql_query: Optional[str] = None
    
    # Response details
    response_data: Optional[Dict[str, Any]] = None
    total_items: int = 0
    execution_time_ms: Optional[float] = None
    
    # Error details (for failed responses)
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    error_traceback: Optional[str] = None
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None


class ResponseLogger:
    """Logs all responses with comprehensive metadata"""
    
    def __init__(self, log_dir: str = "response_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different log types
        (self.log_dir / "success").mkdir(exist_ok=True)
        (self.log_dir / "error").mkdir(exist_ok=True)
        (self.log_dir / "daily").mkdir(exist_ok=True)
        
        # Initialize daily log file
        self.daily_log_file = self._get_daily_log_file()
        
        # In-memory cache for recent logs
        self.recent_logs: List[ResponseLog] = []
        self.max_recent = 100
    
    def _get_daily_log_file(self) -> Path:
        """Get today's log file path"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / "daily" / f"responses_{today}.jsonl"
    
    def _generate_log_id(self, question: str, timestamp: str) -> str:
        """Generate unique log ID"""
        content = f"{question}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def log_response(
        self,
        question: str,
        answer: str,
        status: str,
        method_used: str,
        model_used: Optional[str] = None,
        data_source: Optional[str] = None,
        intent: Optional[str] = None,
        requires_graph: bool = False,
        query_type: Optional[str] = None,
        graph_seeds: Optional[List[str]] = None,
        api_query: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None,
        sql_query: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        error_traceback: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a response with full metadata
        
        Returns:
            log_id: Unique identifier for this log entry
        """
        try:
            timestamp = datetime.now().isoformat()
            log_id = self._generate_log_id(question, timestamp)
            
            # Calculate total items if response data provided
            total_items = 0
            if response_data and isinstance(response_data, dict):
                if 'data' in response_data:
                    total_items = len(response_data['data'])
                elif 'results' in response_data:
                    total_items = len(response_data['results'])
            
            # Create log entry
            log_entry = ResponseLog(
                log_id=log_id,
                timestamp=timestamp,
                question=question,
                answer=answer,
                status=status,
                method_used=method_used,
                model_used=model_used,
                data_source=data_source,
                intent=intent,
                requires_graph=requires_graph,
                query_type=query_type,
                graph_seeds=graph_seeds,
                api_query=api_query,
                endpoint=endpoint,
                sql_query=sql_query,
                response_data=response_data,
                total_items=total_items,
                execution_time_ms=execution_time_ms,
                error_message=error_message,
                error_type=error_type,
                error_traceback=error_traceback,
                metadata=metadata
            )
            
            # Add to recent logs cache
            self.recent_logs.insert(0, log_entry)
            if len(self.recent_logs) > self.max_recent:
                self.recent_logs.pop()
            
            # Write to daily log file
            self._write_to_daily_log(log_entry)
            
            # Write to status-specific file
            self._write_to_status_log(log_entry)
            
            return log_id
            
        except Exception as e:
            print(f"Warning: Could not log response: {e}")
            traceback.print_exc()
            return ""
    
    def _write_to_daily_log(self, log_entry: ResponseLog):
        """Append log entry to daily log file"""
        try:
            with open(self.daily_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(log_entry), default=str) + '\n')
        except Exception as e:
            print(f"Warning: Could not write to daily log: {e}")
    
    def _write_to_status_log(self, log_entry: ResponseLog):
        """Write log entry to status-specific file"""
        try:
            status_dir = self.log_dir / log_entry.status
            status_file = status_dir / f"{log_entry.log_id}.json"
            
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(log_entry), f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not write to status log: {e}")
    
    def get_recent_logs(self, limit: int = 20, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent log entries"""
        logs = self.recent_logs
        
        if status:
            logs = [log for log in logs if log.status == status]
        
        return [asdict(log) for log in logs[:limit]]
    
    def get_logs_by_method(self, method: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get logs for a specific method"""
        logs = [log for log in self.recent_logs if log.method_used == method]
        return [asdict(log) for log in logs[:limit]]
    
    def get_error_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent error logs"""
        return self.get_recent_logs(limit=limit, status='error')
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about logged responses"""
        try:
            total_success = sum(1 for log in self.recent_logs if log.status == 'success')
            total_error = sum(1 for log in self.recent_logs if log.status == 'error')
            total_partial = sum(1 for log in self.recent_logs if log.status == 'partial')
            
            # Method usage
            method_counts = {}
            for log in self.recent_logs:
                method_counts[log.method_used] = method_counts.get(log.method_used, 0) + 1
            
            # Model usage
            model_counts = {}
            for log in self.recent_logs:
                if log.model_used:
                    model_counts[log.model_used] = model_counts.get(log.model_used, 0) + 1
            
            # Average execution time
            exec_times = [log.execution_time_ms for log in self.recent_logs if log.execution_time_ms]
            avg_exec_time = sum(exec_times) / len(exec_times) if exec_times else 0
            
            return {
                "total_logs": len(self.recent_logs),
                "success_count": total_success,
                "error_count": total_error,
                "partial_count": total_partial,
                "success_rate": total_success / len(self.recent_logs) if self.recent_logs else 0,
                "method_usage": method_counts,
                "model_usage": model_counts,
                "avg_execution_time_ms": avg_exec_time,
                "log_directory": str(self.log_dir)
            }
            
        except Exception as e:
            print(f"Warning: Could not get statistics: {e}")
            return {"error": str(e)}
    
    def search_logs(
        self,
        query: Optional[str] = None,
        method: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search logs with filters"""
        logs = self.recent_logs
        
        # Filter by query text
        if query:
            query_lower = query.lower()
            logs = [log for log in logs if query_lower in log.question.lower() or query_lower in log.answer.lower()]
        
        # Filter by method
        if method:
            logs = [log for log in logs if log.method_used == method]
        
        # Filter by status
        if status:
            logs = [log for log in logs if log.status == status]
        
        # Filter by date range
        if date_from:
            logs = [log for log in logs if log.timestamp >= date_from]
        if date_to:
            logs = [log for log in logs if log.timestamp <= date_to]
        
        return [asdict(log) for log in logs[:limit]]
    
    def export_logs(self, output_file: str, date: Optional[str] = None):
        """Export logs to a file"""
        try:
            if date:
                # Export specific date
                log_file = self.log_dir / "daily" / f"responses_{date}.jsonl"
            else:
                # Export all recent logs
                log_file = output_file
                with open(log_file, 'w', encoding='utf-8') as f:
                    for log in self.recent_logs:
                        f.write(json.dumps(asdict(log), default=str) + '\n')
                return
            
            # Copy daily log file
            if log_file.exists():
                import shutil
                shutil.copy(log_file, output_file)
                print(f"Exported logs to {output_file}")
            else:
                print(f"No logs found for date {date}")
                
        except Exception as e:
            print(f"Warning: Could not export logs: {e}")

