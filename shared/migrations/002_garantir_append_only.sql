-- Migração: Garantir append-only e transição estrita de status
-- Task: SCRUM-71 (subtarefa da SCRUM-45)
-- Área: shared/migrations (Área protegida - revisão obrigatória: Miguel)
--
-- Invariantes implementadas:
-- 1. Invariante 4: Nada é apagado.
--    Tabelas mensagem_bruta, evento, quarentena e item não aceitam DELETE.
--    Remoção de item é exclusivamente lógica via coluna 'oculto = TRUE'.
--    Exceção única permitida pelo sistema: tabela 'processamento' (Decisão 13).
--
-- 2. Invariante 2: situacao só avança: aberto -> reivindicado -> encerrado.
--    Nunca retrocede e nunca pula etapa, com a única exceção autorizada pelo PO:
--    declaração de desfecho de 'aberto' direto a 'encerrado' (casos 19 e 20).

BEGIN;

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
-- 2. FUNÇÃO E TRIGGER PARA TRANSIÇÃO ESTRITA DE SITUAÇÃO (INVARIANTE 2)
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
            RETURN NEW;
        END IF;
    END IF;

    -- Regra 2: Se o item está 'reivindicado', só pode avançar para 'encerrado'.
    -- É proibido retroceder para 'aberto'.
    IF OLD.situacao = 'reivindicado' THEN
        IF NEW.situacao = 'encerrado' THEN
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
