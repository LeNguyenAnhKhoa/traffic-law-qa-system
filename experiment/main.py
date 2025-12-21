import os
import sys
import json
import asyncio
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

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Đường dẫn file Input/Output ---
INPUT_FILE = current_dir / "input" / "data.csv"
OUTPUT_DIR = current_dir / "output"
OUTPUT_FILE = OUTPUT_DIR / "experiment_result.csv"

# Tạo thư mục output nếu chưa có
os.makedirs(OUTPUT_DIR, exist_ok=True)

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
    logger.info("Bắt đầu quy trình chạy thực nghiệm...")

    # 1. Đọc dữ liệu
    if not INPUT_FILE.exists():
        logger.error(f"Không tìm thấy file input tại: {INPUT_FILE}")
        return

    try:
        df = pd.read_csv(INPUT_FILE)
        logger.info(f"Đã đọc {len(df)} dòng dữ liệu từ {INPUT_FILE}")
    except Exception as e:
        logger.error(f"Lỗi khi đọc file CSV: {e}")
        return

    # Kiểm tra cột Question
    if "Question" not in df.columns:
        logger.error("File CSV không có cột 'Question'")
        return

    # Đảm bảo cột Our System tồn tại và để kiểu object (string)
    if "Our System" not in df.columns:
        df["Our System"] = ""
    
    df["Our System"] = df["Our System"].astype(str)

    # 2. Xử lý từng dòng
    total_rows = len(df)
    
    # Batch save config (lưu mỗi 10 dòng để tránh mất dữ liệu nếu crash)
    save_interval = 10 

    for index, row in df.iterrows():
        question = row["Question"]
        row_id = row.get("ID", index)
        
        # Bỏ qua nếu câu hỏi rỗng
        if pd.isna(question) or str(question).strip() == "":
            continue
            
        logger.info(f"[{index + 1}/{total_rows}] Đang xử lý ID {row_id}: {question[:50]}...")
        
        # Gọi RAG
        answer = await get_rag_answer(str(question))
        
        # Ghi vào DataFrame
        df.at[index, "Our System"] = answer
        
        # Lưu định kỳ
        if (index + 1) % save_interval == 0:
            df.to_csv(OUTPUT_FILE, index=False)
            logger.info(f"Đã lưu checkpoint tại dòng {index + 1}")

    # 3. Lưu kết quả cuối cùng
    df.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"✅ Hoàn tất! Kết quả đã được lưu tại: {OUTPUT_FILE}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Đã dừng chương trình bởi người dùng.")
    except Exception as e:
        logger.error(f"Lỗi không mong muốn: {e}")