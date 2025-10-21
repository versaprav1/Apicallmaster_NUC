"""
Module: auth_manager

Purpose:
    Manage authentication for the WHINT Integration Cockpit API. Centralizes
    bearer token and API key handling, header construction, lightweight
    credential validation, and diagnostics.

Key Concepts:
    - Header construction for authenticated HTTP requests
    - Cached credential validation to minimize network calls
    - Simple diagnostics for missing/expired credentials

Public API:
    - `AuthManager`: Encapsulates credential storage, header creation, and
      validation helpers.
    - `create_from_environment` / `create_from_secrets`: Helpers to build an
      instance from environment variables or app secrets.

Inputs/Outputs:
    - Inputs: `WHINT_API_X_API_KEY`, `WHINT_API_BEARER_TOKEN`, and optional
      `WHINT_API_BASE_URL` env vars.
    - Outputs: HTTP headers for requests; validation status and diagnostics.

Dependencies:
    - External: `requests` for a minimal validation call; `os`, `time`.

Usage:
    >>> mgr = AuthManager.create_from_environment()
    >>> headers = mgr.get_headers()
    >>> is_valid = mgr.validate_credentials()
"""

import os
import time
from typing import Dict, Optional
import requests

class AuthManager:
    """Manages authentication for WHINT Integration Cockpit API"""
    
    def __init__(self, api_key: str, bearer_token: str):
        self.api_key = api_key
        self.bearer_token = bearer_token
        self.last_validation = None
        self.validation_cache_duration = 3600  # 1 hour
    
    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def validate_credentials(self, force_check: bool = False) -> bool:
        """Validate API credentials"""
        # Use cached validation if recent
        if not force_check and self.last_validation:
            if time.time() - self.last_validation < self.validation_cache_duration:
                return True
        
        try:
            # Make a minimal test request
            test_url = os.getenv("WHINT_API_BASE_URL", "https://whint.prod.apimanagement.eu10.hana.ondemand.com:443/api")
            test_data = {
                "query": {
                    "entity": "inventory",
                    "fields": ["id"],
                    "limit": 1
                }
            }
            
            response = requests.post(
                test_url,
                headers=self.get_headers(),
                json=test_data,
                timeout=10
            )
            
            is_valid = response.status_code == 200
            if is_valid:
                self.last_validation = time.time()
            
            return is_valid
            
        except Exception as e:
            print(f"Credential validation failed: {str(e)}")
            return False
    
    def get_token_info(self) -> Dict[str, str]:
        """Get information about the current tokens (masked for security)"""
        return {
            "api_key_preview": f"{self.api_key[:8]}..." if len(self.api_key) > 8 else "***",
            "bearer_token_preview": f"{self.bearer_token[:12]}..." if len(self.bearer_token) > 12 else "***",
            "last_validation": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_validation)) if self.last_validation else "Never"
        }
    
    def refresh_validation_cache(self):
        """Force refresh of validation cache"""
        self.last_validation = None
        return self.validate_credentials(force_check=True)
    
    def is_token_expired(self) -> bool:
        """Check if tokens might be expired based on validation history"""
        if not self.last_validation:
            return True
        
        # Consider tokens potentially expired if last validation was over 24 hours ago
        return time.time() - self.last_validation > 86400
    
    @staticmethod
    def create_from_environment() -> Optional['AuthManager']:
        """Create AuthManager from environment variables"""
        api_key = os.getenv("WHINT_API_X_API_KEY")
        bearer_token = os.getenv("WHINT_API_BEARER_TOKEN")
        
        if not api_key or not bearer_token:
            return None
        
        return AuthManager(api_key, bearer_token)
    
    @staticmethod
    def create_from_secrets(secrets: dict) -> Optional['AuthManager']:
        """Create AuthManager from Streamlit secrets"""
        api_key = secrets.get("whint_api_x_api_key")
        bearer_token = secrets.get("whint_api_bearer_token")
        
        if not api_key or not bearer_token:
            return None
        
        return AuthManager(api_key, bearer_token)
    
    def update_credentials(self, api_key: str = None, bearer_token: str = None):
        """Update credentials and clear validation cache"""
        if api_key:
            self.api_key = api_key
        if bearer_token:
            self.bearer_token = bearer_token
        
        # Clear validation cache when credentials change
        self.last_validation = None
    
    def get_auth_status(self) -> Dict[str, any]:
        """Get comprehensive authentication status"""
        return {
            "has_api_key": bool(self.api_key),
            "has_bearer_token": bool(self.bearer_token), 
            "last_validation": self.last_validation,
            "is_validated": bool(self.last_validation),
            "might_be_expired": self.is_token_expired(),
            "validation_age_hours": (time.time() - self.last_validation) / 3600 if self.last_validation else None
        }
    
    def diagnose_auth_issues(self) -> list:
        """Diagnose potential authentication issues"""
        issues = []
        
        if not self.api_key:
            issues.append("Missing API key")
        elif len(self.api_key) < 10:
            issues.append("API key appears to be too short")
        
        if not self.bearer_token:
            issues.append("Missing Bearer token")
        elif len(self.bearer_token) < 20:
            issues.append("Bearer token appears to be too short")
        
        if self.is_token_expired():
            issues.append("Tokens may have expired (last validation over 24 hours ago)")
        
        if not self.last_validation:
            issues.append("Credentials have never been validated")
        
        return issues
    
    def __str__(self) -> str:
        """String representation for debugging"""
        return f"AuthManager(api_key={'set' if self.api_key else 'not set'}, bearer_token={'set' if self.bearer_token else 'not set'})"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return f"AuthManager(api_key_length={len(self.api_key) if self.api_key else 0}, bearer_token_length={len(self.bearer_token) if self.bearer_token else 0}, last_validation={self.last_validation})"
