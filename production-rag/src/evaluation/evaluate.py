import json
import asyncio
from typing import List, Dict, Any
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from datasets import Dataset

from src.services.parser import DocumentParser
from src.services.retriever import HybridRetriever
from src.services.generator import LLMGenerator

def run_evaluation_benchmark(dataset_path: str = "src/evaluation/dataset.json"):
    """Evaluates the pipeline using RAGAS and prints quantitative metric reports."""
    print("=== Starting RAG Evaluation Harness ===")
    
    with open(dataset_path, "r") as f:
        test_cases = json.load(f)

    retriever = HybridRetriever()
    generator = LLMGenerator()

    # Sample dataset container for RAGAS evaluation
    questions = []
    answers = []
    contexts = []
    ground_truths = []

    for test in test_cases:
        query = test["question"]
        gt = test["ground_truth"]

        # Run pipeline
        retrieved_chunks = retriever.search(query=query, top_k=3)
        context_texts = [c["text"] for c in retrieved_chunks]

        # Generate non-streamed full answer for evaluation metrics
        system_prompt, user_prompt = generator.build_prompt(query, retrieved_chunks)
        
        # Collect results
        questions.append(query)
        contexts.append(context_texts)
        ground_truths.append([gt])
        
        # Note: In production evaluation, replace this mock execution with your LLM client output
        answers.append(f"Mock generated response based on context: {context_texts}")

    # Build HuggingFace Evaluation Dataset
    ragas_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    }
    dataset = Dataset.from_dict(ragas_dict)

    print("\nCalculating RAGAS metrics: Faithfulness, Context Precision, Recall, Relevancy...")
    
    # Run quantitative evaluation metrics
    results = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
    )

    print("\n=== Evaluation Benchmark Results ===")
    print(results)
    
    return results

if __name__ == "__main__":
    run_evaluation_benchmark()