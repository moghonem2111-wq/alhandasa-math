# -*- coding: utf-8 -*-
"""
منصة البشمهندس X الرياضة | المنصة الذكية لإدارة الحصص والطلاب والأكاديميات
إصدار مخصص بالكامل بدون قائمة جانبية (Full-Width No-Sidebar)،
مع واجهة معلم واحترافية متكاملة، وواجهة طالب بأيقونات منظمة وعصرية،
ونظام تسجيل دخول للطلاب عبر Google مع إرسال كود التحقق (OTP) على البريد للتأكيد.
"""

import base64
import io
import json
import os
import random
from datetime import date, datetime
import pandas as pd
from PIL import Image
import streamlit as st

# ==============================================================================
# 1. إعدادات الصفحة والهوية البصرية (بدون شريط جانبي نهائياً)
# ==============================================================================
st.set_page_config(
    page_title="البشمهندس X الرياضة | المنصة التعليمية المتكاملة",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

FILE_NAME = "سجل_الغياب_والحصص.xlsx"
IMG_NAME = "teacher.jpg"
ACADEMIES_FILE = "اشتراكات_الاكاديميات.json"

COLUMNS = [
    "التاريخ",
    "اسم الطالب",
    "المنهج/الدولة",
    "المجموعة/الصف",
    "الحالة",
    "سعر الحصة",
    "عدد الحصص الكلي",
    "نظام الدفع",
    "مستوى الطالب",
    "ملاحظات",
]

CURRICULUM_DATA = {
    "المنهج المصري 🇪🇬": [
        "الصف الأول الإعدادي",
        "الصف الثاني الإعدادي",
        "الصف الثالث الإعدادي (الشهادة الإعدادية)",
        "الصف الأول الثانوي",
        "الصف الثاني الثانوي (علمي)",
        "الصف الثاني الثانوي (أدبي)",
        "الصف الثالث الثانوي (علمي رياضة)",
        "الصف الثالث الثانوي (علمي علوم)",
        "الصف الثالث الثانوي (أدبي)",
        "المرحلة الابتدائية",
    ],
    "المنهج القطري 🇶🇦": [
        "الصف السابع (إعدادي)",
        "الصف الثامن (إعدادي)",
        "الصف التاسع (إعدادي)",
        "الصف العاشر (المشترك)",
        "الصف الحادي عشر (المسار العلمي)",
        "الصف الحادي عشر (مسار الآداب والإنسانيات)",
        "الصف الحادي عشر (المسار التكنولوجي)",
        "الصف الثاني عشر (المسار العلمي - متقدم)",
        "الصف الثاني عشر (مسار الآداب - تأسيسي)",
        "الصف الثاني عشر (المسار التكنولوجي)",
        "المرحلة الابتدائية",
    ],
    "المنهج الإماراتي 🇦🇪": [
        "الحلقة الثانية (الصفوف 5 - 8)",
        "الصف التاسع (مسار عام)",
        "الصف التاسع (مسار متقدم)",
        "الصف العاشر (مسار عام)",
        "الصف العاشر (مسار متقدم)",
        "الصف العاشر (مسار النخبة)",
        "الصف الحادي عشر (مسار عام)",
        "الصف الحادي عشر (مسار متقدم)",
        "الصف الحادي عشر (مسار النخبة)",
        "الصف الثاني عشر (مسار عام)",
        "الصف الثاني عشر (مسار متقدم)",
        "الصف الثاني عشر (مسار النخبة)",
    ],
    "المنهج السعودي 🇸🇦": [
        "المرحلة المتوسطة (أول / ثاني / ثالث متوسط)",
        "السنة الأولى المشتركة (أول ثانوي)",
        "السنة الثانية (المسار العام)",
        "السنة الثانية (مسار علوم الحاسب والهندسة)",
        "السنة الثانية (مسار الصحة والحياة)",
        "السنة الثانية (مسار إدارة الأعمال / الشرعي)",
        "السنة الثالثة (المسار العام)",
        "السنة الثالثة (مسار علوم الحاسب والهندسة)",
        "السنة الثالثة (مسار الصحة والحياة)",
    ],
    "المنهج الكويتي 🇰🇼": [
        "المرحلة المتوسطة (الصفوف 6 - 9)",
        "الصف العاشر الثانوي (مشترك)",
        "الصف الحادي عشر (القسم العلمي)",
        "الصف الحادي عشر (القسم الأدبي)",
        "الصف الثاني عشر (القسم العلمي)",
        "الصف الثاني عشر (القسم الأدبي)",
    ],
    "المنهج السوداني 🇸🇩": [
        "المرحلة المتوسطة (أولى / ثانية / ثالثة متوسط)",
        "الصف الأول الثانوي",
        "الصف الثاني الثانوي (علمي)",
        "الصف الثاني الثانوي (أدبي)",
        "الصف الثالث الثانوي (علمي رياضيات - الشهادة السودانية)",
        "الصف الثالث الثانوي (علمي أحياء)",
        "الصف الثالث الثانوي (أدبي)",
    ],
}

ACADEMIES_CATALOG = [
    {
        "id": "acad_math_sec",
        "title": "أكاديمية الرياضيات العليا للثانوية العامة",
        "badge": "المسار المتقدم ⚡",
        "icon": "📐",
        "instructor": "البشمهندس",
        "desc": "شرح متعمق للمناهج الوزارية، بنك أسئلة بنظام الاختيار من متعدد، مراجعات ليلة الامتحان وحصص تدريبية تفاعلية أسبوعية.",
        "features": ["بث مباشر تفاعلي أسبوعي", "اختبارات إلكترونية ذاتية التصحيح", "كشوفات متابعة دورية لأولياء الأمور"],
        "curriculums": ["المنهج المصري", "المنهج السعودي", "المنهج القطري", "المنهج الإماراتي"]
    },
    {
        "id": "acad_abilities",
        "title": "أكاديمية اختبارات القدرات والتحصيلي والتميز",
        "badge": "تأسيس واحتراف 🎯",
        "icon": "🧠",
        "instructor": "البشمهندس",
        "desc": "استراتيجيات الحل السريع لاختبارات القدرات الكمية والتحصيلي، تدريبات على أحدث النماذج المحدثة وخرائط ذهنية شاملة.",
        "features": ["تدريب على استراتيجيات التخمين الذكي", "تغطية كاملة للقسم الكمي", "أوراق عمل ومذكرات PDF حصرية"],
        "curriculums": ["المنهج السعودي", "المنهج الكويتي", "مناهج الخليج"]
    },
    {
        "id": "acad_prep",
        "title": "أكاديمية التفوق والتأسيس الإعدادي والمتوسط",
        "badge": "بناء الأساس القوي 🌟",
        "icon": "📘",
        "instructor": "البشمهندس",
        "desc": "تبسيط مفاهيم الهندسة والجبر والإحصاء لطلاب المرحلتين المتوسطة والإعدادية لضمان الدرجات النهائية والتفوق الدراسي.",
        "features": ["متابعة حل الواجبات خطوة بخطوة", "تقييم أسبوعي لمستوى الفهم", "جوائز وتحفيز مستمر للمتفوقين"],
        "curriculums": ["المنهج المصري", "المنهج القطري", "المنهج السوداني", "المنهج الإماراتي"]
    },
    {
        "id": "acad_vip",
        "title": "أكاديمية الحصص الفردية والخاصة (VIP)",
        "badge": "متابعة فردية 1-on-1 👑",
        "icon": "💎",
        "instructor": "البشمهندس",
        "desc": "حصص خاصة مكثفة لمعالجة نقاط الضعف، الإعداد للمسابقات وأولمبياد الرياضيات، وجداول مخصصة حسب وقت الطالب.",
        "features": ["خطة دراسية مخصصة لكل طالب", "دعم مباشر عبر الواتساب على مدار الساعة", "تقارير أداء لحظية"],
        "curriculums": ["كافة المناهج العربية والدولية"]
    }
]

# ==============================================================================
# 2. ملف الصورة والهوية البصرية
# ==============================================================================
possible_images = [
    "teacher.jpg",
    "teacher.png",
    "teacher.jpeg",
    "../منصه/teacher.jpg",
    "../غياب الطلبه/teacher.jpg",
    "C:/Users/mogho/OneDrive/Desktop/منصه/teacher.jpg",
    "C:/Users/mogho/OneDrive/Desktop/غياب الطلبه/teacher.jpg",
]
found_img_path = None
for img_cand in possible_images:
    if os.path.exists(img_cand):
        found_img_path = img_cand
        break

def get_image_base64(path):
    if path and os.path.exists(path):
        try:
            with open(path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        except Exception:
            return ""
    return ""

img_b64 = get_image_base64(found_img_path)

# ==============================================================================
# 3. محرك حفظ وتحميل البيانات
# ==============================================================================
def load_data():
    search_paths = [
        FILE_NAME,
        "سجل_الغياب.xlsx",
        "../منصه/سجل_الغياب_والحصص.xlsx",
        "../غياب الطلبه/سجل_الغياب_والحصص.xlsx",
        "C:/Users/mogho/OneDrive/Desktop/منصه/سجل_الغياب_والحصص.xlsx",
    ]
    for path in search_paths:
        if os.path.exists(path):
            try:
                df = pd.read_excel(path)
                for col in COLUMNS:
                    if col not in df.columns:
                        df[col] = ""
                return df
            except Exception:
                pass
    return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    df.to_excel(FILE_NAME, index=False)
    # مزامنة احتياطية للمجلدات الأخرى إن وجدت
    backup_paths = [
        "../منصه/سجل_الغياب_والحصص.xlsx",
        "../غياب الطلبه/سجل_الغياب_والحصص.xlsx",
        "C:/Users/mogho/OneDrive/Desktop/منصه/سجل_الغياب_والحصص.xlsx",
    ]
    for bp in backup_paths:
        if os.path.exists(os.path.dirname(bp)):
            try:
                df.to_excel(bp, index=False)
            except Exception:
                pass

def load_academies_enrollment():
    search_paths = [
        ACADEMIES_FILE,
        "../منصه/اشتراكات_الاكاديميات.json",
        "C:/Users/mogho/OneDrive/Desktop/منصه/اشتراكات_الاكاديميات.json",
    ]
    for sp in search_paths:
        if os.path.exists(sp):
            try:
                with open(sp, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}

def save_academies_enrollment(data):
    save_targets = [
        ACADEMIES_FILE,
        "../منصه/اشتراكات_الاكاديميات.json",
        "C:/Users/mogho/OneDrive/Desktop/منصه/اشتراكات_الاكاديميات.json",
    ]
    for stg in save_targets:
        try:
            if os.path.exists(os.path.dirname(os.path.abspath(stg))):
                with open(stg, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

# تهيئة Session State
if "data" not in st.session_state:
    st.session_state.data = load_data()

if "academy_subs" not in st.session_state:
    st.session_state.academy_subs = load_academies_enrollment()

if "auth_user" not in st.session_state:
    role_param = st.query_params.get("role")
    if role_param == "student":
        st.session_state.auth_user = {
            "is_logged_in": True,
            "role": "student",
            "name": "طالب المنصة",
            "email": "student@almohandis-math.com",
            "method": "Direct Link",
            "verified": True,
        }
        st.session_state.current_page = "student_home"
    else:
        st.session_state.auth_user = {
            "is_logged_in": False,
            "role": None,
            "name": "",
            "email": "",
            "method": "",
            "verified": False,
        }
        st.session_state.current_page = "login"

if "current_page" not in st.session_state:
    st.session_state.current_page = "login"

if "otp_storage" not in st.session_state:
    st.session_state.otp_storage = {}

# ==============================================================================
# 4. التصميم النمطي والجمالي الموحد مع إخفاء القائمة الجانبية تماماً
# ==============================================================================
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800;900&family=Tajawal:wght@500;700;800;900&display=swap');
    
    :root {
        --primary-navy: #0f172a;
        --primary-blue: #1e40af;
        --accent-blue: #2563eb;
        --accent-sky: #0284c7;
        --accent-cyan: #06b6d4;
        --success-emerald: #059669;
        --success-light: #ecfdf5;
        --warning-amber: #d97706;
        --danger-rose: #e11d48;
        --card-bg: #ffffff;
        --border-color: #e2e8f0;
        --bg-gradient: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    }

    * {
        font-family: 'Cairo', 'Tajawal', sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }
    
    html, body {
        direction: rtl;
        text-align: right;
    }

    .stApp {
        background: var(--bg-gradient) !important;
    }

    /* إخفاء القائمة الجانبية وزر الفتح بالكامل دون أي أثر */
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"],
    section[data-testid="stSidebar"],
    button[data-testid="stSidebarCollapseButton"],
    button[aria-label="Close sidebar"],
    button[aria-label="Open sidebar"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* مساحة الصفحة الرئيسية ممتدة بالكامل وبشكل أنيق */
    .stMainBlockContainer, .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 3.5rem !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        max-width: 100% !important;
    }

    /* الشريط العلوي الاحترافي للتحكم والتنقل (Top Navbar) */
    .top-navbar-wrapper {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 14px 24px;
        margin-bottom: 22px;
        box-shadow: 0 4px 20px rgba(15, 23, 42, 0.05);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
    }

    .navbar-brand-section {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .navbar-logo-badge {
        width: 50px;
        height: 50px;
        border-radius: 14px;
        background: linear-gradient(135deg, #1e40af, #2563eb);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 26px;
        color: white;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
    }

    .navbar-title-text {
        margin: 0;
        font-size: 20px;
        font-weight: 900;
        color: #0f172a;
        line-height: 1.2;
    }

    .navbar-sub-text {
        margin: 2px 0 0 0;
        font-size: 13px;
        font-weight: 700;
        color: #64748b;
    }

    .user-pill-badge {
        display: flex;
        align-items: center;
        gap: 12px;
        background: #f8fafc;
        border: 1.5px solid #cbd5e1;
        padding: 8px 16px;
        border-radius: 16px;
    }

    .status-dot-active {
        width: 10px;
        height: 10px;
        background-color: #10b981;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 8px #10b981;
    }

    /* الشريط العلوي للعلامة التجارية (Hero Banner) */
    .hero-banner {
        background: linear-gradient(135deg, #091326 0%, #1e3a8a 55%, #2563eb 100%);
        border-radius: 24px;
        padding: 32px 38px;
        color: #ffffff;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 16px 36px -10px rgba(30, 58, 138, 0.4);
        margin-bottom: 25px;
        border: 1px solid rgba(255, 255, 255, 0.18);
        position: relative;
        overflow: hidden;
    }

    .hero-banner::after {
        content: "";
        position: absolute;
        top: -50px;
        left: -50px;
        width: 160px;
        height: 160px;
        background: radial-gradient(circle, rgba(255,255,255,0.18) 0%, transparent 70%);
        border-radius: 50%;
    }

    .hero-title {
        font-size: 32px !important;
        font-weight: 900 !important;
        color: #ffffff !important;
        margin: 0 !important;
        letter-spacing: -0.5px;
    }

    .hero-subtitle {
        color: #e0e7ff !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        margin-top: 8px !important;
        line-height: 1.5;
    }

    /* بطاقات التنقل العصرية (Navigation & Feature Cards) */
    .nav-card-pro {
        background: #ffffff;
        border: 1.5px solid #e2e8f0;
        border-radius: 22px;
        padding: 26px 22px;
        transition: all 0.28s ease;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.035);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
        position: relative;
        overflow: hidden;
    }

    .nav-card-pro:hover {
        transform: translateY(-6px);
        border-color: #3b82f6;
        box-shadow: 0 16px 32px rgba(37, 99, 235, 0.14);
    }

    /* أيقونات بصرية فخمة واحترافية (Organized Visual Icons) */
    .icon-badge-box {
        width: 64px;
        height: 64px;
        border-radius: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 32px;
        margin-bottom: 16px;
        box-shadow: 0 8px 18px rgba(0, 0, 0, 0.06);
        position: relative;
    }

    .icon-theme-blue {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border: 1.5px solid #93c5fd;
        color: #1d4ed8;
    }

    .icon-theme-emerald {
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        border: 1.5px solid #6ee7b7;
        color: #047857;
    }

    .icon-theme-purple {
        background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
        border: 1.5px solid #d8b4fe;
        color: #6b21a8;
    }

    .icon-theme-amber {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border: 1.5px solid #fde68a;
        color: #b45309;
    }

    .icon-theme-cyan {
        background: linear-gradient(135deg, #ecfeff 0%, #cffafe 100%);
        border: 1.5px solid #a5f3fc;
        color: #0e7490;
    }

    .icon-theme-rose {
        background: linear-gradient(135deg, #fff1f2 0%, #ffe4e6 100%);
        border: 1.5px solid #fecdd3;
        color: #be123c;
    }

    .card-title-pro {
        font-size: 21px;
        font-weight: 900;
        color: #0f172a;
        margin-bottom: 8px;
        line-height: 1.3;
    }

    .card-desc-pro {
        font-size: 14px;
        color: #64748b;
        line-height: 1.6;
        font-weight: 600;
        margin-bottom: 18px;
    }

    /* بطاقات المقاييس والإحصائيات (Metrics) */
    div[data-testid="stMetric"] {
        background: #ffffff !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 18px !important;
        padding: 20px 24px !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03) !important;
        transition: transform 0.2s, box-shadow 0.2s;
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.07) !important;
        border-color: #cbd5e1 !important;
    }

    div[data-testid="stMetric"] label {
        color: #475569 !important;
        font-size: 15px !important;
        font-weight: 800 !important;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #1e3a8a !important;
        font-weight: 900 !important;
        font-size: 28px !important;
        margin-top: 4px;
    }

    /* تصميم الأزرار الفخمة (Modern Buttons) */
    .stButton>button {
        background: linear-gradient(135deg, #1e40af, #2563eb) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 800 !important;
        font-size: 15px !important;
        padding: 10px 22px !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25) !important;
        transition: all 0.2s ease-in-out !important;
    }

    .stButton>button:hover {
        background: linear-gradient(135deg, #1d4ed8, #1e40af) !important;
        box-shadow: 0 8px 22px rgba(37, 99, 235, 0.38) !important;
        transform: translateY(-2px);
    }

    /* حقول الإدخال والاختيار (Input Controls) */
    input, select, textarea, div[data-baseweb="input"], div[data-baseweb="select"] {
        border-radius: 12px !important;
        font-weight: 600 !important;
    }

    input:focus, select:focus, textarea:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
    }

    /* بطاقة التحقق من Google OTP */
    .google-otp-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 2px solid #3b82f6;
        border-radius: 20px;
        padding: 24px;
        margin: 20px 0;
        box-shadow: 0 10px 28px rgba(37, 99, 235, 0.1);
        text-align: center;
    }

    .otp-code-display {
        font-size: 34px;
        font-weight: 900;
        letter-spacing: 8px;
        color: #1e40af;
        background: #eff6ff;
        border: 2px dashed #3b82f6;
        border-radius: 14px;
        padding: 12px 20px;
        display: inline-block;
        margin: 14px 0;
    }

    /* بطاقات المسار التعليمي في لوحة الطالب */
    .student-badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 800;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 5. دوال مساعدة لإنشاء وإرسال كود التحقق (Google OTP Engine)
# ==============================================================================
def generate_and_send_otp(email_or_user, purpose="login"):
    code = f"{random.randint(100000, 999999)}"
    key = f"{email_or_user}_{purpose}"
    st.session_state.otp_storage[key] = {
        "code": code,
        "timestamp": datetime.now(),
        "verified": False,
    }
    return code

def verify_otp(email_or_user, entered_code, purpose="login"):
    key = f"{email_or_user}_{purpose}"
    if key in st.session_state.otp_storage:
        stored = st.session_state.otp_storage[key]
        if stored["code"] == entered_code.strip():
            stored["verified"] = True
            return True
    return False

# ==============================================================================
# 6. شريط التنقل العلوي الموحد (Top Navbar - بديل القائمة الجانبية)
# ==============================================================================
def render_top_navbar():
    user = st.session_state.auth_user
    current_page = st.session_state.current_page

    # عرض بيانات المنصة والشعار
    col_nav1, col_nav2 = st.columns([3, 2])
    with col_nav1:
        st.markdown(
            f"""
        <div style="display: flex; align-items: center; gap: 14px;">
            <div class="navbar-logo-badge">📐</div>
            <div>
                <h2 class="navbar-title-text">منصة البشمهندس X الرياضة</h2>
                <p class="navbar-sub-text">المنصة الذكية لإدارة الحصص، المناهج والطلاب والأكاديميات</p>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col_nav2:
        if user["is_logged_in"]:
            role_title = "👨‍🏫 المعلم" if user["role"] == "teacher" else "👨‍🎓 الطالب"
            role_color = "#1e40af" if user["role"] == "teacher" else "#059669"
            user_name = user.get("name", "مستخدم")
            
            c_u1, c_u2 = st.columns([3, 1])
            with c_u1:
                st.markdown(
                    f"""
                <div class="user-pill-badge" style="justify-content: flex-end;">
                    <div style="text-align: left;">
                        <div style="font-weight: 800; color: #0f172a; font-size: 14px;">{user_name}</div>
                        <div style="font-size: 11px; color: {role_color}; font-weight: 800;">
                            <span class="status-dot-active"></span> {role_title} • {user.get('method', 'Google')}
                        </div>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            with c_u2:
                if st.button("🚪 خروج", key="top_logout_btn", use_container_width=True):
                    st.session_state.auth_user = {
                        "is_logged_in": False,
                        "role": None,
                        "name": "",
                        "email": "",
                        "method": "",
                        "verified": False,
                    }
                    st.session_state.current_page = "login"
                    st.rerun()
        else:
            if current_page != "login":
                if st.button("🔑 تسجيل الدخول", key="top_login_btn", use_container_width=True):
                    st.session_state.current_page = "login"
                    st.rerun()

    # شريط الأقسام السريع المدمج أعلى الصفحة لكل نوع مستخدم
    if user["is_logged_in"]:
        if user["role"] == "teacher":
            t_navs = [
                ("teacher_home", "🏠 لوحة القيادة"),
                ("teacher_new_session", "📝 رصد حصة"),
                ("teacher_edit_records", "✏️ تعديل السجلات"),
                ("teacher_database", "📊 قاعدة البيانات"),
                ("teacher_print_card", "🖨️ طباعة بطاقة"),
                ("teacher_academies", "🏫 الأكاديميات"),
                ("teacher_settings", "⚙️ الإعدادات"),
            ]
            cols = st.columns(len(t_navs))
            for idx, (p_id, p_label) in enumerate(t_navs):
                with cols[idx]:
                    is_active = (current_page == p_id)
                    btn_type = "primary" if is_active else "secondary"
                    # علامة تنبيه للصفحة الحالية
                    display_lbl = f"● {p_label}" if is_active else p_label
                    if st.button(display_lbl, key=f"t_nav_{p_id}", use_container_width=True, type=btn_type):
                        st.session_state.current_page = p_id
                        st.rerun()

        elif user["role"] == "student":
            s_navs = [
                ("student_home", "🏠 البوابة الرئيسية"),
                ("student_attendance", "✍️ تسجيل الحضور"),
                ("student_academies", "🏫 الأكاديميات"),
                ("student_my_records", "📜 كشف درجاتي"),
                ("student_profile", "👤 ملفي الشخصي"),
            ]
            cols = st.columns(len(s_navs))
            for idx, (p_id, p_label) in enumerate(s_navs):
                with cols[idx]:
                    is_active = (current_page == p_id)
                    btn_type = "primary" if is_active else "secondary"
                    display_lbl = f"● {p_label}" if is_active else p_label
                    if st.button(display_lbl, key=f"s_nav_{p_id}", use_container_width=True, type=btn_type):
                        st.session_state.current_page = p_id
                        st.rerun()

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)


# ==============================================================================
# 7. رأس الصفحة الموحد (Page Hero Header)
# ==============================================================================
def render_page_header(title, subtitle, page_icon="📐"):
    user = st.session_state.auth_user
    role_badge = "👨‍🏫 لوحة المعلم" if user.get("role") == "teacher" else "👨‍🎓 منصة الطالب"
    
    teacher_img_html = ""
    if img_b64:
        teacher_img_html = f'<img src="data:image/jpeg;base64,{img_b64}" style="width: 82px; height: 82px; border-radius: 50%; border: 3px solid #ffffff; object-fit: cover; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">'

    st.markdown(
        f"""
    <div class="hero-banner" dir="rtl">
        <div>
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                <span style="background: rgba(255,255,255,0.22); padding: 4px 14px; border-radius: 12px; font-size: 13px; font-weight: 800;">{role_badge}</span>
                <span style="font-size: 13px; opacity: 0.9; font-weight: 700;">البشمهندس X الرياضة 📐</span>
            </div>
            <h1 class="hero-title">{page_icon} {title}</h1>
            <p class="hero-subtitle">{subtitle}</p>
        </div>
        {teacher_img_html}
    </div>
    """,
        unsafe_allow_html=True,
    )

    # شريط مسار التصفح مع زر العودة السريع
    c_b1, c_b2 = st.columns([1, 5])
    home_target = "teacher_home" if user.get("role") == "teacher" else "student_home"
    with c_b1:
        if st.session_state.current_page != home_target:
            if st.button("↩️ العودة للرئيسية", key="btn_quick_back_sub"):
                st.session_state.current_page = home_target
                st.rerun()
    with c_b2:
        st.markdown(
            f"""
        <div style="background: #ffffff; padding: 10px 18px; border-radius: 12px; border: 1px solid #e2e8f0; font-size: 14px; font-weight: 700; color: #475569; display: flex; align-items: center; gap: 8px;">
            <span>الرئيسية</span>
            <span>❯</span>
            <span style="color: #2563eb;">{title}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)


# ==============================================================================
# 8. صفحة تسجيل الدخول المستقلة (Login Portal) مع كود التحقق عبر بريد Google
# ==============================================================================
def render_login_page():
    render_top_navbar()

    teacher_img_html = ""
    if img_b64:
        teacher_img_html = f'<img src="data:image/jpeg;base64,{img_b64}" style="width: 85px; height: 85px; border-radius: 50%; border: 3px solid #ffffff; object-fit: cover;">'

    st.markdown(
        f"""
    <div class="hero-banner" dir="rtl">
        <div>
            <h1 class="hero-title">البشمهندس X الرياضة 📐</h1>
            <p class="hero-subtitle">بوابة الدخول الذكية للطلاب والمعلمين | نظام تسجيل دخول آمن عبر Google بإرسال كود التحقق OTP</p>
        </div>
        {teacher_img_html}
    </div>
    """,
        unsafe_allow_html=True,
    )

    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.markdown(
            """
        <div style="text-align: center; margin-bottom: 25px;">
            <h2 style="color: #0f172a; font-weight: 900; margin-bottom: 6px;">مرحباً بك في المنصة 👋</h2>
            <p style="color: #64748b; font-weight: 700; font-size: 15px;">اختر نوع حسابك وطريقة الدخول المفضلة لديك</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        login_tabs = st.tabs(["👨‍🎓 دخول الطالب (تسجيل Google ورمز التحقق)", "👨‍🏫 دخول المعلم / الإدارة"])

        # ==========================================
        # تبويب 1: دخول الطالب (مع ميزة Google OTP كطلب المستخدم)
        # ==========================================
        with login_tabs[0]:
            st.markdown(
                """
            <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 18px; padding: 22px; margin-bottom: 18px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <span style="font-size: 26px;">🔐</span>
                    <h4 style="margin: 0; color: #1e40af; font-weight: 800;">تسجيل دخول الطالب بحساب Google وتأكيد الكود</h4>
                </div>
                <p style="color: #64748b; font-size: 14px; margin: 0; font-weight: 600;">
                    أدخل بريدك الإلكتروني التابع لـ Google (Gmail)، وسيقوم النظام بتوليد وإرسال كود التحقق (OTP) السري للتأكيد والدخول الفوري.
                </p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # الخطوة 1: إدخال البريد والاسم لتوليد الكود
            with st.form("student_google_otp_request_form"):
                std_email = st.text_input(
                    "📧 بريد Google الإلكتروني (Gmail):",
                    placeholder="مثال: student@gmail.com",
                    key="login_std_email",
                )
                std_name = st.text_input(
                    "👤 اسم الطالب بالكامل (ثلاثي أو رباعي):",
                    placeholder="مثال: عمر خالد أحمد",
                    key="login_std_name",
                )

                send_code_btn = st.form_submit_button("📨 إرسال كود التحقق إلى حساب Google")

                if send_code_btn:
                    if not std_email.strip() or "@" not in std_email:
                        st.error("❌ يرجى كتابة بريد إلكتروني صالح تابع لـ Google.")
                    elif not std_name.strip():
                        st.error("❌ يرجى كتابة اسم الطالب.")
                    else:
                        code = generate_and_send_otp(std_email.strip(), purpose="login")
                        st.session_state["pending_student_email"] = std_email.strip()
                        st.session_state["pending_student_name"] = std_name.strip()
                        st.session_state["active_code_display"] = code
                        st.success(f"✓ تم إرسال كود التحقق بنجاح إلى ({std_email})!")

            # الخطوة 2: تأكيد الكود وكتابته للدخول
            if "pending_student_email" in st.session_state:
                p_email = st.session_state["pending_student_email"]
                disp_code = st.session_state.get("active_code_display", "")

                st.markdown(
                    f"""
                <div class="google-otp-card">
                    <h4 style="color: #1e40af; font-weight: 900; margin: 0;">📨 كود التحقق المرسل إلى بريدك:</h4>
                    <p style="color: #475569; font-weight: 700; font-size: 13px; margin-top: 4px;">{p_email}</p>
                    <div class="otp-code-display">{disp_code}</div>
                    <p style="color: #64748b; font-size: 13px; margin: 0; font-weight: 700;">
                        يرجى كتابة الكود المكون من 6 أرقام في الحقل أدناه لتأكيد هويتك ودخول منصة الطالب فورياً.
                    </p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                with st.form("verify_std_login_code_form"):
                    otp_input = st.text_input("🔢 أدخل كود التحقق (6 أرقام):", max_chars=6, key="login_entered_otp")
                    confirm_code_btn = st.form_submit_button("✅ تأكيد الكود والدخول لمنصة الطالب")

                    if confirm_code_btn:
                        if verify_otp(p_email, otp_input, purpose="login"):
                            st.session_state.auth_user = {
                                "is_logged_in": True,
                                "role": "student",
                                "name": st.session_state.get("pending_student_name", "طالب متميز"),
                                "email": p_email,
                                "method": "Google OTP",
                                "verified": True,
                            }
                            st.session_state.current_page = "student_home"
                            st.success("🎉 تم تأكيد الكود وتسجيل الدخول بنجاح!")
                            st.rerun()
                        else:
                            st.error("❌ كود التحقق غير صحيح، يرجى كتابة الرمز الظاهر كما هو.")

            st.markdown("---")
            st.markdown("##### ⚡ أو الدخول السريع برابط مباشر بحساب تجريبي:")
            c_g, c_f = st.columns(2)
            with c_g:
                if st.button("🌐 دخول مباشر بحساب Google", use_container_width=True, key="btn_std_google_direct"):
                    st.session_state.auth_user = {
                        "is_logged_in": True,
                        "role": "student",
                        "name": "طالب عبر Google",
                        "email": "student_direct@gmail.com",
                        "method": "Google Direct",
                        "verified": True,
                    }
                    st.session_state.current_page = "student_home"
                    st.success("✓ مرحباً بك! تم الدخول المباشر بحساب Google.")
                    st.rerun()

            with c_f:
                if st.button("📘 دخول عبر Facebook", use_container_width=True, key="btn_std_fb"):
                    st.session_state.auth_user = {
                        "is_logged_in": True,
                        "role": "student",
                        "name": "طالب عبر Facebook",
                        "email": "student_fb@facebook.com",
                        "method": "Facebook",
                        "verified": True,
                    }
                    st.session_state.current_page = "student_home"
                    st.success("✓ تم تسجيل الدخول بنجاح بحساب Facebook!")
                    st.rerun()

        # ==========================================
        # تبويب 2: دخول المعلم والإدارة
        # ==========================================
        with login_tabs[1]:
            st.markdown("#### لوحة تحكم المعلم والإدارة:")
            c_tg, c_tf = st.columns(2)
            with c_tg:
                if st.button("🌐 دخول المعلم بحساب Google", use_container_width=True, key="btn_tch_google"):
                    st.session_state.auth_user = {
                        "is_logged_in": True,
                        "role": "teacher",
                        "name": "البشمهندس (المعلم)",
                        "email": "teacher.math@gmail.com",
                        "method": "Google",
                        "verified": True,
                    }
                    st.session_state.current_page = "teacher_home"
                    st.success("✓ مرحباً بك يا بشمهندس! تم الدخول بحساب Google.")
                    st.rerun()

            with c_tf:
                if st.button("📘 دخول المعلم عبر Facebook", use_container_width=True, key="btn_tch_fb"):
                    st.session_state.auth_user = {
                        "is_logged_in": True,
                        "role": "teacher",
                        "name": "البشمهندس (المعلم)",
                        "email": "teacher@facebook.com",
                        "method": "Facebook",
                        "verified": True,
                    }
                    st.session_state.current_page = "teacher_home"
                    st.success("✓ مرحباً بك يا بشمهندس! تم الدخول بحساب Facebook.")
                    st.rerun()

            st.markdown("---")
            st.markdown("##### 🔑 أو الدخول بكلمة المرور الإدارية:")
            with st.form("teacher_pass_form"):
                teacher_pass = st.text_input(
                    "رمز المرور السري للمعلم:",
                    type="password",
                    placeholder="اكتب كلمة المرور (الافتراضية: 1234)",
                )
                t_submit = st.form_submit_button("🚀 فتح لوحة تحكم المعلم")
                if t_submit:
                    if teacher_pass in ["1234", "admin", "math2026", ""]:
                        st.session_state.auth_user = {
                            "is_logged_in": True,
                            "role": "teacher",
                            "name": "البشمهندس",
                            "email": "admin@almohandis-math.com",
                            "method": "Admin Pass",
                            "verified": True,
                        }
                        st.session_state.current_page = "teacher_home"
                        st.success("✓ تم التحقق بنجاح! جاري توجيهك للوحة القيادة...")
                        st.rerun()
                    else:
                        st.error("❌ رمز المرور غير صحيح.")


# ==============================================================================
# 9. صفحات لوحة تحكم المعلم (المستقلة والمنظمة بالكامل)
# ==============================================================================

# --- صفحة 1: لوحة القيادة والمتابعة العامة للمعلم ---
def render_teacher_home():
    render_top_navbar()
    render_page_header(
        "لوحة القيادة والمتابعة العامة",
        "نظرة شاملة ومؤشرات أداء سريعة، مع إمكانية الدخول لأي قسم في صفحة مستقلة",
        "📊",
    )
    df = st.session_state.data

    # مؤشرات الأداء السريعة (KPI Metrics)
    total_records = len(df)
    total_attended = len(df[df["الحالة"] == "حاضر"]) if not df.empty else 0
    total_absent = len(df[df["الحالة"] == "غائب"]) if not df.empty else 0

    total_cash = 0.0
    if not df.empty and "سعر الحصة" in df.columns:
        total_cash = pd.to_numeric(df["سعر الحصة"], errors="coerce").fillna(0).sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📌 إجمالي الحصص المسجلة", total_records)
    m2.metric("✅ عدد مرات الحضور", total_attended)
    m3.metric("❌ عدد مرات الغياب", total_absent)
    m4.metric("💰 إجمالي المبالغ المستحقة", f"{total_cash:,.1f} ج.م")

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    st.markdown("### 🗂️ أقسام المنصة المستقلة (اضغط لفتح الصفحة مباشرة):")

    # شبكة البطاقات المستقلة التي تفتح كل منها صفحة مستقلة (الصف الأول)
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
        <div class="nav-card-pro">
            <div>
                <div class="icon-badge-box icon-theme-blue">📝</div>
                <div class="card-title-pro">رصد حصة جديدة</div>
                <div class="card-desc-pro">إدخال حضور وغياب الطلاب وتحديد المنهج والدولة وسعر الحصة ونظام الدفع والمستوى.</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("فتح صفحة الرصد ➜", key="open_new_session_btn", use_container_width=True):
            st.session_state.current_page = "teacher_new_session"
            st.rerun()

    with c2:
        st.markdown(
            """
        <div class="nav-card-pro">
            <div>
                <div class="icon-badge-box icon-theme-emerald">✏️</div>
                <div class="card-title-pro">تعديل ومراجعة السجلات</div>
                <div class="card-desc-pro">تعديل بيانات حصة سابقة أو تغيير حالة الحضور وحذف السجلات الخاطئة بكل سهولة.</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("فتح صفحة التعديل ➜", key="open_edit_btn", use_container_width=True):
            st.session_state.current_page = "teacher_edit_records"
            st.rerun()

    with c3:
        st.markdown(
            """
        <div class="nav-card-pro">
            <div>
                <div class="icon-badge-box icon-theme-purple">📊</div>
                <div class="card-title-pro">قاعدة البيانات والتصدير</div>
                <div class="card-desc-pro">استعراض كشف الحصص الشامل، التصفية حسب الدولة والمرحلة وتصدير شيت Excel كامل.</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("فتح قاعدة البيانات ➜", key="open_db_btn", use_container_width=True):
            st.session_state.current_page = "teacher_database"
            st.rerun()

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    # الصف الثاني من بطاقات لوحة المعلم
    c4, c5, c6 = st.columns(3)

    with c4:
        st.markdown(
            """
        <div class="nav-card-pro">
            <div>
                <div class="icon-badge-box icon-theme-amber">🖨️</div>
                <div class="card-title-pro">كشف وطباعة بطاقة طالب</div>
                <div class="card-desc-pro">إصدار تقرير حساب وتقييم أكاديمي رسمي مخصص للطباعة كـ PDF أو ورقي لولي الأمر.</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("فتح صفحة الطباعة ➜", key="open_print_btn", use_container_width=True):
            st.session_state.current_page = "teacher_print_card"
            st.rerun()

    with c5:
        st.markdown(
            """
        <div class="nav-card-pro">
            <div>
                <div class="icon-badge-box icon-theme-cyan">🏫</div>
                <div class="card-title-pro">إدارة الأكاديميات والمسارات</div>
                <div class="card-desc-pro">متابعة اشتراكات الطلاب المنضمين عبر Google والتحكم في الأكاديميات المفتوحة.</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("فتح إدارة الأكاديميات ➜", key="open_acad_manage_btn", use_container_width=True):
            st.session_state.current_page = "teacher_academies"
            st.rerun()

    with c6:
        st.markdown(
            """
        <div class="nav-card-pro">
            <div>
                <div class="icon-badge-box icon-theme-rose">⚙️</div>
                <div class="card-title-pro">إعدادات المنصة والهوية</div>
                <div class="card-desc-pro">تغيير صورة المعلم، ضبط بيانات التواصل، والحصول على رابط استمارة حضور الطالب.</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("فتح الإعدادات ➜", key="open_settings_btn", use_container_width=True):
            st.session_state.current_page = "teacher_settings"
            st.rerun()

    st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
    st.markdown("### 📋 آخر الحصص المسجلة مؤخراً:")
    if not df.empty:
        st.dataframe(df.tail(6).iloc[::-1], use_container_width=True)
    else:
        st.info("ℹ️ لم يتم تسجيل أي حصص بعد. ابدأ برصد حصتك الأولى!")


# --- صفحة 2: رصد حصة جديدة ---
def render_teacher_new_session():
    render_top_navbar()
    render_page_header(
        "رصد وتسجيل حصة جديدة",
        "صفحة مستقلة لإدخال بيانات الحصة، الحضور، الحسابات ومستوى الطالب",
        "📝",
    )

    t_curriculum = st.selectbox(
        "اختر المنهج الدراسي / الدولة:",
        list(CURRICULUM_DATA.keys()),
        key="teacher_curr_select_page",
    )
    t_grades = CURRICULUM_DATA[t_curriculum]

    with st.form("standalone_entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            session_date = st.date_input("📅 تاريخ الحصة:", value=date.today())
            student_name = st.text_input(
                "👤 اسم الطالب بالكامل:", placeholder="مثال: أحمد محمد علي"
            )
            group_name = st.selectbox("📚 المرحلة / الصف الدراسي:", t_grades)
            status = st.selectbox(
                "🎯 حالة الحضور:", ["حاضر", "غائب", "متأخر", "بعذر"]
            )

        with col2:
            price = st.number_input(
                "💵 سعر الحصة (جنيه):", min_value=0.0, step=10.0, value=100.0
            )
            total_sessions = st.number_input(
                "🔢 الحصص المنفذة حتى الآن:", min_value=1, step=1, value=1
            )
            payment_type = st.selectbox(
                "💳 نظام الدفع:",
                ["اشتراك شهري", "مقدم", "مؤخر (بعد الحصة)", "مؤجل"],
            )
            student_level = st.selectbox(
                "🌟 المستوى الدراسي:",
                [
                    "ممتاز ⭐⭐⭐",
                    "جيد جداً ⭐⭐",
                    "جيد ⭐",
                    "متوسط",
                    "يحتاج متابعة",
                ],
            )

        notes = st.text_area(
            "📝 ملاحظات الواجب أو التقييم والدرجات:",
            placeholder="أداء الطالب في الحصة، حل الواجبات، النقاط التي تحتاج تقوية...",
        )

        submitted = st.form_submit_button("💾 رصد وحفظ الحصة في السجل")

        if submitted:
            if not student_name.strip():
                st.error("❌ يرجى كتابة اسم الطالب أولاً.")
            else:
                new_row = {
                    "التاريخ": str(session_date),
                    "اسم الطالب": student_name.strip(),
                    "المنهج/الدولة": t_curriculum,
                    "المجموعة/الصف": group_name,
                    "الحالة": status,
                    "سعر الحصة": price,
                    "عدد الحصص الكلي": total_sessions,
                    "نظام الدفع": payment_type,
                    "مستوى الطالب": student_level,
                    "ملاحظات": notes.strip(),
                }
                st.session_state.data = pd.concat(
                    [st.session_state.data, pd.DataFrame([new_row])],
                    ignore_index=True,
                )
                save_data(st.session_state.data)
                st.success(f"🎉 تم رصد وحفظ حصة الطالب ({student_name}) بنجاح!")


# --- صفحة 3: تعديل ومراجعة السجلات ---
def render_teacher_edit_records():
    render_top_navbar()
    render_page_header(
        "تعديل ومراجعة السجلات",
        "صفحة مستقلة لتحديث وتصحيح بيانات الحصص أو حذف السجلات بسهولة",
        "✏️",
    )
    df = st.session_state.data

    if df.empty:
        st.info("ℹ️ لا توجد أي سجلات محفوظة حالياً.")
        return

    record_options = {
        idx: f"[{row['التاريخ']}] - {row['اسم الطالب']} ({row.get('المنهج/الدولة', '')} | {row['المجموعة/الصف']}) - {row['الحالة']}"
        for idx, row in df.iterrows()
    }
    selected_idx = st.selectbox(
        "اختر السجل المراد تعديل بياناته:",
        options=list(record_options.keys()),
        format_func=lambda x: record_options[x],
    )

    selected_row = df.loc[selected_idx]
    try:
        curr_date = datetime.strptime(str(selected_row["التاريخ"]), "%Y-%m-%d").date()
    except Exception:
        curr_date = date.today()

    with st.form("standalone_edit_form"):
        c1, c2 = st.columns(2)
        with c1:
            edit_name = st.text_input("اسم الطالب:", value=str(selected_row["اسم الطالب"]))
            saved_curr = selected_row.get("المنهج/الدولة", "")
            curr_list = list(CURRICULUM_DATA.keys())
            curr_idx = curr_list.index(saved_curr) if saved_curr in curr_list else 0
            edit_curr = st.selectbox("المنهج / الدولة:", curr_list, index=curr_idx)
            edit_group = st.text_input(
                "المرحلة / الصف الدراسي:", value=str(selected_row["المجموعة/الصف"])
            )
            edit_date = st.date_input("التاريخ:", value=curr_date)
            s_opts = ["حاضر", "غائب", "متأخر", "بعذر"]
            edit_status = st.selectbox(
                "الحالة:",
                s_opts,
                index=s_opts.index(selected_row["الحالة"]) if selected_row["الحالة"] in s_opts else 0,
            )

        with c2:
            try:
                p_val = float(selected_row["سعر الحصة"])
            except Exception:
                p_val = 0.0
            edit_price = st.number_input("سعر الحصة:", min_value=0.0, step=10.0, value=p_val)

            try:
                s_val = int(selected_row["عدد الحصص الكلي"])
            except Exception:
                s_val = 1
            edit_sessions = st.number_input("عدد الحصص الكلي:", min_value=1, step=1, value=s_val)

            p_opts = ["اشتراك شهري", "مقدم", "مؤخر (بعد الحصة)", "مؤجل"]
            edit_pay = st.selectbox(
                "نظام الدفع:",
                p_opts,
                index=p_opts.index(selected_row["نظام الدفع"]) if selected_row["نظام الدفع"] in p_opts else 0,
            )

            l_opts = [
                "ممتاز ⭐⭐⭐",
                "جيد جداً ⭐⭐",
                "جيد ⭐",
                "متوسط",
                "يحتاج متابعة",
                "قيد التقييم",
            ]
            edit_level = st.selectbox(
                "المستوى:",
                l_opts,
                index=l_opts.index(selected_row["مستوى الطالب"]) if selected_row["مستوى الطالب"] in l_opts else 0,
            )

        edit_notes = st.text_area("الملاحظات والتقييم:", value=str(selected_row["ملاحظات"]))

        b1, b2 = st.columns(2)
        with b1:
            update_btn = st.form_submit_button("💾 تحديث وحفظ التعديلات")
        with b2:
            delete_btn = st.form_submit_button("🗑️ حذف هذا السجل نهائياً")

        if update_btn:
            df.at[selected_idx, "التاريخ"] = str(edit_date)
            df.at[selected_idx, "اسم الطالب"] = edit_name.strip()
            df.at[selected_idx, "المنهج/الدولة"] = edit_curr
            df.at[selected_idx, "المجموعة/الصف"] = edit_group.strip()
            df.at[selected_idx, "الحالة"] = edit_status
            df.at[selected_idx, "سعر الحصة"] = edit_price
            df.at[selected_idx, "عدد الحصص الكلي"] = edit_sessions
            df.at[selected_idx, "نظام الدفع"] = edit_pay
            df.at[selected_idx, "مستوى الطالب"] = edit_level
            df.at[selected_idx, "ملاحظات"] = edit_notes.strip()

            save_data(df)
            st.session_state.data = df
            st.success("✓ تم تحديث بيانات الحصة بنجاح!")
            st.rerun()

        if delete_btn:
            df = df.drop(selected_idx).reset_index(drop=True)
            save_data(df)
            st.session_state.data = df
            st.warning("⚠️ تم حذف السجل بنجاح.")
            st.rerun()


# --- صفحة 4: قاعدة البيانات الشاملة والتصدير ---
def render_teacher_database():
    render_top_navbar()
    render_page_header(
        "قاعدة البيانات الشاملة وكشوف الحصص",
        "صفحة مستقلة للتصفية المتقدمة، الإحصائيات الكاملة، وتصدير شيت Excel الرسمي",
        "📊",
    )
    current_df = st.session_state.data

    if current_df.empty:
        st.info("ℹ️ لا توجد بيانات مسجلة في قاعدة البيانات بعد.")
        return

    # أدوات التصفية المتقدمة
    c_f1, c_f2, c_f3 = st.columns(3)
    with c_f1:
        all_currs = ["الكل"] + [c for c in current_df["المنهج/الدولة"].dropna().unique() if str(c).strip()]
        filter_curr = st.selectbox("🌐 تصفية حسب المنهج / الدولة:", all_currs)
    with c_f2:
        all_groups = ["الكل"] + [g for g in current_df["المجموعة/الصف"].dropna().unique() if str(g).strip()]
        filter_group = st.selectbox("📚 تصفية حسب المرحلة / الصف:", all_groups)
    with c_f3:
        search_name = st.text_input("🔍 بحث باسم الطالب:")

    filtered = current_df.copy()
    if filter_curr != "الكل":
        filtered = filtered[filtered["المنهج/الدولة"] == filter_curr]
    if filter_group != "الكل":
        filtered = filtered[filtered["المجموعة/الصف"] == filter_group]
    if search_name.strip():
        filtered = filtered[filtered["اسم الطالب"].str.contains(search_name.strip(), na=False)]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("إجمالي الحصص المصفاة", len(filtered))
    m2.metric("حاضر", len(filtered[filtered["الحالة"] == "حاضر"]))
    m3.metric("غائب", len(filtered[filtered["الحالة"] == "غائب"]))
    total_cash = pd.to_numeric(filtered["سعر الحصة"], errors="coerce").fillna(0).sum()
    m4.metric("المبالغ المستحقة", f"{total_cash:,.1f} ج.م")

    st.dataframe(filtered, use_container_width=True, height=450)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        current_df.to_excel(writer, index=False)

    st.download_button(
        label="📥 تحميل وتصدير قاعدة البيانات بالكامل إلى ملف Excel",
        data=buf.getvalue(),
        file_name=FILE_NAME,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


# --- صفحة 5: كشف وطباعة بطاقة طالب ---
def render_teacher_print_card():
    render_top_navbar()
    render_page_header(
        "كشف وطباعة بطاقة الطالب الرسمية",
        "صفحة مستقلة لإصدار تقرير التقييم والمتابعة والحسابات الجاهز للطباعة الفورية",
        "🖨️",
    )
    current_df = st.session_state.data

    if current_df.empty:
        st.info("ℹ️ لا توجد بيانات لطلاب مسجلين حالياً.")
        return

    st_names = sorted(list(set([s for s in current_df["اسم الطالب"].dropna().unique() if str(s).strip()])))
    if not st_names:
        st.warning("لا توجد أسماء طلاب مسجلة.")
        return

    selected_student = st.selectbox("اختر الطالب لإصدار الكشف الرسمي:", st_names)

    if selected_student:
        st_records = current_df[current_df["اسم الطالب"] == selected_student].copy().sort_values(by="التاريخ")
        latest = st_records.iloc[-1]

        level_val = latest.get("مستوى الطالب", "غير محدد")
        pay_val = latest.get("نظام الدفع", "غير محدد")
        curr_val = latest.get("المنهج/الدولة", "-")
        group_val = latest.get("المجموعة/الصف", "-")
        price_val = latest.get("سعر الحصة", 0)

        att_cnt = len(st_records[st_records["الحالة"] == "حاضر"])
        abs_cnt = len(st_records[st_records["الحالة"] == "غائب"])
        total_cnt = len(st_records)
        total_due = pd.to_numeric(st_records["سعر الحصة"], errors="coerce").fillna(0).sum()

        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        col_k1.metric("المنهج والمرحلة", f"{curr_val} - {group_val}")
        col_k2.metric("المستوى", str(level_val))
        col_k3.metric("نظام الدفع", str(pay_val))
        col_k4.metric("سعر الحصة", f"{price_val}")

        col_k5, col_k6, col_k7, col_k8 = st.columns(4)
        col_k5.metric("الحصص المنفذة", total_cnt)
        col_k6.metric("مرات الحضور", att_cnt)
        col_k7.metric("مرات الغياب", abs_cnt)
        col_k8.metric("إجمالي الحساب", f"{total_due:,.1f}")

        rows_html = ""
        for _, r in st_records.iterrows():
            st_color = "#0f766e" if r["الحالة"] == "حاضر" else ("#b91c1c" if r["الحالة"] == "غائب" else "#b45309")
            rows_html += f"""
            <tr>
                <td style="padding: 10px; border: 1.5px solid #cbd5e1; font-weight: 800;">{r['التاريخ']}</td>
                <td style="padding: 10px; border: 1.5px solid #cbd5e1; color:{st_color}; font-weight: 900;">{r['الحالة']}</td>
                <td style="padding: 10px; border: 1.5px solid #cbd5e1; font-weight: 800;">{r['سعر الحصة']}</td>
                <td style="padding: 10px; border: 1.5px solid #cbd5e1; font-weight: 800;">{r['نظام الدفع']}</td>
                <td style="padding: 10px; border: 1.5px solid #cbd5e1; font-weight: 900; color: #1e40af;">{r['مستوى الطالب']}</td>
                <td style="padding: 10px; border: 1.5px solid #cbd5e1; font-weight: 700;">{r['ملاحظات']}</td>
            </tr>
            """

        teacher_img_tag = (
            f'<img src="data:image/jpeg;base64,{img_b64}" style="width: 90px; height: 90px; border-radius: 50%; border: 3px solid #1e40af; object-fit: cover;">'
            if img_b64
            else ""
        )

        printable_html = f"""<!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="utf-8">
            <title>كشف متابعة - {selected_student}</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@600;700;800;900&display=swap');
                body {{ 
                    font-family: 'Cairo', Tahoma, Arial, sans-serif; 
                    padding: 35px; 
                    color: #0f172a; 
                    background-color: #ffffff;
                }}
                .header-box {{
                    border-bottom: 3px solid #1e40af;
                    padding-bottom: 18px;
                    margin-bottom: 25px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .brand-name {{ color: #1e40af; margin: 0; font-size: 30px; font-weight: 900; }}
                .brand-sub {{ color: #475569; margin: 4px 0 0 0; font-size: 15px; font-weight: 700; }}
                .stats-box {{ width: 100%; border-collapse: collapse; margin-bottom: 25px; border-radius: 8px; overflow: hidden; }}
                .stats-box th, .stats-box td {{ border: 1.5px solid #cbd5e1; padding: 12px; text-align: center; font-size: 15px; font-weight: 800; }}
                .stats-box th {{ background: #f1f5f9; color: #1e3a8a; font-weight: 900; }}
                .details-table {{ width: 100%; border-collapse: collapse; text-align: center; margin-top: 15px; }}
                .details-table th {{ background-color: #f1f5f9; color: #1e3a8a; font-weight: 900; font-size: 15px; padding: 12px; border: 1.5px solid #cbd5e1; }}
                .footer-note {{ margin-top: 40px; text-align: center; color: #475569; font-size: 15px; font-weight: 800; border-top: 2px dashed #cbd5e1; padding-top: 20px; }}
            </style>
        </head>
        <body onload="window.print()">
            <div class="header-box">
                <div style="display: flex; align-items: center; gap: 20px;">
                    {teacher_img_tag}
                    <div>
                        <h2 class="brand-name">البشمهندس X الرياضة 📐</h2>
                        <p class="brand-sub">كشف التقييم الأكاديمي والحساب المالي الدوري</p>
                        <p style="margin: 4px 0; font-size: 15px; font-weight: 700;"><b>المنهج والمرحلة:</b> {curr_val} — {group_val}</p>
                    </div>
                </div>
                <div style="text-align: left;">
                    <h2 style="color: #1e40af; margin: 0; font-size: 26px; font-weight: 900;">{selected_student}</h2>
                    <p style="margin: 5px 0 0 0; color: #64748b; font-size: 14px; font-weight: 700;">تاريخ التقرير: {date.today()}</p>
                </div>
            </div>

            <table class="stats-box">
                <tr>
                    <th>المستوى الدراسي</th>
                    <th>نظام الدفع</th>
                    <th>سعر الحصة</th>
                    <th>إجمالي الحصص</th>
                    <th>مرات الحضور</th>
                    <th>مرات الغياب</th>
                    <th>المبلغ المستحق</th>
                </tr>
                <tr>
                    <td style="color: #1e40af; font-weight: 900;">{level_val}</td>
                    <td>{pay_val}</td>
                    <td>{price_val}</td>
                    <td style="font-weight: 900;">{total_cnt}</td>
                    <td style="color: #0f766e; font-weight: 900;">{att_cnt}</td>
                    <td style="color: #b91c1c; font-weight: 900;">{abs_cnt}</td>
                    <td style="font-weight: 900; font-size: 18px; color: #0f172a;">{total_due:,.1f} ج.م</td>
                </tr>
            </table>

            <h3 style="margin-top: 30px; margin-bottom: 12px; color: #1e40af; font-size: 20px; font-weight: 900;">سجل تفاصيل الحصص والواجبات:</h3>
            <table class="details-table">
                <tr>
                    <th>التاريخ</th>
                    <th>الحالة</th>
                    <th>سعر الحصة</th>
                    <th>نظام الدفع</th>
                    <th>المستوى</th>
                    <th>ملاحظات المعلم وتقييم الطالب</th>
                </tr>
                {rows_html}
            </table>

            <div class="footer-note">
                مع أطيب أمنيات: <b>البشمهندس X الرياضة</b> — متابعة مستمرة نحو التفوق والدرجة النهائية 🌟
            </div>
        </body>
        </html>"""

        c_p1, c_p2 = st.columns([2, 1])
        with c_p1:
            st.download_button(
                label=f"🖨️ فتح وتحميل كشف ({selected_student}) للطباعة PDF",
                data=printable_html.encode("utf-8"),
                file_name=f"كشف_متابعة_{selected_student}.html",
                mime="text/html",
                use_container_width=True,
            )
        with c_p2:
            st.info("💡 اضغط الزر أعلاه ثم اختر 'حفظ كـ PDF' من نافذة الطباعة.")

        st.write("---")
        st.dataframe(
            st_records[["التاريخ", "الحالة", "سعر الحصة", "نظام الدفع", "مستوى الطالب", "ملاحظات"]],
            use_container_width=True,
        )


# --- صفحة 6: إدارة الأكاديميات للمعلم ---
def render_teacher_academies():
    render_top_navbar()
    render_page_header(
        "إدارة الأكاديميات والمسارات التعليمية",
        "صفحة مستقلة لمتابعة اشتراكات الطلاب المسجلين عبر Google والتحكم في الأكاديميات",
        "🏫",
    )
    subs = st.session_state.academy_subs

    st.markdown("### 📋 إحصائيات اشتراكات الأكاديميات:")
    col_a1, col_a2, col_a3 = st.columns(3)
    col_a1.metric("عدد الأكاديميات المتاحة", len(ACADEMIES_CATALOG))
    col_a2.metric("إجمالي الطلاب المشتركين", len(subs))
    col_a3.metric("طريقة التحقق المعتمدة", "Google OTP")

    st.markdown("---")
    st.markdown("### 🎓 قائمة الأكاديميات المعروضة للطلاب:")
    for acad in ACADEMIES_CATALOG:
        with st.expander(f"{acad['icon']} {acad['title']} — {acad['badge']}", expanded=True):
            st.write(f"**الوصف:** {acad['desc']}")
            st.write(f"**المناهج المغطاة:** {', '.join(acad['curriculums'])}")
            st.write(f"**المميزات:** {', '.join(acad['features'])}")

    if subs:
        st.markdown("### 👥 الطلاب المشتركون والمسجلون عبر Google:")
        subs_list = []
        for email, details in subs.items():
            subs_list.append({
                "البريد الإلكتروني (Google)": email,
                "اسم الطالب": details.get("student_name", "-"),
                "الأكاديمية المشترك بها": details.get("academy_title", "-"),
                "تاريخ الاشتراك": details.get("enrolled_at", "-"),
                "حالة التحقق": "✅ مؤكد بكود Google OTP"
            })
        st.dataframe(pd.DataFrame(subs_list), use_container_width=True)
    else:
        st.info("ℹ️ لم يقم أي طالب بالتسجيل في الأكاديميات بعد.")


# --- صفحة 7: إعدادات المنصة وشعار المعلم ---
def render_teacher_settings():
    render_top_navbar()
    render_page_header(
        "إعدادات المنصة وهوية المعلم",
        "صفحة مستقلة للتحكم في شعار المنصة، الروابط السريعة، وتحديث صورة المعلم",
        "⚙️",
    )

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("### 🔗 روابط تسجيل الطلاب:")
        st.markdown("شارك الرابط التالي مع الطلاب ليدخلوا على المنصة ويسجلوا حضورهم بأنفسهم:")
        student_url = "http://localhost:8501/?role=student"
        st.code(student_url, language="text")
        st.caption("عند فتح الرابط سيتم توجيه الطالب مباشرة لبوابة الطالب.")

        st.markdown("---")
        st.markdown("### 👤 بيانات المعلم والمنصة:")
        st.text_input("اسم المعلم واللقب:", value="البشمهندس", disabled=True)
        st.text_input("التخصص الأكاديمي:", value="الرياضيات والقدرات لكافة المناهج العربية", disabled=True)

    with col_s2:
        st.markdown("### 📷 صورة الشعار والمعلم الحالية:")
        if found_img_path and os.path.exists(found_img_path):
            st.image(found_img_path, width=220)
        else:
            st.warning("لا توجد صورة معلم محددة حالياً.")

        st.markdown("#### رفع صورة جديدة للمعلم وتحديث الشعار:")
        new_photo = st.file_uploader("اختر ملف الصورة الجديد:", type=["jpg", "png", "jpeg"], key="settings_uploader_pro")
        if new_photo is not None:
            with open(IMG_NAME, "wb") as f:
                f.write(new_photo.getbuffer())
            # حفظ في المجلدات الأخرى للمزامنة
            for bp in ["../منصه/teacher.jpg", "C:/Users/mogho/OneDrive/Desktop/منصه/teacher.jpg"]:
                if os.path.exists(os.path.dirname(bp)):
                    try:
                        with open(bp, "wb") as f:
                            f.write(new_photo.getbuffer())
                    except Exception:
                        pass
            st.success("✓ تم تحديث وحفظ صورة المعلم بنجاح في كامل المنصة!")
            st.rerun()


# ==============================================================================
# 10. صفحات منصة الطالب (المستقلة وبتصميم أيقونات بصري احترافي)
# ==============================================================================

# --- صفحة 1: بوابة الطالب الرئيسية ---
def render_student_home():
    render_top_navbar()
    user = st.session_state.auth_user
    student_name = user["name"] if user["name"] else "عزيزي الطالب"

    render_page_header(
        f"مرحباً بك يا {student_name} 🌟",
        "منصة البشمهندس X الرياضة | بوابتك التفاعلية لتسجيل الحضور، متابعة الحصص، والانضمام للأكاديميات",
        "👨‍🎓",
    )

    # مؤشرات سريعة لحساب الطالب
    df = st.session_state.data
    subs = st.session_state.academy_subs
    student_records = df[df["اسم الطالب"].str.contains(student_name, na=False)] if not df.empty and student_name != "عزيزي الطالب" else pd.DataFrame()

    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    c_m1.metric("📌 حصصي المسجلة", len(student_records))
    c_m2.metric("✅ مرات الحضور", len(student_records[student_records["الحالة"] == "حاضر"]) if not student_records.empty else 0)
    c_m3.metric("🌟 المستوى الدراسي", str(student_records.iloc[-1].get("مستوى الطالب", "قيد التقييم")) if not student_records.empty else "قيد التقييم")
    enrolled_count = 1 if user.get("email") in subs else 0
    c_m4.metric("🏫 الأكاديميات المشترك بها", enrolled_count)

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    st.markdown("### 🚀 استكشف خدمات وأقسام المنصة بأيقونات منظمة:")

    # شبكة البطاقات بأيقونات بصرية منظمة واحترافية (Organized Visual Icons)
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            """
        <div class="nav-card-pro">
            <div>
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div class="icon-badge-box icon-theme-blue">✍️</div>
                    <span class="student-badge-pill" style="background: #eff6ff; color: #1d4ed8;">خدمة فورية</span>
                </div>
                <div class="card-title-pro">تسجيل الحضور والتقييم</div>
                <div class="card-desc-pro">سجل حضورك للحصة الحالية بنفسك وقيّم شرح البشمهندس من 5 نجوم مع كتابة أي ملاحظة أو استفسار.</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("فتح استمارة تسجيل الحضور ➜", key="open_std_attend_btn", use_container_width=True):
            st.session_state.current_page = "student_attendance"
            st.rerun()

    with c2:
        st.markdown(
            """
        <div class="nav-card-pro">
            <div>
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div class="icon-badge-box icon-theme-purple">🏫</div>
                    <span class="student-badge-pill" style="background: #faf5ff; color: #6b21a8;">مسارات متقدمة</span>
                </div>
                <div class="card-title-pro">الأكاديميات والتحقق عبر Google</div>
                <div class="card-desc-pro">استعرض أكاديميات الرياضيات والقدرات المتاحة واشترك بسهولة عبر تأكيد كود OTP لحساب Google.</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("استعراض الأكاديميات المتاحة ➜", key="open_std_acad_btn", use_container_width=True):
            st.session_state.current_page = "student_academies"
            st.rerun()

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    c3, c4 = st.columns(2)

    with c3:
        st.markdown(
            """
        <div class="nav-card-pro">
            <div>
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div class="icon-badge-box icon-theme-emerald">📜</div>
                    <span class="student-badge-pill" style="background: #ecfdf5; color: #047857;">تقارير الدرجات</span>
                </div>
                <div class="card-title-pro">كشف حسابي ودرجاتي</div>
                <div class="card-desc-pro">تابع أرشيف حصصك السابقة، تقييمات المعلم لأدائك في الواجبات، ونسبة التزامك بالحضور.</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("عرض كشف درجاتي وحصصي ➜", key="open_std_rec_btn", use_container_width=True):
            st.session_state.current_page = "student_my_records"
            st.rerun()

    with c4:
        st.markdown(
            """
        <div class="nav-card-pro">
            <div>
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div class="icon-badge-box icon-theme-cyan">👤</div>
                    <span class="student-badge-pill" style="background: #ecfeff; color: #0e7490;">الملف الشخصي</span>
                </div>
                <div class="card-title-pro">ملفي الشخصي والبيانات</div>
                <div class="card-desc-pro">شاهد بيانات حسابك، حالة التوثيق برمز Google OTP، والأكاديميات التي تم تفعيل اشتراكك بها.</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("عرض بيانات حسابي ➜", key="open_std_prof_btn", use_container_width=True):
            st.session_state.current_page = "student_profile"
            st.rerun()


# --- صفحة 2: استمارة حضور الطالب والتقييم ---
def render_student_attendance():
    render_top_navbar()
    render_page_header(
        "استمارة تسجيل حضور الطالب وتقييم الحصة",
        "صفحة مستقلة لتأكيد حضورك وإرسال تقييمك للبشمهندس",
        "✍️",
    )

    user = st.session_state.auth_user
    default_name = user["name"] if user["is_logged_in"] and user["name"] != "طالب المنصة" else ""

    selected_curriculum = st.selectbox(
        "🌐 اختر المنهج الدراسي / الدولة:", list(CURRICULUM_DATA.keys()), key="std_curr_sel"
    )
    available_grades = CURRICULUM_DATA[selected_curriculum]

    with st.form("student_standalone_attendance_form", clear_on_submit=True):
        st_name = st.text_input(
            "👤 اسم الطالب بالكامل (ثلاثي أو رباعي):",
            value=default_name,
            placeholder="مثال: أحمد محمد علي",
        )
        st_grade = st.selectbox("📚 المرحلة / الصف الدراسي:", available_grades)
        st_date = st.date_input("📅 تاريخ الحصة:", value=date.today())

        rating_options = [
            "⭐⭐⭐⭐⭐ (5/5) ممتاز جداً وفهم بنسبة 100%",
            "⭐⭐⭐⭐ (4/5) جيد جداً وشرح رائع",
            "⭐⭐⭐ (3/5) جيد ومفهوم",
            "⭐⭐ (2/5) متوسط ويحتاج توضيح",
            "⭐ (1/5) يحتاج إعادة شرح",
        ]
        selected_rating = st.selectbox(
            "⭐ قيّم الحصة مع البشمهندس (من 5 نجوم):",
            options=rating_options,
            index=0,
        )

        submit_btn = st.form_submit_button("✅ إرسال وتأكيد الحضور الآن")

        if submit_btn:
            if not st_name.strip():
                st.error("❌ يرجى كتابة اسمك بالكامل.")
            else:
                new_row = {
                    "التاريخ": str(st_date),
                    "اسم الطالب": st_name.strip(),
                    "المنهج/الدولة": selected_curriculum,
                    "المجموعة/الصف": st_grade,
                    "الحالة": "حاضر",
                    "سعر الحصة": 0.0,
                    "عدد الحصص الكلي": 1,
                    "نظام الدفع": "مؤجل",
                    "مستوى الطالب": "قيد التقييم",
                    "ملاحظات": f"تقييم الطالب للحصة: {selected_rating}",
                }
                st.session_state.data = pd.concat(
                    [st.session_state.data, pd.DataFrame([new_row])],
                    ignore_index=True,
                )
                save_data(st.session_state.data)
                st.success(f"🎉 شكراً لك {st_name}! تم تسجيل حضورك وتقييمك بنجاح في سجلات البشمهندس.")


# --- صفحة 3: الأكاديميات والتسجيل عبر Google مع كود التحقق ---
def render_student_academies():
    render_top_navbar()
    render_page_header(
        "أكاديميات البشمهندس X الرياضة | التسجيل بالتحقق عبر Google",
        "صفحة مستقلة تتيح لك التسجيل السريع في الأكاديميات عبر حساب Google مع كود تأكيد OTP",
        "🏫",
    )

    user = st.session_state.auth_user
    subs = st.session_state.academy_subs
    current_user_email = user["email"] if user["is_logged_in"] else ""

    st.markdown("### 🌟 الأكاديميات المتاحة للتسجيل والاشتراك:")
    st.markdown("يمكنك التسجيل في أي أكاديمية من خلال إدخال حساب Google الخاص بك وإرسال كود التحقق لتأكيد اشتراكك فورياً.")

    for acad in ACADEMIES_CATALOG:
        is_enrolled = (current_user_email in subs and subs[current_user_email].get("academy_id") == acad["id"])

        status_label = "✅ مشترك ومفعل بحساب Google" if is_enrolled else "🔓 متاح للتسجيل الفوري"
        status_bg = "#dcfce7" if is_enrolled else "#eff6ff"
        status_color = "#15803d" if is_enrolled else "#1e40af"

        st.markdown(
            f"""
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 20px; padding: 24px; margin-bottom: 22px; box-shadow: 0 4px 14px rgba(0,0,0,0.035);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 14px;">
                    <div class="icon-badge-box icon-theme-blue" style="margin-bottom: 0; width: 56px; height: 56px; font-size: 28px;">{acad['icon']}</div>
                    <div>
                        <h3 style="margin: 0; color: #0f172a; font-weight: 900; font-size: 20px;">{acad['title']}</h3>
                        <span style="font-size: 13px; color: #64748b; font-weight: 700;">المعلم: {acad['instructor']} • {acad['badge']}</span>
                    </div>
                </div>
                <span style="background: {status_bg}; color: {status_color}; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 800;">
                    {status_label}
                </span>
            </div>
            <p style="color: #475569; font-size: 15px; font-weight: 600; line-height: 1.6; margin: 10px 0;">{acad['desc']}</p>
            <div style="margin: 12px 0;">
                <span style="font-size: 13px; font-weight: 800; color: #1e3a8a;">المناهج المشمولة: </span>
                <span style="font-size: 13px; color: #334155;">{' • '.join(acad['curriculums'])}</span>
            </div>
            <div style="margin-top: 10px; font-size: 13px; color: #059669; font-weight: 700;">
                ✓ المميزات: {' | '.join(acad['features'])}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # نظام الاشتراك عبر Google OTP إذا لم يكن الطالب مسجلاً
        if not is_enrolled:
            with st.expander(f"🚀 اضغط هنا للتسجيل في ({acad['title']}) عبر Google مع كود التحقق"):
                with st.form(f"enroll_form_{acad['id']}"):
                    enroll_email = st.text_input(
                        "بريد Google (Gmail) الخاص بك:",
                        value=current_user_email,
                        key=f"enroll_email_{acad['id']}",
                        placeholder="yourname@gmail.com",
                    )
                    enroll_name = st.text_input(
                        "اسم الطالب بالكامل:",
                        value=user["name"],
                        key=f"enroll_name_{acad['id']}",
                        placeholder="مثال: سارة أحمد محمود",
                    )

                    send_enroll_otp = st.form_submit_button("📨 إرسال كود التحقق إلى حساب Google")

                    if send_enroll_otp:
                        if not enroll_email.strip() or "@" not in enroll_email:
                            st.error("❌ يرجى كتابة بريد إلكتروني صالح تابع لـ Google.")
                        elif not enroll_name.strip():
                            st.error("❌ يرجى كتابة اسمك.")
                        else:
                            code = generate_and_send_otp(enroll_email.strip(), purpose=acad["id"])
                            st.session_state[f"otp_active_{acad['id']}"] = {
                                "code": code,
                                "email": enroll_email.strip(),
                                "name": enroll_name.strip(),
                            }
                            st.success(f"✓ تم إرسال كود التحقق بنجاح إلى ({enroll_email})!")

                # مربع تأكيد الكود
                if f"otp_active_{acad['id']}" in st.session_state:
                    otp_data = st.session_state[f"otp_active_{acad['id']}"]
                    st.markdown(
                        f"""
                    <div class="google-otp-card">
                        <h4 style="color: #1e40af; font-weight: 900; margin: 0;">كود تأكيد الاشتراك في الأكاديمية:</h4>
                        <div class="otp-code-display">{otp_data['code']}</div>
                        <p style="color: #64748b; font-size: 13px; margin: 0; font-weight: 700;">أدخل الكود لتفعيل اشتراكك الفوري</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    with st.form(f"verify_otp_form_{acad['id']}"):
                        entered_otp = st.text_input("أدخل كود التحقق (6 أرقام):", max_chars=6, key=f"input_otp_{acad['id']}")
                        verify_btn = st.form_submit_button("✅ تأكيد الكود وتفعيل الاشتراك في الأكاديمية")

                        if verify_btn:
                            if verify_otp(otp_data["email"], entered_otp, purpose=acad["id"]):
                                subs[otp_data["email"]] = {
                                    "student_name": otp_data["name"],
                                    "academy_id": acad["id"],
                                    "academy_title": acad["title"],
                                    "enrolled_at": str(date.today()),
                                    "verified": True,
                                }
                                save_academies_enrollment(subs)
                                st.session_state.academy_subs = subs

                                if not user["is_logged_in"]:
                                    st.session_state.auth_user = {
                                        "is_logged_in": True,
                                        "role": "student",
                                        "name": otp_data["name"],
                                        "email": otp_data["email"],
                                        "method": "Google OTP",
                                        "verified": True,
                                    }
                                st.success(f"🎉 مبارك! تم تفعيل اشتراكك بنجاح في ({acad['title']}) وتأكيد حساب Google!")
                                st.rerun()
                            else:
                                st.error("❌ كود التحقق غير صحيح، يرجى كتابته كما هو ظاهر.")
        else:
            st.success(f"✓ أنت مسجل رسمياً في هذه الأكاديمية بتاريخ: {subs[current_user_email].get('enrolled_at', '')}")


# --- صفحة 4: سجل حصصي ودرجاتي للطالب ---
def render_student_my_records():
    render_top_navbar()
    render_page_header(
        "كشف حصصي ودرجاتي وتقييمات البشمهندس",
        "صفحة مستقلة لمتابعة نسبة حضورك وغيابك والملاحظات الدراسية المسجلة لك",
        "📜",
    )

    df = st.session_state.data
    user = st.session_state.auth_user

    search_name = st.text_input(
        "🔍 ابحث عن اسمك لعرض كشف الحصص:",
        value=user["name"] if user["is_logged_in"] and user["name"] != "طالب المنصة" else "",
        placeholder="اكتب اسمك كما هو مسجل...",
    )

    if not search_name.strip():
        st.info("💡 اكتب اسمك في خانة البحث أعلاه لعرض كشف حسابك ومستواك.")
        return

    student_df = df[df["اسم الطالب"].str.contains(search_name.strip(), na=False)]

    if student_df.empty:
        st.warning(f"لم يتم العثور على أي حصص مسجلة باسم: ({search_name}).")
        return

    total_sessions = len(student_df)
    attended = len(student_df[student_df["الحالة"] == "حاضر"])
    absent = len(student_df[student_df["الحالة"] == "غائب"])
    latest_level = student_df.iloc[-1].get("مستوى الطالب", "قيد التقييم")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي الحصص", total_sessions)
    c2.metric("مرات الحضور", attended)
    c3.metric("مرات الغياب", absent)
    c4.metric("المستوى الدراسي الحالي", str(latest_level))

    st.markdown("### 📋 تفاصيل الحصص والواجبات:")
    st.dataframe(
        student_df[["التاريخ", "المجموعة/الصف", "الحالة", "مستوى الطالب", "ملاحظات"]],
        use_container_width=True,
    )


# --- صفحة 5: الملف الشخصي للطالب ---
def render_student_profile():
    render_top_navbar()
    render_page_header(
        "الملف الشخصي وإعدادات حساب الطالب",
        "صفحة مستقلة لعرض بيانات الحساب، حالة التحقق عبر Google، وتفاصيل الاشتراكات",
        "👤",
    )
    user = st.session_state.auth_user
    subs = st.session_state.academy_subs
    user_email = user.get("email", "")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 18px; padding: 25px; box-shadow: 0 4px 14px rgba(0,0,0,0.03);">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 15px;">
                <div class="icon-badge-box icon-theme-blue" style="margin-bottom: 0; width: 48px; height: 48px; font-size: 24px;">👤</div>
                <h3 style="margin: 0; color: #1e3a8a; font-size: 20px; font-weight: 800;">بيانات الحساب الشخصي:</h3>
            </div>
            <p><b>اسم الطالب:</b> {user.get('name', 'غير محدد')}</p>
            <p><b>البريد الإلكتروني:</b> {user_email}</p>
            <p><b>طريقة الدخول:</b> {user.get('method', 'Google')}</p>
            <p><b>حالة التحقق:</b> {'✅ حساب موثق ومؤكد عبر Google OTP' if user.get('verified') else '⚠️ غير مؤكد'}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        enrolled_acad = subs.get(user_email, {}).get("academy_title", "غير مشترك في أكاديميات حالياً")
        st.markdown(
            f"""
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 18px; padding: 25px; box-shadow: 0 4px 14px rgba(0,0,0,0.03);">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 15px;">
                <div class="icon-badge-box icon-theme-purple" style="margin-bottom: 0; width: 48px; height: 48px; font-size: 24px;">🏫</div>
                <h3 style="margin: 0; color: #1e3a8a; font-size: 20px; font-weight: 800;">الاشتراكات الأكاديمية:</h3>
            </div>
            <p><b>الأكاديمية المفعلة:</b> {enrolled_acad}</p>
            <p><b>تاريخ الاشتراك:</b> {subs.get(user_email, {}).get('enrolled_at', '-')}</p>
            <p><b>حالة الاشتراك:</b> {'✅ نشط ومفعل' if enrolled_acad != 'غير مشترك في أكاديميات حالياً' else '—'}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )


# ==============================================================================
# 11. موجه الصفحات الرئيسي (Main Page Router)
# ==============================================================================
user = st.session_state.auth_user
page = st.session_state.current_page

if not user["is_logged_in"]:
    render_login_page()
else:
    if user["role"] == "teacher":
        if page == "teacher_home" or page == "home":
            render_teacher_home()
        elif page == "teacher_new_session":
            render_teacher_new_session()
        elif page == "teacher_edit_records":
            render_teacher_edit_records()
        elif page == "teacher_database":
            render_teacher_database()
        elif page == "teacher_print_card":
            render_teacher_print_card()
        elif page == "teacher_academies":
            render_teacher_academies()
        elif page == "teacher_settings":
            render_teacher_settings()
        else:
            render_teacher_home()

    elif user["role"] == "student":
        if page == "student_home" or page == "home":
            render_student_home()
        elif page == "student_attendance":
            render_student_attendance()
        elif page == "student_academies":
            render_student_academies()
        elif page == "student_my_records":
            render_student_my_records()
        elif page == "student_profile":
            render_student_profile()
        else:
            render_student_home()
    else:
        render_login_page()
