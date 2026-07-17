import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
import easyocr
import numpy as np
from rapidfuzz import process, fuzz
import io

# Cấu hình giao diện
st.set_page_config(page_title="Trợ Lý Tìm Đáp Án", layout="centered")
st.title("🔍 Trợ Lý Tìm Đáp Án Qua Ảnh")

# 1. Nạp bộ quét OCR (Load 1 lần, lưu vào bộ nhớ đệm)
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['vi']) # Chỉ nạp Tiếng Việt để chạy nhanh và nhẹ hơn

reader = load_ocr()

# 2. Nạp dữ liệu Excel (Load 1 lần)
@st.cache_data
def load_data(file):
    return pd.read_excel(file)

# 3. Kỹ thuật xử lý ảnh chụp bằng điện thoại (Binarization & Resize)
def preprocess_for_easyocr(image):
    # BƯỚC QUAN TRỌNG NHẤT: Thu nhỏ ảnh để chống sập Server
    # Ảnh dù có to mấy cũng sẽ bị bóp về kích thước an toàn, không quá 1024px
    image.thumbnail((1024, 1024))
    
    # Chuyển ảnh màu sang xám
    img_gray = image.convert('L')
    # Tự động tăng độ tương phản để chữ rõ hơn
    img_contrast = ImageOps.autocontrast(img_gray)
    
    # Phân ngưỡng (Ép mọi thứ tối thành Đen, sáng thành Trắng)
    threshold = 150
    fn = lambda x : 255 if x > threshold else 0
    img_binarized = img_contrast.point(fn, mode='L') 
    
    return np.array(img_binarized)

# ================= GIAO DIỆN CHÍNH =================
st.markdown("### Bước 1: Tải ngân hàng câu hỏi")
excel_file = st.file_uploader("Chọn file Excel (cau hoi.xlsx)", type=["xlsx"])

if excel_file:
    df = load_data(excel_file)
    st.success(f"✅ Đã nạp thành công {len(df)} câu hỏi!")
    
    st.markdown("### Bước 2: Tải ảnh chụp câu hỏi")
    image_file = st.file_uploader("Upload ảnh (nhớ cắt/crop sát vùng chữ)", type=["png", "jpg", "jpeg"])
    
    if image_file:
        image = Image.open(image_file)
        st.image(image, caption="Ảnh bạn vừa tải lên", width=350)
        
        with st.spinner("⏳ Đang phân tích hình ảnh và trích xuất chữ..."):
            # Chạy hàm xử lý ảnh bóng lóa/mờ
            processed_img_np = preprocess_for_easyocr(image)
            
            # Quét chữ bằng EasyOCR
            results = reader.readtext(processed_img_np, detail=0)
            scanned_text = " ".join(results)

        # Hiển thị chữ để bạn kiểm tra thuật toán đọc đúng không
        with st.expander("👀 Xem nội dung chữ đã nhận diện"):
            st.write(scanned_text)

        # 4. THUẬT TOÁN TÌM KIẾM (Chỉ hiện kết quả khi tỷ lệ khớp >= 75%)
        if scanned_text.strip():
            st.markdown("### 🎯 KẾT QUẢ TRA CỨU:")
            
            # Xử lý gộp 5 cột Excel thành 1 chuỗi dài để tìm cho chuẩn
            df_str = df.fillna("").astype(str)
            df_str['Tim_Kiem'] = df_str['Cau hoi'] + " " + df_str['A'] + " " + df_str['B'] + " " + df_str['C'] + " " + df_str['D']
            danh_sach_cau_hoi = df_str['Tim_Kiem'].tolist()
            
            # Tìm 3 câu giống nhất bằng RapidFuzz
            ket_qua_tim_kiem = process.extract(
                scanned_text, 
                danh_sach_cau_hoi, 
                scorer=fuzz.token_set_ratio, 
                limit=3
            )
            
            # Chỉ lấy các câu có độ khớp từ 75% trở lên
            ket_qua_chinh_xac = [kq for kq in ket_qua_tim_kiem if kq[1] >= 75]
            
            if not ket_qua_chinh_xac:
                st.error("❌ Không có câu nào khớp trên 75%. Thử crop ảnh sát vào chữ và chụp lại nhé!")
            else:
                for text_match, score, index in ket_qua_chinh_xac:
                    hang = df.iloc[index]
                    
                    st.markdown("---")
                    st.markdown(f"*(Tỷ lệ khớp: {score:.1f}%)*")
                    
                    # In CÂU HỎI
                    st.markdown(f"**❓ {hang.get('Cau hoi', '')}**")
                    
                    # In 4 ĐÁP ÁN (A, B, C, D)
                    for phuong_an in ['A', 'B', 'C', 'D']:
                        if pd.notna(hang.get(phuong_an)) and str(hang.get(phuong_an)).strip():
                            st.write(f"**{phuong_an}.** {hang[phuong_an]}")
                    
                    # In ĐÁP ÁN ĐÚNG (Bôi xanh nổi bật)
                    dap_an_dung = str(hang.get('Dap an dung', '')).strip().upper()
                    
                    if dap_an_dung in ['A', 'B', 'C', 'D']:
                        noi_dung_dap_an = str(hang[dap_an_dung]).strip()
                        st.success(f"**💡 ĐÁP ÁN: {dap_an_dung}** - {noi_dung_dap_an}")
                    else:
                        st.success(f"**💡 ĐÁP ÁN:** {dap_an_dung}")
