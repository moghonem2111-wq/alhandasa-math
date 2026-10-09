-- Run once in Supabase SQL Editor after the original html_exam_schema.sql.
-- Safe to re-run: columns are added only if they do not already exist.
alter table public.html_exams
  add column if not exists stage text not null default '',
  add column if not exists curriculum text not null default '',
  add column if not exists starts_at timestamptz,
  add column if not exists ends_at timestamptz;

create index if not exists html_exams_starts_at_idx on public.html_exams(starts_at);
create index if not exists html_exams_ends_at_idx on public.html_exams(ends_at);
