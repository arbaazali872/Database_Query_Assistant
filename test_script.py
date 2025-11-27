"""
Test script for InventoryDB Agent LangGraph implementation

Run this to test the graph flow without Streamlit UI
Make sure you have OPENAI_API_KEY in your .env file
"""

import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Import graph components (assumes all files are in same directory)
from langgraph_graph import create_inventory_graph, run_full_graph, run_graph_until_confirmation, continue_graph_after_confirmation
from langgraph_nodes import *

def print_section(title: str):
    """Helper to print formatted section headers"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def test_basic_query():
    """Test 1: Basic query with auto-confirmation"""
    print_section("TEST 1: Basic Query Flow")
    
    query = "Show me all projects from 2021 to 2024"
    print(f"User Query: {query}\n")
    
    # Run the full graph
    result = run_full_graph(user_query=query, show_sql=True, display_cap=500)
    
    # Print results
    print("📝 Improved Prompt:")
    print(result.get("improved_prompt", "N/A"))
    
    print("\n💾 Generated SQL:")
    print(result.get("sql_query", "N/A"))
    
    print("\n📊 Query Results:")
    if result.get("query_results") is not None:
        print(result["query_results"])
        print(f"\nMetadata: {result.get('metadata', {})}")
    else:
        print("No results")
    
    print("\n💡 Insights:")
    print(result.get("insights", "No insights generated"))
    
    if result.get("error"):
        print(f"\n❌ Error: {result['error']}")
    
    return result

def test_with_confirmation_flow():
    """Test 2: Step-by-step execution with manual confirmation simulation"""
    print_section("TEST 2: Step-by-Step with Confirmation")
    
    app = create_inventory_graph()
    
    # Initial state
    state = {
        "user_input": "Show top 10 clients by total order amount",
        "show_sql": False,
        "display_cap": 500,
        "edit_count": 0,
        "metadata": {},
        "user_confirmed": None,  # Will trigger wait state
    }
    
    print(f"User Query: {state['user_input']}\n")
    
    # Step 1: Run until prompt improvement
    print("Step 1: Running until prompt improvement...")
    result = run_graph_until_confirmation(app, state)
    
    print("\n📝 Improved Prompt (waiting for confirmation):")
    print(result.get("improved_prompt", "N/A"))
    
    # Simulate user confirmation
    print("\n✅ Simulating user confirmation (OK)...")
    result = continue_graph_after_confirmation(app, result, confirmed=True)
    
    print("\n💾 Generated SQL:")
    print(result.get("sql_query", "N/A"))
    
    print("\n📊 Query Results:")
    if result.get("query_results") is not None:
        print(result["query_results"])
    else:
        print("No results")
    
    print("\n💡 Insights:")
    print(result.get("insights", "No insights generated"))
    
    return result

def test_error_handling():
    """Test 3: Query that should trigger validation error"""
    print_section("TEST 3: Error Handling")
    
    query = "Show me data from nonexistent_table"
    print(f"User Query: {query}\n")
    
    result = run_full_graph(query)
    
    print("📝 Improved Prompt:")
    print(result.get("improved_prompt", "N/A"))
    
    if result.get("error"):
        print(f"\n❌ Expected Error: {result['error']}")
    else:
        print("\n⚠️ No error detected (unexpected)")
        print(f"SQL: {result.get('sql_query', 'N/A')}")
    
    return result

def test_insights_generation():
    """Test 4: Query that should trigger insights"""
    print_section("TEST 4: Insights Generation")
    
    query = "Show me a breakdown of project budgets by status with average and totals"
    print(f"User Query: {query}\n")
    
    result = run_full_graph(query)
    
    print("📝 Improved Prompt:")
    print(result.get("improved_prompt", "N/A"))
    
    print("\n💾 Generated SQL:")
    print(result.get("sql_query", "N/A"))
    
    print("\n💡 Insights (should be generated due to keywords 'breakdown', 'average'):")
    print(result.get("insights", "No insights generated"))
    
    return result

def run_all_tests():
    """Run all test cases"""
    print("\n" + "🚀 STARTING INVENTORYDB AGENT TESTS " + "🚀")
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY not found in environment")
        print("Please create a .env file with: OPENAI_API_KEY=your_key_here")
        return
    
    print("✅ OpenAI API Key found\n")
    
    try:
        # Run tests
        test_basic_query()
        input("\nPress Enter to continue to next test...")
        
        test_with_confirmation_flow()
        input("\nPress Enter to continue to next test...")
        
        test_error_handling()
        input("\nPress Enter to continue to next test...")
        
        test_insights_generation()
        
        print_section("ALL TESTS COMPLETED")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()