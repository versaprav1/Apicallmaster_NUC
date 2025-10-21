#!/usr/bin/env python3
"""
Test script to verify user intent analysis works correctly
for different types of questions.
"""

import sys
from pathlib import Path

# Add the current directory to the path to import from app.py
sys.path.append(str(Path(__file__).parent))

# Import the intent analysis function
from app import analyze_user_intent

def test_intent_analysis():
    """Test the intent analysis with various question types"""
    print("🧪 Testing User Intent Analysis")
    print("=" * 50)
    
    # Test cases with expected intents
    test_cases = [
        # List intent cases
        ("list all interfaces", "list_names"),
        ("show all interfaces", "list_names"),
        ("give me all interface names", "list_names"),
        ("display all interfaces", "list_names"),
        ("what are the interfaces", "list_names"),
        ("show interfaces", "list_names"),
        ("names of all interfaces", "list_names"),
        
        # Count intent cases
        ("how many interfaces are there", "count"),
        ("count the interfaces", "count"),
        ("number of interfaces", "count"),
        ("total interfaces", "count"),
        ("what's the total count", "count"),
        
        # Search intent cases
        ("find SAP interfaces", "specific_search"),
        ("search for interfaces with name containing CPI", "specific_search"),
        ("look for Azure interfaces", "specific_search"),
        ("interfaces that have MULE", "specific_search"),
        ("where are the SharePoint interfaces", "specific_search"),
        ("matching interfaces for payment", "specific_search"),
        
        # Analysis intent cases (should default to analysis)
        ("analyze the interface landscape", "analysis"),
        ("what are the main patterns in interfaces", "analysis"),
        ("give me insights about the data", "analysis"),
        ("explain the interface architecture", "analysis"),
        ("summarize the integration patterns", "analysis"),
    ]
    
    print("Testing intent detection:")
    print("-" * 60)
    
    correct_predictions = 0
    total_tests = len(test_cases)
    
    for i, (question, expected_intent) in enumerate(test_cases, 1):
        predicted_intent = analyze_user_intent(question)
        is_correct = predicted_intent == expected_intent
        
        status = "✅" if is_correct else "❌"
        print(f"{i:2d}. {status} '{question}'")
        print(f"     Expected: {expected_intent}, Got: {predicted_intent}")
        
        if is_correct:
            correct_predictions += 1
        
        print()
    
    accuracy = (correct_predictions / total_tests) * 100
    print(f"📊 Results Summary:")
    print(f"   - Total tests: {total_tests}")
    print(f"   - Correct predictions: {correct_predictions}")
    print(f"   - Accuracy: {accuracy:.1f}%")
    
    if accuracy >= 90:
        print("🎯 Excellent! Intent analysis is working very well.")
    elif accuracy >= 75:
        print("👍 Good! Intent analysis is working reasonably well.")
    else:
        print("⚠️  Intent analysis may need improvement.")
    
    # Test edge cases
    print(f"\n🔍 Testing Edge Cases:")
    print("-" * 30)
    
    edge_cases = [
        ("", "analysis"),  # Empty string
        ("   ", "analysis"),  # Whitespace only
        ("LIST ALL INTERFACES", "list_names"),  # All caps
        ("List All Interfaces", "list_names"),  # Title case
        ("Can you please list all the interfaces for me?", "list_names"),  # Polite request
        ("I need to find all interfaces containing SAP", "specific_search"),  # Complex sentence
    ]
    
    for question, expected in edge_cases:
        predicted = analyze_user_intent(question)
        status = "✅" if predicted == expected else "❌"
        print(f"{status} '{question}' -> {predicted} (expected: {expected})")

if __name__ == "__main__":
    test_intent_analysis()


