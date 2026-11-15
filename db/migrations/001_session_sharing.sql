-- Session sharing: visibility, publication state, share token.
begin;

alter table content_submissions
  add column if not exists visibility   text not null default 'private',
  add column if not exists published_at timestamptz,
  add column if not exists share_token  text;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'content_submissions_visibility_check') then
    alter table content_submissions
      add constraint content_submissions_visibility_check
      check (visibility in ('private', 'unlisted', 'public'));
  end if;
end $$;

alter table content_submissions
  add column if not exists is_published boolean generated always as (visibility <> 'private') stored;

-- Share tokens are unique; the gallery query gets its own index
create unique index if not exists content_submissions_share_token_key
  on content_submissions (share_token) where share_token is not null;
create index if not exists content_submissions_gallery_idx
  on content_submissions (published_at desc)
  where visibility = 'public' and status = 'approved';

-- Invariant enforced by the database itself:
-- anything that is not approved, or is private, can never carry a published state or a link.
create or replace function public.enforce_session_visibility()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.status is distinct from 'approved' or new.visibility = 'private' then
    new.visibility   := 'private';
    new.published_at := null;
    new.share_token  := null;
  elsif new.published_at is null then
    new.published_at := now();
  end if;
  return new;
end;
$$;

drop trigger if exists enforce_session_visibility on content_submissions;
create trigger enforce_session_visibility
  before insert or update on content_submissions
  for each row execute function public.enforce_session_visibility();

-- Row Level Security: deny by default (already on); add ONE narrow read path.
alter table content_submissions enable row level security;

-- RLS limits rows, not columns, so column grants limit the columns.
-- org_id, storage_path, share_token and created_by_name are never readable with the public key.
revoke all on table content_submissions from anon, authenticated;
grant select (id, title, content_type, text_content, status, visibility, published_at, created_at)
  on table content_submissions to anon, authenticated;

drop policy if exists "public approved sessions are readable" on content_submissions;
create policy "public approved sessions are readable"
  on content_submissions for select to anon, authenticated
  using (visibility = 'public' and status = 'approved');

commit;