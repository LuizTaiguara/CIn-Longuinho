-- Testes de validação para as invariantes de append-only e transição de status
-- Task: SCRUM-71 (subtarefa da SCRUM-45)
--
-- Pode ser executado com psql ou dentro de uma transação com ROLLBACK:
-- psql "$DATABASE_URL" -f shared/testes/test_regras_banco.sql

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

-- 4. Validar transições permitidas e proibidas de 'situacao'
DO $$
BEGIN
    -- Permitido: aberto -> reivindicado
    UPDATE item SET situacao = 'reivindicado' WHERE id = 999901;
    RAISE NOTICE 'SUCESSO: Transição aberto -> reivindicado autorizada.';

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
