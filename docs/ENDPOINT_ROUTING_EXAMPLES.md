# WHINT API Endpoint Routing Examples

## How Endpoint Routing Works

The WHINT AI Assistant automatically routes your queries to specific API endpoints based on the technology type you're asking about. This improves performance and provides more targeted results.

## Supported Endpoint Types

### 1. SAP Endpoint (/sap)
**Triggers when asking about SAP interfaces**

**Example Questions:**
- "Show me SAP interfaces"
- "Find all SAP ODATA services"
- "List SAP SOAP interfaces"
- "What SAP integrations do we have?"

**Generated Query:**
```json
{
  "query": {
    "entity": "inventory",
    "fields": ["name", "sender_name", "receiver_name", "description", "type"],
    "where": [{
      "option": 1,
      "conditions": [{
        "field": {
          "name": "type",
          "in": ["14", "15", "16", "17", "18", "19", "20"]
        }
      }]
    }],
    "limit": 300
  }
}
```

**Endpoint:** `{base_url}/interfaces/sap`

### 2. MULE Endpoint (/mule)
**Triggers when asking about MULE applications**

**Example Questions:**
- "Show me MULE applications"
- "List all MULE APIs"
- "Find MULE integrations"

**Generated Query:**
```json
{
  "query": {
    "entity": "inventory",
    "fields": ["name", "sender_name", "receiver_name", "description", "type"],
    "where": [{
      "option": 1,
      "conditions": [{
        "field": {
          "name": "type",
          "in": ["0", "1"]
        }
      }]
    }],
    "limit": 300
  }
}
```

**Endpoint:** `{base_url}/interfaces/mule`

### 3. Azure Endpoint (/azure)
**Triggers when asking about Azure services**

**Example Questions:**
- "Show me Azure interfaces"
- "List Azure Service Bus queues"
- "Find Azure Event Grid subscriptions"
- "What Azure Logic Apps do we have?"

**Generated Query:**
```json
{
  "query": {
    "entity": "inventory",
    "fields": ["name", "sender_name", "receiver_name", "description", "type"],
    "where": [{
      "option": 1,
      "conditions": [{
        "field": {
          "name": "type",
          "in": ["3", "4", "5", "6", "7", "8"]
        }
      }]
    }],
    "limit": 300
  }
}
```

**Endpoint:** `{base_url}/interfaces/azure`

### 4. APIM Endpoint (/apim)
**Triggers when asking about API Management**

**Example Questions:**
- "Show me APIM interfaces"
- "List API Management services"
- "Find APIM endpoints"

**Generated Query:**
```json
{
  "query": {
    "entity": "inventory",
    "fields": ["name", "sender_name", "receiver_name", "description", "type"],
    "where": [{
      "option": 1,
      "conditions": [{
        "field": {
          "name": "type",
          "eq": "2"
        }
      }]
    }],
    "limit": 300
  }
}
```

**Endpoint:** `{base_url}/interfaces/apim`

### 5. Default Endpoint (/interfaces)
**Used for general or mixed queries**

**Example Questions:**
- "Show me all interfaces"
- "List everything"
- "Find interfaces by name containing 'Order'"
- "What backend systems do we have?"

**Generated Query:**
```json
{
  "query": {
    "entity": "inventory",
    "fields": ["name", "sender_name", "receiver_name", "description", "type"],
    "where": [{
      "option": 1,
      "conditions": [{
        "field": {
          "name": "name",
          "like": "Order"
        }
      }]
    }],
    "limit": 300
  }
}
```

**Endpoint:** `{base_url}/interfaces`

## Type ID Mappings

| Type ID | Technology | Endpoint Route |
|---------|------------|----------------|
| 0 | MULE_API | /mule |
| 1 | MULE_APP | /mule |
| 2 | APIM | /apim |
| 3 | AZURE_APIM | /azure |
| 4 | AZURE_EVENTGRID | /azure |
| 5 | AZURE_LA_CON | /azure |
| 6 | AZURE_LA_STD | /azure |
| 7 | AZURE_SB_QUEUE | /azure |
| 8 | AZURE_SB_TOPIC | /azure |
| 9 | BACKEND | /interfaces |
| 10 | BROKER | /interfaces |
| 11 | ESB | /interfaces |
| 12 | OTHER | /interfaces |
| 13 | PLANNED | /interfaces |
| 14 | SAP_ODATA | /sap |
| 15 | SAP_SOAP | /sap |
| 16 | SAP_EVENTMESH | /sap |
| 17 | SAP_IDOC | /sap |
| 18 | SAP_IS_APIM | /sap |
| 19 | SAP_IS_CI | /sap |
| 20 | SAP_PO | /sap |
| 21 | EAM | /interfaces |

## How to Test Endpoint Routing

1. **Test SAP Routing:**
   - Ask: "Show me SAP interfaces"
   - Look for debug output showing "/sap" endpoint
   - Verify query contains SAP type filtering

2. **Test MULE Routing:**
   - Ask: "Find MULE applications"
   - Look for debug output showing "/mule" endpoint
   - Verify query contains MULE type filtering

3. **Test Azure Routing:**
   - Ask: "Show me Azure services"
   - Look for debug output showing "/azure" endpoint
   - Verify query contains Azure type filtering

4. **Test APIM Routing:**
   - Ask: "List APIM interfaces"
   - Look for debug output showing "/apim" endpoint
   - Verify query contains APIM type filtering

5. **Test General Routing:**
   - Ask: "Show me all interfaces"
   - Look for debug output showing "/interfaces" endpoint
   - Verify no type filtering applied

## Debug Information

When you make a query, the application shows debug information including:
- The generated query structure
- Type conditions found in the query
- The selected endpoint based on type analysis
- The final API URL being called

This helps you understand how the routing works and troubleshoot any issues.

## Benefits of Endpoint Routing

1. **Better Performance:** Targeted queries return faster results
2. **Reduced Load:** Servers handle smaller, focused datasets
3. **Improved Accuracy:** Technology-specific optimizations
4. **Cleaner Results:** More relevant data for your specific needs
5. **Scalability:** Better resource utilization across different service types