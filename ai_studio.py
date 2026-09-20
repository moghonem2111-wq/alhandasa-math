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
def paper(title,grade,subject,qs,answers=False):
 z=[]
 for i,q in enumerate(qs,1):
  s=f"<div class='q'><b>السؤال {i} — {_esc(q.get('type','مقالي'))} ({q.get('points',1)} درجة)</b><p>{esc(q.get('question',''))}</p>"
  if q.get("options"):s+="<div class='opts'>"+"".join(f"<div>□ {esc(x)}</div>" for x in q["options"])+"</div>"
  elif not answers:s+="<div class='lines'>"+"<hr>"*4+"</div>"
  if answers:s+=f"<div class='ans'><b>الإجابة:</b> {esc(q.get('answer',''))}<br>{esc(q.get('explanation',''))}</div>"
  z.append(s+"</div>")
 return f"""<!doctype html><html dir='rtl'><meta charset='utf-8'><style>@page{{size:A4;margin:15mm}}body{{font-family:'DejaVu Sans','Tahoma',Arial,sans-serif;line-height:1.7}}.head{{border:2px solid #1677ff;border-radius:14px;padding:15px;margin-bottom:16px;background:#f6fbff}}h1{{color:#0757b8;margin:2px 0}}.meta{{display:grid;grid-template-columns:1fr 1fr;gap:6px}}.q{{border:1px solid #ccd6e3;border-radius:10px;padding:11px;margin:10px 0;page-break-inside:avoid}}.q>b{{color:#0757b8}}.opts{{display:grid;grid-template-columns:1fr 1fr;gap:7px}}.lines hr{{border:0;border-bottom:1px solid #bbb;margin:17px 0}}.ans{{background:#eef8ee;border:1px solid #8bc48b;padding:7px;border-radius:7px}}</style><body><div class='head'><small>البشمهندس x الرياضه</small><h1>{esc(title)}</h1><div class='meta'><div>الطالب: __________________</div><div>التاريخ: __________</div><div>الصف: {esc(grade)}</div><div>المادة: {esc(subject)}</div></div></div>{''.join(z)}<footer>إعداد المعلم — البشمهندس x الرياضه</footer></body></html>"""
def mind(d):
 cards="".join(f"<div class='card'><h3>{esc(b.get('name',''))}</h3><ul>{''.join(f'<li>{esc(x)}</li>' for x in b.get('items',[]))}</ul></div>" for b in d.get('branches',[]))
 return f"""<!doctype html><html dir='rtl'><meta charset='utf-8'><style>@page{{size:A4 landscape;margin:12mm}}body{{font-family:'DejaVu Sans','Tahoma',Arial,sans-serif}}h1{{text-align:center;color:#0757b8}}.center{{margin:15px auto;padding:18px;border:3px solid #1677ff;border-radius:20px;text-align:center;font-size:24px;font-weight:900;max-width:420px;background:#eef7ff;font-family:'Noto Kufi Arabic','Noto Sans Arabic','Noto Naskh Arabic','DejaVu Sans',sans-serif}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.card{{border:2px solid #c8d3df;border-radius:14px;padding:12px;min-height:120px;background:#fff}}.card h3{{color:#1677ff;font-family:'Noto Kufi Arabic','Noto Sans Arabic','Noto Naskh Arabic','DejaVu Sans',sans-serif;margin-top:0}}</style><h1>خريطة ذهنية — {esc(d.get('title',''))}</h1><div class='center'>{esc(d.get('title',''))}</div><p style='text-align:center'>{esc(d.get('summary',''))}</p><div class='grid'>{cards}</div></html>"""
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
  g=st.text_input("الصف / المرحلة",value="الصف الثالث الثانوي (علمي رياضة)",key="ai_g");s=st.text_input("المادة",value="الرياضيات",key="ai_s");n=st.number_input("عدد الأسئلة",1,40,10,key="ai_n");d=st.selectbox("الصعوبة",["متدرج","سهل","متوسط","صعب"],key="ai_d");typ=st.multiselect("الأنواع",["اختيار من متعدد","مقالي","صح أو خطأ"],["اختيار من متعدد","مقالي"],key="ai_t");src=st.text_area("✍️ نص الدرس / المصدر (اختياري)",height=120,key="ai_txt");fs=uploads("ai_files")
  if st.button("✨ إنشاء الاختبار",type="primary",key="ai_make"):
   if not src.strip() and not fs:st.error("أضف نصاً أو صورة أو PDF.")
   else:
    try:
     p=f"""أنشئ اختبار رياضيات عربي للصف {g}، المادة {s}، صعوبة {d}، عدد {int(n)}، الأنواع {typ}. اعتمد على المصدر المرفق أو النص. أعد JSON فقط: {{\"title\":\"\",\"description\":\"\",\"questions\":[{{\"type\":\"\",\"question\":\"\",\"options\":[\"\"],\"answer\":\"\",\"explanation\":\"\",\"points\":1}}]}}. النص: {src[:12000]}"""
     with st.spinner("جاري إنشاء الاختبار..."):st.session_state.ai_exam=call(p,fs);st.session_state.ai_exam_meta=(g,s)
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
   g,s=st.session_state.ai_exam_meta;h=paper(x["title"],g,s,x["questions"]);k=paper(x["title"],g,s,x["questions"],True);c1,c2,c3=st.columns(3)
   with c1:
    z=pdf(h)
    if z:st.download_button("📄 الاختبار PDF",z,"اختبار_AI.pdf","application/pdf",key="ai_pdf")
    else:st.download_button("🖨️ الاختبار للطباعة",h.encode(),"اختبار_AI.html","text/html",key="ai_html")
   with c2:
    z=pdf(k)
    if z:st.download_button("🗝️ مفتاح الإجابة PDF",z,"مفتاح_إجابة_AI.pdf","application/pdf",key="ai_key")
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
  g=st.text_input("الصف / المرحلة",value="الصف الثالث الثانوي",key="aih_g");s=st.text_input("المادة",value="الرياضيات",key="aih_s");n=st.number_input("عدد الأسئلة",1,40,8,key="aih_n");d=st.selectbox("الصعوبة",["متدرج","سهل","متوسط","صعب"],key="aih_d");typ=st.multiselect("الأنواع",["اختيار من متعدد","مقالي","صح أو خطأ"],["مقالي","اختيار من متعدد"],key="aih_t");src=st.text_area("✍️ نص الواجب / المصدر",height=120,key="aih_txt");fs=uploads("aih_files")
  if st.button("✨ إنشاء الواجب بالذكاء الاصطناعي",type="primary",key="aih_make"):
   if not src.strip() and not fs:st.error("أضف نصاً أو صورة أو PDF.")
   else:
    try:
     p=f"""أنشئ واجب رياضيات عربي للصف {g}، المادة {s}، صعوبة {d}، عدد {int(n)}، الأنواع {typ}. اعتمد على المصدر. أعد JSON فقط: {{\"title\":\"\",\"questions\":[{{\"type\":\"\",\"question\":\"\",\"options\":[\"\"],\"answer\":\"\",\"explanation\":\"\",\"points\":1}}]}}. النص: {src[:12000]}"""
     with st.spinner("جاري إنشاء الواجب..."):st.session_state.ai_hw=call(p,fs);st.session_state.ai_hw_meta=(g,s)
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
   g,s=st.session_state.ai_hw_meta;h=paper(x["title"],g,s,x["questions"]);z=pdf(h)
   if z:st.download_button("📄 طباعة / تحميل الواجب PDF",z,"واجب_AI.pdf","application/pdf",key="aih_pdf")
   else:st.download_button("🖨️ طباعة الواجب",h.encode(),"واجب_AI.html","text/html",key="aih_html")
   if st.button("💾 حفظ الواجب في بنك المنصة",key="aih_save"):
    if save_q("واجب AI",x["title"],{"grade":g,"subject":s,"questions":x["questions"]},save_callback):st.success("تم حفظ الواجب في بنك المنصة.")
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
  g=st.text_input("الصف / المرحلة",value="الصف الثالث الثانوي",key="aim_g");s=st.text_input("المادة",value="الرياضيات",key="aim_s");src=st.text_area("✍️ اسم الدرس أو محتواه",height=120,key="aim_txt");fs=uploads("aim_files")
  if st.button("🧠 إنشاء الخريطة الذهنية",type="primary",key="aim_make"):
   if not src.strip() and not fs:st.error("أضف الدرس أو صورة أو PDF.")
   else:
    try:
     p=f"""حوّل المصدر إلى خريطة ذهنية عربية للصف {g} في {s}. أعد JSON فقط: {{\"title\":\"\",\"summary\":\"\",\"branches\":[{{\"name\":\"\",\"items\":[\"\"]}}]}}. النص: {src[:12000]}"""
     with st.spinner("جاري بناء الخريطة..."):st.session_state.ai_mm=call(p,fs);st.session_state.ai_mm_meta=(g,s)
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
    payload={"grade":g,"subject":s,"mindmap":x,"saved_at":datetime.now().strftime("%Y-%m-%d %H:%M")}
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
