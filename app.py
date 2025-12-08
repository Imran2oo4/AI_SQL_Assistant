"""
Streamlit App for SQL Learning Assistant
Integrates: RAG + Fine-tuned Model + Gemini Enhancement
"""

import streamlit as st
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="SQL Learning Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CUSTOM CSS
# =============================================================================

st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    /* Header styling */
    .main-header {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(120deg, #00d4ff, #7c3aed, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
    }
    
    .sub-header {
        font-size: 1.1rem;
        color: #94a3b8;
        text-align: center;
        margin-bottom: 2rem;
        letter-spacing: 0.5px;
    }
    
    /* Card styling */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    /* SQL output box */
    .sql-box {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid #3b82f6;
        border-radius: 12px;
        padding: 1rem;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.2);
    }
    
    /* Example buttons */
    .stButton > button {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        color: #e2e8f0;
        border: 1px solid #475569;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-size: 0.85rem;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        border-color: #60a5fa;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.4);
        transform: translateY(-2px);
    }
    
    /* Primary button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        border: none;
        font-weight: 600;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
        box-shadow: 0 0 30px rgba(139, 92, 246, 0.5);
    }
    
    /* Input field */
    .stTextInput > div > div > input {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid #475569;
        border-radius: 12px;
        color: #f1f5f9;
        padding: 0.75rem 1rem;
        font-size: 1rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.3);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #f1f5f9;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(30, 41, 59, 0.6);
        border-radius: 10px;
        color: #e2e8f0;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(15, 23, 42, 0.6);
        padding: 0.5rem;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #94a3b8;
        border-radius: 8px;
        padding: 0.5rem 1rem;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        color: white;
    }
    
    /* Chat messages */
    [data-testid="stChatMessage"] {
        background: rgba(30, 41, 59, 0.4);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 1rem;
    }
    
    /* Success/Info boxes */
    .stSuccess {
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.3);
        border-radius: 10px;
    }
    
    .stInfo {
        background: rgba(59, 130, 246, 0.1);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 10px;
    }
    
    /* Code blocks */
    .stCodeBlock {
        border-radius: 12px;
        border: 1px solid #3b82f6;
    }
    
    /* Slider */
    .stSlider > div > div {
        background: #334155;
    }
    
    .stSlider > div > div > div > div {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
    }
    
    /* Status indicators */
    .status-on {
        color: #22c55e;
        font-weight: 600;
    }
    
    .status-off {
        color: #ef4444;
        font-weight: 600;
    }
    
    /* Pipeline flow */
    .pipeline-box {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid #475569;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        margin: 0.25rem 0;
        font-size: 0.85rem;
        text-align: center;
    }
    
    .pipeline-arrow {
        color: #3b82f6;
        text-align: center;
        font-size: 1.2rem;
    }
    
    /* Divider */
    hr {
        border-color: rgba(255, 255, 255, 0.1);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #3b82f6;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# LOAD PIPELINE (CACHED)
# =============================================================================

@st.cache_resource
def load_pipeline():
    """Load the integrated pipeline (cached)."""
    try:
        from pipeline.integrated import IntegratedPipeline
        return IntegratedPipeline()
    except Exception as e:
        st.error(f"Error loading pipeline: {e}")
        return None

# =============================================================================
# HEADER
# =============================================================================

st.markdown('<p class="main-header">⚡ SQL Learning Assistant</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Transform Natural Language into SQL using AI-Powered Pipeline</p>', unsafe_allow_html=True)

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    
    st.markdown("---")
    
    st.markdown("### 🎯 RAG Settings")
    num_examples = st.slider(
        "Similar examples to retrieve",
        min_value=1,
        max_value=5,
        value=3,
        help="Number of similar SQL examples to retrieve from knowledge base"
    )
    
    st.markdown("---")
    
    # Component status
    st.markdown("### 📊 System Status")
    pipeline = load_pipeline()
    
    if pipeline:
        status = pipeline.get_component_status()
        
        col1, col2 = st.columns(2)
        with col1:
            if status.get('rag'):
                st.markdown("✅ **RAG**")
            else:
                st.markdown("❌ **RAG**")
            
            if status.get('finetuned_model'):
                st.markdown("✅ **Model**")
            else:
                st.markdown("❌ **Model**")
        
        with col2:
            if status.get('prompt_builder'):
                st.markdown("✅ **Prompts**")
            else:
                st.markdown("❌ **Prompts**")
            
            if status.get('gemini'):
                st.markdown("✅ **Gemini**")
            else:
                st.markdown("❌ **Gemini**")
    
    st.markdown("---")
    
    # Pipeline Flow
    st.markdown("### 🔄 Pipeline Flow")
    
    pipeline_steps = [
        ("📦", "Synthetic Data", "Training augmentation"),
        ("🎓", "Fine-tuned Model", "Domain-specific training"),
        ("❓", "User Question", "Natural language input"),
        ("🔍", "RAG Retrieval", "Similar examples"),
        ("📝", "Prompt Engineering", "Context formatting"),
        ("🤖", "Model Inference", "SQL generation"),
        ("✨", "Gemini Enhancement", "Refinement & explanation"),
        ("✅", "Final Output", "Optimized SQL"),
    ]
    
    for i, (icon, title, desc) in enumerate(pipeline_steps):
        st.markdown(f"""
        <div class="pipeline-box">
            {icon} <strong>{title}</strong><br>
            <small style="color: #94a3b8;">{desc}</small>
        </div>
        """, unsafe_allow_html=True)
        
        if i < len(pipeline_steps) - 1:
            st.markdown('<p class="pipeline-arrow">↓</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### 📚 About")
    st.markdown("""
    <small style="color: #94a3b8;">
    This assistant uses a combination of:
    <br>• <strong>RAG</strong> for context retrieval
    <br>• <strong>Fine-tuned LLM</strong> for SQL generation
    <br>• <strong>Gemini</strong> for enhancement
    <br><br>
    <strong>Course:</strong> INFO7375
    </small>
    """, unsafe_allow_html=True)

# =============================================================================
# MAIN CONTENT
# =============================================================================

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "results_history" not in st.session_state:
    st.session_state.results_history = []

if "input_text" not in st.session_state:
    st.session_state.input_text = ""

# =============================================================================
# EXAMPLE QUESTIONS
# =============================================================================

st.markdown("### 💡 Try an Example")

example_questions = [
    ("👥 Employees", "Find all employees with salary above 50000"),
    ("📊 Orders", "Count total orders by customer"),
    ("🏆 Top Products", "Show top 5 products by revenue"),
    ("📅 Recent", "List customers who placed orders in 2024"),
    ("💰 Salary", "Calculate average salary by department"),
]

cols = st.columns(5)
for i, (label, ex_question) in enumerate(example_questions):
    with cols[i]:
        if st.button(label, key=f"ex_{i}", use_container_width=True, help=ex_question):
            st.session_state.input_text = ex_question

# =============================================================================
# INPUT AREA
# =============================================================================

st.markdown("### 🎤 Ask Your Question")

# Define callback to clear input after submit
def clear_input():
    st.session_state.input_text = ""

col1, col2 = st.columns([6, 1])

with col1:
    question = st.text_input(
        "Question",
        placeholder="e.g., Find all employees with salary greater than 50000...",
        label_visibility="collapsed",
        key="input_text"
    )

with col2:
    submit_btn = st.button("🚀 Run", type="primary", use_container_width=True)

st.markdown("---")

# =============================================================================
# CHAT HISTORY
# =============================================================================

# Display chat history
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"], avatar="🧑‍💻" if message["role"] == "user" else "🤖"):
        st.markdown(message["content"])
        
        # Show SQL result details if it's an assistant message
        if message["role"] == "assistant":
            result_idx = i // 2
            if result_idx < len(st.session_state.results_history):
                result = st.session_state.results_history[result_idx]
                if result and result.get('success'):
                    with st.expander("🔍 View Pipeline Details", expanded=False):
                        tab1, tab2, tab3, tab4 = st.tabs(["🔍 RAG", "📝 Prompt", "🤖 Fine-tuned", "✨ Gemini"])
                        
                        with tab1:
                            examples = result['steps']['rag'].get('examples', [])
                            st.markdown(f"**Retrieved {len(examples)} similar examples**")
                            for j, ex in enumerate(examples, 1):
                                with st.container():
                                    st.markdown(f"""
                                    **Example {j}** | Score: `{ex.get('score', 0):.3f}` | Complexity: `{ex.get('complexity', 'N/A')}`
                                    """)
                                    st.markdown(f"**Q:** {ex.get('question', 'N/A')}")
                                    st.code(ex.get('sql', 'N/A'), language="sql")
                        
                        with tab2:
                            st.markdown("**Constructed Prompt:**")
                            prompt_text = result['steps']['prompt'].get('prompt', 'N/A')
                            st.code(prompt_text, language="text")
                        
                        with tab3:
                            st.markdown("**Fine-tuned Model Output:**")
                            st.code(result['steps']['finetuned'].get('sql', 'N/A'), language="sql")
                        
                        with tab4:
                            if 'gemini_enhance' in result['steps']:
                                st.markdown("**Enhanced SQL:**")
                                st.code(result['steps']['gemini_enhance'].get('sql', 'N/A'), language="sql")

# =============================================================================
# PROCESS QUERY
# =============================================================================

if submit_btn and question:
    # Clear input after processing
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": question})
    
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(question)
    
    with st.chat_message("assistant", avatar="🤖"):
        if not pipeline:
            st.error("❌ Pipeline not loaded!")
            st.session_state.messages.append({"role": "assistant", "content": "❌ Pipeline not loaded!"})
        else:
            # Progress
            with st.status("🔄 Processing your query...", expanded=True) as status:
                st.write("🔍 Retrieving similar examples...")
                
                result = pipeline.run(
                    question=question,
                    enhance=True,
                    explain=True,
                    top_k=num_examples
                )
                
                st.write("📝 Building prompt...")
                st.write("🤖 Generating SQL...")
                st.write("✨ Enhancing with Gemini...")
                
                status.update(label="✅ Complete!", state="complete", expanded=False)
            
            st.session_state.results_history.append(result)
            
            if result['success']:
                # Final SQL
                st.markdown("### ✅ Generated SQL")
                st.code(result['final_sql'], language="sql")
                
                # Enhancement badge
                col1, col2 = st.columns(2)
                with col1:
                    if 'gemini_enhance' in result['steps']:
                        original = result['steps']['finetuned'].get('sql', '')
                        enhanced = result['steps']['gemini_enhance'].get('sql', '')
                        if original != enhanced:
                            st.success("✨ Query optimized by Gemini!")
                        else:
                            st.info("✓ Query was already optimal")
                
                # Explanation
                if 'explanation' in result and result['explanation']:
                    if not result['explanation'].startswith("Explanation error"):
                        st.markdown("### 📖 Explanation")
                        st.info(result['explanation'])
                
                # Details
                with st.expander("🔍 View Pipeline Details", expanded=False):
                    tab1, tab2, tab3, tab4 = st.tabs(["🔍 RAG", "📝 Prompt", "🤖 Fine-tuned", "✨ Gemini"])
                    
                    with tab1:
                        examples = result['steps']['rag'].get('examples', [])
                        st.markdown(f"**Retrieved {len(examples)} similar examples**")
                        for j, ex in enumerate(examples, 1):
                            st.markdown(f"""
                            **Example {j}** | Score: `{ex.get('score', 0):.3f}` | Complexity: `{ex.get('complexity', 'N/A')}`
                            """)
                            st.markdown(f"**Q:** {ex.get('question', 'N/A')}")
                            st.code(ex.get('sql', 'N/A'), language="sql")
                            st.markdown("---")
                    
                    with tab2:
                        st.markdown("**Constructed Prompt:**")
                        prompt_text = result['steps']['prompt'].get('prompt', 'N/A')
                        st.code(prompt_text, language="text")
                    
                    with tab3:
                        st.markdown("**Fine-tuned Model Output:**")
                        st.code(result['steps']['finetuned'].get('sql', 'N/A'), language="sql")
                    
                    with tab4:
                        if 'gemini_enhance' in result['steps']:
                            st.markdown("**Enhanced SQL:**")
                            st.code(result['steps']['gemini_enhance'].get('sql', 'N/A'), language="sql")
                            info = result['steps']['gemini_enhance'].get('info', {})
                            if info.get('enhanced'):
                                st.success("✅ Enhancement applied successfully")
                
                # Save to history
                response_text = f"**Generated SQL:**\n```sql\n{result['final_sql']}\n```"
                if 'explanation' in result and not result['explanation'].startswith("Explanation error"):
                    response_text += f"\n\n**Explanation:** {result['explanation']}"
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            
            else:
                st.error("❌ Failed to generate SQL. Please try again.")
                st.session_state.messages.append({"role": "assistant", "content": "❌ Failed to generate SQL."})

elif submit_btn and not question:
    st.warning("⚠️ Please enter a question first!")

# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.results_history = []
        st.session_state.input_text = ""
        st.rerun()

with col2:
    st.markdown("""
    <p style="text-align: center; color: #64748b; font-size: 0.9rem;">
        Built with ❤️ using <strong>Streamlit</strong> • <strong>LangChain</strong> • <strong>Gemini</strong>
    </p>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <p style="text-align: right; color: #64748b; font-size: 0.9rem;">
        <strong>INFO7375</strong>
    </p>
    """, unsafe_allow_html=True)