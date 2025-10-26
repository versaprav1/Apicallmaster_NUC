"""
Test Ollama connection from this machine to diagnose the issue.
"""

import requests
import socket
import time

print("=" * 70)
print("🔍 OLLAMA CONNECTION DIAGNOSTIC")
print("=" * 70)

# ============================================================================
# 1. CHECK LOCAL MACHINE INFO
# ============================================================================
print("\n1️⃣ Machine Information:")
print("-" * 70)
print(f"  Hostname: {socket.gethostname()}")
print(f"  Running from: {__file__ if '__file__' in dir() else 'interactive'}")

# ============================================================================
# 2. TEST OLLAMA API CONNECTION
# ============================================================================
print("\n2️⃣ Testing Ollama API Connection...")
print("-" * 70)

url = "http://localhost:11434/api/tags"
print(f"  Testing: {url}")

try:
    start = time.time()
    response = requests.get(url, timeout=5)
    elapsed = time.time() - start
    
    if response.status_code == 200:
        print(f"  ✅ Connection successful! ({elapsed:.2f}s)")
        
        data = response.json()
        models = data.get('models', [])
        print(f"\n  📦 Available models: {len(models)}")
        for model in models:
            name = model.get('name', 'unknown')
            size = model.get('size', 0) / (1024**3)
            print(f"    • {name} ({size:.1f} GB)")
    else:
        print(f"  ❌ HTTP {response.status_code}: {response.text}")
        
except requests.exceptions.Timeout:
    print(f"  ❌ Connection timed out after 5 seconds")
    print(f"     This suggests Ollama is not responding on this machine")
    
except requests.exceptions.ConnectionError as e:
    print(f"  ❌ Connection refused: {e}")
    print(f"     Ollama is not running on THIS machine at localhost:11434")
    
except Exception as e:
    print(f"  ❌ Error: {e}")

# ============================================================================
# 3. TEST GENERATE ENDPOINT WITH SHORT TIMEOUT
# ============================================================================
print("\n3️⃣ Testing Generate Endpoint (10s timeout)...")
print("-" * 70)

try:
    payload = {
        "model": "mistral-nemo:latest",
        "prompt": "Say 'test' and nothing else.",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 10
        }
    }
    
    print(f"  Sending request to mistral-nemo:latest...")
    start = time.time()
    
    response = requests.post(
        "http://localhost:11434/api/generate",
        json=payload,
        timeout=10  # Short timeout for testing
    )
    
    elapsed = time.time() - start
    
    if response.status_code == 200:
        result = response.json()
        response_text = result.get("response", "")
        print(f"  ✅ Generate works! ({elapsed:.2f}s)")
        print(f"     Response: {response_text[:100]}")
    else:
        print(f"  ❌ HTTP {response.status_code}: {response.text}")
        
except requests.exceptions.Timeout:
    elapsed = time.time() - start
    print(f"  ⚠️  Request timed out after {elapsed:.1f}s")
    print(f"     This is the PROBLEM! Ollama is not responding to generate requests")
    print(f"     from THIS machine within reasonable time.")
    print(f"\n  💡 Possible causes:")
    print(f"     1. Ollama is running on a DIFFERENT machine")
    print(f"     2. Network/firewall blocking the connection")
    print(f"     3. Ollama API server not started (only CLI works)")
    print(f"     4. Model is stuck or overloaded")
    
except requests.exceptions.ConnectionError as e:
    print(f"  ❌ Connection refused: {e}")
    print(f"     Ollama is NOT accessible from this machine")
    
except Exception as e:
    print(f"  ❌ Error: {e}")

# ============================================================================
# 4. CHECK ALTERNATIVE HOSTS
# ============================================================================
print("\n4️⃣ Checking Alternative Connection Methods...")
print("-" * 70)

# Try different host variations
hosts_to_try = [
    "http://127.0.0.1:11434/api/tags",
    "http://localhost:11434/api/tags",
]

for host_url in hosts_to_try:
    try:
        response = requests.get(host_url, timeout=2)
        if response.status_code == 200:
            print(f"  ✅ {host_url} - Works!")
        else:
            print(f"  ❌ {host_url} - HTTP {response.status_code}")
    except requests.exceptions.Timeout:
        print(f"  ⏱️  {host_url} - Timeout")
    except requests.exceptions.ConnectionError:
        print(f"  ❌ {host_url} - Connection refused")
    except Exception as e:
        print(f"  ❌ {host_url} - {str(e)[:50]}")

# ============================================================================
# DIAGNOSIS
# ============================================================================
print("\n" + "=" * 70)
print("📋 DIAGNOSIS")
print("=" * 70)

print("""
Based on your error (300-second timeout):

The issue is that:
✅ Ollama IS running (you confirmed with `ollama ps`)
✅ Model IS loaded (mistral-nemo:latest on 100% GPU)
❌ But the Streamlit app CANNOT connect to it

Possible reasons:

1. **Different Machines**:
   - You checked `ollama ps` on machine A (C:\\Users\\trans)
   - Streamlit app is running on machine B
   - Machine B's "localhost" ≠ Machine A's "localhost"
   
   FIX: Set OLLAMA_HOST in app to point to correct machine:
        OLLAMA_BASE_URL=http://192.168.1.x:11434

2. **Firewall Blocking**:
   - Windows Firewall blocking port 11434
   
   FIX: Allow port 11434 in Windows Firewall

3. **Ollama API Not Started**:
   - CLI works but API server isn't running
   
   FIX: Restart Ollama: ollama serve

4. **Network Interface**:
   - Ollama listening on specific interface, not all
   
   FIX: Set OLLAMA_HOST=0.0.0.0 when starting Ollama

Run this script ON THE SAME MACHINE as your Streamlit app to diagnose!
""")

print("=" * 70)

