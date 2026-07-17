import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
from rapidfuzz import process, fuzz
import numpy as np

# Cấu hình giao diện Streamlit
st.set_page_config(page_title="Trợ Lý Tìm Đáp Án", layout="centered")

st.title("🔍 Trợ Lý Tìm Đáp Án Qua Ảnh")

# 1. Hàm nạp dữ liệu (Load 1 lần để tăng tốc)
@st.cache_data
def load_data(file):
    return pd.read_excel(file)

# 2. Xử lý ảnh trước khi quét để tăng độ chính xác OCR
def preprocess_image(image):
    # Chuyển ảnh màu sang trắng đen (Grayscale)
    img_gray = image.convert('L')
    return img_gray

# GIAO DIỆN CHÍNH
st.markdown("### Bước 1: Tải file dữ liệu (.xlsx)")
excel_file = st.file_uploader("Chọn file Excel (Cột 1: Câu hỏi, Cột 2: Đáp án)", type=["xlsx"])

if excel_file:
    df = load_data(excel_file)
    st.success(f"✅ Đã nạp {len(df)} câu hỏi.")
    
    st.markdown("### Bước 2: Tải ảnh câu hỏi")
    image_file = st.file_uploader("Chọn ảnh cần quét", type=["png", "jpg", "jpeg"])
    
    if image_file:
        # Hiển thị ảnh đang quét
        image = Image.open(image_file)
        st.image(image, caption="Ảnh của bạn", width=300)
        
        with st.spinner("Đang quét chữ..."):
            try:
                # Tiền xử lý và quét chữ
                processed_img = preprocess_image(image)
                # lang='vie' bắt buộc Tesseract dùng bộ nhận diện Tiếng Việt
                scanned_text = pytesseract.image_to_string(processed_img, lang='vie') 
            except Exception as e:
                st.error("Lỗi hệ thống OCR. Đảm bảo đã cài đặt Tesseract trên server.")
                st.stop()

        # Hiển thị chữ quét được (để bạn kiểm tra xem nó quét đúng/sai)
        with st.expander("Nội dung quét được (Bấm để xem)"):
            st.write(scanned_text)

        # 3. THUẬT TOÁN TÌM KIẾM ĐÁP ÁN (Ngưỡng >= 80)
        if scanned_text.strip():
            st.markdown("### 🎯 KẾT QUẢ:")
            
            # Gộp tất cả các cột thành 1 chuỗi để tìm kiếm
            df_str = df.fillna("").astype(str)
            df_str['Tim_Kiem'] = df_str.apply(lambda row: ' '.join(row.values), axis=1)
            danh_sach_cau_hoi = df_str['Tim_Kiem'].tolist()
            
            # Quét tìm câu giống nhất bằng Rapidfuzz
            ket_qua_tim_kiem = process.extract(
                scanned_text, 
                danh_sach_cau_hoi, 
                scorer=fuzz.token_set_ratio, 
                limit=3
            )
            
            # Lọc kết quả: Lấy những câu có độ khớp >= 80%
            ket_qua_chinh_xac = [kq for kq in ket_qua_tim_kiem if kq[1] >= 80]
            
            if not ket_qua_chinh_xac:
                st.warning("⚠️ Không tìm thấy đáp án chính xác (Độ khớp < 80%). Bạn hãy chụp rõ hơn.")
            else:
                # In ra các đáp án tìm được
                for text_match, score, index in ket_qua_chinh_xac:
                    hang_du_lieu = df.iloc[index]
                    
                    st.markdown("---")
                    
                    # Giả định cột 0 là Câu hỏi, cột 1 là Đáp án
                    if len(df.columns) >= 2:
                        cot_cau_hoi = df.columns[0]
                        cot_dap_an = df.columns[1]
                        
                        st.markdown(f"**❓ Câu hỏi:** {hang_du_lieu[cot_cau_hoi]}")
                        st.success(f"**💡 Đáp án:** {hang_du_lieu[cot_dap_an]}")
                    else:
                        st.success(f"**Nội dung:** {hang_du_lieu[df.columns[0]]}")
