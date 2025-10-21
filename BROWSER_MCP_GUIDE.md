# Browser-Use MCP Complete Guide

**Status**: ✅ Fully Integrated | **Last Updated**: October 20, 2025

---

## 📖 What is Browser-Use MCP?

**Browser-Use MCP** is an AI-powered browser automation system integrated into your ApiCallMaster project. It allows you to:
- Control a web browser programmatically (navigate, click, type, extract content)
- Delegate complex tasks to an autonomous AI agent
- Automate web scraping, form filling, testing, and research tasks

### Why Was My Container Stopping?

**The Problem**: Running `docker run -d browseruse --mcp` stopped immediately.

**The Reason**: MCP uses **stdio protocol** (stdin/stdout communication). In detached mode with no client attached, the process has nothing to do and exits.

**The Solution**: We use the **"idle container + docker exec"** pattern:
1. Container runs idle (`tail -f /dev/null`)
2. Client spawns MCP via `docker exec -i browseruse-mcp browser-use --mcp`
3. MCP stays alive while client is connected
4. Container remains ready for next connection

### Key Capabilities

- **11 Browser Tools**: Navigate, click, type, scroll, extract, manage tabs/sessions
- **Autonomous Agent**: Describe a task in plain English, AI figures out the steps
- **Headless Mode**: Browser runs in Docker (no visible window), view via screenshots
- **Streamlit UI**: User-friendly interface with 3 tabs (Agent Tasks, Manual Control, Browser State)
- **Python API**: Use `BrowserUseMCPClient` anywhere in your code

---

## 🚀 Quick Start

### Step 1: Create `.env` File

```powershell
# Navigate to browser-use directory
cd browser-use\docker-praveen

# Create .env file
notepad .env
```

Add at least **ONE** API key:
```bash
# Required: Choose at least ONE
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...
# OR
OPENROUTER_API_KEY=sk-or-...

# Optional
BROWSER_USE_HEADLESS=false  # Set to true for production
```

### Step 2: Build Docker Image (First Time Only)

```powershell
# From browser-use directory
cd browser-use
docker build -t browseruse .
```

### Step 3: Start Container

```powershell
# From project root (ApiCallMaster)
.\scripts\maintenance\start_browser_mcp_container.ps1
```

Expected output:
```
✅ Container started successfully!
✅ Container is running: Up 2 seconds
🎉 Browser-Use MCP Container is Ready!
```

### Step 4: Test Connection

```powershell
.\.venv\Scripts\python.exe scripts/examples/test_browser_mcp.py
```

Expected output:
```
✅ Connected! 11 tools available
✅ Navigation complete
✅ All basic operations completed successfully!
```

### Step 5: Launch Streamlit UI

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```
- Navigate to **"🌐 Browser Automation"** page
- Click **"🔌 Connect"** in sidebar
- Start automating!

---

## 🎯 How to Use

### Option 1: Streamlit UI (Recommended for Beginners)

#### Connect to Browser
1. Open Streamlit app
2. Go to **"Browser Automation"** page
3. Click **"🔌 Connect"** in sidebar
4. Wait for "✅ Connected! 11 tools available"

#### Three Tabs Available:

**🤖 Agent Tasks Tab** (Autonomous AI)
- Describe task in plain English
- AI figures out the steps automatically
- Example: "Go to GitHub and search for 'browser-use', extract top 3 results"
- Wait time: 2-5 minutes

**🎮 Manual Control Tab** (Step-by-Step)
- Navigate to URLs
- Click elements (by CSS selector)
- Type into fields (by CSS selector)
- Scroll, go back, extract content
- Wait time: 30-60 seconds for first navigation

**📊 Browser State Tab** (View Results)
- Click "🔄 Refresh State" to get current page info
- View screenshot, title, URL, DOM
- Manage tabs and sessions
- See what the headless browser is doing

### Option 2: Python Code (For Developers)

#### Basic Connection

```python
from src.browser_mcp_client import BrowserUseMCPClient
import asyncio

async def main():
    client = BrowserUseMCPClient(
        mode="docker", 
        docker_container="browseruse-mcp"
    )
    
    try:
        # Initialize connection
        await client.initialize()
        print("✅ Connected!")
        
        # Your automation code here
        
    finally:
        await client.close()

asyncio.run(main())
```

#### Simple Web Scraping

```python
async def scrape_heading():
    client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
    
    try:
        await client.initialize()
        
        # Navigate to page
        await client.navigate("https://example.com")
        
        # Extract heading
        heading = await client.extract_content("h1")
        print(f"Heading: {heading}")
        
    finally:
        await client.close()

asyncio.run(scrape_heading())
```

#### Form Automation

```python
async def fill_form():
    client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
    
    try:
        await client.initialize()
        
        # Navigate to form
        await client.navigate("https://form.example.com")
        
        # Fill fields
        await client.type_text("#name", "John Doe")
        await client.type_text("#email", "john@example.com")
        
        # Submit
        await client.click("button[type='submit']")
        
        # Get confirmation
        state = await client.get_state()
        print(f"Current page: {state['title']}")
        
    finally:
        await client.close()

asyncio.run(fill_form())
```

#### Autonomous Agent Task (Most Powerful)

```python
async def research_task():
    client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
    
    try:
        await client.initialize()
        
        # Let AI agent figure out the steps
        result = await client.run_agent_task(
            "Go to company.com/pricing and extract all plan names and prices"
        )
        
        print(f"Agent result: {result}")
        
    finally:
        await client.close()

asyncio.run(research_task())
```

#### Use in Streamlit Apps

```python
import streamlit as st
from src.browser_mcp_client import BrowserUseMCPClient

def _run_async(coro):
    """Helper for running async in Streamlit."""
    import asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(coro)

# In your Streamlit page
task = st.text_area("Browser task:")

if st.button("Run"):
    async def run():
        client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
        try:
            await client.initialize()
            result = await client.run_agent_task(task)
            return result
        finally:
            await client.close()
    
    result = _run_async(run())
    st.json(result)
```

---

## 🛠️ Available Tools (11 Total)

### Navigation & State
| Tool | Description | Example |
|------|-------------|---------|
| `navigate(url)` | Go to URL | `await client.navigate("https://example.com")` |
| `go_back()` | Browser back button | `await client.go_back()` |
| `get_state()` | Get page title, URL, DOM, screenshot | `state = await client.get_state()` |

### Interaction
| Tool | Description | Example |
|------|-------------|---------|
| `click(selector)` | Click element (CSS selector) | `await client.click("button#submit")` |
| `type_text(selector, text)` | Type into field | `await client.type_text("#email", "user@example.com")` |
| `scroll(direction, amount)` | Scroll page | `await client.scroll("down", 500)` |

### Extraction
| Tool | Description | Example |
|------|-------------|---------|
| `extract_content(selector)` | Extract text from elements | `text = await client.extract_content("h1")` |

### Tab Management
| Tool | Description | Example |
|------|-------------|---------|
| `list_tabs()` | List all open tabs | `tabs = await client.list_tabs()` |
| `switch_tab(tab_id)` | Switch to specific tab | `await client.switch_tab(tab_id)` |
| `close_tab(tab_id)` | Close tab | `await client.close_tab(tab_id)` |

### Autonomous Agent (★ Most Powerful)
| Tool | Description | Example |
|------|-------------|---------|
| `run_agent_task(task)` | Delegate complex task to AI | `await client.run_agent_task("search GitHub for browser-use")` |

---

## ⚡ Important to Know

### Browser is Headless (No Visible Window)
- Browser runs **inside Docker** without a visible window
- You **won't see it** on your screen
- View results via **screenshots** in "Browser State" tab
- This is **normal and expected**

### Expected Wait Times
| Operation | Time | Reason |
|-----------|------|--------|
| First navigation | 30-60 seconds | Chromium starting up |
| Subsequent navigation | 5-15 seconds | Browser already running |
| Simple agent task | 1-3 minutes | LLM planning + execution |
| Complex agent task | 3-5 minutes | Multiple LLM calls + steps |

**Be patient!** Operations take time, especially on first run.

### Timeouts
- **Tool calls**: 300 seconds (5 minutes)
- **Regular requests**: 60 seconds
- **Agent tasks legitimately take 2-5 minutes** - this is normal!

### Tips for Success
1. **Test with example.com first** before your target website
2. **Use "Browser State" tab** to see what's happening (screenshots)
3. **Don't refresh page** while operations are running
4. **Start simple**, then gradually increase task complexity
5. **Monitor terminal** for debug messages `[Browser-Use]`

---

## 🐛 Troubleshooting

### Container Stops Immediately
- ✅ **Fixed!** Use the provided startup script
- Never run `docker run -d browseruse --mcp` directly
- Always use: `.\scripts\maintenance\start_browser_mcp_container.ps1`

### "No API key found" Error
```powershell
# Check .env exists
cd browser-use\docker-praveen
dir .env

# Verify API key is set
docker exec browseruse-mcp env | Select-String OPENAI

# Restart container
docker restart browseruse-mcp
```

### "Connection refused" / Can't Connect
```powershell
# 1. Check container is running
docker ps | Select-String browseruse-mcp

# 2. View logs
docker logs browseruse-mcp

# 3. Test manual connection
docker exec -i browseruse-mcp browser-use --mcp
# (Press Ctrl+C to exit)

# 4. If all fails, recreate container
docker rm -f browseruse-mcp
.\scripts\maintenance\start_browser_mcp_container.ps1
```

### "Request timeout after 60s"
- ✅ **Fixed!** Timeouts increased to 300s
- Agent tasks take 2-5 minutes - **this is normal**
- Be patient and wait for completion

### "Browser state shows nothing"
- **Cause**: Haven't navigated to a page yet
- **Solution**: Navigate to a URL first, then refresh state

### "Agent failed"
- Check task description is clear and specific
- Try simpler task first (e.g., "Go to example.com and get the title")
- Some tasks may be too complex or website may block automation

### Chromium Crashes
- ✅ **Fixed!** Script uses `--shm-size=2g` automatically
- If still crashes, check available system memory

---

## 🔧 Container Management

### Check Status
```powershell
docker ps | Select-String browseruse-mcp
```

### View Logs
```powershell
docker logs browseruse-mcp

# Follow logs in real-time
docker logs -f browseruse-mcp
```

### Restart Container
```powershell
docker restart browseruse-mcp
```

### Stop Container
```powershell
docker stop browseruse-mcp
```

### Remove and Recreate
```powershell
docker rm -f browseruse-mcp
.\scripts\maintenance\start_browser_mcp_container.ps1
```

### Check Container Health
```powershell
# All-in-one health check
docker ps | Select-String browseruse-mcp  # Should show "Up"
.\.venv\Scripts\python.exe scripts/examples/test_browser_mcp.py  # Should pass
```

---

## 📁 Key Files and Locations

| File | Purpose |
|------|---------|
| `src/browser_mcp_client.py` | Python MCP client (use this in your code) |
| `src/browser_automation_page.py` | Streamlit UI page |
| `scripts/examples/test_browser_mcp.py` | Test script to verify setup |
| `scripts/maintenance/start_browser_mcp_container.ps1` | Container startup script |
| `browser-use/docker-praveen/.env` | API keys configuration (create this) |
| `docs/BROWSER_USE_MCP_INTEGRATION_GUIDE.md` | Detailed technical guide |
| `docs/MCP_AGENT_REFERENCE.txt` | Share with other agents |

---

## 🤝 Share with Other Agents

If you need to give this MCP server info to another agent or developer, share this:

### Connection Info

**Command to Connect**:
```bash
docker exec -i browseruse-mcp browser-use --mcp
```

**Protocol**: MCP over stdio (JSON-RPC 2.0)

**Required Environment**: One of these API keys must be set in container:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENROUTER_API_KEY`

**Available Tools** (11 total):
- Navigation: `browser_navigate`, `browser_go_back`, `browser_get_state`
- Interaction: `browser_click`, `browser_type`, `browser_scroll`
- Extraction: `browser_extract_content`
- Tabs: `browser_list_tabs`, `browser_switch_tab`, `browser_close_tab`
- Agent: `retry_with_browser_use_agent` (autonomous task delegation)

### Python Client Example

```python
from src.browser_mcp_client import BrowserUseMCPClient
import asyncio

async def main():
    client = BrowserUseMCPClient(
        mode="docker", 
        docker_container="browseruse-mcp"
    )
    
    try:
        await client.initialize()
        result = await client.run_agent_task("your task here")
        print(result)
    finally:
        await client.close()

asyncio.run(main())
```

**Full Reference**: See `docs/MCP_AGENT_REFERENCE.txt` for complete protocol details.

---

## 🎓 Common Use Cases

### Web Scraping
```python
await client.navigate("https://site.com")
content = await client.extract_content(".main-content")
```

### Automated Research
```python
result = await client.run_agent_task(
    "Search Google for 'browser automation' and extract top 5 results"
)
```

### Form Testing
```python
await client.navigate("https://testsite.com/form")
await client.type_text("#username", "testuser")
await client.type_text("#password", "testpass")
await client.click("button[type='submit']")
state = await client.get_state()
assert "Dashboard" in state['title']
```

### Website Monitoring
```python
await client.navigate("https://status.example.com")
status = await client.extract_content(".status-indicator")
if "down" in status.lower():
    send_alert("Website is down!")
```

### Competitive Analysis
```python
result = await client.run_agent_task(
    "Go to competitor.com/pricing and extract all pricing tiers with features"
)
```

---

## 🎯 Example Workflows

### Workflow 1: Quick Website Check
1. Launch Streamlit → Browser Automation
2. Click "Connect"
3. Manual Control tab → Enter URL → Navigate (wait 30-60s)
4. Browser State tab → Refresh State → View screenshot
5. Done! You can see the page

### Workflow 2: Extract Data from Website
1. Connect to browser
2. Agent Tasks tab
3. Enter: "Go to [URL] and extract all product names and prices"
4. Click Run Agent (wait 2-5 minutes)
5. View extracted data in Result section

### Workflow 3: Test Your Web Application
1. Connect to browser
2. Manual Control tab
3. Navigate to your app
4. Fill form fields with `type_text()`
5. Click submit button with `click()`
6. Extract confirmation message
7. Verify success in Browser State

---

## 🔒 Security & Best Practices

### Security Notes
- ⚠️ **Never commit `.env` files** with API keys to Git
- ⚠️ `BROWSER_USE_DISABLE_SECURITY=true` is for **testing only**
- ⚠️ Respect `robots.txt` and website terms of service
- ⚠️ Some sites detect/block automated access - use responsibly

### Best Practices
1. **Use headless mode in production** (`BROWSER_USE_HEADLESS=true`)
2. **Close sessions when done** (`await client.close()`)
3. **Monitor LLM costs** (agent tasks use LLM for planning)
4. **Add delays between requests** to avoid rate limits
5. **Handle errors gracefully** (sites may be down or change structure)

---

## 📊 Technical Architecture

```
Streamlit App (app.py)
    └─ Browser Automation Page
       └─ BrowserUseMCPClient (src/browser_mcp_client.py)
          │
          │ stdio (JSON-RPC 2.0)
          ▼
    docker exec -i browseruse-mcp browser-use --mcp
          │
          ▼
    MCP Server (exposes 11 tools)
          │
          ▼
    Browser-Use Agent (AI planning & execution)
          │
          ▼
    Chromium Browser (Playwright, headless mode)
```

**Protocol**: MCP 2024-11-05 specification  
**Transport**: stdin/stdout (stdio)  
**Container**: Docker with idle mode  
**Browser**: Chromium via Playwright  

---

## ✅ Quick Verification Checklist

Run these commands to verify everything is working:

```powershell
# 1. Container running?
docker ps | Select-String browseruse-mcp
# Should show: Up X seconds/minutes

# 2. API key configured?
docker exec browseruse-mcp env | Select-String OPENAI
# Should show: OPENAI_API_KEY=sk-...

# 3. Connection works?
.\.venv\Scripts\python.exe scripts/examples/test_browser_mcp.py
# Should show: ✅ All tests passed

# 4. UI works?
.\.venv\Scripts\streamlit.exe run app.py
# Open Browser Automation page, click Connect
# Should show: 🟢 Connected
```

---

## 🎉 Summary

You now have **AI-powered browser automation** integrated into ApiCallMaster:

✅ **11 browser control tools** (navigate, click, type, extract, etc.)  
✅ **Autonomous AI agent** for complex multi-step tasks  
✅ **Streamlit UI** for easy interaction  
✅ **Python API** for programmatic control  
✅ **Headless operation** in Docker (view via screenshots)  
✅ **5-minute timeout** for long-running tasks  
✅ **Comprehensive error handling** and troubleshooting  

### Get Started Right Now

```powershell
# If not set up yet:
.\scripts\maintenance\start_browser_mcp_container.ps1
.\.venv\Scripts\python.exe scripts/examples/test_browser_mcp.py

# If already set up:
.\.venv\Scripts\streamlit.exe run app.py
# Navigate to: 🌐 Browser Automation
```

**Happy Automating!** 🤖🌐

---

**Questions?** Check `docs/BROWSER_USE_MCP_INTEGRATION_GUIDE.md` for detailed technical reference.  
**Issues?** Run `docker logs browseruse-mcp` and see troubleshooting section above.  
**Status**: ✅ **Ready to Use**

