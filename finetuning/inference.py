"""
Inference Module for Fine-Tuned SQL Model
Loads from: Local checkpoint OR Hugging Face Hub
"""

import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# Hugging Face Model ID (set in .env or Streamlit secrets)
HF_MODEL_ID = os.getenv("HF_MODEL_ID", None)

# Local paths
LOCAL_MODEL_DIR = "outputs/finetuning/checkpoints/final"
BASE_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# =============================================================================
# SQL GENERATOR CLASS
# =============================================================================

class SQLGenerator:
    """SQL Generation using fine-tuned model."""
    
    def __init__(self):
        """Load the fine-tuned model from local or HuggingFace."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Device: {self.device}")
        
        load_path = self._get_model_path()
        
        # Load tokenizer and model
        print(f"Loading model from: {load_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(load_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            load_path,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None,
            trust_remote_code=True
        )
        
        self.tokenizer.pad_token = self.tokenizer.eos_token
        print("✓ Model loaded!")
    
    def _get_model_path(self):
        """Determine where to load model from."""
        
        # Check for required model files (not just folder existence)
        required_files = ['config.json', 'tokenizer.json', 'tokenizer_config.json']
        
        # Priority 1: Local checkpoint with actual model files
        if os.path.exists(LOCAL_MODEL_DIR):
            local_files = os.listdir(LOCAL_MODEL_DIR) if os.path.isdir(LOCAL_MODEL_DIR) else []
            has_model_files = any(f in local_files for f in required_files) or any(f.endswith('.safetensors') or f.endswith('.bin') for f in local_files)
            
            if has_model_files:
                print(f"📁 Found local model checkpoint: {LOCAL_MODEL_DIR}")
                return LOCAL_MODEL_DIR
            else:
                print(f"⚠️ Local folder exists but no model files found")
        
        # Priority 2: Download from HuggingFace Hub
        if HF_MODEL_ID:
            print(f"☁️ Downloading model from HuggingFace: {HF_MODEL_ID}")
            return HF_MODEL_ID
        
        # Priority 3: Base model fallback
        print("⚠️ No fine-tuned model found, using base model")
        return BASE_MODEL
    
    def generate(self, question, context="", max_tokens=128):
        """Generate SQL from question."""
        
        # Build prompt
        if context:
            prompt = f"""{context}

### Question:
{question}

### SQL:"""
        else:
            prompt = f"""### Question:
{question}

### SQL:"""
        
        # Tokenize
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        ).to(self.device)
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=0.1,
                do_sample=True,
                top_p=0.95,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode
        generated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract SQL
        sql = generated[len(prompt):].strip()
        if "###" in sql:
            sql = sql.split("###")[0].strip()
        
        return sql

# =============================================================================
# STANDALONE FUNCTION
# =============================================================================

_generator = None

def generate_sql(question, context=""):
    """Standalone SQL generation."""
    global _generator
    if _generator is None:
        _generator = SQLGenerator()
    return _generator.generate(question, context)

# =============================================================================
# TEST
# =============================================================================

def test_inference():
    """Test the model."""
    print("=" * 60)
    print("TESTING SQL GENERATION")
    print("=" * 60)
    
    generator = SQLGenerator()
    
    questions = [
        "Find all employees with salary greater than 50000",
    ]
    
    print("\n" + "-" * 60)
    for q in questions:
        print(f"Q: {q}")
        sql = generator.generate(q)
        print(f"SQL: {sql}")
        print("-" * 60)
    
    print("\n✓ Test complete")

if __name__ == "__main__":
    test_inference()