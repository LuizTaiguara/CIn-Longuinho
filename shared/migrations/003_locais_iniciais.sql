-- Migração: vocabulário inicial de locais do CIn
-- Task: SCRUM-64 (F-07, levantamento do espaço físico feito pelo PO; docs/espaco-fisico/)
-- Área: shared/migrations (Área protegida - revisão obrigatória: Miguel)
--
-- O `nome` é o valor que GET /api/locais devolve e que o filtro `local` de GET /api/itens aceita.
-- Os nomes de uso ("Grad01", "Grad 05", "lab de hardware") ficam com o parser do worker e com a
-- busca, não aqui (ver "Nomes das Grads" no levantamento).
-- Para incluir um local novo, acrescente uma linha. Para tirar um de circulação, `ativo = FALSE`.

BEGIN;

INSERT INTO local (nome, bloco, ponto_custodia) VALUES
    ('Grad 1', 'Vermelho', FALSE),
    ('Grad 2', 'Vermelho', FALSE),
    ('Grad 3', 'Vermelho', FALSE),
    ('Grad 4', 'Vermelho', FALSE),
    ('Grad 5', 'Vermelho', FALSE),
    ('Laboratório de hardware', 'Vermelho', FALSE),
    ('Laboratório de pós-graduação', 'Vermelho', FALSE),
    ('Anfiteatro', 'Vermelho', FALSE),
    ('Gerinfra (sala B021)', NULL, TRUE)
ON CONFLICT (nome) DO NOTHING;

COMMIT;
