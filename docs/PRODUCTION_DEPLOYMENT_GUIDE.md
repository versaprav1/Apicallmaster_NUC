# WHINT API AI Assistant - Complete Production Deployment Guide

## What is the "dist" folder and How to Use It

### Understanding the Deployment Package

The `dist/whint-ai-assistant/` folder contains a complete, ready-to-deploy copy of your application. Think of it as a "package" that contains everything needed to run your WHINT AI Assistant on any server or cloud platform.

**What's inside the dist folder:**
```
dist/whint-ai-assistant/
├── app.py                 # Main application file
├── auth_manager.py        # Handles API authentication
├── inventory_types.py     # WHINT inventory type mappings
├── nlp_processor.py       # AI language processing
├── query_builder.py       # API query construction
├── whint_api.py          # WHINT API client
├── pyproject.toml        # Python dependencies
├── Dockerfile            # Docker container instructions
├── docker-compose.yml    # Multi-container setup
├── kubernetes.yaml       # Kubernetes deployment config
├── Procfile             # Heroku deployment config
├── .env.example         # Environment variables template
├── deploy.sh            # Automated deployment script
└── README.md            # Quick start instructions
```

## Step-by-Step Deployment Options for Beginners

### Option 1: Local Computer Setup (Easiest for Beginners)

**What you need:**
- A computer with Python 3.11 or newer
- Internet connection
- Your WHINT and OpenAI API credentials

**Step-by-step process:**

1. **Copy the deployment package to your computer**
   ```bash
   # Copy the entire dist/whint-ai-assistant folder to your desired location
   cp -r dist/whint-ai-assistant /path/to/your/deployment
   cd /path/to/your/deployment/whint-ai-assistant
   ```

2. **Set up your credentials**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit the .env file with your actual credentials
   nano .env  # or use any text editor
   ```
   
   Replace the placeholders with your real values:
   ```env
   WHINT_API_BASE_URL=https://whint.prod.apimanagement.eu10.hana.ondemand.com:443/wic
   WHINT_API_X_API_KEY=your_actual_api_key
   WHINT_USERNAME=your_whint_username
   WHINT_PASSWORD=your_whint_password
   OPENAI_API_KEY=your_openai_api_key
   ```

3. **Run the automated setup**
   ```bash
   # Make the deployment script executable
   chmod +x deploy.sh
   
   # Run local deployment setup
   ./deploy.sh local
   ```
   
   This will:
   - Check if Python is installed
   - Create a virtual environment
   - Install all dependencies
   - Set up the environment

4. **Start the application**
   ```bash
   # Activate the virtual environment
   source venv/bin/activate
   
   # Start the application
   streamlit run app.py --server.port 8501
   ```

5. **Access your application**
   - Open your web browser
   - Go to: `http://localhost:8501`
   - Your WHINT AI Assistant is now running!

**When to use this:** Perfect for testing, internal company use, or when you want to run it on your own computer/server.

### Option 2: Docker Deployment (Recommended for Production)

**What you need:**
- Docker installed on your computer/server
- Your WHINT and OpenAI API credentials

**Why Docker:** Docker packages your application with everything it needs to run, making it portable and consistent across different environments.

**Step-by-step process:**

1. **Prepare your environment**
   ```bash
   cd dist/whint-ai-assistant
   
   # Set up your credentials
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

2. **Build and run with Docker**
   ```bash
   # Build the Docker image
   ./deploy.sh docker
   
   # Run using Docker Compose (easier)
   docker-compose up -d
   ```

3. **Access your application**
   - Open browser to: `http://localhost:8501`

**Benefits:**
- Consistent environment everywhere
- Easy to move between servers
- Automatic restart if application crashes
- Easy to scale to multiple instances

**When to use this:** Production deployments, when you need reliability, or when deploying to cloud platforms.

### Option 3: Cloud Platform Deployment

#### Google Cloud Run (Easiest Cloud Option)

**What you need:**
- Google Cloud account
- Google Cloud SDK installed

**Step-by-step process:**

1. **Prepare your project**
   ```bash
   cd dist/whint-ai-assistant
   
   # Set up credentials in Google Cloud Console (not in .env file)
   ```

2. **Deploy to Google Cloud Run**
   ```bash
   # Login to Google Cloud
   gcloud auth login
   
   # Set your project
   gcloud config set project YOUR_PROJECT_ID
   
   # Deploy the application
   gcloud run deploy whint-ai-assistant \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

3. **Set environment variables in Google Cloud Console:**
   - Go to Google Cloud Console > Cloud Run
   - Select your service
   - Click "Edit & Deploy New Revision"
   - Add environment variables:
     - WHINT_API_BASE_URL
     - WHINT_API_X_API_KEY
     - WHINT_USERNAME
     - WHINT_PASSWORD
     - OPENAI_API_KEY

**Benefits:**
- Automatically scales based on traffic
- Only pay for what you use
- Managed by Google (no server maintenance)
- Global availability

#### Heroku (Simple Cloud Platform)

**What you need:**
- Heroku account
- Heroku CLI installed

**Step-by-step process:**

1. **Prepare for Heroku**
   ```bash
   cd dist/whint-ai-assistant
   
   # Initialize git repository
   git init
   git add .
   git commit -m "Initial deployment"
   ```

2. **Create and deploy Heroku app**
   ```bash
   # Login to Heroku
   heroku login
   
   # Create new app
   heroku create your-whint-assistant
   
   # Set environment variables
   heroku config:set WHINT_API_BASE_URL="https://whint.prod.apimanagement.eu10.hana.ondemand.com:443/wic"
   heroku config:set WHINT_API_X_API_KEY="your_api_key"
   heroku config:set WHINT_USERNAME="your_username"
   heroku config:set WHINT_PASSWORD="your_password"
   heroku config:set OPENAI_API_KEY="your_openai_key"
   
   # Deploy
   git push heroku main
   ```

3. **Access your app**
   - Heroku will provide a URL like: `https://your-whint-assistant.herokuapp.com`

### Option 4: Enterprise Kubernetes Deployment

**What you need:**
- Kubernetes cluster access
- kubectl command-line tool
- Understanding of Kubernetes concepts

**Step-by-step process:**

1. **Prepare Kubernetes configuration**
   ```bash
   cd dist/whint-ai-assistant
   
   # Edit kubernetes.yaml with your actual credentials
   nano kubernetes.yaml
   ```

2. **Deploy to Kubernetes**
   ```bash
   # Apply the configuration
   kubectl apply -f kubernetes.yaml
   
   # Check deployment status
   kubectl get pods
   kubectl get services
   ```

**Benefits:**
- High availability and scaling
- Enterprise-grade features
- Load balancing
- Health monitoring

**When to use:** Large organizations, high-traffic applications, when you need advanced features like auto-scaling.

## Troubleshooting Common Issues

### 1. "Python not found" Error
**Solution:** Install Python 3.11 or newer from python.org

### 2. "Permission denied" on deploy.sh
**Solution:** 
```bash
chmod +x deploy.sh
```

### 3. "Port 8501 already in use"
**Solution:** 
```bash
# Kill existing process
pkill -f streamlit
# Or use a different port
streamlit run app.py --server.port 8502
```

### 4. Authentication Errors
**Solution:** 
- Double-check your API credentials in .env file
- Ensure no extra spaces or quotes
- Test credentials separately using the "Test Connection" button

### 5. Docker not starting
**Solution:**
- Make sure Docker is installed and running
- Check Docker logs: `docker-compose logs`

## Security Best Practices

1. **Never commit .env files to version control**
2. **Use environment variables for all sensitive data**
3. **Regularly rotate API keys**
4. **Use HTTPS in production**
5. **Implement proper access controls**

## Monitoring and Maintenance

### Health Checks
All deployment options include health check endpoints at:
- `/_stcore/health` - Application health status

### Logs
- **Local:** Check terminal output
- **Docker:** `docker-compose logs -f`
- **Cloud platforms:** Use platform-specific logging tools

### Updates
To update your deployment:
1. Get new version of the application
2. Update the dist folder
3. Redeploy using the same method

## Getting Help

If you encounter issues:
1. Check the logs first
2. Verify your credentials
3. Ensure all dependencies are installed
4. Test with the simplest deployment option (local) first

## Summary of Deployment Options

| Option | Difficulty | Cost | Best For |
|--------|------------|------|----------|
| Local | Easy | Free | Testing, internal use |
| Docker | Medium | Low | Production, reliability |
| Google Cloud Run | Medium | Pay-per-use | Scalable production |
| Heroku | Easy | $7/month | Simple production |
| Kubernetes | Hard | Variable | Enterprise, high-scale |

Choose the option that best fits your technical expertise and requirements. Start with the local option to test everything works, then move to your preferred production deployment method.