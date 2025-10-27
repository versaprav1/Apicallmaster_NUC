"""
Browser Automation Page for Streamlit App - Minimal Clean Version
"""

import streamlit as st
import asyncio
import platform
from datetime import datetime
import traceback
from methods.browser_automation import BrowserAutomationEngine


def _run_async(coro):
    """Helper to run async code in Streamlit with Windows subprocess support."""
    # Fix Windows asyncio subprocess support
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


def browser_automation_page():
    """Main browser automation page."""
    
    st.title("🌐 Browser Automation")
    st.markdown("Automate WHINT dashboard interactions with AI-powered browser control")
    
    # Initialize session state
    if 'browser_engine' not in st.session_state:
        st.session_state.browser_engine = None
        st.session_state.browser_active = False
        st.session_state.task_history = []
    
    # Sidebar settings
    with st.sidebar:
        st.markdown("### ⚙️ Browser Settings")
        
        # Get available models
        if 'llm_manager' not in st.session_state:
            from src.llm_providers import LLMProviderManager
            st.session_state.llm_manager = LLMProviderManager()
        
        available_models = st.session_state.llm_manager.get_available_models(show_all=True)
        model_names = list(available_models.keys())
        
        # Add Ollama models
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                ollama_models = [m["name"] for m in data.get("models", []) if "name" in m]
                for ollama_model in ollama_models:
                    if ollama_model not in model_names:
                        model_names.append(ollama_model)
        except:
            pass
        
        fallback_model_names = model_names + ["None"]
        
        # Model selection
        primary_model = st.selectbox("Primary Model", model_names, index=0 if model_names else 0)
        fallback_raw = st.selectbox("Fallback Model", fallback_model_names, index=1 if len(fallback_model_names) > 1 else 0)
        fallback_model = None if fallback_raw == "None" else fallback_raw
        
        # Browser settings
        headless = not st.checkbox("Show browser window", value=True)
        whint_url = st.text_input("WHINT URL", value="https://whintic-test.cfapps.eu10.hana.ondemand.com/")
        
        # Session Management (Storage State)
        st.markdown("**Session Management**")
        storage_state_file = st.text_input(
            "Session file", 
            value="whint_session.json",
            help="Cookie file to save/load your login session"
        )
        
        from pathlib import Path
        if Path(storage_state_file).exists():
            st.success("✅ Saved session found - you should already be logged in!")
            if st.button("🗑️ Clear saved session", help="Delete saved cookies to login fresh"):
                Path(storage_state_file).unlink()
                st.success("Session cleared! Refresh to see changes.")
                st.rerun()
        else:
            st.info("ℹ️ First time: You'll login manually and session will be saved")
        
        st.markdown("---")
        
        # Browser control buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Start", disabled=st.session_state.browser_active, use_container_width=True):
                with st.spinner("Starting browser..."):
                    try:
                        engine = BrowserAutomationEngine(
                            primary_model=primary_model,
                            fallback_model=fallback_model,
                            headless=headless,
                            whint_url=whint_url,
                            storage_state_file=storage_state_file
                        )
                        
                        # Initialize browser
                        result = _run_async(engine.initialize_browser())
                        
                        if result["status"] == "initialized":
                            st.session_state.browser_engine = engine
                            st.session_state.browser_active = True
                            
                            # Navigate to WHINT (Streamlit-friendly - no input() wait)
                            async def navigate_to_whint():
                                page = await engine.browser_session.get_current_page()
                                await page.goto(engine.whint_url)
                                return {"status": "navigated"}
                            
                            nav_result = _run_async(navigate_to_whint())
                            
                            if nav_result["status"] == "navigated":
                                if result.get("has_saved_session"):
                                    st.success("✅ Browser started! Using saved session - you should be logged in.")
                                else:
                                    st.warning("⏸️ Browser started! Please login manually in the browser window, then use the task panel below.")
                                st.rerun()
                            else:
                                st.error("❌ Navigation failed")
                        else:
                            st.error(f"❌ Failed: {result.get('error', 'Unknown')}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        with col2:
            if st.button("🛑 Stop", disabled=not st.session_state.browser_active, use_container_width=True):
                if st.session_state.browser_engine:
                    try:
                        _run_async(st.session_state.browser_engine.close())
                        st.session_state.browser_engine = None
                        st.session_state.browser_active = False
                        st.success("✅ Stopped")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        # Status & Session Save
        if st.session_state.browser_active:
            st.success("🟢 Active")
            
            # Save session button (if not already saved)
            if st.session_state.browser_engine:
                storage_file = Path(st.session_state.browser_engine.storage_state_file)
                if not storage_file.exists():
                    if st.button("💾 Save Session", help="Save your login for next time"):
                        try:
                            async def save_session():
                                engine = st.session_state.browser_engine
                                page = await engine.browser_session.get_current_page()
                                context = page.context
                                storage_state = await context.storage_state()
                                import json
                                with open(storage_file, 'w') as f:
                                    json.dump(storage_state, f, indent=2)
                                return {"status": "saved"}
                            
                            result = _run_async(save_session())
                            if result["status"] == "saved":
                                st.success(f"✅ Session saved to {storage_file}!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Save failed: {str(e)}")
        else:
            st.warning("🔴 Inactive")
    
    # Main area
    if not st.session_state.browser_active:
        st.info("👈 Click 'Start' in sidebar")
        return
    
    # Tabs
    tab1, tab2 = st.tabs(["💬 Interactive", "📊 History"])
    
    with tab1:
        st.markdown("### Ask Questions")
        
        task = st.text_area(
            "Your Question",
            height=100,
            placeholder="e.g., Navigate to Objects and count interfaces"
        )
        
        if st.button("▶️ Execute", type="primary", disabled=not task.strip()):
            with st.spinner("Working..."):
                try:
                    result = _run_async(
                        st.session_state.browser_engine.execute_task(task)
                    )
                    
                    if result["status"] == "success":
                        st.success(f"✅ Done ({result['duration_seconds']:.1f}s)")
                        st.markdown("### Result")
                        st.markdown(result["result"])
                        
                        st.session_state.task_history.append({
                            "timestamp": datetime.now().isoformat(),
                            "task": task,
                            "result": result["result"]
                        })
                    else:
                        st.error(f"❌ Failed: {result.get('error', 'Unknown')}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.code(traceback.format_exc())
    
    with tab2:
        st.markdown("### History")
        
        if not st.session_state.task_history:
            st.info("No history yet")
        else:
            for entry in reversed(st.session_state.task_history[-5:]):
                with st.expander(f"{entry['timestamp'][:19]}"):
                    st.markdown(f"**Task:** {entry['task']}")
                    st.markdown(f"**Result:** {entry['result'][:200]}...")
