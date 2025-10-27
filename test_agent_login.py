"""
Test Agent-Driven Automatic Login
Quick test to see if the AI model can handle login automatically
"""

import asyncio
from methods.browser_automation import BrowserAutomationEngine


async def test_auto_login():
    """Test automatic login with Agent."""
    
    # Replace with your actual credentials
    USERNAME = "autprof55@gmail.com"  # Replace with your username
    PASSWORD = "your_password_here"   # Replace with your password
    
    print("\n" + "="*70)
    print("Testing Agent-Driven Automatic Login")
    print("="*70)
    print("\n⚠️  BEFORE RUNNING:")
    print("   1. Update USERNAME and PASSWORD in this script")
    print("   2. Delete whint_session.json if it exists (to test fresh login)")
    print("   3. Make sure Chrome is closed")
    print("\n")
    
    # Check if credentials are updated
    if PASSWORD == "your_password_here":
        print("❌ ERROR: Please update the PASSWORD in this script first!")
        return
    
    # Create engine
    engine = BrowserAutomationEngine(
        primary_model="gemini-2.0-flash-exp",
        fallback_model="gemini-2.0-flash",
        headless=False,  # Show browser so you can watch
        whint_url="https://whintic-test.cfapps.eu10.hana.ondemand.com/",
        storage_state_file="whint_session.json"
    )
    
    try:
        # Agent will handle everything
        result = await engine.auto_login_with_agent(
            username=USERNAME,
            password=PASSWORD,
            save_session=True
        )
        
        print("\n" + "="*70)
        print("RESULT:")
        print("="*70)
        
        if result["status"] == "success":
            print("✅ SUCCESS!")
            print(f"   Duration: {result['duration_seconds']:.1f} seconds")
            print(f"   Session saved: {result['session_saved']}")
            print(f"\n   Agent output:")
            print(f"   {result['agent_result']}")
            print("\n✅ Browser will stay open - you can interact with it")
            print("   Press Ctrl+C to close")
            
            # Keep browser open
            await asyncio.sleep(3600)  # 1 hour
        else:
            print("❌ FAILED!")
            print(f"   Error: {result.get('error', 'Unknown')}")
            
            if "CAPTCHA" in str(result.get('error', '')):
                print("\n💡 TIP: The site has CAPTCHA - you'll need to solve it manually")
                print("   Browser will stay open - solve it and wait...")
                await asyncio.sleep(60)  # Wait 60 seconds for manual intervention
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Exception: {str(e)}")
    finally:
        print("\n🧹 Cleaning up...")
        await engine.close()
        print("✅ Done")


if __name__ == "__main__":
    asyncio.run(test_auto_login())

