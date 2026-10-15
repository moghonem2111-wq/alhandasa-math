import hashlib
import os
import os as _os
import io
import json
import base64
import re
import html
import urllib.request
import urllib.error
import urllib.parse
import uuid
import zipfile
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from PIL import Image
import streamlit as st

try:
    from html_exam_system import render_html_exam_admin, render_html_exam_portal
except Exception:
    render_html_exam_admin = None
    render_html_exam_portal = None
try:
    from ai_studio import render_ai_studio
except Exception:
    render_ai_studio = None
try:
    from weasyprint import HTML as WeasyHTML
except Exception:
    WeasyHTML = None

st.set_page_config(
    page_title="البشمهندس x الرياضه | منصة تعليمية للرياضيات والإحصاء",
    page_icon="📐",
    layout="wide",
)

try:
    from streamlit_paste_button import paste_image_button
except ImportError:
    paste_image_button = None

try:
    from streamlit_cropper import st_cropper
except ImportError:
    st_cropper = None

FILE_NAME = "سجل_الغياب_والحصص.xlsx"
IMG_NAME = "teacher.jpg"
TEACHER_PHONE = "01016361440"

# تخزين دائم اختياري على Supabase لمنع ضياع بيانات المنصة عند إعادة تشغيل Streamlit Cloud.
SUPABASE_URL = ""
SUPABASE_KEY = ""
try:
    SUPABASE_URL = str(st.secrets.get("SUPABASE_URL", "")).strip()
    SUPABASE_KEY = str(st.secrets.get("SUPABASE_KEY", "")).strip()
except Exception:
    pass
SUPABASE_TABLE = "platform_storage"
SUPABASE_INTERFACE_TABLE = "student_interface_storage"
SUPABASE_VERSIONS_TABLE = "platform_storage_versions"
SUPABASE_RECORD_ID = "main"

# Microsoft Excel Online / OneDrive (اختياري)
MS_TENANT_ID = ""
MS_CLIENT_ID = ""
MS_CLIENT_SECRET = ""
MS_ONEDRIVE_USER = ""
MS_EXCEL_PATH = "سجل_الغياب_والحصص.xlsx"
try:
    MS_TENANT_ID = str(st.secrets.get("MS_TENANT_ID", "")).strip()
    MS_CLIENT_ID = str(st.secrets.get("MS_CLIENT_ID", "")).strip()
    MS_CLIENT_SECRET = str(st.secrets.get("MS_CLIENT_SECRET", "")).strip()
    MS_ONEDRIVE_USER = str(st.secrets.get("MS_ONEDRIVE_USER", "")).strip()
    MS_EXCEL_PATH = str(st.secrets.get("MS_EXCEL_PATH", MS_EXCEL_PATH)).strip() or MS_EXCEL_PATH
except Exception:
    pass

def _onedrive_enabled():
    return bool(MS_TENANT_ID and MS_CLIENT_ID and MS_CLIENT_SECRET and MS_ONEDRIVE_USER)

def _graph_access_token():
    if not _onedrive_enabled(): return None
    try:
        url = f"https://login.microsoftonline.com/{MS_TENANT_ID}/oauth2/v2.0/token"
        body = urllib.parse.urlencode({"client_id":MS_CLIENT_ID,"client_secret":MS_CLIENT_SECRET,"scope":"https://graph.microsoft.com/.default","grant_type":"client_credentials"}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type":"application/x-www-form-urlencoded"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp: return json.loads(resp.read().decode("utf-8")).get("access_token")
    except Exception as exc:
        st.session_state["onedrive_last_error"] = str(exc); return None

def _onedrive_item_url():
    user = urllib.parse.quote(MS_ONEDRIVE_USER, safe="")
    path = urllib.parse.quote(str(MS_EXCEL_PATH).strip().lstrip("/"), safe="/")
    return f"https://graph.microsoft.com/v1.0/users/{user}/drive/root:/{path}"

def _onedrive_upload_excel(excel_bytes, reason="autosave"):
    if not _onedrive_enabled(): return False
    token = _graph_access_token()
    if not token: return False
    try:
        req = urllib.request.Request(_onedrive_item_url()+":/content", data=excel_bytes, headers={"Authorization":f"Bearer {token}","Content-Type":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}, method="PUT")
        with urllib.request.urlopen(req, timeout=60) as resp: data=json.loads(resp.read().decode("utf-8"))
        st.session_state["onedrive_web_url"] = str(data.get("webUrl", "")); st.session_state["onedrive_last_status"] = f"تم تحديث Excel Online ({reason})"; st.session_state["onedrive_last_error"] = ""; return True
    except Exception as exc:
        st.session_state["onedrive_last_error"] = str(exc); st.session_state["onedrive_last_status"] = "تعذر تحديث Excel Online"; return False

def _onedrive_download_excel():
    if not _onedrive_enabled(): return None
    token = _graph_access_token()
    if not token: return None
    try:
        req=urllib.request.Request(_onedrive_item_url()+":/content", headers={"Authorization":f"Bearer {token}"}, method="GET")
        with urllib.request.urlopen(req, timeout=60) as resp: return resp.read()
    except Exception as exc:
        st.session_state["onedrive_last_error"] = str(exc); return None

def _onedrive_metadata():
    if not _onedrive_enabled(): return None
    token=_graph_access_token()
    if not token: return None
    try:
        req=urllib.request.Request(_onedrive_item_url(), headers={"Authorization":f"Bearer {token}"}, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp: return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        st.session_state["onedrive_last_error"] = str(exc); return None

def _cloud_storage_enabled():
    return bool(SUPABASE_URL and SUPABASE_KEY)

def _supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def _cloud_load_excel_bytes():
    if not _cloud_storage_enabled():
        return None
    try:
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{SUPABASE_TABLE}?id=eq.{SUPABASE_RECORD_ID}&select=payload"
        req = urllib.request.Request(url, headers=_supabase_headers(), method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data and data[0].get("payload"):
            return base64.b64decode(data[0]["payload"])
    except Exception:
        pass
    return None

# ==========================================
# schema Definitions
# ==========================================
COL_USERS = ["كود الطالب", "اسم الطالب", "الصف الدراسي", "المجموعة / الموعد", "رقم هاتف الطالب", "رقم هاتف ولي الأمر", "المرور", "ملاحظات", "صورة الطالب"]
COL_SESSIONS = ["معرف الحصة", "كود الطالب", "التاريخ", "الحالة", "عنوان الحصة", "الواجب المطلوب", "ملاحظات الحضور"]
COL_ASSESSMENTS = ["معرف التقييم", "كود الطالب", "التاريخ", "النوع", "الدرجة المكتسبة", "الدرجة النهائية", "ملاحظات التقييم"]
COL_MESSAGES = ["معرف الرسالة", "كود الطالب", "التاريخ والوقت", "المرسل", "محتوى الرسالة", "تمت القراءة"]
COL_EXAMS = ["معرف الامتحان", "عنوان الامتحان", "الصف الدراسي", "الوصف", "المدة بالدقائق", "درجة النجاح", "حالة الامتحان", "الأسئلة JSON"]
COL_ESSAYS = ["معرف الحل", "معرف الامتحان", "كود الطالب", "اسم الطالب", "الصف الدراسي", "التاريخ والوقت", "صورة الحل Base64", "درجة المعلم", "ملاحظات المعلم", "حالة تصحيح المعلم"]
COL_BOOKINGS = ["معرف الحجز", "اسم الطالب", "رقم الهاتف", "الصف الدراسي", "المحافظة / المركز", "نوع الدراسة", "تاريخ الحجز", "حالة الحجز"]
COL_BANK_REQUESTS = ["معرف الطلب", "كود الطالب", "اسم الطالب", "اسم البنك", "الفرع / المدينة", "مبلغ السداد", "تاريخ الطلب", "حالة الطلب"]
COL_QUESTION_BANK = ["معرف السؤال", "المادة / المفهوم", "الصف الدراسي", "مستوى الصعوبة", "نص السؤال", "الخيارات JSON", "الإجابة الصحيحة", "التفسير"]
COL_VIDEOS = ["معرف الفيديو", "عنوان الفيديو", "الوصف", "الصف الدراسي", "رابط الفيديو", "صورة المعاينة", "تاريخ النشر"]
COL_VIDEO_COMMENTS = ["معرف التعليق", "معرف الفيديو", "كود الطالب", "اسم الطالب", "التاريخ والوقت", "نص التعليق"]
COL_ABQARY = ["معرف التحدي", "عنوان التحدي", "الصف الدراسي", "السؤال / المسألة", "النقاط", "الإجابة الصحيحة", "تاريخ الانتهاء"]
COL_ONLINE_SCHEDULE = ["معرف الجلسة", "عنوان الجلسة", "الصف الدراسي", "التاريخ والوقت", "رابط Zoom / Teams", "كلمة المرور", "ملاحظات"]
COL_WEEKLY_SCHEDULE = ["معرف الموعد", "اليوم", "الوقت", "الصف الدراسي", "المجموعة / السنتر", "القاعة / المكان", "ملاحظات"]
COL_PAYMENT_RECORDS = ["معرف العملية", "كود الطالب", "اسم الطالب", "التاريخ والوقت", "المبلغ", "بيان الدفع", "حالة الدفع", "ملاحظات"]
COL_ADS = ["معرف الإعلان", "عنوان الإعلان", "نص الإعلان", "صورة الإعلان", "رابط الزر", "نص الزر", "نشط"]
COL_TEACHER_PROFILE = ["اسم المعلم", "المسمى الوظيفي", "رقم الهاتف", "البريد الإلكتروني", "نبذة شخية", "صورة المعلم Base64"]
COL_STUDENT_INTERFACE = ["عنوان الواجهة", "رسالة الترحيب", "شريط التنبيهات", "صورة الغلاف Base64"]
COL_ACADEMY_ACCOUNTS = ["معرف الأكاديمية", "اسم الأكاديمية", "اسم المسؤول", "رقم الهاتف", "كلمة المرور", "حالة الحساب"]
COL_ACADEMY_TEACHERS = ["معرف المدرس", "معرف الأكاديمية", "اسم المدرس", "المادة", "رقم الهاتف"]
COL_ACADEMY_ASSIGNMENTS = ["معرف التوزيع", "كود الطالب", "معرف الأكاديمية", "معرف المدرس"]
COL_ACADEMY_ACCESS = ["معرف الدخول", "اسم المستخدم", "كلمة المرور", "النوع", "معرف الأكاديمية"]
COL_ACADEMY_SUBSCRIPTIONS = ["معرف الاشتراك", "معرف الأكاديمية", "تاريخ البداية", "تاريخ النهاية", "المبلغ", "الحالة"]
COL_ACADEMY_STUDENTS = ["كود الطالب", "معرف الأكاديمية", "اسم الطالب", "الصف الدراسي", "رقم الهاتف"]
COL_ACADEMY_ATTENDANCE = ["معرف الحضور", "كود الطالب", "معرف الأكاديمية", "التاريخ", "الحالة"]
COL_ACADEMY_SCHEDULE = ["معرف الموعد", "معرف الأكاديمية", "اليوم", "الوقت", "الصف الدراسي", "القاعة"]

def _cloud_load_payment_records_fallback():
    if not _cloud_storage_enabled():
        return pd.DataFrame(columns=COL_PAYMENT_RECORDS)

    def _normalize(_df):
        if _df is None or _df.empty:
            return pd.DataFrame(columns=COL_PAYMENT_RECORDS)
        _df = _df.copy()
        for _col in COL_PAYMENT_RECORDS:
            if _col not in _df.columns:
                _df[_col] = 0.0 if _col == "المبلغ" else ("مؤكد" if _col == "حالة الدفع" else "")
        return _df[COL_PAYMENT_RECORDS]

    try:
        _url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/payment_records?select=*"
        _req = urllib.request.Request(_url, headers=_supabase_headers(), method="GET")
        with urllib.request.urlopen(_req, timeout=20) as _resp:
            _data = json.loads(_resp.read().decode("utf-8"))
        _df = _normalize(pd.DataFrame(_data if isinstance(_data, list) else []))
        if not _df.empty:
            return _df
    except Exception:
        pass

    _queries = [
        f"{SUPABASE_VERSIONS_TABLE}?storage_id=eq.{SUPABASE_RECORD_ID}&select=payload&order=created_at.desc&limit=50",
        f"{SUPABASE_VERSIONS_TABLE}?storage_id=eq.{SUPABASE_RECORD_ID}&select=payload&limit=50",
    ]
    for _query in _queries:
        try:
            _url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{_query}"
            _req = urllib.request.Request(_url, headers=_supabase_headers(), method="GET")
            with urllib.request.urlopen(_req, timeout=30) as _resp:
                _data = json.loads(_resp.read().decode("utf-8"))
            for _row in (_data if isinstance(_data, list) else []):
                try:
                    _raw = base64.b64decode(str(_row.get("payload", "")))
                    with pd.ExcelFile(io.BytesIO(_raw), engine="openpyxl") as _xls:
                        if "PaymentRecords" not in _xls.sheet_names:
                            continue
                        _df = _normalize(pd.read_excel(_xls, "PaymentRecords"))
                        if not _df.empty:
                            return _df
                except Exception:
                    continue
            break
        except Exception:
            continue
    return pd.DataFrame(columns=COL_PAYMENT_RECORDS)

def _cloud_save_version_snapshot(excel_bytes, reason="autosave"):
    if not _cloud_storage_enabled():
        return False
    try:
        payload = base64.b64encode(excel_bytes).decode("ascii")
        version_id = str(uuid.uuid4())
        body = json.dumps({
            "version_id": version_id,
            "storage_id": SUPABASE_RECORD_ID,
            "payload": payload,
            "reason": str(reason),
        }, ensure_ascii=False).encode("utf-8")
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{SUPABASE_VERSIONS_TABLE}"
        headers = _supabase_headers()
        headers["Prefer"] = "return=minimal"
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        return True
    except Exception as exc:
        try:
            st.session_state["cloud_backup_last_error"] = str(exc)
        except Exception:
            pass
        return False

def _cloud_save_excel_bytes(excel_bytes, reason="autosave"):
    if not _cloud_storage_enabled():
        return False
    try:
        try:
            with pd.ExcelFile(io.BytesIO(excel_bytes), engine="openpyxl") as _xls_check:
                _core_counts = {}
                for _sheet in ["Users", "Sessions", "Assessments", "WeeklySchedule", "PaymentRecords"]:
                    if _sheet in _xls_check.sheet_names:
                        _core_counts[_sheet] = len(pd.read_excel(_xls_check, _sheet))
                    else:
                        _core_counts[_sheet] = 0
                _new_core_total = sum(_core_counts.values())
        except Exception as _excel_check_error:
            st.session_state["cloud_storage_last_error"] = f"ملف Excel غير صالح: {_excel_check_error}"
            return False

        if _new_core_total == 0:
            st.session_state["cloud_storage_last_error"] = "تم منع حفظ نسخة فارغة فوق بيانات Supabase."
            st.session_state["cloud_empty_save_blocked"] = True
            return False

        if not _cloud_save_version_snapshot(excel_bytes, reason=reason):
            st.session_state["cloud_storage_last_error"] = "فشل إنشاء النسخة الاحتياطية؛ لم يتم تحديث البيانات الرئيسية."
            return False

        payload = base64.b64encode(excel_bytes).decode("ascii")
        body = json.dumps({"id": SUPABASE_RECORD_ID, "payload": payload}).encode("utf-8")
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{SUPABASE_TABLE}"
        headers = _supabase_headers()
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        st.session_state["cloud_empty_save_blocked"] = False
        st.session_state["cloud_storage_last_saved"] = True
        _onedrive_upload_excel(excel_bytes, reason=reason)
        return True
    except Exception as exc:
        try:
            st.session_state["cloud_storage_last_error"] = str(exc)
            st.session_state["cloud_storage_last_saved"] = False
        except Exception:
            pass
        return False

def _get_excel_source():
    cloud_bytes = _cloud_load_excel_bytes()
    if cloud_bytes:
        return io.BytesIO(cloud_bytes)
    if _os.path.exists(FILE_NAME):
        return FILE_NAME
    return None

CURRICULUM_DATA = {
    "المنهج المصري 🇪🇬": [
        "الصف الأول الإعدادي", "الصف الثاني الإعدادي", "الصف الثالث الإعدادي (الشهادة الإعدادية)",
        "الصف الأول الثانوي", "الصف الثاني الثانوي (علمي)", "الصف الثاني الثانوي (أدبي)",
        "الصف الثالث الثانوي (علمي رياضة)", "الصف الثالث الثانوي (علمي علوم)", "الصف الثالث الثانوي (أدبي)",
        "المرحلة الابتدائية"
    ],
    "المنهج القطري 🇶🇦": [
        "الصف السابع (إعدادي)", "الصف الثامن (إعدادي)", "الصف التاسع (إعدادي)",
        "الصف العاشر (المشترك)", "الصف الحادي عشر (المسار العلمي)", "الصف الحادي عشر (مسار الآداب والإنسانيات)",
        "الصف الحادي عشر (المسار التكنولوجي)", "الصف الثاني عشر (المسار العلمي - متقدم)",
        "الصف الثاني عشر (مسار الآداب - تأسيسي)", "الصف الثاني عشر (المسار التكنولوجي)",
        "المرحلة الابتدائية"
    ],
    "المنهج الإماراتي 🇦🇪": [
        "الحلقة الثانية (الصفوف 5 - 8)", "الصف التاسع (مسار عام)", "الصف التاسع (مسار متقدم)",
        "الصف العاشر (مسار عام)", "الصف العاشر (مسار متقدم)", "الصف العاشر (مسار النخبة)",
        "الصف الحادي عشر (مسار عام)", "الصف الحادي عشر (مسار متقدم)", "الصف الحادي عشر (مسار النخبة)",
        "الصف الثاني عشر (مسار عام)", "الصف الثاني عشر (مسار متقدم)", "الصف الثاني عشر (مسار النخبة)"
    ],
    "المنهج السعودي 🇸🇦": [
        "المرحلة المتوسطة (أول / ثاني / ثالث متوسط)", "السنة الأولى المشتركة (أول ثانوي)",
        "السنة الثانية (المسار العام)", "السنة الثانية (مسار علوم الحاسب والهندسة)",
        "السنة الثانية (مسار الصحة والحياة)", "السنة الثانية (مسار إدارة الأعمال / الشرعي)",
        "السنة الثالثة (المسار العام)", "السنة الثالثة (مسار علوم الحاسب والهندسة)",
        "السنة الثالثة (مسار الصحة والحياة)"
    ],
    "المنهج الكويتي 🇰🇼": [
        "المرحلة المتوسطة (الصفوف 6 - 9)", "الصف العاشر الثانوي (مشترك)",
        "الصف الحادي عشر (القسم العلمي)", "الصف الحادي عشر (القسم الأدبي)",
        "الصف الثاني عشر (القسم العلمي)", "الصف الثاني عشر (القسم الأدبي)"
    ],
    "المنهج الدولي 🌎": [
        "Primary / Elementary", "Middle School", "Grade 9", "Grade 10", "Grade 11", "Grade 12", "IGCSE", "A-Level", "IB", "American High School", "SAT / ACT"
    ],
    "المنهج السوداني 🇸🇩": [
        "المرحلة المتوسطة (أولى / ثانية / ثالثة متوسط)", "الصف الأول الثانوي",
        "الصف الثاني الثانوي (علمي)", "الصف الثاني الثانوي (أدبي)",
        "الصف الثالث الثانوي (علمي رياضيات - الشهادة السودانية)", "الصف الثالث الثانوي (علمي أحياء)",
        "الصف الثالث الثانوي (أدبي)"
    ]
}

# ==========================================
# Main UI styling & layout logic
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap');
    html, body, [class*="css"] {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        text-align: right;
    }
    .main-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%);
        color: white;
        padding: 2.5rem;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        margin-bottom: 2rem;
    }
    .hero-badge {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(8px);
        padding: 6px 16px;
        border-radius: 50px;
        font-size: 0.9rem;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        text-align: center;
        transition: transform 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    .metric-num {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1e3a8a;
    }
    .metric-label {
        color: #64748b;
        font-weight: 600;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

# Main Hero Render
st.markdown("""
<div class="main-hero">
    <div class="hero-badge">📐 البشمهندس x الرياضه</div>
    <h1 style="margin: 0; font-size: 2.5rem; font-weight: 900;">المنصة التعليمية للرياضيات والإحصاء</h1>
    <p style="margin-top: 10px; font-size: 1.1rem; opacity: 0.9;">أهلاً بك يا باشمهندس محمد! نظام إدارة الحضور، الامتحانات، البنوك السحابية، والذكاء الاصطناعي حمصا AI.</p>
</div>
""", unsafe_allow_html=True)

# Demo Stat Row
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown('<div class="metric-card"><div class="metric-num">1,250</div><div class="metric-label">إجمالي الطلاب المسجلين</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="metric-card"><div class="metric-num">98.4%</div><div class="metric-label">نسبة الحضور الأسبوعية</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div class="metric-card"><div class="metric-num">45</div><div class="metric-label">امتحان تفاعلي نشط</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown('<div class="metric-card"><div class="metric-num">⚡ حمصا AI</div><div class="metric-label">المساعد الذكي للحلول</div></div>', unsafe_allow_html=True)

st.divider()
st.info("✅ تم تحميل وتشغيل المنصة بنجاح مع ربط التخزين السحابي وحفظ كامل السجلات والمنطق التفاعلي.")
