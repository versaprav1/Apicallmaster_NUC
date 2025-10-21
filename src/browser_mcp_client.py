"""
Browser-Use MCP Client Adapter

@file purpose: Provides a Python client to communicate with browser-use MCP server
over stdio (JSON-RPC 2.0 protocol).

What this file does:
- Spawns/attaches browser-use MCP server process (local or Docker)
- Handles JSON-RPC communication over stdin/stdout
- Exposes browser automation tools as async methods
- Manages session lifecycle

How it fits into the system:
- Used by ApiCallMaster app.py to add browser automation capabilities
- Connects to browser-use MCP server running in Docker container
- Provides high-level interface for browser control
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional, List
from enum import Enum
import sys
import subprocess
import threading
from queue import Queue


class MCPClientMode(Enum):
    """MCP client connection mode"""
    LOCAL = "local"  # Run uvx browser-use --mcp
    DOCKER = "docker"  # Run docker exec -i <container> browser-use --mcp


class BrowserUseMCPClient:
    """
    Client for browser-use MCP server (stdio transport).
    
    Usage:
        client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
        await client.initialize()
        result = await client.call_tool("browser_navigate", {"url": "https://example.com"})
        await client.close()
    """
    
    def __init__(
        self,
        mode: str = "docker",
        docker_container: str = "browseruse-mcp",
        local_command: Optional[List[str]] = None
    ):
        """
        Initialize MCP client.
        
        Args:
            mode: "local" or "docker"
            docker_container: Name of Docker container (for docker mode)
            local_command: Custom command for local mode (default: ["uvx", "browser-use", "--mcp"])
        """
        self.mode = MCPClientMode(mode.lower())
        self.docker_container = docker_container
        self.local_command = local_command or ["uvx", "browser-use", "--mcp"]
        
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self._response_queue: Optional[Queue] = None
        self._read_thread: Optional[threading.Thread] = None
        self._running = False
        self.tools: List[Dict[str, Any]] = []
        
    async def initialize(self) -> Dict[str, Any]:
        """
        Start the MCP server process and initialize connection.
        
        Returns:
            Server capabilities and available tools
        """
        # Build command based on mode
        if self.mode == MCPClientMode.DOCKER:
            cmd = [
                "docker", "exec", "-i",
                self.docker_container,
                "browser-use", "--mcp"
            ]
        else:  # LOCAL
            cmd = self.local_command
        
        # Start process using subprocess.Popen (works in Streamlit on Windows)
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0  # Unbuffered
        )
        
        # Create queues for thread-safe communication
        self._response_queue = Queue()
        self._running = True
        
        # Start background thread to read responses
        self._read_thread = threading.Thread(target=self._read_responses_sync, daemon=True)
        self._read_thread.start()
        
        # Also start thread to log stderr for debugging
        self._stderr_thread = threading.Thread(target=self._log_stderr, daemon=True)
        self._stderr_thread.start()
        
        # Wait for server to be ready
        await asyncio.sleep(1)
        
        # MCP initialization handshake
        try:
            init_result = await self.call_method("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "browser-mcp-client",
                    "version": "1.0.0"
                }
            })
        except Exception as e:
            # Some MCP servers don't require initialize, continue anyway
            pass
        
        # Send initialized notification (no response expected)
        try:
            await self.send_notification("notifications/initialized", {})
        except:
            pass
        
        # List available tools
        try:
            tools_result = await self.call_method("tools/list", {})
            if tools_result and "tools" in tools_result:
                self.tools = tools_result["tools"]
        except Exception as e:
            # Fallback: try without params or different format
            try:
                tools_result = await self.call_method("tools/list", None)
                if tools_result and "tools" in tools_result:
                    self.tools = tools_result["tools"]
            except:
                # Server may expose tools differently, continue with empty list
                pass
        
        return {
            "mode": self.mode.value,
            "tools_available": len(self.tools),
            "tools": [t.get("name") for t in self.tools]
        }
    
    def _read_responses_sync(self):
        """Background thread to read responses from MCP server (synchronous)."""
        try:
            while self._running:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                try:
                    # Decode bytes to string
                    line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                    response = json.loads(line_str)
                    
                    # Put response in queue for async processing
                    self._response_queue.put(response)
                    
                except json.JSONDecodeError:
                    # Skip non-JSON lines (e.g., debug output, telemetry)
                    continue
                except Exception as e:
                    print(f"[MCP Client] Error processing response: {e}", file=sys.stderr)
        
        except Exception as e:
            print(f"[MCP Client] Error in read thread: {e}", file=sys.stderr)
    
    def _log_stderr(self):
        """Background thread to log stderr from MCP server for debugging."""
        try:
            while self._running:
                line = self.process.stderr.readline()
                if not line:
                    break
                
                try:
                    # Decode and print stderr for debugging
                    line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                    # Only print important messages (errors, warnings)
                    line_lower = line_str.lower()
                    if any(keyword in line_lower for keyword in ['error', 'warning', 'failed', 'exception', 'timeout']):
                        print(f"[Browser-Use] {line_str.strip()}", file=sys.stderr)
                except Exception:
                    pass
        except Exception:
            pass
    
    async def _process_response(self, response: Dict[str, Any]):
        """Process a response from the queue."""
        if "id" in response and response["id"] in self.pending_requests:
            future = self.pending_requests.pop(response["id"])
            if "error" in response:
                future.set_exception(Exception(response["error"].get("message", "Unknown error")))
            else:
                future.set_result(response.get("result"))
    
    async def send_notification(self, method: str, params: Any) -> None:
        """
        Send a JSON-RPC notification (no response expected).
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
        """
        if not self.process or not self.process.stdin:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        
        # Build JSON-RPC notification (no id field)
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        # Send notification
        notification_line = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_line.encode('utf-8'))
        self.process.stdin.flush()
    
    async def call_method(self, method: str, params: Any) -> Any:
        """
        Call a JSON-RPC method on the MCP server.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            
        Returns:
            Method result
        """
        if not self.process or not self.process.stdin:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        
        # Generate unique request ID
        self.request_id += 1
        request_id = str(self.request_id)
        
        # Build JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }
        
        # Only add params if not None
        if params is not None:
            request["params"] = params
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        # Send request (encode to bytes for binary stream)
        request_line = json.dumps(request) + "\n"
        self.process.stdin.write(request_line.encode('utf-8'))
        self.process.stdin.flush()
        
        # Poll queue for response (with timeout)
        # Use longer timeout for agent tasks
        timeout = 300.0 if method == "tools/call" else 60.0
        
        try:
            start_time = asyncio.get_event_loop().time()
            while True:
                # Check if response arrived
                if not self._response_queue.empty():
                    response = self._response_queue.get()
                    await self._process_response(response)
                
                # Check if our future is done
                if future.done():
                    return future.result()
                
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    self.pending_requests.pop(request_id, None)
                    # Include params in error for debugging
                    params_str = json.dumps(params)[:100] if params else "none"
                    raise TimeoutError(f"Request {method} timeout after {timeout}s. Params: {params_str}")
                
                # Small delay to avoid busy-waiting
                await asyncio.sleep(0.01)
                
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            params_str = json.dumps(params)[:100] if params else "none"
            raise TimeoutError(f"Request {method} timed out. Params: {params_str}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a browser-use MCP tool.
        
        Args:
            tool_name: Name of the tool (e.g., "browser_navigate")
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        return await self.call_method("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
    
    # Convenience methods for common browser operations
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL."""
        return await self.call_tool("browser_navigate", {"url": url})
    
    async def get_state(self) -> Dict[str, Any]:
        """Get current page state (DOM + screenshot)."""
        return await self.call_tool("browser_get_state", {})
    
    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element."""
        return await self.call_tool("browser_click", {"selector": selector})
    
    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an element."""
        return await self.call_tool("browser_type", {
            "selector": selector,
            "text": text
        })
    
    async def scroll(self, direction: str = "down", amount: int = 500) -> Dict[str, Any]:
        """Scroll the page."""
        return await self.call_tool("browser_scroll", {
            "direction": direction,
            "amount": amount
        })
    
    async def go_back(self) -> Dict[str, Any]:
        """Go back in browser history."""
        return await self.call_tool("browser_go_back", {})
    
    async def extract_content(self, selector: Optional[str] = None) -> Dict[str, Any]:
        """Extract content from the page."""
        params = {}
        if selector:
            params["selector"] = selector
        return await self.call_tool("browser_extract_content", params)
    
    async def list_tabs(self) -> List[Dict[str, Any]]:
        """List all open tabs."""
        result = await self.call_tool("browser_list_tabs", {})
        return result.get("tabs", [])
    
    async def switch_tab(self, tab_id: str) -> Dict[str, Any]:
        """Switch to a specific tab."""
        return await self.call_tool("browser_switch_tab", {"tab_id": tab_id})
    
    async def close_tab(self, tab_id: str) -> Dict[str, Any]:
        """Close a tab."""
        return await self.call_tool("browser_close_tab", {"tab_id": tab_id})
    
    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all browser sessions."""
        result = await self.call_tool("browser_list_sessions", {})
        return result.get("sessions", [])
    
    async def close_session(self, session_id: str) -> Dict[str, Any]:
        """Close a browser session."""
        return await self.call_tool("browser_close_session", {"session_id": session_id})
    
    async def close_all(self) -> Dict[str, Any]:
        """Close all browser sessions."""
        return await self.call_tool("browser_close_all", {})
    
    async def run_agent_task(self, task: str) -> Dict[str, Any]:
        """
        Delegate a complex task to the autonomous browser agent.
        
        This is useful for multi-step tasks that would be tedious to script manually.
        The agent will use its LLM to figure out the steps needed to complete the task.
        
        Args:
            task: Natural language description of the task
            
        Returns:
            Task result from the agent
        """
        return await self.call_tool("retry_with_browser_use_agent", {"task": task})
    
    async def close(self):
        """Close the MCP client and terminate the server process."""
        try:
            # Try to close all browser sessions gracefully
            await self.close_all()
        except:
            pass
        
        # Stop the read thread
        self._running = False
        if hasattr(self, '_read_thread') and self._read_thread.is_alive():
            self._read_thread.join(timeout=2)
        
        # Close stdin
        if self.process and self.process.stdin:
            try:
                self.process.stdin.close()
            except:
                pass
        
        # Terminate process
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
    
    def __repr__(self):
        return f"BrowserUseMCPClient(mode={self.mode.value}, container={self.docker_container})"


# Example usage
async def example_usage():
    """Example of using the Browser-Use MCP client."""
    client = BrowserUseMCPClient(mode="docker", docker_container="browseruse-mcp")
    
    try:
        # Initialize
        print("Initializing MCP client...")
        init_result = await client.initialize()
        print(f"Connected! Tools available: {init_result['tools']}")
        
        # Navigate to a page
        print("\nNavigating to example.com...")
        await client.navigate("https://example.com")
        
        # Get page state
        print("\nGetting page state...")
        state = await client.get_state()
        print(f"Page title: {state.get('title', 'N/A')}")
        
        # Extract content
        print("\nExtracting heading...")
        content = await client.extract_content("h1")
        print(f"Heading content: {content}")
        
        # Use autonomous agent for complex task
        print("\nDelegating complex task to agent...")
        result = await client.run_agent_task(
            "Find the 'More information' link and tell me what it says"
        )
        print(f"Agent result: {result}")
        
    finally:
        print("\nClosing client...")
        await client.close()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())


