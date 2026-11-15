-- Migração: campos que o contrato expõe e que o schema inicial não tinha
-- Task: SCRUM-45 (F-02), preparando US-02, US-04, US-06, US-07 e US-15
-- Área: shared/migrations (Área protegida - revisão obrigatória: Miguel)
--
-- Cada coluna aqui corresponde a um campo do shared/openapi.yaml ou a uma regra do backlog:
--   origem                 'lista' (veio do e-mail) ou 'site' (cadastro pelo formulário, US-06)
--   revisar                confiança média do classificador: publica com o selo "revisar" (ADR-004)
--   foto_url               foto do anúncio (US-06), servida pela API
--   data_anuncio           data do e-mail original ou do cadastro; o contrato expõe como data_registro
--   aviso_autor_enviado_em US-15: "um único aviso por conversa". NULL = ainda não avisou
--
-- "Ainda não foi para a lista" (US-07) é derivado: origem = 'site' AND thread_id IS NULL.
-- Quando o worker lê o e-mail com o código do item, preenche thread_id e a marcação some.

BEGIN;

ALTER TABLE item
    ADD COLUMN origem TEXT NOT NULL DEFAULT 'lista',
    ADD COLUMN revisar BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN foto_url TEXT,
    ADD COLUMN data_anuncio TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN aviso_autor_enviado_em TIMESTAMPTZ;

ALTER TABLE item ADD CONSTRAINT chk_item_origem_valor CHECK (origem IN ('lista', 'site'));

CREATE INDEX idx_item_data_anuncio ON item (data_anuncio DESC);

-- Busca sem acento e sem maiúscula (US-04). As duas extensões vêm na imagem oficial do Postgres.
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

COMMIT;
