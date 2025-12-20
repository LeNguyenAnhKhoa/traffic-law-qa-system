# Law Crawler - Trích xuất dữ liệu Luật Giao thông

## Cài đặt

```bash
pip install pypdf pandas
```

## Sử dụng

### 1. Crawl dữ liệu từ PDF
```bash
python crawl_pdf.py
```

Script sẽ:
- Đọc tất cả file PDF trong thư mục `data/`
- Parse các điều luật, khoản và mức phạt
- Lưu kết quả vào `output/traffic_laws.json` và `output/traffic_laws.csv`

### 2. Xem thống kê
```bash
python view_stats.py
```

## Cấu trúc dữ liệu

### JSON
```json
{
  "year": "2019",
  "article": "5",
  "title": "Xử phạt người điều khiển xe...",
  "content": "Nội dung đầy đủ của điều luật",
  "clauses": [
    {
      "clause_number": "1",
      "content": "Nội dung khoản 1",
      "fine_info": {
        "has_fine": true,
        "fine_range": "200000 - 400000",
        "violations": ["Vi phạm 1", "Vi phạm 2"]
      }
    }
  ]
}
```

### CSV
Các cột: year, article, title, clause_number, content, has_fine, fine_amount, fine_range, violations

## Kết quả

- 214 điều luật từ 3 file PDF (2019, 2021, 2024)
- 1084 khoản luật
- 132 điều có quy định mức phạt
