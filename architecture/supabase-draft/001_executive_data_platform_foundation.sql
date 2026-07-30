-- DESIGN DRAFT - NOT APPLIED TO ANY ENVIRONMENT
-- Hermes Executive Data Platform foundation sketch.
-- This file is intentionally outside supabase/migrations.

create schema if not exists identity;
create schema if not exists governance;
create schema if not exists audit;
create schema if not exists documents;

create type governance.capability_state as enum (
  'unavailable',
  'read_only',
  'proposal_only',
  'enabled'
);

create table if not exists identity.tenants (
  tenant_id uuid primary key,
  slug text not null unique,
  display_name text not null,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists identity.users (
  user_id uuid primary key,
  auth_user_id uuid unique,
  display_name text,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists identity.tenant_memberships (
  membership_id uuid primary key,
  tenant_id uuid not null references identity.tenants(tenant_id),
  user_id uuid not null references identity.users(user_id),
  role_key text not null,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  unique (tenant_id, user_id, role_key)
);

create table if not exists governance.capability_truth (
  capability_truth_id uuid primary key,
  tenant_id uuid not null references identity.tenants(tenant_id),
  capability_key text not null,
  channel_key text not null default 'all',
  state governance.capability_state not null default 'unavailable',
  connection_required boolean not null default false,
  live_execution_allowed boolean not null default false,
  reason text,
  source text not null default 'operator',
  effective_from timestamptz not null default now(),
  effective_to timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, capability_key, channel_key)
);

create table if not exists governance.improvement_proposals (
  proposal_id uuid primary key,
  tenant_id uuid not null references identity.tenants(tenant_id),
  proposal_type text not null,
  target_area text not null,
  proposal_digest text not null,
  safe_summary text not null,
  status text not null default 'proposed',
  created_by uuid references identity.users(user_id),
  created_at timestamptz not null default now(),
  reviewed_at timestamptz,
  unique (tenant_id, proposal_type, proposal_digest)
);

create table if not exists audit.audit_events (
  event_id uuid primary key,
  tenant_id uuid not null references identity.tenants(tenant_id),
  actor_type text not null,
  actor_id uuid,
  aggregate_type text not null,
  aggregate_id uuid,
  event_type text not null,
  schema_version integer not null default 1,
  occurred_at timestamptz not null,
  recorded_at timestamptz not null default now(),
  correlation_id text,
  causation_id uuid,
  safe_payload jsonb not null default '{}'::jsonb,
  payload_digest text,
  sensitivity text not null default 'internal',
  retention_policy text not null default 'standard'
);

create index if not exists idx_audit_events_tenant_time
  on audit.audit_events (tenant_id, occurred_at desc);

create index if not exists idx_audit_events_correlation
  on audit.audit_events (correlation_id);

alter table identity.tenants enable row level security;
alter table identity.users enable row level security;
alter table identity.tenant_memberships enable row level security;
alter table governance.capability_truth enable row level security;
alter table governance.improvement_proposals enable row level security;
alter table audit.audit_events enable row level security;

-- Example only. Production policies should use reviewed stable functions such
-- as identity.current_user_id() and identity.has_tenant_role().
create policy tenants_service_read_draft
  on identity.tenants
  for select
  using (false);

create policy audit_service_insert_draft
  on audit.audit_events
  for insert
  with check (false);
