#!/usr/bin/env python3
"""
Test script to verify Graph RAG integration with ApiCallMaster
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.method_router import MethodRouter
from src.nlp_processor import NLPProcessor

def test_method_router():
    """Test the method router functionality"""
    print("🧪 Testing Method Router...")
    
    # Initialize router
    router = MethodRouter()
    
    # Test queries
    test_queries = [
        "Show me all SAP interfaces",
        "Which systems send data to Salesforce?",
        "What is the shortest path from SAP to Azure?",
        "Find interfaces connected to MuleSoft",
        "How does data flow from System A to System B?",
        "List all interfaces with their properties"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        
        # Route the query
        routing_result = router.route_query(query)
        method_name = routing_result["method_name"]
        intent = routing_result["routing_info"]["intent"]
        
        print(f"   Method: {method_name}")
        print(f"   Requires Graph: {intent.get('requires_graph', False)}")
        print(f"   Graph Seeds: {intent.get('graph_seeds', [])}")
        print(f"   Sender/Receiver: {intent.get('sender_receiver')}")
    
    print("\n✅ Method Router test completed!")

def test_nlp_processor():
    """Test the NLP processor graph detection"""
    print("\n🧪 Testing NLP Processor...")
    
    # Use empty string for API key in test mode
    processor = NLPProcessor(openai_api_key="")
    
    # Test graph detection
    test_queries = [
        "Which systems send data to Salesforce?",
        "What is the shortest path from SAP to Azure?",
        "Find interfaces connected to MuleSoft",
        "How does data flow from System A to System B?",
        "Show me all SAP interfaces",  # Should NOT require graph
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        
        intent = processor.analyze_query_intent(query)
        print(f"   Requires Graph: {intent.get('requires_graph', False)}")
        print(f"   Query Type: {intent.get('query_type', 'unknown')}")
        print(f"   Graph Seeds: {intent.get('graph_seeds', [])}")
        print(f"   Sender/Receiver: {intent.get('sender_receiver')}")
    
    print("\n✅ NLP Processor test completed!")

def test_health_status():
    """Test health status checking"""
    print("\n🧪 Testing Health Status...")
    
    router = MethodRouter()
    health = router.get_health_status()
    
    print("Health Status:")
    print(f"   Enabled Methods: {health.get('enabled_methods', [])}")
    print(f"   Method Priority: {health.get('method_priority', [])}")
    print(f"   Graph Backend: {health.get('graph_backend', 'unknown')}")
    
    print("\nMethod Status:")
    for method, status in health.get('method_status', {}).items():
        print(f"   {method}: {status.get('status', 'unknown')}")
        if status.get('error'):
            print(f"     Error: {status['error']}")
    
    print("\n✅ Health Status test completed!")

def main():
    """Run all tests"""
    print("🚀 Starting Graph RAG Integration Tests...")
    print("=" * 50)
    
    try:
        test_nlp_processor()
        test_method_router()
        test_health_status()
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")
        print("\nNext steps:")
        print("1. Start the Streamlit app: streamlit run app.py")
        print("2. Try graph queries like:")
        print("   - 'Which systems send data to Salesforce?'")
        print("   - 'What is the shortest path from SAP to Azure?'")
        print("   - 'Find interfaces connected to MuleSoft'")
        print("3. Check method health in the sidebar")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


