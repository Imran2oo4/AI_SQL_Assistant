"""
TinyLlama SQL Generator with LoRA Support
Generates SQL queries using TinyLlama-1.1B-Chat model with optional LoRA fine-tuning.
"""

import os
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig
)
from peft import PeftModel, PeftConfig
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_MODEL = os.getenv("TINYLLAMA_MODEL_NAME", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
LORA_PATH = os.getenv("TINYLLAMA_LORA_PATH", "./models/tinyllama_lora")
USE_LORA = os.getenv("TINYLLAMA_USE_LORA", "false").lower() == "true"
MAX_LENGTH = int(os.getenv("TINYLLAMA_MAX_LENGTH", "512"))
TEMPERATURE = float(os.getenv("TINYLLAMA_TEMPERATURE", "0.1"))

# =============================================================================
# TINYLLAMA SQL GENERATOR
# =============================================================================

class SQLGenerator:
    """TinyLlama-based SQL generator with LoRA support."""
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        use_lora: bool = USE_LORA,
        lora_path: Optional[str] = LORA_PATH,
        use_4bit: bool = True,
        device: str = "auto"
    ):
        """
        Initialize TinyLlama SQL generator.
        
        Args:
            model_name: HuggingFace model ID
            use_lora: Whether to load LoRA weights
            lora_path: Path to LoRA adapter
            use_4bit: Use 4-bit quantization to save memory
            device: Device to run on ('auto', 'cuda', 'cpu')
        """
        self.model_name = model_name
        self.use_lora = use_lora and os.path.exists(lora_path)
        self.lora_path = lora_path
        self.device = self._get_device(device)
        
        print(f"\n{'='*60}")
        print("Initializing TinyLlama SQL Generator")
        print(f"{'='*60}")
        print(f"Model: {model_name}")
        print(f"LoRA: {self.use_lora}")
        print(f"Device: {self.device}")
        print(f"4-bit Quantization: {use_4bit}")
        
        # Load tokenizer
        self.tokenizer = self._load_tokenizer()
        
        # Load model
        self.model = self._load_model(use_4bit)
        
        print("✓ TinyLlama initialized successfully")
        print(f"{'='*60}\n")
    
    def _get_device(self, device: str) -> str:
        """Determine the device to use."""
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
    
    def _load_tokenizer(self):
        """Load the tokenizer."""
        print("Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            padding_side="left"
        )
        
        # Set pad token if not present
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        return tokenizer
    
    def _load_model(self, use_4bit: bool):
        """Load the model with optional quantization and LoRA."""
        print("Loading model...")
        
        # Quantization config for memory efficiency
        if use_4bit and self.device == "cuda":
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
        else:
            quantization_config = None
        
        # Load base model
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=quantization_config,
            device_map=self.device if self.device != "auto" else "auto",
            trust_remote_code=True,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
        )
        
        # Load LoRA adapter if enabled
        if self.use_lora:
            print(f"Loading LoRA adapter from {self.lora_path}...")
            model = PeftModel.from_pretrained(model, self.lora_path)
            print("✓ LoRA adapter loaded")
        
        model.eval()
        return model
    
    def generate_sql(
        self,
        prompt: str,
        max_length: int = MAX_LENGTH,
        temperature: float = TEMPERATURE,
        top_p: float = 0.9,
        num_return_sequences: int = 1
    ) -> str:
        """
        Generate SQL from prompt.
        
        Args:
            prompt: The full prompt including schema and question
            max_length: Maximum tokens to generate
            temperature: Sampling temperature (lower = more deterministic)
            top_p: Nucleus sampling parameter
            num_return_sequences: Number of sequences to generate
        
        Returns:
            Generated SQL query
        """
        # Tokenize input
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length
        ).to(self.device)
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=temperature,
                top_p=top_p,
                num_return_sequences=num_return_sequences,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode output
        generated_text = self.tokenizer.decode(
            outputs[0],
            skip_special_tokens=True
        )
        
        # Extract SQL (everything after the prompt)
        sql_output = generated_text[len(prompt):].strip()
        
        return sql_output
    
    def batch_generate(
        self,
        prompts: list,
        max_length: int = MAX_LENGTH,
        temperature: float = TEMPERATURE
    ) -> list:
        """
        Generate SQL for multiple prompts in batch.
        
        Args:
            prompts: List of prompts
            max_length: Maximum tokens to generate
            temperature: Sampling temperature
        
        Returns:
            List of generated SQL queries
        """
        results = []
        for prompt in prompts:
            sql = self.generate_sql(prompt, max_length, temperature)
            results.append(sql)
        return results


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_sql_generator(
    model_name: str = DEFAULT_MODEL,
    use_lora: bool = USE_LORA,
    lora_path: Optional[str] = LORA_PATH
) -> SQLGenerator:
    """
    Factory function to create SQL generator.
    
    Args:
        model_name: HuggingFace model ID
        use_lora: Whether to use LoRA
        lora_path: Path to LoRA adapter
    
    Returns:
        SQLGenerator instance
    """
    return SQLGenerator(
        model_name=model_name,
        use_lora=use_lora,
        lora_path=lora_path
    )
