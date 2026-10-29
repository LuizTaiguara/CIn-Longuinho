-- Migração inicial do banco de dados (PostgreSQL)
-- Task: SCRUM-69 (subtarefa da SCRUM-45)
-- Área: shared/migrations (Área protegida - revisão obrigatória: Miguel)

BEGIN;

-- ============================================================================
-- 1. TIPOS ENUMERADOS (VOCABULÁRIO FECHADO)
-- Nota: Os ENUMs fecham o vocabulário, mas a progressão de estados e as regras
-- de não-inferência são garantidas pela lógica da aplicação / worker.
-- ============================================================================

-- Classificação do item entre achado e perdido
CREATE TYPE tipo_item AS ENUM (
    'achado',
    'perdido'
);

-- Situação do item no catálogo
-- Fonte: docs/ARQUITETURA.md §2.2 ("Os dois eixos de estado")
-- aberto -> reivindicado -> encerrado
CREATE TYPE situacao_item AS ENUM (
    'aberto',
    'reivindicado',
    'encerrado'
);

-- Localização física atual do objeto
-- Fonte: docs/ARQUITETURA.md §2.2 ("Os dois eixos de estado")
-- 'com um setor' foi incluído pelo PO em 14/10/2026.
CREATE TYPE localizacao_item AS ENUM (
    'no local',
    'com quem achou',
    'com um setor',
    'caixa do bloco A/E',
    'devolvido'
);

-- ============================================================================
-- 2. TABELA DE VOCABULÁRIO DE LOCAIS
-- F-07: Catálogo parametrizável do espaço físico do CIn (locais, blocos e
-- pontos de custódia). Não possui FK direta com item.local, servindo para
-- alimentar listas de sugestões e normalização sem hardcode.
-- ============================================================================

CREATE TABLE local (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    bloco TEXT,
    ponto_custodia BOOLEAN NOT NULL DEFAULT FALSE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 3. MENSAGEM BRUTA (APPEND-ONLY)
-- Guarda o corpo integral antes de qualquer extração (ARQUITETURA §2.2).
-- Permite reprocessamento sem reler o Gmail e compõe o conjunto de testes.
-- ============================================================================

CREATE TABLE mensagem_bruta (
    id BIGSERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL,
    mensagem_id TEXT NOT NULL UNIQUE,
    remetente TEXT NOT NULL, -- DADO PESSOAL (Invariante 1: nunca expor na API, logs ou front)
    assunto TEXT,
    corpo TEXT NOT NULL,
    cabecalhos JSONB,
    data_envio TIMESTAMPTZ,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 4. ITEM (UNIDADE DE REGISTRO = THREAD)
-- Uma linha por conversa do Gmail (ADR-005).
-- ============================================================================

CREATE TABLE item (
    id BIGSERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL UNIQUE, -- ADR-005: uma linha por thread
    tipo tipo_item NOT NULL,
    descricao TEXT,
    local TEXT[], -- Lista de locais citados (ARQUITETURA §2.2; 6% citam >1 local)
    situacao situacao_item NOT NULL DEFAULT 'aberto',
    -- Invariante 3: localizacao é NULL por padrão. O worker nunca infere localização.
    localizacao localizacao_item DEFAULT NULL,
    setor TEXT, -- Preenchido quando localizacao = 'com um setor'
    autor_email TEXT NOT NULL, -- DADO PESSOAL (Invariante 1: nunca expor na API; usado só p/ checar autoria no login - ADR-010)
    fonte_encerramento TEXT, -- Preenchido no encerramento (ex.: 'confirmação do autor', 'terceiro')
    oculto BOOLEAN NOT NULL DEFAULT FALSE, -- Invariante 4: remoção é ocultar do catálogo, nunca DELETE
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 5. EVENTO (HISTÓRICO APPEND-ONLY)
-- Registra cada transição ou tentativa de transição, com sua fonte declarada.
-- Se um evento vier fora de ordem, ele é registrado aqui com aplicado = FALSE
-- e o status do item não muda (Invariante 2 e AGENTS.md raiz).
-- NÃO possui CHECK que proíba transições fora de ordem ou inválidas.
-- ============================================================================

CREATE TABLE evento (
    id BIGSERIAL PRIMARY KEY,
    item_id BIGINT NOT NULL REFERENCES item(id) ON DELETE RESTRICT,
    tipo_evento TEXT NOT NULL, -- ex: 'criacao', 'reivindicacao', 'desfecho', 'edicao_local', 'ocultacao'
    situacao_anterior situacao_item,
    situacao_nova situacao_item,
    fonte TEXT NOT NULL, -- ex: 'confirmação do autor', 'terceiro', 'detecção automática'
    aplicado BOOLEAN NOT NULL, -- TRUE se atualizou o item; FALSE se no-op/recusado/fora de ordem
    motivo_recusa TEXT, -- Preenchido quando aplicado = FALSE
    detalhes JSONB,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 6. QUARENTENA
-- Mensagens retidas por baixa confiança ou ambiguidade (ADR-004).
-- O remetente não é duplicado aqui: obtém-se via FK de mensagem_bruta (Invariante 1).
-- ============================================================================

CREATE TABLE quarentena (
    id BIGSERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL,
    mensagem_bruta_id BIGINT NOT NULL REFERENCES mensagem_bruta(id) ON DELETE RESTRICT,
    motivo_retencao TEXT NOT NULL,
    grau_confianca REAL,
    resolvida BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 7. PROCESSAMENTO
-- Controle de "já processei esta mensagem" no banco, não na caixa (Decisão 13).
--
-- ATENÇÃO: Conforme a descrição da SCRUM-45 e ARQUITETURA §2.2, esta é a
-- ÚNICA tabela do sistema onde DELETE é permitido. Reprocessar uma mensagem
-- consiste em apagar a linha correspondente nesta tabela.
-- ============================================================================

CREATE TABLE processamento (
    mensagem_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    status TEXT NOT NULL, -- ex: 'processado', 'quarentena'
    processado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 8. ÍNDICES
-- ============================================================================

CREATE INDEX idx_mensagem_bruta_thread_id ON mensagem_bruta(thread_id);
CREATE INDEX idx_item_situacao_oculto ON item(situacao, oculto);
CREATE INDEX idx_item_autor_email ON item(autor_email);
CREATE INDEX idx_evento_item_id ON evento(item_id);
CREATE INDEX idx_quarentena_thread_id ON quarentena(thread_id);
CREATE INDEX idx_processamento_thread_id ON processamento(thread_id);

COMMIT;
