"""
Simple Browser Automation Test

Quick test to verify browser automation works with a simple Google search.
This demonstrates the basic usage without WHINT login.
"""

import asyncio
from methods.browser_automation import BrowserAutomationEngine


async def main():
    print("🚀 Starting simple browser automation test...\n")
    
    # Create browser engine (no login for Google test)
    engine = BrowserAutomationEngine(
        primary_model="gemini-2.0-flash-exp",  # Fast and cheap
        fallback_model="gpt-4o-mini",          # Reliable backup
        headless=False,                         # Show browser window
        auto_login=False                        # No login needed for Google
    )
    
    try:
        # Initialize browser (skip auto-login)
        print("📂 Initializing browser...")
        init_result = await engine.initialize_browser()
        print(f"✅ Browser started: {init_result['model']}\n")
        
        # Execute a simple task
        task = "Go to google.com and search for 'browser automation'. Tell me the first 3 search result titles."
        print(f"📋 Task: {task}\n")
        print("🤖 Agent is working... (this may take 30-60 seconds)\n")
        
        result = await engine.execute_task(task)
        
        if result["status"] == "success":
            print(f"✅ Task completed in {result['duration_seconds']:.1f}s\n")
            print("📊 Result:")
            print("=" * 60)
            print(result["result"])
            print("=" * 60)
        else:
            print(f"❌ Task failed: {result.get('error')}")
    
    finally:
        # Close browser
        print("\n🛑 Closing browser...")
        await engine.close()
        print("✅ Done!")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║         Browser Automation Simple Test (Google)              ║
║                                                              ║
║  This test demonstrates:                                     ║
║  • Opening a visible browser                                 ║
║  • Navigating to Google                                      ║
║  • Performing a search                                       ║
║  • Extracting results                                        ║
║                                                              ║
║  Model: gemini-2.0-flash-exp (fast & cheap)                  ║
║  Fallback: gpt-4o-mini (reliable)                            ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Fix Windows asyncio subprocess support
    import platform
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())

