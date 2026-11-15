-- Migração: Garantir append-only e transição estrita de status
-- Task: SCRUM-71 (subtarefa da SCRUM-45)
-- Área: shared/migrations (Área protegida - revisão obrigatória: Miguel)
--
-- Invariantes implementadas:
-- 1. Invariante 4: Nada é apagado.
--    Tabelas mensagem_bruta, evento, quarentena e item não aceitam DELETE.
--    mensagem_bruta e evento também não aceitam UPDATE: são append-only de verdade.
--    quarentena aceita UPDATE, porque `resolvida` muda quando o autor classifica a retida.
--    Remoção de item é exclusivamente lógica via coluna 'oculto = TRUE', e é irreversível
--    (decisão do PO em 28/10/2026, US-15).
--    Exceção única permitida pelo sistema: tabela 'processamento' (Decisão 13).
--
-- 2. Invariante 2: situacao só avança: aberto -> reivindicado -> encerrado.
--    Nunca retrocede e nunca pula etapa, com a única exceção autorizada pelo PO:
--    declaração de desfecho de 'aberto' direto a 'encerrado' (casos 19 e 20).
--    A cada transição aplicada, `data_situacao` recebe NOW() (US-04 mostra há quanto tempo).
--
-- 3. `fonte_encerramento` só aceita 'confirmação do autor' ou 'terceiro' (ou NULL).
--
-- Os itens de UPDATE, oculto irreversível, data_situacao e o CHECK foram pedidos pelo PO em
-- 13/11/2026 (PR #17) e entraram nesta mesma migração antes de qualquer banco ser implantado.

BEGIN;

-- ============================================================================
-- 0. LACUNAS DO SCHEMA INICIAL
-- ============================================================================

-- Momento da última transição de situação (o contrato expõe `data_situacao`).
ALTER TABLE item ADD COLUMN data_situacao TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Vocabulário fechado da fonte do encerramento (ARQUITETURA §2.2, regra 1).
ALTER TABLE item ADD CONSTRAINT chk_item_fonte_encerramento
    CHECK (fonte_encerramento IS NULL OR fonte_encerramento IN ('confirmação do autor', 'terceiro'));

-- ============================================================================
-- 1. FUNÇÃO E TRIGGERS PARA BLOQUEIO DE DELETE (INVARIANTE 4)
-- ============================================================================

CREATE OR REPLACE FUNCTION proibir_delete_append_only()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Operação DELETE proibida na tabela "%". O sistema é append-only (Invariante 4). Remoção de itens deve ser feita via coluna "oculto".', TG_TABLE_NAME
        USING ERRCODE = 'check_violation';
END;
$$ LANGUAGE plpgsql;

-- Bloqueio em mensagem_bruta
DROP TRIGGER IF EXISTS trg_proibir_delete_mensagem_bruta ON mensagem_bruta;
CREATE TRIGGER trg_proibir_delete_mensagem_bruta
    BEFORE DELETE ON mensagem_bruta
    FOR EACH ROW
    EXECUTE FUNCTION proibir_delete_append_only();

-- Bloqueio em item
DROP TRIGGER IF EXISTS trg_proibir_delete_item ON item;
CREATE TRIGGER trg_proibir_delete_item
    BEFORE DELETE ON item
    FOR EACH ROW
    EXECUTE FUNCTION proibir_delete_append_only();

-- Bloqueio em evento
DROP TRIGGER IF EXISTS trg_proibir_delete_evento ON evento;
CREATE TRIGGER trg_proibir_delete_evento
    BEFORE DELETE ON evento
    FOR EACH ROW
    EXECUTE FUNCTION proibir_delete_append_only();

-- Bloqueio em quarentena
DROP TRIGGER IF EXISTS trg_proibir_delete_quarentena ON quarentena;
CREATE TRIGGER trg_proibir_delete_quarentena
    BEFORE DELETE ON quarentena
    FOR EACH ROW
    EXECUTE FUNCTION proibir_delete_append_only();

-- Nota: A tabela 'processamento' NÃO recebe esta trigger porque o DELETE nela
-- é o mecanismo intencional de reprocessamento (Decisão 13 e ARQUITETURA §2.2).

-- ============================================================================
-- 2. FUNÇÃO E TRIGGERS PARA BLOQUEIO DE UPDATE (INVARIANTE 4, APPEND-ONLY)
-- ============================================================================

CREATE OR REPLACE FUNCTION proibir_update_append_only()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Operação UPDATE proibida na tabela "%". Ela é append-only (Invariante 4): registre uma linha nova em vez de alterar.', TG_TABLE_NAME
        USING ERRCODE = 'check_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_proibir_update_mensagem_bruta ON mensagem_bruta;
CREATE TRIGGER trg_proibir_update_mensagem_bruta
    BEFORE UPDATE ON mensagem_bruta
    FOR EACH ROW
    EXECUTE FUNCTION proibir_update_append_only();

DROP TRIGGER IF EXISTS trg_proibir_update_evento ON evento;
CREATE TRIGGER trg_proibir_update_evento
    BEFORE UPDATE ON evento
    FOR EACH ROW
    EXECUTE FUNCTION proibir_update_append_only();

-- ============================================================================
-- 3. OCULTAR É IRREVERSÍVEL (US-15, decisão do PO em 28/10/2026)
-- ============================================================================

CREATE OR REPLACE FUNCTION proibir_reexibir_item()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.oculto = TRUE AND NEW.oculto = FALSE THEN
        RAISE EXCEPTION 'Item % foi ocultado e não pode voltar ao catálogo pelo sistema (US-15). Reexibir é operação manual, fora do site.', OLD.id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_proibir_reexibir_item ON item;
CREATE TRIGGER trg_proibir_reexibir_item
    BEFORE UPDATE OF oculto ON item
    FOR EACH ROW
    EXECUTE FUNCTION proibir_reexibir_item();

-- ============================================================================
-- 4. FUNÇÃO E TRIGGER PARA TRANSIÇÃO ESTRITA DE SITUAÇÃO (INVARIANTE 2)
-- ============================================================================

CREATE OR REPLACE FUNCTION validar_transicao_situacao_item()
RETURNS TRIGGER AS $$
BEGIN
    -- Se a situação não mudou, permite a atualização de outros campos
    IF OLD.situacao = NEW.situacao THEN
        RETURN NEW;
    END IF;

    -- Regra 1: Se o item está 'aberto', só pode avançar para 'reivindicado'
    -- ou direto para 'encerrado' (exceção autorizada de desfecho).
    IF OLD.situacao = 'aberto' THEN
        IF NEW.situacao IN ('reivindicado', 'encerrado') THEN
            NEW.data_situacao := NOW();
            RETURN NEW;
        END IF;
    END IF;

    -- Regra 2: Se o item está 'reivindicado', só pode avançar para 'encerrado'.
    -- É proibido retroceder para 'aberto'.
    IF OLD.situacao = 'reivindicado' THEN
        IF NEW.situacao = 'encerrado' THEN
            NEW.data_situacao := NOW();
            RETURN NEW;
        END IF;
    END IF;

    -- Regra 3: Se o item já está 'encerrado', a situação NUNCA mais muda.
    -- É proibido retroceder para 'reivindicado' ou 'aberto'.
    IF OLD.situacao = 'encerrado' THEN
        RAISE EXCEPTION 'Transição de situação inválida no item %: não é permitido alterar status de um item já "encerrado" (Invariante 2).', OLD.id
            USING ERRCODE = 'check_violation';
    END IF;

    -- Qualquer outra combinação não autorizada dispara erro
    RAISE EXCEPTION 'Transição de situação inválida no item %: tentou mudar de "%" para "%". O status só avança (Invariante 2).',
        OLD.id, OLD.situacao, NEW.situacao
        USING ERRCODE = 'check_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validar_transicao_situacao_item ON item;
CREATE TRIGGER trg_validar_transicao_situacao_item
    BEFORE UPDATE OF situacao ON item
    FOR EACH ROW
    EXECUTE FUNCTION validar_transicao_situacao_item();

COMMIT;
