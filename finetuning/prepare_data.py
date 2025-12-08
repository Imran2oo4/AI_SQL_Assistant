"""
Data Preparation for Fine-Tuning
Uses train.csv, validation.csv, test.csv correctly.
"""

import os
import pandas as pd
import json
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_DIR = "outputs/finetuning"
DATA_DIR = "data"

# Change this for testing vs full training
MAX_SAMPLES = 100  # Set to None for full data

def setup_directories():
    for d in [OUTPUT_DIR, f"{OUTPUT_DIR}/results", f"{OUTPUT_DIR}/logs"]:
        os.makedirs(d, exist_ok=True)

# =============================================================================
# PROMPT TEMPLATE
# =============================================================================

def format_for_training(question, sql):
    """Format single example for instruction fine-tuning."""
    text = f"""### Question:
{question}

### SQL:
{sql}"""
    return text

# =============================================================================
# DATA LOADING
# =============================================================================

def load_csv_file(filepath, max_samples=None):
    """Load a single CSV file."""
    if not os.path.exists(filepath):
        print(f"  File not found: {filepath}")
        return None
    
    df = pd.read_csv(filepath)
    
    if max_samples and len(df) > max_samples:
        df = df.sample(n=max_samples, random_state=42)
    
    return df

def format_dataframe(df, source_name):
    """Convert dataframe to training format."""
    formatted = []
    for _, row in df.iterrows():
        formatted.append({
            'text': format_for_training(row['question'], row['sql']),
            'question': str(row['question']),
            'sql': str(row['sql']),
            'source': source_name
        })
    return formatted

def save_jsonl(data, filepath):
    """Save data as JSONL file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item) + '\n')
    print(f"  Saved: {filepath}")

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def prepare_finetuning_data():
    """Prepare data for fine-tuning."""
    
    print("=" * 50)
    print("PREPARING FINE-TUNING DATA")
    print(f"Max samples per file: {MAX_SAMPLES if MAX_SAMPLES else 'ALL'}")
    print("=" * 50)
    
    setup_directories()
    
    # Load train data
    print("\n[1/5] Loading training data...")
    train_df = load_csv_file(f"{DATA_DIR}/train.csv", MAX_SAMPLES)
    print(f"  train.csv: {len(train_df):,} rows")
    
    # Load synthetic and combine with train
    # synthetic_df = load_csv_file(f"{DATA_DIR}/synthetic.csv", MAX_SAMPLES)
    # if synthetic_df is not None:
    #     print(f"  synthetic.csv: {len(synthetic_df):,} rows")
    #     train_df = pd.concat([train_df, synthetic_df], ignore_index=True)
    #     print(f"  Combined training: {len(train_df):,} rows")
    
    # Load validation data
    print("\n[2/5] Loading validation data...")
    val_df = load_csv_file(f"{DATA_DIR}/validation.csv", MAX_SAMPLES)
    print(f"  validation.csv: {len(val_df):,} rows")
    
    # Load test data
    print("\n[3/5] Loading test data...")
    test_df = load_csv_file(f"{DATA_DIR}/test.csv", MAX_SAMPLES)
    print(f"  test.csv: {len(test_df):,} rows")
    
    # Format data
    print("\n[4/5] Formatting data...")
    train_data = format_dataframe(train_df, 'train')
    val_data = format_dataframe(val_df, 'validation')
    test_data = format_dataframe(test_df, 'test')
    
    # Save files
    print("\n[5/5] Saving files...")
    save_jsonl(train_data, f"{OUTPUT_DIR}/train.jsonl")
    save_jsonl(val_data, f"{OUTPUT_DIR}/val.jsonl")
    save_jsonl(test_data, f"{OUTPUT_DIR}/test.jsonl")
    
    # Save stats
    stats = {
        'train_samples': len(train_data),
        'val_samples': len(val_data),
        'test_samples': len(test_data),
        'max_samples': MAX_SAMPLES,
        'created_at': datetime.now().isoformat()
    }
    
    with open(f"{OUTPUT_DIR}/data_stats.json", 'w') as f:
        json.dump(stats, f, indent=2)
    
    # Summary
    print("\n" + "=" * 50)
    print("COMPLETE")
    print("=" * 50)
    print(f"  Train: {len(train_data):,}")
    print(f"  Val:   {len(val_data):,}")
    print(f"  Test:  {len(test_data):,}")
    
    return stats

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    prepare_finetuning_data()