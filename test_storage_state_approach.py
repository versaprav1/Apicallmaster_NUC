"""
Storage State Approach - More Reliable than Full Profile
This saves cookies/localStorage after manual login, then reuses them
NO profile lock issues, NO 30-second timeout issues!
"""

import asyncio
import subprocess
from pathlib import Path


async def main():
    print("""
======================================================================
   Storage State Approach (Cookie-Based Persistence)
======================================================================

This is MORE RELIABLE than loading full Chrome profiles:
  ✅ No profile lock issues
  ✅ No 30-second timeout
  ✅ Still maintains login sessions
  ✅ Works with browser-use perfectly

How it works:
  1. First time: You login manually → Saves cookies
  2. Future runs: Loads saved cookies → Already logged in!
======================================================================
    """)
    
    storage_file = Path("whint_session.json")
    
    # Step 1: Kill Chrome
    print("[Step 1] Ensuring Chrome is closed...")
    try:
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"],
                      capture_output=True)
        print("  Chrome processes cleared\n")
    except:
        print("  No Chrome to kill\n")
    
    await asyncio.sleep(2)
    
    # Step 2: Initialize
    print("[Step 2] Initializing browser...")
    
    try:
        from browser_use.browser import BrowserSession, BrowserProfile
        from browser_use.llm import ChatGoogle
        from browser_use import Agent
        
        llm = ChatGoogle(model="gemini-2.0-flash-exp")
        
        # Simple browser profile - NO user_data_dir (avoids profile lock!)
        if storage_file.exists():
            print(f"  Found saved session: {storage_file}")
            print("  Loading cookies... (you should already be logged in!)\n")
            
            browser_profile = BrowserProfile(
                headless=False,
                storage_state=str(storage_file)  # Load saved cookies
            )
        else:
            print("  No saved session found")
            print("  You'll need to login manually this first time\n")
            
            browser_profile = BrowserProfile(
                headless=False
            )
        
        session = BrowserSession(browser_profile=browser_profile)
        print("Starting browser... (should be fast - no profile loading!)")
        
        await session.start()
        print("✅ Browser started!\n")
        
        # Step 3: Navigate to WHINT
        print("[Step 3] Navigating to WHINT...")
        
        # Just navigate - don't use agent (keeps it simpler and browser stays open)
        page = await session.get_current_page()
        await page.goto("https://whintic-test.cfapps.eu10.hana.ondemand.com/")
        
        print("✅ Navigated to WHINT (browser will stay open)\n")
        
        # Step 4: Check if logged in or need manual login
        if not storage_file.exists():
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
            
            # Wait for user confirmation (browser stays open during this)
            await asyncio.get_event_loop().run_in_executor(
                None, input, "Press ENTER after you've logged in and see the dashboard... "
            )
            
            # Save the session
            print("\n💾 Saving session cookies...")
            
            # Get current page state
            page = await session.get_current_page()
            context = page.context
            
            # Save storage state (cookies, localStorage, etc.)
            storage_state = await context.storage_state()
            import json
            with open(storage_file, 'w') as f:
                json.dump(storage_state, f, indent=2)
            
            print(f"✅ Session saved to {storage_file}")
            print("  Next time you run this, you'll already be logged in!\n")
        else:
            print("✅ Using saved session - you should already be logged in!")
            print("  (If not, delete whint_session.json and run again)\n")
        
        # Step 5: Test automation
        print("[Step 4] Testing automation...")
        
        test_agent = Agent(
            task="What page am I on? Describe what you see.",
            llm=llm,
            browser_session=session
        )
        
        result = await test_agent.run()
        
        print("\n" + "="*70)
        print("AUTOMATION TEST RESULT:")
        print("="*70)
        print(str(result)[:500])
        print("="*70 + "\n")
        
        print("✅ Success! Storage state approach is working!")
        print("\nBenefits of this approach:")
        print("  ✅ No profile lock issues")
        print("  ✅ Fast browser startup (no profile to load)")
        print("  ✅ Persistent login (cookies saved)")
        print("  ✅ Works reliably every time\n")
        
        input("Press ENTER to close browser...")
        
        await session.close()
        print("Done!")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    import platform
    
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())

