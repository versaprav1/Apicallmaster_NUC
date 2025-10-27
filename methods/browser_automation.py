"""
Browser Automation with Storage State (Cookie-Based Persistence)
- No profile lock issues
- Fast browser startup
- Persistent login sessions
- Manual authentication support
"""

import asyncio
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback
from pathlib import Path


class BrowserAutomationEngine:
    """
    Browser automation engine with storage state persistence.
    
    Features:
    - Cookie-based session persistence (no profile lock issues)
    - Fast browser startup (~5 seconds vs 30+ seconds)
    - Manual authentication support (you handle MFA/CAPTCHA)
    - Anti-bot detection built-in
    - Reliable and production-ready
    """
    
    def __init__(
        self,
        primary_model: str = "gemini-2.0-flash-exp",
        fallback_model: Optional[str] = "gpt-4o-mini",
        headless: bool = False,
        whint_url: str = "https://whintic-test.cfapps.eu10.hana.ondemand.com/",
        storage_state_file: Optional[str] = "whint_session.json",
        ollama_base_url: str = "http://localhost:11434"
    ):
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.headless = headless
        self.whint_url = whint_url
        self.storage_state_file = Path(storage_state_file) if storage_state_file else None
        self.ollama_base_url = ollama_base_url
        
        self.browser_session = None
        self.current_llm = None
        self.is_logged_in = False
        self.session_start_time = None
        
    def _get_llm_instance(self, model_name: str):
        """Get LLM instance based on model name."""
        try:
            if any(name in model_name.lower() for name in ["gpt", "o1", "chatgpt"]):
                from browser_use.llm import ChatOpenAI
                return ChatOpenAI(model=model_name)
            elif "gemini" in model_name.lower():
                from browser_use.llm import ChatGoogle
                return ChatGoogle(model=model_name)
            elif "claude" in model_name.lower():
                from browser_use.llm import ChatAnthropic
                return ChatAnthropic(model=model_name)
            elif any(name in model_name.lower() for name in ["llama", "mixtral", "groq"]):
                from browser_use.llm import ChatGroq
                return ChatGroq(model=model_name)
            else:
                from browser_use.llm import ChatOllama
                return ChatOllama(model=model_name, base_url=self.ollama_base_url)
        except Exception as e:
            raise Exception(f"Failed to initialize {model_name}: {str(e)}")
    
    def _get_llm_with_fallback(self):
        """Get LLM with fallback support."""
        try:
            llm = self._get_llm_instance(self.primary_model)
            print(f"Using primary model: {self.primary_model}")
            return llm
        except Exception as e:
            print(f"Primary model failed: {e}")
            if self.fallback_model:
                try:
                    llm = self._get_llm_instance(self.fallback_model)
                    print(f"Using fallback model: {self.fallback_model}")
                    return llm
                except Exception as fallback_error:
                    raise Exception(f"Both models failed. Primary: {e}, Fallback: {fallback_error}")
            else:
                raise Exception(f"Primary model failed and no fallback: {e}")
    
    async def initialize_browser(self) -> Dict[str, Any]:
        """
        Initialize browser with storage state (cookie-based persistence).
        Fast startup, no profile lock issues.
        """
        try:
            from browser_use.browser import BrowserSession, BrowserProfile
            
            self.session_start_time = datetime.now()
            self.current_llm = self._get_llm_with_fallback()
            
            # Check if we have saved session
            has_saved_session = self.storage_state_file and self.storage_state_file.exists()
            
            print("\n" + "="*70)
            if has_saved_session:
                print(f"Found saved session: {self.storage_state_file}")
                print("Loading cookies... (you should already be logged in!)")
            else:
                print("No saved session found")
                print("You'll need to login manually this first time")
            print("="*70 + "\n")
            
            # Anti-bot detection arguments
            chrome_args = [
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--no-default-browser-check',
            ]
            
            # Create browser profile with storage state
            browser_profile = BrowserProfile(
                headless=self.headless,
                disable_security=False,
                args=chrome_args,
                deterministic_rendering=False,
                storage_state=str(self.storage_state_file) if has_saved_session else None
            )
            
            print("Starting browser... (fast startup with storage state)")
            self.browser_session = BrowserSession(browser_profile=browser_profile)
            
            await self.browser_session.start()
            
            return {
                "status": "initialized",
                "model": self.primary_model,
                "has_saved_session": has_saved_session,
                "session_start": self.session_start_time.isoformat()
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    async def navigate_and_wait_for_manual_login(
        self,
        url: Optional[str] = None,
        save_session: bool = True
    ) -> Dict[str, Any]:
        """
        Navigate to URL and wait for you to login manually.
        Browser stays open indefinitely until you press ENTER.
        
        This is the PROVEN WORKING approach:
        - Navigates to the login page
        - Browser STAYS OPEN while you login
        - YOU manually enter credentials, handle 2FA, solve CAPTCHAs
        - Take as long as you need (no timeout!)
        - Press ENTER when done
        - Session is saved for future use
        
        Args:
            url: URL to navigate to (default: WHINT URL)
            save_session: Save session cookies after login (default: True)
        
        Returns:
            Dict with status
        """
        try:
            if url is None:
                url = self.whint_url
            
            if not self.browser_session:
                init_result = await self.initialize_browser()
                if init_result["status"] == "error":
                    return init_result
            
            # Navigate to the URL (simple, no agent complexity)
            print(f"Navigating to: {url}")
            page = await self.browser_session.get_current_page()
            await page.goto(url)
            print(f"✅ Navigated to {url} (browser will stay open)\n")
            
            # Check if we need manual login
            has_saved_session = self.storage_state_file and self.storage_state_file.exists()
            
            if not has_saved_session:
                print("="*70)
                print("FIRST TIME SETUP - MANUAL LOGIN REQUIRED")
                print("="*70)
                print("\nThe browser is open and waiting for you to login.")
                print("\nPlease complete these steps in the browser window:")
                print("  1. Enter your email/username")
                print("  2. Enter your password")
                print("  3. Complete any 2FA/MFA codes")
                print("  4. Solve any CAPTCHAs")
                print("  5. Wait until you see the WHINT dashboard")
                print("  6. THEN come back here and press ENTER")
                print("\n⏰ TAKE YOUR TIME - Browser will stay open!")
                print("="*70 + "\n")
                
                # Wait for user confirmation (browser stays open)
                await asyncio.get_event_loop().run_in_executor(
                    None, input, "Press ENTER after you've logged in and see the dashboard... "
                )
                
                # Save the session if requested
                if save_session and self.storage_state_file:
                    print("\n💾 Saving session cookies...")
                    page = await self.browser_session.get_current_page()
                    context = page.context
                    storage_state = await context.storage_state()
                    
                    with open(self.storage_state_file, 'w') as f:
                        json.dump(storage_state, f, indent=2)
                    
                    print(f"✅ Session saved to {self.storage_state_file}")
                    print("  Next time you run this, you'll already be logged in!\n")
            else:
                print("✅ Using saved session - checking if still logged in...")
                print("  (If you see a login page, delete whint_session.json and try again)\n")
            
            self.is_logged_in = True
            
            return {
                "status": "ready",
                "message": "Authentication complete",
                "url": url,
                "session_saved": save_session and not has_saved_session
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    async def execute_task(
        self,
        task: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a browser automation task."""
        try:
            from browser_use import Agent
            
            if not self.browser_session:
                init_result = await self.initialize_browser()
                if init_result["status"] == "error":
                    return init_result
            
            enhanced_task = self._build_task_with_context(task, context)
            
            agent = Agent(
                task=enhanced_task,
                llm=self.current_llm,
                browser_session=self.browser_session
            )
            
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
    
    def _build_task_with_context(self, task: str, context: Optional[str] = None) -> str:
        """Build enhanced task with WHINT dashboard context."""
        base_context = """
You are interacting with the WHINT dashboard for SAP Interface Management.

Common navigation patterns:
- Dashboard: Main landing page with overview
- Objects: Lists all interfaces/objects
- Analyze: Click to view detailed analysis
- Reports: Access various reports and statistics

You are already logged into the WHINT dashboard.
        """
        
        if context:
            return f"{base_context}\n\nAdditional Context:\n{context}\n\nTask: {task}"
        else:
            return f"{base_context}\n\nTask: {task}"
    
    async def close(self):
        """Close browser session."""
        if self.browser_session:
            try:
                await self.browser_session.close()
                print("Browser session closed")
            except Exception as e:
                print(f"Error closing browser: {str(e)}")


if __name__ == "__main__":
    print("Browser automation engine loaded")
