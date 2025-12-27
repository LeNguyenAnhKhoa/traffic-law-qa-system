import json

# Read JSON file
with open('./data/traffic_laws.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Calculate content length and store details
content_lengths = []
max_length = 0
max_content_item = None

for item in data:
    if 'content' in item and item['content']:
        content = item['content']
        length = len(content)
        content_lengths.append(length)
        
        if length > max_length:
            max_length = length
            max_content_item = {
                'year': item.get('year'),
                'article': item.get('article'),
                'title': item.get('title'),
                'length': length
            }

# Statistics
print("=" * 60)
print("CONTENT LENGTH STATISTICS (excluding content in clauses)")
print("=" * 60)
print(f"Total articles: {len(content_lengths)}")
print(f"Max content length: {max_length:,} characters")
print(f"Average content length: {sum(content_lengths)/len(content_lengths):,.2f} characters")
print(f"Min content length: {min(content_lengths):,} characters")
print()

# Article with longest content
if max_content_item:
    print("Article with longest content:")
    print(f"  - Year: {max_content_item['year']}")
    print(f"  - Article: {max_content_item['article']}")
    print(f"  - Title: {max_content_item['title']}")
    print(f"  - Length: {max_content_item['length']:,} characters")
print()

# Length distribution
print("Content length distribution:")
ranges = [
    (0, 500, "0-500 chars"),
    (500, 1000, "500-1,000 chars"),
    (1000, 2000, "1,000-2,000 chars"),
    (2000, 5000, "2,000-5,000 chars"),
    (5000, 10000, "5,000-10,000 chars"),
    (10000, float('inf'), ">10,000 chars")
]

for min_len, max_len, label in ranges:
    count = sum(1 for l in content_lengths if min_len <= l < max_len)
    if count > 0:
        percentage = (count / len(content_lengths)) * 100
        print(f"  {label}: {count} articles ({percentage:.1f}%)")

print()
print("=" * 60)
print("CHUNKING & EMBEDDING STRATEGY SUGGESTIONS")
print("=" * 60)

# Estimate tokens (Vietnamese usually ~1.5-2 chars/token with most tokenizers)
max_tokens_estimate = max_length / 1.5

print(f"Estimated max tokens: ~{max_tokens_estimate:,.0f} tokens")
print()

if max_length <= 1000:
    print("✓ Direct embedding of full content (no chunking needed)")
    print("  Suggested model: text-embedding-ada-002 (8191 tokens)")
elif max_length <= 5000:
    print("⚠ Consider chunking for long content")
    print("  Strategy:")
    print("  - Chunk by clauses (already available in data)")
    print("  - Or chunk by paragraph/sentence with overlap")
    print("  - Chunk size: 500-1000 tokens, overlap: 100-200 tokens")
else:
    print("⚠ Chunking is required")
    print("  Strategy:")
    print("  - Prefer chunking by clauses (semantic chunking)")
    print("  - If clause is too long, chunk further by paragraph")
    print("  - Chunk size: 500-800 tokens, overlap: 100-150 tokens")
    print("  - Metadata: save article, year, clause_number for traceability")

print("=" * 60)