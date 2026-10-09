"""Shareable HTML and native exams for the Alhandasa Streamlit platform.

HTML is presentation-only and is sanitized before display. To make a custom HTML
exam interactive, include a JSON manifest in:
<script type="application/json" id="exam-questions">{"questions":[...]}</script>
The answer key remains server-side and is never sent to student pages.
"""
import html
import json
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, time as dt_time, timedelta, timezone
from zoneinfo import ZoneInfo
from html.parser import HTMLParser

import streamlit as st

EXAMS_TABLE = "html_exams"
ATTEMPTS_TABLE = "html_exam_submissions"


def _now():
    return datetime.now(timezone.utc)


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else str(value or "")


def _cairo_datetime(day, clock):
    return datetime.combine(day, clock).replace(tzinfo=ZoneInfo("Africa/Cairo")).astimezone(timezone.utc).isoformat()


def _exam_window(exam):
    now = _now()
    starts = datetime.fromisoformat(str(exam.get("starts_at") or "").replace("Z", "+00:00")) if exam.get("starts_at") else None
    ends = datetime.fromisoformat(str(exam.get("ends_at") or "").replace("Z", "+00:00")) if exam.get("ends_at") else None
    if starts and starts.tzinfo is None: starts = starts.replace(tzinfo=timezone.utc)
    if ends and ends.tzinfo is None: ends = ends.replace(tzinfo=timezone.utc)
    if starts and now < starts: return "upcoming", starts
    if ends and now > ends: return "ended", ends
    return "open", None


def _report_html(exam, attempt):
    answers = attempt.get("answers") or {}
    details = []
    review_count = 0
    for i, q in enumerate(exam.get("questions") or [], 1):
        student = str(answers.get(q.get("id", ""), "") or "—")
        correct = str(q.get("answer", "") or "غير محددة")
        ok = bool(q.get("answer", "").strip()) and student.strip().casefold() == correct.strip().casefold()
        if not ok: review_count += 1
        details.append("<section><h3>" + str(i) + ". " + html.escape(str(q.get("question", ""))) + "</h3><p><b>إجابة الطالب:</b> " + html.escape(student) + "</p><p><b>الإجابة النموذجية:</b> " + html.escape(correct) + "</p><p><b>التقييم:</b> " + ("صحيح" if ok else "يحتاج مراجعة") + "</p></section>")
    score = float(attempt.get("score") or 0)
    maximum = float(attempt.get("max_score") or 0)
    pct = round(score / maximum * 100) if maximum else 0
    return "<!doctype html><html lang='ar' dir='rtl'><meta charset='utf-8'><title>تقرير الطالب</title><style>body{font-family:Arial;margin:24px;color:#172033}header{background:#0b2b58;color:white;padding:20px;border-radius:12px}section,.meta div{border:1px solid #ccd6e3;padding:12px;border-radius:9px;margin:10px 0}.meta{display:grid;grid-template-columns:1fr 1fr;gap:8px}@media print{body{margin:10mm}}</style><header><h1>تقرير مستوى الطالب</h1><h2>" + html.escape(str(exam.get("title", ""))) + "</h2></header><div class='meta'><div><b>الطالب:</b> " + html.escape(str(attempt.get("student_name", ""))) + "</div><div><b>المرحلة:</b> " + html.escape(str(exam.get("stage", "—") or "—")) + "</div><div><b>المنهج:</b> " + html.escape(str(exam.get("curriculum", "—") or "—")) + "</div><div><b>الدرجة:</b> " + str(score) + " / " + str(maximum) + " (" + str(pct) + "%)</div><div><b>بدأ:</b> " + html.escape(str(attempt.get("started_at", "—"))) + "</div><div><b>سلّم:</b> " + html.escape(str(attempt.get("submitted_at", "—"))) + "</div><div><b>أسئلة تحتاج مراجعة:</b> " + str(review_count) + "</div></div>" + "".join(details) + "<script>window.onload=()=>window.print()</script></html>"


def _api(url, key, method="GET", payload=None, query=""):
    if not url or not key:
        raise RuntimeError("أضف SUPABASE_SERVICE_ROLE_KEY إلى Secrets لاستخدام الاختبارات المشتركة.")
    base = url.rstrip("/") + "/rest/v1/"
    endpoint = base + query
    headers = {
        "apikey": key,
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else []
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:700]
        if exc.code in (401, 403):
            raise RuntimeError("صلاحيات Supabase غير كافية. أضف مفتاح Service Role في Secrets وتأكد من تشغيل ملف SQL المرفق.") from exc
        if exc.code == 404 or "does not exist" in detail:
            raise RuntimeError("جداول الاختبارات غير موجودة. شغّل ملف html_exam_schema.sql في Supabase SQL Editor.") from exc
        raise RuntimeError("خطأ Supabase: " + detail) from exc


def _list_exams(url, key):
    return _api(url, key, query=f"{EXAMS_TABLE}?select=*&order=created_at.desc")


def _get_exam(url, key, exam_id):
    rows = _api(url, key, query=f"{EXAMS_TABLE}?id=eq.{urllib.parse.quote(str(exam_id), safe='')}&select=*&limit=1")
    return rows[0] if rows else None


def _save_exam(url, key, exam):
    found = _get_exam(url, key, exam["id"])
    if found:
        _api(url, key, "PATCH", {k: v for k, v in exam.items() if k != "id"},
             f"{EXAMS_TABLE}?id=eq.{urllib.parse.quote(exam['id'], safe='')}")
    else:
        _api(url, key, "POST", exam, EXAMS_TABLE)
    return True


def _list_attempts(url, key, exam_id=None):
    query = f"{ATTEMPTS_TABLE}?select=*&order=started_at.desc"
    if exam_id:
        query = f"{ATTEMPTS_TABLE}?exam_id=eq.{urllib.parse.quote(str(exam_id), safe='')}&select=*&order=started_at.desc"
    return _api(url, key, query=query)


def _get_attempt_by_token(url, key, token, field):
    if field not in ("result_token", "review_token", "id"):
        return None
    rows = _api(url, key, query=f"{ATTEMPTS_TABLE}?{field}=eq.{urllib.parse.quote(str(token), safe='')}&select=*&limit=1")
    return rows[0] if rows else None


def _save_attempt(url, key, attempt, insert=False):
    if insert:
        _api(url, key, "POST", attempt, ATTEMPTS_TABLE)
    else:
        _api(url, key, "PATCH", {k: v for k, v in attempt.items() if k not in ("id", "exam_id")},
             f"{ATTEMPTS_TABLE}?id=eq.{urllib.parse.quote(attempt['id'], safe='')}")
    return True


def _questions_from_html(code):
    """Read the explicit JSON manifest; never execute teacher-supplied JavaScript."""
    patterns = [
        r'<script[^>]*id=["\']exam-questions["\'][^>]*>(.*?)</script\s*>',
        r'<script[^>]*type=["\']application/json["\'][^>]*id=["\']exam-questions["\'][^>]*>(.*?)</script\s*>',
    ]
    raw = None
    for pattern in patterns:
        match = re.search(pattern, code or "", re.I | re.S)
        if match:
            raw = match.group(1).strip()
            break
    if raw is None and str(code or "").strip().startswith("{"):
        raw = str(code).strip()
    if not raw:
        return []
    data = json.loads(raw)
    questions = data.get("questions", data) if isinstance(data, dict) else data
    if not isinstance(questions, list):
        raise ValueError("صيغة الأسئلة داخل كود HTML غير صحيحة.")
    return _normalize_questions(questions)



def _questions_from_images(files):
    """Convert uploaded exam images to a reviewable question manifest using the platform AI helper."""
    if not files:
        raise ValueError("ارفع صورة واحدة على الأقل.")
    try:
        from ai_studio import call as _gemini_call
        packed = []
        for uploaded in files:
            name = str(getattr(uploaded, "name", "") or "question.jpg")
            kind = "pdf" if name.lower().endswith(".pdf") else "image"
            packed.append((kind, name, uploaded.getvalue()))
        prompt = """
اقرأ صور ورقة امتحان الرياضيات واستخرج الأسئلة الموجودة فعلاً فقط. حافظ على نص الأسئلة والأرقام والرموز والاختيارات كما تظهر، ولا تخترع أسئلة. أعد JSON صالحاً فقط بالشكل:
{"questions":[{"question":"نص السؤال مع LaTeX عند الحاجة","type":"mcq","options":["أ","ب","ج","د"],"answer":"","points":1}]}
استخدم type=mcq للاختيار من متعدد وtype=short لغير ذلك. اكتب المعادلات بصيغة LaTeX بين $...$ عند الحاجة. إذا لم تكن الإجابة واضحة اترك answer فارغاً. رتّب الأسئلة حسب الصور ولا تكتب أي شرح خارج JSON.
"""
        parsed = _gemini_call(prompt, packed)
        items = parsed.get("questions", parsed) if isinstance(parsed, dict) else parsed
        return _normalize_questions(items)
    except Exception as exc:
        raise RuntimeError("تعذر استخراج الأسئلة بالذكاء الاصطناعي. تأكد من عمل GEMINI_API_KEY ثم حاول مجدداً. " + str(exc)[:250]) from exc


def _normalize_questions(items):
    out = []
    for i, item in enumerate(items, 1):
        if not isinstance(item, dict):
            continue
        qtype = str(item.get("type", "mcq")).lower()
        if qtype not in ("mcq", "short", "text"):
            qtype = "mcq"
        question = str(item.get("question", item.get("text", ""))).strip()
        if not question:
            continue
        options = item.get("options", [])
        if isinstance(options, str):
            options = [x.strip() for x in options.split("|") if x.strip()]
        if not isinstance(options, list):
            options = []
        out.append({
            "id": str(item.get("id") or f"q{i}"),
            "question": question,
            "type": qtype,
            "options": [str(x) for x in options],
            "answer": str(item.get("answer", item.get("correct_answer", ""))).strip(),
            "points": max(0.0, float(item.get("points", 1) or 1)),
        })
    if not out:
        raise ValueError("أضف سؤالاً واحداً على الأقل.")
    return out


class _SafeHTML(HTMLParser):
    """Conservative HTML sanitizer: no scripts, event handlers, forms or external loads."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    DROP = {"script", "iframe", "object", "embed", "form", "button", "input", "textarea", "select", "option", "video", "audio", "link", "meta", "base"}
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []
        self.drop_depth = 0
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.DROP:
            self.drop_depth += 1
            return
        if self.drop_depth:
            return
        allowed = []
        for key, value in attrs:
            key = key.lower()
            value = value or ""
            if key.startswith("on") or key in ("srcdoc", "formaction", "action"):
                continue
            if key in ("src", "href") and re.match(r"(?i)\s*(javascript:|data:|https?://|//)", value):
                continue
            if key not in ("class", "id", "style", "title", "dir", "lang", "href", "src", "alt", "width", "height", "colspan", "rowspan"):
                continue
            allowed.append(f' {key}="{html.escape(value, quote=True)}"')
        self.parts.append("<" + tag + "".join(allowed) + ">")
    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.DROP:
            if self.drop_depth:
                self.drop_depth -= 1
            return
        if not self.drop_depth and tag not in self.VOID:
            self.parts.append(f"</{tag}>")
    def handle_data(self, data):
        if not self.drop_depth:
            self.parts.append(data)
    def handle_entityref(self, name):
        if not self.drop_depth:
            self.parts.append(f"&{name};")
    def handle_charref(self, name):
        if not self.drop_depth:
            self.parts.append(f"&#{name};")


def _safe_html(code):
    parser = _SafeHTML()
    try:
        parser.feed(str(code or ""))
        return "".join(parser.parts)
    except Exception:
        return "<div dir='rtl'>تعذر عرض تصميم HTML؛ ستظل الأسئلة قابلة للإجابة أدناه.</div>"


def _base_url():
    # Do not mutate the current query string: the student may be inside an active exam.
    return "https://engmohamedghonaim.streamlit.app/"


def _link(kind, token):
    return _base_url() + "?" + urllib.parse.urlencode({kind: token})


def _share_link(label, url, key):
    c1, c2 = st.columns([4, 1])
    with c1:
        st.code(url, language=None)
    with c2:
        st.button("📋 نسخ الرابط", key=key, on_click=lambda: st.session_state.update({"_copy_notice": url}))
    if st.session_state.get("_copy_notice") == url:
        st.caption("حدّد الرابط وانسخه من الخانة؛ يمكنك أيضاً فتحه مباشرة.")


def _score(questions, answers):
    score = 0.0
    maximum = 0.0
    for q in questions:
        points = float(q.get("points", 1) or 1)
        maximum += points
        if q.get("type") == "mcq":
            if str(answers.get(q["id"], "")).strip() == str(q.get("answer", "")).strip():
                score += points
        elif str(answers.get(q["id"], "")).strip().casefold() == str(q.get("answer", "")).strip().casefold():
            score += points
    return round(score, 2), round(maximum, 2)


def _public_exam_page(url, key, exam_id, attempt_id_from_url=""):
    exam = _get_exam(url, key, exam_id)
    if not exam or not exam.get("active", True):
        st.error("الاختبار غير موجود أو تم إيقافه من المعلم.")
        return True
    st.markdown(f"<div dir='rtl' style='background:linear-gradient(120deg,#0b1f42,#1769cf);padding:22px;border-radius:18px;color:white'><h1 style='margin:0'>{html.escape(exam['title'])}</h1><p>اختبار إلكتروني · المدة {int(exam.get('duration_minutes',30))} دقيقة</p></div>", unsafe_allow_html=True)
    attempt_id_from_url = str(attempt_id_from_url or "").strip()
    attempt_id_session = st.session_state.get("_hexam_verified_" + exam_id, "")
    attempt_id = attempt_id_from_url or attempt_id_session
    if not attempt_id:
        window_state, boundary = _exam_window(exam)
        if window_state == "upcoming":
            st.info("الاختبار لم يبدأ بعد. موعد البدء بتوقيت القاهرة: " + boundary.astimezone(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d %I:%M %p"))
            return True
        if window_state == "ended":
            st.error("انتهت فترة إتاحة هذا الاختبار. تواصل مع المدرس.")
            return True
        with st.form("html_exam_entry_form"):
            name = st.text_input("اسم الطالب الثلاثي", placeholder="اكتب اسمك الثلاثي")
            code = st.text_input("كود الاختبار", type="password")
            go = st.form_submit_button("🚀 ابدأ الامتحان", type="primary", use_container_width=True)
        if go:
            if len([p for p in name.strip().split() if p]) < 3:
                st.error("من فضلك اكتب الاسم الثلاثي.")
            elif not secrets.compare_digest(str(code).strip(), str(exam.get("access_code", ""))):
                st.error("كود الاختبار غير صحيح.")
            else:
                existing = _list_attempts(url, key, exam_id)
                duplicate = next((a for a in existing if str(a.get("student_name","")).casefold() == name.strip().casefold() and a.get("status") == "submitted"), None)
                if duplicate:
                    st.error("تم تسليم محاولة بهذا الاسم بالفعل. تواصل مع المعلم إذا كنت تحتاج إعادة المحاولة.")
                else:
                    attempt_id = uuid.uuid4().hex
                    now = _now()
                    attempt = {
                        "id": attempt_id, "exam_id": exam_id, "student_name": name.strip(),
                        "answers": {}, "score": 0, "max_score": 0, "status": "started",
                        "started_at": now.isoformat(), "submitted_at": None,
                        "result_token": secrets.token_urlsafe(24), "review_token": secrets.token_urlsafe(24),
                    }
                    _save_attempt(url, key, attempt, insert=True)
                    st.session_state["_hexam_verified_" + exam_id] = attempt_id
                    st.query_params["hattempt"] = attempt_id
                    st.rerun()
        return True

    st.session_state["_hexam_verified_" + exam_id] = attempt_id
    attempts = _list_attempts(url, key, exam_id)
    attempt = next((a for a in attempts if a.get("id") == attempt_id), None)
    if not attempt:
        st.session_state.pop("_hexam_verified_" + exam_id, None)
        st.error("انتهت جلسة الاختبار. افتح الرابط من جديد.")
        return True
    if attempt.get("status") == "submitted":
        st.success("تم تسليم هذا الاختبار بالفعل.")
        st.markdown("### رابط النتيجة")
        st.code(_link("hresult", attempt["result_token"]), language=None)
        st.markdown("### رابط مراجعة الإجابات")
        st.code(_link("hreview", attempt["review_token"]), language=None)
        return True
    questions = exam.get("questions", [])
    if exam.get("html_code"):
        safe = _safe_html(exam["html_code"])
        if safe.strip():
            st.components.v1.html("<div dir='rtl' style='font-family:Arial;'>" + safe + "</div>", height=180, scrolling=True)
    st.markdown(f"<div dir='rtl' style='margin:18px 0 12px;padding:12px 16px;border-radius:14px;background:#eff6ff;border:1px solid #bfdbfe;color:#12355f;font-weight:700'>👤 الطالب: {html.escape(attempt['student_name'])}<span style='float:left;color:#1769cf'>📘 {len(questions)} سؤال</span></div>", unsafe_allow_html=True)
    st.markdown("""
    <style>
    div[data-testid="stVerticalBlockBorderWrapper"] {border-color:#dbe5f0!important;border-radius:16px!important}
    .exam-q-label {font-size:12px;font-weight:800;color:#1769cf;letter-spacing:.2px}
    </style>
    """, unsafe_allow_html=True)
    for i, q in enumerate(questions, 1):
        with st.container(border=True):
            st.markdown(f"<div dir='rtl' class='exam-q-label'>السؤال {i} <span style='float:left'>{q.get('points',1)} درجة</span></div>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown(q["question"])
            widget_key = f"hexam_{exam_id}_{attempt_id}_{q['id']}"
            if q.get("type") == "mcq" and q.get("options"):
                st.radio("اختر الإجابة:", q["options"], index=None, key=widget_key, label_visibility="collapsed",
                         on_change=_persist_one_answer, args=(url, key, attempt_id, q["id"], widget_key))
            else:
                st.text_input("اكتب إجابتك هنا:", key=widget_key, on_change=_persist_one_answer,
                              args=(url, key, attempt_id, q["id"], widget_key))
    _render_timer(url, key, exam, attempt)
    if st.button("📨 تسليم الاختبار", type="primary", use_container_width=True, key=f"hexam_submit_{attempt_id}"):
        latest = _get_attempt_by_token(url, key, attempt_id, "id") or attempt
        _submit_current_attempt(url, key, exam, latest, latest.get("answers") or {})
        st.rerun()
    st.caption("تُحفظ الإجابات تلقائياً أثناء الحل. لا تغلق الصفحة قبل ظهور رسالة التسليم.")


def _persist_one_answer(url, key, attempt_id, question_id, widget_key):
    try:
        attempt = _get_attempt_by_token(url, key, attempt_id, "id")
        if not attempt or attempt.get("status") != "started":
            return
        answers = dict(attempt.get("answers") or {})
        answers[str(question_id)] = st.session_state.get(widget_key, "")
        attempt["answers"] = answers
        _save_attempt(url, key, attempt, insert=False)
    except Exception as exc:
        st.session_state["_hexam_answer_save_error"] = str(exc)


@st.fragment(run_every="1s")
def _render_timer(url, key, exam, attempt):
    current = _get_attempt_by_token(url, key, attempt["id"], "id") or attempt
    if current.get("status") == "submitted":
        st.success("تم تسليم الاختبار.")
        return
    started = datetime.fromisoformat(str(current["started_at"]).replace("Z", "+00:00")).astimezone(timezone.utc)
    elapsed = max(0, int((_now() - started).total_seconds()))
    remaining = max(0, int(exam.get("duration_minutes", 30)) * 60 - elapsed)
    st.markdown(f"### ⏱️ الوقت المتبقي: {remaining // 60:02d}:{remaining % 60:02d}")
    if remaining <= 0:
        _submit_current_attempt(url, key, exam, current, current.get("answers") or {})
        st.rerun()


def _submit_current_attempt(url, key, exam, attempt, answers):
    score, maximum = _score(exam.get("questions", []), answers)
    attempt["answers"] = answers
    attempt["score"] = score
    attempt["max_score"] = maximum
    attempt["status"] = "submitted"
    attempt["submitted_at"] = _now().isoformat()
    _save_attempt(url, key, attempt, insert=False)
    st.session_state["_last_exam_result_links"] = {
        "result": _link("hresult", attempt["result_token"]),
        "review": _link("hreview", attempt["review_token"]),
    }


def _public_result_page(url, key, token, review=False):
    field = "review_token" if review else "result_token"
    attempt = _get_attempt_by_token(url, key, token, field)
    if not attempt:
        st.error("الرابط غير صحيح أو لم يعد متاحاً.")
        return True
    exam = _get_exam(url, key, attempt["exam_id"])
    if not exam:
        st.error("الاختبار غير موجود.")
        return True
    if attempt.get("status") != "submitted":
        st.info("لم يتم تسليم الاختبار بعد.")
        return True
    st.markdown(f"<div dir='rtl' style='background:#eff6ff;border:1px solid #bfdbfe;padding:20px;border-radius:16px'><h2>{html.escape(exam['title'])}</h2><p>الطالب: <b>{html.escape(attempt['student_name'])}</b></p><h1>{attempt.get('score',0)} / {attempt.get('max_score',0)}</h1><p>وقت التسليم: {html.escape(str(attempt.get('submitted_at','')))}</p></div>", unsafe_allow_html=True)
    if review:
        st.markdown("### مراجعة الإجابات")
        answers = attempt.get("answers") or {}
        for i, q in enumerate(exam.get("questions", []), 1):
            student_answer = str(answers.get(q["id"], "") or "—")
            correct = str(q.get("answer", "") or "—")
            is_correct = student_answer.strip().casefold() == correct.strip().casefold()
            st.markdown(f"**{i}. {q['question']}**")
            st.write("إجابتك:", student_answer)
            st.write("الإجابة الصحيحة:", correct)
            st.caption("صحيح" if is_correct else "تحتاج مراجعة")
    st.caption("يمكنك طباعة الصفحة من المتصفح باستخدام Ctrl+P.")
    return True


def render_html_exam_portal(supabase_url, supabase_key, query_params):
    """Returns True when a shared exam/result/review route owns the current page."""
    if "hexam" in query_params:
        _public_exam_page(supabase_url, supabase_key, str(query_params["hexam"]), str(query_params.get("hattempt", "")))
        return True
    if "hresult" in query_params:
        _public_result_page(supabase_url, supabase_key, str(query_params["hresult"]), False)
        return True
    if "hreview" in query_params:
        _public_result_page(supabase_url, supabase_key, str(query_params["hreview"]), True)
        return True
    return False


def render_html_exam_admin(supabase_url, supabase_key, public_base_url):
    st.markdown("## 🧪 الاختبارات الإلكترونية القابلة للمشاركة")
    st.caption("أنشئ اختباراً بأسئلة المنصة أو الصق كود HTML. تنبيه: لتسجيل إجابات اختبار HTML المخصص، أضف بيان الأسئلة JSON داخل الكود كما هو موضح أدناه.")
    if not supabase_url or not supabase_key:
        st.error("إعداد Supabase غير مكتمل. أضف SUPABASE_URL وSUPABASE_SERVICE_ROLE_KEY في Streamlit Secrets.")
        return
    tab_create, tab_manage, tab_results = st.tabs(["➕ إنشاء اختبار", "🔗 إدارة الروابط", "📊 كشف الدرجات"])
    with tab_create:
        mode = st.radio("طريقة إنشاء الاختبار", ["بناء الأسئلة داخل المنصة", "تحويل صور الأسئلة بالذكاء الاصطناعي", "كود HTML جاهز"], horizontal=True, key="hexam_mode")
        if mode == "تحويل صور الأسئلة بالذكاء الاصطناعي":
            image_files = st.file_uploader("📷 ارفع صور ورقة الأسئلة", type=["png", "jpg", "jpeg", "webp", "pdf"], accept_multiple_files=True, key="hexam_ai_images")
            st.caption("سيحوّل Gemini الصور إلى أسئلة قابلة للتعديل. راجع النص والإجابات قبل النشر.")
            if st.button("✨ استخراج الأسئلة من الصور", type="secondary", use_container_width=True, key="hexam_ai_extract"):
                try:
                    with st.spinner("جاري قراءة الصور وتحويلها إلى أسئلة..."):
                        extracted = _questions_from_images(image_files or [])
                    st.session_state["hexam_ai_questions_json"] = json.dumps(extracted, ensure_ascii=False, indent=2)
                    st.success(f"تم استخراج {len(extracted)} سؤال. راجعها قبل الحفظ.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        with st.form("hexam_create_form", clear_on_submit=False):
            title = st.text_input("اسم الاختبار", placeholder="اختبار النهايات")
            stage = st.selectbox("المرحلة الدراسية", ["الصف الأول الثانوي", "الصف الثاني الثانوي", "الصف الثالث الثانوي", "الصف 12 قطري", "مرحلة أخرى"], key="hexam_stage")
            curriculum = st.text_input("المنهج / الوحدة / الدرس", placeholder="مثال: الرياضيات — مفهوم النهايات")
            access_code = st.text_input("الكود السري لدخول الطلاب", value=secrets.token_hex(3).upper(), key="hexam_access_code_input")
            duration = st.number_input("مدة الاختبار بالدقائق", min_value=1, max_value=300, value=30)
            start_default = (datetime.now(ZoneInfo("Africa/Cairo")) + timedelta(minutes=5)).replace(second=0, microsecond=0)
            start_day = st.date_input("تاريخ فتح الاختبار", value=start_default.date(), key="hexam_start_day")
            start_clock = st.time_input("وقت بدء الاختبار — القاهرة", value=start_default.time(), key="hexam_start_clock")
            end_default = start_default + timedelta(hours=3)
            end_day = st.date_input("تاريخ إغلاق الاختبار", value=end_default.date(), key="hexam_end_day")
            end_clock = st.time_input("وقت إغلاق الاختبار — القاهرة", value=end_default.time(), key="hexam_end_clock")
            if mode == "بناء الأسئلة داخل المنصة":
                question_json = st.text_area("الأسئلة بصيغة JSON", value='[{"question":"نص السؤال؟","type":"mcq","options":["أ","ب","ج","د"],"answer":"أ","points":1}]', height=180)
                html_code = ""
            elif mode == "تحويل صور الأسئلة بالذكاء الاصطناعي":
                question_json = st.text_area("الأسئلة المستخرجة — راجع وعدّل قبل النشر", value=st.session_state.get("hexam_ai_questions_json", '[{"question":"ارفع الصور ثم اضغط استخراج الأسئلة","type":"short","options":[],"answer":"","points":1}]'), height=260, key="hexam_ai_review_json")
                html_code = ""
            else:
                html_code = st.text_area("الصق كود HTML", height=260, placeholder="الصق كود HTML هنا. أضف script id='exam-questions' يحتوي JSON للأسئلة والتصحيح.")
                question_json = ""
            active = st.checkbox("نشر الاختبار فور الحفظ", value=True)
            save = st.form_submit_button("💾 حفظ ونشر الاختبار", type="primary", use_container_width=True)
        if save:
            try:
                if not title.strip():
                    raise ValueError("اكتب اسم الاختبار.")
                if mode in ("بناء الأسئلة داخل المنصة", "تحويل صور الأسئلة بالذكاء الاصطناعي"):
                    questions = _normalize_questions(json.loads(question_json))
                else:
                    if not html_code.strip():
                        raise ValueError("الصق كود HTML أولاً.")
                    questions = _questions_from_html(html_code)
                if not access_code.strip():
                    raise ValueError("اكتب الكود السري للاختبار.")
                starts_at = _cairo_datetime(start_day, start_clock)
                ends_at = _cairo_datetime(end_day, end_clock)
                if datetime.fromisoformat(ends_at) <= datetime.fromisoformat(starts_at):
                    raise ValueError("موعد الإغلاق يجب أن يكون بعد موعد الفتح.")
                exam_id = uuid.uuid4().hex[:16]
                exam = {
                    "id": exam_id, "title": title.strip(), "access_code": access_code.strip(),
                    "stage": stage, "curriculum": curriculum.strip(), "starts_at": starts_at, "ends_at": ends_at,
                    "duration_minutes": int(duration), "mode": "html" if mode == "كود HTML جاهز" else ("ai_images" if mode == "تحويل صور الأسئلة بالذكاء الاصطناعي" else "builder"),
                    "questions": questions, "html_code": html_code, "active": bool(active),
                    "created_at": _now().isoformat(),
                }
                _save_exam(supabase_url, supabase_key, exam)
                st.session_state["_hexam_new_link"] = _link("hexam", exam_id)
                st.session_state["_hexam_new_code"] = access_code.strip()
                st.success("تم حفظ الاختبار في Supabase.")
            except Exception as exc:
                st.error(str(exc))
        if st.session_state.get("_hexam_new_link"):
            st.markdown("### رابط الاختبار")
            st.code(st.session_state["_hexam_new_link"], language=None)
            st.caption("كود الدخول: " + str(st.session_state.get("_hexam_new_code", "")))
    with tab_manage:
        try:
            exams = _list_exams(supabase_url, supabase_key)
            if not exams:
                st.info("لا توجد اختبارات مشتركة بعد.")
            for exam in exams:
                with st.container(border=True):
                    st.markdown(f"**{html.escape(exam['title'])}** — {'منشور' if exam.get('active') else 'متوقف'}")
                    st.caption(f"المرحلة: {exam.get('stage','—')} · المنهج: {exam.get('curriculum','—')} · المدة: {exam.get('duration_minutes')} دقيقة · عدد الأسئلة: {len(exam.get('questions') or [])}")
                    st.caption(f"يفتح: {exam.get('starts_at','—')} · يغلق: {exam.get('ends_at','—')}")
                    st.code(_link("hexam", exam["id"]), language=None)
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("إيقاف/نشر", key="hexam_toggle_"+exam["id"]):
                            exam["active"] = not bool(exam.get("active", True))
                            _save_exam(supabase_url, supabase_key, exam)
                            st.rerun()
                    with c2:
                        if st.button("كشف هذا الاختبار", key="hexam_results_"+exam["id"]):
                            st.session_state["_hexam_selected_results"] = exam["id"]
                            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    with tab_results:
        try:
            exams = _list_exams(supabase_url, supabase_key)
            if not exams:
                st.info("لا توجد اختبارات لعرض نتائجها.")
            else:
                selected = st.selectbox("اختر الاختبار", [x["id"] for x in exams], format_func=lambda eid: next((x["title"] for x in exams if x["id"] == eid), eid), key="hexam_result_select")
                attempts = _list_attempts(supabase_url, supabase_key, selected)
                rows = []
                for a in attempts:
                    rows.append({"اسم الطالب": a.get("student_name",""), "الدرجة": a.get("score",0), "الدرجة النهائية": a.get("max_score",0), "الحالة": "تم التسليم" if a.get("status")=="submitted" else "بدأ ولم يسلم", "بدأ في": a.get("started_at",""), "سلّم في": a.get("submitted_at",""), "رابط النتيجة": _link("hresult",a.get("result_token","")), "رابط الإجابات": _link("hreview",a.get("review_token",""))})
                    if a.get("status") == "submitted":
                        report_exam = next((e for e in exams if e["id"] == selected), {})
                        report = _report_html(report_exam, a)
                        report_name = re.sub(r"[^\\w\\-]+", "_", str(a.get("student_name", "طالب")))
                        st.download_button("🖨️ طباعة تقرير: " + str(a.get("student_name", "طالب")), report.encode("utf-8"), file_name="تقرير_الطالب_" + report_name + ".html", mime="text/html", key="hexam_report_" + str(a.get("id", "")))
                if rows:
                    import pandas as pd
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.download_button("📥 تحميل كشف الدرجات CSV", df.to_csv(index=False).encode("utf-8-sig"), file_name="كشف_درجات_الاختبار.csv", mime="text/csv")
                    print_rows = "".join("<tr>"+"".join(f"<td>{html.escape(str(v))}</td>" for v in row.values())+"</tr>" for row in rows)
                    headers = "".join(f"<th>{html.escape(str(c))}</th>" for c in rows[0].keys())
                    print_html = f"<!doctype html><html dir='rtl' lang='ar'><meta charset='utf-8'><title>كشف الدرجات</title><style>body{{font-family:Arial;margin:24px}}h1{{text-align:center}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd6e3;padding:8px;text-align:right;word-break:break-word}}th{{background:#0b2b58;color:#fff}}@media print{{button{{display:none}}}}</style><h1>كشف درجات الاختبار</h1><table><tr>{headers}</tr>{print_rows}</table><script>window.onload=()=>window.print()</script></html>"
                    st.download_button("🖨️ نسخة كشف قابلة للطباعة", print_html.encode("utf-8"), file_name="كشف_الدرجات.html", mime="text/html")
                    st.caption("روابط مراجعة الإجابات والنتيجة موجودة لكل محاولة داخل الكشف ويمكن نسخها.")
                else:
                    st.info("لم يسلّم أي طالب هذا الاختبار بعد.")
        except Exception as exc:
            st.error(str(exc))
