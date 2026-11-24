-- ═══════════════════════════════════════════════════════════════════
--  Espace volontariat — schéma Supabase
--  À coller dans Supabase → SQL Editor → New query → Run (une seule fois)
-- ═══════════════════════════════════════════════════════════════════

-- ── Profils (un par compte) ──────────────────────────────────────────
create table if not exists public.profiles (
  id               uuid primary key references auth.users(id) on delete cascade,
  email            text,
  full_name        text,
  role             text not null default 'candidat' check (role in ('candidat', 'admin')),
  stage            int  not null default 0 check (stage between 0 and 5),
  contract_type    text check (contract_type in ('long', 'court')),  -- copié du contrat signé
  duration         text,
  paid_at          timestamptz,                -- rempli par l'équipe quand le reçu est validé
  paid_amount      numeric(10, 2),
  payment_method   text,                       -- 'paypal' ou 'carte' (choisi au contrat)
  payment_ref      text,                       -- note de l'équipe
  admin_message    text default '',
  test_date        date,
  test_result      text default '',
  interview_date   timestamptz,
  visa_appointment timestamptz,
  created_at       timestamptz not null default now()
);

-- ── Contrats signés (un par candidat, non modifiable) ───────────────
create table if not exists public.contracts (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null unique references public.profiles(id) on delete cascade,
  contract_type    text not null check (contract_type in ('long', 'court')),  -- long = 1 an (1 500 €), court = moins de 3 mois (1 200 €)
  duration         text not null,
  payment_method   text not null check (payment_method in ('paypal', 'carte')),  -- choisi par le candidat
  first_name       text not null,
  last_name        text not null,
  birth_date       date not null,
  birth_place      text not null,
  nationality      text not null,
  passport_number  text not null,
  phone            text not null,
  address          text not null,
  contract_version text not null,
  contract_hash    text not null,
  signature_data   text not null,          -- image PNG de la signature (data URL)
  mention          text not null,          -- « Lu et approuvé » écrit par le candidat
  user_agent       text,
  signed_at        timestamptz not null default now()
);

-- ── Documents envoyés ───────────────────────────────────────────────
create table if not exists public.documents (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.profiles(id) on delete cascade,
  doc_type     text not null,
  file_path    text not null,
  file_name    text not null,
  file_size    bigint,
  status       text not null default 'en_attente' check (status in ('en_attente', 'valide', 'refuse')),
  comment      text,
  uploaded_at  timestamptz not null default now(),
  reviewed_at  timestamptz
);
create index if not exists documents_user_idx on public.documents(user_id);

-- ── Fonctions utilitaires ───────────────────────────────────────────
create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = auth.uid() and role = 'admin');
$$;

-- Création automatique du profil à l'inscription
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, full_name)
  values (new.id, new.email, coalesce(new.raw_user_meta_data->>'full_name', ''));
  return new;
end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- Contrat signé → le candidat passe automatiquement à l'étape "Dossier"
create or replace function public.handle_contract_signed() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.signed_at := now();  -- l'heure de signature vient du serveur, pas du navigateur
  update public.profiles
     set stage = greatest(stage, 1), contract_type = new.contract_type, duration = new.duration,
         payment_method = new.payment_method
   where id = new.user_id;
  return new;
end $$;
drop trigger if exists on_contract_signed on public.contracts;
create trigger on_contract_signed before insert on public.contracts
  for each row execute function public.handle_contract_signed();

-- ── Sécurité (Row Level Security) ───────────────────────────────────
alter table public.profiles  enable row level security;
alter table public.contracts enable row level security;
alter table public.documents enable row level security;

-- profils : chacun lit le sien ; seule l'équipe modifie (étape, dates, messages)
drop policy if exists "profil: lecture" on public.profiles;
create policy "profil: lecture" on public.profiles for select using (id = auth.uid() or public.is_admin());
drop policy if exists "profil: équipe modifie" on public.profiles;
create policy "profil: équipe modifie" on public.profiles for update using (public.is_admin()) with check (public.is_admin());

-- contrats : le candidat signe une fois le sien ; personne ne le modifie
drop policy if exists "contrat: lecture" on public.contracts;
create policy "contrat: lecture" on public.contracts for select using (user_id = auth.uid() or public.is_admin());
drop policy if exists "contrat: signature" on public.contracts;
create policy "contrat: signature" on public.contracts for insert with check (user_id = auth.uid());

-- documents : le candidat ajoute/supprime les siens (tant qu'ils ne sont pas vérifiés) ; l'équipe valide
drop policy if exists "doc: lecture" on public.documents;
create policy "doc: lecture" on public.documents for select using (user_id = auth.uid() or public.is_admin());
drop policy if exists "doc: envoi" on public.documents;
create policy "doc: envoi" on public.documents for insert
  with check (user_id = auth.uid() and status = 'en_attente' and comment is null
              and (
                -- le reçu de paiement peut être envoyé dès que le contrat est signé
                (doc_type = 'recu_paiement' and exists (select 1 from public.contracts c where c.user_id = auth.uid()))
                -- les autres documents : une fois le paiement validé par l'équipe
                or exists (select 1 from public.profiles p where p.id = auth.uid() and p.paid_at is not null)
              ));
drop policy if exists "doc: suppression" on public.documents;
create policy "doc: suppression" on public.documents for delete
  using ((user_id = auth.uid() and status = 'en_attente') or public.is_admin());
drop policy if exists "doc: équipe valide" on public.documents;
create policy "doc: équipe valide" on public.documents for update using (public.is_admin()) with check (public.is_admin());

-- ── Stockage des fichiers (bucket privé "documents") ────────────────
insert into storage.buckets (id, name, public, file_size_limit)
values ('documents', 'documents', false, 10485760)
on conflict (id) do update set public = false, file_size_limit = 10485760;

drop policy if exists "fichiers: lecture" on storage.objects;
create policy "fichiers: lecture" on storage.objects for select
  using (bucket_id = 'documents' and ((storage.foldername(name))[1] = auth.uid()::text or public.is_admin()));
drop policy if exists "fichiers: envoi" on storage.objects;
create policy "fichiers: envoi" on storage.objects for insert
  with check (bucket_id = 'documents' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists "fichiers: suppression" on storage.objects;
create policy "fichiers: suppression" on storage.objects for delete
  using (bucket_id = 'documents' and ((storage.foldername(name))[1] = auth.uid()::text or public.is_admin()));

-- ═══════════════════════════════════════════════════════════════════
--  Donner l'accès "équipe" à un compte (après qu'il s'est inscrit) :
--    update public.profiles set role = 'admin' where email = 'ton@email.com';
-- ═══════════════════════════════════════════════════════════════════
