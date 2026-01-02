"""
Streamlit Frontend for Text-to-SQL Application
New UX: Question → SQL → Results → Explanation → Edit & Re-run
"""

import streamlit as st
import requests
import pandas as pd
import json
import time
from typing import Dict, List, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIGURATION - RENDER-COMPATIBLE
# =============================================================================

# Backend URL from environment (Render auto-injects service URLs)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# If BACKEND_URL is just a hostname (from Render), add https://
if BACKEND_URL and not BACKEND_URL.startswith(('http://', 'https://')):
    BACKEND_URL = f"https://{BACKEND_URL}"

print(f"🔗 Frontend configured to use backend: {BACKEND_URL}")

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="AI SQL Query Assistant",
    page_icon="👾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Force sidebar to be open
if 'sidebar_state' not in st.session_state:
    st.session_state.sidebar_state = 'expanded'

# Hide Streamlit's default "Press Enter to apply" hint
st.markdown("""
<style>
    /* Hide the press enter hint in text inputs */
    .stTextInput > div > div > input::placeholder {
        opacity: 0 !important;
    }
    div[data-baseweb="input"] > div::after {
        content: none !important;
    }
    /* Hide instructions text that appears below inputs */
    .stTextInput [data-testid="InputInstructions"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

if 'history' not in st.session_state:
    st.session_state.history = []

if 'current_question' not in st.session_state:
    st.session_state.current_question = ""

if 'current_sql' not in st.session_state:
    st.session_state.current_sql = ""

if 'current_results' not in st.session_state:
    st.session_state.current_results = []

if 'current_explanation' not in st.session_state:
    st.session_state.current_explanation = ""

if 'current_meta' not in st.session_state:
    st.session_state.current_meta = {}

if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False

if 'groq_api_key' not in st.session_state:
    st.session_state.groq_api_key = ""

if 'api_key_reset_counter' not in st.session_state:
    st.session_state.api_key_reset_counter = 0

if 'processing_query' not in st.session_state:
    st.session_state.processing_query = False

if 'query_top_k' not in st.session_state:
    st.session_state.query_top_k = 3

if 'should_process_query' not in st.session_state:
    st.session_state.should_process_query = False

if 'query_question' not in st.session_state:
    st.session_state.query_question = ""

if 'query_top_k_value' not in st.session_state:
    st.session_state.query_top_k_value = 3

if 'suggestion_index' not in st.session_state:
    st.session_state.suggestion_index = 0

if 'last_suggestion_update' not in st.session_state:
    st.session_state.last_suggestion_update = 0

if 'db_connected' not in st.session_state:
    st.session_state.db_connected = False

if 'db_config' not in st.session_state:
    st.session_state.db_config = {
        'host': 'localhost',
        'port': 3306,
        'username': '',
        'password': '',
        'database': '',
        'db_type': 'mysql'
    }

if 'db_schema' not in st.session_state:
    st.session_state.db_schema = {}

if 'show_password' not in st.session_state:
    st.session_state.show_password = False

if 'file_uploaded' not in st.session_state:
    st.session_state.file_uploaded = False

if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None

if 'file_schema' not in st.session_state:
    st.session_state.file_schema = {}

if 'data_source' not in st.session_state:
    st.session_state.data_source = None  # 'database' or 'file'

if 'dynamic_suggestions' not in st.session_state:
    st.session_state.dynamic_suggestions = None

if 'suggestions_loaded' not in st.session_state:
    st.session_state.suggestions_loaded = False

if 'data_source_changed' not in st.session_state:
    st.session_state.data_source_changed = False

# =============================================================================
# API CALLS
# =============================================================================

def validate_groq_key(api_key: str) -> bool:
    """Validate Groq API key by making a test call."""
    if not api_key:
        return False
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        # Test with a minimal request
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=5
        )
        return True
    except Exception as e:
        error_msg = str(e).lower()
        # Only return False if it's clearly an API key issue
        if any(word in error_msg for word in ['api key', 'api_key', 'invalid', 'unauthorized', '401', '403', 'permission']):
            return False
        # For other errors, might still be valid
        return True

def call_ask_api(question: str, top_k: int = 3, groq_api_key: str = None) -> Dict:
    """Call the /ask endpoint."""
    try:
        payload = {
            "question": question,
            "top_k": top_k
        }
        if groq_api_key:
            payload["groq_api_key"] = groq_api_key
        
        response = requests.post(
            f"{BACKEND_URL}/ask",
            json=payload,
            timeout=180
        )
        
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "data": data}
        else:
            try:
                error_detail = response.json().get("detail", {})
                # Handle both dict and string error formats
                if isinstance(error_detail, dict):
                    error_type = error_detail.get("error", "Unknown error")
                    error_msg = error_detail.get("message", "Unknown error occurred")
                else:
                    error_type = "Error"
                    error_msg = str(error_detail) if error_detail else "Unknown error occurred"
                
                # Add helpful context for rate limit errors
                if "rate limit" in error_msg.lower():
                    error_msg += "\n\n💡 Tip: Wait 2-3 minutes between queries when using free tier Groq API."
            except:
                error_type = "Error"
                error_msg = f"Server returned error: {response.status_code}"
            
            return {
                "success": False,
                "error": error_type,
                "message": error_msg
            }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out. The query may be too complex."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Cannot connect to backend server. Is it running?"}
    except Exception as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}


def call_schema_api() -> Dict:
    """Call the /schema endpoint."""
    try:
        response = requests.get(f"{BACKEND_URL}/schema", timeout=10)
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": "Failed to fetch schema"}
    except Exception as e:
        return {"success": False, "error": f"Schema request failed: {str(e)}"}

def call_connect_database_api(host: str, port: int, username: str, password: str, database: str, db_type: str = "mysql") -> Dict:
    """Call the /connect-database endpoint."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/connect-database",
            json={
                "host": host,
                "port": port,
                "username": username,
                "password": password,
                "database": database,
                "db_type": db_type
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": data["success"],
                "message": data["message"],
                "schema": data.get("schema"),
                "tables_count": data.get("tables_count", 0)
            }
        else:
            return {"success": False, "message": "Connection request failed"}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Connection timeout. Please check your host and port."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Cannot connect to backend server. Is it running?"}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}

def call_suggestions_api() -> Dict:
    """Call the /suggestions endpoint to get dynamic suggestions."""
    try:
        response = requests.get(f"{BACKEND_URL}/suggestions", timeout=5)
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "suggestions": []}
    except Exception as e:
        return {"success": False, "suggestions": []}

def call_feedback_api(question: str, sql: str, accepted: bool, corrected_sql: Optional[str] = None) -> Dict:
    """Call the /feedback endpoint."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/feedback",
            json={
                "question": question,
                "sql": sql,
                "accepted": accepted,
                "corrected_sql": corrected_sql
            },
            timeout=10
        )
        return {"success": response.status_code == 200}
    except:
        return {"success": False}


def process_uploaded_file(uploaded_file) -> Dict:
    """Process uploaded CSV or Excel file and convert to SQLite database."""
    try:
        import sqlite3
        import tempfile
        import os
        
        # Reset file pointer to beginning (important for re-reads)
        uploaded_file.seek(0)
        
        # Read the file based on extension
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == 'csv':
            # Try different encodings and handle empty files
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='latin-1')
            except pd.errors.EmptyDataError:
                return {"success": False, "message": "The CSV file is empty"}
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(uploaded_file)
        else:
            return {"success": False, "message": "Unsupported file format. Please upload CSV or Excel files."}
        
        # Validate dataframe is not empty
        if df.empty or len(df.columns) == 0:
            return {"success": False, "message": "File has no data or columns"}
        
        # Create a temporary SQLite database in /tmp which is writable in HF Spaces
        # Use absolute path that both frontend and backend can access
        os.makedirs("/tmp", exist_ok=True)
        temp_db_path = f"/tmp/uploaded_data_{hash(uploaded_file.name)}.db"
        
        # Store data in SQLite
        conn = sqlite3.connect(temp_db_path)
        table_name = uploaded_file.name.split('.')[0].replace(' ', '_').replace('-', '_')
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Get schema
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        
        schema = {table_name: columns}
        
        return {
            "success": True,
            "message": f"Successfully loaded {len(df)} rows from {uploaded_file.name}",
            "schema": schema,
            "db_path": temp_db_path,
            "table_name": table_name,
            "row_count": len(df)
        }
        
    except Exception as e:
        return {"success": False, "message": f"Failed to process file: {str(e)}"}


def call_upload_file_api(db_path: str, table_name: str) -> Dict:
    """Call the backend to register the uploaded file database."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/upload-file",
            json={
                "db_path": db_path,
                "db_type": "sqlite"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": data["success"],
                "message": data["message"],
                "schema": data.get("schema")
            }
        else:
            # Capture detailed error information
            error_detail = f"Status {response.status_code}"
            try:
                error_detail += f": {response.json()}"
            except:
                error_detail += f": {response.text}"
            return {"success": False, "error": error_detail}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Cannot connect to backend server. Is it running?"}
    except Exception as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_header():
    """Render page header."""
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown("<h1><img src='https://fonts.gstatic.com/s/e/notoemoji/latest/1f916/512.gif' alt='🤖' width='48' height='48' style='vertical-align: middle;'> AI SQL Query Assistant</h1>", unsafe_allow_html=True)
        st.markdown("Convert natural language questions into accurate, executable SQL for your database")
    with col2:
        # Vertical status indicators - API Key first, then Database
        if st.session_state.groq_api_key:
            st.success("✅ Groq Active")
        else:
            st.warning("⚠️ API Key Not Configured")
        
        if st.session_state.db_connected:
            st.success("🗄️ DB Connected")
        elif st.session_state.file_uploaded:
            st.success("📂 File Loaded")
        else:
            st.warning("⚠️ Database Not Connected")
    st.divider()


def render_question_input():
    """Render the main question input area."""
    import time
    
    # Check if Groq is activated
    groq_active = st.session_state.get('api_key_valid', False) or bool(st.session_state.groq_api_key)
    
    # Load dynamic suggestions when data source changes or not yet loaded
    should_reload = (
        not st.session_state.suggestions_loaded or
        st.session_state.get('data_source_changed', False)
    )
    
    if should_reload and (st.session_state.db_connected or st.session_state.file_uploaded):
        result = call_suggestions_api()
        if result.get('success') and result.get('data'):
            st.session_state.dynamic_suggestions = result['data'].get('suggestions', [])
            st.session_state.suggestions_loaded = True
            st.session_state.data_source_changed = False
    
    # Use dynamic suggestions if available, otherwise use defaults
    if st.session_state.dynamic_suggestions:
        suggestions = st.session_state.dynamic_suggestions
    else:
        # Default suggestions if API call fails
        suggestions = [
            "Show all records",
            "Count total records",
            "Show recent entries",
            "List unique values",
            "Show records from last month",
            "Count by category",
            "Show top 10 records",
            "List all data"
        ]
    
    # Only rotate suggestions if Groq is active
    if groq_active:
        # Check if 3 seconds have passed and update suggestion
        # Only rerun if the current question is empty (not actively working on a query)
        current_time = time.time()
        if (current_time - st.session_state.last_suggestion_update >= 3 and 
            not st.session_state.current_question and
            not st.session_state.get('api_key_input_active', False)):
            st.session_state.suggestion_index = (st.session_state.suggestion_index + 1) % len(suggestions)
            st.session_state.last_suggestion_update = current_time
            st.rerun()
        
        placeholder_text = f"Try: {suggestions[st.session_state.suggestion_index]}"
    else:
        # Static placeholder when Groq is not active
        placeholder_text = "Enter your question about the database..."
    
    st.subheader("🔎 Natural Language Query")
    
    # Handle clear input flag BEFORE creating the widget
    input_value = st.session_state.current_question
    if st.session_state.get('should_clear_input', False):
        input_value = ""
        st.session_state.current_question = ""
        st.session_state.typed_question = ""
        # Clear the widget's session state key too
        if 'question_input' in st.session_state:
            del st.session_state['question_input']
        st.session_state.should_clear_input = False
    
    question = st.text_area(
        label="Describe the data you want to retrieve from the database",
        value=input_value,
        height=120,
        placeholder=placeholder_text,
        key="question_input",
        on_change=lambda: st.session_state.update({"typed_question": st.session_state.question_input})
    )
    
    # Update typed_question whenever text changes
    if 'typed_question' not in st.session_state:
        st.session_state.typed_question = question
    
    # Show warning if no data source connected
    if not st.session_state.db_connected and not st.session_state.file_uploaded:
        st.warning("⚠️ A database connection or data source is required before generating SQL queries.")
    else:
        # Show data source status
        if st.session_state.file_uploaded:
            st.info(f"📊 Using uploaded file: **{st.session_state.uploaded_file_name}**")
        elif st.session_state.db_connected:
            st.info(f"📊 Connected to database: **{st.session_state.db_config['database']}**")
    
    col1, col2, col3, col4, col5 = st.columns([1.5, 0.3, 1, 0.3, 2])
    
    with col1:
        # Use callback to capture values immediately
        def on_run_query_click():
            """Callback to capture question when button is clicked"""
            st.session_state.should_process_query = True
            st.session_state.query_question = st.session_state.get('typed_question', st.session_state.question_input)
            st.session_state.query_top_k_value = st.session_state.get('top_k_selector', 3)
        
        ask_button = st.button(
            "🚀 Run Query", 
            type="primary", 
            use_container_width=True,
            disabled=(not st.session_state.db_connected and not st.session_state.file_uploaded),
            key="btn_run_query",
            on_click=on_run_query_click
        )
    
    with col3:
        top_k = st.selectbox("Examples", [2, 3, 4, 5], index=1, help="Number of similar examples to use", key="top_k_selector")
    
    with col5:
        def on_clear_query_click():
            """Callback to clear query state"""
            st.session_state.current_question = ""
            st.session_state.current_sql = ""
            st.session_state.current_results = []
            st.session_state.current_explanation = ""
            st.session_state.current_meta = {}
            st.session_state.edit_mode = False
            st.session_state.typed_question = ""
            # Clear the widget's key immediately
            if 'question_input' in st.session_state:
                st.session_state.question_input = ""
            # Set a flag to clear the input on next render
            st.session_state.should_clear_input = True
        
        st.button(
            "✨ Clear Query & Start New Request", 
            use_container_width=True,
            on_click=on_clear_query_click
        )
    
    return question, ask_button, top_k


def render_results_section():
    """Render SQL, results table, and explanation."""
    if not st.session_state.current_sql:
        return
    
    st.divider()
    
    # SQL Display and Edit Section
    st.subheader("Generated SQL")
    
    if st.session_state.edit_mode:
        edited_sql = st.text_area(
            "Edit SQL",
            value=st.session_state.current_sql,
            height=150,
            key="sql_editor"
        )
        
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("✅ Execute", type="primary"):
                st.session_state.current_sql = edited_sql
                st.session_state.edit_mode = False
                st.warning("Custom SQL execution not yet implemented")
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.edit_mode = False
                st.rerun()
    else:
        st.code(st.session_state.current_sql, language="sql")
        
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("📝 Edit SQL"):
                st.session_state.edit_mode = True
                st.rerun()
        with col2:
            if st.button("📋 Copy SQL"):
                st.success("SQL copied to clipboard!")
    
    # Results Table
    if st.session_state.current_results:
        st.subheader(f"Results ({len(st.session_state.current_results)} rows)")
        
        # Convert to DataFrame for better display
        df = pd.DataFrame(st.session_state.current_results)
        
        # Display with scrollable container
        st.dataframe(
            df,
            use_container_width=True,
            height=400
        )
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Results (CSV)",
            data=csv,
            file_name="query_results.csv",
            mime="text/csv"
        )
    elif st.session_state.current_sql:
        st.info("Query returned no results")
    
    # RAG Examples Section (Transparency) - After results, before explanation
    if st.session_state.current_meta and st.session_state.current_meta.get('rag_examples'):
        st.divider()
        st.subheader("📚 Retrieved Examples (RAG)")
        st.caption("Similar question-SQL pairs used to guide the model:")
        
        rag_examples = st.session_state.current_meta['rag_examples']
        for i, example in enumerate(rag_examples, 1):
            with st.expander(f"Example {i}: {example['question'][:80]}...", expanded=False):
                st.markdown(f"**Question:** {example['question']}")
                st.code(example['sql'], language="sql")
                st.caption(f"Relevance score: {example.get('score', 0):.3f}")
    
    # Explanation
    if st.session_state.current_explanation:
        st.divider()
        st.subheader("Explanation")
        st.info(st.session_state.current_explanation)
    
    # Query Details - After explanation
    if st.session_state.current_meta:
        with st.expander("Query Details"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Execution Time", f"{st.session_state.current_meta.get('time_ms', 0):.2f} ms")
                st.write("**Model Chain:**", ", ".join(st.session_state.current_meta.get('model_chain', [])))
            
            with col2:
                st.metric("Result Count", st.session_state.current_meta.get('result_count', 0))
                if st.session_state.current_meta.get('used_examples'):
                    st.write("**Similar Examples Used:**")
                    for ex in st.session_state.current_meta['used_examples'][:3]:
                        st.write(f"- {ex[:80]}...")
    
    # Feedback Section
    render_feedback_section()


def render_feedback_section():
    """Render feedback buttons."""
    st.divider()
    st.subheader("Was this helpful?")
    
    col1, col2, col3 = st.columns([1, 1, 4])
    
    with col1:
        if st.button("👍 Yes, Correct", use_container_width=True):
            call_feedback_api(
                st.session_state.current_question,
                st.session_state.current_sql,
                accepted=True
            )
            st.success("Thank you for your feedback!")
    
    with col2:
        if st.button("👎 Needs Work", use_container_width=True):
            st.session_state.show_correction = True
    
    # Show correction input if user clicked "Needs Work"
    if st.session_state.get('show_correction', False):
        st.write("**Please provide the correct SQL:**")
        corrected_sql = st.text_area("Correct SQL", height=100, key="corrected_sql")
        if st.button("Submit Correction"):
            call_feedback_api(
                st.session_state.current_question,
                st.session_state.current_sql,
                accepted=False,
                corrected_sql=corrected_sql
            )
            st.success("Thank you for helping us improve!")
            st.session_state.show_correction = False


def render_sidebar():
    """Render sidebar with schema and history."""
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Groq API Key input
        with st.expander("🔑 Groq API Key", expanded=True):
            st.markdown("Enter your Groq API key")
            st.markdown("**Get your free API key:** [Groq Console](https://console.groq.com/keys)")
            
            # Use dynamic key to force widget reset when needed
            api_key_input = st.text_input(
                "API Key",
                value=st.session_state.groq_api_key,
                type="password",
                placeholder="",
                key=f"api_key_input_{st.session_state.api_key_reset_counter}"
            )
            
            # Always show the press enter hint below the input box
            st.caption("⏎ Press Enter to apply")
            
            if api_key_input != st.session_state.groq_api_key:
                if api_key_input:
                    # Validate the API key
                    with st.spinner("Validating API key..."):
                        is_valid = validate_groq_key(api_key_input)
                    
                    if is_valid:
                        st.session_state.groq_api_key = api_key_input
                        st.session_state.api_key_valid = True
                        st.success("✅ API key set!")
                        # Brief delay to show success message, then update header
                        import time
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        # Don't save invalid key to session state
                        st.session_state.api_key_valid = False
                        st.error("❌ Invalid API key")
                        if st.button("🔄 Retry", key="retry_api_key"):
                            # Clear everything immediately to remove error message
                            del st.session_state.api_key_valid
                            st.session_state.groq_api_key = ""
                            st.session_state.api_key_reset_counter += 1
                            st.rerun()
                else:
                    st.session_state.groq_api_key = api_key_input
                    if 'api_key_valid' in st.session_state:
                        del st.session_state.api_key_valid
                    st.info("💡 No API key set - Groq features will be disabled")
        
        st.divider()
        
        # Database Configuration Panel
        with st.expander("🗄️ Database Configuration", expanded=False):
            st.markdown("**Connect to your database**")
            
            # Database type selection with callback to update port
            def on_db_type_change():
                """Update port automatically when database type changes"""
                db_type = st.session_state.db_type_select
                if db_type == "MySQL":
                    st.session_state.db_config['port'] = 3306
                    st.session_state.db_port = 3306  # Update widget state too
                elif db_type == "PostgreSQL":
                    st.session_state.db_config['port'] = 5432
                    st.session_state.db_port = 5432  # Update widget state too
                elif db_type == "SQLite":
                    st.session_state.db_config['port'] = 1  # Not used for SQLite
                    st.session_state.db_port = 1
                st.session_state.db_config['db_type'] = db_type.lower().replace('sql', '')
            
            db_type = st.selectbox(
                "Database Type",
                options=["MySQL", "PostgreSQL", "SQLite"],
                index=0,
                key="db_type_select",
                on_change=on_db_type_change
            )
            
            # Initialize port if not set
            if 'port' not in st.session_state.db_config or st.session_state.db_config['port'] is None:
                if db_type == "MySQL":
                    st.session_state.db_config['port'] = 3306
                elif db_type == "PostgreSQL":
                    st.session_state.db_config['port'] = 5432
                elif db_type == "SQLite":
                    st.session_state.db_config['port'] = 1
            
            # Sync widget state with config state
            if 'db_port' not in st.session_state:
                st.session_state.db_port = st.session_state.db_config['port']
            
            # Connection fields
            col1, col2 = st.columns([2, 1])
            with col1:
                host = st.text_input(
                    "Host",
                    value=st.session_state.db_config['host'],
                    key="db_host",
                    help=" ",
                    disabled=(db_type == "SQLite")
                )
            with col2:
                port = st.number_input(
                    "Port",
                    value=st.session_state.db_config['port'],
                    min_value=1,
                    max_value=65535,
                    key="db_port",
                    disabled=(db_type == "SQLite")
                )
            
            username = st.text_input(
                "Username",
                value=st.session_state.db_config['username'],
                key="db_username",
                help=" "
            )
            
            password = st.text_input(
                "Password",
                value=st.session_state.db_config['password'],
                type="password",
                key="db_password",
                help=" "
            )
            
            database = st.text_input(
                "Database Name",
                value=st.session_state.db_config['database'],
                key="db_database",
                help=" "
            )
            
            # Connect button
            if st.button("🔌 Connect to Database", type="primary", use_container_width=True):
                if not all([host, username, password, database]):
                    st.error("Please fill in all connection fields")
                else:
                    with st.spinner("Connecting to database..."):
                        result = call_connect_database_api(
                            host=host,
                            port=port,
                            username=username,
                            password=password,
                            database=database,
                            db_type=st.session_state.db_config['db_type']
                        )
                    
                    if result['success']:
                        st.session_state.db_connected = True
                        st.session_state.db_config.update({
                            'host': host,
                            'port': port,
                            'username': username,
                            'password': password,
                            'database': database
                        })
                        st.session_state.db_schema = result.get('schema', {})
                        st.session_state.data_source = 'database'
                        # Clear file schema when connecting to database
                        st.session_state.file_uploaded = False
                        st.session_state.file_schema = {}
                        st.session_state.uploaded_file_name = None
                        st.success(result['message'])
                        st.rerun()
                    else:
                        st.error(f"❌ {result['message']}")
            
            # Connection status
            if st.session_state.db_connected:
                st.success(f"✅ Connected to {st.session_state.db_config['database']}")
                st.caption(f"{len(st.session_state.db_schema)} tables available")
                if st.button("🔌 Disconnect", use_container_width=True):
                    st.session_state.db_connected = False
                    st.session_state.db_schema = {}
                    st.session_state.data_source = None
                    st.rerun()
        
        st.divider()
        
        # File Upload Panel
        with st.expander("📂 Upload Data File", expanded=True):
            st.markdown("**Analyze data from CSV or Excel file**")
            st.caption("Upload a CSV or Excel file to analyze your data without connecting to a database")
            
            # File upload status
            if st.session_state.file_uploaded:
                st.success(f"✅ File loaded: {st.session_state.uploaded_file_name}")
                # Show detailed schema info
                if st.session_state.file_schema:
                    with st.expander("📊 View File Schema", expanded=False):
                        for table, cols in st.session_state.file_schema.items():
                            st.write(f"**Table: {table}**")
                            st.write(f"Columns ({len(cols)}): {', '.join(cols)}")
                st.caption(f"{len(st.session_state.file_schema)} table(s) available")
                if st.button("🗑️ Remove File", use_container_width=True, key="btn_remove_file"):
                    st.session_state.file_uploaded = False
                    st.session_state.uploaded_file_name = None
                    st.session_state.file_schema = {}
                    st.session_state.data_source = None
                    st.rerun()
            else:
                # File uploader with session state persistence
                uploaded_file = st.file_uploader(
                    "Choose a CSV or Excel file",
                    type=['csv', 'xlsx', 'xls'],
                    help="Select a file and click the button below to process",
                    key="file_uploader"
                )
                
                # Store file in session state when uploaded
                if uploaded_file is not None:
                    st.session_state.temp_file = uploaded_file
                    st.info(f"📄 **{uploaded_file.name}** ({uploaded_file.size:,} bytes)")
                elif 'temp_file' in st.session_state and st.session_state.temp_file is not None:
                    st.info(f"📄 **{st.session_state.temp_file.name}** ({st.session_state.temp_file.size:,} bytes)")
                
                # Upload button
                if st.button("📤 Upload and Process", type="primary", use_container_width=True, key="btn_upload_file"):
                    file_to_process = st.session_state.get('temp_file', None) or uploaded_file
                    
                    if file_to_process is None:
                        st.error("⚠️ Please select a file first")
                    else:
                        with st.spinner("Processing file..."):
                            try:
                                result = process_uploaded_file(file_to_process)
                                
                                if result['success']:
                                    # Register with backend
                                    backend_result = call_upload_file_api(
                                        db_path=result['db_path'],
                                        table_name=result['table_name']
                                    )
                                    
                                    if backend_result['success']:
                                        st.session_state.file_uploaded = True
                                        st.session_state.uploaded_file_name = file_to_process.name
                                        st.session_state.file_schema = backend_result.get('schema', result.get('schema', {}))
                                        st.session_state.data_source = 'file'
                                        st.session_state.db_connected = False
                                        st.session_state.db_schema = {}
                                        st.session_state.temp_file = None
                                        st.session_state.data_source_changed = True  # Trigger suggestions reload
                                        st.success("✅ File uploaded and processed successfully!")
                                        st.balloons()
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Backend error: {backend_result.get('error', 'Unknown error')}")
                                else:
                                    st.error(f"❌ Processing error: {result.get('error', 'Unknown error')}")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
        
        st.divider()
        st.header("Data Schema")
        
        # Show schema only from connected database or uploaded file
        if st.session_state.db_connected and st.session_state.db_schema:
            schema_data = {'tables': st.session_state.db_schema, 'fks': []}
            st.info(f"📊 Schema from **{st.session_state.db_config['database']}** database")
            
            with st.expander("📊 View Tables", expanded=True):
                for table_name, columns in schema_data['tables'].items():
                    st.write(f"**{table_name}**")
                    for col in columns:
                        st.write(f"  • {col}")
                    st.write("")
        elif st.session_state.file_uploaded and st.session_state.file_schema:
            st.info(f"📊 Schema from uploaded file: **{st.session_state.uploaded_file_name}**")
            
            with st.expander("📊 View Tables", expanded=True):
                for table_name, columns in st.session_state.file_schema.items():
                    st.write(f"**{table_name}**")
                    for col in columns:
                        st.write(f"  • {col}")
                    st.write("")
        else:
            st.warning("⚠️ No data source connected. Please connect to a database or upload a file to see the schema.")
        
        st.divider()
        
        # Query History
        st.header("Recent Queries")
        if st.session_state.history:
            for i, item in enumerate(reversed(st.session_state.history[-5:])):
                with st.expander(f"Query {len(st.session_state.history) - i}"):
                    st.write("**Question:**", item['question'][:100] + "...")
                    st.code(item['sql'][:150] + "...", language="sql")
                    if st.button("Reload", key=f"reload_{i}"):
                        st.session_state.current_question = item['question']
                        st.session_state.current_sql = item['sql']
                        st.session_state.current_results = item.get('results', [])
                        st.session_state.current_explanation = item.get('explanation', '')
                        st.rerun()
        else:
            st.write("No recent queries")


# =============================================================================
# MAIN APP
# =============================================================================

def main():
    """Main application logic."""
    
    # Render UI components
    render_header()
    question, ask_button, top_k = render_question_input()
    
    # Check if we should process a query (set by button callback)
    if st.session_state.should_process_query:
        # Reset flag
        st.session_state.should_process_query = False
        
        # Get the question and top_k from session state (captured by callback)
        question = st.session_state.query_question
        top_k = st.session_state.query_top_k_value
        
        # Validate inputs
        if not question or question.strip() == "":
            st.error("⚠️ Please enter a question in the text box above")
        elif not st.session_state.groq_api_key or st.session_state.groq_api_key.strip() == "":
            st.error("❌ Please enter your Groq API key in the sidebar first")
        else:
            # Store question for display
            st.session_state.current_question = question
            
            # First, make a quick API call to validate the question
            with st.spinner("Validating question..."):
                result = call_ask_api(question, top_k, st.session_state.groq_api_key)
            
            # Check for irrelevant question error - show warning and stop
            if not result['success'] and 'Irrelevant Question' in result.get('error', ''):
                st.warning(f"⚠️ {result.get('message', 'Invalid question, please ask about the database.')}")
                st.stop()
            
            # Check for API key validation error
            if not result['success'] and 'Invalid API Key' in result.get('error', ''):
                st.session_state.api_key_valid = False
                st.error("❌ Invalid API key. Please check your Groq API key in the sidebar.")
                st.stop()
            
            # If we get here, question is valid - show the processing flow
            # Add CSS for rotating gear emojis in steps
            st.markdown("""
            <style>
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .spinning {
                display: inline-block;
                animation: spin 1s linear infinite;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Create live process pipeline in a styled container
            title_placeholder = st.empty()
            title_placeholder.markdown("### ⏳ Query Processing Flow", unsafe_allow_html=True)
            
            # Create a container with border styling
            pipeline_container = st.container(border=True)
            
            with pipeline_container:
                # Create columns with arrows between them
                cols = st.columns([1, 0.2, 1, 0.2, 1, 0.2, 1, 0.2, 1])
                
                # Create placeholders for each step that can be updated
                step1 = cols[0].empty()
                arrow1 = cols[1].empty()
                step2 = cols[2].empty()
                arrow2 = cols[3].empty()
                step3 = cols[4].empty()
                arrow3 = cols[5].empty()
                step4 = cols[6].empty()
                arrow4 = cols[7].empty()
                step5 = cols[8].empty()
                
                # Step 1: Schema Analysis
                step1.markdown("<div><span class='spinning'>⚙️</span> <strong>Schema Analysis</strong><br><small>Extracting table structures and constraints</small></div>", unsafe_allow_html=True)
                time.sleep(0.4)
                step1.markdown("✅ **Schema Analysis**\n\n<small style='color: green;'>Structures and constraints extracted</small>", unsafe_allow_html=True)
                arrow1.markdown("<h3 style='text-align: center; color: #00cc00;'>→</h3>", unsafe_allow_html=True)
                
                # Step 2: RAG Context Retrieval
                step2.markdown("<div><span class='spinning'>⚙️</span> <strong>RAG Context Retrieval</strong><br><small>Finding similar question-SQL pairs</small></div>", unsafe_allow_html=True)
                time.sleep(0.4)
                step2.markdown("✅ **RAG Context Retrieval**\n\n<small style='color: green;'>Similar question-SQL pairs found</small>", unsafe_allow_html=True)
                arrow2.markdown("<h3 style='text-align: center; color: #00cc00;'>→</h3>", unsafe_allow_html=True)
                
                # Step 3: SQL Generation (already called, just show animation)
                step3.markdown("<div><span class='spinning'>⚙️</span> <strong>SQL Generation</strong><br><small>Groq AI generating query</small></div>", unsafe_allow_html=True)
                time.sleep(0.4)
                
                # Check result (already validated earlier, but handle other errors)
                if not result['success']:
                    step3.markdown("❌ **SQL Generation**\n\n<small style='color: red;'>Generation failed</small>", unsafe_allow_html=True)
                    title_placeholder.markdown("### ❌ Query Processing Flow", unsafe_allow_html=True)
                    st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
                    st.stop()
                
                # Success - show remaining steps
                step3.markdown("✅ **SQL Generation**\n\n<small style='color: green;'>Query generated</small>", unsafe_allow_html=True)
                arrow3.markdown("<h3 style='text-align: center; color: #00cc00;'>→</h3>", unsafe_allow_html=True)
                
                # Step 4: Query Execution
                step4.markdown("<div><span class='spinning'>⚙️</span> <strong>Query Execution</strong><br><small>Running query on database</small></div>", unsafe_allow_html=True)
                time.sleep(0.4)
                step4.markdown("✅ **Query Execution**\n\n<small style='color: green;'>Query executed successfully</small>", unsafe_allow_html=True)
                arrow4.markdown("<h3 style='text-align: center; color: #00cc00;'>→</h3>", unsafe_allow_html=True)
                
                # Step 5: AI Explanation
                step5.markdown("<div><span class='spinning'>⚙️</span> <strong>AI Explanation</strong><br><small>Generating human explanation</small></div>", unsafe_allow_html=True)
                time.sleep(0.3)
                step5.markdown("✅ **AI Explanation**\n\n<small style='color: green;'>Human explanation generated</small>", unsafe_allow_html=True)
                
                # Update title to show completion
                title_placeholder.markdown("### ✅ Query Processing Flow", unsafe_allow_html=True)
            
            if result['success']:
                data = result['data']
                
                # Update session state
                st.session_state.current_sql = data['sql']
                st.session_state.current_results = data['results']
                st.session_state.current_explanation = data['explanation']
                st.session_state.current_meta = data['meta']
                
                # Add to history
                st.session_state.history.append({
                    'question': question,
                    'sql': data['sql'],
                    'results': data['results'],
                    'explanation': data['explanation']
                })
                
                st.success("🎉 All steps completed successfully! Scroll down to see the results.")
            else:
                st.error(f"❌ Error: {result['error']}")
    
    # Render results section
    render_results_section()
    
    # Render sidebar
    render_sidebar()
    
    # Footer
    st.divider()
    st.caption("AI SQL Assistant v2.0 | Schema-aware natural language to SQL generation powered by RAG and LLM inference")


if __name__ == "__main__":
    main()
