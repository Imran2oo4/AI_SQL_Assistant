"""
Integrated Pipeline: RAG + Fine-tuned Model + Gemini Enhancement
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_DIR = "outputs/pipeline"
LOGS_DIR = f"{OUTPUT_DIR}/logs"

# Gemini config - loaded from .env with fallbacks
GEMINI_KEYS = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_FALLBACK_1"),
    os.getenv("GEMINI_API_KEY_FALLBACK_2"),
]
# Remove None values
GEMINI_KEYS = [k for k in GEMINI_KEYS if k]

GEMINI_MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    os.getenv("GEMINI_MODEL_FALLBACK_1"),
]
# Remove None values
GEMINI_MODELS = [m for m in GEMINI_MODELS if m]

if not GEMINI_KEYS:
    print("⚠️ Warning: No GEMINI_API_KEY found in .env file")
else:
    print(f"✓ Found {len(GEMINI_KEYS)} Gemini API key(s)")
    print(f"✓ Found {len(GEMINI_MODELS)} Gemini model(s)")

def setup_directories():
    for d in [OUTPUT_DIR, LOGS_DIR]:
        os.makedirs(d, exist_ok=True)

# =============================================================================
# GEMINI CLIENT WITH FALLBACK
# =============================================================================

class GeminiClient:
    """Gemini client with automatic fallback for rate limits."""
    
    def __init__(self):
        self.genai = None
        self.current_key_idx = 0
        self.current_model_idx = 0
        self.model = None
        self.initialized = False
        
        try:
            import google.generativeai as genai
            self.genai = genai
            self._init_model()
        except ImportError:
            print("✗ google-generativeai not installed")
    
    def _init_model(self):
        """Initialize model with current key and model."""
        if not GEMINI_KEYS:
            return False
        
        key = GEMINI_KEYS[self.current_key_idx]
        model_name = GEMINI_MODELS[self.current_model_idx]
        
        try:
            self.genai.configure(api_key=key)
            self.model = self.genai.GenerativeModel(model_name)
            self.initialized = True
            print(f"  Using API key #{self.current_key_idx + 1}, model: {model_name}")
            return True
        except Exception as e:
            print(f"  Failed to init Gemini: {e}")
            return False
    
    def _switch_to_next(self):
        """Switch to next model or key combination."""
        # Try next model with same key
        if self.current_model_idx < len(GEMINI_MODELS) - 1:
            self.current_model_idx += 1
            print(f"  ⟳ Switching to fallback model: {GEMINI_MODELS[self.current_model_idx]}")
            return self._init_model()
        
        # Try next key with first model
        if self.current_key_idx < len(GEMINI_KEYS) - 1:
            self.current_key_idx += 1
            self.current_model_idx = 0
            print(f"  ⟳ Switching to fallback API key #{self.current_key_idx + 1}")
            return self._init_model()
        
        # No more fallbacks
        print("  ✗ All Gemini keys/models exhausted")
        return False
    
    def generate(self, prompt, max_retries=None):
        """Generate content with automatic fallback."""
        if not self.initialized or not self.model:
            return None, "Gemini not initialized"
        
        # Calculate max retries based on available combinations
        if max_retries is None:
            max_retries = len(GEMINI_KEYS) * len(GEMINI_MODELS)
        
        attempts = 0
        while attempts < max_retries:
            try:
                response = self.model.generate_content(prompt)
                return response.text.strip(), None
            except Exception as e:
                error_str = str(e)
                
                # Check if rate limit error
                if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                    print(f"  ⚠️ Rate limit hit")
                    if not self._switch_to_next():
                        return None, "All API keys exhausted"
                    attempts += 1
                else:
                    # Other error, don't retry
                    return None, error_str
        
        return None, "Max retries exceeded"
    
    def is_available(self):
        """Check if Gemini is available."""
        return self.initialized and self.model is not None


# =============================================================================
# COMPONENT IMPORTS
# =============================================================================

def load_components():
    """Load all pipeline components."""
    components = {}
    
    # 1. RAG Retriever (using SQLRetriever class)
    try:
        from rag.retriever import SQLRetriever
        components['rag'] = SQLRetriever()
        print("✓ RAG Retriever loaded")
    except Exception as e:
        components['rag'] = None
        print(f"✗ RAG not available: {e}")
    
    # 2. Prompt Builder
    try:
        from prompts.prompt_builder import PromptBuilder
        components['prompt_builder'] = PromptBuilder()
        print("✓ Prompt Builder loaded")
    except Exception as e:
        components['prompt_builder'] = None
        print(f"✗ Prompt Builder not available: {e}")
    
    # 3. Fine-tuned Model
    try:
        from finetuning.inference import SQLGenerator
        components['finetuned_model'] = SQLGenerator()
        print("✓ Fine-tuned model loaded")
    except Exception as e:
        components['finetuned_model'] = None
        print(f"✗ Fine-tuned model not available: {e}")
    
    # 4. Gemini with fallback support
    try:
        if GEMINI_KEYS:
            components['gemini'] = GeminiClient()
            if components['gemini'].is_available():
                print("✓ Gemini loaded")
            else:
                components['gemini'] = None
                print("✗ Gemini failed to initialize")
        else:
            components['gemini'] = None
            print("✗ Gemini not available (no API keys)")
    except Exception as e:
        components['gemini'] = None
        print(f"✗ Gemini not available: {e}")
    
    return components

# =============================================================================
# GEMINI ENHANCEMENT PROMPTS
# =============================================================================

GEMINI_REFINE_PROMPT = """You are an SQL expert. Review and enhance this SQL query.

Original Question: {question}

Generated SQL (by a smaller model):
{sql}

Your tasks:
1. Check for syntax errors
2. Check for logical errors
3. Optimize if possible
4. Fix any issues

Rules:
- If the SQL is correct, return it unchanged
- If it needs fixes, return the corrected version
- Return ONLY the SQL query, no explanations

Enhanced SQL:"""

GEMINI_VALIDATE_PROMPT = """You are an SQL validator. Check this SQL query.

Question: {question}
SQL: {sql}

Respond in JSON format:
{{
    "is_valid": true/false,
    "errors": ["list of errors if any"],
    "suggestions": ["list of suggestions if any"],
    "confidence": 0.0-1.0
}}

JSON Response:"""

GEMINI_EXPLAIN_PROMPT = """Explain this SQL query in simple terms.

SQL: {sql}

Provide a brief, beginner-friendly explanation (2-3 sentences):"""

# =============================================================================
# PIPELINE CLASS
# =============================================================================

class IntegratedPipeline:
    """
    Complete pipeline: RAG → Prompt → Fine-tuned Model → Gemini Enhancement
    """
    
    def __init__(self):
        setup_directories()
        print("\n" + "=" * 50)
        print("LOADING PIPELINE COMPONENTS")
        print("=" * 50)
        self.components = load_components()
        print("=" * 50 + "\n")
    
    # -------------------------------------------------------------------------
    # STEP 1: RAG Retrieval
    # -------------------------------------------------------------------------
    def retrieve_context(self, question, top_k=3):
        """Retrieve similar examples using RAG."""
        if not self.components['rag']:
            return "", []
        
        try:
            # Use SQLRetriever's retrieve method
            results = self.components['rag'].retrieve(question, top_k=top_k)
            
            # Format as context string
            context = "Similar SQL examples:\n\n"
            examples = []
            for i, r in enumerate(results, 1):
                context += f"Example {i}:\n"
                context += f"Question: {r['question']}\n"
                context += f"SQL: {r['sql']}\n\n"
                examples.append(r)
            
            return context, examples
        except Exception as e:
            print(f"RAG error: {e}")
            return "", []
    
    def retrieve_context_formatted(self, question, top_k=3):
        """Use SQLRetriever's built-in context formatting."""
        if not self.components['rag']:
            return ""
        
        try:
            return self.components['rag'].retrieve_as_context(question, top_k=top_k)
        except Exception as e:
            print(f"RAG error: {e}")
            return ""
    
    # -------------------------------------------------------------------------
    # STEP 2: Build Prompt
    # -------------------------------------------------------------------------
    def build_prompt(self, question, rag_context):
        """Build prompt with context."""
        if self.components['prompt_builder']:
            result = self.components['prompt_builder'].build_prompt(
                question=question,
                rag_context=rag_context
            )
            if result['success']:
                return result['prompt']
        
        # Fallback: simple prompt
        if rag_context:
            return f"{rag_context}\nQuestion: {question}\n\nSQL:"
        return f"Generate SQL for: {question}\n\nSQL:"
    
    # -------------------------------------------------------------------------
    # STEP 3: Fine-tuned Model Generation
    # -------------------------------------------------------------------------
    def generate_with_finetuned(self, question, context=""):
        """Generate SQL using fine-tuned model."""
        if not self.components['finetuned_model']:
            return None, "Fine-tuned model not available"
        
        try:
            sql = self.components['finetuned_model'].generate(question, context)
            return sql, None
        except Exception as e:
            return None, str(e)
    
    # -------------------------------------------------------------------------
    # STEP 4: Gemini Enhancement
    # -------------------------------------------------------------------------
    def enhance_with_gemini(self, question, sql):
        """Use Gemini to refine/validate the SQL."""
        if not self.components['gemini']:
            return sql, {"enhanced": False, "reason": "Gemini not available"}
        
        try:
            prompt = GEMINI_REFINE_PROMPT.format(question=question, sql=sql)
            enhanced_sql, error = self.components['gemini'].generate(prompt)
            
            if error:
                return sql, {"enhanced": False, "reason": error}
            
            # Clean up response
            enhanced_sql = self._clean_sql(enhanced_sql)
            
            return enhanced_sql, {"enhanced": True, "original": sql}
        except Exception as e:
            return sql, {"enhanced": False, "reason": str(e)}
    
    def validate_with_gemini(self, question, sql):
        """Use Gemini to validate SQL."""
        if not self.components['gemini']:
            return {"is_valid": True, "confidence": 0.5}
        
        try:
            prompt = GEMINI_VALIDATE_PROMPT.format(question=question, sql=sql)
            text, error = self.components['gemini'].generate(prompt)
            
            if error:
                return {"is_valid": True, "confidence": 0.5, "error": error}
            
            # Remove markdown code blocks if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            return json.loads(text)
        except:
            return {"is_valid": True, "confidence": 0.5}
    
    def explain_with_gemini(self, sql):
        """Use Gemini to explain the SQL."""
        if not self.components['gemini']:
            return "Explanation not available"
        
        try:
            prompt = GEMINI_EXPLAIN_PROMPT.format(sql=sql)
            explanation, error = self.components['gemini'].generate(prompt)
            
            if error:
                return f"Explanation error: {error}"
            
            return explanation
        except Exception as e:
            return f"Explanation error: {e}"
    
    # -------------------------------------------------------------------------
    # MAIN PIPELINE
    # -------------------------------------------------------------------------
    def run(self, question, enhance=True, validate=False, explain=False, top_k=3):
        """
        Run the complete pipeline.
        
        Args:
            question: Natural language question
            enhance: Use Gemini to enhance SQL
            validate: Use Gemini to validate SQL
            explain: Use Gemini to explain SQL
            top_k: Number of RAG examples to retrieve
            
        Returns:
            dict with all results
        """
        result = {
            'question': question,
            'timestamp': datetime.now().isoformat(),
            'steps': {}
        }
        
        # Step 1: RAG Retrieval
        rag_context, examples = self.retrieve_context(question, top_k=top_k)
        result['steps']['rag'] = {
            'context': rag_context,
            'examples': examples,
            'num_examples': len(examples)
        }
        
        # Step 2: Build Prompt
        prompt = self.build_prompt(question, rag_context)
        result['steps']['prompt'] = {
            'prompt': prompt,
            'length': len(prompt)
        }
        
        # Step 3: Fine-tuned Model
        finetuned_sql, error = self.generate_with_finetuned(question, rag_context)
        result['steps']['finetuned'] = {
            'sql': finetuned_sql,
            'error': error
        }
        
        if not finetuned_sql:
            result['success'] = False
            result['final_sql'] = None
            return result
        
        # Step 4: Gemini Enhancement
        if enhance:
            enhanced_sql, enhance_info = self.enhance_with_gemini(question, finetuned_sql)
            result['steps']['gemini_enhance'] = {
                'sql': enhanced_sql,
                'info': enhance_info
            }
            result['final_sql'] = enhanced_sql
        else:
            result['final_sql'] = finetuned_sql
        
        # Optional: Validation
        if validate:
            validation = self.validate_with_gemini(question, result['final_sql'])
            result['steps']['validation'] = validation
        
        # Optional: Explanation
        if explain:
            explanation = self.explain_with_gemini(result['final_sql'])
            result['explanation'] = explanation
        
        result['success'] = True
        
        # Log result
        self._log_result(result)
        
        return result
    
    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------
    def _clean_sql(self, sql):
        """Clean SQL output."""
        sql = sql.strip()
        # Remove markdown code blocks
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        # Remove leading 'sql' keyword
        if sql.lower().startswith("sql"):
            sql = sql[3:].strip()
        return sql
    
    def _log_result(self, result):
        """Log pipeline result."""
        log_file = f"{LOGS_DIR}/pipeline_log.jsonl"
        # Remove examples from log to save space
        log_result = {k: v for k, v in result.items()}
        if 'steps' in log_result and 'rag' in log_result['steps']:
            log_result['steps']['rag'] = {
                'num_examples': log_result['steps']['rag'].get('num_examples', 0)
            }
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_result, default=str) + '\n')
    
    def get_component_status(self):
        """Get status of all components."""
        return {
            'rag': self.components['rag'] is not None,
            'prompt_builder': self.components['prompt_builder'] is not None,
            'finetuned_model': self.components['finetuned_model'] is not None,
            'gemini': self.components['gemini'] is not None
        }

# =============================================================================
# SIMPLE INTERFACE
# =============================================================================

_pipeline = None

def get_pipeline():
    """Get or create pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = IntegratedPipeline()
    return _pipeline

def generate_sql(question, enhance=True, explain=False):
    """Simple function to generate SQL."""
    pipeline = get_pipeline()
    result = pipeline.run(question, enhance=enhance, explain=explain)
    
    if result['success']:
        return result['final_sql']
    return None

# =============================================================================
# TEST
# =============================================================================

def test_pipeline():
    """Test the integrated pipeline."""
    
    print("=" * 60)
    print("TESTING INTEGRATED PIPELINE")
    print("=" * 60)
    
    pipeline = IntegratedPipeline()
    
    # Show component status
    print("\nComponent Status:")
    status = pipeline.get_component_status()
    for comp, loaded in status.items():
        icon = "✓" if loaded else "✗"
        print(f"  {icon} {comp}")
    
    questions = [
        "Find all employees with salary above 50000",
    ]
    
    for q in questions:
        print(f"\n{'='*60}")
        print(f"Question: {q}")
        print("-" * 60)
        
        result = pipeline.run(q, enhance=True, explain=True, top_k=3)
        
        # Show RAG results
        print(f"\n[RAG] Retrieved {result['steps']['rag']['num_examples']} examples")
        
        # Show fine-tuned output
        print(f"\n[Fine-tuned Model]")
        if result['steps']['finetuned']['sql']:
            print(f"  SQL: {result['steps']['finetuned']['sql']}")
        else:
            print(f"  Error: {result['steps']['finetuned']['error']}")
        
        # Show Gemini enhancement
        if 'gemini_enhance' in result['steps']:
            print(f"\n[Gemini Enhanced]")
            print(f"  SQL: {result['steps']['gemini_enhance']['sql']}")
            if result['steps']['finetuned']['sql'] != result['steps']['gemini_enhance']['sql']:
                print(f"  ✨ Query was improved!")
        
        # Show final
        print(f"\n[Final SQL]")
        print(f"  {result['final_sql']}")
        
        # Show explanation
        if 'explanation' in result:
            print(f"\n[Explanation]")
            print(f"  {result['explanation']}")
    
    print("\n" + "=" * 60)
    print("✓ Pipeline test complete")
    print("=" * 60)

if __name__ == "__main__":
    test_pipeline()