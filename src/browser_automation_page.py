"""
Browser Automation Page for Streamlit App

@file purpose: Provides a Streamlit UI for browser automation using browser-use MCP.

What this file does:
- Adds a browser automation page to the ApiCallMaster Streamlit app
- Provides UI for manual browser control and autonomous agent tasks
- Shows browser state, screenshots, and extracted content

How it fits into the system:
- Integrated into app.py as a new page option
- Uses BrowserUseMCPClient to communicate with browser-use MCP server
"""

import streamlit as st
import asyncio
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import json
import base64

from src.browser_mcp_client import BrowserUseMCPClient


def _run_async(coro):
    """Helper to run async code in Streamlit with proper event loop."""
    if 'browser_event_loop' in st.session_state and st.session_state.browser_event_loop:
        loop = st.session_state.browser_event_loop
        return loop.run_until_complete(coro)
    else:
        # Fallback for operations before connection
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        return asyncio.run(coro)


def browser_automation_page():
    """Display browser automation page."""
    st.title("🌐 Browser Automation")
    st.markdown("Control a web browser or delegate tasks to an autonomous agent.")
    
    # Connection status
    with st.sidebar:
        st.markdown("### Browser Control Status")
        
        # Initialize client if not already in session
        if 'browser_client' not in st.session_state:
            st.session_state.browser_client = None
            st.session_state.browser_connected = False
            st.session_state.browser_event_loop = None
        
        # Connection controls
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔌 Connect", disabled=st.session_state.browser_connected):
                with st.spinner("Connecting to browser..."):
                    try:
                        # On Windows, we need to use SelectorEventLoop for subprocess support
                        # MUST set policy BEFORE creating the loop
                        if sys.platform == "win32":
                            policy = asyncio.WindowsSelectorEventLoopPolicy()
                            asyncio.set_event_loop_policy(policy)
                            loop = policy.new_event_loop()
                        else:
                            loop = asyncio.new_event_loop()
                        
                        asyncio.set_event_loop(loop)
                        
                        try:
                            client = BrowserUseMCPClient(
                                mode="docker",
                                docker_container="browseruse-mcp"
                            )
                            result = loop.run_until_complete(client.initialize())
                            st.session_state.browser_client = client
                            st.session_state.browser_connected = True
                            st.session_state.browser_event_loop = loop
                            st.success(f"✅ Connected! {result['tools_available']} tools available")
                            st.rerun()
                        finally:
                            # Don't close the loop as the client needs it
                            pass
                    except ImportError:
                        st.error("Please install nest-asyncio: pip install nest-asyncio")
                    except Exception as e:
                        st.error(f"Failed to connect: {str(e)}")
                        import traceback
                        st.error(traceback.format_exc())
        
        with col2:
            if st.button("🔌 Disconnect", disabled=not st.session_state.browser_connected):
                if st.session_state.browser_client:
                    try:
                        _run_async(st.session_state.browser_client.close())
                    except:
                        pass
                    st.session_state.browser_client = None
                    st.session_state.browser_connected = False
                    st.session_state.browser_event_loop = None
                    st.success("Disconnected")
                    st.rerun()
        
        # Show connection status
        if st.session_state.browser_connected:
            st.success("🟢 Connected")
        else:
            st.warning("🔴 Not Connected")
            st.info("Click 'Connect' to start browser automation.")
    
    if not st.session_state.browser_connected:
        st.warning("⚠️ Browser not connected. Click 'Connect' in the sidebar to start.")
        
        # Show setup instructions
        with st.expander("📖 Setup Instructions", expanded=True):
            st.markdown("""
            ### Prerequisites
            1. Docker Desktop running
            2. Browser-use container started
            
            ### Quick Start
            ```powershell
            # Start the container
            .\\scripts\\maintenance\\start_browser_mcp_container.ps1
            
            # Verify it's running
            docker ps | Select-String browseruse-mcp
            ```
            
            ### Test Connection
            ```powershell
            python scripts/examples/test_browser_mcp.py
            ```
            
            ### Documentation
            - [Quick Start Guide](../docs/BROWSER_MCP_QUICK_START.md)
            - [Full Integration Guide](../docs/BROWSER_USE_MCP_INTEGRATION_GUIDE.md)
            """)
        return
    
    # Important notes
    st.info("ℹ️ **Note:** The browser runs **headless** (no visible window). Use the Browser State tab to see screenshots and page content.")
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["🤖 Agent Tasks", "🎮 Manual Control", "📊 Browser State"])
    
    # Tab 1: Autonomous Agent Tasks
    with tab1:
        st.markdown("### Autonomous Browser Agent")
        st.markdown("Describe a task and let the AI agent figure out how to complete it.")
        
        # Task presets
        presets = [
            "— None —",
            "Go to example.com and extract the main heading",
            "Search Google for 'browser automation' and extract top 3 results",
            "Navigate to GitHub homepage and extract the trending repositories",
            "Go to OpenAI website and extract the navigation menu items",
        ]
        preset = st.selectbox("Example Tasks", presets, key="agent_preset")
        
        # Task input
        default_task = preset if preset != "— None —" else ""
        task = st.text_area(
            "Task Description",
            value=default_task,
            placeholder="e.g., Go to company.com/pricing and extract all plan names and prices",
            height=100,
            key="agent_task"
        )
        
        # Run button
        col1, col2 = st.columns([1, 4])
        with col1:
            run_agent = st.button("▶️ Run Agent", type="primary", disabled=not task.strip())
        
        if run_agent and task.strip():
            st.warning("⚠️ Agent tasks can take 2-5 minutes! The agent needs to plan, navigate, and execute multiple steps.")
            with st.spinner("🤖 Agent is working... This may take several minutes. Please be patient!"):
                start_time = datetime.now()
                try:
                    result = _run_async(
                        st.session_state.browser_client.run_agent_task(task)
                    )
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    st.success(f"✅ Task completed in {duration:.1f}s")
                    
                    # Show result
                    st.markdown("### Result")
                    if isinstance(result, dict):
                        st.json(result)
                    else:
                        st.markdown(str(result))
                    
                    # Log to history
                    if 'browser_history' not in st.session_state:
                        st.session_state.browser_history = []
                    st.session_state.browser_history.append({
                        'timestamp': datetime.now().isoformat(),
                        'type': 'agent_task',
                        'task': task,
                        'result': result,
                        'duration': duration
                    })
                    
                except Exception as e:
                    st.error(f"❌ Agent failed: {str(e)}")
    
    # Tab 2: Manual Control
    with tab2:
        st.markdown("### Manual Browser Control")
        st.markdown("Use individual tools to control the browser step by step.")
        
        # Quick test section
        st.markdown("#### Quick Test")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.text("Test navigation to example.com")
        with col2:
            if st.button("🧪 Test"):
                with st.spinner("Testing... (may take 30-60 seconds on first run)"):
                    try:
                        start = datetime.now()
                        result = _run_async(st.session_state.browser_client.navigate("https://example.com"))
                        duration = (datetime.now() - start).total_seconds()
                        st.success(f"✅ Test passed! ({duration:.1f}s)")
                    except Exception as e:
                        st.error(f"❌ Test failed: {str(e)}")
        
        st.markdown("---")
        
        # Navigation section
        st.markdown("#### Navigation")
        st.warning("⚠️ First navigation takes 30-60s to start Chromium. Be patient!")
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            url = st.text_input("URL", value="https://whintic-test.cfapps.eu10.hana.ondemand.com/", key="manual_url")
        with col2:
            if st.button("🌐 Navigate"):
                with st.spinner(f"Navigating to {url}... (may take 30-60s)"):
                    try:
                        start = datetime.now()
                        result = _run_async(st.session_state.browser_client.navigate(url))
                        duration = (datetime.now() - start).total_seconds()
                        st.success(f"✅ Navigated to {url} ({duration:.1f}s)")
                        st.info("💡 Go to 'Browser State' tab and click 'Refresh State' to see the page")
                    except Exception as e:
                        st.error(f"Failed: {str(e)}")
        with col3:
            if st.button("⬅️ Back"):
                with st.spinner("Going back..."):
                    try:
                        result = _run_async(st.session_state.browser_client.go_back())
                        st.success("✅ Went back")
                    except Exception as e:
                        st.error(f"Failed: {str(e)}")
        
        st.markdown("---")
        
        # Interaction section
        st.markdown("#### Interaction")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Click Element**")
            click_selector = st.text_input("CSS Selector", key="click_selector", placeholder="e.g., button#submit")
            if st.button("🖱️ Click"):
                if click_selector:
                    try:
                        result = _run_async(st.session_state.browser_client.click(click_selector))
                        st.success(f"✅ Clicked {click_selector}")
                    except Exception as e:
                        st.error(f"Failed: {str(e)}")
        
        with col2:
            st.markdown("**Type Text**")
            type_selector = st.text_input("CSS Selector", key="type_selector", placeholder="e.g., input#name")
            type_text = st.text_input("Text", key="type_text")
            if st.button("⌨️ Type"):
                if type_selector and type_text:
                    try:
                        result = _run_async(
                            st.session_state.browser_client.type_text(type_selector, type_text)
                        )
                        st.success(f"✅ Typed into {type_selector}")
                    except Exception as e:
                        st.error(f"Failed: {str(e)}")
        
        st.markdown("---")
        
        # Extraction section
        st.markdown("#### Content Extraction")
        extract_selector = st.text_input(
            "CSS Selector (optional, leave empty for all text)",
            key="extract_selector"
        )
        if st.button("📄 Extract Content"):
            try:
                result = _run_async(
                    st.session_state.browser_client.extract_content(
                        extract_selector if extract_selector else None
                    )
                )
                st.success("✅ Content extracted")
                st.markdown("**Extracted Content:**")
                st.text_area("", value=str(result), height=200, key="extracted_content_display")
            except Exception as e:
                st.error(f"Failed: {str(e)}")
        
        st.markdown("---")
        
        # Scroll section
        st.markdown("#### Scroll")
        col1, col2, col3 = st.columns(3)
        with col1:
            scroll_direction = st.selectbox("Direction", ["down", "up"], key="scroll_direction")
        with col2:
            scroll_amount = st.number_input("Amount (px)", value=500, key="scroll_amount")
        with col3:
            if st.button("⬇️ Scroll"):
                try:
                    result = _run_async(
                        st.session_state.browser_client.scroll(scroll_direction, scroll_amount)
                    )
                    st.success(f"✅ Scrolled {scroll_direction} {scroll_amount}px")
                except Exception as e:
                    st.error(f"Failed: {str(e)}")
    
    # Tab 3: Browser State
    with tab3:
        st.markdown("### Current Browser State")
        
        if st.button("🔄 Refresh State"):
            try:
                with st.spinner("Getting browser state..."):
                    state = _run_async(st.session_state.browser_client.get_state())
                    st.session_state.browser_state = state
                    st.success("✅ State refreshed")
            except Exception as e:
                st.error(f"Failed: {str(e)}")
        
        if 'browser_state' in st.session_state and st.session_state.browser_state:
            state = st.session_state.browser_state
            
            # Basic info
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Page Title:**")
                st.text(state.get('title', 'N/A'))
            with col2:
                st.markdown("**URL:**")
                st.text(state.get('url', 'N/A'))
            
            # Screenshot
            if 'screenshot' in state and state['screenshot']:
                st.markdown("**Screenshot:**")
                try:
                    # Decode base64 screenshot
                    img_data = base64.b64decode(state['screenshot'])
                    st.image(img_data, use_column_width=True)
                except:
                    st.warning("Could not display screenshot")
            
            # DOM snapshot
            with st.expander("🌳 DOM Snapshot"):
                st.text_area("", value=str(state.get('dom', 'N/A')), height=400, key="dom_display")
            
            # Tabs
            tabs = _run_async(st.session_state.browser_client.list_tabs())
            if tabs:
                with st.expander(f"📑 Open Tabs ({len(tabs)})"):
                    for i, tab in enumerate(tabs):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.text(f"{i+1}. {tab.get('title', 'Untitled')}")
                        with col2:
                            if st.button("Switch", key=f"switch_tab_{i}"):
                                try:
                                    _run_async(st.session_state.browser_client.switch_tab(tab['id']))
                                    st.success("Switched!")
                                except Exception as e:
                                    st.error(f"Failed: {e}")
                        with col3:
                            if st.button("Close", key=f"close_tab_{i}"):
                                try:
                                    _run_async(st.session_state.browser_client.close_tab(tab['id']))
                                    st.success("Closed!")
                                except Exception as e:
                                    st.error(f"Failed: {e}")
            
            # Sessions
            sessions = _run_async(st.session_state.browser_client.list_sessions())
            if sessions:
                with st.expander(f"🖥️ Browser Sessions ({len(sessions)})"):
                    for i, session in enumerate(sessions):
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.text(f"Session {i+1}: {session.get('id', 'N/A')}")
                        with col2:
                            if st.button("Close", key=f"close_session_{i}"):
                                try:
                                    _run_async(
                                        st.session_state.browser_client.close_session(session['id'])
                                    )
                                    st.success("Closed!")
                                except Exception as e:
                                    st.error(f"Failed: {e}")
        else:
            st.info("Click 'Refresh State' to view current browser state")
    
    # History sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Recent Activity")
        
        if 'browser_history' in st.session_state and st.session_state.browser_history:
            for item in reversed(st.session_state.browser_history[-5:]):
                with st.expander(f"🕐 {item['timestamp'][:16]}"):
                    st.markdown(f"**Type:** {item['type']}")
                    if item['type'] == 'agent_task':
                        st.markdown(f"**Task:** {item['task'][:50]}...")
                        st.markdown(f"**Duration:** {item['duration']:.1f}s")
        else:
            st.info("No recent activity")


# Cleanup function to close browser on app shutdown
def cleanup_browser_client():
    """Close browser client on app shutdown."""
    if 'browser_client' in st.session_state and st.session_state.browser_client:
        try:
            _run_async(st.session_state.browser_client.close())
        except:
            pass


# Register cleanup
import atexit
atexit.register(cleanup_browser_client)


