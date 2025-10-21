# Browser-Use MCP Quick Start Guide

**Quick copy-paste commands to get browser-use MCP running in 5 minutes.**

## Prerequisites
- Docker Desktop installed and running
- Python 3.11+ with asyncio support
- At least one LLM API key (OpenAI, Anthropic, or OpenRouter)

## Step 1: Build the Docker Image (First Time Only)

```powershell
# Navigate to browser-use directory
cd browser-use

# Build the image
docker build -t browseruse .
```

## Step 2: Create .env File

Create `browser-use/docker-praveen/.env` with your API keys:

```bash
# At least one of these is required
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=...
# OR
OPENROUTER_API_KEY=...

# Optional settings
BROWSER_USE_HEADLESS=false  # Set to true to hide browser window
BROWSER_USE_DISABLE_SECURITY=true  # For testing only
```

## Step 3: Start the Container

From project root:

```powershell
# Run the setup script
.\scripts\maintenance\start_browser_mcp_container.ps1
```

Or manually:

```powershell
# Set paths
$envFile = (Resolve-Path .\browser-use\docker-praveen\.env).Path
$dataDir = (Resolve-Path .\browser-use\data).Path

# Start container
docker run -d `
  --name browseruse-mcp `
  --shm-size=2g `
  --user root `
  -v "$($dataDir):/data" `
  --env-file "$envFile" `
  browseruse `
  tail -f /dev/null
```

## Step 4: Verify Container is Running

```powershell
# Check status
docker ps | Select-String browseruse-mcp

# Should show: browseruse-mcp ... Up ... 
```

## Step 5: Test the Connection

```powershell
# Run test script
python scripts/examples/test_browser_mcp.py
```

You should see:
```
✅ Connected! Available tools: 15
✅ Navigation complete
✅ Page title: Example Domain
✅ All basic operations completed successfully!
```

## Step 6: Use in Your Code

### Simple Example

```python
import asyncio
from src.browser_mcp_client import BrowserUseMCPClient

async def main():
    client = BrowserUseMCPClient(
        mode="docker",
        docker_container="browseruse-mcp"
    )
    
    try:
        await client.initialize()
        
        # Navigate to a page
        await client.navigate("https://example.com")
        
        # Extract content
        heading = await client.extract_content("h1")
        print(f"Heading: {heading}")
        
    finally:
        await client.close()

asyncio.run(main())
```

### Autonomous Agent Example

```python
async def agent_example():
    client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
    
    try:
        await client.initialize()
        
        # Let the agent handle a complex task
        result = await client.run_agent_task(
            "Go to GitHub, search for 'browser-use', "
            "and extract the description of the first result"
        )
        
        print(f"Agent found: {result}")
        
    finally:
        await client.close()

asyncio.run(agent_example())
```

## Available Methods

### Navigation
- `await client.navigate(url)` - Go to URL
- `await client.go_back()` - Go back
- `await client.get_state()` - Get page state (title, URL, DOM)

### Interaction
- `await client.click(selector)` - Click element
- `await client.type_text(selector, text)` - Type text
- `await client.scroll(direction, amount)` - Scroll page

### Extraction
- `await client.extract_content(selector)` - Extract content from elements

### Tabs & Sessions
- `await client.list_tabs()` - List open tabs
- `await client.switch_tab(tab_id)` - Switch to tab
- `await client.close_tab(tab_id)` - Close tab
- `await client.list_sessions()` - List browser sessions
- `await client.close_all()` - Close all sessions

### Autonomous Agent
- `await client.run_agent_task(task_description)` - Delegate complex task to AI agent

## Troubleshooting

### Container Stops Immediately
**Problem**: Container exits right after starting.

**Solution**: The idle mode keeps it running. If it still stops:
```powershell
# Check logs
docker logs browseruse-mcp

# Restart
docker restart browseruse-mcp
```

### "No API key found"
**Problem**: MCP server can't find LLM API key.

**Solution**: 
1. Check `.env` file exists and has a valid key
2. Restart container: `docker restart browseruse-mcp`
3. Verify key is loaded: `docker exec browseruse-mcp env | Select-String OPENAI`

### "Connection refused" / Can't Connect
**Problem**: Client can't connect to MCP server.

**Solution**:
```powershell
# 1. Verify container is running
docker ps | Select-String browseruse-mcp

# 2. Test manual exec
docker exec -i browseruse-mcp browser-use --mcp

# 3. Should output JSON. Press Ctrl+C to exit
```

### Chromium Crashes
**Problem**: Browser crashes with shared memory errors.

**Solution**: Ensure `--shm-size=2g` is set (already in startup script).

### Permission Errors
**Problem**: Volume mount fails.

**Solution**: Run as root with `--user root` (already in startup script).

## Container Management

```powershell
# View logs
docker logs browseruse-mcp

# Stop container
docker stop browseruse-mcp

# Start container
docker start browseruse-mcp

# Restart container
docker restart browseruse-mcp

# Remove container (to recreate)
docker rm -f browseruse-mcp

# Access container shell
docker exec -it browseruse-mcp /bin/bash
```

## Next Steps

1. ✅ **Integrate into Streamlit app** - Add browser automation page
2. ✅ **Create workflows** - Define common browser automation tasks
3. ✅ **Add error handling** - Implement retries and fallbacks
4. ✅ **Monitor usage** - Track browser automation costs and performance

## Full Documentation

- [Complete Integration Guide](./BROWSER_USE_MCP_INTEGRATION_GUIDE.md)
- [Browser-Use MCP Docs](https://docs.browser-use.com/customize/mcp-server)
- [MCP Protocol Spec](https://spec.modelcontextprotocol.io/)

## Support

If you encounter issues:
1. Check logs: `docker logs browseruse-mcp`
2. Verify .env file has valid API keys
3. Test connection: `python scripts/examples/test_browser_mcp.py`
4. See [troubleshooting guide](./BROWSER_USE_MCP_INTEGRATION_GUIDE.md#troubleshooting)

---

**That's it!** You now have a working browser automation MCP server ready to use. 🎉


