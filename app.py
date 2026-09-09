import os
import time
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError
from PIL import Image
import pypdf

# ---------------------------------------------------------
# 1. การตั้งค่าหน้าเว็บ และการดึง API Key
# ---------------------------------------------------------
st.set_page_config(
    page_title="สรุปบทเรียน & เนื้อหาหนังสือ",
    page_icon="📚",
    layout="wide"
)

# โหลด API Key (รองรับทั้ง Streamlit Secrets และ .env)
load_dotenv()
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("❌ ไม่พบ GEMINI_API_KEY กรุณาตั้งค่าใน Streamlit Secrets หรือไฟล์ .env")
    st.stop()

# สร้าง Client
client = genai.Client(api_key=api_key)

# ---------------------------------------------------------
# 2. ฟังก์ชันเรียกใช้งาน Gemini พร้อมระบบกัน Error 503 (Retry)
# ---------------------------------------------------------
def generate_content_with_retry(client, model, contents, config=None, max_retries=3):
    """ส่งคำสั่งไปยัง Gemini พร้อมลองซ้ำให้อัตโนมัติเมื่อเจอ 503 UNAVAILABLE"""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            return response.text
        except APIError as e:
            # หากเจอ Error 503 ให้รอ 2 วินาที แล้วลองใหม่
            if ("503" in str(e) or "UNAVAILABLE" in str(e)) and attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                raise e

# ---------------------------------------------------------
# 3. ส่วนแสดงผล UI หน้าเว็บ
# ---------------------------------------------------------
st.title("📚 สรุปบทเรียน & เนื้อหาหนังสือ")
st.caption("วางข้อความ, อัปโหลดไฟล์ PDF หรืออัปโหลดรูปภาพหน้าหนังสือ เพื่อให้ AI สรุปเนื้อหาและสูตรสำคัญให้อัตโนมัติ")

# แถบเมนูด้านข้าง (Sidebar)
with st.sidebar:
    st.header("⚙️ การตั้งค่า")
    summary_style = st.selectbox(
        "สไตล์การสรุปเนื้อหา:",
        [
            "สรุปบทเรียนคณิตศาสตร์ (เน้นสูตร + วิธีทำ + นิยามสำคัญ)",
            "สรุปกระชับ สั้น ไว (เน้นจุดออกสอบบ่อย)",
            "สรุปละเอียด ครบถ้วน (แบ่งหัวข้อย่อยชัดเจน)",
            "สรุปแบบภาษาพูด เข้าใจง่าย"
        ]
    )

# แท็บเลือกรูปแบบไฟล์อินพุต
tab_text, tab_pdf, tab_img = st.tabs(["📝 ข้อความ", "📄 ไฟล์ PDF", "🖼️ รูปภาพหน้าหนังสือ"])

prompt_instruction = f"กรุณาช่วยสรุปเนื้อหาดังต่อไปนี้ โดยใช้สไตล์: {summary_style}"

# --- TAB 1: ข้อความ ---
with tab_text:
    user_text = st.text_area("วางเนื้อหาที่นี่:", height=200, placeholder="เช่น บทเรียนเรื่อง แคลคูลัส เบื้องต้น...")
    if st.button("🚀 เริ่มสรุปเนื้อหา", key="btn_text"):
        if not user_text.strip():
            st.warning("กรุณากรอกข้อความก่อนกดเริ่มสรุป")
        else:
            with st.spinner("กำลังประมวลผลสรุปเนื้อหา... (อาจใช้เวลาสักครู่)"):
                try:
                    full_prompt = [prompt_instruction, user_text]
                    result = generate_content_with_retry(
                        client=client,
                        model='gemini-3.6-flash',
                        contents=full_prompt
                    )
                    st.success("✨ สรุปเนื้อหาเรียบร้อยแล้ว!")
                    st.markdown(result)
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")

# --- TAB 2: ไฟล์ PDF ---
with tab_pdf:
    uploaded_pdf = st.file_uploader("อัปโหลดไฟล์ PDF บทเรียน:", type=["pdf"])
    if st.button("🚀 เริ่มสรุปจาก PDF", key="btn_pdf"):
        if uploaded_pdf is None:
            st.warning("กรุณาอัปโหลดไฟล์ PDF ก่อน")
        else:
            with st.spinner("กำลังอ่านและสรุปเนื้อหาจาก PDF..."):
                try:
                    pdf_reader = pypdf.PdfReader(uploaded_pdf)
                    extracted_text = ""
                    for page in pdf_reader.pages:
                        extracted_text += page.extract_text() or ""
                    
                    if not extracted_text.strip():
                        st.error("ไม่สามารถอ่านข้อความจาก PDF นี้ได้ (อาจเป็นไฟล์สแกนแบบภาพ)")
                    else:
                        full_prompt = [prompt_instruction, extracted_text]
                        result = generate_content_with_retry(
                            client=client,
                            model='gemini-3.6-flash',
                            contents=full_prompt
                        )
                        st.success("✨ สรุปเนื้อหาจาก PDF เรียบร้อยแล้ว!")
                        st.markdown(result)
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์ PDF: {e}")

# --- TAB 3: รูปภาพหน้าหนังสือ ---
with tab_img:
    uploaded_img = st.file_uploader("อัปโหลดรูปภาพหน้าหนังสือ:", type=["png", "jpg", "jpeg"])
    if uploaded_img:
        st.image(uploaded_img, caption="รูปภาพที่อัปโหลด", use_column_width=True)
        
    if st.button("🚀 เริ่มสรุปจากรูปภาพ", key="btn_img"):
        if uploaded_img is None:
            st.warning("กรุณาอัปโหลดรูปภาพก่อน")
        else:
            with st.spinner("กำลังวิเคราะห์รูปภาพและสรุปเนื้อหา..."):
                try:
                    image = Image.open(uploaded_img)
                    full_prompt = [prompt_instruction, image]
                    result = generate_content_with_retry(
                        client=client,
                        model='gemini-3.6-flash',
                        contents=full_prompt
                    )
                    st.success("✨ สรุปเนื้อหาจากรูปภาพเรียบร้อยแล้ว!")
                    st.markdown(result)
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการวิเคราะห์รูปภาพ: {e}")