"""
Synthetic Data Generation for SQL Learning Assistant

Covers:
1. Create synthetic datasets for training/testing
2. Implement data augmentation techniques  
3. Ensure diversity and quality of generated data
4. Address privacy and ethical considerations
"""

import pandas as pd
import random
import re
import hashlib
import json
from collections import Counter
from datetime import datetime
import matplotlib.pyplot as plt
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from synthetic.synonyms import SYNONYMS, get_synonym, has_synonym

# =============================================================================
# OUTPUT DIRECTORIES
# =============================================================================

OUTPUT_DIR = "outputs/synthetic"
VIZ_DIR = f"{OUTPUT_DIR}/visualizations"
REPORT_DIR = f"{OUTPUT_DIR}/reports"
STATS_DIR = f"{OUTPUT_DIR}/stats"

def setup_directories():
    """Create output directories."""
    for d in [OUTPUT_DIR, VIZ_DIR, REPORT_DIR, STATS_DIR]:
        os.makedirs(d, exist_ok=True)

# =============================================================================
# SENTENCE VARIATIONS
# =============================================================================

PREFIXES = ["", "Can you ", "Please ", "I want to ", "I need to ", 
            "Could you ", "Help me ", "Show me how to "]

SUFFIXES = ["", "?", " please", " for me", " please?"]

# =============================================================================
# AUGMENTATION TECHNIQUES
# =============================================================================

def replace_synonyms(text, prob=0.4):
    """Technique 1: Replace words with synonyms."""
    words = text.split()
    result = []
    for word in words:
        clean = re.sub(r'[^\w]', '', word).lower()
        if has_synonym(clean) and random.random() < prob:
            syn = get_synonym(clean)
            result.append(syn if word[-1] not in '.,?!' else syn + word[-1])
        else:
            result.append(word)
    return ' '.join(result)

def random_insertion(text, prob=0.15):
    """Technique 2: Insert contextual words."""
    inserts = ["also", "specifically", "exactly", "just", "only"]
    words = text.split()
    if len(words) > 3 and random.random() < prob:
        pos = random.randint(1, len(words) - 1)
        words.insert(pos, random.choice(inserts))
    return ' '.join(words)

def random_swap(text, prob=0.1):
    """Technique 3: Swap adjacent words."""
    words = text.split()
    if len(words) > 4 and random.random() < prob:
        pos = random.randint(1, len(words) - 3)
        words[pos], words[pos + 1] = words[pos + 1], words[pos]
    return ' '.join(words)

def structure_variation(text):
    """Technique 4: Add prefixes and suffixes."""
    prefix = random.choice(PREFIXES)
    suffix = random.choice(SUFFIXES)
    if prefix:
        text = text[0].lower() + text[1:] if text else text
    result = prefix + text + suffix
    return result[0].upper() + result[1:] if result else result

def case_variation(text):
    """Technique 5: Vary capitalization."""
    r = random.random()
    if r < 0.6:
        return text[0].upper() + text[1:].lower() if text else text
    elif r < 0.85:
        return text.lower()
    return text

def generate_variation(question):
    """Apply all augmentation techniques."""
    variation = question
    variation = replace_synonyms(variation)
    variation = random_insertion(variation)
    variation = random_swap(variation)
    variation = structure_variation(variation)
    variation = case_variation(variation)
    return variation

# =============================================================================
# QUALITY AND DIVERSITY
# =============================================================================

def diversity_score(original, variation):
    """Calculate diversity between original and variation."""
    orig_words = set(original.lower().split())
    var_words = set(variation.lower().split())
    if not orig_words or not var_words:
        return 0
    intersection = orig_words & var_words
    union = orig_words | var_words
    return 1 - (len(intersection) / len(union))

def quality_check(question, sql):
    """Check if generated data passes quality standards."""
    if not question or len(question.strip()) < 10:
        return False
    if not sql or len(sql.strip()) < 5:
        return False
    if not re.search(r'[a-zA-Z]', question):
        return False
    if len(question) > 500:
        return False
    return True

def remove_duplicates(data):
    """Remove duplicate entries."""
    seen = set()
    unique = []
    for item in data:
        normalized = re.sub(r'[^\w\s]', '', item['question'].lower())
        normalized = ' '.join(normalized.split())
        h = hashlib.md5(normalized.encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(item)
    return unique

# =============================================================================
# PRIVACY (ETHICAL CONSIDERATIONS)
# =============================================================================

def anonymize(text):
    """Remove sensitive information."""
    text = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', '[EMAIL]', text)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    return text

# =============================================================================
# STATISTICS
# =============================================================================

def calculate_stats(original_df, synthetic_df):
    """Calculate dataset statistics."""
    def get_stats(df, name):
        questions = df['question'].tolist()
        lengths = [len(q.split()) for q in questions]
        return {
            'name': name,
            'samples': len(df),
            'avg_length': round(sum(lengths) / len(lengths), 2),
            'min_length': min(lengths),
            'max_length': max(lengths),
            'unique_words': len(set(' '.join(questions).lower().split()))
        }
    
    orig_stats = get_stats(original_df, 'Original')
    synth_stats = get_stats(synthetic_df, 'Synthetic')
    
    diversity_scores = synthetic_df['diversity_score'].tolist()
    diversity_stats = {
        'avg': round(sum(diversity_scores) / len(diversity_scores), 4),
        'min': round(min(diversity_scores), 4),
        'max': round(max(diversity_scores), 4)
    }
    
    return {
        'original': orig_stats,
        'synthetic': synth_stats,
        'diversity': diversity_stats,
        'augmentation_factor': round(len(synthetic_df) / len(original_df), 2)
    }

# =============================================================================
# VISUALIZATIONS
# =============================================================================

def create_visualizations(original_df, synthetic_df):
    """Create and save visualizations."""
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # 1. Dataset Size Comparison
    fig, ax = plt.subplots(figsize=(8, 5))
    sizes = [len(original_df), len(synthetic_df)]
    bars = ax.bar(['Original', 'Synthetic'], sizes, color=['#3498db', '#2ecc71'])
    for bar, size in zip(bars, sizes):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20,
                f'{size:,}', ha='center', fontweight='bold')
    ax.set_ylabel('Samples')
    ax.set_title('Dataset Size Comparison')
    plt.savefig(f'{VIZ_DIR}/01_size_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 2. Question Length Distribution
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    orig_len = [len(q.split()) for q in original_df['question']]
    synth_len = [len(q.split()) for q in synthetic_df['question']]
    
    axes[0].hist(orig_len, bins=25, color='#3498db', alpha=0.7)
    axes[0].set_title('Original - Question Length')
    axes[0].set_xlabel('Words')
    
    axes[1].hist(synth_len, bins=25, color='#2ecc71', alpha=0.7)
    axes[1].set_title('Synthetic - Question Length')
    axes[1].set_xlabel('Words')
    
    plt.tight_layout()
    plt.savefig(f'{VIZ_DIR}/02_length_distribution.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    # 3. Diversity Score Distribution
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(synthetic_df['diversity_score'], bins=20, color='#9b59b6', alpha=0.7)
    ax.axvline(synthetic_df['diversity_score'].mean(), color='red', linestyle='--',
               label=f"Mean: {synthetic_df['diversity_score'].mean():.3f}")
    ax.set_xlabel('Diversity Score')
    ax.set_ylabel('Frequency')
    ax.set_title('Diversity Score Distribution')
    ax.legend()
    plt.savefig(f'{VIZ_DIR}/03_diversity_distribution.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  Visualizations saved to {VIZ_DIR}/")

# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(stats):
    """Generate markdown report."""
    report = f"""# Synthetic Data Generation Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Dataset Statistics

| Metric | Original | Synthetic |
|--------|----------|-----------|
| Samples | {stats['original']['samples']:,} | {stats['synthetic']['samples']:,} |
| Avg Length | {stats['original']['avg_length']} | {stats['synthetic']['avg_length']} |
| Min Length | {stats['original']['min_length']} | {stats['synthetic']['min_length']} |
| Max Length | {stats['original']['max_length']} | {stats['synthetic']['max_length']} |
| Unique Words | {stats['original']['unique_words']:,} | {stats['synthetic']['unique_words']:,} |

## Augmentation Results

- **Augmentation Factor:** {stats['augmentation_factor']}x
- **Avg Diversity Score:** {stats['diversity']['avg']}
- **Min Diversity Score:** {stats['diversity']['min']}
- **Max Diversity Score:** {stats['diversity']['max']}

## Techniques Used

1. Synonym Replacement (40% probability)
2. Random Insertion (15% probability)
3. Random Swap (10% probability)
4. Structure Variation (prefix/suffix)
5. Case Variation

## Quality Controls

- Minimum question length: 10 characters
- Maximum question length: 500 characters
- Minimum diversity score: 0.1
- Duplicate removal via MD5 hashing

## Privacy Measures

- Email anonymization
- Phone number anonymization
- SSN anonymization

## Visualizations

- `01_size_comparison.png` - Dataset size comparison
- `02_length_distribution.png` - Question length distribution
- `03_diversity_distribution.png` - Diversity score distribution
"""
    
    with open(f'{REPORT_DIR}/synthetic_report.md', 'w') as f:
        f.write(report)
    print(f"  Report saved to {REPORT_DIR}/synthetic_report.md")

# =============================================================================
# MAIN PIPELINE
# =============================================================================

def generate_synthetic_data(input_csv, output_csv, sample_size=500, variations=3, min_diversity=0.1):
    """Main synthetic data generation pipeline."""
    
    print("=" * 50)
    print("SYNTHETIC DATA GENERATION")
    print("=" * 50)
    
    # Setup
    setup_directories()
    
    # Load data
    print(f"\n[1/6] Loading {input_csv}...")
    df = pd.read_csv(input_csv)
    sample_df = df.sample(n=min(sample_size, len(df)), random_state=42)
    print(f"  Sampled {len(sample_df)} rows")
    
    # Generate variations
    print(f"\n[2/6] Generating variations...")
    synthetic_data = []
    skipped = 0
    
    for _, row in sample_df.iterrows():
        question = anonymize(str(row['question']))
        sql = anonymize(str(row['sql']))
        
        for _ in range(variations):
            variation = generate_variation(question)
            div_score = diversity_score(question, variation)
            
            if div_score < min_diversity or not quality_check(variation, sql):
                skipped += 1
                continue
            
            synthetic_data.append({
                'question': variation,
                'sql': sql,
                'original_question': question,
                'diversity_score': round(div_score, 3),
                'is_synthetic': True
            })
    
    print(f"  Generated: {len(synthetic_data)}, Skipped: {skipped}")
    
    # Remove duplicates
    print(f"\n[3/6] Removing duplicates...")
    before = len(synthetic_data)
    synthetic_data = remove_duplicates(synthetic_data)
    print(f"  Removed {before - len(synthetic_data)} duplicates")
    
    # Save data
    print(f"\n[4/6] Saving data...")
    synthetic_df = pd.DataFrame(synthetic_data)
    synthetic_df.to_csv(output_csv, index=False)
    print(f"  Saved to {output_csv}")
    
    # Calculate stats
    print(f"\n[5/6] Calculating statistics...")
    stats = calculate_stats(sample_df, synthetic_df)
    
    # Save stats as JSON
    with open(f'{STATS_DIR}/statistics.json', 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"  Stats saved to {STATS_DIR}/statistics.json")
    
    # Generate visualizations and report
    print(f"\n[6/6] Creating outputs...")
    create_visualizations(sample_df, synthetic_df)
    generate_report(stats)
    
    # Summary
    print("\n" + "=" * 50)
    print("COMPLETE")
    print("=" * 50)
    print(f"  Original: {stats['original']['samples']:,} samples")
    print(f"  Synthetic: {stats['synthetic']['samples']:,} samples")
    print(f"  Augmentation: {stats['augmentation_factor']}x")
    print(f"  Avg Diversity: {stats['diversity']['avg']}")
    
    return synthetic_df

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    generate_synthetic_data(
        input_csv="data/train.csv",
        output_csv="data/synthetic.csv",
        sample_size=52527,
        variations=3,
        min_diversity=0.1
    )