import os
import csv
import logging
import argparse
import time
from typing import List, Dict
from dotenv import load_dotenv
from openai import OpenAI

# 1. Cấu hình Logging
# Tạo thư mục logs nếu chưa tồn tại
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "nvidia.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 2. Load biến môi trường
# Load .env từ thư mục hiện tại hoặc thư mục cha
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

NVIDIA_URL = os.getenv("NVIDIA_URL")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL")

def get_nvidia_response(client: OpenAI, question: str) -> str:
    """
    Gửi câu hỏi đến NVIDIA Model qua OpenAI SDK và trả về nội dung phản hồi.
    Không config gì thêm ngoài user_prompt.
    """
    try:
        response = client.chat.completions.create(
            model=NVIDIA_MODEL,
            messages=[
                {"role": "user", "content": question}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Lỗi khi gọi API cho câu hỏi: {question[:30]}... - Error: {e}")
        return "ERROR_FETCHING"

def main():
    # 3. Parse tham số dòng lệnh
    parser = argparse.ArgumentParser(description="Chạy inference sử dụng model NVIDIA.")
    parser.add_argument("--start", type=int, default=None, help="ID bắt đầu (inclusive)")
    parser.add_argument("--end", type=int, default=None, help="ID kết thúc (inclusive)")
    args = parser.parse_args()

    # Kiểm tra biến môi trường
    if not all([NVIDIA_URL, NVIDIA_API_KEY, NVIDIA_MODEL]):
        logger.error("Thiếu biến môi trường (NVIDIA_URL, NVIDIA_API_KEY, NVIDIA_MODEL). Vui lòng kiểm tra file .env")
        return

    # Khởi tạo Client
    client = OpenAI(
        base_url=NVIDIA_URL,
        api_key=NVIDIA_API_KEY
    )

    data_path = "./data/data.csv"
    if not os.path.exists(data_path):
        logger.error(f"Không tìm thấy file dữ liệu tại: {data_path}")
        return

    # 4. Đọc dữ liệu
    rows: List[Dict[str, str]] = []
    fieldnames: List[str] = []
    
    logger.info(f"Đang đọc file {data_path}...")
    try:
        with open(data_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            fieldnames = reader.fieldnames
            rows = list(reader)
    except Exception as e:
        logger.error(f"Lỗi đọc file CSV: {e}")
        return

    # Đảm bảo cột output tồn tại trong header
    target_column = "Deepseek v3.1"
    if target_column not in fieldnames:
        fieldnames.append(target_column)

    # 5. Xử lý Inference
    process_count = 0
    
    logger.info(f"Bắt đầu inference với Model: {NVIDIA_MODEL}")
    if args.start is not None or args.end is not None:
        logger.info(f"Phạm vi ID: {args.start} -> {args.end}")
    else:
        logger.info("Phạm vi: Toàn bộ file")

    for row in rows:
        try:
            row_id = int(row.get("ID", -1))
        except ValueError:
            logger.warning(f"Bỏ qua dòng có ID không hợp lệ: {row.get('ID')}")
            continue

        # Logic lọc theo ID start/end
        if args.start is not None and row_id < args.start:
            continue
        if args.end is not None and row_id > args.end:
            continue

        # Lấy câu hỏi và gọi API
        question = row.get("Question", "")
        if question:
            logger.info(f"Đang xử lý ID {row_id}...")
            answer = get_nvidia_response(client, question)
            
            # Ghi vào cột Deepseek v3.1
            row[target_column] = answer
            process_count += 1
            time.sleep(2)  # Thêm delay 2 giây giữa các lần gọi API
        else:
            logger.warning(f"ID {row_id} không có nội dung Question.")

    logger.info(f"Đã xử lý xong {process_count} mẫu.")

    # 6. Ghi đè lại file CSV
    logger.info(f"Đang lưu kết quả vào {data_path}...")
    try:
        with open(data_path, mode='w', encoding='utf-8', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        logger.info("Lưu file thành công.")
    except Exception as e:
        logger.error(f"Lỗi khi ghi file CSV: {e}")

if __name__ == "__main__":
    main()