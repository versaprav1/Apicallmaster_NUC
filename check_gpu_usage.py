"""
Quick script to verify GPU usage with Ollama.
Run this to confirm your GPU is being utilized.
"""

import subprocess
import requests
import json
import os

print("=" * 70)
print("🎮 GPU USAGE DIAGNOSTIC FOR OLLAMA")
print("=" * 70)

# ============================================================================
# 1. CHECK NVIDIA GPU
# ============================================================================
print("\n1️⃣ Checking NVIDIA GPU...")
print("-" * 70)

try:
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ NVIDIA GPU detected!")
        print("\nGPU Information:")
        # Show just the relevant lines
        for line in result.stdout.split('\n')[:15]:
            print(f"  {line}")
    else:
        print("❌ nvidia-smi failed")
        print("   If you have an NVIDIA GPU, install drivers and CUDA toolkit")
except FileNotFoundError:
    print("❌ nvidia-smi not found")
    print("   If you have an NVIDIA GPU, install NVIDIA drivers")
    print("   If you have AMD GPU, skip this - Ollama uses ROCm instead")
except Exception as e:
    print(f"❌ Error: {e}")

# ============================================================================
# 2. CHECK OLLAMA STATUS
# ============================================================================
print("\n\n2️⃣ Checking Ollama Status...")
print("-" * 70)

try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    
    if response.status_code == 200:
        print("✅ Ollama is running")
        
        data = response.json()
        models = data.get('models', [])
        print(f"\n📦 Loaded models: {len(models)}")
        
        for model in models[:5]:
            name = model.get('name', 'unknown')
            size = model.get('size', 0) / (1024**3)
            print(f"  • {name} ({size:.1f} GB)")
    else:
        print(f"❌ Ollama returned status {response.status_code}")
        
except Exception as e:
    print(f"❌ Cannot connect to Ollama: {e}")
    print("   Start Ollama with: ollama serve")

# ============================================================================
# 3. CHECK RUNNING MODELS (GPU USAGE)
# ============================================================================
print("\n\n3️⃣ Checking Currently Running Models (GPU Usage)...")
print("-" * 70)

try:
    result = subprocess.run(['ollama', 'ps'], capture_output=True, text=True)
    
    if result.returncode == 0:
        output = result.stdout.strip()
        
        if output and 'NAME' in output:
            print("📊 Active models:\n")
            print(output)
            
            # Check if GPU is being used
            if '100% GPU' in output or 'GPU' in output:
                print("\n✅ GPU IS BEING USED! 🎉")
            elif 'CPU' in output:
                print("\n⚠️  WARNING: Models running on CPU, not GPU!")
                print("   Possible fixes:")
                print("     1. Restart Ollama server")
                print("     2. Check if GPU has enough VRAM")
                print("     3. Verify CUDA/ROCm installation")
            else:
                print("\n❓ Cannot determine GPU usage from output")
        else:
            print("No models currently running")
            print("Models will load when you make a request")
    else:
        print(f"❌ Error running 'ollama ps': {result.stderr}")
        
except FileNotFoundError:
    print("❌ 'ollama' command not found")
    print("   Install Ollama from: https://ollama.ai")
except Exception as e:
    print(f"❌ Error: {e}")

# ============================================================================
# 4. TEST REQUEST WITH GPU CONFIG
# ============================================================================
print("\n\n4️⃣ Testing Request with GPU Configuration...")
print("-" * 70)

try:
    # Get environment variable settings
    num_gpu = os.getenv("OLLAMA_NUM_GPU", "1")
    num_threads = os.getenv("OLLAMA_NUM_THREADS", "8")
    
    print(f"Current settings:")
    print(f"  • OLLAMA_NUM_GPU: {num_gpu}")
    print(f"  • OLLAMA_NUM_THREADS: {num_threads}")
    
    test_payload = {
        "model": "deepseek-r1:14b",
        "prompt": "What is 2+2? Answer in one word.",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 50,
            "num_gpu": int(num_gpu),
            "num_thread": int(num_threads),
            "use_mmap": True,
            "use_mlock": False,
        }
    }
    
    print(f"\nSending test request to deepseek-r1:14b...")
    
    response = requests.post(
        "http://localhost:11434/api/generate",
        json=test_payload,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        response_text = result.get("response", "")
        total_duration = result.get("total_duration", 0) / 1e9  # Convert to seconds
        eval_duration = result.get("eval_duration", 0) / 1e9
        
        print(f"✅ Request successful!")
        print(f"   Response: {response_text[:100]}")
        print(f"   Total time: {total_duration:.2f}s")
        print(f"   Eval time: {eval_duration:.2f}s")
        
        # Now check if model loaded on GPU
        print(f"\n5️⃣ Verifying GPU usage after request...")
        result = subprocess.run(['ollama', 'ps'], capture_output=True, text=True)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            print(output)
            
            if '100% GPU' in output:
                print("\n✅✅✅ SUCCESS! Model is running on GPU! ✅✅✅")
            elif 'GPU' in output:
                print("\n✅ Model is using GPU (partial)")
            else:
                print("\n⚠️  Model may be on CPU")
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"   Error: {response.text}")
        
except Exception as e:
    print(f"❌ Error testing request: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("📋 TROUBLESHOOTING TIPS")
print("=" * 70)
print("""
If GPU is NOT being used:

1. Verify GPU drivers are installed:
   • NVIDIA: nvidia-smi should work
   • AMD: rocm-smi should work

2. Check VRAM availability:
   • deepseek-r1:14b needs ~8-10GB VRAM
   • Check with: nvidia-smi (look at Memory-Usage)

3. Environment variables (optional):
   • Set OLLAMA_NUM_GPU=1 in .env file (default: 1)
   • Set OLLAMA_NUM_THREADS=4 in .env file (lower = more GPU focus)

4. Restart Ollama:
   • Windows: Stop and start Ollama service
   • Linux/Mac: pkill ollama && ollama serve

5. Force GPU usage:
   • Unload model: ollama stop deepseek-r1:14b
   • Reload model: Make a new request

6. Check Ollama version:
   • ollama --version
   • Update if needed: Download from ollama.ai
""")
print("=" * 70)


