"""
Force Ollama models to reload with GPU acceleration.
This script unloads CPU-loaded models and forces GPU usage.
"""

import subprocess
import requests
import time
import os

print("=" * 70)
print("🔄 FORCE GPU RELOAD FOR OLLAMA MODELS")
print("=" * 70)

# ============================================================================
# 1. CHECK CURRENT STATUS
# ============================================================================
print("\n1️⃣ Current model status:")
print("-" * 70)

try:
    result = subprocess.run(['ollama', 'ps'], capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout)
        
        if 'CPU' in result.stdout:
            print("⚠️  Models are running on CPU - will fix this!")
        elif 'GPU' in result.stdout:
            print("✅ Models already on GPU - you're good!")
            exit(0)
    else:
        print(f"❌ Error: {result.stderr}")
        exit(1)
except Exception as e:
    print(f"❌ Error checking status: {e}")
    exit(1)

# ============================================================================
# 2. UNLOAD ALL MODELS
# ============================================================================
print("\n2️⃣ Unloading all models to clear CPU cache...")
print("-" * 70)

# Get list of currently loaded models
loaded_models = []
try:
    result = subprocess.run(['ollama', 'ps'], capture_output=True, text=True)
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:  # Skip header
            for line in lines[1:]:
                if line.strip():
                    # Parse model name (first column)
                    parts = line.split()
                    if parts:
                        model_name = parts[0]
                        loaded_models.append(model_name)
                        print(f"  Found loaded model: {model_name}")
except Exception as e:
    print(f"❌ Error getting loaded models: {e}")

# Unload each model
for model in loaded_models:
    try:
        print(f"\n  Unloading {model}...")
        result = subprocess.run(['ollama', 'stop', model], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"  ✅ Unloaded {model}")
        else:
            print(f"  ⚠️  {result.stderr.strip() if result.stderr else 'Already unloaded'}")
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Timeout unloading {model}")
    except Exception as e:
        print(f"  ⚠️  Error: {e}")

# Wait for models to fully unload
print("\n  Waiting 3 seconds for cleanup...")
time.sleep(3)

# ============================================================================
# 3. VERIFY UNLOAD
# ============================================================================
print("\n3️⃣ Verifying models are unloaded...")
print("-" * 70)

try:
    result = subprocess.run(['ollama', 'ps'], capture_output=True, text=True)
    if result.returncode == 0:
        output = result.stdout.strip()
        lines = [l for l in output.split('\n') if l.strip()]
        
        if len(lines) <= 1:  # Only header
            print("✅ All models unloaded successfully!")
        else:
            print("⚠️  Some models still loaded:")
            print(output)
except Exception as e:
    print(f"❌ Error: {e}")

# ============================================================================
# 4. TEST GPU RELOAD
# ============================================================================
print("\n4️⃣ Testing GPU reload with deepseek-r1:14b...")
print("-" * 70)

# Check if model exists
model_to_test = "deepseek-r1:14b"
try:
    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
    if model_to_test not in result.stdout:
        print(f"⚠️  {model_to_test} not found, trying granite3.3:8b instead...")
        model_to_test = "granite3.3:8b"
        
        if model_to_test not in result.stdout:
            print("❌ No compatible models found!")
            print("Available models:")
            print(result.stdout)
            exit(1)
except Exception as e:
    print(f"⚠️  Could not check model list: {e}")

print(f"\nSending test request to {model_to_test} with GPU config...")

# Create request with GPU settings
num_gpu = int(os.getenv("OLLAMA_NUM_GPU", "1"))
num_threads = int(os.getenv("OLLAMA_NUM_THREADS", "4"))  # Lower threads for GPU

payload = {
    "model": model_to_test,
    "prompt": "Say 'GPU test successful' and nothing else.",
    "stream": False,
    "options": {
        "temperature": 0.1,
        "num_predict": 20,
        "num_gpu": num_gpu,  # Force GPU usage
        "num_thread": num_threads,  # Fewer CPU threads
        "use_mmap": True,
        "use_mlock": False,
    }
}

try:
    print(f"  GPU config: num_gpu={num_gpu}, num_thread={num_threads}")
    
    response = requests.post(
        "http://localhost:11434/api/generate",
        json=payload,
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        response_text = result.get("response", "").strip()
        
        print(f"\n✅ Request completed!")
        print(f"  Response: {response_text}")
        
        # Wait a moment for model to fully load
        time.sleep(2)
        
        # Check GPU usage
        print(f"\n5️⃣ Checking GPU usage...")
        print("-" * 70)
        
        ps_result = subprocess.run(['ollama', 'ps'], capture_output=True, text=True)
        if ps_result.returncode == 0:
            print(ps_result.stdout)
            
            if '100% GPU' in ps_result.stdout:
                print("\n" + "=" * 70)
                print("✅✅✅ SUCCESS! MODEL NOW RUNNING ON GPU! ✅✅✅")
                print("=" * 70)
                print("\nYour GPU is now being utilized! 🎉")
                print("The model will stay on GPU until you unload it.")
            elif 'GPU' in ps_result.stdout:
                print("\n✅ Partial GPU usage detected")
                print("Some layers may be on CPU if VRAM is limited")
            else:
                print("\n⚠️  Still showing CPU usage")
                print("\nPossible reasons:")
                print("  1. Not enough VRAM for this model")
                print("  2. GPU drivers not properly installed")
                print("  3. Ollama not configured for GPU")
                print("\nTry these fixes:")
                print("  • Check GPU memory: nvidia-smi")
                print("  • Restart Ollama service")
                print("  • Try smaller model: ollama run llama3.2:3b")
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"  Error: {response.text}")
        
except requests.exceptions.Timeout:
    print("⚠️  Request timed out - model may be loading on GPU (this can take time)")
    print("  Check status with: ollama ps")
except Exception as e:
    print(f"❌ Error: {e}")

# ============================================================================
# FINAL STATUS
# ============================================================================
print("\n" + "=" * 70)
print("📊 FINAL STATUS")
print("=" * 70)

try:
    result = subprocess.run(['ollama', 'ps'], capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout)
        
        # Also show GPU memory usage if NVIDIA
        print("\n🎮 GPU Memory Status:")
        print("-" * 70)
        try:
            gpu_result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'], 
                                       capture_output=True, text=True, timeout=5)
            if gpu_result.returncode == 0:
                used, total = gpu_result.stdout.strip().split(',')
                used_gb = float(used) / 1024
                total_gb = float(total) / 1024
                percent = (float(used) / float(total)) * 100
                print(f"VRAM Usage: {used_gb:.1f} GB / {total_gb:.1f} GB ({percent:.1f}%)")
                
                if used_gb > 1:
                    print("✅ GPU VRAM is being used!")
                else:
                    print("⚠️  Low VRAM usage - model may still be on CPU")
        except:
            print("(nvidia-smi not available)")
            
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 70)
print("💡 TIP: Your Streamlit app will now use GPU for new requests!")
print("=" * 70)


