# منصة البشمهندس x الرياضه

نسخة جاهزة للنشر المجاني عبر خدمة تستضيف Docker/Streamlit.

## مهم قبل التشغيل

التطبيق الحالي يدعم التخزين الدائم عبر Supabase عند ضبط الأسرار التالية:

- `SUPABASE_URL`
- `SUPABASE_KEY`

لا تضع مفاتيح Supabase السرية داخل `app.py` أو GitHub.

## التشغيل محلياً

```bash
pip install -r requirements.txt
streamlit run app.py
```

## النشر

ارفع محتويات هذا المجلد إلى مستودع GitHub أو إلى Hugging Face Space باستخدام Docker.

في إعدادات المنصة المستضيفة أضف Secrets/Environment Variables:

```text
SUPABASE_URL=...
SUPABASE_KEY=...
```

ثم شغّل الحاوية على المنفذ 7860.

## ملاحظة

هذه النسخة تحافظ على منطق التطبيق الحالي. التخزين الأساسي الحالي ما زال يستطيع حفظ نسخة Excel كاملة في Supabase، لذلك لا تعتبر هذه الحزمة ترحيلاً كاملاً لكل العمليات إلى جداول PostgreSQL المنظمة.
