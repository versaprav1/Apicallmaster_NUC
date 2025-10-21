# 🔧 Neo4j Authentication Setup Guide

## 🚨 Current Issue

Your Neo4j authentication is failing because:
1. **No `.env` file exists** in the ApiCallMaster directory
2. The application is using default environment variables that don't match your Neo4j container

## ✅ Solution: Create .env File

### Step 1: Create the .env file

Create a file named `.env` in the `ApiCallMaster` directory with the following content:

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=pass

# Graph RAG Configuration
GRAPH_BACKEND=neo4j

# Method Configuration
METHODS_ENABLED=graph_rag,vector_rag,db_lookup,llm_synthesis
METHOD_PRIORITY=graph_rag,vector_rag,db_lookup
```

### Step 2: Verify Your Neo4j Container Password

Your Docker container was started with: `docker run ... -e NEO4J_AUTH=neo4j/pass ...`

This means:
- **Username**: `neo4j`
- **Password**: `pass`

The `.env` file above matches these credentials.

### Step 3: Quick Copy Command

**Option A: Using PowerShell**
```powershell
# Navigate to ApiCallMaster directory
cd D:\versa\project_Files\replit_dell\ApiCallMaster

# Copy the example file and rename it
Copy-Item env.example .env

# Or create it manually with this command:
@"
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=pass
GRAPH_BACKEND=neo4j
METHODS_ENABLED=graph_rag,vector_rag,db_lookup,llm_synthesis
METHOD_PRIORITY=graph_rag,vector_rag,db_lookup
"@ | Out-File -FilePath .env -Encoding UTF8
```

**Option B: Manual Creation**
1. Open Notepad or VS Code
2. Copy the content from `env.example`
3. Save as `.env` (not `.env.txt`) in the `ApiCallMaster` directory

### Step 4: Test the Connection

After creating the `.env` file, test the connection:

```bash
python src/neo4j_wrapper.py
```

You should see:
```
Testing Neo4j wrapper...
Neo4j available: True
Connection test: True
Message: Connection successful: <Record test=1>
```

### Step 5: Test Graph RAG

```bash
python test_local_json_flow.py
```

### Step 6: Run Streamlit

```bash
streamlit run app.py
```

Then ask: "which systems send data to salesforce"

---

## 🔄 Alternative: Reset Neo4j Container

If the password `pass` doesn't work, reset your Neo4j container:

```powershell
# Stop and remove current container
docker stop neo4j
docker rm neo4j

# Start with a known password
docker run -d `
  --name neo4j `
  -p 7474:7474 -p 7687:7687 `
  -e NEO4J_AUTH=neo4j/yourpassword `
  neo4j:5.22

# Then update .env file with:
# NEO4J_PASSWORD=yourpassword
```

---

## 🧪 Verify Everything Works

### Test 1: Neo4j Connection
```bash
python -c "
from src.neo4j_wrapper import test_connection
import os
from dotenv import load_dotenv
load_dotenv()

uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
user = os.getenv('NEO4J_USER', 'neo4j')
password = os.getenv('NEO4J_PASSWORD', 'pass')

success, message = test_connection(uri, (user, password))
print(f'Success: {success}')
print(f'Message: {message}')
"
```

### Test 2: Graph RAG with Sample Data
```bash
python -c "
import json
from methods.graph_rag import run

with open('23-09-2025.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

sample_data = data[:10]
result, meta = run('which systems send data to salesforce', data=sample_data)
print(result)
"
```

### Test 3: Streamlit App
```bash
streamlit run app.py
```

---

## 📝 Notes

- The `.env` file is in `.gitignore` so it won't be committed to version control
- Never share your `.env` file publicly as it may contain API keys
- For production, use strong passwords and enable authentication
- The `env.example` file is a template you can copy

---

## ✅ Expected Result

After creating the `.env` file, your Graph RAG should work and show:

```
🔍 Graph RAG Debug Info:
  • Query: 'which systems send data to salesforce'
  • Backend: neo4j
  • Data provided: True
  • Data records count: 5771
  • Analyzing data structure...
  • Records with sender: 3
  • Records with receiver: 4
  • Salesforce mentions: 17
  • Adapting data for Graph RAG...
  • Adapted 5771 records
  • Ingesting 5771 records into Neo4j...
  • ✅ Data ingestion completed
  • Extracted seeds: ['Salesforce']
  • Searching neighborhood around seed: 'Salesforce'
  • Found X neighborhood nodes
```

And you'll see Salesforce-related interfaces in the results! 🎉
