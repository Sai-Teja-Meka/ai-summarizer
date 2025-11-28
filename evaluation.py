"""
Evaluation Module
Measures summarization quality using ROUGE metrics and other criteria
"""

from rouge_score import rouge_scorer
import streamlit as st
from typing import Dict
import csv
from datetime import datetime


# Simple ROUGE scorer
scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)


def calculate_rouge_scores(reference: str, candidate: str) -> Dict:
    """
    Calculate ROUGE scores between reference and candidate text
    
    ROUGE Explanation:
    - ROUGE-1: Measures single-word overlap (unigrams)
    - ROUGE-2: Measures two-word phrase overlap (bigrams)
    - ROUGE-L: Measures longest common sequence (captures sequence order)
    
    Higher scores = better quality (0-1 scale, where 1.0 = perfect match)
    
    Args:
        reference: Ground truth / reference summary
        candidate: Generated summary to evaluate
    
    Returns:
        Dict with ROUGE-1, ROUGE-2, ROUGE-L F1 scores
    """
    
    try:
        scores = scorer.score(reference, candidate)
        
        return {
            "rouge1": round(scores['rouge1'].fmeasure, 3),
            "rouge2": round(scores['rouge2'].fmeasure, 3),
            "rougeL": round(scores['rougeL'].fmeasure, 3),
            "average": round((scores['rouge1'].fmeasure + scores['rouge2'].fmeasure + scores['rougeL'].fmeasure) / 3, 3)
        }
    except Exception as e:
        st.error(f"Error calculating ROUGE: {str(e)}")
        return {
            "rouge1": None,
            "rouge2": None,
            "rougeL": None,
            "average": None
        }


def calculate_basic_metrics(reference: str, candidate: str) -> Dict:
    """
    Calculate basic quality metrics
    
    Args:
        reference: Reference/ideal summary
        candidate: Generated summary
    
    Returns:
        Dict with basic metrics
    """
    
    # Length metrics
    ref_length = len(reference)
    cand_length = len(candidate)
    compression_ratio = round((cand_length / ref_length * 100), 2) if ref_length > 0 else 0
    
    # Similarity metrics (simple word overlap)
    ref_words = set(reference.lower().split())
    cand_words = set(candidate.lower().split())
    
    if len(ref_words) == 0:
        word_overlap = 0
    else:
        word_overlap = round((len(ref_words & cand_words) / len(ref_words) * 100), 2)
    
    return {
        "reference_length": ref_length,
        "candidate_length": cand_length,
        "compression_ratio": compression_ratio,
        "word_overlap_percentage": word_overlap
    }


def calculate_readability_score(text: str) -> Dict:
    """
    Estimate readability using simple metrics
    
    Returns:
        Dict with readability metrics
    """
    
    words = text.split()
    sentences = text.split('.')
    
    avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
    avg_sentence_length = len(words) / len(sentences) if sentences else 0
    
    # Simple scoring: lower is better (shorter words/sentences = easier to read)
    readability_score = min(100, round((5 - avg_word_length + 10 - avg_sentence_length) * 5, 0))
    readability_score = max(20, readability_score)  # Keep between 20-100
    
    return {
        "avg_word_length": round(avg_word_length, 2),
        "avg_sentence_length": round(avg_sentence_length, 2),
        "readability_score": int(readability_score)  # Higher = more readable
    }


def log_prompt_evaluation(
    prompt_version: str,
    input_text: str,
    generated_summary: str,
    reference_summary: str,
    rouge_scores: Dict,
    basic_metrics: Dict,
    readability: Dict,
    processing_time: float
):
    """
    Log prompt evaluation results to CSV for tracking
    
    FIXED: Handle None values in ROUGE scores properly
    """
    
    eval_file = "prompt_evaluations.csv"
    
    # Create file with headers if doesn't exist
    import os
    if not os.path.exists(eval_file):
        with open(eval_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "prompt_version",
                "input_length",
                "rouge1_score",
                "rouge2_score",
                "rougeL_score",
                "average_rouge",
                "word_overlap_pct",
                "compression_ratio",
                "readability_score",
                "processing_time"
            ])
    
    # FIXED: Convert None to 0.0 for CSV storage (so we don't get empty strings)
    rouge1 = rouge_scores["rouge1"] if rouge_scores["rouge1"] is not None else 0.0
    rouge2 = rouge_scores["rouge2"] if rouge_scores["rouge2"] is not None else 0.0
    rougeL = rouge_scores["rougeL"] if rouge_scores["rougeL"] is not None else 0.0
    avg_rouge = rouge_scores["average"] if rouge_scores["average"] is not None else 0.0
    
    # Append evaluation
    with open(eval_file, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            prompt_version,
            len(input_text),
            rouge1,
            rouge2,
            rougeL,
            avg_rouge,
            basic_metrics["word_overlap_percentage"],
            basic_metrics["compression_ratio"],
            readability["readability_score"],
            round(processing_time, 2)
        ])


def get_evaluation_summary():
    """
    Read evaluation CSV and return summary by prompt version
    FIXED: Handle 0.0 values (which represent "no reference provided" runs)
    """
    
    import os
    import csv
    
    eval_file = "prompt_evaluations.csv"
    
    if not os.path.exists(eval_file):
        return None
    
    try:
        with open(eval_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            return None
        
        # Group by prompt version
        version_stats = {}
        
        for row in rows:
            version = row["prompt_version"]
            
            if version not in version_stats:
                version_stats[version] = {
                    "count": 0,
                    "avg_rouge1": 0,
                    "avg_rouge2": 0,
                    "avg_rougeL": 0,
                    "avg_readability": 0,
                    "total_time": 0
                }
            
            version_stats[version]["count"] += 1
            
            # FIXED: Safely parse ROUGE scores (handle strings with 0.0)
            try:
                r1 = float(row["rouge1_score"])
            except (ValueError, TypeError):
                r1 = 0.0
            
            try:
                r2 = float(row["rouge2_score"])
            except (ValueError, TypeError):
                r2 = 0.0
            
            try:
                rL = float(row["rougeL_score"])
            except (ValueError, TypeError):
                rL = 0.0
            
            try:
                readability = float(row["readability_score"])
            except (ValueError, TypeError):
                readability = 0.0
            
            try:
                proc_time = float(row["processing_time"])
            except (ValueError, TypeError):
                proc_time = 0.0
            
            version_stats[version]["avg_rouge1"] += r1
            version_stats[version]["avg_rouge2"] += r2
            version_stats[version]["avg_rougeL"] += rL
            version_stats[version]["avg_readability"] += readability
            version_stats[version]["total_time"] += proc_time
        
        # Calculate averages
        for version in version_stats:
            count = version_stats[version]["count"]
            version_stats[version]["avg_rouge1"] = round(version_stats[version]["avg_rouge1"] / count, 3)
            version_stats[version]["avg_rouge2"] = round(version_stats[version]["avg_rouge2"] / count, 3)
            version_stats[version]["avg_rougeL"] = round(version_stats[version]["avg_rougeL"] / count, 3)
            version_stats[version]["avg_readability"] = round(version_stats[version]["avg_readability"] / count, 1)
            version_stats[version]["avg_time"] = round(version_stats[version]["total_time"] / count, 2)
        
        return {
            "version_stats": version_stats,
            "rows": rows,
            "total_evaluations": len(rows)
        }
    
    except Exception as e:
        st.error(f"Error reading evaluations: {str(e)}")
        return None
