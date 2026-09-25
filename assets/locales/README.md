# `assets/locales/` — traduções da interface

**Responsabilidade:** as mensagens da interface em pt_BR, en_US, es_ES e ja_JP, por seção (`menu`, `status`, `tool_options`...).

## Porta de entrada

`ui/infrastructure/i18n` (`tr(chave, padrão)`); en_US é o fallback quando a chave falta no idioma ativo.

## Regras

- Chave nova entra nos quatro arquivos no mesmo commit (`tests/test_i18n_keys_exist.py` confere cada `tr(...)` e `Text(...)` literal).
- Arquivos em UTF-8, indentação de 2 espaços, sem escapar acentos.
