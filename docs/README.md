# WHINT API AI Assistant

## Overview
This project is a Streamlit-based AI assistant for the WHINT Integration Cockpit API. It enables users to fetch, store, explore, and query integration interface data using natural language, powered by LLMs (such as OpenAI GPT-4). The assistant supports local data caching, advanced query building, and multiple deployment options.

---

## Project Structure

| Folder/File         | Purpose/Use                                                                 | Safe to Delete?         |
|---------------------|-----------------------------------------------------------------------------|-------------------------|
| knowledge_cache/    | Caching for LLM/knowledge responses                                         | No (unless clearing cache) |
| .streamlit/         | Streamlit config and secrets                                                | No                      |
| dist/               | Production-ready deployment package                                         | No (unless not deploying) |
| attached_assets/    | Sample data, helper scripts, API docs                                       | Only if not needed      |
| app.py              | Main Streamlit app                                                          | No                      |
| *.py (core modules) | Core logic for API, NLP, LLM, etc.                                          | No                      |
| test_chunking.py    | Test script for chunking                                                    | Yes, if not testing     |
| Dockerfile, ...     | Deployment configs                                                          | Only if not deploying   |
| *.md                | Documentation                                                               | Only if consolidating   |
| pyproject.toml, ... | Dependency management                                                       | No                      |

---

## Folder & File Details

### knowledge_cache/
- **Purpose**: Stores cached LLM responses and knowledge to speed up repeated queries and reduce API costs.
- **Usage**: Used internally by the app. You may clear its contents to reset the cache, but do not delete the folder if you want caching to work.

### .streamlit/
- **Purpose**: Contains Streamlit configuration files (`config.toml`, `secrets.toml.example`).
- **Usage**: Required for app configuration and storing API keys/secrets. Edit `secrets.toml` with your credentials.

### dist/
- **Purpose**: Contains a ready-to-deploy copy of your app (`whint-ai-assistant/`).
- **Usage**: Use for production deployment (Docker, cloud, etc.).

### attached_assets/
- **Purpose**: Stores sample data, API responses, helper scripts, and API documentation PDFs.
- **Usage**: Useful for testing, development, and reference. Safe to delete only if you are sure you do not need these assets.

### Core Python Files
- **app.py**: Main entry point for the Streamlit app. Run this file to start the app.
- **auth_manager.py, whint_api.py, query_builder.py, nlp_processor.py, inventory_types.py, llm_helper.py, llm_providers.py, knowledge_store.py**: Core modules for authentication, API access, query building, NLP, inventory mapping, LLM integration, and knowledge storage. Do not delete.

### test_chunking.py
- **Purpose**: Test script for chunking logic. Safe to delete if you do not need to test chunking.

### Deployment/Config Files
- **Dockerfile, docker-compose.yml, kubernetes.yaml, deploy.sh, Procfile**: For various deployment methods. Keep only those relevant to your deployment strategy.

### Documentation
- **API_KEY_SETUP_GUIDE.md, ENDPOINT_ROUTING_EXAMPLES.md, HOW_TO_USE_DIST_FOLDER.md, KNOWLEDGE_STORAGE_APPROACH.md, PRODUCTION_DEPLOYMENT_GUIDE.md, UNDERSTANDING_GIT_AND_CREDENTIAL_STORAGE.md, replit.md**: Guides and documentation for setup, deployment, and usage. Keep for reference or consolidate as needed.

### Dependency Files
- **pyproject.toml, uv.lock**: Python dependencies and lock file. Required for package management.

---

## How to Run the Project

### Local Development
1. **Install Python 3.11+**
2. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   # or, if using pyproject.toml:
   pip install .
   # or, if using uv:
   uv pip install -r requirements.txt
   ```
3. **Set up secrets**
   - Edit `.streamlit/secrets.toml` or use environment variables as described in the docs.
4. **Run the app**
   ```sh
   streamlit run app.py
   ```
   - Access at [http://localhost:8501](http://localhost:8501)

### Production/Cloud Deployment
- Use the `dist/whint-ai-assistant/` package and follow the `PRODUCTION_DEPLOYMENT_GUIDE.md` for Docker, Kubernetes, or cloud deployment.
- Example for Docker:
  ```sh
  cd dist/whint-ai-assistant
  cp .env.example .env
  # Edit .env with your credentials
  ./deploy.sh docker
  docker-compose up -d
  ```

---

## Recommendations for Deletion
- **test_chunking.py**: Delete if you do not need to test chunking logic.
- **Deployment/config files**: Delete only those you are certain you will never use (e.g., `kubernetes.yaml` if not using Kubernetes).
- **attached_assets/**: Delete only if you are sure you do not need the sample data, helper scripts, or API docs.
- **dist/**: Delete only if you are not deploying or distributing the app.

**Do NOT delete any core `.py` files, `.streamlit/`, or dependency files unless you are absolutely sure.**

---

## Additional Resources
- See the various `.md` documentation files for detailed setup, deployment, and usage instructions.
- For production deployment, refer to `PRODUCTION_DEPLOYMENT_GUIDE.md` and `HOW_TO_USE_DIST_FOLDER.md`.
- For API key setup, see `API_KEY_SETUP_GUIDE.md`.

---

## License
This project is provided as-is for educational and integration analytics purposes. 