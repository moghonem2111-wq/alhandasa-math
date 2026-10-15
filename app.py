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
        with urllib.request.urlopen(req, timeout=30) as resp: return json.loads(resp.read().decode()).get("access_token")
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
        with urllib.request.urlopen(req, timeout=60) as resp: data=json.loads(resp.read().decode())
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
        with urllib.request.urlopen(req, timeout=30) as resp: return json.loads(resp.read().decode())
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

def _cloud_load_academy_login_records():
    if not _cloud_storage_enabled():
        return pd.DataFrame(columns=COL_ACADEMY_ACCESS), pd.DataFrame(columns=COL_ACADEMY_ACCOUNTS)
    def _get(table, cols):
        try:
            url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}?select=*"
            req = urllib.request.Request(url, headers=_supabase_headers(), method="GET")
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            df = pd.DataFrame(data if isinstance(data, list) else [])
            for col in cols:
                if col not in df.columns:
                    df[col] = ""
            return df[cols]
        except Exception as exc:
            st.session_state["academy_login_cloud_error"] = str(exc)
            return pd.DataFrame(columns=cols)
    return _get("academy_access", COL_ACADEMY_ACCESS), _get("academy_accounts", COL_ACADEMY_ACCOUNTS)

def _cloud_sync_dataframe(table_name, df, label=None):
    if not _cloud_storage_enabled():
        return True
    label = label or table_name
    try:
        if df is None:
            df = pd.DataFrame()
        work = df.copy()
        if not work.empty:
            work.columns = [str(c) for c in work.columns]
            records = json.loads(work.to_json(orient="records", force_ascii=False, date_format="iso"))
        else:
            records = []

        sig_source = work.copy()
        try:
            sig_source.columns = [str(c) for c in sig_source.columns]
            for col in sig_source.columns:
                sig_source[col] = sig_source[col].map(lambda x: "" if pd.isna(x) else str(x))
            raw_sig = pd.util.hash_pandas_object(sig_source, index=True).values.tobytes()
            signature = hashlib.sha256(
                (table_name + "|" + "|".join(sig_source.columns) + "|" + str(len(sig_source))).encode("utf-8") + raw_sig
            ).hexdigest()
        except Exception:
            signature = hashlib.sha256(repr(records).encode("utf-8")).hexdigest()

        cache_key = f"_structured_sync_sig_{table_name}"
        if st.session_state.get(cache_key) == signature:
            return True

        base_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table_name}"
        delete_url = base_url + "?id=not.is.null"
        delete_headers = _supabase_headers()
        delete_headers["Prefer"] = "return=minimal"
        req = urllib.request.Request(delete_url, headers=delete_headers, method="DELETE")
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()

        if records:
            batch_size = 10 if any("base64" in str(c).lower() for c in work.columns) else 50
            for start in range(0, len(records), batch_size):
                batch = records[start:start + batch_size]
                body = json.dumps(batch, ensure_ascii=False, allow_nan=False).encode("utf-8")
                headers = _supabase_headers()
                headers["Prefer"] = "return=minimal"
                req = urllib.request.Request(base_url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=60) as resp:
                    resp.read()

        st.session_state[cache_key] = signature
        st.session_state["structured_sync_last_error"] = ""
        return True
    except Exception as exc:
        st.session_state["structured_sync_last_error"] = f"{label}: {exc}"
        return False

def _cloud_sync_all_structured_tables(users_df, sessions_df, assessments_df, messages_df,
                                      exams_df, essays_df, bookings_df, bank_requests_df,
                                      question_bank_df, videos_df, video_comments_df, abqary_df,
                                      online_schedule_df, weekly_schedule_df, payment_records_df,
                                      ads_df):
    tables = [
        ("users", users_df, "الطلاب"),
        ("sessions", sessions_df, "الحصص والحضور"),
        ("assessments", assessments_df, "الواجبات والتقييمات"),
        ("messages", messages_df, "الرسائل"),
        ("exams", exams_df, "الامتحانات"),
        ("essays", essays_df, "الحلول المقالية"),
        ("bookings", bookings_df, "الحجوزات"),
        ("bank_requests", bank_requests_df, "طلبات البنك"),
        ("question_bank", question_bank_df, "بنك الأسئلة"),
        ("videos", videos_df, "الفيديوهات"),
        ("video_comments", video_comments_df, "تعليقات الفيديو"),
        ("abqary", abqary_df, "عبقري"),
        ("online_schedule", online_schedule_df, "جداول Zoom"),
        ("weekly_schedule", weekly_schedule_df, "المواعيد الأسبوعية"),
        ("payment_records", payment_records_df, "المدفوعات"),
        ("ads", ads_df, "الإعلانات"),
    ]
    teacher_profile_df = st.session_state.get("teacher_profile_df", pd.DataFrame(columns=COL_TEACHER_PROFILE))
    student_interface_df = st.session_state.get("student_interface_df", pd.DataFrame(columns=COL_STUDENT_INTERFACE))
    tables.extend([
        ("teacher_profile", teacher_profile_df, "بيانات المعلم"),
        ("student_interface", student_interface_df, "واجهة الطالب"),
        ("academy_accounts", st.session_state.get("academy_accounts_df", pd.DataFrame(columns=COL_ACADEMY_ACCOUNTS)), "حسابات الأكاديميات"),
        ("academy_teachers", st.session_state.get("academy_teachers_df", pd.DataFrame(columns=COL_ACADEMY_TEACHERS)), "مدرسو الأكاديميات"),
        ("academy_assignments", st.session_state.get("academy_assignments_df", pd.DataFrame(columns=COL_ACADEMY_ASSIGNMENTS)), "توزيع طلاب الأكاديميات"),
        ("academy_access", st.session_state.get("academy_access_df", pd.DataFrame(columns=COL_ACADEMY_ACCESS)), "دخول الأكاديميات والمشرفين"),
        ("academy_subscriptions", st.session_state.get("academy_subscriptions_df", pd.DataFrame(columns=COL_ACADEMY_SUBSCRIPTIONS)), "اشتراكات الأكاديميات"),
        ("academy_students", st.session_state.get("academy_students_df", pd.DataFrame(columns=COL_ACADEMY_STUDENTS)), "طلاب الأكاديميات"),
        ("academy_attendance", st.session_state.get("academy_attendance_df", pd.DataFrame(columns=COL_ACADEMY_ATTENDANCE)), "حضور الأكاديميات"),
        ("academy_schedule", st.session_state.get("academy_schedule_df", pd.DataFrame(columns=COL_ACADEMY_SCHEDULE)), "جداول الأكاديميات"),
    ])
    results = []
    for table_name, df, label in tables:
        results.append(_cloud_sync_dataframe(table_name, df, label))
    return all(results)

def _cloud_load_student_interface():
    if not _cloud_storage_enabled():
        return None
    try:
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{SUPABASE_INTERFACE_TABLE}?id=eq.{SUPABASE_RECORD_ID}&select=payload"
        req = urllib.request.Request(url, headers=_supabase_headers(), method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8
