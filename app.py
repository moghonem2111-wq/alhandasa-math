
def _hamza_secret(name):
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""

def _hamza_ai_call(user_text, media_items=None, history=None):
    """حمصا: مدرس رياضيات بالذكاء الاصطناعي من Google Gemini، يدعم النص والصور وملفات PDF."""
    key = _hamza_secret("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("AI_KEY_MISSING")

    preferred = _hamza_secret("GEMINI_MODEL").strip()
    # تجاهل أي موديل قديم محفوظ في Secrets مثل gemini-2.5-flash-lite.
    allowed_models = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
    ]
    models = []
    if preferred in allowed_models:
        models.append(preferred)
    for candidate in allowed_models:
        if candidate not in models:
            models.append(candidate)

    context = ""
    if history:
        context = "\n\n".join(
            f"الطالب: {str(h.get('student','')).strip()}\nحمصا: {str(h.get('assistant','')).strip()}"
            for h in history[-6:]
        )

    prompt = f"""
أنت "حمصا"، مدرس رياضيات وإحصاء داخل منصة تعليمية.
مهمتك حل المسألة الموجودة في رسالة الطالب أو الصورة/الملف المرفق، وليس البحث على الإنترنت.
لا تقل للطالب "ابحث" أو "سأبحث" ولا تستخدم أدوات بحث. اقرأ الصورة بنفسك وحل المسألة.

أخرج الإجابة التعليمية بهذا الترتيب:
1. "فهم السؤال"
2. "القانون أو الفكرة"
3. "الحل خطوة بخطوة"
4. "الإجابة النهائية"

قواعد الرياضيات:
- استخدم LaTeX بشكل صحيح ولا تكتب كلمات مثل frac أو sqrt بدلاً من الأمر الرياضي.
- المعادلات داخل السطر بين $...$، والمعادلات المستقلة في سطر كامل بين $$...$$.
- الكسور يجب أن تكون مثل $\frac{a}{b}$، والجذور مثل $\sqrt{x}$، والأسس مثل $x^2$ والمؤشرات مثل $a_1$.
- اجعل كل معادلة رياضية واتجاه الأرقام الرياضية LTR من اليسار إلى اليمين، حتى داخل شرح عربي.
- إذا كانت المسألة بالإنجليزية، حافظ على نصها واتجاهها LTR.
- إذا كانت المسألة بالعربية، اجعل الشرح RTL، مع إبقاء المعادلات والأرقام داخل $...$ أو $$...$$ باتجاه LTR.
- نظّم الحل بعناوين واضحة: فهم السؤال، القانون أو الفكرة، الحل خطوة بخطوة، الإجابة النهائية.
- لا تستخدم $ كعملة.
- لا تغيّر أرقام السؤال ولا تخمّن رقماً غير واضح؛ إذا كانت قيمة في الصورة غير مقروءة فعلاً اذكر ذلك بوضوح.
- لا تعطِ النتيجة فقط؛ اشرح طريقة الحل بالعربية المصرية المبسطة.

المحادثة السابقة:
{context or "لا توجد محادثة سابقة."}

رسالة الطالب:
{user_text.strip() or "حل المسألة الموجودة في الملف المرفق."}

اكتب الإجابة مباشرة كنص منظم، ولا تستخدم JSON ولا تغلف الإجابة داخل كود.
ابدأ بعنوان "فهم السؤال"، ثم "القانون أو الفكرة"، ثم "الحل خطوة بخطوة"، ثم "الإجابة النهائية".
ضع كل معادلة مستقلة في سطر بين $...$، والمعادلات داخل الشرح بين $...$.
"""
    parts = [{"text": prompt}]
    for item in (media_items or []):
        if not item or not item.get("data"):
            continue
        parts.append({
            "inline_data": {
                "mime_type": str(item.get("mime") or "image/jpeg"),
                "data": str(item["data"])
            }
        })

    # نستخدم GenerateContent بشكل بسيط ومتوافق: بدون responseSchema/JSON mode.
    # حمصا يطلب JSON من النموذج ونقوم بتحليله محلياً، مع إبقاء الصور/PDF كما هي.
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "maxOutputTokens": 4096,
            "temperature": 0.2
        }
    }

    last_error = ""
    for model in models:
        for attempt in range(3):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            req = urllib.request.Request(
                url,
                data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json", "x-goog-api-key": key},
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    raw = json.loads(resp.read().decode("utf-8"))

                candidates = raw.get("candidates") or []
                if not candidates:
                    raise RuntimeError("EMPTY_RESPONSE")
                content = candidates[0].get("content") or {}
                text_parts = content.get("parts") or []
                text = "".join(
                    str(p.get("text", ""))
                    for p in text_parts
                    if p.get("text") is not None
                ).strip()
                if not text:
                    raise RuntimeError("EMPTY_RESPONSE")

                text = text.replace(chr(96)*3 + "json", "").replace(chr(96)*3, "").strip()
                # نستخدم النص الخام مباشرة: هذا يمنع فشل التحليل بسبب اختلاف تنسيق JSON
                # ويترك LaTeX كما أرسله Gemini لعرض المعادلات والكسور بصورة صحيحة.
                return {
                    "answer": text,
                    "final_answer": "",
                    "topic": "رياضيات"
                }

            except urllib.error.HTTPError as ex:
                msg = ex.read().decode("utf-8", errors="ignore")
                last_error = f"HTTP {getattr(ex,'code',0)}: {msg[:700]}"
                status = getattr(ex, "code", 0)
                if status in (429, 500, 502, 503, 504):
                    import time
                    if attempt < 2:
                        time.sleep(2 ** (attempt + 1))
                        continue
                    break
                if status in (400, 401, 403, 404):
                    break
                if attempt < 2:
                    import time
                    time.sleep(2 ** (attempt + 1))
                    continue
