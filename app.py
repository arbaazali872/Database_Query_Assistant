"""
InventoryDB Agent - Streamlit UI
Natural Language to SQL Conversion Interface

Run with: streamlit run app.py
"""

import streamlit as st
from config import setup_logging
from src import run_graph, validate_openai_connection, validate_database_connection

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
**Describe your request in plain English.** Be specific: include date ranges, filters, columns, and whether you want a full table or a sample. 

This assistant is **read-only** and will never modify the database. The app will display the result table (first 500 rows) — no download is provided.
""")

st.markdown("---")

# =============================================================================
# INPUT SECTION
# =============================================================================

user_query = st.text_area(
    "Enter your query:",
    placeholder="Example: Show me all projects from 2023 with their budgets and client names",
    height=100,
    help="Describe what data you want to see in plain English"
)

# Controls row
col1, col2, col3 = st.columns([1, 1, 4])

with col1:
    show_sql = st.checkbox("Show SQL", value=False, help="Display the generated SQL query")

with col2:
    submit_button = st.button("Submit", type="primary", use_container_width=True)

# =============================================================================
# QUERY EXECUTION
# =============================================================================

if submit_button:
    if not user_query.strip():
        st.warning("⚠️ Please enter a query before submitting.")
    else:
        with st.spinner("🔄 Processing your query..."):
            try:
                result = run_graph(
                    user_query=user_query.strip(),
                    show_sql=show_sql,
                    display_cap=500
                )
                
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
    
    # Check for errors first
    if result.get("error"):
        st.error(f"❌ **Error:** {result['error']}")
        
        if result.get("improved_prompt"):
            with st.expander("📝 Improved Prompt", expanded=False):
                st.info(result["improved_prompt"])
        
        st.stop()
    
    # Show improved prompt (collapsed by default)
    if result.get("improved_prompt"):
        with st.expander("📝 Improved Prompt (for transparency)", expanded=False):
            st.info(result["improved_prompt"])
    
    # Show SQL if toggle was ON
    if show_sql and result.get("sql_query"):
        with st.expander("💾 Generated SQL", expanded=True):
            st.code(result["sql_query"], language="sql")
    
    # Display results table
    st.markdown("### Query Results")
    
    metadata = result.get("metadata", {})
    result_message = metadata.get("result_message")
    
    if result_message:
        if "0 rows" in result_message:
            st.warning(result_message)
        else:
            st.info(result_message)
    
    # Display the table
    if result.get("query_results") is not None:
        df = result["query_results"]
        
        if len(df) > 0:
            st.dataframe(df, use_container_width=True, height=400)
            
            total_rows = metadata.get("total_rows", 0)
            displayed_rows = metadata.get("displayed_rows", 0)
            execution_time = metadata.get("execution_time", 0)
            
            st.caption(f"📈 Rows: {displayed_rows} displayed / {total_rows} total | ⏱️ Execution time: {execution_time:.3f}s")
        else:
            st.info("No rows to display.")
    else:
        st.warning("No results returned.")
    
    # Display insights if available
    if result.get("insights"):
        st.markdown("### 💡 Insights")
        st.markdown(result["insights"])

# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.caption("🔒 Read-only database access | No data modifications allowed")