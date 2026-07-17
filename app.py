import streamlit as st
import pandas as pd
from PIL import Image
import easyocr
import numpy as np
import io

# =====================================================================
# 1. BẢO MẬT: BẮT BUỘC ĐĂNG NHẬP BẰNG KEY / PASSWORD
# (Tránh bị share link xài chùa)
# =====================================================================
VALID_KEYS = ["ADMIN123", "VIP_USER_2026", "STUDY_HARD_99"] # Danh sách Key của bạn

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 Xác Thực Truy Cập")
    user_key = st.text_input("Nhập mã kích hoạt của bạn:", type="password")
    if st.button("Kích hoạt"):
        if user_key in VALID_KEYS:
            st.session_state["authenticated"] = True
            st.success("Kích hoạt thành công! Vui lòng bấm F5 hoặc đợi 1s...")
            st.rerun()
        else:
            st.error("Mã kích hoạt không đúng hoặc đã hết hạn!")
    st.stop() # Dừng toàn bộ app nếu chưa nhập đúng Key

# =====================================================================
# 2. CODE CORE CHẠY APP (CHỈ CHẠY KHI ĐÃ NHẬP ĐÚNG KEY)
# =====================================================================
st.title("🔍 Trợ Lý Tìm Đáp Án Qua Ảnh (Bản Bảo Mật)")

# Dùng cache_data để KHÔNG load lại file Excel mỗi khi người dùng up ảnh
@st.cache_data
def load_database(uploaded_file):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    return None

# Dùng cache_resource để giữ bộ quét chữ OCR luôn trong bộ nhớ, không khởi động lại
@st.cache_resource
def load_ocr_model():
    return easyocr.Reader(['vi', 'en']) # Hỗ trợ Tiếng Việt và Tiếng Anh

reader = load_ocr_model()

# BƯỚC 1: Nạp ngân hàng câu hỏi
st.subheader("Bước 1: Nạp dữ liệu câu hỏi (.xlsx)")
excel_file = st.file_uploader("Tải file Excel câu hỏi lên", type=["xlsx"])
df_questions = load_database(excel_file)

if df_questions is not None:
    st.success("✅ Đã nạp dữ liệu câu hỏi thành công!")
    
    # BƯỚC 2: Tải ảnh câu hỏi lên
    st.subheader("Bước 2: Chụp hoặc tải ảnh câu hỏi")
    image_file = st.file_uploader("Upload hoặc chụp ảnh câu hỏi", type=["jpg", "jpeg", "png"])
    
    if image_file is not None:
        # TỰ ĐỘNG NÉN ẢNH: Chuyển đổi dung lượng lớn (5MB) về ảnh siêu nhẹ (dưới 300KB)
        image = Image.open(image_file)
        
        # Resize ảnh về kích thước tối đa 1024px để quét chữ nhanh hơn mà không giảm độ chính xác
        image.thumbnail((1024, 1024))
        
        # Nén ảnh dạng JPEG với chất lượng 80% (giảm tối đa dung lượng)
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=80)
        compressed_image_bytes = buffer.getvalue()
        
        # Đọc lại ảnh đã nén để đưa vào bộ OCR
        final_image = Image.open(io.BytesIO(compressed_image_bytes))
        image_np = np.array(final_image)
        
        st.info("⚡ Đang nén ảnh và trích xuất chữ viết...")
        
        # Quét chữ
        with st.spinner("Đang đọc chữ từ ảnh..."):
            results = reader.readtext(image_np, detail=0)
            scanned_text = " ".join(results)
        
        st.text_area("Nội dung chữ quét được từ ảnh:", scanned_text, height=100)
        
        # Thuật toán tìm kiếm thông minh trong Excel (bạn có thể thay bằng fuzzy matching)
        # Thuật toán tìm kiếm thông minh trong Excel
        # THUẬT TOÁN TÌM KIẾM MỚI: FUZZY MATCHING BẰNG RAPIDFUZZ
        if scanned_text.strip():
            st.subheader("🎯 Kết quả tra cứu:")
            
            # Cần import thêm thư viện này (Bạn nhớ thêm rapidfuzz vào file requirements.txt nhé)
            try:
                from rapidfuzz import process, fuzz
            except ImportError:
                st.error("Thiếu thư viện rapidfuzz. Hãy thêm 'rapidfuzz' vào requirements.txt")
                st.stop()
                
            # Tạo một list chứa toàn bộ nội dung của tất cả các cột để so sánh
            # Ở đây ta ưu tiên ghép nối các cột lại để có chuỗi so sánh dài nhất
            df_questions_str = df_questions.fillna("").astype(str)
            
            # Tạo một cột tạm chứa toàn bộ text của mỗi hàng
            df_questions_str['combined_text'] = df_questions_str.apply(lambda row: ' '.join(row.values), axis=1)
            choices = df_questions_str['combined_text'].tolist()
            
            # Sử dụng token_set_ratio của rapidfuzz để so khớp mờ. 
            # Dù OCR ra chữ "Lảm isc uen dường dày bung", nó vẫn tìm được câu "Làm đứt cáp đường dây điện"
            results_fuzz = process.extract(scanned_text, choices, scorer=fuzz.token_set_ratio, limit=5)
            
            # Lọc ra những kết quả có độ chính xác trên 40% (Bạn có thể tăng giảm số 40 này)
            valid_results = [res for res in results_fuzz if res[1] >= 40]
            
            if not valid_results:
                 st.warning("Không tìm thấy đáp án nào tương đồng. Vui lòng chụp rõ hơn!")
            else:
                st.success(f"🔍 Tìm thấy {len(valid_results)} kết quả tương đồng nhất!")
                
                for best_match, score, index in valid_results:
                    # Lấy ra đúng cái hàng (row) gốc trong file Excel dựa vào index
                    row_data = df_questions.iloc[index]
                    
                    st.markdown("---")
                    st.markdown(f"*(Độ tin cậy: {score:.1f}%)*") # Hiển thị số % giống nhau
                    
                    # Hiển thị kết quả y như cũ
                    if len(df_questions.columns) >= 2:
                        col_q = df_questions.columns[0]
                        col_a = df_questions.columns[1]
                        
                        st.markdown(f"**Câu hỏi:** {row_data[col_q]}")
                        st.info(f"👉 **Đáp án:** {row_data[col_a]}")
                        
                        for extra_col in df_questions.columns[2:]:
                             if pd.notna(row_data[extra_col]):
                                st.write(f"*{extra_col}:* {row_data[extra_col]}")
                    else:
                        st.markdown(f"**Nội dung tìm thấy:** {row_data[df_questions.columns[0]]}")
