# Equipe

| Pessoa | Papel | Jira (displayName) | GitHub |
|---|---|---|---|
| Luiz Taiguara | PO — decisões de produto, aceite das histórias | `ltog` | `LuizTaiguara` |
| Miguel | Backend; revisor de `shared/` e do contrato | `luiz miguel` (não é o Luiz!) | `oliveiraluizmiguel57-blip` |
| Cleyton | Backend (worker) | Cleyton junior da silva cardoso 
| Samuel | Backend (worker) | Samuel Renan Mendes |  `samuel renan`| `samukarn` | |
| Pedro | Front (site) | Pedro Henrique Cabral Galdino dos Santos | _preencher_ |
| Rafael | Front (site) | RAFAEL DUMKE DE MEDEIROS | _preencher_ |
| Klarissa | UX | Klarissa Andrade de Morais | _preencher_ |

> **Primeira tarefa de cada pessoa:** preencher seu usuário do GitHub nesta tabela, usando o
> fluxo completo (branch → commit → `/abrir-pr`). É o treino do fluxo antes da primeira task real.

## Quem revisa o quê (F-08, SCRUM-83)

PR é obrigatório, e **ninguém faz merge do próprio**. A revisão sai em até 24h.

| O PR mexe em… | Revisor |
|---|---|
| `worker/` | Cleyton ↔ Samuel (um revisa o outro) |
| `shared/` (contrato, schema) | **Miguel**, sempre |
| `site/` | Pedro ↔ Rafael. Inclua o Miguel se o PR tocar no consumo do contrato |
| `AGENTS.md`, `.agents/`, `docs/` | Luiz |

- **O revisor checa as invariantes**: vazamento de e-mail, status retrocedendo, `DELETE` em vez de ocultar, regra de visibilidade no cliente.
- Estilo não é com o revisor, é com o linter.
- Aceitar a história contra o critério de aceitação é do **PO**, não do revisor.
