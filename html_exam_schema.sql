-- Alhandasa shareable HTML exams.
-- Run in Supabase SQL Editor. Keep RLS enabled and do not add anon policies.
create table if not exists public.html_exams (
  id text primary key,
  title text not null,
  access_code text not null,
  duration_minutes integer not null default 30 check (duration_minutes between 1 and 300),
  mode text not null default 'builder',
  questions jsonb not null default '[]'::jsonb,
  html_code text not null default '',
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.html_exam_submissions (
  id text primary key,
  exam_id text not null references public.html_exams(id) on delete cascade,
  student_name text not null,
  answers jsonb not null default '{}'::jsonb,
  score numeric not null default 0,
  max_score numeric not null default 0,
  status text not null default 'started' check (status in ('started','submitted')),
  started_at timestamptz not null default now(),
  submitted_at timestamptz,
  result_token text not null unique,
  review_token text not null unique
);

create index if not exists html_exam_submissions_exam_id_idx
  on public.html_exam_submissions(exam_id);
create index if not exists html_exam_submissions_student_name_idx
  on public.html_exam_submissions(lower(student_name));

alter table public.html_exams enable row level security;
alter table public.html_exam_submissions enable row level security;

-- Access is server-side only. Streamlit must use SUPABASE_SERVICE_ROLE_KEY.
-- Do NOT create public/anon policies for these tables: answer keys and student answers are private.
