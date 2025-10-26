"""
Local Executor Module

Provides local execution capabilities for queries without API calls.
"""

from .adapters import to_api_response
from .executor import execute_query
from .loader import iter_records
from .router import select_collection

__all__ = [
    'to_api_response',
    'execute_query',
    'iter_records',
    'select_collection'
]


