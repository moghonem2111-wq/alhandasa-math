-- جداول نظام الأكاديميات المستقل في Supabase
-- شغّل هذا الملف مرة واحدة من Supabase > SQL Editor.
-- البيانات مستقلة عن users / sessions / weekly_schedule الخاصة بالمنصة.

create extension if not exists pgcrypto;

create table if not exists public.academy_accounts (
  id uuid primary key default gen_random_uuid(),
  "اسم الأكاديمية" text,
  "رقم الهاتف" text,
  "كلمة المرور" text,
  "نسبة الأكاديمية" numeric default 0,
  "الحالة" text
);

create table if not exists public.academy_teachers (
  id uuid primary key default gen_random_uuid(),
  "اسم الأكاديمية" text,
  "اسم المدرس" text,
  "المادة" text default '',
  "نسبة المدرس" numeric default 0,
  "الحالة" text
);

create table if not exists public.academy_assignments (
  id uuid primary key default gen_random_uuid(),
  "اسم الأكاديمية" text,
  "اسم الطالب" text,
  "اسم المدرس" text,
  "سعر الحصة" numeric default 0,
  "نسبة المدرس" numeric default 0,
  "نسبة الأكاديمية" numeric default 0,
  "نصيب المدرس" numeric default 0,
  "نصيب الأكاديمية" numeric default 0,
  "الحالة" text
);

create table if not exists public.academy_access (
  id uuid primary key default gen_random_uuid(),
  "اسم الأكاديمية" text,
  "رقم الهاتف" text,
  "كلمة المرور" text,
  "نوع الحساب" text,
  "الحالة" text
);

create table if not exists public.academy_subscriptions (
  id uuid primary key default gen_random_uuid(),
  "اسم الأكاديمية" text,
  "اسم الطالب" text,
  "قيمة الاشتراك" numeric default 0,
  "تاريخ البداية" text,
  "تاريخ النهاية" text,
  "نوع الدفع" text default 'مقدم',
  "الحالة" text,
  "ملاحظات" text
);

create table if not exists public.academy_students (
  id uuid primary key default gen_random_uuid(),
  "معرف الطالب" text,
  "اسم الأكاديمية" text,
  "اسم الطالب" text,
  "رقم الهاتف" text,
  "المنهج" text,
  "المرحلة" text,
  "المادة" text,
  "اسم المشرف" text,
  "الحالة" text,
  "ملاحظات" text
);

create table if not exists public.academy_attendance (
  id uuid primary key default gen_random_uuid(),
  "معرف السجل" text,
  "اسم الأكاديمية" text,
  "اسم الطالب" text,
  "اسم المدرس" text,
  "التاريخ" text,
  "الوقت" text,
  "الحالة" text,
  "سعر الحصة" numeric default 0,
  "نسبة المدرس" numeric default 0,
  "نسبة الأكاديمية" numeric default 0,
  "نصيب المدرس" numeric default 0,
  "نصيب الأكاديمية" numeric default 0,
  "ملاحظات" text
);

create table if not exists public.academy_schedule (
  id uuid primary key default gen_random_uuid(),
  "اسم الأكاديمية" text,
  "اسم الطالب" text,
  "اسم المدرس" text,
  "اليوم" text,
  "الموعد" text,
  "سعر الحصة" numeric default 0,
  "الحالة" text
);

-- ترقية الجداول التي تم إنشاؤها بالنسخة القديمة من الملف.
alter table public.academy_teachers add column if not exists "المادة" text default '';
alter table public.academy_assignments add column if not exists "سعر الحصة" numeric default 0;
alter table public.academy_assignments add column if not exists "نسبة المدرس" numeric default 0;
alter table public.academy_assignments add column if not exists "نسبة الأكاديمية" numeric default 0;
alter table public.academy_assignments add column if not exists "نصيب المدرس" numeric default 0;
alter table public.academy_assignments add column if not exists "نصيب الأكاديمية" numeric default 0;
alter table public.academy_attendance add column if not exists "نسبة المدرس" numeric default 0;
alter table public.academy_attendance add column if not exists "نسبة الأكاديمية" numeric default 0;
alter table public.academy_attendance add column if not exists "نصيب المدرس" numeric default 0;
alter table public.academy_attendance add column if not exists "نصيب الأكاديمية" numeric default 0;

-- تفعيل القراءة/الإضافة/التعديل/الحذف من خلال مفتاح Supabase المستخدم في التطبيق.
alter table public.academy_accounts enable row level security;
alter table public.academy_teachers enable row level security;
alter table public.academy_assignments enable row level security;
alter table public.academy_access enable row level security;
alter table public.academy_subscriptions enable row level security;
alter table public.academy_students enable row level security;
alter table public.academy_attendance enable row level security;
alter table public.academy_schedule enable row level security;

drop policy if exists "academy_accounts_app_access" on public.academy_accounts;
drop policy if exists "academy_teachers_app_access" on public.academy_teachers;
drop policy if exists "academy_assignments_app_access" on public.academy_assignments;
drop policy if exists "academy_access_app_access" on public.academy_access;
drop policy if exists "academy_subscriptions_app_access" on public.academy_subscriptions;
drop policy if exists "academy_students_app_access" on public.academy_students;
drop policy if exists "academy_attendance_app_access" on public.academy_attendance;
drop policy if exists "academy_schedule_app_access" on public.academy_schedule;

create policy "academy_accounts_app_access" on public.academy_accounts for all using (true) with check (true);
create policy "academy_teachers_app_access" on public.academy_teachers for all using (true) with check (true);
create policy "academy_assignments_app_access" on public.academy_assignments for all using (true) with check (true);
create policy "academy_access_app_access" on public.academy_access for all using (true) with check (true);
create policy "academy_subscriptions_app_access" on public.academy_subscriptions for all using (true) with check (true);
create policy "academy_students_app_access" on public.academy_students for all using (true) with check (true);
create policy "academy_attendance_app_access" on public.academy_attendance for all using (true) with check (true);
create policy "academy_schedule_app_access" on public.academy_schedule for all using (true) with check (true);
