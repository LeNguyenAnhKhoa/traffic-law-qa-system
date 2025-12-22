import os
import argparse
import logging
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

# Cấu hình đường dẫn
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'data.csv')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'openai.log')
ENV_PATH = os.path.join(os.path.dirname(BASE_DIR), '.env')  # Giả định .env nằm ở thư mục gốc dự án

# Load biến môi trường từ file .env
load_dotenv(ENV_PATH)

# Cấu hình Logging
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    # Cấu hình tham số dòng lệnh
    parser = argparse.ArgumentParser(description="Chạy inference với GPT-5-mini")
    parser.add_argument('--start', type=int, default=None, help="ID bắt đầu")
    parser.add_argument('--end', type=int, default=None, help="ID kết thúc")
    args = parser.parse_args()

    # Kiểm tra API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("Không tìm thấy OPENAI_API_KEY trong file .env")
        return

    # Khởi tạo OpenAI Client
    client = OpenAI(api_key=api_key)

    # Đọc dữ liệu
    try:
        df = pd.read_csv(DATA_FILE)
        logger.info(f"Đã đọc file dữ liệu: {DATA_FILE}")
    except Exception as e:
        logger.error(f"Lỗi khi đọc file CSV: {e}")
        return

    # Xác định phạm vi ID cần chạy
    min_id = df['ID'].min()
    max_id = df['ID'].max()
    
    start_id = args.start if args.start is not None else min_id
    end_id = args.end if args.end is not None else max_id

    logger.info(f"Bắt đầu xử lý các ID từ {start_id} đến {end_id}")

    processed_count = 0

    # Duyệt qua từng dòng trong DataFrame
    for index, row in df.iterrows():
        current_id = row['ID']

        # Bỏ qua nếu ID nằm ngoài phạm vi yêu cầu
        if current_id < start_id or current_id > end_id:
            continue

        question = row['Question']
        logger.info(f"Đang xử lý ID: {current_id}...")

        try:
            # Gọi OpenAI API
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "user", "content": question}
                ],
                reasoning_effort="low"
            )

            # Lấy câu trả lời
            answer = response.choices[0].message.content
            
            # Ghi vào cột GPT-5-mini
            df.at[index, 'GPT-5-mini'] = answer
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý ID {current_id}: {e}")

    # Ghi lại file CSV sau khi chạy xong
    try:
        df.to_csv(DATA_FILE, index=False)
        logger.info(f"Hoàn tất. Đã lưu dữ liệu vào {DATA_FILE}")
        logger.info(f"Tổng số câu đã xử lý: {processed_count}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu file CSV: {e}")

if __name__ == "__main__":
    main()