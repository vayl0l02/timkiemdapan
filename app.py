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
        if scanned_text.strip():
            st.subheader("🎯 Kết quả tra cứu:")
            
            # Cải tiến: Trích xuất các từ khóa dài từ ảnh để tăng độ chính xác khi tìm kiếm
            # Bỏ qua các từ quá ngắn (như "a", "an", "là", "thì"...)
            keywords = [word.lower() for word in scanned_text.split() if len(word) > 2]
            
            if not keywords:
                st.warning("Ảnh quá mờ hoặc chứa quá ít chữ để nhận diện. Vui lòng thử lại!")
            else:
                # Tìm kiếm trên tất cả các cột của file Excel
                # Lọc ra những hàng có chứa ít nhất 1 từ khóa
                mask = pd.Series(False, index=df_questions.index)
                for col in df_questions.columns:
                    mask |= df_questions[col].astype(str).str.lower().apply(
                        lambda x: any(kw in x for kw in keywords)
                    )
                
                match_df = df_questions[mask]
                
                if not match_df.empty:
                    # Hiển thị số lượng kết quả tìm được
                    st.success(f"🔍 Tìm thấy {len(match_df)} kết quả phù hợp!")
                    
                    # Cải tiến giao diện hiển thị: In rõ câu hỏi và đáp án
                    for index, row in match_df.head(5).iterrows(): # Hiển thị tối đa 5 kết quả tốt nhất
                        st.markdown("---")
                        
                        # Giả định: 
                        # - Nếu file có 2 cột: Cột 1 là câu hỏi, cột 2 là đáp án
                        # - Nếu file có >2 cột: In ra toàn bộ thông tin của dòng đó
                        if len(df_questions.columns) >= 2:
                            col_q = df_questions.columns[0]
                            col_a = df_questions.columns[1]
                            
                            st.markdown(f"**Câu hỏi:** {row[col_q]}")
                            st.info(f"👉 **Đáp án:** {row[col_a]}")
                            
                            # Nếu có thêm các cột khác (ví dụ giải thích, môn học...), hiển thị thêm
                            for extra_col in df_questions.columns[2:]:
                                st.write(f"*{extra_col}:* {row[extra_col]}")
                        else:
                             # Phòng trường hợp file Excel chỉ có 1 cột
                             st.markdown(f"**Nội dung tìm thấy:** {row[df_questions.columns[0]]}")
                else:
                    st.error("❌ Không tìm thấy đáp án nào khớp với ảnh trong file Excel. Vui lòng kiểm tra lại ngân hàng câu hỏi!")
