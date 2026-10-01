-- ============================================================
-- Base de conhecimento do assistente (Parte 2: RAG)
-- Cole este arquivo inteiro no SQL Editor do Supabase e clique em Run.
-- Pode rodar de novo sem problema: ele não apaga os trechos já gravados.
-- ============================================================

-- 1. Liga a extensão de vetores (pgvector)
create extension if not exists vector with schema extensions;

-- 2. A tabela dos trechos. Cada linha é um trecho de documento.
--    colecao = 'teste'    → índice novo, ainda sendo avaliado pelo portão
--    colecao = 'producao' → índice que o assistente no ar consulta
create table if not exists public.trechos (
  id uuid primary key default gen_random_uuid(),
  colecao text not null check (colecao in ('teste', 'producao')),
  fonte text not null,                             -- arquivo de origem, ex.: parte1-cicd-deploy.md
  secao text not null,                             -- título da seção de onde veio o trecho
  conteudo text not null,                          -- o texto do trecho
  embedding extensions.vector(384) not null,       -- o vetor (384 números no modelo padrão)
  fts tsvector generated always as                 -- índice de palavras, em português
    (to_tsvector('portuguese', secao || ' ' || conteudo)) stored,
  criado_em timestamptz not null default now()
);

create index if not exists trechos_colecao_idx on public.trechos (colecao);
create index if not exists trechos_fts_idx on public.trechos using gin (fts);
-- Sem índice HNSW de propósito: com poucos milhares de trechos, a busca exata é
-- rápida e sempre certa. Com muito mais, crie um: using hnsw (embedding vector_cosine_ops).

-- 3. Busca híbrida: palavras (busca textual do Postgres) + sentido (cosseno),
--    juntando as duas listas por RRF: soma de peso / (rrf_k + posição).
create or replace function public.buscar_hibrido(
  texto_pergunta text,
  vetor_pergunta extensions.vector(384),
  quantidade int default 4,
  colecao_alvo text default 'producao',
  peso_palavras float default 1,
  peso_sentido float default 1,
  rrf_k int default 60
)
returns table (fonte text, secao text, conteudo text, similaridade float, nota_rrf float)
language sql
stable
set search_path = public, extensions
as $$
  with consulta as (
    -- transforma a pergunta em palavras-raiz ligadas por OU: 'guard' | 'chav' | 'model'
    select to_tsquery('simple', coalesce(string_agg(quote_literal(lexema), ' | '), '')) as q
    from unnest(tsvector_to_array(to_tsvector('portuguese', texto_pergunta))) as lexema
  ),
  por_palavras as (
    select t.id, row_number() over (order by ts_rank_cd(t.fts, c.q) desc) as posicao
    from trechos t, consulta c
    where t.colecao = colecao_alvo and peso_palavras > 0 and t.fts @@ c.q
    order by posicao
    limit quantidade * 5
  ),
  por_sentido as (
    select t.id, row_number() over (order by t.embedding <=> vetor_pergunta) as posicao
    from trechos t
    where t.colecao = colecao_alvo and peso_sentido > 0
    order by posicao
    limit quantidade * 5
  )
  select t.fonte, t.secao, t.conteudo,
         1 - (t.embedding <=> vetor_pergunta) as similaridade,
         coalesce(peso_palavras / (rrf_k + p.posicao), 0)
           + coalesce(peso_sentido / (rrf_k + s.posicao), 0) as nota_rrf
  from por_palavras p
  full outer join por_sentido s on p.id = s.id
  join trechos t on t.id = coalesce(p.id, s.id)
  order by nota_rrf desc
  limit quantidade;
$$;

-- 4. Promove o índice avaliado: troca a coleção 'producao' pela 'teste', de uma vez só.
create or replace function public.promover_colecao()
returns int
language plpgsql
set search_path = public, extensions
as $$
declare
  total int;
begin
  delete from trechos where colecao = 'producao';
  insert into trechos (colecao, fonte, secao, conteudo, embedding)
    select 'producao', fonte, secao, conteudo, embedding from trechos where colecao = 'teste';
  get diagnostics total = row_count;
  return total;
end;
$$;

-- 5. Segurança: quem só lê (o Space, com a chave publicável) enxerga só a produção.
--    Quem escreve (o GitHub Actions, com a chave secreta) ignora estas regras.
alter table public.trechos enable row level security;

drop policy if exists "leitura da colecao producao" on public.trechos;
create policy "leitura da colecao producao" on public.trechos
  for select to anon, authenticated using (colecao = 'producao');

grant select on public.trechos to anon, authenticated;
grant all on public.trechos to service_role;

grant execute on function public.buscar_hibrido(text, extensions.vector, int, text, float, float, int)
  to anon, authenticated, service_role;

revoke execute on function public.promover_colecao() from public, anon, authenticated;
grant execute on function public.promover_colecao() to service_role;
