import os
import json
import csv
import re
from pypdf import PdfReader
from pathlib import Path


def extract_text_from_pdf(pdf_path):
    """Trích xuất text từ file PDF"""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def parse_traffic_law(text, year):
    """Parse nội dung luật giao thông thành các điều khoản có cấu trúc"""
    articles = []
    
    # Pattern để tìm các điều luật: "Điều X." hoặc "Điều X:"
    article_pattern = r'Điều\s+(\d+[a-z]?)[\.:]'
    
    # Tách text thành các điều
    matches = list(re.finditer(article_pattern, text, re.IGNORECASE))
    
    for i, match in enumerate(matches):
        article_num = match.group(1)
        start_pos = match.start()
        
        # Lấy nội dung từ điều này đến điều tiếp theo (hoặc cuối văn bản)
        if i < len(matches) - 1:
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(text)
        
        content = text[start_pos:end_pos].strip()
        
        # Parse các khoản trong điều
        clauses = parse_clauses(content)
        
        # Tìm tiêu đề của điều (nếu có)
        title_match = re.search(r'Điều\s+\d+[a-z]?[\.:](.+?)(?:\n|Khoản|\d\.)', content, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""
        
        articles.append({
            'year': year,
            'article': article_num,
            'title': title,
            'content': content,
            'clauses': clauses
        })
    
    return articles


def parse_clauses(article_content):
    """Parse các khoản trong một điều luật"""
    clauses = []
    
    # Pattern để tìm các khoản: "1." hoặc "Khoản 1"
    clause_patterns = [
        r'(?:^|\n)(\d+)\.\s+',  # Số thứ tự với dấu chấm
        r'Khoản\s+(\d+)[\.:]'    # "Khoản X"
    ]
    
    for pattern in clause_patterns:
        matches = list(re.finditer(pattern, article_content, re.MULTILINE))
        if matches:
            for i, match in enumerate(matches):
                clause_num = match.group(1)
                start_pos = match.start()
                
                if i < len(matches) - 1:
                    end_pos = matches[i + 1].start()
                else:
                    end_pos = len(article_content)
                
                clause_content = article_content[start_pos:end_pos].strip()
                
                # Tìm mức phạt trong khoản (nếu có)
                fine_info = extract_fine_info(clause_content)
                
                clauses.append({
                    'clause_number': clause_num,
                    'content': clause_content,
                    'fine_info': fine_info
                })
            break
    
    return clauses


def extract_fine_info(text):
    """Trích xuất thông tin về mức phạt"""
    fine_info = {
        'has_fine': False,
        'fine_amount': None,
        'fine_range': None,
        'violations': []
    }
    
    # Tìm mức phạt (VD: "400.000 đồng đến 600.000 đồng", "từ 2.000.000 đến 4.000.000 đồng")
    fine_patterns = [
        r'(?:phạt|phạt tiền)\s+(?:từ\s+)?(\d+(?:\.\d+)*)\s*(?:đồng|triệu)?\s*(?:đến|-)?\s*(\d+(?:\.\d+)*)?\s*(?:đồng|triệu)',
        r'mức\s+phạt\s+(?:từ\s+)?(\d+(?:\.\d+)*)\s*(?:đồng|triệu)?\s*(?:đến|-)?\s*(\d+(?:\.\d+)*)?\s*(?:đồng|triệu)',
    ]
    
    for pattern in fine_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fine_info['has_fine'] = True
            min_fine = match.group(1).replace('.', '')
            max_fine = match.group(2).replace('.', '') if match.group(2) else None
            
            # Xử lý đơn vị triệu
            if 'triệu' in match.group(0).lower():
                min_fine = str(int(min_fine) * 1000000)
                if max_fine:
                    max_fine = str(int(max_fine) * 1000000)
            
            if max_fine:
                fine_info['fine_range'] = f"{min_fine} - {max_fine}"
            else:
                fine_info['fine_amount'] = min_fine
            break
    
    # Tìm các hành vi vi phạm (thường bắt đầu bằng chữ thường hoặc trong danh sách)
    violation_patterns = [
        r'[a-z]\)\s*(.+?)(?=\n[a-z]\)|$)',  # a) b) c)...
        r'-\s*(.+?)(?=\n-|$)',               # Dấu gạch đầu dòng
    ]
    
    for pattern in violation_patterns:
        matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
        if matches:
            fine_info['violations'] = [v.strip() for v in matches if v.strip()]
            break
    
    return fine_info


def save_to_json(data, output_path):
    """Lưu dữ liệu ra file JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ Đã lưu file JSON: {output_path}")


def save_to_csv(data, output_path):
    """Lưu dữ liệu ra file CSV"""
    # Làm phẳng dữ liệu cho CSV
    flat_data = []
    for article in data:
        if article['clauses']:
            for clause in article['clauses']:
                row = {
                    'year': article['year'],
                    'article': article['article'],
                    'title': article['title'],
                    'clause_number': clause['clause_number'],
                    'content': clause['content'],
                    'has_fine': clause['fine_info']['has_fine'],
                    'fine_amount': clause['fine_info']['fine_amount'],
                    'fine_range': clause['fine_info']['fine_range'],
                    'violations': '; '.join(clause['fine_info']['violations'])
                }
                flat_data.append(row)
        else:
            # Nếu không có khoản, lưu toàn bộ điều
            row = {
                'year': article['year'],
                'article': article['article'],
                'title': article['title'],
                'clause_number': '',
                'content': article['content'],
                'has_fine': False,
                'fine_amount': '',
                'fine_range': '',
                'violations': ''
            }
            flat_data.append(row)
    
    if flat_data:
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=flat_data[0].keys())
            writer.writeheader()
            writer.writerows(flat_data)
        print(f"✓ Đã lưu file CSV: {output_path}")


def main():
    # Đường dẫn thư mục chứa PDF
    data_dir = Path(__file__).parent / 'data'
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)
    
    # Lấy danh sách file PDF
    pdf_files = list(data_dir.glob('*.pdf'))
    
    if not pdf_files:
        print("Không tìm thấy file PDF nào trong thư mục data/")
        return
    
    print(f"Tìm thấy {len(pdf_files)} file PDF:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file.name}")
    print()
    
    all_articles = []
    
    # Xử lý từng file PDF
    for pdf_file in pdf_files:
        print(f"Đang xử lý: {pdf_file.name}...")
        
        # Lấy năm từ tên file (VD: 2019.pdf -> 2019)
        year = pdf_file.stem
        
        try:
            # Trích xuất text từ PDF
            text = extract_text_from_pdf(pdf_file)
            
            # Parse các điều luật
            articles = parse_traffic_law(text, year)
            all_articles.extend(articles)
            
            print(f"  ✓ Đã parse {len(articles)} điều luật từ {pdf_file.name}")
            
        except Exception as e:
            print(f"  ✗ Lỗi khi xử lý {pdf_file.name}: {str(e)}")
    
    print(f"\nTổng cộng: {len(all_articles)} điều luật")
    
    # Lưu kết quả
    if all_articles:
        # Lưu ra JSON
        json_output = output_dir / 'traffic_laws.json'
        save_to_json(all_articles, json_output)
        
        # Lưu ra CSV
        csv_output = output_dir / 'traffic_laws.csv'
        save_to_csv(all_articles, csv_output)
        
        print(f"\n✓ Hoàn thành! Dữ liệu đã được lưu vào thư mục: {output_dir}")
    else:
        print("\n✗ Không có dữ liệu để lưu")


if __name__ == '__main__':
    main()
