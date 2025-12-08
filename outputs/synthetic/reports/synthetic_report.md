# Synthetic Data Generation Report

**Generated:** 2025-12-07 23:24:17

## Dataset Statistics

| Metric | Original | Synthetic |
|--------|----------|-----------|
| Samples | 52,527 | 142,639 |
| Avg Length | 11.64 | 14.75 |
| Min Length | 3 | 3 |
| Max Length | 44 | 49 |
| Unique Words | 50,846 | 60,734 |

## Augmentation Results

- **Augmentation Factor:** 2.72x
- **Avg Diversity Score:** 0.2832
- **Min Diversity Score:** 0.103
- **Max Diversity Score:** 0.8

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
