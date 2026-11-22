# Fixture do roteiro de integração (SCRUM-82)

`anuncio-com-codigo.eml` é o e-mail pronto (US-07) de um item cadastrado pelo site, já passando pela
lista. Serve para conferir, à mão, que o worker liga a thread ao item pelo código do assunto e que a
marcação "ainda não foi para a lista" some de "Meus anúncios".

O código `AP-AAAAAA` é um marcador: troque pelo código do item que você cadastrou.

```bash
mkdir -p /tmp/eml-codigo
sed 's/AP-AAAAAA/AP-XXXXXX/' worker/testes/fixtures/site/anuncio-com-codigo.eml > /tmp/eml-codigo/01.eml
docker compose run --rm -v /tmp/eml-codigo:/eml worker python -m worker --fonte arquivos --dir /eml --uma-vez
```

Pessoa e endereço são fictícios (`fic.*`). O teste automático desse caminho fica em
`worker/testes/test_codigo_e_aviso.py`.
