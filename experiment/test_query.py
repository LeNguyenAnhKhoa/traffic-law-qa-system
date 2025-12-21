"""
Test script to visualize RAG pipeline with a sample query.
This script demonstrates how documents are retrieved, reranked, and scored.
MODIFIED: Fetch top 50 hybrid -> Rerank top 50 -> Print all with both scores.
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv
import logging

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Load environment variables
root_env = Path(__file__).parent.parent / ".env"
load_dotenv(root_env)

# Initialize logger
logger = logging.getLogger(__name__)

from src.services.qdrant_service import qdrant_service
from src.services.reranker_service import reranker_service

# Output file for saving results
OUTPUT_FILE = Path(__file__).parent / "data" / "rag_test_output.txt"

def print_output(text=""):
    """Print to both console and file."""
    print(text)
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")


async def test_rag_pipeline(query: str):
    """
    Test the complete RAG pipeline with a given query.
    
    Args:
        query: The user's question about traffic law
    """
    print_output("=" * 80)
    print_output(f"TESTING RAG PIPELINE WITH QUERY: {query}")
    print_output("=" * 80)
    
    # Step 1: Hybrid Search
    # UPDATED: Changed limit to 50
    print_output("\n[STEP 1] Running Hybrid Search (Dense + Sparse vectors with RRF fusion)...")
    search_results = qdrant_service.hybrid_search(query, limit=50)
    print_output(f"✓ Found {len(search_results)} documents from hybrid search.")
    
    # Step 2: Reranking with LLM
    print_output("\n[STEP 2] Reranking with LLM...")
    
    # UPDATED: Rerank top 50 (keep all from hybrid search)
    # Now using the service directly to get reasoning
    reranked_docs, llm_reasoning = await reranker_service.rerank(
        query, 
        search_results, 
        top_k=50, 
        return_reasoning=True
    )
    
    print_output(f"✓ Reranking complete. Processing {len(reranked_docs)} documents...\n")
    
    # Sort by LLM Score (rerank_score) descending
    reranked_docs.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

    # Step 3: Display Results
    print_output("=" * 80)
    print_output("LLM REASONING")
    print_output("=" * 80)
    if llm_reasoning:
        print_output(f"{llm_reasoning}\n")
    else:
        print_output("(Reasoning not available)\n")
    
    print_output("=" * 80)
    print_output("FINAL TOP DOCUMENTS (Sorted by LLM Score)")
    print_output("Format: [Rank] | LLM Score (0-10) | Hybrid Score")
    print_output("=" * 80)
    
    if reranked_docs:
        seen_content = set() # To ensure uniqueness
        count = 0
        
        for doc in reranked_docs:
            payload = doc.get("payload", {})
            content = payload.get("content", "N/A")
            
            # Deduplication check based on content
            if content in seen_content:
                continue
            seen_content.add(content)
            
            count += 1
            llm_score = doc.get("rerank_score", 0)
            hybrid_score = doc.get("score", 0) # Qdrant score
            
            # Formatting scores
            bar_len = int(llm_score)
            visual_bar = '█' * bar_len + '░' * (10 - bar_len)
            
            print_output(f"\nRANK #{count}")
            print_output(f"Scores: LLM {llm_score:.2f}/10 {visual_bar} | Hybrid: {hybrid_score:.4f}")
            print_output("-" * 80)
            print_output(f"Title   : {payload.get('title', 'N/A')}")
            print_output(f"Article : {payload.get('article', 'N/A')}")
            print_output(f"Year    : {payload.get('year', 'N/A')}")
            print_output(f"Content : {content}")
            print_output("-" * 80)
            
            # Stop if we have printed 50 unique docs
            if count >= 50:
                break
                
        if count == 0:
             print_output("\n⚠ No unique documents found!")
    else:
        print_output("\n⚠ No documents found!")
    
    # Step 4: Summary
    print_output("\n" + "=" * 80)
    print_output("SUMMARY")
    print_output("=" * 80)
    print_output(f"Original hybrid search results: {len(search_results)}")
    print_output(f"Final unique documents printed: {len(reranked_docs)}")
    print_output("\n" + "=" * 80)
    
    return reranked_docs


# Sample queries for testing
SAMPLE_QUERIES = [
    "Lái xe vượt đèn đỏ phạt bao nhiêu tiền"
]


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test RAG pipeline with a query.")
    parser.add_argument("query", nargs="?", help="The query to test", default=None)
    args = parser.parse_args()

    # Clear previous output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("")
    
    # Determine query
    if args.query:
        query = args.query
    else:
        query = SAMPLE_QUERIES[0]
    
    print_output("\n")
    print_output("╔" + "=" * 78 + "╗")
    print_output("║" + " " * 20 + "TRAFFIC LAW Q&A SYSTEM - TEST SCRIPT" + " " * 23 + "║")
    print_output("║" + " " * 18 + "   Top 50 Retrieval & Rerank Analysis   " + " " * 18 + "║")
    print_output("╚" + "=" * 78 + "╝")
    
    await test_rag_pipeline(query)
    
    print_output(f"\n\n✅ Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        error_msg = f"\n❌ Error: {e}"
        print_output(error_msg)
        import traceback
        traceback.print_exc()
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            traceback.print_exc(file=f)