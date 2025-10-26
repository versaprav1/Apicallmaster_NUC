"""
Browser Automation Method for ApiCallMaster

@file purpose: Core browser automation engine using browser-use library

What this file does:
- Provides browser automation capabilities for WHINT dashboard interaction
- Supports multiple LLM providers (OpenAI, Google, Anthropic, Groq, Ollama)
- Handles auto-login to WHINT with Microsoft credentials
- Supports both interactive Q&A and batch processing
- Includes fallback mechanism for model failures

How it fits into the system:
- Used by src/browser_automation_page.py (dedicated UI)
- Used by src/method_router.py (chat integration)
- Integrates with src/llm_providers.py for model management
"""

import asyncio
import os
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import traceback
from pathlib import Path


class BrowserAutomationEngine:
    """
    Core browser automation engine with multi-provider LLM support.
    
    Supports:
    - OpenAI (gpt-4o, gpt-4o-mini, gpt-4.1-mini)
    - Google (gemini-2.0-flash-exp, gemini-2.5-pro)
    - Anthropic (claude-3-5-sonnet-20241022)
    - Groq (llama-3.3-70b-versatile, llama-3.1-8b-instant)
    - Ollama (any local model: mistral-nemo, llama3.1, qwen2.5, etc.)
    """
    
    def __init__(
        self,
        primary_model: str = "gemini-2.0-flash-exp",
        fallback_model: Optional[str] = "gpt-4o-mini",
        headless: bool = False,
        whint_url: str = "https://whintic-test.cfapps.eu10.hana.ondemand.com/",
        auto_login: bool = True,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ollama_base_url: str = "http://localhost:11434"
    ):
        """
        Initialize browser automation engine.
        
        Args:
            primary_model: Primary LLM model to use
            fallback_model: Fallback LLM if primary fails
            headless: Run browser in headless mode (False = visible)
            whint_url: WHINT dashboard URL
            auto_login: Auto-login on browser start
            username: Microsoft login username
            password: Microsoft login password
            ollama_base_url: Ollama API base URL
        """
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.headless = headless
        self.whint_url = whint_url
        self.auto_login = auto_login
        self.username = username
        self.password = password
        self.ollama_base_url = ollama_base_url
        
        self.browser_session = None
        self.current_llm = None
        self.is_logged_in = False
        self.session_start_time = None
        
    def _get_llm_instance(self, model_name: str):
        """
        Get LLM instance for browser-use based on model name.
        
        Automatically detects provider from model name and returns
        appropriate browser-use LLM instance.
        """
        try:
            # OpenAI models
            if any(name in model_name.lower() for name in ["gpt", "o1", "chatgpt"]):
                from browser_use.llm import ChatOpenAI
                return ChatOpenAI(model=model_name)
            
            # Google Gemini models
            elif "gemini" in model_name.lower():
                from browser_use.llm import ChatGoogle
                return ChatGoogle(model=model_name)
            
            # Anthropic Claude models
            elif "claude" in model_name.lower():
                from browser_use.llm import ChatAnthropic
                return ChatAnthropic(model=model_name)
            
            # Groq models
            elif any(name in model_name.lower() for name in ["llama", "mixtral", "groq"]):
                from browser_use.llm import ChatGroq
                return ChatGroq(model=model_name)
            
            # Ollama models (local)
            else:
                # Assume it's an Ollama model
                from browser_use.llm import ChatOllama
                return ChatOllama(
                    model=model_name,
                    base_url=self.ollama_base_url
                )
        
        except Exception as e:
            raise Exception(f"Failed to initialize {model_name}: {str(e)}")
    
    def _get_llm_with_fallback(self) -> Any:
        """Get LLM with fallback support."""
        try:
            # Try primary model first
            llm = self._get_llm_instance(self.primary_model)
            print(f"✅ Using primary model: {self.primary_model}")
            return llm
        
        except Exception as e:
            print(f"⚠️ Primary model {self.primary_model} failed: {str(e)}")
            
            if self.fallback_model:
                try:
                    llm = self._get_llm_instance(self.fallback_model)
                    print(f"✅ Using fallback model: {self.fallback_model}")
                    return llm
                except Exception as fallback_error:
                    raise Exception(
                        f"Both primary ({self.primary_model}) and fallback ({self.fallback_model}) models failed. "
                        f"Primary error: {str(e)}, Fallback error: {str(fallback_error)}"
                    )
            else:
                raise Exception(f"Primary model failed and no fallback configured: {str(e)}")
    
    async def initialize_browser(self) -> Dict[str, Any]:
        """
        Initialize browser session and optionally perform auto-login.
        
        Returns:
            Dict with status, login_success, and browser info
        """
        try:
            from browser_use import Agent
            from browser_use.browser import BrowserSession, BrowserProfile
            
            self.session_start_time = datetime.now()
            
            # Get LLM with fallback
            self.current_llm = self._get_llm_with_fallback()
            
            # Create browser profile (non-headless for testing)
            browser_profile = BrowserProfile(
                headless=self.headless,
                disable_security=False,
                extra_chromium_args=[
                    '--start-maximized',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            # Create browser session
            self.browser_session = BrowserSession(browser_profile=browser_profile)
            
            result = {
                "status": "initialized",
                "model": self.primary_model,
                "headless": self.headless,
                "session_start": self.session_start_time.isoformat(),
                "login_success": False
            }
            
            # Auto-login if enabled
            if self.auto_login and self.username and self.password:
                login_result = await self._perform_login()
                result["login_success"] = login_result["success"]
                result["login_message"] = login_result.get("message", "")
            
            return result
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    async def _perform_login(self) -> Dict[str, Any]:
        """
        Perform auto-login to WHINT with Microsoft credentials.
        
        Returns:
            Dict with success status and message
        """
        try:
            from browser_use import Agent
            
            # Define login task
            login_task = f"""
            Navigate to {self.whint_url} and log in with Microsoft credentials.
            
            Steps:
            1. Go to {self.whint_url}
            2. Wait for the page to load (may show login options)
            3. Look for and click "Login with Microsoft" or "Microsoft" button
            4. On the Microsoft login page:
               - Enter username in the email/username field
               - Click Next
               - Enter password in the password field
               - Click Sign in
            5. If asked "Stay signed in?", click Yes
            6. Wait for redirect back to WHINT dashboard
            7. Confirm successful login by checking if dashboard is visible
            
            Return: "Login successful" if you reach the dashboard, otherwise describe what you see.
            """
            
            # Sensitive data for login (masked from LLM)
            sensitive_data = {
                f"{self.whint_url}": {
                    'microsoft_username': self.username,
                    'microsoft_password': self.password
                },
                "https://login.microsoftonline.com": {
                    'microsoft_username': self.username,
                    'microsoft_password': self.password
                },
                "https://*.microsoft.com": {
                    'microsoft_username': self.username,
                    'microsoft_password': self.password
                }
            }
            
            # Create agent for login
            agent = Agent(
                task=login_task,
                llm=self.current_llm,
                browser_session=self.browser_session,
                sensitive_data=sensitive_data
            )
            
            # Execute login
            result = await agent.run()
            
            self.is_logged_in = True
            
            return {
                "success": True,
                "message": "Login successful",
                "result": str(result)
            }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"Login failed: {str(e)}",
                "error": traceback.format_exc()
            }
    
    async def execute_task(
        self,
        task: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a browser automation task (interactive mode).
        
        Args:
            task: Task description from user
            context: Optional context about WHINT dashboard
        
        Returns:
            Dict with result, extracted_data, and metadata
        """
        try:
            from browser_use import Agent
            
            # Ensure browser is initialized
            if not self.browser_session:
                init_result = await self.initialize_browser()
                if init_result["status"] == "error":
                    return init_result
            
            # Build enhanced task with context
            enhanced_task = self._build_task_with_context(task, context)
            
            # Create agent
            agent = Agent(
                task=enhanced_task,
                llm=self.current_llm,
                browser_session=self.browser_session
            )
            
            # Execute task
            start_time = datetime.now()
            result = await agent.run()
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "status": "success",
                "result": str(result),
                "task": task,
                "duration_seconds": duration,
                "model_used": self.primary_model,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "task": task
            }
    
    async def execute_batch(
        self,
        tasks: List[str],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute multiple browser automation tasks in sequence (batch mode).
        
        Args:
            tasks: List of task descriptions
            context: Optional context about WHINT dashboard
        
        Returns:
            Dict with results for each task and summary
        """
        try:
            # Ensure browser is initialized
            if not self.browser_session:
                init_result = await self.initialize_browser()
                if init_result["status"] == "error":
                    return init_result
            
            batch_start = datetime.now()
            results = []
            successful = 0
            failed = 0
            
            for i, task in enumerate(tasks, 1):
                print(f"📋 Executing task {i}/{len(tasks)}: {task[:50]}...")
                
                task_result = await self.execute_task(task, context)
                
                if task_result["status"] == "success":
                    successful += 1
                else:
                    failed += 1
                
                results.append({
                    "task_number": i,
                    "task": task,
                    "result": task_result
                })
            
            batch_duration = (datetime.now() - batch_start).total_seconds()
            
            return {
                "status": "completed",
                "total_tasks": len(tasks),
                "successful": successful,
                "failed": failed,
                "results": results,
                "total_duration_seconds": batch_duration,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _build_task_with_context(self, task: str, context: Optional[str] = None) -> str:
        """Build enhanced task with WHINT dashboard context."""
        base_context = """
You are interacting with the WHINT dashboard for SAP Interface Management.

Common navigation patterns:
- Dashboard: Main landing page with overview
- Objects: Lists all interfaces/objects
- Analyze: Click to view detailed analysis
- Reports: Access various reports and statistics

Key actions:
- Navigate to specific sections using menu
- Click "Analyze" buttons to see details
- Extract data from tables and charts
- Summarize findings

Current location: You are already logged into the WHINT dashboard.
        """
        
        if context:
            enhanced_task = f"{base_context}\n\nAdditional Context:\n{context}\n\nTask: {task}"
        else:
            enhanced_task = f"{base_context}\n\nTask: {task}"
        
        return enhanced_task
    
    async def close(self):
        """Close browser session."""
        if self.browser_session:
            try:
                await self.browser_session.close()
                print("✅ Browser session closed")
            except Exception as e:
                print(f"⚠️ Error closing browser: {str(e)}")


# Helper function for synchronous environments
def run_browser_task(
    task: str,
    primary_model: str = "gemini-2.0-flash-exp",
    fallback_model: str = "gpt-4o-mini",
    username: Optional[str] = None,
    password: Optional[str] = None,
    headless: bool = False
) -> Dict[str, Any]:
    """
    Synchronous wrapper for browser automation (for use in non-async contexts).
    
    Example:
        result = run_browser_task(
            task="Navigate to Objects and count interfaces",
            primary_model="gemini-2.0-flash-exp",
            username="user@example.com",
            password="password123"
        )
    """
    import sys
    import platform
    
    # Fix Windows asyncio subprocess support
    if platform.system() == 'Windows':
        # Use ProactorEventLoop for subprocess support on Windows
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    async def _async_wrapper():
        engine = BrowserAutomationEngine(
            primary_model=primary_model,
            fallback_model=fallback_model,
            username=username,
            password=password,
            headless=headless
        )
        
        try:
            # Initialize browser with auto-login
            await engine.initialize_browser()
            
            # Execute task
            result = await engine.execute_task(task)
            
            return result
        finally:
            await engine.close()
    
    # Run async code with proper event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_async_wrapper())


if __name__ == "__main__":
    # Example usage
    print("🤖 Browser Automation Engine - Example Usage\n")
    
    # Test with Gemini (fast and cheap)
    result = run_browser_task(
        task="Go to google.com and tell me the first search result for 'browser automation'",
        primary_model="gemini-2.0-flash-exp",
        fallback_model="gpt-4o-mini",
        headless=False
    )
    
    print("\n📊 Result:")
    print(result)

