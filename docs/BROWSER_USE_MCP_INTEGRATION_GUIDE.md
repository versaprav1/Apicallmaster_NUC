# Browser-Use MCP Integration Guide

## Overview
This guide explains how to integrate browser-use MCP (Model Context Protocol) server into your ApiCallMaster project for programmatic browser automation.

## What is Browser-Use MCP?

Browser-Use MCP is a **stdio-based server** that exposes browser automation tools over the Model Context Protocol. It allows your agents to:
- Navigate web pages
- Click elements
- Type text
- Extract content
- Manage tabs and sessions
- Delegate complex tasks to an autonomous browser agent

## Why Containers Keep Stopping

**Problem**: When you run `docker run -d browseruse --mcp`, the container stops immediately.

**Reason**: MCP is a **stdio server** (stdin/stdout communication). When run detached (`-d`), there's no client connected to stdio, so the process exits.

**Solutions**:
1. **Keep container attached** (`-it`) while a client is connected
2. **Run an idle container** and use `docker exec -i` when client connects

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ApiCallMaster (app.py)                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │          Browser-Use MCP Client Adapter               │  │
│  │  - Spawns/attaches MCP server process                │  │
│  │  - Communicates via stdio (JSON-RPC)                 │  │
│  │  - Provides high-level browser operations            │  │
│  └──────────────┬────────────────────────────────────────┘  │
│                 │ stdio                                      │
│                 │                                            │
└─────────────────┼────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│        Browser-Use MCP Server (stdio process)                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Command: docker exec -i browseruse-mcp               │  │
│  │           browser-use --mcp                           │  │
│  │                                                       │  │
│  │  Exposes tools:                                      │  │
│  │  - browser_navigate                                  │  │
│  │  - browser_click                                     │  │
│  │  - browser_type                                      │  │
│  │  - browser_get_state                                 │  │
│  │  - browser_extract_content                           │  │
│  │  - retry_with_browser_use_agent                      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Setup Instructions

### Step 1: Prepare Environment

Create or update your `.env` file in the browser-use directory:

```bash
# Required: At least one LLM provider
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=...
# OR
OPENROUTER_API_KEY=...

# Optional: Browser settings
BROWSER_USE_HEADLESS=false  # Set to true for production
BROWSER_USE_DISABLE_SECURITY=true  # For testing only
```

### Step 2: Start Idle Container (Recommended Approach)

From the `browser-use` directory:

```powershell
# Windows PowerShell
$envFile = (Resolve-Path .\docker-praveen\.env).Path
$dataDir = (Resolve-Path .\data).Path

docker run -d `
  --name browseruse-mcp `
  --shm-size=2g `
  --user root `
  -v "$($dataDir):/data" `
  --env-file "$envFile" `
  browseruse `
  tail -f /dev/null
```

This keeps a container running idle. Your MCP client will use `docker exec -i` to spawn the actual MCP process.

### Step 3: Verify Container is Running

```powershell
docker ps | Select-String browseruse-mcp
```

You should see the container in "Up" status.

### Step 4: Use the MCP Client Adapter

The `BrowserUseMCPClient` class (see `src/browser_mcp_client.py`) handles:
- Starting the MCP server process via `docker exec -i`
- JSON-RPC communication over stdio
- Tool discovery and invocation
- Session lifecycle management

## Available MCP Tools

### Direct Control Tools
- **browser_navigate(url)**: Navigate to a URL
- **browser_get_state()**: Get current page state (DOM + screenshot)
- **browser_click(element_selector)**: Click an element
- **browser_type(element_selector, text)**: Type into an element
- **browser_scroll(direction, amount)**: Scroll the page
- **browser_go_back()**: Go back in history

### Tab Management
- **browser_list_tabs()**: List all open tabs
- **browser_switch_tab(tab_id)**: Switch to a tab
- **browser_close_tab(tab_id)**: Close a tab

### Session Management
- **browser_list_sessions()**: List all browser sessions
- **browser_close_session(session_id)**: Close a session
- **browser_close_all()**: Close all sessions

### Content Extraction
- **browser_extract_content(selector)**: Extract content from elements

### Agent Delegation
- **retry_with_browser_use_agent(task)**: Delegate a complex task to the autonomous browser agent

## Usage Examples

### Example 1: Simple Navigation and Extraction

```python
from src.browser_mcp_client import BrowserUseMCPClient

async def scrape_example():
    client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
    
    try:
        # Initialize connection
        await client.initialize()
        
        # Navigate
        result = await client.call_tool("browser_navigate", {"url": "https://example.com"})
        print(f"Navigated: {result}")
        
        # Get page state
        state = await client.call_tool("browser_get_state", {})
        print(f"Page title: {state.get('title')}")
        
        # Extract content
        content = await client.call_tool("browser_extract_content", {
            "selector": "h1"
        })
        print(f"Heading: {content}")
        
    finally:
        await client.close()
```

### Example 2: Delegate Complex Task to Agent

```python
async def agent_task():
    client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
    
    try:
        await client.initialize()
        
        # Let the agent handle a complex multi-step task
        result = await client.call_tool("retry_with_browser_use_agent", {
            "task": "Go to GitHub, search for 'browser-use', find the first repository, and extract the description"
        })
        
        print(f"Agent result: {result}")
        
    finally:
        await client.close()
```

### Example 3: Integration with Streamlit App

```python
import streamlit as st
import asyncio
from src.browser_mcp_client import BrowserUseMCPClient

async def run_browser_task(task_description):
    client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
    try:
        await client.initialize()
        result = await client.call_tool("retry_with_browser_use_agent", {
            "task": task_description
        })
        return result
    finally:
        await client.close()

def browser_automation_page():
    st.title("🌐 Browser Automation")
    
    task = st.text_area("Describe the browser task:", 
                       placeholder="e.g., Go to OpenAI website and extract pricing info")
    
    if st.button("Run Browser Task"):
        with st.spinner("Running browser automation..."):
            result = asyncio.run(run_browser_task(task))
            st.success("Task completed!")
            st.json(result)
```

## Connection Details Summary

**For giving to another agent/team:**

```yaml
Server Command (Docker):
  - docker exec -i browseruse-mcp browser-use --mcp

Required Environment:
  - One of: OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY

Optional Environment:
  - BROWSER_USE_HEADLESS=false  # Show browser window
  - BROWSER_USE_DISABLE_SECURITY=true  # Disable web security

Data Persistence:
  - Mount: host_dir:/data (stores profiles, downloads, screenshots)

Protocol:
  - MCP over stdio (JSON-RPC 2.0)
  - Client spawns/attaches command and communicates via stdin/stdout

Tools Available:
  - Navigation: browser_navigate, browser_go_back
  - Interaction: browser_click, browser_type, browser_scroll
  - State: browser_get_state, browser_extract_content
  - Tabs: browser_list_tabs, browser_switch_tab, browser_close_tab
  - Sessions: browser_list_sessions, browser_close_session, browser_close_all
  - Agent: retry_with_browser_use_agent (autonomous subtask)
```

## Troubleshooting

### Container Stops Immediately
**Problem**: `docker run -d browseruse --mcp` exits right away.

**Solution**: MCP needs an attached stdio client. Use the idle container approach:
```powershell
docker run -d --name browseruse-mcp ... browseruse tail -f /dev/null
```

### Chromium Crashes
**Problem**: Browser crashes with "Shared memory" errors.

**Solution**: Ensure `--shm-size=2g` is set:
```powershell
docker run --shm-size=2g ...
```

### Permission Errors on Windows
**Problem**: Volume mount fails with permission errors.

**Solution**: Run container as root:
```powershell
docker run --user root ...
```

### No API Key Errors
**Problem**: "No API key found for LLM provider"

**Solution**: Check that your `.env` file contains at least one of:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENROUTER_API_KEY`

### Process Can't Connect
**Problem**: MCP client can't connect to server process.

**Solution**: 
1. Verify container is running: `docker ps`
2. Test manual exec: `docker exec -i browseruse-mcp browser-use --mcp`
3. Check that command outputs JSON on startup

## Next Steps

1. ✅ Start idle container (see Step 2)
2. ✅ Test connection with `BrowserUseMCPClient`
3. ✅ Integrate into your Streamlit app
4. ✅ Add browser automation features to your UI

## References

- [Browser-Use MCP Docs](https://docs.browser-use.com/customize/mcp-server)
- [Model Context Protocol Spec](https://spec.modelcontextprotocol.io/)
- [Browser-Use GitHub](https://github.com/browser-use/browser-use)


