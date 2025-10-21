"""
Inventory types mapping for WHINT Integration Cockpit
Based on the official API documentation
"""

# Official WHINT API Inventory Types
INVENTORY_TYPES = {
    0: "MULE_API",
    1: "MULE_APP", 
    2: "APIM",
    3: "AZURE_APIM",
    4: "AZURE_EVENTGRID",
    5: "AZURE_LA_CON",
    6: "AZURE_LA_STD", 
    7: "AZURE_SB_QUEUE",
    8: "AZURE_SB_TOPIC",
    9: "BACKEND",
    10: "BROKER",
    11: "ESB",
    12: "OTHER",
    13: "PLANNED",
    14: "SAP_ODATA",
    15: "SAP_SOAP",
    16: "SAP_EVENTMESH",
    17: "SAP_IDOC",
    18: "SAP_IS_APIM",
    19: "SAP_IS_CI",
    20: "SAP_PO",
    21: "EAM"
}

# Database short forms mapping to full names
INVENTORY_TYPE_SHORT_FORMS = {
    "MLAPI": "MULE_API",
    "MLAPP": "MULE_APP",
    "GAP": "APIM",
    "AZA": "AZURE_APIM",
    "AZE": "AZURE_EVENTGRID",
    "AZC": "AZURE_LA_CON",
    "AZS": "AZURE_LA_STD",
    "AZQ": "AZURE_SB_QUEUE",
    "AZT": "AZURE_SB_TOPIC",
    "BAC": "BACKEND",
    "BRO": "BROKER",
    "ESB": "ESB",
    "OTH": "OTHER",
    "PLA": "PLANNED",
    "SAO": "SAP_ODATA",
    "SAS": "SAP_SOAP",
    "SAE": "SAP_EVENTMESH",
    "SAI": "SAP_IDOC",
    "SIA": "SAP_IS_APIM",
    "SIC": "SAP_IS_CI",
    "SAP": "SAP_PO",
    "EAM": "EAM",
}

# Reverse mapping for lookup by name
INVENTORY_TYPES_BY_NAME = {v: k for k, v in INVENTORY_TYPES.items()}

def get_inventory_type_name(type_id: int) -> str:
    """Get the name of an inventory type by its ID"""
    return INVENTORY_TYPES.get(type_id, f"Unknown Type ({type_id})")

def get_inventory_type_id(type_name: str) -> int:
    """Get the ID of an inventory type by its name"""
    return INVENTORY_TYPES_BY_NAME.get(type_name.upper(), -1)

def expand_short_form(short_form: str) -> str:
    """Convert database short form to full inventory type name"""
    return INVENTORY_TYPE_SHORT_FORMS.get(short_form.upper(), short_form)

def get_type_from_short_form(short_form: str) -> int:
    """Get inventory type ID from database short form"""
    full_name = expand_short_form(short_form)
    return get_inventory_type_id(full_name)

def is_valid_inventory_type(type_id: int) -> bool:
    """Check if an inventory type ID is valid"""
    return type_id in INVENTORY_TYPES

def get_sap_types() -> dict:
    """Get all SAP-related inventory types"""
    return {k: v for k, v in INVENTORY_TYPES.items() if v.startswith("SAP_")}

def get_azure_types() -> dict:
    """Get all Azure-related inventory types"""
    return {k: v for k, v in INVENTORY_TYPES.items() if v.startswith("AZURE_")}

def get_mule_types() -> dict:
    """Get all MuleSoft-related inventory types"""
    return {k: v for k, v in INVENTORY_TYPES.items() if v.startswith("MULE_")}

def categorize_inventory_types() -> dict:
    """Categorize inventory types by platform/technology"""
    categories = {
        "SAP": get_sap_types(),
        "Azure": get_azure_types(), 
        "MuleSoft": get_mule_types(),
        "Integration Platforms": {
            k: v for k, v in INVENTORY_TYPES.items() 
            if v in ["APIM", "ESB", "BROKER"]
        },
        "Other": {
            k: v for k, v in INVENTORY_TYPES.items()
            if v in ["BACKEND", "OTHER", "PLANNED", "EAM"]
        }
    }
    return categories

def get_type_description(type_id: int) -> str:
    """Get a human-readable description of an inventory type"""
    descriptions = {
        0: "MuleSoft API",
        1: "MuleSoft Application",
        2: "API Management Platform",
        3: "Azure API Management",
        4: "Azure Event Grid",
        5: "Azure Logic Apps Connector",
        6: "Azure Logic Apps Standard",
        7: "Azure Service Bus Queue",
        8: "Azure Service Bus Topic",
        9: "Backend System",
        10: "Message Broker",
        11: "Enterprise Service Bus",
        12: "Other/Miscellaneous System",
        13: "Planned Integration",
        14: "SAP OData Service",
        15: "SAP SOAP Service",
        16: "SAP Event Mesh",
        17: "SAP IDoc Interface",
        18: "SAP Integration Suite API Management",
        19: "SAP Integration Suite Cloud Integration",
        20: "SAP Process Orchestration",
        21: "Enterprise Architecture Management"
    }
    return descriptions.get(type_id, f"Unknown inventory type with ID {type_id}")

def filter_by_category(category: str) -> dict:
    """Filter inventory types by category"""
    categories = categorize_inventory_types()
    return categories.get(category, {})

def search_inventory_types(search_term: str) -> dict:
    """Search inventory types by name or description"""
    search_term = search_term.upper()
    results = {}
    
    for type_id, type_name in INVENTORY_TYPES.items():
        if search_term in type_name or search_term in get_type_description(type_id).upper():
            results[type_id] = type_name
    
    return results

def get_inventory_type_stats(data: list) -> dict:
    """Calculate statistics for inventory types in a dataset"""
    if not data:
        return {}
    
    type_counts = {}
    total_items = len(data)
    
    for item in data:
        item_type = item.get('type')
        if item_type is not None:
            type_name = get_inventory_type_name(item_type)
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    # Calculate percentages
    type_stats = {}
    for type_name, count in type_counts.items():
        type_stats[type_name] = {
            'count': count,
            'percentage': round((count / total_items) * 100, 2)
        }
    
    return type_stats

def validate_inventory_type_data(item: dict) -> list:
    """Validate inventory type data in an item"""
    errors = []
    
    if 'type' not in item:
        errors.append("Missing 'type' field")
    else:
        type_id = item['type']
        if not isinstance(type_id, int):
            errors.append(f"Type must be an integer, got {type(type_id)}")
        elif not is_valid_inventory_type(type_id):
            errors.append(f"Invalid inventory type ID: {type_id}")
    
    return errors
