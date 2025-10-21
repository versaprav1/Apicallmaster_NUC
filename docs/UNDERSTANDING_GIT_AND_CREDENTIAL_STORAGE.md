# Understanding Git and Credential Storage Options

## What is the .git Folder?

The `.git` folder is a hidden directory that contains all the version control information for your project. Think of it as the "memory" of your project that tracks all changes over time.

### What Git Does:
- **Version Control**: Tracks every change you make to your code
- **History**: Keeps a complete history of all modifications
- **Backup**: Acts as a distributed backup system
- **Collaboration**: Allows multiple developers to work on the same project
- **Rollback**: Lets you go back to any previous version

### What's Inside .git Folder:
```
.git/
├── objects/        # Stores all your file versions
├── refs/           # Stores branch and tag information  
├── logs/           # Keeps logs of all changes
├── config          # Git configuration for this project
├── HEAD            # Points to current branch
└── index           # Staging area for changes
```

### Why Git is Helpful for Your WHINT Assistant:

1. **Track Changes**: See exactly what changed in your code between versions
2. **Experimentation**: Try new features without fear of breaking working code
3. **Deployment History**: Track which version is deployed where
4. **Collaboration**: Share your project with team members safely
5. **Backup**: Your code is backed up with full history

### Basic Git Commands:
```bash
# Check status of your project
git status

# Save changes with a message
git add .
git commit -m "Added credential storage options"

# See history of changes
git log --oneline

# Go back to a previous version
git checkout <commit-hash>

# Create a new branch for experiments
git branch new-feature
git checkout new-feature
```

## Comprehensive Credential Storage Options

Your WHINT AI Assistant now supports multiple ways to store credentials so you don't have to enter them every time:

### Option 1: Session Storage (Default)
**How it works**: Credentials stored in browser memory only
**Duration**: Until you close the browser/app
**Security**: High (no files created)
**Best for**: Testing, one-time use

### Option 2: .env File Storage
**How it works**: Automatically saves credentials to `.env` file
**Duration**: Permanent until you delete the file
**Security**: Medium (local file only)
**Best for**: Local development, personal use

**What happens**:
- App creates/updates `.env` file with your credentials
- Future app starts automatically load from this file
- File is ignored by Git (won't be accidentally shared)

### Option 3: Streamlit Secrets
**How it works**: Uses Streamlit's built-in secrets management
**Duration**: Permanent
**Security**: High (encrypted in production)
**Best for**: Production deployments

**Setup**:
1. Create `.streamlit/secrets.toml` file
2. Add your credentials in TOML format
3. App automatically detects and uses them

Example secrets.toml:
```toml
[whint_api]
base_url = "https://whint.prod.apimanagement.eu10.hana.ondemand.com:443/wic"
x_api_key = "your_api_key"
username = "your_username"
password = "your_password"

[openai]
api_key = "your_openai_key"
```

### Option 4: System Environment Variables
**How it works**: Set credentials globally on your computer/server
**Duration**: Permanent until removed
**Security**: High (system-level protection)
**Best for**: Production servers, shared environments

**Setup**:
```bash
# Linux/Mac
export WHINT_API_BASE_URL="https://whint.prod.apimanagement.eu10.hana.ondemand.com:443/wic"
export WHINT_API_X_API_KEY="your_api_key"
export WHINT_USERNAME="your_username"
export WHINT_PASSWORD="your_password"
export OPENAI_API_KEY="your_openai_key"

# Windows
set WHINT_API_BASE_URL=https://whint.prod.apimanagement.eu10.hana.ondemand.com:443/wic
set WHINT_API_X_API_KEY=your_api_key
# ... etc
```

## Credential Loading Priority

The app checks for credentials in this order:

1. **System Environment Variables** (highest priority)
2. **Streamlit Secrets** (.streamlit/secrets.toml)
3. **Local .env File** (python-dotenv)
4. **Manual Entry** (user input)

This means if you have credentials in multiple places, system environment variables will be used first.

## Security Best Practices

### Do Store:
- Credentials in .env files for local development
- Secrets in Streamlit secrets for production
- Environment variables on secure servers

### Don't Store:
- Credentials in your source code
- Credentials in Git repositories
- Credentials in public files or documentation

### Protection Measures:
- `.env` files are automatically added to `.gitignore`
- Streamlit secrets are encrypted in production
- System environment variables are protected by OS security

## Troubleshooting Common Issues

### "Credentials not loading from .env"
- Check file is named exactly `.env` (no extension)
- Ensure no extra spaces around the `=` sign
- Verify file is in the same directory as `app.py`

### "Streamlit secrets not working"
- Check file path: `.streamlit/secrets.toml`
- Verify TOML syntax is correct
- Ensure proper section names `[whint_api]` and `[openai]`

### "Environment variables not found"
- Restart your terminal/command prompt after setting
- Check spelling of variable names (case-sensitive)
- Use `echo $VARIABLE_NAME` (Linux/Mac) or `echo %VARIABLE_NAME%` (Windows) to verify

### "App keeps asking for credentials"
- Check which storage method you selected
- Verify credentials are actually saved in chosen location
- Look for error messages in the app interface

## Migration Between Storage Methods

### From Session to .env File:
1. Select "Save to .env File" option
2. Enter credentials and connect
3. App automatically creates .env file

### From .env to Streamlit Secrets:
1. Create `.streamlit/secrets.toml` file
2. Copy credentials from .env to secrets.toml (convert format)
3. Select "Use Streamlit Secrets" option

### From Local to Production:
1. Use environment variables on production server
2. Or use Streamlit Cloud secrets management
3. Never copy .env files to production servers

## Git Integration and Credential Safety

### Files Automatically Protected:
- `.env` - Added to .gitignore
- `.streamlit/secrets.toml` - Added to .gitignore
- Any file with "secret", "key", or "password" in name

### Safe Git Practices:
```bash
# Always check what you're committing
git status
git diff

# Never commit these files
git add .env                    # ❌ Don't do this
git add .streamlit/secrets.toml # ❌ Don't do this

# Safe commits
git add app.py                  # ✅ Safe
git add README.md              # ✅ Safe
git commit -m "Updated features"
```

### Emergency: Accidentally Committed Secrets
```bash
# Remove from Git history (before pushing)
git rm --cached .env
git commit -m "Remove secrets file"

# If already pushed, rotate all API keys immediately
# Then remove from history and force push (dangerous)
```

## Summary

You now have four flexible options for credential storage:

1. **Session Only**: Perfect for testing
2. **.env File**: Great for local development  
3. **Streamlit Secrets**: Ideal for production
4. **Environment Variables**: Best for servers

The app automatically detects and uses credentials from any of these sources, with system environment variables taking highest priority. Your credentials are protected from accidental sharing through Git, and you can choose the method that best fits your deployment scenario.