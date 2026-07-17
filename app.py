import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
from rapidfuzz import process, fuzz

# Cấu hình giao diện Streamlit
st.set_page_config(page_title="Trợ Lý Tìm Đáp Án", layout="centered")

st.title("🔍 Trợ Lý Tìm Đáp Án Qua Ảnh")

# 1. Hàm nạp dữ liệu (Load 1 lần để tăng tốc)
@st.cache_data
def load_data(file):
    return pd.read_excel(file)

# 2. Xử lý ảnh trước khi quét 
def preprocess_image(image):
    return image.convert('L') # Chuyển sang trắng đen giúp Tesseract đọc tốt hơn

st.markdown("### Bước 1: Tải file dữ liệu (.xlsx)")
excel_file = st.file_uploader("Chọn file Excel (cau hoi.xlsx)", type=["xlsx"])

if excel_file:
    df = load_data(excel_file)
    st.success(f"✅ Đã nạp thành công {len(df)} câu hỏi.")
    
    st.markdown("### Bước 2: Tải ảnh câu hỏi")
    image_file = st.file_uploader("Chọn ảnh cần quét", type=["png", "jpg", "jpeg"])
    
    if image_file:
        image = Image.open(image_file)
        st.image(image, caption="Ảnh của bạn", width=300)
        
        with st.spinner("Đang quét chữ..."):
            try:
                processed_img = preprocess_image(image)
                # Dùng Tesseract quét tiếng Việt
                scanned_text = pytesseract.image_to_string(processed_img, lang='vie') 
            except Exception as e:
                st.error("Lỗi hệ thống OCR. Đảm bảo đã cài file packages.txt trên server.")
                st.stop()

        with st.expander("Nội dung quét được (Bấm để xem)"):
            st.write(scanned_text)

        # 3. THUẬT TOÁN TÌM KIẾM ĐÁP ÁN (Ngưỡng >= 80%)
        if scanned_text.strip():
            st.markdown("### 🎯 KẾT QUẢ:")
            
            df_str = df.fillna("").astype(str)
            # Gộp Câu hỏi và 4 đáp án lại thành 1 chuỗi để tăng tỷ lệ so khớp trúng
            df_str['Tim_Kiem'] = df_str['Cau hoi'] + " " + df_str['A'] + " " + df_str['B'] + " " + df_str['C'] + " " + df_str['D']
            danh_sach_cau_hoi = df_str['Tim_Kiem'].tolist()
            
            ket_qua_tim_kiem = process.extract(
                scanned_text, 
                danh_sach_cau_hoi, 
                scorer=fuzz.token_set_ratio, 
                limit=3
            )
            
            ket_qua_chinh_xac = [kq for kq in ket_qua_tim_kiem if kq[1] >= 80]
            
            if not ket_qua_chinh_xac:
                st.warning("⚠️ Không tìm thấy đáp án (Độ khớp < 80%). Bạn hãy chụp sát và rõ chữ hơn nhé.")
            else:
                for text_match, score, index in ket_qua_chinh_xac:
                    hang = df.iloc[index]
                    
                    st.markdown("---")
                    # In ra câu hỏi
                    st.markdown(f"**❓ {hang.get('Cau hoi', '')}**")
                    
                    # In ra 4 đáp án
                    if pd.notna(hang.get('A')) and str(hang.get('A')).strip(): st.write(f"**A.** {hang['A']}")
                    if pd.notna(hang.get('B')) and str(hang.get('B')).strip(): st.write(f"**B.** {hang['B']}")
                    if pd.notna(hang.get('C')) and str(hang.get('C')).strip(): st.write(f"**C.** {hang['C']}")
                    if pd.notna(hang.get('D')) and str(hang.get('D')).strip(): st.write(f"**D.** {hang['D']}")
                    
                    # Trích xuất và in ra đáp án đúng
                    dap_an_dung = str(hang.get('Dap an dung', '')).strip().upper()
                    
                    if dap_an_dung in ['A', 'B', 'C', 'D']:
                        noi_dung_dap_an = str(hang[dap_an_dung]).strip()
                        st.success(f"**💡 ĐÁP ÁN ĐÚNG: {dap_an_dung}** - {noi_dung_dap_an}")
                    else:
                        st.success(f"**💡 ĐÁP ÁN ĐÚNG:** {dap_an_dung}")
