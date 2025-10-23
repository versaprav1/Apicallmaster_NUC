"""
Result Saver: Save all question-answer pairs for future reference
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

class ResultSaver:
    def __init__(self, save_dir: str = "saved_results"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)
        self.results_file = self.save_dir / "all_results.json"
        self.load_existing_results()
    
    def load_existing_results(self):
        """Load existing results from file"""
        if self.results_file.exists():
            try:
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    self.results = json.load(f)
            except Exception:
                self.results = []
        else:
            self.results = []
    
    def save_result(self, question: str, answer: str, method: str, model: str, 
                   data_source: str, metadata: Dict[str, Any] = None):
        """Save a question-answer pair with metadata"""
        result_entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer,
            "method": method,
            "model": model,
            "data_source": data_source,
            "metadata": metadata or {},
            "id": len(self.results) + 1
        }
        
        self.results.append(result_entry)
        self.save_to_file()
        return result_entry["id"]
    
    def save_to_file(self):
        """Save results to JSON file"""
        try:
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving results: {e}")
    
    def get_all_results(self) -> List[Dict[str, Any]]:
        """Get all saved results"""
        return self.results
    
    def get_results_by_method(self, method: str) -> List[Dict[str, Any]]:
        """Get results filtered by method"""
        return [r for r in self.results if r.get("method") == method]
    
    def get_results_by_data_source(self, data_source: str) -> List[Dict[str, Any]]:
        """Get results filtered by data source"""
        return [r for r in self.results if r.get("data_source") == data_source]
    
    def get_results_by_model(self, model: str) -> List[Dict[str, Any]]:
        """Get results filtered by model"""
        return [r for r in self.results if r.get("model") == model]
    
    def search_results(self, query: str) -> List[Dict[str, Any]]:
        """Search results by question content"""
        query_lower = query.lower()
        return [r for r in self.results if query_lower in r.get("question", "").lower()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about saved results"""
        if not self.results:
            return {"total": 0}
        
        methods = {}
        data_sources = {}
        models = {}
        
        for result in self.results:
            method = result.get("method", "unknown")
            data_source = result.get("data_source", "unknown")
            model = result.get("model", "unknown")
            
            methods[method] = methods.get(method, 0) + 1
            data_sources[data_source] = data_sources.get(data_source, 0) + 1
            models[model] = models.get(model, 0) + 1
        
        return {
            "total": len(self.results),
            "methods": methods,
            "data_sources": data_sources,
            "models": models,
            "latest": self.results[-1] if self.results else None
        }
    
    def export_results(self, export_file: str = None) -> str:
        """Export results to a specific file"""
        if not export_file:
            export_file = self.save_dir / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            return str(export_file)
        except Exception as e:
            print(f"Error exporting results: {e}")
            return None

