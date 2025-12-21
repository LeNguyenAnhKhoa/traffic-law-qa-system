import os
import sys
import json
import asyncio
import argparse
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import logging

# --- Cấu hình đường dẫn ---
# Thêm thư mục backend vào sys.path để import được các module từ src
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Load biến môi trường
load_dotenv(current_dir.parent / ".env")

# --- Import Service ---
# Lưu ý: Import sau khi đã setup sys.path và load_dotenv
from src.services.rag_service import rag_service

# --- Cấu hình Logging ---
# Tạo thư mục logs nếu chưa tồn tại
LOG_DIR = current_dir / "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = LOG_DIR / "main.log"

# Cấu hình logging để xuất ra cả File và Console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'), # Ghi vào file logs/main.log
        logging.StreamHandler(sys.stdout)                # Ghi ra màn hình console
    ]
)
logger = logging.getLogger(__name__)

# --- Đường dẫn file Data ---
# File nằm tại experiment/data/data.csv
DATA_DIR = current_dir / "data"
DATA_FILE = DATA_DIR / "data.csv"

async def get_rag_answer(query: str) -> str:
    """
    Gọi RAG service và lấy câu trả lời cuối cùng từ stream.
    """
    final_answer = ""
    try:
        # rag_service.process_query trả về một async generator yield các JSON string
        async for chunk_str in rag_service.process_query(query):
            try:
                chunk_data = json.loads(chunk_str)
                # Chúng ta chỉ quan tâm đến type "answer"
                if chunk_data.get("type") == "answer":
                    # Trong rag_service.py, content của type 'answer' là full_answer (đã cộng dồn)
                    final_answer = chunk_data.get("content", "")
            except json.JSONDecodeError:
                continue
    except Exception as e:
        logger.error(f"Lỗi khi xử lý câu hỏi '{query}': {e}")
        return f"Error: {str(e)}"
    
    return final_answer

async def main():
    # --- Xử lý tham số dòng lệnh ---
    parser = argparse.ArgumentParser(description="Chạy thực nghiệm RAG Traffic Law")
    parser.add_argument("--start", type=int, default=None, help="ID bắt đầu xử lý")
    parser.add_argument("--end", type=int, default=None, help="ID kết thúc xử lý")
    args = parser.parse_args()

    logger.info("============== BẮT ĐẦU PHIÊN CHẠY MỚI ==============")
    logger.info("Bắt đầu quy trình chạy thực nghiệm...")
    
    if args.start is not None:
        logger.info(f"Cấu hình chạy từ ID: {args.start}")
    if args.end is not None:
        logger.info(f"Cấu hình chạy đến ID: {args.end}")

    # 1. Đọc dữ liệu
    if not DATA_FILE.exists():
        logger.error(f"Không tìm thấy file dữ liệu tại: {DATA_FILE}")
        return

    try:
        df = pd.read_csv(DATA_FILE)
        logger.info(f"Đã đọc {len(df)} dòng dữ liệu từ {DATA_FILE}")
    except Exception as e:
        logger.error(f"Lỗi khi đọc file CSV: {e}")
        return

    # Kiểm tra các cột cần thiết
    required_columns = ["ID", "Question"]
    for col in required_columns:
        if col not in df.columns:
            logger.error(f"File CSV thiếu cột '{col}'")
            return

    # Đảm bảo cột Our System tồn tại để ghi kết quả
    if "Our System" not in df.columns:
        df["Our System"] = ""
    
    # Chuyển cột Our System về dạng string để tránh lỗi
    df["Our System"] = df["Our System"].astype(str)

    # 2. Xử lý từng dòng
    total_rows = len(df)
    processed_count = 0
    
    # Batch save config (lưu mỗi 5 dòng để tránh mất dữ liệu nếu crash)
    save_interval = 5

    for index, row in df.iterrows():
        try:
            row_id = int(row["ID"])
        except ValueError:
            logger.warning(f"Dòng {index}: ID không hợp lệ ({row['ID']}), bỏ qua.")
            continue

        # --- Logic lọc theo ID ---
        if args.start is not None and row_id < args.start:
            continue
        
        if args.end is not None and row_id > args.end:
            continue

        question = row["Question"]
        
        # Bỏ qua nếu câu hỏi rỗng
        if pd.isna(question) or str(question).strip() == "":
            logger.warning(f"ID {row_id}: Câu hỏi trống, bỏ qua.")
            continue
            
        logger.info(f"Đang xử lý ID {row_id}: {str(question)[:50]}...")
        
        # Gọi RAG
        answer = await get_rag_answer(str(question))
        
        # Ghi vào DataFrame
        df.at[index, "Our System"] = answer
        processed_count += 1
        
        # Lưu định kỳ vào chính file data.csv
        if processed_count % save_interval == 0:
            df.to_csv(DATA_FILE, index=False)
            logger.info(f"Đã lưu checkpoint (ID vừa xong: {row_id}) vào {DATA_FILE.name}")

    # 3. Lưu kết quả cuối cùng
    df.to_csv(DATA_FILE, index=False)
    logger.info(f"✅ Hoàn tất! Đã xử lý {processed_count} câu hỏi.")
    logger.info(f"Kết quả đã được cập nhật tại: {DATA_FILE}")
    logger.info("============== KẾT THÚC PHIÊN CHẠY ==============\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Đã dừng chương trình bởi người dùng.")
    except Exception as e:
        logger.error(f"Lỗi không mong muốn: {e}")