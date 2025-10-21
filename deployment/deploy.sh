#!/bin/bash
# Production Deployment Script for WHINT API AI Assistant

set -e

echo "🚀 WHINT API AI Assistant - Production Deployment"
echo "================================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
check_dependencies() {
    echo "Checking dependencies..."
    
    if ! command_exists python3; then
        echo "❌ Python 3 is required but not installed."
        exit 1
    fi
    
    if ! command_exists pip; then
        echo "❌ pip is required but not installed."
        exit 1
    fi
    
    echo "✅ Dependencies check passed"
}

# Setup virtual environment
setup_venv() {
    echo "Setting up virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -e .
    echo "✅ Virtual environment created"
}

# Setup environment variables
setup_env() {
    if [ ! -f .env ]; then
        echo "Creating .env file from template..."
        cp .env.example .env
        echo "⚠️  Please edit .env file with your API credentials before running the application"
        echo "   Required variables:"
        echo "   - WHINT_API_BASE_URL"
        echo "   - WHINT_API_X_API_KEY"
        echo "   - WHINT_USERNAME"
        echo "   - WHINT_PASSWORD"
        echo "   - OPENAI_API_KEY"
    else
        echo "✅ .env file already exists"
    fi
}

# Main deployment options
case "${1:-help}" in
    "local")
        echo "🏠 Local Production Setup"
        check_dependencies
        setup_venv
        setup_env
        echo ""
        echo "🎉 Local setup complete!"
        echo "To run the application:"
        echo "  source venv/bin/activate"
        echo "  streamlit run app.py --server.port 8501"
        ;;
    
    "docker")
        echo "🐳 Docker Deployment"
        if ! command_exists docker; then
            echo "❌ Docker is required but not installed."
            exit 1
        fi
        
        setup_env
        echo "Building Docker image..."
        docker build -t whint-ai-assistant .
        echo ""
        echo "🎉 Docker build complete!"
        echo "To run with Docker:"
        echo "  docker run -p 8501:8501 --env-file .env whint-ai-assistant"
        echo "Or use Docker Compose:"
        echo "  docker-compose up -d"
        ;;
    
    "cloud")
        echo "☁️  Cloud Deployment Files Created"
        echo "Available cloud deployment options:"
        echo ""
        echo "1. AWS ECS/Fargate:"
        echo "   - Use the Dockerfile provided"
        echo "   - Set environment variables in ECS task definition"
        echo ""
        echo "2. Google Cloud Run:"
        echo "   - gcloud run deploy --source . --platform managed"
        echo ""
        echo "3. Azure Container Instances:"
        echo "   - Use Docker image with Azure Container Instances"
        echo ""
        echo "4. Heroku:"
        echo "   - Add Procfile for Heroku deployment"
        echo ""
        setup_env
        ;;
    
    "export")
        echo "📦 Exporting Production Files"
        
        # Create deployment package
        mkdir -p dist/whint-ai-assistant
        
        # Copy core application files
        cp app.py dist/whint-ai-assistant/
        cp *.py dist/whint-ai-assistant/ 2>/dev/null || true
        cp pyproject.toml dist/whint-ai-assistant/
        cp Dockerfile dist/whint-ai-assistant/
        cp docker-compose.yml dist/whint-ai-assistant/
        cp .env.example dist/whint-ai-assistant/
        cp deploy.sh dist/whint-ai-assistant/
        
        # Create README for deployment
        cat > dist/whint-ai-assistant/README.md << 'EOF'
# WHINT API AI Assistant - Production Deployment

## Quick Start

1. Copy `.env.example` to `.env` and configure your API credentials
2. Choose your deployment method:

### Local Deployment
```bash
./deploy.sh local
source venv/bin/activate
streamlit run app.py --server.port 8501
```

### Docker Deployment
```bash
./deploy.sh docker
docker-compose up -d
```

### Manual Setup
```bash
pip install -e .
streamlit run app.py --server.port 8501
```

## Configuration

Edit `.env` file with your credentials:
- WHINT_API_BASE_URL
- WHINT_API_X_API_KEY  
- WHINT_USERNAME
- WHINT_PASSWORD
- OPENAI_API_KEY

## Access

Once running, access the application at: http://localhost:8501
EOF
        
        echo "✅ Production files exported to: dist/whint-ai-assistant/"
        echo ""
        echo "Package contents:"
        ls -la dist/whint-ai-assistant/
        ;;
    
    *)
        echo "Usage: $0 {local|docker|cloud|export}"
        echo ""
        echo "Deployment Options:"
        echo "  local  - Set up local production environment"
        echo "  docker - Build Docker image for containerized deployment"
        echo "  cloud  - Show cloud deployment guidance"
        echo "  export - Export all files for production deployment"
        echo ""
        echo "Examples:"
        echo "  $0 local   # Set up local production environment"
        echo "  $0 docker  # Build Docker container"
        echo "  $0 export  # Create deployment package"
        ;;
esac