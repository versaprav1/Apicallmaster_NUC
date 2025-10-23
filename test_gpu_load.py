"""
Test script to verify Ollama model loads fully on GPU with optimized settings.
"""

import requests
import subprocess
import time

print("=" * 70)
print("🎮 TESTING FULL GPU LOADING")
print("=" * 70)

# Force unload existing model
print("\n1️⃣ Unloading existing model...")
subprocess.run(['ollama', 'stop', 'llama3.2:latest'], capture_output=True)
time.sleep(2)

# Test with optimized GPU settings
print("\n2️⃣ Sending request with optimized GPU settings...")
test_payload = {
    "model": "llama3.2:latest",
    "prompt": "Hello! Say 'GPU test successful' if you can read this.",
    "stream": False,
    "options": {
        "temperature": 0.1,
        "num_predict": 50,
        "num_gpu": 99,  # All layers on GPU
        "num_thread": 4,  # Lower CPU threads
        "use_mmap": True,
        "use_mlock": False,
        "num_ctx": 4096,
    }
}

try:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json=test_payload,
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Response: {result.get('response', '')[:100]}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Error: {e}")

# Check GPU usage
print("\n3️⃣ Checking GPU distribution...")
time.sleep(2)  # Wait for model to settle

result = subprocess.run(['ollama', 'ps'], capture_output=True, text=True)
print(result.stdout)

# Parse the output
if '100% GPU' in result.stdout:
    print("\n✅✅✅ SUCCESS! Model is 100% on GPU! ✅✅✅")
elif 'GPU' in result.stdout:
    # Extract the percentage
    lines = result.stdout.split('\n')
    for line in lines:
        if 'llama3.2' in line:
            print(f"\n📊 GPU Status: {line}")
            if '/' in line:
                parts = line.split()
                for part in parts:
                    if 'CPU/GPU' in part or 'GPU' in part:
                        print(f"   Distribution: {part}")
else:
    print("\n⚠️  Model may be on CPU")

print("\n" + "=" * 70)

