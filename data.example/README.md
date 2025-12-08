# Data Directory

This folder contains the dataset files used for training, validation, and testing the SQL Learning Assistant.

## Dataset Source

**WikiSQL** - A large crowd-sourced dataset for developing natural language interfaces for relational databases.

- **Kaggle:** https://www.kaggle.com/datasets/shahrukhkhan/wikisql/data
- **GitHub:** https://github.com/salesforce/WikiSQL

## Files

| File | Description |
|------|-------------|
| `train.csv` | Training dataset |
| `validation.csv` | Validation dataset |
| `test.csv` | Test dataset |
| `synthetic.csv` | Augmented dataset (generated) |

## Download Instructions

1. Download the dataset from Kaggle: https://www.kaggle.com/datasets/shahrukhkhan/wikisql/data
2. Extract the CSV files into this `data/` folder
3. Run the synthetic data generation script if needed: `python synthetic/generate_data.py`

## Citation

If you use WikiSQL, please cite the following work:
```
Victor Zhong, Caiming Xiong, and Richard Socher. 2017. 
Seq2SQL: Generating Structured Queries from Natural Language using Reinforcement Learning.
```
```bibtex
@article{zhongSeq2SQL2017,
  author = {Victor Zhong and Caiming Xiong and Richard Socher},
  title = {Seq2SQL: Generating Structured Queries from Natural Language using Reinforcement Learning},
  journal = {CoRR},
  volume = {abs/1709.00103},
  year = {2017}
}
```

## License

**BSD 3-Clause License**

Copyright (c) 2017, Salesforce Research. All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

- Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
- Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.