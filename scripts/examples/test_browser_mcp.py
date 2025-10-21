"""
Test script for Browser-Use MCP integration.

Run this to verify your browser-use MCP setup is working.

Usage:
    python scripts/examples/test_browser_mcp.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.browser_mcp_client import BrowserUseMCPClient


async def test_basic_operations():
    """Test basic browser operations."""
    print("=" * 60)
    print("Testing Browser-Use MCP Client - Basic Operations")
    print("=" * 60)
    
    client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
    
    try:
        # Initialize
        print("\n[1/5] Initializing MCP client...")
        init_result = await client.initialize()
        print(f"✅ Connected! Available tools: {len(init_result['tools'])}")
        for tool in init_result['tools'][:5]:
            print(f"   - {tool}")
        if len(init_result['tools']) > 5:
            print(f"   ... and {len(init_result['tools']) - 5} more")
        
        # Navigate
        print("\n[2/5] Navigating to example.com...")
        nav_result = await client.navigate("https://example.com")
        print(f"✅ Navigation complete")
        
        # Get state
        print("\n[3/5] Getting page state...")
        state = await client.get_state()
        print(f"✅ Page title: {state.get('title', 'N/A')}")
        print(f"   URL: {state.get('url', 'N/A')}")
        
        # Extract content
        print("\n[4/5] Extracting content from <h1>...")
        content = await client.extract_content("h1")
        print(f"✅ Heading: {content}")
        
        # List sessions
        print("\n[5/5] Listing browser sessions...")
        sessions = await client.list_sessions()
        print(f"✅ Active sessions: {len(sessions)}")
        
        print("\n" + "=" * 60)
        print("✅ All basic operations completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print("\nClosing client...")
        await client.close()
        print("✅ Client closed")
    
    return True


async def test_agent_task():
    """Test autonomous agent task delegation."""
    print("\n" + "=" * 60)
    print("Testing Browser-Use MCP Client - Agent Task")
    print("=" * 60)
    
    client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
    
    try:
        print("\nInitializing...")
        await client.initialize()
        
        print("\nDelegating task to autonomous agent...")
        print("Task: Go to example.com and extract the main heading and first paragraph")
        
        result = await client.run_agent_task(
            "Go to example.com and extract the main heading (h1) and the first paragraph text"
        )
        
        print("\n✅ Agent completed task!")
        print(f"Result: {result}")
        
        print("\n" + "=" * 60)
        print("✅ Agent task completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print("\nClosing client...")
        await client.close()
        print("✅ Client closed")
    
    return True


async def main():
    """Run all tests."""
    print("\n🚀 Starting Browser-Use MCP Integration Tests\n")
    
    # Test 1: Basic operations
    success1 = await test_basic_operations()
    
    # Test 2: Agent task (optional, can be slow)
    print("\n\nWould you like to test autonomous agent tasks? (This may take longer)")
    print("Press Ctrl+C to skip, or wait 5 seconds to continue...")
    try:
        await asyncio.sleep(5)
        success2 = await test_agent_task()
    except KeyboardInterrupt:
        print("\n⏭️  Skipping agent test")
        success2 = True
    
    # Summary
    print("\n\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Basic Operations: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"Agent Task: {'✅ PASS' if success2 else '❌ FAIL'}")
    print("=" * 60)
    
    if success1 and success2:
        print("\n🎉 All tests passed! Browser-Use MCP is ready to use.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


