import base64,json,html,re,uuid
from datetime import date,datetime
from urllib import request
import streamlit as st
import pandas as pd
try:
 from weasyprint import HTML as WeasyHTML
except Exception:
 WeasyHTML=None
API="https://generativelanguage.googleapis.com/v1beta/models/"
GEMINI_MODEL_DEFAULT="gemini-3.8-flash"
def sec(k,d=""):
 try:return str(st.secrets.get(k,d)).strip()
 except:return d
def pdf(s):
 if WeasyHTML is None:return None
 try:return WeasyHTML(string=s).write_pdf()
 except:return None
def esc(x):return html.escape(str(x or ""))
_esc=esc

def _gemini_parts(prompt,files):
 parts=[{"text":prompt}]
 for kind,name,data in files:
  parts.append({"inline_data":{"mime_type":("application/pdf" if kind=="pdf" else ("image/png" if name.lower().endswith(".png") else ("image/webp" if name.lower().endswith(".webp") else "image/jpeg"))),"data":base64.b64encode(data).decode()}})
 return parts
def call(prompt,files):
 key=sec("GEMINI_API_KEY")
 if not key:raise RuntimeError("AI_KEY_MISSING")
 preferred=sec("GEMINI_MODEL",GEMINI_MODEL_DEFAULT)
 models=[]
 for m in [preferred,"gemini-3.7-flash","gemini-3.6-flash","gemini-3.5-flash","gemini-2.5-flash"]:
  if m and m not in models:models.append(m)
 last=""
 for model in models:
  for attempt in range(3):
   url=f"{API}{model}:generateContent"
   body={"contents":[{"role":"user","parts":_gemini_parts(prompt,files)}],"generationConfig":{"responseMimeType":"application/json"}}
   req=request.Request(url,data=json.dumps(body,ensure_ascii=False).encode(),headers={"Content-Type":"application/json","x-goog-api-key":key},method="POST")
   try:
    with request.urlopen(req,timeout=180) as r:o=json.loads(r.read().decode())
    t=o["candidates"][0]["content"]["parts"][0]["text"].strip()
    t=re.sub(r"^```(?:json)?|^```$","",t,flags=re.I|re.M).strip()
    try:return json.loads(t)
    except Exception:
     s=t.find("{");e=t.rfind("}")
     if s<0 or e<=s:raise ValueError("invalid_json")
     return json.loads(t[s:e+1])
   except Exception as ex:
    raw=getattr(ex,"read",lambda:b"")()
    msg=raw.decode(errors="ignore") if raw else str(ex)
    last=msg
    retryable=any(x in msg for x in ["\"code\":429","\"code\":500","\"code\":502","\"code\":503","\"code\":504","HTTP Error 429","HTTP Error 503"])
    if retryable:
     import time
     time.sleep(2*(attempt+1))
     continue
    break
 raise RuntimeError("AI_TEMPORARILY_UNAVAILABLE")
def uploads(key):
 fs=st.file_uploader("📎 ارفع صور صفحات الكتاب أو PDF",type=["png","jpg","jpeg","webp","pdf"],accept_multiple_files=True,key=key);out=[]
 for f in fs or []:out.append(("pdf" if f.name.lower().endswith(".pdf") else "image",f.name,f.getvalue()))
 return out
def _print_teacher():
 name="م/ محمد غنيم"; phone="01016361440"
 try:
  df=st.session_state.get("teacher_profile_df",pd.DataFrame())
  if isinstance(df,pd.DataFrame) and not df.empty:
   n=str(df.iloc[0].get("اسم المعلم","")).strip()
   if n and n.lower()!="nan":name=n
 except Exception:pass
 return name,phone

def math_html(value):
 s=str(value or "").replace("\\r"," ").replace("\\n"," ").strip()
 s=re.sub(r"\\$\\$(.*?)\\$\\$",r"\\1",s,flags=re.S)
 s=re.sub(r"\\$(.*?)\\$",r"\\1",s,flags=re.S)
 # إزالة أي علامة $ متبقية حتى لا تظهر في ملف الطباعة.
 s=s.replace("$","")
 s=s.replace("\\(","").replace("\\)","").replace("\\[","").replace("\\]","")
 s=s.replace("\\u2212","-").replace("\\u00d7","×")
 for a,b in [(r"\left",""),(r"\right",""),(r"\displaystyle",""),(r"\,"," "),(r"\;"," "),(r"\!",""),(r"\pi","π"),(r"\theta","θ"),(r"\alpha","α"),(r"\beta","β"),(r"\gamma","γ"),(r"\delta","δ"),(r"\lambda","λ"),(r"\mu","μ"),(r"\sigma","σ"),(r"\omega","ω"),(r"\infty","∞"),(r"\times","×"),(r"\cdot","·"),(r"\pm","±"),(r"\mp","∓"),(r"\leq","≤"),(r"\geq","≥"),(r"\neq","≠"),(r"\approx","≈"),(r"\to","→"),(r"\sum","Σ"),(r"\int","∫"),(r"\angle","∠")]:s=s.replace(a,b)
 s=re.sub(r"\text\{([^{}]*)\}",r"\\1",s)
 def bal(t,p):
  if p>=len(t) or t[p]!="{":return "",p
  d=0
  for j in range(p,len(t)):
   if t[j]=="{":d+=1
   elif t[j]=="}":
    d-=1
    if d==0:return t[p+1:j],j+1
  return t[p+1:],len(t)
 def render(t):
  out=[];buf=[];i=0
  def flush():
   if buf:out.append(html.escape("".join(buf),quote=False));buf.clear()
  while i<len(t):
   if t.startswith(r"\frac",i) or t.startswith(r"\dfrac",i) or t.startswith(r"\tfrac",i):
    cmd=6 if t.startswith(r"\dfrac",i) else (6 if t.startswith(r"\tfrac",i) else 5);i+=cmd
    while i<len(t) and t[i].isspace():i+=1
    if i<len(t) and t[i]=="{":
     num,j=bal(t,i);i=j
     while i<len(t) and t[i].isspace():i+=1
     if i<len(t) and t[i]=="{":
      den,j=bal(t,i);i=j;flush();out.append(f"<span class='frac'><span class='num'>{render(num)}</span><span class='den'>{render(den)}</span></span>");continue
    buf.append("/");continue
   if t.startswith(r"\sqrt",i):
    i+=5
    idx=""
    if i<len(t) and t[i]=="[":
     j=t.find("]",i+1);idx=t[i+1:j] if j>=0 else "";i=j+1 if j>=0 else i
    while i<len(t) and t[i].isspace():i+=1
    if i<len(t) and t[i]=="{":
     rad,j=bal(t,i);i=j;flush();ix=f"<span class='root-index'>{render(idx)}</span>" if idx else "";out.append(f"<span class='sqrt'>{ix}<span class='radicand'>{render(rad)}</span></span>");continue
    buf.append("√");continue
   if t[i] in "^_":
    tag="sup" if t[i]=="^" else "sub";i+=1
    if i<len(t) and t[i]=="{":v,j=bal(t,i);i=j
    elif i<len(t):v=t[i];i+=1
    else:v=""
    flush();out.append(f"<{tag}>{render(v)}</{tag}>");continue
   if t[i]=="\\" and i+1<len(t):
    m=re.match(r"\\([A-Za-z]+)",t[i:])
    if m:
     mp={"pi":"π","theta":"θ","alpha":"α","beta":"β","gamma":"γ","delta":"δ","lambda":"λ","mu":"μ","sigma":"σ","omega":"ω","infty":"∞","times":"×","cdot":"·","pm":"±","mp":"∓","leq":"≤","geq":"≥","neq":"≠","approx":"≈","to":"→","sum":"Σ","int":"∫","angle":"∠"};tok=m.group(1);buf.append(mp.get(tok,tok));i+=len(tok)+1;continue
   buf.append(t[i]);i+=1
  flush();return "".join(out)
 # Also recognize simple numeric/algebraic fractions written as 1/2 or (x+1)/(x-1).
 s=re.sub(r"(?<![\w])\(([^()]+)\)\s*/\s*\(([^()]+)\)",lambda m:f"\\frac{{{m.group(1)}}}{{{m.group(2)}}}",s)
 s=re.sub(r"(?<![\w])(-?\d+(?:\.\d+)?)\s*/\s*(-?\d+(?:\.\d+)?)",lambda m:f"\\frac{{{m.group(1)}}}{{{m.group(2)}}}",s)
 s=re.sub(r"(?<![\w])(-?\d+(?:\.\d+)?)\s*/\s*(-?\d+(?:\.\d+)?)",lambda m:f"\\frac{{{m.group(1)}}}{{{m.group(2)}}}",s)
 rendered=render(s)
 has_arabic=bool(re.search(r"[\\u0600-\\u06ff]", s))
 direction_class="rtl-math" if has_arabic else "ltr-math"
 return f"<span class='{direction_class}'>{rendered}</span>"
def paper(title,grade,subject,qs,answers=False):
 teacher_name,teacher_phone=_print_teacher()
 z=[]
 for i,q in enumerate(qs,1):
  s=f"<section class='q'><div class='qhead'><b>السؤال {i}</b><span>{esc(q.get('type','مقالي'))} • {q.get('points',1)} درجة</span></div><div class='qtext'>{math_html(q.get('question',''))}</div>"
  if q.get("options"):s+="<div class='opts'>"+"".join(f"<div class='opt'><span class='box'>□</span>{math_html(x)}</div>" for x in q["options"])+"</div>"
  elif not answers:s+="<div class='lines'>"+"<hr>"*4+"</div>"
  if answers:s+=f"<div class='ans'><b>الإجابة:</b> {math_html(q.get('answer',''))}<br><span>{math_html(q.get('explanation',''))}</span></div>"
  z.append(s+"</section>")
 return f"""<!doctype html><html dir='rtl' lang='ar'><meta charset='utf-8'><style>@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@800;900&display=swap');
@page{{size:A4;margin:11mm 12mm 13mm}}*{{box-sizing:border-box}}body{{font-family:Tahoma,Arial,sans-serif;color:#172033;font-weight:700;line-height:1.9;margin:0;background:#fff}}.header{{position:relative;overflow:hidden;border-radius:18px;padding:15px 20px;margin-bottom:13px;background:linear-gradient(135deg,#0757b8 0%,#1677e8 58%,#3b82f6 100%);color:#fff;box-shadow:0 5px 16px rgba(37,99,235,.18)}}.header:after{{content:'';position:absolute;width:180px;height:180px;border-radius:50%;background:rgba(255,255,255,.10);left:-35px;top:-90px}}.header:before{{content:'';position:absolute;width:120px;height:120px;border-radius:50%;background:rgba(255,255,255,.08);left:95px;bottom:-80px}}.headrow{{position:relative;z-index:2;display:flex;align-items:center;justify-content:space-between;gap:20px}}.brand h2{{margin:0;font-size:21px;color:#fff;font-weight:800}}.brand div{{font-size:11px;color:#eaf3ff;font-weight:600}}.brand .phone{{font-size:12px;margin-top:3px;color:#fff}}.badge{{width:58px;height:58px;border:1px solid rgba(255,255,255,.35);border-radius:16px;background:rgba(255,255,255,.13);display:flex;align-items:center;justify-content:center;font-size:29px;flex:none}}.title{{text-align:center;margin:8px 0 12px;font-size:22px;color:#0757b8;font-weight:800}}.titleline{{height:3px;width:95px;background:#1677e8;border-radius:3px;margin:-5px auto 13px}}.meta{{display:grid;grid-template-columns:1fr 1fr;gap:7px;border:1px solid #cbd8ea;border-radius:13px;padding:10px 12px;background:#f5f9ff;font-size:12px;margin-bottom:12px}}.meta div{{background:#fff;border:1px solid #e1e8f2;border-radius:8px;padding:5px 8px}}.q{{border:1px solid #d6dfeb;border-right:4px solid #1677e8;border-radius:12px;padding:11px 14px;margin:9px 0;page-break-inside:avoid;background:#fff;box-shadow:0 2px 7px rgba(15,23,42,.045)}}.qhead{{display:flex;justify-content:space-between;gap:10px;color:#0757b8;font-size:12.5px;border-bottom:1px solid #e5ebf3;padding-bottom:5px;margin-bottom:7px}}.qtext{{font-size:17px;line-height:2.05;font-weight:700;direction:rtl}}.ltr-math{{direction:ltr!important;unicode-bidi:isolate;display:inline-block;text-align:left}}.rtl-math{{direction:rtl!important;unicode-bidi:isolate;display:inline-block;text-align:right}}.opts{{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:9px;font-size:14px}}.opt{{border:1px solid #dbe5f0;border-radius:8px;padding:5px 8px;background:#f8fbff}}.box{{color:#1677e8;font-size:18px;margin-left:5px}}.lines hr{{border:0;border-bottom:1px solid #d7dee8;margin:16px 0}}.ans{{background:#eef6ff;border:1px solid #9ec5f5;border-right:4px solid #1677e8;padding:8px 10px;border-radius:9px;margin-top:8px;color:#12355f}}.frac{{display:inline-flex;flex-direction:column;vertical-align:middle;text-align:center;line-height:1.05;margin:0 .12em;min-width:1.4em}}.frac .num{{border-bottom:1.5px solid #172033;padding:0 .22em;display:block}}.frac .den{{padding:0 .22em;display:block}}.sqrt{{display:inline-block;position:relative;margin:0 .08em;padding-left:.72em;vertical-align:middle}}.sqrt:before{{content:'√';position:absolute;left:0;top:-.12em;font-size:1.3em;font-weight:400}}.sqrt .radicand{{display:inline-block;border-top:1.5px solid #172033;padding:0 .12em;min-width:.6em}}sup,sub{{font-size:.72em;line-height:0}}.footer{{margin-top:16px;padding:8px 0 0;border-top:2px solid #dbe5f0;text-align:center;font-size:10px;color:#526174;font-weight:700}}.footer strong{{color:#0757b8}}</style><body><div class='header'><div class='headrow'><div class='brand'><h2>{esc(teacher_name)}</h2><div>البشمهندس x الرياضه • منصة تعليمية للرياضيات والإحصاء</div><div class='phone'>📞 {esc(teacher_phone)}</div></div><div class='badge'>📐</div></div></div><div class='title'>{esc(title)}</div><div class='titleline'></div><div class='meta'><div>الطالب: __________________</div><div>التاريخ: __________</div><div>الصف: {esc(grade)}</div><div>المادة: {esc(subject)}</div></div>{''.join(z)}<div class='footer'>إعداد ومتابعة: <strong>{esc(teacher_name)}</strong> &nbsp; | &nbsp; 📞 {esc(teacher_phone)} &nbsp; | &nbsp; البشمهندس x الرياضه</div></body></html>"""
def mind(d):
 teacher_name,teacher_phone=_print_teacher()
 cards="".join(f"<div class='card'><h3>{math_html(b.get('name',''))}</h3><ul>{''.join(f'<li>{math_html(x)}</li>' for x in b.get('items',[]))}</ul></div>" for b in d.get('branches',[]))
 return f"""<!doctype html><html dir='rtl' lang='ar'><meta charset='utf-8'><style>@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@800;900&display=swap');@page{{size:A4 landscape;margin:10mm}}*{{box-sizing:border-box}}body{{font-family:Tahoma,Arial,sans-serif;color:#111;font-weight:700;line-height:1.8;margin:0}}.header{{border:2px solid #0f766e;border-radius:18px;padding:12px 18px;margin-bottom:10px;background:linear-gradient(135deg,#effcf8,#eef7ff);display:flex;align-items:center;justify-content:space-between}}.brand h2{{margin:0;font-size:20px;color:#075985;font-weight:900}}.brand div{{font-size:11px;color:#475569}}h1{{text-align:center;color:#0f172a;font-size:22px;margin:7px 0 10px}}.center{{margin:10px auto;padding:14px;border:3px solid #1677ff;border-radius:20px;text-align:center;font-size:23px;font-weight:900;max-width:420px;background:#eef7ff}}.summary{{text-align:center;font-size:13px;margin:8px 0 12px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.card{{border:1.5px solid #c8d3df;border-radius:14px;padding:10px;min-height:110px;background:#fff}}.card h3{{color:#1677ff;font-size:15px;margin:0 0 5px;font-weight:900}}.card li{{font-size:12px;margin:3px 0}}.footer{{margin-top:12px;padding-top:7px;border-top:1px solid #cbd5e1;text-align:center;font-size:9.5px;color:#475569}}sup,sub{{font-size:.72em;line-height:0}}.frac{{display:inline-flex;flex-direction:column;vertical-align:middle;text-align:center;line-height:1.05}}.frac .num{{border-bottom:1.5px solid #10233f}}.sqrt{{display:inline-block;position:relative;padding-left:.7em}}.sqrt:before{{content:'√';position:absolute;left:0;top:-.12em;font-size:1.2em}}.sqrt .radicand{{border-top:1.5px solid #10233f}}</style><div class='header'><div class='brand'><h2>{esc(teacher_name)}</h2><div>البشمهندس x الرياضه</div><div>📞 {esc(teacher_phone)}</div></div><div style='font-size:26px'>🧠</div></div><h1>خريطة ذهنية — {math_html(d.get('title',''))}</h1><div class='center'>{math_html(d.get('title',''))}</div><p class='summary'>{math_html(d.get('summary',''))}</p><div class='grid'>{cards}</div><div class='footer'>إعداد ومتابعة: <b>{esc(teacher_name)}</b> &nbsp; | &nbsp; 📞 {esc(teacher_phone)} &nbsp; | &nbsp; البشمهندس x الرياضه</div></html>"""
def save_q(kind,title,payload,cb):
 q=st.session_state.get("question_bank_df")
 if not isinstance(q,pd.DataFrame):return False
 r={"معرف_السؤال":f"AI_{uuid.uuid4().hex[:10]}","المنهج/الدولة":"المنهج المصري 🇪🇬","المجموعة/الصف":payload.get("grade",""),"المادة":payload.get("subject",""),"نوع_السؤال":kind,"بيانات_السؤال_JSON":json.dumps({"title":title,"payload":payload},ensure_ascii=False)}
 st.session_state.question_bank_df=pd.concat([q,pd.DataFrame([r])],ignore_index=True)
 if cb:cb()
 return True
def delete_q(qid,cb):
 q=st.session_state.get("question_bank_df")
 if not isinstance(q,pd.DataFrame) or "معرف_السؤال" not in q.columns:return False
 before=len(q)
 st.session_state.question_bank_df=q[q["معرف_السؤال"].astype(str).ne(str(qid))].reset_index(drop=True)
 changed=len(st.session_state.question_bank_df)<before
 if changed and cb:cb()
 return changed
def render_ai_studio(save_callback=None):
 st.markdown("# 🤖 استوديو الذكاء الاصطناعي")
 if not sec("GEMINI_API_KEY"):st.warning("أضف GEMINI_API_KEY في Streamlit Secrets لتشغيل AI. المفتاح محفوظ في Secrets وليس داخل GitHub.")
 a,b,c=st.tabs(["📝 اختبارات AI","📚 واجبات AI","🧠 خرائط ذهنية"])
 with a:
  g=st.text_input("الصف / المرحلة",value="الصف الثالث الثانوي (علمي رياضة)",key="ai_g");s=st.text_input("المادة",value="الرياضيات",key="ai_s");n=st.number_input("عدد الأسئلة",1,40,10,key="ai_n");d=st.selectbox("الصعوبة",["متدرج","سهل","متوسط","صعب"],key="ai_d");typ=st.multiselect("الأنواع",["اختيار من متعدد","مقالي","صح أو خطأ"],["اختيار من متعدد","مقالي"],key="ai_t");notes=st.text_area("📝 ملاحظات وتعليمات للذكاء الاصطناعي (اختياري)",height=90,placeholder="مثال: ركّز على قوانين التفاضل، اجعل الأسئلة متنوعة، وضع سؤالين بمستوى صعب...",key="ai_notes");src=st.text_area("✍️ نص الدرس / المصدر (اختياري)",height=120,key="ai_txt");fs=uploads("ai_files")
  if st.button("✨ إنشاء الاختبار",type="primary",key="ai_make"):
   if not src.strip() and not fs:st.error("أضف نصاً أو صورة أو PDF.")
   else:
    try:
     p=f"""أنشئ اختبار رياضيات عربي للصف {g}، المادة {s}، صعوبة {d}، عدد {int(n)}، الأنواع {typ}. اعتمد على المصدر المرفق أو النص. طبّق ملاحظات المعلم التالية إن وُجدت: {notes[:5000]}. أعد JSON فقط: {{\"title\":\"\",\"description\":\"\",\"questions\":[{{\"type\":\"\",\"question\":\"\",\"options\":[\"\"],\"answer\":\"\",\"explanation\":\"\",\"points\":1}}]}}. النص: {src[:12000]}"""
     with st.spinner("جاري إنشاء الاختبار..."):st.session_state.ai_exam=call(p,fs);st.session_state.ai_exam_meta=(g,s,notes)
    except Exception as e:
     msg=str(e)
     if "503" in msg or "UNAVAILABLE" in msg or "high demand" in msg:
      st.info("الخدمة مشغولة حاليًا. اضغط زر الإنشاء مرة أخرى بعد لحظات.")
     elif "429" in msg:
      st.info("تم الوصول للحد المؤقت للطلبات. جرّب مرة أخرى بعد لحظات.")
     elif "AI_KEY_MISSING" in msg:
      st.warning("ميزة الذكاء الاصطناعي غير مفعلة حاليًا.")
     else:
      st.warning("تعذر إنشاء المحتوى حاليًا. جرّب مرة أخرى.")
  x=st.session_state.get("ai_exam")
  if x:
   x["title"]=st.text_input("عنوان الاختبار",x.get("title","اختبار AI"),key="ai_etitle")
   for i,q in enumerate(x.get("questions",[])):
    with st.expander(f"السؤال {i+1} — {q.get('type','')}"):
     q["question"]=st.text_area("نص السؤال",q.get("question",""),key=f"ai_q{i}")
     for j,o in enumerate(q.get("options") or []):q["options"][j]=st.text_input(f"الخيار {j+1}",o,key=f"ai_o{i}_{j}")
     q["answer"]=st.text_input("الإجابة النموذجية",q.get("answer",""),key=f"ai_a{i}")
   g,s,*_meta_notes=st.session_state.ai_exam_meta;h=paper(x["title"],g,s,x["questions"]);k=paper(x["title"],g,s,x["questions"],True);c1,c2,c3=st.columns(3)
   with c1:
    z=pdf(h)
    if z:st.download_button("📄 الاختبار PDF",z,"اختبار_AI.pdf","application/pdf",key="ai_pdf")
    else:st.download_button("🖨️ الاختبار للطباعة",h.encode(),"اختبار_AI.html","text/html",key="ai_html")
   with c2:
    z=pdf(k)
    if z:st.download_button("🗝️ طباعة نموذج الإجابة PDF",z,"نموذج_إجابة_الاختبار_AI.pdf","application/pdf",key="ai_key")
    else:st.download_button("🖨️ طباعة نموذج الإجابة",k.encode(),"نموذج_إجابة_الاختبار_AI.html","text/html",key="ai_key_html")
   with c3:
    if st.button("🚀 نشر إلكترونياً للطلاب",key="ai_pub"):
     r={"معرف_الامتحان":f"AI_EX_{uuid.uuid4().hex[:10]}","عنوان الامتحان":x["title"],"وصف الامتحان":x.get("description",""),"كلمة المرور":"","المنهج/الدولة":"المنهج المصري 🇪🇬","المجموعة/الصف":g,"المادة":s,"الفصل الدراسي":"","مدة الامتحان بالدقائق":60,"الأسئلة_JSON":json.dumps(x["questions"],ensure_ascii=False),"تاريخ الإنشاء":str(date.today())}
     st.session_state.exams_df=pd.concat([st.session_state.exams_df,pd.DataFrame([r])],ignore_index=True);save_callback() if save_callback else None;st.success("تم حفظ الاختبار في سجل الامتحانات.")
   if st.button("🗑️ مسح الاختبار الحالي",key="ai_clear"):
    st.session_state.pop("ai_exam",None);st.session_state.pop("ai_exam_meta",None);st.rerun()
   edf=st.session_state.get("exams_df")
   if isinstance(edf,pd.DataFrame) and not edf.empty and "معرف_الامتحان" in edf.columns:
    ai_edf=edf[edf["معرف_الامتحان"].astype(str).str.startswith("AI_EX_")]
    if not ai_edf.empty:
     exam_labels=[f'{rr.get("عنوان الامتحان","اختبار AI")} — {rr.get("المجموعة/الصف","")} — {rr.get("تاريخ الإنشاء","")}' for _,rr in ai_edf.iterrows()]
     exam_ids=ai_edf["معرف_الامتحان"].astype(str).tolist()
     exi=st.selectbox("اختر اختبار AI منشور للحذف",range(len(exam_labels)),format_func=lambda i:exam_labels[i],key="ai_delete_exam_select")
     if st.button("🗑️ حذف الاختبار المنشور",key="ai_delete_exam"):
      st.session_state.exams_df=edf[~edf["معرف_الامتحان"].astype(str).eq(exam_ids[exi])].reset_index(drop=True)
      save_callback() if save_callback else None
      st.success("تم حذف الاختبار من سجل الامتحانات.")
      st.rerun()
 with b:
  g=st.text_input("الصف / المرحلة",value="الصف الثالث الثانوي",key="aih_g");s=st.text_input("المادة",value="الرياضيات",key="aih_s");n=st.number_input("عدد الأسئلة",1,40,8,key="aih_n");d=st.selectbox("الصعوبة",["متدرج","سهل","متوسط","صعب"],key="aih_d");typ=st.multiselect("الأنواع",["اختيار من متعدد","مقالي","صح أو خطأ"],["مقالي","اختيار من متعدد"],key="aih_t");notes_h=st.text_area("📝 ملاحظات وتعليمات للذكاء الاصطناعي (اختياري)",height=90,placeholder="مثال: اجعل الواجب مناسبًا للحصة، وركّز على أسئلة تطبيقية...",key="aih_notes");src=st.text_area("✍️ نص الواجب / المصدر",height=120,key="aih_txt");fs=uploads("aih_files")
  if st.button("✨ إنشاء الواجب بالذكاء الاصطناعي",type="primary",key="aih_make"):
   if not src.strip() and not fs:st.error("أضف نصاً أو صورة أو PDF.")
   else:
    try:
     p=f"""أنشئ واجب رياضيات عربي للصف {g}، المادة {s}، صعوبة {d}، عدد {int(n)}، الأنواع {typ}. اعتمد على المصدر. طبّق ملاحظات المعلم التالية إن وُجدت: {notes_h[:5000]}. أعد JSON فقط: {{\"title\":\"\",\"questions\":[{{\"type\":\"\",\"question\":\"\",\"options\":[\"\"],\"answer\":\"\",\"explanation\":\"\",\"points\":1}}]}}. النص: {src[:12000]}"""
     with st.spinner("جاري إنشاء الواجب..."):st.session_state.ai_hw=call(p,fs);st.session_state.ai_hw_meta=(g,s,notes_h)
    except Exception as e:
     msg=str(e)
     if "503" in msg or "UNAVAILABLE" in msg or "high demand" in msg:
      st.info("الخدمة مشغولة حاليًا. اضغط زر الإنشاء مرة أخرى بعد لحظات.")
     elif "429" in msg:
      st.info("تم الوصول للحد المؤقت للطلبات. جرّب مرة أخرى بعد لحظات.")
     elif "AI_KEY_MISSING" in msg:
      st.warning("ميزة الذكاء الاصطناعي غير مفعلة حاليًا.")
     else:
      st.warning("تعذر إنشاء المحتوى حاليًا. جرّب مرة أخرى.")
  x=st.session_state.get("ai_hw")
  if x:
   x["title"]=st.text_input("عنوان الواجب",x.get("title","واجب AI"),key="aih_title")
   for i,q in enumerate(x.get("questions",[])):
    with st.expander(f"السؤال {i+1}"):q["question"]=st.text_area("نص السؤال",q.get("question",""),key=f"aih_q{i}")
   g,s,*_hw_notes=st.session_state.ai_hw_meta;h=paper(x["title"],g,s,x["questions"]);k=paper(x["title"],g,s,x["questions"],True);z=pdf(h);ak=pdf(k)
   c1,c2=st.columns(2)
   with c1:
    if z:st.download_button("📄 الواجب PDF",z,"واجب_AI.pdf","application/pdf",key="aih_pdf")
    else:st.download_button("🖨️ طباعة الواجب",h.encode(),"واجب_AI.html","text/html",key="aih_html")
   with c2:
    if ak:st.download_button("🗝️ طباعة نموذج إجابة الواجب PDF",ak,"نموذج_إجابة_واجب_AI.pdf","application/pdf",key="aih_key_pdf")
    else:st.download_button("🖨️ طباعة نموذج إجابة الواجب",k.encode(),"نموذج_إجابة_واجب_AI.html","text/html",key="aih_key_html")
   if st.button("💾 حفظ الواجب في بنك المنصة",key="aih_save"):
    if save_q("واجب AI",x["title"],{"grade":g,"subject":s,"notes":notes_h,"questions":x["questions"]},save_callback):st.success("تم حفظ الواجب في بنك المنصة.")
   if st.button("🗑️ مسح الواجب الحالي",key="aih_clear"):
    st.session_state.pop("ai_hw",None);st.session_state.pop("ai_hw_meta",None);st.rerun()
   qdf_hw=st.session_state.get("question_bank_df")
   hw_saved=[]
   if isinstance(qdf_hw,pd.DataFrame) and not qdf_hw.empty and "نوع_السؤال" in qdf_hw.columns and "بيانات_السؤال_JSON" in qdf_hw.columns:
    for _,rr in qdf_hw[qdf_hw["نوع_السؤال"].astype(str).eq("واجب AI")].iterrows():
     try:
      obj=json.loads(str(rr.get("بيانات_السؤال_JSON","")));pl=obj.get("payload",{})
      hw_saved.append({"id":rr.get("معرف_السؤال",""),"title":obj.get("title","واجب AI"),"grade":pl.get("grade",""),"saved_at":pl.get("saved_at","")})
     except Exception:pass
   if hw_saved:
    hw_labels=[f'{v["title"]} — {v["grade"]}' for v in hw_saved]
    hwi=st.selectbox("اختر واجب AI محفوظ للحذف",range(len(hw_labels)),format_func=lambda i:hw_labels[i],key="aih_delete_select")
    if st.button("🗑️ حذف الواجب المحفوظ",key="aih_delete"):
     if delete_q(hw_saved[hwi]["id"],save_callback):
      st.success("تم حذف الواجب من بنك المنصة.")
      st.rerun()
 with c:
  g=st.text_input("الصف / المرحلة",value="الصف الثالث الثانوي",key="aim_g");s=st.text_input("المادة",value="الرياضيات",key="aim_s");notes_m=st.text_area("📝 ملاحظات وتعليمات للذكاء الاصطناعي (اختياري)",height=90,placeholder="مثال: أظهر القوانين الأساسية، اجعل الفروع واضحة، وركّز على النقاط المهمة...",key="aim_notes");src=st.text_area("✍️ اسم الدرس أو محتواه",height=120,key="aim_txt");fs=uploads("aim_files")
  if st.button("🧠 إنشاء الخريطة الذهنية",type="primary",key="aim_make"):
   if not src.strip() and not fs:st.error("أضف الدرس أو صورة أو PDF.")
   else:
    try:
     p=f"""حوّل المصدر إلى خريطة ذهنية عربية للصف {g} في {s}. أعد JSON فقط: {{\"title\":\"\",\"summary\":\"\",\"branches\":[{{\"name\":\"\",\"items\":[\"\"]}}]}}. النص: {src[:12000]}"""
     with st.spinner("جاري بناء الخريطة..."):st.session_state.ai_mm=call(p,fs);st.session_state.ai_mm_meta=(g,s,notes_m)
    except Exception as e:
     msg=str(e)
     if "503" in msg or "UNAVAILABLE" in msg or "high demand" in msg:
      st.info("الخدمة مشغولة حاليًا. اضغط زر الإنشاء مرة أخرى بعد لحظات.")
     elif "429" in msg:
      st.info("تم الوصول للحد المؤقت للطلبات. جرّب مرة أخرى بعد لحظات.")
     elif "AI_KEY_MISSING" in msg:
      st.warning("ميزة الذكاء الاصطناعي غير مفعلة حاليًا.")
     else:
      st.warning("تعذر إنشاء المحتوى حاليًا. جرّب مرة أخرى.")
  x=st.session_state.get("ai_mm")
  if x:
   x["title"]=st.text_input("عنوان الخريطة",x.get("title","خريطة ذهنية"),key="aim_title");x["summary"]=st.text_area("الملخص",x.get("summary",""),key="aim_summary")
   for i,b in enumerate(x.get("branches",[])):
    with st.expander(f"فرع: {b.get('name','')}"):b["name"]=st.text_input("اسم الفرع",b.get("name",""),key=f"aim_b{i}");b["items"]=[v.strip() for v in st.text_area("النقاط — كل نقطة في سطر","\n".join(b.get("items",[])),key=f"aim_i{i}").splitlines() if v.strip()]
   h=mind(x);st.components.v1.html(h,height=580,scrolling=True);z=pdf(h)
   if z:st.download_button("📄 تصدير الخريطة PDF",z,"خريطة_ذهنية_AI.pdf","application/pdf",key="aim_pdf")
   if st.button("💾 حفظ الخريطة في بنك المنصة",key="aim_save"):
    payload={"grade":g,"subject":s,"notes":notes_m,"mindmap":x,"saved_at":datetime.now().strftime("%Y-%m-%d %H:%M")}
    if save_q("خريطة ذهنية AI",x["title"],payload,save_callback):
     st.session_state["ai_mm_saved_title"]=x["title"]
     st.success("تم حفظ الخريطة الذهنية في المنصة ويمكنك فتحها من قسم «الخرائط المحفوظة».")
   if st.button("🗑️ مسح الخريطة الحالية",key="aim_clear"):
    st.session_state.pop("ai_mm",None);st.session_state.pop("ai_mm_meta",None);st.rerun()
   
   st.markdown("---")
   st.markdown("### 📚 الخرائط الذهنية المحفوظة على المنصة")
   qdf=st.session_state.get("question_bank_df")
   saved=[]
   if isinstance(qdf,pd.DataFrame) and not qdf.empty and "نوع_السؤال" in qdf.columns and "بيانات_السؤال_JSON" in qdf.columns:
    for _,rr in qdf[qdf["نوع_السؤال"].astype(str).eq("خريطة ذهنية AI")].iterrows():
     try:
      obj=json.loads(str(rr.get("بيانات_السؤال_JSON","")))
      pl=obj.get("payload",{})
      mm=pl.get("mindmap",{})
      saved.append({"id":rr.get("معرف_السؤال",""),"title":obj.get("title","خريطة ذهنية"),"grade":pl.get("grade",""),"subject":pl.get("subject",""),"saved_at":pl.get("saved_at",""),"mindmap":mm})
     except Exception:
      pass
   if saved:
    labels=[f'{v["title"]} — {v["grade"]} — {v["saved_at"]}' for v in saved]
    idx=st.selectbox("اختر خريطة محفوظة لعرضها أو طباعتها",range(len(saved)),format_func=lambda i:labels[i],key="aim_saved_select")
    chosen=saved[idx]
    st.components.v1.html(mind(chosen["mindmap"]),height=520,scrolling=True)
    saved_pdf=pdf(mind(chosen["mindmap"]))
    if saved_pdf:
     st.download_button("📄 طباعة / تحميل الخريطة المحفوظة PDF",saved_pdf,"خريطة_ذهنية_محفوظة.pdf","application/pdf",key="aim_saved_pdf")
    if st.button("🗑️ حذف الخريطة المحفوظة",key="aim_delete_saved"):
     if delete_q(chosen["id"],save_callback):
      st.success("تم حذف الخريطة الذهنية من بنك المنصة.")
      st.rerun()
   else:
    st.info("لا توجد خرائط ذهنية محفوظة حتى الآن. أنشئ خريطة ثم اضغط «حفظ الخريطة في بنك المنصة».")
