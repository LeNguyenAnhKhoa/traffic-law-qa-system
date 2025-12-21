"""
Test script to visualize RAG pipeline with a sample query.
This script demonstrates how documents are retrieved, reranked, and scored.
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load environment variables
root_env = Path(__file__).parent / ".env"
load_dotenv(root_env)

from src.services.qdrant_service import qdrant_service
from src.services.reranker_service import reranker_service

# Output file for saving results
OUTPUT_FILE = Path(__file__).parent / "rag_test_output.txt"

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
    print_output("\n[STEP 1] Running Hybrid Search (Dense + Sparse vectors with RRF fusion)...")
    print_output("-" * 80)
    
    search_results = qdrant_service.hybrid_search(query, limit=30)
    print_output(f"✓ Found {len(search_results)} documents from hybrid search (processing...)\n")
    
    # Step 2: Reranking with LLM
    print_output("\n" + "=" * 80)
    print_output("[STEP 2] Reranking with LLM (gpt-4.1-mini)...")
    print_output("-" * 80)
    
    reranked_docs = await reranker_service.rerank(query, search_results, top_k=7)
    
    print_output(f"✓ Reranking complete")
    print_output(f"✓ Selected top 7 documents with highest scores: {len(reranked_docs)} documents")
    print_output(f"✓ Verification: Exactly 7 documents (or all available if < 7)? {len(reranked_docs) <= 7}\n")
    
    # Step 3: Display Results
    print_output("=" * 80)
    print_output("TOP 7 RERANKED DOCUMENTS (highest scores, sorted by score)")
    print_output("=" * 80)
    
    if reranked_docs:
        for idx, doc in enumerate(reranked_docs, 1):
            payload = doc.get("payload", {})
            rerank_score = doc.get("rerank_score", 0)
            
            print_output(f"\n{idx}. {'█' * int(rerank_score)} {rerank_score:.1f}/10")
            print_output(f"   Title: {payload.get('title', 'N/A')}")
            print_output(f"   Article: {payload.get('article', 'N/A')}")
            print_output(f"   Content: {payload.get('content', 'N/A')}")
    else:
        print_output("\n⚠ No documents found!")
        print_output("  This should not happen since we get top 10 by default.")
    
    # Step 4: Summary Statistics
    print_output("\n" + "=" * 80)
    print_output("SUMMARY STATISTICS")
    print_output("=" * 80)
    print_output(f"Original hybrid search results: {len(search_results)}")
    print_output(f"After reranking (top 7 by score): {len(reranked_docs)}")
    
    # Verify filtering and limit
    print_output("\n[VERIFICATION]")
    if reranked_docs:
        scores = [doc.get("rerank_score", 0) for doc in reranked_docs]
        print_output(f"✓ Scores sorted in descending order? {all(scores[i] >= scores[i+1] for i in range(len(scores)-1))}")
        print_output(f"✓ Document count <= 7? {len(reranked_docs) <= 7}")
        print_output(f"Average rerank score: {sum(scores) / len(scores):.2f}")
        print_output(f"Max score: {max(scores):.2f}")
        print_output(f"Min score: {min(scores):.2f}")
    else:
        print_output("⚠ No documents found")
    
    print_output("\n" + "=" * 80)
    
    return reranked_docs


# Sample queries for testing
SAMPLE_QUERIES = [
    "Lái ô tô vượt đèn đỏ bị phạt bao nhiêu tiền và có bị trừ điểm bằng lái không?",
    "Chở người ngồi sau xe máy không đội mũ bảo hiểm phạt thế nào?",
    "Lái ô tô vượt đèn đỏ bị phạt bao nhiêu tiền và có bị trừ điểm bằng lái không?",
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
    print_output("║" + " " * 18 + "Visualizing the RAG pipeline with reranking" + " " * 17 + "║")
    print_output("╚" + "=" * 78 + "╝")
    
    await test_rag_pipeline(query)
    
    # Optional: test with other queries
    if not args.query:
        print_output("\n\n💡 Tip: To test with other queries, pass a query as an argument.")
        print_output("   Example: python test_query.py \"Your question here\"")
        print_output("💡 Tip: Available sample queries:")
        for i, q in enumerate(SAMPLE_QUERIES, 1):
            print_output(f"   {i}. {q}")
    
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
