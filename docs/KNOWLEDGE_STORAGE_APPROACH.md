# Knowledge Storage Approach for WHINT API Assistant

## Overview

I've implemented a comprehensive knowledge storage system that caches processed API responses to avoid reprocessing large datasets. Here's how it works and how to use it:

## 1. How to Add API Keys and Select Models

### Adding API Keys
1. **Access Credentials Page**: When you first open the app, you'll see the credentials page
2. **Scroll to AI Provider Settings**: Below the WHINT API credentials
3. **Add Keys for Your Preferred Providers**:
   - **OpenAI**: General purpose, 128k context
   - **Google Gemini**: Best for large responses (2M context)
   - **Anthropic Claude**: Advanced reasoning (200k context)
   - **Groq**: Ultra-fast inference (131k context)
   - **OpenRouter**: Cost-effective access to many models

### Model Selection Options
- **Auto-select best model** (Recommended): System automatically chooses the best available model
- **Manual selection**: Pick specific provider:model combinations
- **Sidebar quick switch**: Change models during chat sessions

### Recommended Setup for Your Use Case
```
Priority 1: Google Gemini 2.0 Flash (2M context, $0.25/1M tokens)
Priority 2: Anthropic Claude 3.5 Sonnet (200k context, $15/1M tokens)  
Priority 3: Groq Llama 3.1 70B (131k context, fast inference)
```

## 2. Knowledge Storage System Features

### Automatic Caching
- **Query-based caching**: Each unique query+endpoint combination gets cached
- **7-day expiration**: Cached responses expire after 7 days
- **Chunk preservation**: Both raw responses and processed summaries are stored
- **Smart retrieval**: Similar queries automatically find related cached responses

### Cache Management
- **Real-time status**: Sidebar shows cache statistics
- **Search functionality**: Find cached responses by content
- **Cleanup tools**: Remove expired entries automatically
- **Size monitoring**: Track cache storage usage

### Intelligence Features
- **Similar query detection**: Finds related cached responses for new questions
- **Content search**: Search through cached summaries
- **Response reuse**: Avoid reprocessing identical or similar requests

## 3. Recommended Workflow

### Initial Setup
1. **Add Google Gemini API key** (highest priority for 2M context)
2. **Add Anthropic API key** (backup for complex reasoning)
3. **Add Groq API key** (for speed-critical queries)
4. **Select "Auto-select best model"** (system will prioritize high-context models)

### Daily Usage
1. **Ask questions normally** - system automatically caches responses
2. **Check sidebar cache stats** - see how much knowledge is accumulated
3. **Use cache search** - find previous analyses quickly
4. **Review similar queries** - system suggests related cached responses

### Large Response Handling
The system now has three approaches:
1. **High-context models**: Use Gemini 2M context to process entire response
2. **Intelligent chunking**: Break large responses into manageable pieces if needed
3. **Knowledge caching**: Store processed results to avoid reprocessing

## 4. Benefits of This Approach

### Performance
- **Instant responses** for previously asked questions
- **Reduced API costs** by avoiding duplicate processing
- **Faster iteration** on similar questions

### Intelligence
- **Accumulated knowledge** builds over time
- **Pattern recognition** across multiple queries
- **Contextual suggestions** based on cache history

### Cost Efficiency
- **Avoid redundant processing** of large datasets
- **Use cached summaries** for follow-up questions
- **Smart model selection** balances cost vs capability

## 5. Advanced Features

### Cache Search Examples
```
Search: "SAP interfaces" → Finds all cached SAP-related responses
Search: "failed connections" → Finds error-related analyses  
Search: "Azure Service Bus" → Finds Azure messaging responses
```

### Similar Query Detection
When you ask: "Show me MULE applications"
System suggests: "Previous analysis of MULE APIs from 2 days ago (150 items)"

### Model Auto-Selection Logic
1. **Estimate response size** from query complexity
2. **Check available high-context models** (Gemini 2M > Claude 200k > others)
3. **Select best model** that can handle the estimated load
4. **Fall back to chunking** if response exceeds even high-context limits

## 6. Getting Started

### Immediate Steps
1. **Get a Google Gemini API key** from https://aistudio.google.com/app/apikey
2. **Add it to the credentials page** under "Google Gemini API Key"
3. **Select "Auto-select best model"** for optimal performance
4. **Ask a large query** like "Show me all interfaces" to test the system

### Testing the Knowledge Storage
1. **Ask a complex question** that generates a large response
2. **Wait for processing and caching** (you'll see progress indicators)
3. **Ask the same question again** - should get instant response from cache
4. **Ask a similar question** - system will suggest related cached responses
5. **Check sidebar cache stats** to see accumulated knowledge

This approach ensures you never waste time reprocessing the same data while building an intelligent knowledge base that improves over time.