import os
import json
import csv
import re
from pypdf import PdfReader
from pathlib import Path


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def parse_traffic_law(text, year):
    """Parse traffic law content into structured articles."""
    articles = []
    
    # Pattern to find articles: "Điều X." or "Điều X:"
    article_pattern = r'Điều\s+(\d+[a-z]?)[\.:]'
    
    # Split text into articles
    matches = list(re.finditer(article_pattern, text, re.IGNORECASE))
    
    for i, match in enumerate(matches):
        article_num = match.group(1)
        start_pos = match.start()
        
        # Get content from this article to the next (or end of text)
        if i < len(matches) - 1:
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(text)
        
        content = text[start_pos:end_pos].strip()
        
        # Parse clauses in the article
        clauses = parse_clauses(content)
        
        # Find article title (if available)
        # Identify the prefix "Điều X."
        prefix_match = re.match(r'Điều\s+\d+[a-z]?[\.:]', content, re.IGNORECASE)
        if prefix_match:
            prefix_end = prefix_match.end()
            
            # Find the starting position of the first clause
            first_clause_start = len(content)
            
            # Pattern to find clauses: "1." or "Khoản 1"
            clause_patterns = [
                r'(?:^|\n)(\d+)\.\s+',  # Numbered with period
                r'(?:^|\n)Khoản\s+(\d+)[\.:]'    # "Khoản X"
            ]
            
            for pattern in clause_patterns:
                # Find in remaining content
                match = re.search(pattern, content[prefix_end:])
                if match:
                    first_clause_start = prefix_end + match.start()
                    break
            
            title_raw = content[prefix_end:first_clause_start].strip()
            # Clean title: replace newlines with spaces
            title = re.sub(r'\s+', ' ', title_raw).strip()
        else:
            title = ""
        
        articles.append({
            'year': year,
            'article': article_num,
            'title': title,
            'content': content,
            'clauses': clauses
        })
    
    return articles


def parse_clauses(article_content):
    """Parse clauses within an article."""
    clauses = []
    
    # Pattern to find clauses: "1." or "Khoản 1"
    clause_patterns = [
        r'(?:^|\n)(\d+)\.\s+',  # Numbered with period
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
                
                # Find fine information in the clause (if any)
                fine_info = extract_fine_info(clause_content)
                
                clauses.append({
                    'clause_number': clause_num,
                    'content': clause_content,
                    'fine_info': fine_info
                })
            break
    
    return clauses


def extract_fine_info(text):
    """Extract fine information from text."""
    fine_info = {
        'has_fine': False,
        'fine_amount': None,
        'fine_range': None,
        'violations': []
    }
    
    # Find fine amount (e.g., "400.000 đồng đến 600.000 đồng", "từ 2.000.000 đến 4.000.000 đồng")
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
            
            # Handle million unit
            if 'triệu' in match.group(0).lower():
                min_fine = str(int(min_fine) * 1000000)
                if max_fine:
                    max_fine = str(int(max_fine) * 1000000)
            
            if max_fine:
                fine_info['fine_range'] = f"{min_fine} - {max_fine}"
            else:
                fine_info['fine_amount'] = min_fine
            break
    
    # Find violations (usually start with lowercase or in lists)
    violation_patterns = [
        r'[a-z]\)\s*(.+?)(?=\n[a-z]\)|$)',  # a) b) c)...
        r'-\s*(.+?)(?=\n-|$)',               # Bullet points
    ]
    
    for pattern in violation_patterns:
        matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
        if matches:
            fine_info['violations'] = [v.strip() for v in matches if v.strip()]
            break
    
    return fine_info


def save_to_json(data, output_path):
    """Save data to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved JSON file: {output_path}")


def save_to_csv(data, output_path):
    """Save data to CSV file."""
    # Flatten data for CSV
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
            # If no clauses, save the entire article
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
        print(f"✓ Saved CSV file: {output_path}")


def main():
    # Directory path containing PDFs
    data_dir = Path(__file__).parent / 'data'
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(exist_ok=True)
    
    # Get list of PDF files
    pdf_files = list(data_dir.glob('*.pdf'))
    
    if not pdf_files:
        print("No PDF files found in data/ directory")
        return
    
    print(f"Found {len(pdf_files)} PDF files:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file.name}")
    print()
    
    all_articles = []
    
    # Process each PDF file
    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}...")
        
        # Get year from filename (e.g., 2019.pdf -> 2019)
        year = pdf_file.stem
        
        try:
            # Extract text from PDF
            text = extract_text_from_pdf(pdf_file)
            
            # Parse articles
            articles = parse_traffic_law(text, year)
            all_articles.extend(articles)
            
            print(f"  ✓ Parsed {len(articles)} articles from {pdf_file.name}")
            
        except Exception as e:
            print(f"  ✗ Error processing {pdf_file.name}: {str(e)}")
    
    print(f"\nTotal: {len(all_articles)} articles")
    
    # Save results
    if all_articles:
        # Save to JSON
        json_output = output_dir / 'traffic_laws.json'
        save_to_json(all_articles, json_output)
        
        # Save to CSV
        csv_output = output_dir / 'traffic_laws.csv'
        save_to_csv(all_articles, csv_output)
        
        print(f"\n✓ Done! Data saved to directory: {output_dir}")
    else:
        print("\n✗ No data to save")


if __name__ == '__main__':
    main()
