"""
Streamlit App for SQL Learning Assistant
Eager Loading - Load everything at startup
"""

import streamlit as st
import os
import sys
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Add parent directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# PAGE CONFIG - MUST BE FIRST STREAMLIT COMMAND
# =============================================================================

st.set_page_config(
    page_title="SQL Learning Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# LOAD ALL COMPONENTS AT STARTUP (EAGER LOADING)
# =============================================================================

@st.cache_resource(show_spinner=True)
def load_all_components():
    """Load all components at startup."""
    components = {
        'retriever': None,
        'model': None,
        'prompt_builder': None,
        'gemini': None
    }
    
    # 1. Load ChromaDB first
    print("=" * 50)
    print("LOADING ALL COMPONENTS AT STARTUP")
    print("=" * 50)
    
    chromadb_path = "chromadb_data"
    hf_chromadb_id = os.getenv("HF_CHROMADB_ID")
    
    # Check if ChromaDB has actual files
    has_files = False
    if os.path.exists(chromadb_path):
        local_files = os.listdir(chromadb_path) if os.path.isdir(chromadb_path) else []
        has_files = any('chroma' in f.lower() or 'sqlite' in f.lower() for f in local_files) or len(local_files) > 2
    
    if not has_files and hf_chromadb_id:
        print(f"☁️ Downloading ChromaDB from HuggingFace: {hf_chromadb_id}")
        from huggingface_hub import snapshot_download
        os.makedirs(chromadb_path, exist_ok=True)
        snapshot_download(repo_id=hf_chromadb_id, repo_type="dataset", local_dir=chromadb_path)
        print("✓ ChromaDB downloaded!")
    
    # 2. Load RAG Retriever
    try:
        print("Loading RAG Retriever...")
        from rag.retriever import SQLRetriever
        components['retriever'] = SQLRetriever()
        print("✓ RAG Retriever loaded")
    except Exception as e:
        print(f"✗ RAG error: {e}")
    
    # 3. Load Fine-tuned Model
    try:
        print("Loading Fine-tuned Model...")
        from finetuning.inference import SQLGenerator
        components['model'] = SQLGenerator()
        print("✓ Fine-tuned Model loaded")
    except Exception as e:
        print(f"✗ Model error: {e}")
    
    # 4. Load Prompt Builder
    try:
        print("Loading Prompt Builder...")
        from prompts.prompt_builder import PromptBuilder
        components['prompt_builder'] = PromptBuilder()
        print("✓ Prompt Builder loaded")
    except Exception as e:
        print(f"✗ Prompt Builder error: {e}")
    
    # 5. Load Gemini
    try:
        print("Loading Gemini...")
        from pipeline.integrated import GeminiClient, GEMINI_KEYS
        if GEMINI_KEYS:
            components['gemini'] = GeminiClient()
            print("✓ Gemini loaded")
        else:
            print("⚠️ No Gemini API keys found")
    except Exception as e:
        print(f"✗ Gemini error: {e}")
    
    print("=" * 50)
    print("ALL COMPONENTS LOADED")
    print("=" * 50)
    
    return components

# =============================================================================
# LOAD COMPONENTS NOW (AT STARTUP)
# =============================================================================

with st.spinner("🚀 Loading SQL Learning Assistant... Please wait..."):
    COMPONENTS = load_all_components()

retriever = COMPONENTS['retriever']
model = COMPONENTS['model']
prompt_builder = COMPONENTS['prompt_builder']
gemini = COMPONENTS['gemini']

# =============================================================================
# HELPER FUNCTION TO RUN PIPELINE
# =============================================================================

def run_pipeline(question, num_examples=3):
    """Run the full pipeline using pre-loaded components."""
    result = {
        'question': question,
        'success': False,
        'steps': {}
    }
    
    # Step 1: RAG
    rag_context = ""
    examples = []
    if retriever:
        try:
            examples = retriever.retrieve(question, top_k=num_examples)
            rag_context = "Similar SQL examples:\n\n"
            for i, r in enumerate(examples, 1):
                rag_context += f"Example {i}:\nQuestion: {r['question']}\nSQL: {r['sql']}\n\n"
        except Exception as e:
            st.warning(f"RAG error: {e}")
    
    result['steps']['rag'] = {'examples': examples, 'num_examples': len(examples), 'context': rag_context}
    
    # Step 2: Prompt
    prompt = ""
    if prompt_builder:
        try:
            prompt_result = prompt_builder.build_prompt(question=question, rag_context=rag_context)
            if prompt_result['success']:
                prompt = prompt_result['prompt']
        except:
            pass
    if not prompt:
        prompt = f"{rag_context}\nQuestion: {question}\n\nSQL:"
    
    result['steps']['prompt'] = {'prompt': prompt, 'length': len(prompt)}
    
    # Step 3: Fine-tuned Model
    finetuned_sql = None
    if model:
        try:
            finetuned_sql = model.generate(question, rag_context)
        except Exception as e:
            st.warning(f"Model error: {e}")
    
    result['steps']['finetuned'] = {'sql': finetuned_sql, 'error': None if finetuned_sql else 'Model not available'}
    
    if not finetuned_sql:
        return result
    
    # Step 4: Gemini Enhancement
    enhanced_sql = finetuned_sql
    if gemini:
        try:
            enhance_prompt = f"""You are an SQL expert. Review and enhance this SQL query.

Original Question: {question}

Generated SQL (by a smaller model):
{finetuned_sql}

Rules:
- If the SQL is correct, return it unchanged
- If it needs fixes, return the corrected version
- Return ONLY the SQL query, no explanations

Enhanced SQL:"""
            response, error = gemini.generate(enhance_prompt)
            if response and not error:
                enhanced_sql = response.strip()
                if enhanced_sql.startswith("```"):
                    lines = enhanced_sql.split("\n")
                    enhanced_sql = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
                if enhanced_sql.lower().startswith("sql"):
                    enhanced_sql = enhanced_sql[3:].strip()
        except Exception as e:
            st.warning(f"Gemini enhance error: {e}")
    
    result['steps']['gemini_enhance'] = {'sql': enhanced_sql, 'info': {'enhanced': enhanced_sql != finetuned_sql}}
    result['final_sql'] = enhanced_sql
    
    # Step 5: Explanation
    explanation = ""
    if gemini:
        try:
            explain_prompt = f"Explain this SQL query in simple terms (2-3 sentences):\n\nSQL: {enhanced_sql}"
            response, error = gemini.generate(explain_prompt)
            if response and not error:
                explanation = response.strip()
        except:
            pass
    
    result['explanation'] = explanation
    result['success'] = True
    
    return result

# =============================================================================
# CUSTOM CSS
# =============================================================================

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    .main-header {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(120deg, #00d4ff, #7c3aed, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        font-size: 1.1rem;
        color: #94a3b8;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        color: #e2e8f0;
        border: 1px solid #475569;
        border-radius: 10px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        border-color: #60a5fa;
        transform: translateY(-2px);
    }
    
    .stTextInput > div > div > input {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid #475569;
        border-radius: 12px;
        color: #f1f5f9;
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    
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
</style>
""", unsafe_allow_html=True)

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
    num_examples = st.slider("Similar examples to retrieve", min_value=1, max_value=5, value=3)
    
    st.markdown("---")
    
    st.markdown("### 📊 System Status")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("✅ **RAG**" if retriever else "❌ **RAG**")
        st.markdown("✅ **Model**" if model else "❌ **Model**")
    with col2:
        st.markdown("✅ **Prompts**" if prompt_builder else "❌ **Prompts**")
        st.markdown("✅ **Gemini**" if gemini else "❌ **Gemini**")
    
    st.markdown("---")
    
    st.markdown("### 🔄 Pipeline Flow")
    pipeline_steps = [
        ("📦", "Synthetic Data"),
        ("🎓", "Fine-tuned Model"),
        ("❓", "User Question"),
        ("🔍", "RAG Retrieval"),
        ("📝", "Prompt Engineering"),
        ("🤖", "Model Inference"),
        ("✨", "Gemini Enhancement"),
        ("✅", "Final Output"),
    ]
    
    for i, (icon, title) in enumerate(pipeline_steps):
        st.markdown(f'<div class="pipeline-box">{icon} <strong>{title}</strong></div>', unsafe_allow_html=True)
        if i < len(pipeline_steps) - 1:
            st.markdown('<p class="pipeline-arrow">↓</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📚 About")
    st.markdown("**Course:** INFO7375")

# =============================================================================
# MAIN CONTENT
# =============================================================================

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

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"], avatar="🧑‍💻" if message["role"] == "user" else "🤖"):
        st.markdown(message["content"])
        
        if message["role"] == "assistant":
            result_idx = i // 2
            if result_idx < len(st.session_state.results_history):
                result = st.session_state.results_history[result_idx]
                if result and result.get('success'):
                    with st.expander("🔍 View Pipeline Details", expanded=False):
                        tab1, tab2, tab3, tab4 = st.tabs(["🔍 RAG", "📝 Prompt", "🤖 Fine-tuned", "✨ Gemini"])
                        
                        with tab1:
                            examples = result['steps']['rag'].get('examples', [])
                            st.markdown(f"**Retrieved {len(examples)} examples**")
                            for j, ex in enumerate(examples, 1):
                                st.markdown(f"**Example {j}** | Score: `{ex.get('score', 0):.3f}`")
                                st.markdown(f"Q: {ex.get('question', 'N/A')}")
                                st.code(ex.get('sql', 'N/A'), language="sql")
                        
                        with tab2:
                            st.markdown("**Constructed Prompt:**")
                            st.code(result['steps']['prompt'].get('prompt', 'N/A'), language="text")
                        
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
    st.session_state.messages.append({"role": "user", "content": question})
    
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(question)
    
    with st.chat_message("assistant", avatar="🤖"):
        with st.status("🔄 Processing your query...", expanded=True) as status:
            st.write("🔍 Retrieving similar examples...")
            st.write("📝 Building prompt...")
            st.write("🤖 Generating SQL...")
            st.write("✨ Enhancing with Gemini...")
            
            result = run_pipeline(question=question, num_examples=num_examples)
            
            status.update(label="✅ Complete!", state="complete", expanded=False)
        
        st.session_state.results_history.append(result)
        
        if result['success']:
            st.markdown("### ✅ Generated SQL")
            st.code(result['final_sql'], language="sql")
            
            if 'gemini_enhance' in result['steps']:
                original = result['steps']['finetuned'].get('sql', '')
                enhanced = result['steps']['gemini_enhance'].get('sql', '')
                if original != enhanced:
                    st.success("✨ Query optimized by Gemini!")
                else:
                    st.info("✓ Query was already optimal")
            
            if 'explanation' in result and result['explanation']:
                if not result['explanation'].startswith("Explanation error"):
                    st.markdown("### 📖 Explanation")
                    st.info(result['explanation'])
            
            with st.expander("🔍 View Pipeline Details", expanded=False):
                tab1, tab2, tab3, tab4 = st.tabs(["🔍 RAG", "📝 Prompt", "🤖 Fine-tuned", "✨ Gemini"])
                
                with tab1:
                    examples = result['steps']['rag'].get('examples', [])
                    st.markdown(f"**Retrieved {len(examples)} examples**")
                    for j, ex in enumerate(examples, 1):
                        st.markdown(f"**Example {j}** | Score: `{ex.get('score', 0):.3f}`")
                        st.markdown(f"Q: {ex.get('question', 'N/A')}")
                        st.code(ex.get('sql', 'N/A'), language="sql")
                
                with tab2:
                    st.markdown("**Constructed Prompt:**")
                    st.code(result['steps']['prompt'].get('prompt', 'N/A'), language="text")
                
                with tab3:
                    st.markdown("**Fine-tuned Model Output:**")
                    st.code(result['steps']['finetuned'].get('sql', 'N/A'), language="sql")
                
                with tab4:
                    if 'gemini_enhance' in result['steps']:
                        st.markdown("**Enhanced SQL:**")
                        st.code(result['steps']['gemini_enhance'].get('sql', 'N/A'), language="sql")
            
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
    st.markdown('<p style="text-align: center; color: #64748b;">Built with ❤️ using Streamlit • LangChain • Gemini</p>', unsafe_allow_html=True)

with col3:
    st.markdown('<p style="text-align: right; color: #64748b;"><strong>INFO7375</strong></p>', unsafe_allow_html=True)