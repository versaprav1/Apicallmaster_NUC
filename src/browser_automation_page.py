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
        
        # Login Settings
        st.markdown("**Login Settings**")
        
        from pathlib import Path
        storage_state_file = st.text_input(
            "Session file", 
            value="whint_session.json",
            help="Cookie file to save/load your login session"
        )
        
        has_saved_session = Path(storage_state_file).exists()
        
        if has_saved_session:
            st.success("✅ Saved session found")
            st.caption("Will use saved cookies - no login needed!")
            if st.button("🗑️ Clear saved session", help="Delete saved cookies to login fresh"):
                Path(storage_state_file).unlink()
                st.success("Session cleared! Refresh to see changes.")
                st.rerun()
        else:
            st.info("ℹ️ First time: Agent will login for you")
            
            # Username and password inputs
            username = st.text_input(
                "Username/Email",
                value="",
                placeholder="your-email@example.com",
                help="Login username or email"
            )
            password = st.text_input(
                "Password",
                type="password",
                value="",
                placeholder="Your password",
                help="Login password (not saved, only used once)"
            )
            
            st.caption("⚠️ Agent can handle simple login forms. For 2FA/CAPTCHA, you may need to intervene manually.")
        
        st.markdown("---")
        
        # Browser control buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Start", disabled=st.session_state.browser_active, use_container_width=True):
                # Check if we need credentials (first time, no saved session)
                if not has_saved_session:
                    if not username or not password:
                        st.error("❌ Please enter username and password (first time login)")
                        st.stop()
                
                with st.spinner("Starting browser..."):
                    try:
                        engine = BrowserAutomationEngine(
                            primary_model=primary_model,
                            fallback_model=fallback_model,
                            headless=headless,
                            whint_url=whint_url,
                            storage_state_file=storage_state_file
                        )
                        
                        st.session_state.browser_engine = engine
                        st.session_state.browser_active = True
                        
                        # Decide: Auto-login with Agent OR use saved session
                        if has_saved_session:
                            # Use saved session (fast!)
                            with st.spinner("Loading saved session..."):
                                result = _run_async(engine.initialize_browser(use_saved_session=True))
                                
                                if result["status"] == "initialized":
                                    # Navigate to WHINT
                                    async def navigate_to_whint():
                                        page = await engine.browser_session.get_current_page()
                                        await page.goto(engine.whint_url)
                                        return {"status": "navigated"}
                                    
                                    nav_result = _run_async(navigate_to_whint())
                                    
                                    if nav_result["status"] == "navigated":
                                        st.success("✅ Browser started with saved session!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Navigation failed")
                                else:
                                    st.error(f"❌ Failed: {result.get('error', 'Unknown')}")
                        else:
                            # First time: Agent handles login
                            with st.spinner("🤖 Agent is logging in... (watch the browser)"):
                                result = _run_async(engine.auto_login_with_agent(
                                    username=username,
                                    password=password,
                                    url=whint_url,
                                    save_session=True
                                ))
                                
                                if result["status"] == "success":
                                    st.success("✅ Agent logged in successfully!")
                                    st.info(f"Session saved! Next time, no login needed.")
                                    st.rerun()
                                elif "CAPTCHA" in result.get("error", "") or "2FA" in result.get("error", ""):
                                    st.warning("⚠️ Agent encountered CAPTCHA or 2FA. Please complete it in the browser.")
                                    st.info("After completing, click 'Save Session' in sidebar to save your login.")
                                else:
                                    st.error(f"❌ Login failed: {result.get('error', 'Unknown')}")
                                    st.error("Try again or use manual login if needed.")
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        st.session_state.browser_active = False
                        st.session_state.browser_engine = None
        
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
