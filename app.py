import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import pypdf
import os
import streamlit as st
from dotenv import load_dotenv
from google import genai

# โหลด API Key จากไฟล์ .env อัตโนมัติ
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# เรียกใช้งาน Client ด้วย Key จาก .env
client = genai.Client(api_key=api_key)

# 1. ตั้งค่าหน้าตาเว็บไซต์
st.set_page_config(page_title=" สรุปบทเรียน & หนังสือ", page_icon="📚", layout="wide")

st.title("📚 สรุปบทเรียน & เนื้อหาหนังสือ")
st.caption("วางข้อความ, อัปโหลดไฟล์ PDF หรืออัปโหลดรูปภาพหน้าหนังสือ เพื่อให้ AI สรุปเนื้อหาและสูตรสำคัญให้อัตโนมัติ")

# 2. แถบข้าง (Sidebar) สำหรับกรอก API Key และเลือกโหมดการสรุป
with st.sidebar:
    st.header("⚙️ การตั้งค่า")
   
    
    summary_style = st.selectbox(
        "สไตล์การสรุปเนื้อหา:",
        ["สรุปบทเรียนคณิตศาสตร์ (เน้นสูตร + นิยาม + ตัวอย่าง)", 
         "สรุปทั่วไป (เน้นประเด็นสำคัญ + ข้อสรุป)",
         "สรุปแบบข้อสอบ (สร้างคำถาม-ตอบ เพื่อทบทวน)"]
    )
    

# Function สำหรับสร้าง Prompt ตามโหมดที่เลือก
def get_system_prompt(style_option):
    if "คณิตศาสตร์" in style_option:
        return """
        คุณคือผู้เชี่ยวชาญด้านการสอนและสรุปวิชาคณิตศาสตร์ 
        ช่วยสรุปเนื้อหาที่ได้รับให้อ่านเข้าใจง่ายสำหรับนักเรียน โดยจัดโครงสร้างดังนี้:
        1. 🎯 **หัวใจสำคัญ / แนวคิดหลัก (Core Concept)**
        2. 📐 **สูตร นิยาม และทฤษฎีบทที่ต้องจำ** (เขียนสูตรให้ชัดเจน)
        3. 💡 **เทคนิคหรือจุดที่มักจะโดนหลอก/ข้อควรระวัง**
        4. 📝 **ตัวอย่างการนำไปใช้หรือตัวอย่างโจทย์แบบย่อ**
        """
    elif "ข้อสอบ" in style_option:
        return """
        คุณคือติวเตอร์เตรียมสอบ ช่วยสรุปเนื้อหานี้ให้ออกมาในรูปแบบ Flashcards / Q&A ทบทวนความจำ:
        - สรุปประเด็นหลัก 3-5 ข้อ
        - สร้าง Q&A (คำถาม - คำตอบ) จากเนื้อหา 5 ข้อ สำหรับทดสอบตัวเอง
        """
    else:
        return """
        คุณคือผู้เชี่ยวชาญด้านการสรุปความ สรุปเนื้อหาให้อ่านง่าย กระชับ แบ่งเป็นหัวข้อหลัก หัวข้อย่อย และ Highlight สาระสำคัญ
        """

# 3. ส่วนรับ Input จากผู้ใช้ (เลือกได้ 3 แบบ)
tab1, tab2, tab3 = st.tabs(["📝 ข้อความ", "📄 ไฟล์ PDF", "🖼️ รูปภาพหน้าหนังสือ"])

input_text = ""
input_image = None

with tab1:
    input_text = st.text_area("วางเนื้อหาที่นี่:", height=250, placeholder="เช่น บทเรียนเรื่อง แคลคูลัส เบื้องต้น...")

with tab2:
    uploaded_pdf = st.file_uploader("อัปโหลดไฟล์ PDF:", type=["pdf"])
    if uploaded_pdf:
        pdf_reader = pypdf.PdfReader(uploaded_pdf)
        pdf_text = ""
        for page in pdf_reader.pages:
            pdf_text += page.extract_text() or ""
        input_text = pdf_text
        st.info(f"ดึงข้อความจาก PDF เรียบร้อยแล้ว (ความยาวประมาณ {len(input_text)} ตัวอักษร)")

with tab3:
    uploaded_image = st.file_uploader("อัปโหลดรูปภาพหน้าหนังสือ:", type=["jpg", "jpeg", "png"])
    if uploaded_image:
        input_image = Image.open(uploaded_image)
        st.image(input_image, caption="รูปภาพที่อัปโหลด", use_column_width=True)

# 4. ปุ่มประมวลผลสรุปเนื้อหา
if st.button("🚀 เริ่มสรุปเนื้อหา", type="primary"):
    if not api_key:
        st.error("⚠️ กรุณากรอก Gemini API Key ในแถบด้านข้างซ้ายมือครับ")
    elif not input_text and not input_image:
        st.warning("⚠️ กรุณาป้อนข้อความ อัปโหลด PDF หรืออัปโหลดรูปภาพอย่างใดอย่างหนึ่งก่อนครับ")
    else:
        with st.spinner("🧠 AI กำลังอ่านและสรุปเนื้อหา..."):
            try:
                # เชื่อมต่อกับ Gemini API
                client = genai.Client(api_key=api_key)
                
                system_instruction = get_system_prompt(summary_style)
                
                # เตรียมข้อมูลส่งให้ Gemini 2.5 Flash
                contents = []
                if input_image:
                    contents.append(input_image)
                    contents.append("ช่วยอ่านเนื้อหาคณิตศาสตร์/บทเรียนในภาพนี้ แล้วสรุปตามโครงสร้างที่กำหนด")
                else:
                    contents.append(f"เนื้อหาที่ต้องการให้สรุป:\n\n{input_text}")

                # เรียกใช้งานโมเดล
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.3 # ตั้งค่าอุณหภูมิต่ำเพื่อให้สรุปได้ตรงฉบับจริง ไม่มโนเพิ่ม
                    )
                )

                # แสดงผลลัพธ์
                st.success("✨ สรุปเนื้อหาเรียบร้อยแล้ว!")
                st.markdown("---")
                st.markdown(response.text)

            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")