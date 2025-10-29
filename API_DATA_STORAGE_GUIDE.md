# 📊 API Data Storage - Complete Guide

## Where Does API Data Get Saved?

When you use **API mode** to ask questions, the data is saved in **TWO places**:

---

## 🎯 Two Storage Mechanisms

### **1. Q&A Storage (Automatic - Per Question)**

Every time you ask a question in API mode, it saves:

#### **Location 1: Vector Database (ChromaDB)**
- **Path:** `vector_store/chroma_db/`
- **Format:** Vector embeddings + metadata
- **Purpose:** Fast semantic search, find similar questions
- **Auto-created:** Yes, when you ask a question

**What gets stored:**
```json
{
  "question": "List SAP interfaces",
  "answer": "Here are the SAP interfaces...",
  "timestamp": "2025-10-28T14:30:45",
  "data_source": "api",
  "method": "api_direct",
  "response_data": {...},  // Actual API response
  "query": {...},          // API query used
  "endpoint": "/inventory/query"
}
```

#### **Location 2: Daily Response Log (JSONL)**
- **Path:** `response_logs/daily/responses_2025-10-28.jsonl`
- **Format:** JSON Lines (one JSON per line)
- **Purpose:** Audit trail, debugging, analytics
- **Auto-created:** Yes, new file per day

**What gets stored:**
```json
{"timestamp": "2025-10-28T14:30:45", "question": "List SAP interfaces", "answer": "...", "status": "success", "method": "api_direct", "execution_time_ms": 523, "data_source": "api", "model_used": "gpt-4o", ...}
```

---

### **2. Full Data Sync (Manual - All Data)**

When you click **"🚀 Start Live Sync"** or run the script:

#### **Location 3: Timestamped JSON File**
- **Path:** `api_data_28-10-2025_143020.json`
- **Format:** JSON array of all records
- **Purpose:** Full snapshot backup
- **Manual:** You trigger this sync

**Example:**
```json
[
  {"id": 1, "name": "SAP Interface 1", "type": "SAP_PO", ...},
  {"id": 2, "name": "SAP Interface 2", "type": "SAP_PO", ...},
  ...5771 records
]
```

**Metadata file:**
```json
{
  "filename": "api_data_28-10-2025_143020.json",
  "timestamp": "2025-10-28T14:30:20",
  "record_count": 5771,
  "source": "WHINT API Live Fetch"
}
```

#### **Location 4: DuckDB Database**
- **Path:** `duckdb_engine/wic.duckdb`
- **Format:** SQLite-like database
- **Purpose:** Fast SQL queries
- **Updated:** When you run sync

**Tables:**
- `raw_all` - All records
- `inventory_view` - Normalized view with sender/receiver

#### **Location 5: Neo4j Graph Database**
- **Location:** Neo4j server (local or cloud)
- **Format:** Graph nodes + relationships
- **Purpose:** Relationship analysis
- **Updated:** When you run sync (optional)

**Nodes:**
- `Interface` nodes (5,771)
- `System` nodes (extracted from sender/receiver)

**Relationships:**
- `SENT_BY` (Interface → System)
- `RECEIVED_BY` (Interface → System)

---

## 📋 Complete Storage Matrix

| Storage Location | Type | When | Purpose | Size |
|-----------------|------|------|---------|------|
| **ChromaDB** | Vector DB | Every question | Semantic search | ~10 MB |
| **Response Logs** | JSONL | Every question | Audit trail | ~1 KB/question |
| **JSON File** | JSON | Manual sync | Full backup | ~85 MB |
| **DuckDB** | SQL DB | Manual sync | Fast queries | ~50 MB |
| **Neo4j** | Graph DB | Manual sync | Relationships | ~100 MB |

---

## 🔄 Example Workflow

### **Scenario 1: Ask a Question**

```
You: "List SAP interfaces"
    ↓
📡 Fetch from API (523ms)
    ↓
💾 Save to ChromaDB ← Q&A pair
    ↓
📝 Log to response_logs/daily/responses_2025-10-28.jsonl
    ↓
✅ Display answer
```

**Saved:**
- ✅ ChromaDB: `vector_store/chroma_db/`
- ✅ Log: `response_logs/daily/responses_2025-10-28.jsonl`
- ❌ NOT in JSON/DuckDB/Neo4j (use sync for that)

---

### **Scenario 2: Full Data Sync**

```
You: Click "🚀 Start Live Sync"
    ↓
📡 Fetch ALL data from API (52 seconds)
    ↓
💾 Save to api_data_28-10-2025_143020.json
    ↓
🦆 Update duckdb_engine/wic.duckdb
    ↓
🕸️  Update Neo4j (optional)
    ↓
✅ All storage systems updated
```

**Saved:**
- ✅ JSON: `api_data_28-10-2025_143020.json` (full snapshot)
- ✅ DuckDB: `duckdb_engine/wic.duckdb` (all records)
- ✅ Neo4j: Graph database (if enabled)
- ✅ Metadata: `api_data_28-10-2025_143020_metadata.json`

---

## 🎯 When to Use Each

### **Use Q&A Storage (Automatic)**
- ✅ Quick questions
- ✅ Need answer history
- ✅ Find similar past questions
- ✅ Automatic, no effort

**Example:**
```
"List SAP interfaces"
"Show APIM APIs"
"Find interfaces from Salesforce"
```

Each question is automatically saved to ChromaDB + logs.

---

### **Use Full Data Sync (Manual)**
- ✅ Need complete dataset offline
- ✅ Want to do complex SQL queries
- ✅ Need relationship analysis (Neo4j)
- ✅ Create timestamped backups

**Example:**
```bash
# Sync all data once per day
python live_data_sync.py --full
```

Or click the sync button in the UI.

---

## 📂 File Structure After Use

```
ApiCallMaster/
│
├── vector_store/                    # Q&A Storage
│   └── chroma_db/                   # ← Every question saved here
│       ├── chroma.sqlite3
│       └── 2c87b214.../
│           ├── data_level0.bin
│           └── length.bin
│
├── response_logs/                   # Response Logs
│   └── daily/
│       ├── responses_2025-10-27.jsonl  # Yesterday's logs
│       └── responses_2025-10-28.jsonl  # ← Today's logs
│
├── api_data_28-10-2025_143020.json      # Full Sync: JSON
├── api_data_28-10-2025_143020_metadata.json
│
└── duckdb_engine/
    └── wic.duckdb                   # Full Sync: DuckDB
```

---

## 🔍 How to View Saved Data

### **1. View Q&A History (ChromaDB)**

In the Streamlit app:
1. Click **"📊 View Response Logs"** in sidebar
2. Or click **"📚 Q&A Pairs Explorer"**

Or programmatically:
```python
from src.vector_knowledge_store import VectorKnowledgeStore

store = VectorKnowledgeStore()
recent_qa = store.get_recent_qa_pairs(data_source="api", limit=10)

for qa in recent_qa:
    print(f"Q: {qa['question']}")
    print(f"A: {qa['answer'][:100]}...")
```

---

### **2. View Daily Logs**

```bash
# View today's logs
cat response_logs/daily/responses_2025-10-28.jsonl

# Count questions asked today
wc -l response_logs/daily/responses_2025-10-28.jsonl

# Search for specific questions
grep "SAP" response_logs/daily/responses_2025-10-28.jsonl
```

---

### **3. View Synced JSON Data**

```bash
# View JSON file
cat api_data_28-10-2025_143020.json | jq '.[:3]'  # First 3 records

# Count records
cat api_data_28-10-2025_143020.json | jq 'length'

# Find SAP interfaces
cat api_data_28-10-2025_143020.json | jq '.[] | select(.type | contains("SAP"))'
```

---

### **4. Query DuckDB**

```python
import duckdb

con = duckdb.connect('duckdb_engine/wic.duckdb')

# Count all interfaces
result = con.execute("SELECT COUNT(*) FROM raw_all").fetchone()
print(f"Total interfaces: {result[0]}")

# Get SAP interfaces
sap = con.execute("""
    SELECT name, type 
    FROM inventory_view 
    WHERE norm_type LIKE '%SAP%' 
    LIMIT 10
""").fetchall()

for interface in sap:
    print(interface)
```

---

### **5. Query Neo4j**

```cypher
// Count all interfaces
MATCH (i:Interface) RETURN count(i)

// Find SAP systems
MATCH (s:System) 
WHERE s.name CONTAINS 'SAP' 
RETURN s.name

// Find interfaces between SAP and Salesforce
MATCH (i:Interface)-[:SENT_BY]->(sender:System)
WHERE sender.name CONTAINS 'SAP'
  AND (i)-[:RECEIVED_BY]->(:System {name: 'Salesforce'})
RETURN i.name, sender.name
```

---

## 💡 Best Practices

### **1. Daily Q&A Storage**
- ✅ Automatic - just ask questions
- ✅ Builds up knowledge base over time
- ✅ Can search similar questions later
- ✅ Great for frequently asked questions

### **2. Weekly/Monthly Full Sync**
- ✅ Keep offline copy up to date
- ✅ Enable fast SQL analytics
- ✅ Create timestamped backups
- ✅ Update graph relationships

### **3. Cleanup Old Data**
```bash
# Archive logs older than 30 days
find response_logs/daily -name "*.jsonl" -mtime +30 -exec gzip {} \;

# Keep only last 3 JSON snapshots
ls -t api_data_*.json | tail -n +4 | xargs rm
```

---

## 🎯 Summary

### **Ask Questions → Automatic Storage**
```
Question → ChromaDB + Logs (automatic)
```

### **Full Sync → Manual Storage**
```
Sync Button → JSON + DuckDB + Neo4j (manual)
```

### **Both are useful!**
- **Q&A Storage:** History of what you asked
- **Full Sync:** Complete dataset for offline analysis

---

## 📊 Storage Size Estimates

For ~5,771 interfaces:

| Storage | Size | Growth Rate |
|---------|------|-------------|
| ChromaDB | ~10 MB | +100 KB per 10 questions |
| Daily Logs | ~1 MB/month | +1 KB per question |
| JSON Snapshot | ~85 MB | Fixed per sync |
| DuckDB | ~50 MB | Fixed per sync |
| Neo4j | ~100 MB | Fixed per sync |

**Total:** ~250 MB for complete storage

---

## 🚀 Quick Commands

### **View what's stored:**
```bash
# Q&A count
ls -lh vector_store/chroma_db/

# Today's questions
wc -l response_logs/daily/responses_$(date +%Y-%m-%d).jsonl

# Latest snapshot
ls -lht api_data_*.json | head -1
```

### **Full sync:**
```bash
python live_data_sync.py --full
```

### **Query stored data:**
```python
# Recent questions
from src.vector_knowledge_store import VectorKnowledgeStore
store = VectorKnowledgeStore()
store.get_recent_qa_pairs("api", 10)
```

---

**That's it! Your data is safely stored and easily accessible.** 🎉

