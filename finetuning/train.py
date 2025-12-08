"""
Fine-Tuning Script for SQL Generation Model
Uses LoRA for efficient fine-tuning.
"""

import os
import json
import torch
from datetime import datetime
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType

# =============================================================================
# CONFIGURATION
# =============================================================================

MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
OUTPUT_DIR = "outputs/finetuning"
CHECKPOINT_DIR = f"{OUTPUT_DIR}/checkpoints"
LOGS_DIR = f"{OUTPUT_DIR}/logs"

# Training config (optimized for RTX 4070)
TRAINING_CONFIG = {
    'num_epochs': 3,
    'batch_size': 8,
    'learning_rate': 2e-4,
    'max_length': 256,
    'warmup_steps': 100,
    'logging_steps': 50,
    'save_steps': 500,
    'gradient_accumulation_steps': 2,
}

# LoRA config
LORA_CONFIG = {
    'r': 16,
    'lora_alpha': 32,
    'lora_dropout': 0.1,
    'target_modules': ['q_proj', 'v_proj', 'k_proj', 'o_proj']
}

def setup_directories():
    for d in [OUTPUT_DIR, CHECKPOINT_DIR, LOGS_DIR]:
        os.makedirs(d, exist_ok=True)

# =============================================================================
# TRAINING FUNCTIONS
# =============================================================================

def load_data():
    """Load prepared training data."""
    train_file = f"{OUTPUT_DIR}/train.jsonl"
    val_file = f"{OUTPUT_DIR}/val.jsonl"
    
    if not os.path.exists(train_file):
        raise FileNotFoundError("Run prepare_data.py first!")
    
    return load_dataset('json', data_files={
        'train': train_file,
        'validation': val_file
    })

def setup_model():
    """Load model and tokenizer with LoRA."""
    print(f"Loading: {MODEL_NAME}")
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=LORA_CONFIG['r'],
        lora_alpha=LORA_CONFIG['lora_alpha'],
        lora_dropout=LORA_CONFIG['lora_dropout'],
        target_modules=LORA_CONFIG['target_modules']
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    return model, tokenizer

def tokenize(examples, tokenizer):
    """Tokenize examples."""
    return tokenizer(
        examples['text'],
        truncation=True,
        padding='max_length',
        max_length=TRAINING_CONFIG['max_length']
    )

def train(model, tokenizer, dataset):
    """Train the model."""
    
    # Tokenize
    print("Tokenizing...")
    tokenized_train = dataset['train'].map(
        lambda x: tokenize(x, tokenizer),
        batched=True,
        remove_columns=dataset['train'].column_names
    )
    tokenized_val = dataset['validation'].map(
        lambda x: tokenize(x, tokenizer),
        batched=True,
        remove_columns=dataset['validation'].column_names
    )
    
    # Training args
    training_args = TrainingArguments(
        output_dir=CHECKPOINT_DIR,
        num_train_epochs=TRAINING_CONFIG['num_epochs'],
        per_device_train_batch_size=TRAINING_CONFIG['batch_size'],
        per_device_eval_batch_size=TRAINING_CONFIG['batch_size'],
        learning_rate=TRAINING_CONFIG['learning_rate'],
        warmup_steps=TRAINING_CONFIG['warmup_steps'],
        logging_steps=TRAINING_CONFIG['logging_steps'],
        save_steps=TRAINING_CONFIG['save_steps'],
        gradient_accumulation_steps=TRAINING_CONFIG['gradient_accumulation_steps'],
        eval_strategy="steps",
        eval_steps=TRAINING_CONFIG['save_steps'],
        save_total_limit=2,
        fp16=True,
        report_to="none",
        logging_dir=LOGS_DIR,
        dataloader_pin_memory=False,
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_val,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    )
    
    # Train
    print(f"\nTraining: {len(tokenized_train)} samples, {TRAINING_CONFIG['num_epochs']} epochs")
    result = trainer.train()
    
    # Save
    print("\nSaving model...")
    trainer.save_model(f"{CHECKPOINT_DIR}/final")
    tokenizer.save_pretrained(f"{CHECKPOINT_DIR}/final")
    
    # Stats
    stats = {
        'train_loss': result.training_loss,
        'runtime_seconds': result.metrics['train_runtime'],
        'samples_per_second': result.metrics['train_samples_per_second'],
        'epochs': TRAINING_CONFIG['num_epochs'],
        'total_steps': result.global_step,
        'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU',
        'completed_at': datetime.now().isoformat()
    }
    
    with open(f"{CHECKPOINT_DIR}/training_stats.json", 'w') as f:
        json.dump(stats, f, indent=2)
    
    return stats

# =============================================================================
# MAIN
# =============================================================================

def run_finetuning():
    """Main function."""
    
    print("=" * 60)
    print("FINE-TUNING SQL MODEL")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("GPU: Not available (using CPU)")
    print("=" * 60)
    
    setup_directories()
    
    # Load data
    print("\n[1/3] Loading data...")
    dataset = load_data()
    print(f"  Train: {len(dataset['train']):,}")
    print(f"  Val: {len(dataset['validation']):,}")
    
    # Setup model
    print("\n[2/3] Setting up model...")
    model, tokenizer = setup_model()
    
    # Train
    print("\n[3/3] Training...")
    stats = train(model, tokenizer, dataset)
    
    # Done
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"  Loss: {stats['train_loss']:.4f}")
    print(f"  Time: {stats['runtime_seconds']/60:.1f} min")
    print(f"  Model: {CHECKPOINT_DIR}/final")
    
    return stats

if __name__ == "__main__":
    run_finetuning()