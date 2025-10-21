# API Key Setup Guide

## How to Add LLM Provider API Keys

### 1. Access the Credentials Page
- Open the WHINT AI Assistant
- Go to the credentials page (first screen when not authenticated)
- Scroll down to "AI Provider Settings"

### 2. Available Providers and Where to Get Keys

#### OpenAI (GPT-4O, GPT-4O Mini - 128k context)
- **Get API Key**: https://platform.openai.com/api-keys
- **Cost**: $15/1M input tokens, $60/1M output tokens
- **Best For**: General purpose, reliable performance

#### Google Gemini (2M context - Best for large responses)
- **Get API Key**: https://aistudio.google.com/app/apikey
- **Cost**: $0.25/1M input tokens (Flash), $1.25/1M input tokens (Pro)
- **Best For**: Ultra-large responses without chunking

#### Anthropic Claude (200k context)
- **Get API Key**: https://console.anthropic.com/
- **Cost**: $15/1M input tokens, $75/1M output tokens
- **Best For**: Complex reasoning, code analysis

#### Groq (Fast inference)
- **Get API Key**: https://console.groq.com/keys
- **Cost**: $0.59/1M tokens (70B), $0.05/1M tokens (8B)
- **Best For**: Speed-critical applications

#### OpenRouter (Access to many models)
- **Get API Key**: https://openrouter.ai/keys
- **Cost**: Varies by model ($0.14-$5.4/1M tokens)
- **Best For**: Cost optimization, model variety

### 3. Model Selection Options

#### Automatic Selection (Recommended)
- Choose "Auto-select best model"
- System prioritizes high-context models for large responses
- Falls back to chunking if no suitable model available

#### Manual Selection
- Pick specific provider:model combination
- Example: "google:gemini-2.0-flash" for 2M context
- Example: "groq:llama-3.1-8b-instant" for speed

### 4. High-Context Model Recommendations

**For Large API Responses (avoid chunking):**
1. **Google Gemini 2.0 Flash** - 2M context, fast, cost-effective
2. **Google Gemini 2.0 Pro** - 2M context, advanced reasoning
3. **Anthropic Claude 3.5 Sonnet** - 200k context, excellent quality

**For Speed:**
1. **Groq Llama 3.1 8B** - Ultra-fast inference
2. **Groq Llama 3.1 70B** - Fast with better quality

**For Cost Efficiency:**
1. **OpenRouter DeepSeek** - $0.14/1M tokens
2. **GPT-4O Mini** - $1.5/1M tokens
3. **Gemini 2.0 Flash** - $0.25/1M tokens

### 5. Provider Status Check
- Enable "Show Provider Status" checkbox
- See which providers are available
- Check model counts and descriptions

### 6. Credential Storage
- **Session Only**: Keys stored until you close the app
- **Save to .env File**: Permanent local storage
- **Streamlit Secrets**: For production deployments
- **Manual Entry**: Enter each time