-- Testes de validação para as invariantes de append-only e transição de status
-- Task: SCRUM-71 (subtarefa da SCRUM-45)
--
-- Roda dentro de uma transação e termina em ROLLBACK, sem deixar lixo:
-- psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f shared/testes/test_regras_banco.sql
-- Qualquer FALHA aborta o psql com erro; só NOTICEs de SUCESSO significam que passou.

BEGIN;

-- 1. Criar dados de teste
INSERT INTO item (id, thread_id, tipo, descricao, situacao, autor_email)
VALUES (999901, 'thread-teste-01', 'achado', 'Item para teste de DELETE', 'aberto', 'autor@cin.ufpe.br');

INSERT INTO mensagem_bruta (id, thread_id, mensagem_id, remetente, corpo)
VALUES (999901, 'thread-teste-01', '<msg-teste-01@cin.ufpe.br>', 'autor@cin.ufpe.br', 'Corpo de teste');

INSERT INTO evento (id, item_id, tipo_evento, situacao_anterior, situacao_nova, fonte, aplicado)
VALUES (999901, 999901, 'criacao', NULL, 'aberto', 'teste', TRUE);

INSERT INTO quarentena (id, thread_id, mensagem_bruta_id, motivo_retencao)
VALUES (999901, 'thread-teste-01', 999901, 'Motivo de teste');

INSERT INTO processamento (mensagem_id, thread_id, status)
VALUES ('<msg-teste-01@cin.ufpe.br>', 'thread-teste-01', 'processado');

-- 2. Validar que DELETE em 'processamento' é PERMITIDO (Decisão 13)
DELETE FROM processamento WHERE mensagem_id = '<msg-teste-01@cin.ufpe.br>';

-- 3. Validar bloco de teste para bloqueio de DELETE (deve falhar se tentar apagar)
DO $$
BEGIN
    BEGIN
        DELETE FROM item WHERE id = 999901;
        RAISE EXCEPTION 'FALHA: DELETE em "item" deveria ter sido bloqueado!';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'SUCESSO: DELETE em "item" bloqueado conforme esperado.';
    END;

    BEGIN
        DELETE FROM mensagem_bruta WHERE id = 999901;
        RAISE EXCEPTION 'FALHA: DELETE em "mensagem_bruta" deveria ter sido bloqueado!';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'SUCESSO: DELETE em "mensagem_bruta" bloqueado conforme esperado.';
    END;

    BEGIN
        DELETE FROM evento WHERE id = 999901;
        RAISE EXCEPTION 'FALHA: DELETE em "evento" deveria ter sido bloqueado!';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'SUCESSO: DELETE em "evento" bloqueado conforme esperado.';
    END;

    BEGIN
        DELETE FROM quarentena WHERE id = 999901;
        RAISE EXCEPTION 'FALHA: DELETE em "quarentena" deveria ter sido bloqueado!';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'SUCESSO: DELETE em "quarentena" bloqueado conforme esperado.';
    END;
END;
$$;

-- 3b. Validar bloqueio de UPDATE nas tabelas append-only (e liberação na quarentena)
DO $$
BEGIN
    BEGIN
        UPDATE mensagem_bruta SET corpo = 'alterado' WHERE id = 999901;
        RAISE EXCEPTION 'FALHA: UPDATE em "mensagem_bruta" deveria ter sido bloqueado!';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'SUCESSO: UPDATE em "mensagem_bruta" bloqueado conforme esperado.';
    END;

    BEGIN
        UPDATE evento SET fonte = 'alterada' WHERE id = 999901;
        RAISE EXCEPTION 'FALHA: UPDATE em "evento" deveria ter sido bloqueado!';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'SUCESSO: UPDATE em "evento" bloqueado conforme esperado.';
    END;

    -- Permitido: a quarentena muda quando o autor classifica a retida
    UPDATE quarentena SET resolvida = TRUE WHERE id = 999901;
    RAISE NOTICE 'SUCESSO: UPDATE em "quarentena" (resolvida) autorizado.';
END;
$$;

-- 3c. Validar que ocultar é irreversível
DO $$
BEGIN
    UPDATE item SET oculto = TRUE WHERE id = 999901;
    RAISE NOTICE 'SUCESSO: ocultar o item autorizado.';

    BEGIN
        UPDATE item SET oculto = FALSE WHERE id = 999901;
        RAISE EXCEPTION 'FALHA: reexibir o item (oculto TRUE -> FALSE) deveria ter sido bloqueado!';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'SUCESSO: reexibir o item bloqueado conforme esperado.';
    END;
END;
$$;

-- 3d. Validar o vocabulário de fonte_encerramento
DO $$
BEGIN
    BEGIN
        UPDATE item SET fonte_encerramento = 'palpite' WHERE id = 999901;
        RAISE EXCEPTION 'FALHA: fonte_encerramento fora do vocabulário deveria ter sido bloqueada!';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'SUCESSO: fonte_encerramento fora do vocabulário bloqueada conforme esperado.';
    END;

    UPDATE item SET fonte_encerramento = 'terceiro' WHERE id = 999901;
    RAISE NOTICE 'SUCESSO: fonte_encerramento "terceiro" aceita.';
    UPDATE item SET fonte_encerramento = NULL WHERE id = 999901;
END;
$$;

-- 4. Validar transições permitidas e proibidas de 'situacao', e o data_situacao
DO $$
DECLARE
    antes TIMESTAMPTZ;
    depois TIMESTAMPTZ;
BEGIN
    -- data_situacao de teste no passado, para ver a troca
    UPDATE item SET data_situacao = NOW() - INTERVAL '1 day' WHERE id = 999901;
    SELECT data_situacao INTO antes FROM item WHERE id = 999901;

    -- Permitido: aberto -> reivindicado
    UPDATE item SET situacao = 'reivindicado' WHERE id = 999901;
    RAISE NOTICE 'SUCESSO: Transição aberto -> reivindicado autorizada.';

    SELECT data_situacao INTO depois FROM item WHERE id = 999901;
    IF depois <= antes THEN
        RAISE EXCEPTION 'FALHA: data_situacao deveria ter avançado na transição!';
    END IF;
    RAISE NOTICE 'SUCESSO: data_situacao atualizada na transição.';

    -- Proibido: reivindicado -> aberto (retrocesso)
    BEGIN
        UPDATE item SET situacao = 'aberto' WHERE id = 999901;
        RAISE EXCEPTION 'FALHA: Transição reivindicado -> aberto deveria ter sido bloqueada!';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'SUCESSO: Transição reivindicado -> aberto bloqueada conforme esperado.';
    END;

    -- Permitido: reivindicado -> encerrado
    UPDATE item SET situacao = 'encerrado' WHERE id = 999901;
    RAISE NOTICE 'SUCESSO: Transição reivindicado -> encerrado autorizada.';

    -- Proibido: encerrado -> aberto (retrocesso)
    BEGIN
        UPDATE item SET situacao = 'aberto' WHERE id = 999901;
        RAISE EXCEPTION 'FALHA: Transição encerrado -> aberto deveria ter sido bloqueada!';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'SUCESSO: Transição encerrado -> aberto bloqueada conforme esperado.';
    END;

    -- Proibido: encerrado -> reivindicado (retrocesso)
    BEGIN
        UPDATE item SET situacao = 'reivindicado' WHERE id = 999901;
        RAISE EXCEPTION 'FALHA: Transição encerrado -> reivindicado deveria ter sido bloqueada!';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'SUCESSO: Transição encerrado -> reivindicado bloqueada conforme esperado.';
    END;
END;
$$;

-- 5. Validar exceção de desfecho direto (aberto -> encerrado)
INSERT INTO item (id, thread_id, tipo, descricao, situacao, autor_email)
VALUES (999902, 'thread-teste-02', 'achado', 'Item para teste de desfecho direto', 'aberto', 'autor2@cin.ufpe.br');

DO $$
BEGIN
    -- Permitido: aberto -> encerrado (exceção PO de desfecho)
    UPDATE item SET situacao = 'encerrado' WHERE id = 999902;
    RAISE NOTICE 'SUCESSO: Exceção de desfecho aberto -> encerrado autorizada.';
END;
$$;

ROLLBACK;
