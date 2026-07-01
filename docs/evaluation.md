# Evaluation Methodology

This document outlines the rigorous testing and evaluation framework used to ensure high-fidelity responses and mitigate hallucination in the Kannada RAG Agent.

## Evaluation Framework

The project utilizes **RAGAS (Retrieval Augmented Generation Assessment)** as the primary evaluation framework. RAGAS provides a set of reference-free metrics that compute scores based on the relationships between the User Query, the Retrieved Context, and the Generated Answer.

## Core Metrics

We evaluate on four primary axes:

1. **Faithfulness**: Measures if the generated answer is entirely grounded in the retrieved context. (Prevents LLM hallucination).
2. **Answer Relevancy**: Measures if the generated answer directly addresses the user's query. (Prevents evasive or tangential responses).
3. **Context Precision**: Measures whether the most relevant chunks of text are ranked at the very top of the retrieved context. (Evaluates the Cross-Encoder).
4. **Context Recall**: Measures whether the retrieved context contains all the necessary information to answer the question. (Evaluates Hybrid Search / BM25 / Dense Retrieval).

## Datasets

The evaluation suite uses a custom "Golden Dataset" (`data/eval_dataset.json` - internal only) comprising 50 highly complex, multi-hop queries derived from the novel.

**Query Types in Dataset:**
- **Exact Fact Retrieval**: "What color was the car on page 100?"
- **Thematic/Abstract**: "Explain the internal conflict of the protagonist in chapter 3."
- **Multi-hop**: "Who did Kaveramma meet before speaking to Himavant?"
- **Sparsity testing**: Queries containing rare Kannada colloquialisms.

## Validation Suite

The validation scripts are located in `scripts/eval/`.

- `eval_ragas.py`: Runs the full RAGAS suite against the golden dataset and outputs `eval_results.json`.
- `eval_hybrid.py`: Tests the precision of the BM25 vs Dense retrieval components in isolation.
- `eval_reranking.py`: Tests the MRR (Mean Reciprocal Rank) improvements gained by the CrossEncoder.

### Running Evaluations Locally

```bash
# Ensure dev dependencies are installed
pip install -r scripts/eval/requirements_eval.txt

# Run the core RAGAS evaluation
python scripts/eval/eval_ragas.py
```
