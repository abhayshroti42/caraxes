-- =====================================================
-- Caraxes schema v1
-- Every tenant table carries org_id for data isolation.
-- =====================================================

create extension if not exists vector;

-- ---------- Organisations & users ----------
create table organisations (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  created_at  timestamptz not null default now()
);

-- One row per user. id matches the Supabase Auth user id.
create table profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  org_id      uuid not null references organisations(id) on delete cascade,
  full_name   text,
  role        text not null check (role in ('admin','creator','reviewer')),
  created_at  timestamptz not null default now()
);

-- ---------- Brand knowledge ----------
create table brand_documents (
  id             uuid primary key default gen_random_uuid(),
  org_id         uuid not null references organisations(id) on delete cascade,
  filename       text not null,
  storage_path   text not null,
  page_count     int,
  status         text not null default 'uploaded'
                 check (status in ('uploaded','processing','extracted','failed')),
  error_message  text,
  uploaded_by    uuid references profiles(id),
  created_at     timestamptz not null default now()
);

create table knowledge_items (
  id                  uuid primary key default gen_random_uuid(),
  org_id              uuid not null references organisations(id) on delete cascade,
  source_document_id  uuid references brand_documents(id) on delete set null,
  item_type           text not null check (item_type in ('rule','fact','tagline')),
  category            text not null check (category in (
                        'tone','terminology','messaging','visual_consistency',
                        'accessibility','promotional_claims','fact','tagline')),
  title               text,
  content             text not null,
  source_page         int,
  source_excerpt      text,
  is_global           boolean not null default false,
  metadata            jsonb not null default '{}'::jsonb,
  status              text not null default 'pending'
                      check (status in ('pending','approved','rejected')),
  embedding           vector(768),
  reviewed_by         uuid references profiles(id),
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

create table brand_assets (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references organisations(id) on delete cascade,
  asset_type    text not null check (asset_type in ('logo','image')),
  name          text not null,
  storage_path  text not null,
  mime_type     text,
  metadata      jsonb not null default '{}'::jsonb,
  uploaded_by   uuid references profiles(id),
  created_at    timestamptz not null default now()
);

-- ---------- Content review ----------
create table content_submissions (
  id               uuid primary key default gen_random_uuid(),
  org_id           uuid not null references organisations(id) on delete cascade,
  created_by       uuid references profiles(id),
  title            text,
  content_type     text not null check (content_type in ('text','pdf','image')),
  text_content     text,
  storage_path     text,
  status           text not null default 'draft'
                   check (status in ('draft','analyzing','in_review',
                                     'approved','needs_revision','rejected')),
  current_version  int not null default 1,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create table submission_versions (
  id             uuid primary key default gen_random_uuid(),
  org_id         uuid not null references organisations(id) on delete cascade,
  submission_id  uuid not null references content_submissions(id) on delete cascade,
  version_no     int not null,
  text_content   text,
  storage_path   text,
  created_by     uuid references profiles(id),
  created_at     timestamptz not null default now(),
  unique (submission_id, version_no)
);

create table analyses (
  id             uuid primary key default gen_random_uuid(),
  org_id         uuid not null references organisations(id) on delete cascade,
  submission_id  uuid not null references content_submissions(id) on delete cascade,
  version_no     int not null default 1,
  status         text not null default 'running'
                 check (status in ('running','completed','failed')),
  summary        jsonb not null default '{}'::jsonb,
  created_at     timestamptz not null default now()
);

-- One row per violation. knowledge_item_id = the rule that was violated.
create table findings (
  id                    uuid primary key default gen_random_uuid(),
  org_id                uuid not null references organisations(id) on delete cascade,
  analysis_id           uuid not null references analyses(id) on delete cascade,
  knowledge_item_id     uuid references knowledge_items(id) on delete set null,
  source                text not null check (source in ('text','visual','deterministic')),
  severity              text not null default 'medium'
                        check (severity in ('low','medium','high')),
  segment_text          text,
  location              jsonb,            -- e.g. bounding box for images
  explanation           text not null,
  suggested_correction  text,
  status                text not null default 'open'
                        check (status in ('open','accepted','dismissed','fixed')),
  created_at            timestamptz not null default now()
);

create table reviews (
  id             uuid primary key default gen_random_uuid(),
  org_id         uuid not null references organisations(id) on delete cascade,
  submission_id  uuid not null references content_submissions(id) on delete cascade,
  reviewer_id    uuid references profiles(id),
  decision       text not null check (decision in ('approved','rejected','changes_requested')),
  comment        text,
  created_at     timestamptz not null default now()
);

-- ---------- Indexes ----------
create index on profiles (org_id);
create index on brand_documents (org_id);
create index on knowledge_items (org_id, status, is_global);
create index on knowledge_items using hnsw (embedding vector_cosine_ops);
create index on brand_assets (org_id);
create index on content_submissions (org_id, status);
create index on analyses (submission_id);
create index on findings (analysis_id);
create index on findings (knowledge_item_id);

-- ---------- Security ----------
-- RLS ON with no policies = the public (anon) key can read nothing.
-- Only our backend, using the secret/service key, can access data.
alter table organisations        enable row level security;
alter table profiles             enable row level security;
alter table brand_documents      enable row level security;
alter table knowledge_items      enable row level security;
alter table brand_assets         enable row level security;
alter table content_submissions  enable row level security;
alter table submission_versions  enable row level security;
alter table analyses             enable row level security;
alter table findings             enable row level security;
alter table reviews              enable row level security;
create table document_pages (
  id              uuid primary key default gen_random_uuid(),
  org_id          uuid not null references organisations(id) on delete cascade,
  document_id     uuid not null references brand_documents(id) on delete cascade,
  page_number     int not null,
  text            text not null default '',
  method          text not null check (method in ('native','ocr')),
  ocr_confidence  real,
  created_at      timestamptz not null default now(),
  unique (document_id, page_number)
);

create index on document_pages (document_id);
alter table document_pages enable row level security;
create or replace function match_knowledge_items(
  query_embedding   vector(768),
  match_org_id      uuid,
  match_count       int      default 8,
  filter_categories text[]   default null,
  filter_item_types text[]   default null,
  filter_tags       text[]   default null,
  min_similarity    float    default 0.0
)
returns table (
  id                 uuid,
  item_type          text,
  category           text,
  title              text,
  content            text,
  source_document_id uuid,
  source_page        int,
  source_excerpt     text,
  is_global          boolean,
  metadata           jsonb,
  similarity         float
)
language sql stable
as $$
  select
    ki.id, ki.item_type, ki.category, ki.title, ki.content,
    ki.source_document_id, ki.source_page, ki.source_excerpt,
    ki.is_global, ki.metadata,
    (1 - (ki.embedding <=> query_embedding))::float as similarity
  from knowledge_items ki
  where ki.org_id = match_org_id            -- organisation isolation
    and ki.status = 'approved'              -- only approved knowledge
    and ki.is_global = false                -- global rules are fetched separately
    and ki.embedding is not null
    and (filter_categories is null or ki.category = any (filter_categories))
    and (filter_item_types is null or ki.item_type = any (filter_item_types))
    and (filter_tags is null or ki.metadata->'applies_to' ?| filter_tags)
    and (1 - (ki.embedding <=> query_embedding)) >= min_similarity
  order by ki.embedding <=> query_embedding
  limit match_count;
$$;
alter table findings
  add column finding_type text not null default 'rule_violation'
  check (finding_type in ('rule_violation', 'unsupported_claim', 'fact_conflict'));
  alter table content_submissions add column created_by_name text;
alter table submission_versions add column author_name text;
alter table reviews add column reviewer_name text;