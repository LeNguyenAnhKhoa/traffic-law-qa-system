import json

# Đọc file JSON
with open('./data/traffic_laws.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Tính độ dài content và lưu thông tin chi tiết
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

# Thống kê
print("=" * 60)
print("THỐNG KÊ ĐỘ DÀI CONTENT (không tính content trong clauses)")
print("=" * 60)
print(f"Tổng số articles: {len(content_lengths)}")
print(f"Độ dài content tối đa: {max_length:,} ký tự")
print(f"Độ dài content trung bình: {sum(content_lengths)/len(content_lengths):,.2f} ký tự")
print(f"Độ dài content nhỏ nhất: {min(content_lengths):,} ký tự")
print()

# Thông tin article có content dài nhất
if max_content_item:
    print("Article có content dài nhất:")
    print(f"  - Năm: {max_content_item['year']}")
    print(f"  - Điều: {max_content_item['article']}")
    print(f"  - Tiêu đề: {max_content_item['title']}")
    print(f"  - Độ dài: {max_content_item['length']:,} ký tự")
print()

# Phân bố độ dài
print("Phân bố độ dài content:")
ranges = [
    (0, 500, "0-500 ký tự"),
    (500, 1000, "500-1,000 ký tự"),
    (1000, 2000, "1,000-2,000 ký tự"),
    (2000, 5000, "2,000-5,000 ký tự"),
    (5000, 10000, "5,000-10,000 ký tự"),
    (10000, float('inf'), ">10,000 ký tự")
]

for min_len, max_len, label in ranges:
    count = sum(1 for l in content_lengths if min_len <= l < max_len)
    if count > 0:
        percentage = (count / len(content_lengths)) * 100
        print(f"  {label}: {count} articles ({percentage:.1f}%)")

print()
print("=" * 60)
print("GỢI Ý CHIẾN LƯỢC CHUNKING & EMBEDDING")
print("=" * 60)

# Ước tính tokens (tiếng Việt thường ~1.5-2 chars/token với nhiều tokenizer)
max_tokens_estimate = max_length / 1.5

print(f"Ước tính tokens tối đa: ~{max_tokens_estimate:,.0f} tokens")
print()

if max_length <= 1000:
    print("✓ Embedding trực tiếp toàn bộ content (không cần chunk)")
    print("  Model gợi ý: text-embedding-ada-002 (8191 tokens)")
elif max_length <= 5000:
    print("⚠ Nên xem xét chunking cho content dài")
    print("  Chiến lược:")
    print("  - Chunk theo clauses (đã có sẵn trong data)")
    print("  - Hoặc chunk theo paragraph/sentence với overlap")
    print("  - Chunk size: 500-1000 tokens, overlap: 100-200 tokens")
else:
    print("⚠ Bắt buộc phải chunking")
    print("  Chiến lược:")
    print("  - Ưu tiên chunk theo clauses (semantic chunking)")
    print("  - Nếu clause quá dài, chunk thêm theo paragraph")
    print("  - Chunk size: 500-800 tokens, overlap: 100-150 tokens")
    print("  - Metadata: lưu article, year, clause_number để truy vết")

print("=" * 60)