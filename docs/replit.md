# WHINT API AI Assistant

## Overview

This is a clean, simplified Streamlit-based AI assistant for the WHINT Integration Cockpit API. The application provides a streamlined interface where users input their API credentials and ask natural language questions. An AI agent analyzes the questions, creates appropriate API calls using the official WHINT documentation, executes GET requests to retrieve data, and provides structured responses based on the user's questions.

## System Architecture

### Application Architecture
- **Framework**: Streamlit web application with clean, minimal UI
- **Deployment**: Autoscale deployment on Replit platform (port 5000)
- **User Flow**: Credentials input → Natural language Q&A interface
- **AI Integration**: OpenAI GPT-4o for query translation and response analysis

### Core Workflow
1. **Credentials Page**: Simple form for API authentication details
2. **AI Agent Processing**: 
   - Analyzes user questions using WHINT API documentation
   - Creates appropriate JSON queries for the API
   - Executes GET requests to retrieve data
   - Analyzes responses and provides structured answers
3. **Session Management**: Maintains chat history and connection status

## Key Components

### Authentication Manager (`auth_manager.py`)
- Handles Bearer token and API key authentication
- Provides credential validation with caching (1-hour cache duration)
- Manages HTTP headers for API requests
- **Rationale**: Centralizes authentication logic and provides credential validation to ensure reliable API access

### WHINT API Client (`whint_api.py`)
- Core API communication layer
- Supports both single and paginated queries
- Implements proper error handling and timeout management
- **Rationale**: Abstracts API complexity and provides consistent interface for data retrieval

### Query Builder (`query_builder.py`)
- Constructs structured queries for WHINT API
- Supports complex filtering, sorting, and pagination
- Validates query parameters against supported entities and operators
- **Rationale**: Provides type-safe query construction and reduces API query errors

### NLP Processor (`nlp_processor.py`)
- Translates natural language queries to structured API queries
- Supports both OpenAI-based and rule-based translation
- Includes pattern matching for common query types
- **Rationale**: Enables non-technical users to query data using natural language

### Inventory Types (`inventory_types.py`)
- Defines mapping between inventory type IDs and names
- Supports 22 different inventory types (MULE, SAP, Azure, etc.)
- Provides utility functions for type validation and lookup
- **Rationale**: Ensures consistent handling of inventory types across the application

## Data Flow

1. **User Input**: Natural language query or structured query parameters
2. **Query Translation**: NLP processor converts natural language to API query
3. **Query Execution**: API client sends authenticated request to WHINT API
4. **Data Processing**: Response data is parsed and formatted
5. **Visualization**: Streamlit components display results to user
6. **Session Persistence**: Query history and results stored in session state

## External Dependencies

### Required APIs
- **WHINT Integration Cockpit API**: Primary data source
- **OpenAI API**: Natural language processing capabilities

### Python Libraries
- **streamlit**: Web application framework
- **requests**: HTTP client for API communication
- **openai**: OpenAI API integration
- **pandas**: Data manipulation and analysis

### Authentication Requirements
- WHINT API Base URL
- WHINT API Key (x-api-key header)
- WHINT Bearer Token
- OpenAI API Key (optional, for NLP features)

## Deployment Strategy

### Platform Configuration
- **Environment**: Replit with Python 3.11
- **Deployment Target**: Autoscale deployment
- **Process Management**: Streamlit server with custom port configuration

### Environment Variables
- Credentials can be provided via environment variables or Streamlit secrets
- Fallback mechanism ensures flexibility in deployment environments
- **Rationale**: Supports both development and production deployment scenarios

### Scaling Considerations
- Stateless application design enables horizontal scaling
- Session state management handles concurrent users
- API rate limiting considerations built into client

## Recent Changes

### July 4, 2025 - Multi-Provider LLM System with Knowledge Storage
- ✓ Implemented comprehensive multi-provider LLM system supporting 5 major providers
- ✓ Added support for high-context models (up to 2M tokens) to handle large API responses
- ✓ Created intelligent response chunking system as fallback for token limits
- ✓ Enhanced credentials page with individual API key fields for each provider
- ✓ Added automatic model selection based on context requirements and availability
- ✓ Implemented smart provider detection and status reporting
- ✓ Created endpoint routing system for all WHINT API types (SAP, MULE, AZURE, APIM)
- ✓ Implemented knowledge storage system to cache processed responses and avoid reprocessing
- ✓ Added intelligent cache management with search, cleanup, and similarity detection
- ✓ Created sidebar controls for model selection and cache management

### LLM Providers Supported
- **OpenAI**: GPT-4O, GPT-4O Mini (128k context)
- **Google Gemini**: 2.0 Flash, 2.0 Pro (2M context) - Ultra-high context for large responses
- **Anthropic**: Claude 3.5 Sonnet (200k context) - Advanced reasoning
- **Groq**: Llama 3.1 70B/8B (131k context) - Fast inference
- **OpenRouter**: DeepSeek Chat, Llama 405B (128k-131k context) - Cost-effective access

### Response Processing Features
- **Automatic Token Estimation**: Detects when responses exceed model limits
- **Intelligent Chunking**: Processes large responses in manageable pieces with progress tracking
- **High-Context Prioritization**: Automatically selects models with sufficient context to avoid chunking
- **Provider Fallback**: Graceful degradation when preferred providers are unavailable
- **Real-time Status**: Shows which providers are available and their capabilities

### June 26, 2025 - Comprehensive Credential Storage & Git Integration
- ✓ Implemented multiple credential storage options with priority loading system
- ✓ Added .env file auto-save functionality for persistent local storage
- ✓ Created Streamlit secrets integration for production deployments
- ✓ Enhanced credentials page with storage method selection and setup instructions
- ✓ Added system environment variable support with automatic detection
- ✓ Updated sidebar to show current storage method and credential management options
- ✓ Created comprehensive documentation explaining Git folder and credential security
- ✓ Added python-dotenv dependency for .env file support

## Environment Setup

### Required Environment Variables
```bash
# WHINT Integration Cockpit API
WHINT_API_BASE_URL=https://whint.prod.apimanagement.eu10.hana.ondemand.com:443/wic
WHINT_API_X_API_KEY=your_api_key_here
WHINT_USERNAME=your_username_here
WHINT_PASSWORD=your_password_here

# OpenAI for Natural Language Processing
OPENAI_API_KEY=your_openai_key_here
```

### Database Short Forms
The application now supports inventory type short forms as stored in the database:
- MLAPI → MULE_API
- GAP → APIM
- SIC → SAP_IS_CI
- And 19 other mappings for all inventory types

## User Preferences

Preferred communication style: Simple, everyday language.