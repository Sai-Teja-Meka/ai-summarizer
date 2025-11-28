"""
Metrics Tracking Module
Logs and analyzes summarization performance
"""

import csv
import os
from datetime import datetime
import json
import streamlit as st


def get_metrics_file():
    """Get or create the metrics CSV file"""
    metrics_file = "summaries_metrics.csv"
    
    # Create file with headers if it doesn't exist
    if not os.path.exists(metrics_file):
        with open(metrics_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "input_length",
                "summary_length",
                "compression_ratio",
                "summary_tone",
                "summary_length_setting",
                "input_source",
                "file_type",
                "api_cost_estimate",
                "processing_time_seconds"
            ])
    
    return metrics_file


def log_summary(
    input_length: int,
    summary_length: int,
    compression_ratio: float,  # NEW: Accept compression_ratio as parameter
    tone: str,
    length_setting: str,
    input_source: str = "text",
    file_type: str = None,
    processing_time: float = 0.0
):
    """
    Log a summary to the metrics file
    
    Args:
        input_length: Characters in original text
        summary_length: Characters in summary
        compression_ratio: Pre-calculated compression ratio (now accepts it)
        tone: Selected tone (Neutral, Academic, Casual)
        length_setting: Selected length (Short, Medium, Long)
        input_source: "text" (pasted) or "file" (uploaded)
        file_type: File extension if uploaded
        processing_time: How long API call took
    """
    
    metrics_file = get_metrics_file()
    
    # Estimate API cost
    input_tokens = input_length / 4
    output_tokens = summary_length / 4
    api_cost = round((input_tokens * 0.0005 + output_tokens * 0.0015) / 1000, 4)
    
    # Write to CSV
    with open(metrics_file, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            input_length,
            summary_length,
            compression_ratio,  # Use passed value
            tone,
            length_setting,
            input_source,
            file_type or "N/A",
            api_cost,
            round(processing_time, 2)
        ])


def get_metrics_summary():
    """
    Read metrics file and return summary statistics
    Returns dict with aggregated stats
    """
    
    metrics_file = get_metrics_file()
    
    if not os.path.exists(metrics_file):
        return None
    
    try:
        with open(metrics_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            return None
        
        # Calculate statistics
        total_summaries = len(rows)
        total_input = sum(int(row["input_length"]) for row in rows)
        total_output = sum(int(row["summary_length"]) for row in rows)
        
        # Fixed: Handle empty compression_ratio gracefully
        compression_ratios = []
        for row in rows:
            try:
                cr = float(row["compression_ratio"])
                compression_ratios.append(cr)
            except (ValueError, TypeError):
                # If empty or invalid, skip it
                pass
        
        avg_compression = sum(compression_ratios) / len(compression_ratios) if compression_ratios else 0
        total_cost = sum(float(row["api_cost_estimate"]) for row in rows)
        
        # Fixed: Handle empty processing_time
        processing_times = []
        for row in rows:
            try:
                pt = float(row["processing_time_seconds"])
                processing_times.append(pt)
            except (ValueError, TypeError):
                pass
        
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Count by input source
        text_count = sum(1 for row in rows if row["input_source"] == "text")
        file_count = sum(1 for row in rows if row["input_source"] == "file")
        
        # Count by tone
        tone_counts = {}
        for row in rows:
            tone = row["summary_tone"]
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
        
        # Count by length setting
        length_counts = {}
        for row in rows:
            length = row["summary_length_setting"]
            length_counts[length] = length_counts.get(length, 0) + 1
        
        return {
            "total_summaries": total_summaries,
            "total_input_chars": total_input,
            "total_output_chars": total_output,
            "avg_compression_ratio": round(avg_compression, 2),
            "total_cost_usd": round(total_cost, 4),
            "avg_processing_time": round(avg_processing_time, 2),
            "text_uploads": text_count,
            "file_uploads": file_count,
            "tone_distribution": tone_counts,
            "length_distribution": length_counts,
            "rows": rows
        }
    
    except Exception as e:
        st.error(f"Error reading metrics: {str(e)}")
        return None


def get_recent_summaries(limit: int = 10):
    """Get the N most recent summaries"""
    metrics = get_metrics_summary()
    if metrics:
        return metrics["rows"][-limit:]
    return []
