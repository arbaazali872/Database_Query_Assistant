"""
InventoryDB Agent - Streamlit UI
ReAct Agent Interface

Run with: streamlit run app.py
"""

import streamlit as st
import json
from config import setup_logging
from src import run_agent, validate_openai_connection, validate_database_connection

# Setup logging
setup_logging()

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="InventoryDB Agent",
    page_icon="🗄️",
    layout="wide"
)

# =============================================================================
# HEADER & CONNECTION STATUS
# =============================================================================

st.title("🗄️ InventoryDB Agent")

# Display connection status
col1, col2 = st.columns(2)

with col1:
    openai_valid, openai_msg = validate_openai_connection()
    if openai_valid:
        st.success(f"✅ {openai_msg}")
    else:
        st.error(f"❌ {openai_msg}")

with col2:
    db_valid, db_msg = validate_database_connection()
    if db_valid:
        st.success(f"✅ {db_msg}")
    else:
        st.error(f"❌ {db_msg}")

# Stop app if connections are not valid
if not openai_valid or not db_valid:
    st.warning("⚠️ Please fix the connection issues above before proceeding.")
    st.info("""
    **Setup Instructions:**
    1. Create a `.env` file in your project directory
    2. Add `OPENAI_API_KEY=your_key_here`
    3. Add `DATABASE_URL=postgresql://user:password@host:port/dbname`
    4. Restart the Streamlit app
    """)
    st.stop()

st.markdown("---")

# =============================================================================
# INSTRUCTIONS
# =============================================================================

st.markdown("""
**Ask questions in plain English.** The AI agent will automatically:
- Retrieve database schema
- Generate SQL queries
- Execute queries safely
- Provide insights when helpful

This assistant is **read-only** and will never modify the database.
""")

st.markdown("---")

# =============================================================================
# INPUT SECTION
# =============================================================================

user_query = st.text_area(
    "Enter your question:",
    placeholder="Example: Show me all projects from 2023 with their budgets and client names",
    height=100,
    help="Ask anything about your database in plain English"
)

# Controls
col1, col2, col3 = st.columns([1, 1, 4])

with col1:
    show_reasoning = st.checkbox("Show Reasoning", value=False, help="Display agent's thought process")

with col2:
    submit_button = st.button("Submit", type="primary", use_container_width=True)

# =============================================================================
# QUERY EXECUTION
# =============================================================================

if submit_button:
    if not user_query.strip():
        st.warning("⚠️ Please enter a question before submitting.")
    else:
        with st.spinner("🤖 Agent is thinking..."):
            try:
                result = run_agent(user_query=user_query.strip())
                st.session_state['last_result'] = result
                
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
                st.stop()

# =============================================================================
# DISPLAY RESULTS
# =============================================================================

if 'last_result' in st.session_state:
    result = st.session_state['last_result']
    
    st.markdown("---")
    st.subheader("📊 Results")
    
    # Extract messages
    messages = result.get("messages", [])
    
    # Show reasoning if enabled
    if show_reasoning and messages:
        with st.expander("🧠 Agent Reasoning", expanded=False):
            for i, msg in enumerate(messages):
                msg_type = type(msg).__name__
                
                if hasattr(msg, 'content') and msg.content:
                    st.markdown(f"**[{i}] {msg_type}:**")
                    st.text(msg.content)
                
                # Show tool calls if present
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    st.markdown(f"**Tool Calls:**")
                    for tc in msg.tool_calls:
                        st.json({
                            "tool": tc["name"],
                            "args": tc["args"]
                        })
                
                st.markdown("---")
    
    # Find the last AI message without tool calls (final response)
    final_response = None
    for msg in reversed(messages):
        if type(msg).__name__ == "AIMessage":
            # Skip if it has tool calls (still working)
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                continue
            # This is the final response
            if hasattr(msg, 'content') and msg.content:
                final_response = msg.content
                break
    
    if final_response:
        st.markdown("### Agent Response")
        st.markdown(final_response)
    
    # Try to extract and display query results from state
    query_results = result.get("query_results")
    if query_results is not None and len(query_results) > 0:
        st.markdown("### Query Results")
        st.dataframe(query_results, use_container_width=True, height=400)
        st.caption(f"📈 Rows: {len(query_results)}")
    
    # Display insights if available
    insights = result.get("insights")
    if insights:
        st.markdown("### 💡 Insights")
        st.markdown(insights)

# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.caption("🔒 Read-only database access | Powered by ReAct Agent")