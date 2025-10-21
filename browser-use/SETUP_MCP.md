# Browser-Use MCP Setup for ApiCallMaster

This guide walks you through setting up browser-use MCP integration in your ApiCallMaster project.

## Why Your Container Was Stopping

**The Problem**: When you ran `docker run -d browseruse --mcp`, the container immediately stopped.

**The Reason**: Browser-use MCP is a **stdio-based server** (it communicates via stdin/stdout). When you run it in detached mode (`-d`), there's no client attached to its stdio, so the process has nothing to do and exits immediately.

**The Solution**: We use an "idle container" approach:
1. Run a container that stays alive doing nothing (`tail -f /dev/null`)
2. When your client needs to connect, it uses `docker exec -i` to spawn the MCP process inside the running container
3. The MCP process stays alive while the client is connected via stdio
4. When client disconnects, the MCP process exits (but container stays idle)

## Quick Setup (5 Minutes)

### Step 1: Create Environment File

Create `docker-praveen/.env` in this directory with your API keys:

```bash
# Required: At least ONE of these
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...

# Optional
BROWSER_USE_HEADLESS=false  # Show browser (useful for debugging)
BROWSER_USE_DISABLE_SECURITY=true  # For testing only
```

### Step 2: Build Docker Image (First Time Only)

```powershell
# From browser-use directory
docker build -t browseruse .
```

Or use the fast build:
```powershell
# Build base images first
./docker/build-base-images.sh

# Then build app
docker build -f Dockerfile.fast -t browseruse .
```

### Step 3: Start Idle Container

From **project root** (ApiCallMaster directory):

```powershell
.\scripts\maintenance\start_browser_mcp_container.ps1
```

Or manually:
```powershell
$envFile = (Resolve-Path .\browser-use\docker-praveen\.env).Path
$dataDir = (Resolve-Path .\browser-use\data).Path

docker run -d `
  --name browseruse-mcp `
  --shm-size=2g `
  --user root `
  -v "$($dataDir):/data" `
  --env-file "$envFile" `
  browseruse `
  tail -f /dev/null
```

### Step 4: Verify Container is Running

```powershell
docker ps | Select-String browseruse-mcp
```

You should see output like:
```
browseruse-mcp  ...  Up 5 seconds  ...
```

### Step 5: Test Connection

```powershell
# From project root
python scripts/examples/test_browser_mcp.py
```

Expected output:
```
✅ Connected! Available tools: 15
✅ Navigation complete
✅ Page title: Example Domain
✅ All basic operations completed successfully!
```

### Step 6: Use in Your App

The browser automation page is already integrated into `app.py`. Just:

1. Start Streamlit: `streamlit run app.py`
2. Navigate to "🌐 Browser Automation" page
3. Click "Connect" in the sidebar
4. Start automating!

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  Streamlit App (app.py)                         │
│  └─ Browser Automation Page                     │
│     └─ BrowserUseMCPClient (Python)             │
│        │                                         │
│        │ stdio (JSON-RPC)                       │
│        ▼                                         │
│  ┌─────────────────────────────────────────┐   │
│  │ docker exec -i browseruse-mcp           │   │
│  │   browser-use --mcp                     │   │
│  │                                         │   │
│  │ MCP Server exposes browser tools:      │   │
│  │ - browser_navigate                      │   │
│  │ - browser_click                         │   │
│  │ - browser_extract_content               │   │
│  │ - retry_with_browser_use_agent          │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│  Docker Container: browseruse-mcp                │
│  - Runs idle (tail -f /dev/null)               │
│  - Spawns MCP process per client connection     │
│  - Mounts ./data for browser profiles           │
└─────────────────────────────────────────────────┘
```

## Available Browser Tools

### Direct Control
- `navigate(url)` - Navigate to a URL
- `click(selector)` - Click an element
- `type_text(selector, text)` - Type into input
- `scroll(direction, amount)` - Scroll page
- `go_back()` - Browser back button
- `get_state()` - Get page title, URL, DOM, screenshot

### Extraction
- `extract_content(selector)` - Extract text from elements

### Tab Management
- `list_tabs()` - List all open tabs
- `switch_tab(tab_id)` - Switch to a tab
- `close_tab(tab_id)` - Close a tab

### Session Management
- `list_sessions()` - List browser sessions
- `close_session(session_id)` - Close a session
- `close_all()` - Close everything

### Autonomous Agent
- `run_agent_task(task)` - Delegate complex task to AI agent

## Usage Examples

### Example 1: Simple Scraping

```python
from src.browser_mcp_client import BrowserUseMCPClient
import asyncio

async def scrape_example():
    client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
    
    try:
        await client.initialize()
        await client.navigate("https://example.com")
        heading = await client.extract_content("h1")
        print(f"Heading: {heading}")
    finally:
        await client.close()

asyncio.run(scrape_example())
```

### Example 2: Autonomous Agent

```python
async def agent_research():
    client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
    
    try:
        await client.initialize()
        
        result = await client.run_agent_task(
            "Go to GitHub, search for 'browser-use', "
            "click the first result, and extract the repository description"
        )
        
        print(f"Result: {result}")
    finally:
        await client.close()

asyncio.run(agent_research())
```

## Troubleshooting

### Container Stops Immediately
✅ **Solution**: Use the idle container approach (see Step 3). Never run `docker run -d browseruse --mcp` directly.

### "No API key found" Error
✅ **Solution**: Check that `docker-praveen/.env` has at least one valid LLM API key.

```powershell
# Verify env is loaded in container
docker exec browseruse-mcp env | Select-String OPENAI
```

### Connection Refused / Can't Connect
✅ **Solution**: Verify container is running and test manual exec:

```powershell
# Check status
docker ps | Select-String browseruse-mcp

# Test manual connection (should output JSON)
docker exec -i browseruse-mcp browser-use --mcp
# Press Ctrl+C to exit
```

### Chromium Crashes
✅ **Solution**: Ensure `--shm-size=2g` is set (already in startup script).

### Windows Volume Permission Errors
✅ **Solution**: Run as root with `--user root` (already in startup script).

### Port Conflicts
If you see port conflicts (9222, 9242):
```powershell
# Find conflicting process
netstat -ano | Select-String "9222"

# Kill process or remove port mapping from container
docker stop browseruse-mcp
docker rm browseruse-mcp
# Restart without -p flags (not needed for stdio)
```

## Container Management

```powershell
# View logs
docker logs browseruse-mcp

# View live logs
docker logs -f browseruse-mcp

# Stop container
docker stop browseruse-mcp

# Start container
docker start browseruse-mcp

# Restart container
docker restart browseruse-mcp

# Remove container (to recreate)
docker rm -f browseruse-mcp

# Shell access (for debugging)
docker exec -it browseruse-mcp /bin/bash
```

## Performance Tips

1. **Use Headless Mode in Production**
   ```bash
   BROWSER_USE_HEADLESS=true
   ```
   Saves memory and CPU.

2. **Close Sessions When Done**
   ```python
   await client.close_all()
   ```
   Prevents browser instances from accumulating.

3. **Use Agent Tasks for Complex Workflows**
   Instead of scripting 10 manual steps, describe the task and let the agent figure it out.

4. **Reuse Client Connections**
   Create one client per session, not per request.

## Security Notes

⚠️ **BROWSER_USE_DISABLE_SECURITY=true** disables web security. Only use for testing.

⚠️ Store API keys securely. Never commit `.env` files.

⚠️ Browser automation can be detected by some websites. Use responsibly.

## What to Share with Other Agents

Give them the file: `docs/MCP_AGENT_REFERENCE.txt`

It contains everything needed to connect:
- Connection command
- Required environment variables
- Available tools
- Protocol specification
- Python examples

## Next Steps

1. ✅ Container is running
2. ✅ Test connection works
3. ✅ Try the Streamlit UI
4. ✅ Build your automation workflows
5. ✅ Integrate with your existing ApiCallMaster features

## Support & Documentation

- [Quick Start Guide](../docs/BROWSER_MCP_QUICK_START.md) - Fast setup instructions
- [Full Integration Guide](../docs/BROWSER_USE_MCP_INTEGRATION_GUIDE.md) - Complete reference
- [Agent Reference](../docs/MCP_AGENT_REFERENCE.txt) - Copy-paste for other agents
- [Browser-Use Docs](https://docs.browser-use.com) - Official documentation
- [MCP Protocol](https://spec.modelcontextprotocol.io/) - Protocol specification

## Common Questions

**Q: Why not just run `browser-use --mcp` directly?**
A: MCP requires stdin/stdout communication. Docker exec provides that connection.

**Q: Can I run multiple clients simultaneously?**
A: Yes! Each `docker exec` spawns a separate MCP process and browser instance.

**Q: Does the container need to restart when I reconnect?**
A: No. The idle container stays running. Only the MCP processes start/stop.

**Q: Can I use this without Docker?**
A: Yes, run `uvx browser-use --mcp` locally. Update client mode to "local".

**Q: How do I monitor browser usage/costs?**
A: Check your LLM provider's dashboard. The agent uses LLM calls for decision making.

---

**You're all set!** 🎉 Start automating at `http://localhost:8501` (Browser Automation page)


