import streamlit as st
import requests
import openai
import json
import pandas as pd
import time
import os

# --- CONFIG ---
API_URL = st.secrets["whint_api_base_url"] if "whint_api_base_url" in st.secrets else "https://whint.prod.apimanagement.eu10.hana.ondemand.com:443/api"
API_KEY = st.secrets["whint_api_x_api_key"] if "whint_api_x_api_key" in st.secrets else os.getenv("WHINT_API_X_API_KEY")
BEARER_TOKEN = st.secrets["whint_api_bearer_token"] if "whint_api_bearer_token" in st.secrets else os.getenv("WHINT_API_BEARER_TOKEN")
OPENAI_API_KEY = st.secrets["openai_api_key"] if "openai_api_key" in st.secrets else os.getenv("OPENAI_API_KEY")

# --- API Request Body (from Postman) ---
API_BODY = {
    "query": {
        "entity": "inventory",
        "fields": ["name", "description"],
        "with": [
            {
                "entity": "sender",
                "fields": ["name"],
                "with": [
                    {
                        "entity": "properties",
                        "fields": ["type_id", "value"],
                        "with": [{
                            "entity": "type",
                            "fields": ["name", "kind"]
                        }]
                    }
                ]
            },
            {
                "entity": "receiver",
                "fields": ["name"],
                "with": [
                    {
                        "entity": "properties",
                        "fields": ["type_id", "value"],
                        "with": [{
                            "entity": "type",
                            "fields": ["name", "kind"]
                        }]
                    }
                ]
            },
            {
                "entity": "tags",
                "fields": ["value", "tag_id"],
                "with": [{
                    "entity": "tag",
                    "fields": ["name"]
                }]
            },
            {
                "entity": "properties",
                "fields": ["type_id", "value"],
                "with": [{
                    "entity": "type",
                    "fields": ["name", "kind"]
                }]
            },
            {
                "entity": "metadata",
                "fields": ["name", "value"]
            }
        ],
        "limit": 5000,
        "offset": 0
    }
}

# --- Functions ---
def fetch_api_data():
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(API_URL, headers=headers, data=json.dumps(API_BODY))
    response.raise_for_status()
    return response.json()

def fetch_all_api_data():
    """Fetch all data from the API using pagination and store in all_data.json, merging with existing data."""
    all_results = []
    limit = 5000
    offset = 0
    seen_ids = set()
    # Load existing data if present
    if os.path.exists("all_data.json"):
        with open("all_data.json") as f:
            existing = json.load(f)
            for item in existing:
                if isinstance(item, dict) and "id" in item:
                    seen_ids.add(item["id"])
            all_results.extend(existing)
    while True:
        body = dict(API_BODY)
        body["query"] = dict(API_BODY["query"])
        body["query"]["limit"] = limit
        body["query"]["offset"] = offset
        headers = {
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.post(API_URL, headers=headers, data=json.dumps(body))
        response.raise_for_status()
        data = response.json()
        page = data.get("data", []) if isinstance(data, dict) else data
        if not page:
            break
        # Merge, avoiding duplicates by 'id'
        for item in page:
            if isinstance(item, dict) and "id" in item:
                if item["id"] not in seen_ids:
                    all_results.append(item)
                    seen_ids.add(item["id"])
            else:
                all_results.append(item)
        if len(page) < limit:
            break
        offset += limit
    # Save to all_data.json
    with open("all_data.json", "w") as f:
        json.dump(all_results, f)
    # Save last fetch timestamp
    with open("last_fetch.txt", "w") as f:
        f.write(str(int(time.time())))
    return all_results

def should_refresh_daily():
    """Return True if more than 24h since last fetch, else False."""
    if not os.path.exists("last_fetch.txt"):
        return True
    with open("last_fetch.txt") as f:
        last = int(f.read().strip())
    return (time.time() - last) > 86400

def download_data_button():
    if os.path.exists("all_data.json"):
        with open("all_data.json", "r") as f:
            st.download_button("Download All Data (JSON)", f.read(), file_name="all_data.json", mime="application/json")
        # Also offer CSV
        df = pd.read_json("all_data.json")
        csv = df.to_csv(index=False)
        st.download_button("Download All Data (CSV)", csv, file_name="all_data.csv", mime="text/csv")

def summarize_data(data, max_rows=3):
    # Enhanced summary: show name, description, sender, receiver, and first property/tag for each interface
    if isinstance(data, dict):
        flows = data.get("data", [])
    elif isinstance(data, list):
        flows = data
    else:
        flows = []
    summary = []
    for flow in flows[:max_rows]:
        if not isinstance(flow, dict):
            summary.append(str(flow))
            continue
        name = flow.get("name", "N/A")
        desc = flow.get("description", "")
        sender = flow.get("sender", {}).get("name", "")
        receiver = flow.get("receiver", {}).get("name", "")
        # Show first property, tag, and metadata if available
        properties = flow.get("properties", [])
        tags = flow.get("tags", [])
        metadata = flow.get("metadata", [])
        prop_str = ""
        tag_str = ""
        meta_str = ""
        if properties:
            p = properties[0]
            prop_str = f" | Property: {p.get('type', {}).get('name', '')} = {p.get('value', '')}"
        if tags:
            t = tags[0]
            tag_str = f" | Tag: {t.get('tag', {}).get('name', '')} = {t.get('value', '')}"
        if metadata:
            m = metadata[0]
            meta_str = f" | Metadata: {m.get('name', '')} = {m.get('value', '')}"
        summary.append(f"- {name}: {desc} | Sender: {sender} | Receiver: {receiver}{prop_str}{tag_str}{meta_str}")
    return "\n".join(summary) if summary else "No data found.", len(flows)

def extract_property(data, interface_name, property_name):
    # Find the interface by name and return the value of the given property (if present)
    if isinstance(data, dict):
        flows = data.get("data", [])
    elif isinstance(data, list):
        flows = data
    else:
        flows = []
    for flow in flows:
        if flow.get("name", "").lower() == interface_name.lower():
            for prop in flow.get("properties", []):
                type_info = prop.get("type", {})
                if type_info.get("name", "").lower() == property_name.lower():
                    return prop.get("value", "Not available")
    return "Not available"

def extract_tag(data, interface_name, tag_name):
    # Find the interface by name and return the value of the given tag (if present)
    if isinstance(data, dict):
        flows = data.get("data", [])
    elif isinstance(data, list):
        flows = data
    else:
        flows = []
    for flow in flows:
        if flow.get("name", "").lower() == interface_name.lower():
            for tag in flow.get("tags", []):
                tag_info = tag.get("tag", {})
                if tag_info.get("name", "").lower() == tag_name.lower():
                    return tag.get("value", "Not available")
    return "Not available"

def ask_llm(summary, user_query, data=None):
    import openai
    openai.api_key = OPENAI_API_KEY
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    # Enhanced prompt for properties and tags
    available_fields = (
        "You have access to the following data fields for each interface: "
        "name, description, sender, receiver, tags, properties, items. "
        "The 'properties' field contains key-value pairs for each interface, such as URLs, teams, or IDs. "
        "The 'tags' field contains labels like domain, country, or status."
    )
    
    # Try to answer property/tag questions directly first
    if data and "property" in user_query.lower() and "for interface" in user_query.lower():
        import re
        m = re.search(r'property (.*?) for interface (.*?)[\?\.]?$', user_query, re.IGNORECASE)
        if m:
            property_name = m.group(1).strip()
            interface_name = m.group(2).strip()
            value = extract_property(data, interface_name, property_name)
            if value != "Not available":
                return f"The property '{property_name}' for interface '{interface_name}' is: {value}"
    
    if data and "tag" in user_query.lower() and "for interface" in user_query.lower():
        import re
        m = re.search(r'tag (.*?) for interface (.*?)[\?\.]?$', user_query, re.IGNORECASE)
        if m:
            tag_name = m.group(1).strip()
            interface_name = m.group(2).strip()
            value = extract_tag(data, interface_name, tag_name)
            if value != "Not available":
                return f"The tag '{tag_name}' for interface '{interface_name}' is: {value}"

    # Create a concise summary if the data is too large
    if len(summary) > 4000:  # Roughly 1000 tokens
        summary = summary[:4000] + "... (truncated for brevity)"
    
    prompt = f"{available_fields}\n\nHere is a sample of the data:\n{summary}\n\nUser question: {user_query}"
    
    try:
        # Try with GPT-3.5-Turbo first (higher rate limits)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content
        
        # If the answer indicates uncertainty, try with GPT-4 but with reduced context
        if any(phrase in answer.lower() for phrase in ["not sure", "cannot determine", "unclear"]):
            compact_prompt = f"Question about interface data: {user_query}\nContext (summarized): {summary[:2000]}"
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": compact_prompt}]
            )
            return response.choices[0].message.content
        
        return answer
        
    except openai.RateLimitError as e:
        # Fallback to an even more conservative approach
        minimal_prompt = f"Question about interface data: {user_query}\nContext: Working with interface data that includes {', '.join(data[0].keys() if data else ['unknown fields'])}."
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": minimal_prompt}]
        )
        return response.choices[0].message.content + "\n(Note: Response was generated with limited context due to rate limits)"

# --- Streamlit UI ---
st.title("WHINT API Data Q&A with LLM")

# Daily auto-refresh
if should_refresh_daily():
    with st.spinner("Auto-refreshing all data from API (once per day)..."):
        all_data = fetch_all_api_data()
        st.session_state['data'] = {"data": all_data}
        st.success(f"Auto-refreshed {len(all_data)} records and saved to all_data.json!")

if st.button("Fetch All Data from API (Full Download)"):
    with st.spinner("Fetching all data from API (may take a while)..."):
        all_data = fetch_all_api_data()
        st.session_state['data'] = {"data": all_data}
        st.success(f"Fetched {len(all_data)} records and saved to all_data.json!")
        st.write("Sample data:", all_data[:3])

# Download buttons
with st.expander("Download Data"):
    download_data_button()

# On app start, try to load all_data.json if available
if 'data' not in st.session_state:
    if os.path.exists("all_data.json"):
        with open("all_data.json") as f:
            all_data = json.load(f)
            st.session_state['data'] = {"data": all_data}

if 'data' in st.session_state:
    flows = st.session_state['data'].get("data", []) if isinstance(st.session_state['data'], dict) else st.session_state['data']
    total_rows = len(flows)
    st.write("**Data Summary:**")
    # Show a scrollable code block with up/down arrows (height=5 rows by default)
    summary, _ = summarize_data(st.session_state['data'], total_rows)
    st.code(summary, language=None)
    st.markdown(
        """
        <style>
        .element-container pre {
            max-height: 10em;
            overflow-y: auto;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.subheader("Ask a question about the data:")
    user_query = st.text_input("Your question")
    if user_query:
        with st.spinner("Getting answer from LLM..."):
            answer = ask_llm(summary, user_query, st.session_state['data'])
        st.markdown("**Answer:**")
        st.write(answer)
