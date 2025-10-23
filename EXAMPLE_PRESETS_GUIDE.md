# Example Presets Guide

## Overview

The example presets in the WHINT API AI Assistant are now organized into **8 distinct categories** with **visual emoji indicators** to help users quickly identify the type of query they want to run.

---

## 📋 Categories

### 📊 **TYPE-BASED QUERIES** (9 presets)
**Best for:** DuckDB or API data sources  
**Purpose:** Filter interfaces by their integration type

**Examples:**
- `Show APIM interfaces` → Returns all APIM, SAP_IS_APIM, AZURE_APIM interfaces
- `List SAP interfaces` → Returns all SAP_* type interfaces
- `Find SAP IDOC interfaces` → Returns only SAP_IDOC interfaces
- `Show SAP ODATA interfaces` → Returns SAP_ODATA interfaces
- `List SAP Process Orchestration (PO) interfaces` → Returns SAP_PO interfaces
- `Show SAP EventMesh interfaces` → Returns SAP_EVENTMESH interfaces
- `List MuleSoft applications` → Returns MULE_API and MULE_APP
- `Find Azure interfaces` → Returns all AZURE_* types
- `Show all EAM interfaces` → Returns EAM type interfaces

**What you'll learn:**
- How many interfaces of each type you have
- Distribution of integration technologies
- Type-specific configurations

---

### 🔍 **NAME & TEXT SEARCH** (5 presets)
**Best for:** DuckDB or API data sources  
**Purpose:** Search interfaces by name patterns

**Examples:**
- `Show interfaces where name contains 'Connect'` → Find all "Connect" interfaces
- `Find interfaces with 'Business Partner' in name` → Business partner integrations
- `List interfaces containing 'EXCHANGE_RATE'` → Currency exchange interfaces
- `Show interfaces starting with 'AGS_'` → All AGS_ prefixed interfaces
- `Find all Salesforce interfaces` → Salesforce-related integrations

**What you'll learn:**
- Naming conventions in your landscape
- Related interface groups
- Business process patterns

---

### 🔗 **SENDER & RECEIVER QUERIES** (7 presets)
**Best for:** DuckDB or API data sources  
**Purpose:** Analyze data flow between systems

**Examples:**
- `Find interfaces from SAP Solution Manager` → All interfaces sending from SAP Solution Manager
- `Show interfaces to Workday HCM` → All interfaces receiving to Workday HCM
- `List interfaces from SAP S/4HANA` → Outbound from S/4HANA
- `Find interfaces with sender 'Enterprise Alert'` → Enterprise Alert senders
- `Show interfaces where receiver is 'B2B Supplier'` → B2B Supplier receivers
- `Find interfaces with no sender` → Incomplete sender data
- `Show interfaces with no receiver` → Incomplete receiver data

**What you'll learn:**
- System integration points
- Data flow directions
- Data quality issues (missing sender/receiver)

---

### 📈 **ANALYTICAL QUERIES** (5 presets)
**Best for:** DuckDB (optimal for analytics)  
**Purpose:** Statistical analysis and data exploration

**Examples:**
- `Show all interfaces (complete dataset)` → Returns all 5,699+ interfaces
- `Count interfaces by type` → Type distribution statistics
- `Show top 10 most common senders` → Most active sending systems
- `Find interfaces with missing descriptions` → Data quality check
- `List first 50 interfaces alphabetically` → Limited result set

**What you'll learn:**
- Overall landscape size
- Most used systems and technologies
- Data quality metrics
- Common patterns

---

### 🏷️ **METADATA & PROPERTIES** (4 presets)
**Best for:** DuckDB or API data sources  
**Purpose:** Retrieve interfaces with additional context data

**Examples:**
- `Get interfaces with metadata included` → Include metadata objects
- `Show interfaces with properties` → Include property details
- `List interfaces with tags` → Include tag information
- `Find interfaces with all objects included` → Full detail retrieval

**What you'll learn:**
- Configuration details
- Custom properties
- Categorization via tags
- Complete interface context

---

### 🌐 **BUSINESS SCENARIOS** (5 presets)
**Best for:** DuckDB or API data sources  
**Purpose:** Real-world business use cases based on your data

**Examples:**
- `Show currency exchange rate interfaces` → EXCHANGE_RATE patterns
- `Find business partner replication flows` → Business Partner data sync
- `List all OANDA integrations` → OANDA system connections
- `Show European Central Bank interfaces` → ECB integrations
- `Find marketing cloud integrations` → Marketing cloud connections

**What you'll learn:**
- Common business processes
- Third-party integrations
- Data replication patterns
- Industry-specific integrations

---

### 🚫 **EXCLUSION QUERIES** (3 presets)
**Best for:** DuckDB or API data sources  
**Purpose:** Filter OUT unwanted data

**Examples:**
- `Exclude EAM and PLANNED interfaces` → Remove EAM and PLANNED types
- `Show interfaces that are NOT type 21` → Exclude specific type
- `List non-SAP interfaces` → Everything except SAP

**What you'll learn:**
- Active vs. planned interfaces
- Non-SAP technology usage
- Filtered views for specific analysis

---

### 🕸️ **GRAPH QUERIES** (6 presets)
**Best for:** Neo4j Graph data source ONLY  
**Purpose:** Relationship and path analysis

**Examples:**
- `Show all systems connected to Salesforce` → Salesforce integration map
- `What is the path from SAP to Azure?` → Connection path discovery
- `Find all interfaces that connect to MuleSoft` → MuleSoft dependencies
- `Show the data flow between System A and System B` → A-to-B paths
- `What systems are 2 hops away from SAP?` → Multi-hop analysis
- `Find shortest path from SharePoint to SAP` → Optimal route

**What you'll learn:**
- System dependencies
- Integration architecture
- Connection paths
- Multi-hop relationships

---

### 📋 **OTHER ENTITIES** (5 presets)
**Best for:** API data source  
**Purpose:** Query non-interface entities

**Examples:**
- `List all tasks with failed runs` → Task entity queries
- `Show all log entries` → Log entity queries
- `List all datasources` → Datasource catalog
- `Find systems containing 'SAP'` → System entity searches
- `Show dataflows containing 'sync'` → Dataflow analysis

**What you'll learn:**
- Task execution status
- System logs
- Available datasources
- System catalog
- Dataflow configurations

---

## 🎯 How to Use

1. **Select Data Source** (API, Local JSON, DuckDB, or Neo4j)
2. **Choose Category** based on your analysis needs:
   - Want to know about types? → 📊 TYPE-BASED
   - Looking for specific names? → 🔍 NAME SEARCH
   - Analyzing connections? → 🔗 SENDER/RECEIVER or 🕸️ GRAPH
   - Need statistics? → 📈 ANALYTICAL
   - Checking data quality? → 📈 ANALYTICAL or 🚫 EXCLUSION
   - Business use cases? → 🌐 BUSINESS SCENARIOS

3. **Select Preset** from dropdown
4. **Question auto-fills** with the query (emoji removed)
5. **Click "Ask AI Assistant"**

---

## 📊 Preset Distribution

| Category | Count | Icon |
|----------|-------|------|
| Type-Based Queries | 9 | 📊 |
| Name & Text Search | 5 | 🔍 |
| Sender & Receiver | 7 | 🔗 |
| Analytical Queries | 5 | 📈 |
| Metadata & Properties | 4 | 🏷️ |
| Business Scenarios | 5 | 🌐 |
| Exclusion Queries | 3 | 🚫 |
| Graph Queries | 6 | 🕸️ |
| Other Entities | 5 | 📋 |
| **TOTAL** | **49 presets** | |

---

## 💡 Smart Features

### Auto-Detection
The presets demonstrate various query patterns that the NLP processor can understand:
- Type aliases (APIM, SAP, IDOC, etc.)
- Text search patterns (contains, starts with)
- Sender/receiver patterns
- Exclusion logic (NOT, exclude)
- Graph relationships (connected to, path from)

### Emoji Removal
When you select a preset, the emoji prefix is automatically removed:
- Display: `📊 Show APIM interfaces`
- Query sent: `Show APIM interfaces`

### Visual Grouping
Emojis help categorize presets in the dropdown for easier navigation, especially with 49+ options.

---

## 🔄 Compatibility Matrix

| Category | API | Local JSON | DuckDB | Neo4j |
|----------|-----|------------|--------|-------|
| 📊 Type-Based | ✅ | ✅ | ✅ | ❌ |
| 🔍 Name Search | ✅ | ✅ | ✅ | ❌ |
| 🔗 Sender/Receiver | ✅ | ✅ | ✅ | ❌ |
| 📈 Analytical | ✅ | ⚠️ | ✅✅✅ | ❌ |
| 🏷️ Metadata | ✅ | ✅ | ✅ | ❌ |
| 🌐 Business Scenarios | ✅ | ✅ | ✅ | ❌ |
| 🚫 Exclusion | ✅ | ⚠️ | ✅ | ❌ |
| 🕸️ Graph | ❌ | ❌ | ❌ | ✅✅✅ |
| 📋 Other Entities | ✅ | ❌ | ⚠️ | ❌ |

**Legend:**
- ✅✅✅ = Best performance
- ✅ = Supported
- ⚠️ = Limited support
- ❌ = Not supported

---

## 🎓 Learning Path

### For New Users:
1. Start with **📊 Type-Based** queries to understand your landscape
2. Try **📈 Analytical** queries to see overall statistics
3. Explore **🔍 Name Search** to find specific interfaces

### For Advanced Users:
1. Use **🔗 Sender/Receiver** for integration architecture analysis
2. Apply **🚫 Exclusion** for filtered views
3. Leverage **🕸️ Graph** queries for relationship mapping (if using Neo4j)
4. Explore **🌐 Business Scenarios** for real-world use cases

---

## 📝 Custom Queries

While presets are helpful, you can also type your own questions:
- "Show me all interfaces updated in the last 30 days"
- "Find interfaces with both metadata and properties"
- "List top 5 senders by interface count"
- "Show interfaces from SAP to Azure"

The NLP processor will translate these into appropriate queries!

---

## Date: October 23, 2025
## Total Presets: 49
## Categories: 8

