"""
Quick test to navigate to whint website and check browser state.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.browser_mcp_client import BrowserUseMCPClient


async def test_whint_navigation():
    """Test navigating to the whint website."""
    client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
    
    try:
        print("=" * 60)
        print("CONNECTING TO BROWSER-USE MCP SERVER")
        print("=" * 60)
        
        # Initialize
        print("\n[1] Initializing...")
        init_result = await client.initialize()
        print(f"✅ Connected! {init_result['tools_available']} tools available")
        print(f"   Available tools: {', '.join(init_result['tools'][:5])}...")
        
        # Navigate to whint website
        print("\n[2] Navigating to whint website...")
        target_url = "https://whintic-test.cfapps.eu10.hana.ondemand.com/"
        
        try:
            nav_result = await client.navigate(target_url)
            print(f"✅ Navigation complete!")
            print(f"   Result: {nav_result}")
        except Exception as e:
            print(f"❌ Navigation failed: {e}")
            print("   Trying alternative tool names...")
            
            # Try different tool names
            for tool_name in ["browser_navigate", "navigate", "browser_go_to", "goto"]:
                try:
                    print(f"   Trying {tool_name}...")
                    nav_result = await client.call_tool(tool_name, {"url": target_url})
                    print(f"   ✅ {tool_name} worked!")
                    break
                except Exception as e2:
                    print(f"   ❌ {tool_name} failed: {e2}")
        
        # Get browser state
        print("\n[3] Getting browser state...")
        try:
            state = await client.get_state()
            print(f"✅ State retrieved!")
            print(f"   Title: {state.get('title', 'N/A')}")
            print(f"   URL: {state.get('url', 'N/A')}")
            print(f"   Has screenshot: {'screenshot' in state}")
            print(f"   Has DOM: {'dom' in state}")
        except Exception as e:
            print(f"❌ Get state failed: {e}")
            print("   Trying alternative tool names...")
            
            # Try different tool names
            for tool_name in ["browser_get_state", "get_state", "browser_state", "state"]:
                try:
                    print(f"   Trying {tool_name}...")
                    state = await client.call_tool(tool_name, {})
                    print(f"   ✅ {tool_name} worked!")
                    print(f"   Title: {state.get('title', 'N/A')}")
                    break
                except Exception as e2:
                    print(f"   ❌ {tool_name} failed: {e2}")
        
        # List all available tools with details
        print("\n[4] Available Tools:")
        print("-" * 60)
        for i, tool in enumerate(client.tools, 1):
            print(f"{i}. {tool.get('name', 'unnamed')}")
            if 'description' in tool:
                print(f"   Description: {tool['description'][:80]}...")
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n[5] Closing client...")
        try:
            await client.close()
            print("✅ Closed successfully")
        except:
            print("⚠️ Close had issues (non-critical)")


if __name__ == "__main__":
    asyncio.run(test_whint_navigation())



