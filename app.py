import streamlit as st
import pandas as pd
import easyocr
from PIL import Image
import numpy as np
from difflib import SequenceMatcher

st.set_page_config(page_title="Trợ Lý Tìm Đáp Án", layout="centered")

st.title("🔍 Trợ Lý Tìm Đáp Án Qua Ảnh")
st.write("Tải file Excel câu hỏi lên, sau đó chụp hoặc up ảnh câu hỏi để tìm đáp án đúng ngay lập tức!")

# 1. Khởi tạo bộ đọc chữ OCR (Lưu vào bộ nhớ để không bị load lại nhiều lần)
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['vi', 'en']) # Hỗ trợ tiếng Việt và tiếng Anh

reader = load_ocr()

# 2. Khu vực upload File Excel
uploaded_excel = st.file_uploader("Bước 1: Upload File Excel câu hỏi (.xlsx)", type=["xlsx"])

if uploaded_excel:
    try:
        df = pd.read_excel(uploaded_excel)
        # Chuẩn hóa tên cột viết thường, bỏ dấu để tránh lỗi
        df.columns = [str(c).strip().lower() for c in df.columns]
        st.success("✅ Đã nạp dữ liệu Excel thành công!")
    except Exception as e:
        st.error(f"Lỗi đọc file Excel: {e}")
        df = None
else:
    df = None

# 3. Khu vực upload Ảnh câu hỏi
uploaded_image = st.file_uploader("Bước 2: Upload hoặc chụp ảnh câu hỏi", type=["jpg", "jpeg", "png"])

if uploaded_image and df is not None:
    # Hiển thị ảnh đã up
    image = Image.open(uploaded_image)
    st.image(image, caption="Ảnh đã tải lên", use_container_width=True)
    
    with st.spinner("🔄 Đang đọc chữ từ ảnh..."):
        # Chuyển ảnh thành dạng mà thư viện OCR đọc được
        img_np = np.array(image)
        results = reader.readtext(img_np, detail=0)
        
        # Ghép các dòng chữ đọc được thành 1 đoạn văn bản
        scanned_text = " ".join(results).strip()
        
    if scanned_text:
        st.info(f"📝 **Chữ quét được từ ảnh:** {scanned_text}")
        
        # 4. Tìm câu hỏi khớp nhất trong Excel
        best_match_idx = -1
        highest_ratio = 0.0
        
        # Tìm cột chứa câu hỏi (cột có chữ 'cau' hoặc 'hoi' hoặc cột đầu tiên)
        q_column = None
        for col in df.columns:
            if 'cau' in col or 'hoi' in col or 'question' in col:
                q_column = col
                break
        if not q_column:
            q_column = df.columns[0] # Mặc định lấy cột đầu tiên nếu không tìm thấy
            
        # Thuật toán so khớp mờ tìm câu hỏi giống nhất
        for idx, row in df.iterrows():
            question_in_db = str(row[q_column])
            # Tính tỉ lệ giống nhau giữa chữ trên ảnh và câu hỏi trong Excel
            ratio = SequenceMatcher(None, scanned_text.lower(), question_in_db.lower()).ratio()
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match_idx = idx
                
        # Hiển thị kết quả nếu độ chính xác trên 30%
        if highest_ratio > 0.3:
            matched_row = df.iloc[best_match_idx]
            
            st.success(f"🎯 **Tìm thấy câu hỏi khớp nhất (Độ chính xác: {highest_ratio*100:.1f}%)**")
            
            # Hiển thị nội dung
            st.markdown(f"### **Câu hỏi:** {matched_row[q_column]}")
            
            # Lấy các cột đáp án
            cols_ans = [c for c in df.columns if c in ['a', 'b', 'c', 'd']]
            if cols_ans:
                for col in cols_ans:
                    st.write(f"- **{col.upper()}:** {matched_row[col]}")
            
            # Hiển thị đáp án đúng nổi bật
            correct_col = [c for c in df.columns if 'dung' in c or 'correct' in c or 'dap an' in c]
            if correct_col:
                correct_ans = str(matched_row[correct_col[0]]).upper()
                st.markdown(f"## 🚨 **ĐÁP ÁN ĐÚNG: {correct_ans}**")
        else:
            st.warning("⚠️ Không tìm thấy câu hỏi nào đủ giống trong cơ sở dữ liệu Excel của bạn.")
    else:
        st.error("Không thể đọc được chữ từ bức ảnh này. Bạn hãy thử chụp ảnh rõ nét hơn nhé!")
