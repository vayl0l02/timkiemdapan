import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
from difflib import SequenceMatcher

st.set_page_config(page_title="Trợ Lý Tìm Đáp Án", layout="centered")

st.title("🔍 Trợ Lý Tìm Đáp Án Qua Ảnh")
st.write("Tải file Excel câu hỏi lên, sau đó chụp hoặc up ảnh câu hỏi để tìm đáp án đúng ngay lập tức!")

# Khu vực upload File Excel
uploaded_excel = st.file_uploader("Bước 1: Upload File Excel câu hỏi (.xlsx)", type=["xlsx"])

if uploaded_excel:
    try:
        df = pd.read_excel(uploaded_excel)
        df.columns = [str(c).strip().lower() for c in df.columns]
        st.success("✅ Đã nạp dữ liệu Excel thành công!")
    except Exception as e:
        st.error(f"Lỗi đọc file Excel: {e}")
        df = None
else:
    df = None

# Khu vực upload Ảnh câu hỏi
uploaded_image = st.file_uploader("Bước 2: Upload hoặc chụp ảnh câu hỏi", type=["jpg", "jpeg", "png"])

if uploaded_image and df is not None:
    image = Image.open(uploaded_image)
    st.image(image, caption="Ảnh đã tải lên", use_container_width=True)
    
    with st.spinner("🔄 Đang quét chữ từ ảnh (Sử dụng Tesseract siêu nhẹ)..."):
        try:
            # Sử dụng Tesseract quét cả tiếng Việt và tiếng Anh
            scanned_text = pytesseract.image_to_string(image, lang='vie+eng').strip()
        except Exception as e:
            st.error(f"Lỗi hệ thống khi quét ảnh: {e}")
            scanned_text = ""
        
    if scanned_text:
        st.info(f"📝 **Chữ quét được từ ảnh:** {scanned_text}")
        
        # Tìm câu hỏi khớp nhất trong Excel
        best_match_idx = -1
        highest_ratio = 0.0
        
        q_column = None
        for col in df.columns:
            if 'cau' in col or 'hoi' in col or 'question' in col:
                q_column = col
                break
        if not q_column:
            q_column = df.columns[0]
            
        for idx, row in df.iterrows():
            question_in_db = str(row[q_column])
            ratio = SequenceMatcher(None, scanned_text.lower(), question_in_db.lower()).ratio()
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match_idx = idx
                
        if highest_ratio > 0.25:  # Hạ nhẹ tỷ lệ khớp tối thiểu để bù sai sót ký tự
            matched_row = df.iloc[best_match_idx]
            st.success(f"🎯 **Tìm thấy câu hỏi khớp nhất (Độ chính xác: {highest_ratio*100:.1f}%)**")
            st.markdown(f"### **Câu hỏi:** {matched_row[q_column]}")
            
            cols_ans = [c for c in df.columns if c in ['a', 'b', 'c', 'd']]
            if cols_ans:
                for col in cols_ans:
                    st.write(f"- **{col.upper()}:** {matched_row[col]}")
            
            correct_col = [c for c in df.columns if 'dung' in c or 'correct' in c or 'dap an' in c]
            if correct_col:
                correct_ans = str(matched_row[correct_col[0]]).upper()
                st.markdown(f"## 🚨 **ĐÁP ÁN ĐÚNG: {correct_ans}**")
        else:
            st.warning("⚠️ Không tìm thấy câu hỏi nào đủ giống trong cơ sở dữ liệu Excel của bạn.")
    else:
        st.error("Không thể đọc được chữ từ bức ảnh này. Bạn hãy thử chụp ảnh rõ nét hơn nhé!")
