# ⚡ Prompt to SQL using RAG + LLM

AI-powered Natural Language to SQL conversion using RAG, Fine-tuned LLM, and Gemini Enhancement.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 🌐 Live Demo

- **📄 Project Page:** [GitHub Pages](https://moheesh.github.io/Prompt_to_SQL_using_RAG_LLM)
- **🚀 Web App:** [Streamlit App](https://huggingface.co/spaces/moheesh/sql-learning-assistant)


## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **RAG Retrieval** | 80,000+ SQL examples in ChromaDB vector store |
| 🤖 **Fine-tuned LLM** | TinyLlama with LoRA for SQL generation |
| ✨ **Gemini Enhancement** | Query refinement, validation & explanation |
| 📝 **Prompt Engineering** | Context management, edge cases, query analysis |
| 📦 **Synthetic Data** | Data augmentation with 5 techniques |
| 🔄 **Auto Fallback** | Multiple API keys & models for reliability |

## 🔄 Pipeline Architecture

```
┌─────────────────────┐
│   Synthetic Data    │  (Training augmentation)
└─────────┬───────────┘
          ↓
┌─────────────────────┐
│  Fine-tuned Model   │  (LoRA training on TinyLlama)
└─────────┬───────────┘
          ↓
┌─────────────────────┐
│   User Question     │  (Natural language input)
└─────────┬───────────┘
          ↓
┌─────────────────────┐
│   RAG Retrieval     │  (Similar examples from ChromaDB)
└─────────┬───────────┘
          ↓
┌─────────────────────┐
│ Prompt Engineering  │  (Context + query formatting)
└─────────┬───────────┘
          ↓
┌─────────────────────┐
│  Fine-tuned Model   │  (SQL generation)
└─────────┬───────────┘
          ↓
┌─────────────────────┐
│ Gemini Enhancement  │  (Refine + explain)
└─────────┬───────────┘
          ↓
┌─────────────────────┐
│    Final SQL        │  (Optimized output)
└─────────────────────┘
```

## 📁 Project Structure

```
Prompt_to_SQL_using_RAG_LLM/
├── app.py                    # Streamlit UI
├── config.py                 # Central configuration
├── requirements.txt          # Dependencies
│
├── pipeline/
│   └── integrated.py         # Main pipeline (RAG + Model + Gemini)
│
├── finetuning/
│   ├── prepare_data.py       # Data preparation
│   ├── train.py              # LoRA fine-tuning
│   ├── evaluate.py           # Model evaluation
│   └── inference.py          # SQL generation
│
├── rag/
│   ├── embeddings.py         # Sentence transformers
│   ├── knowledge_base.py     # ChromaDB builder
│   └── retriever.py          # LangChain retriever
│
├── prompts/
│   ├── prompt_builder.py     # Context management
│   └── system_prompts.py     # Prompt templates
│
├── synthetic/
│   ├── generate_data.py      # Data augmentation
│   └── synonyms.py           # Synonym dictionary
│
├── data/
│   ├── train.csv
│   ├── validation.csv
│   └── test.csv
│
└── docs/
    └── index.html            # GitHub Pages
```

## 🛠️ Setup

### 1. Clone the Repository

```bash
git clone https://github.com/moheesh/Prompt_to_SQL_using_RAG_LLM.git
cd Prompt_to_SQL_using_RAG_LLM
```

### 2. Create Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create a `.env` file:

```env
# Gemini API
GEMINI_API_KEY=your-primary-key
GEMINI_MODEL=gemini-2.5-flash

# HuggingFace (for cloud deployment)
HF_TOKEN=your-hf-token
HF_MODEL_ID=your-username/sql-tinyllama-lora
HF_CHROMADB_ID=your-username/sql-chromadb
```

### 5. Build Knowledge Base (First Time)

```bash
python rag/knowledge_base.py
```

### 6. Run the App

```bash
streamlit run app.py
```

## 🚀 Deployment

### Upload to HuggingFace

```bash
# Login
huggingface-cli login

# Upload model
python -c "from huggingface_hub import HfApi; api = HfApi(); api.upload_folder(folder_path='outputs/finetuning/checkpoints/final', repo_id='moheesh/sql-tinyllama-lora', repo_type='model', create_repo=True)"

# Upload ChromaDB
python -c "from huggingface_hub import HfApi; api = HfApi(); api.upload_folder(folder_path='chromadb_data', repo_id='moheesh/sql-chromadb', repo_type='dataset', create_repo=True)"
```

### Deploy to Streamlit Cloud

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo
4. Add secrets (same as `.env`)
5. Deploy!

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| LLM | TinyLlama + LoRA |
| Vector DB | ChromaDB |
| Embeddings | all-MiniLM-L6-v2 |
| Enhancement | Gemini API |
| Framework | LangChain |
| UI | Streamlit |

## 📊 Evaluation Metrics

| Metric | Score |
|--------|-------|
| Exact Match | XX% |
| Token Accuracy | XX% |
| Keyword Accuracy | XX% |
| Structure Similarity | XX% |

## 🎓 Course

**INFO7375** - Northeastern University

## 👤 Author

**Your Name**
- GitHub: [@moheesh](https://github.com/moheesh)
- LinkedIn: [LinkedIn](https://linkedin.com/in/moheesh-k-a-a95306169)

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.