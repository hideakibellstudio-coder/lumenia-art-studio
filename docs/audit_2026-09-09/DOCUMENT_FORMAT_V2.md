# Contrato LMN v2 — 10/09/2026

O arquivo é um ZIP com `manifest.json` UTF-8 e entradas declaradas pelo manifesto.
O leitor rejeita nomes ZIP duplicados, entradas extras, recursos ausentes,
tamanhos incorretos, referências fora do namespace e versões futuras.

| Entrada | Conteúdo |
|---|---|
| `layers/<uid>.rgba` | Pixels RGBA8 da camada raster, largura × altura × 4 bytes. |
| `masks/selection.gray` | Seleção com cobertura de 8 bits, largura × altura bytes; ausente quando não há seleção. |
| `assets/canvas.gray` | Textura do papel com um canal de 8 bits, dimensões próprias declaradas no manifesto. |

O manifesto conserva UIDs, hierarquia, grupo/filtro, parâmetros de filtro,
opacidade, blend, visibilidade, locks, clipping, camada ativa, câmera e papel.
`canvas_resource` contém escala, contraste, inversão, habilitação e os 256
valores da LUT da curva de textura. A reabertura compara o recurso restaurado
com o original. Alterar cor/visibilidade do papel conserva a textura incorporada.

Pontos de guia (`p0`–`p3`, `vpA`–`vpC`) são pares JSON `[x, y]`; o carregamento
reconstitui `QPointF`. Guias e simetria têm tipos, flags e números validados.
O controlador reinicializa seus defaults ao trocar de documento antes de aplicar
esses estados. Alterações de papel, guias, seleção e perfil invalidam o estado salvo.

Migrações explícitas: v0 → v1 fornece papel, câmera e estados auxiliares;
v1 → v2 fornece perfil 0, ausência de seleção/textura incorporada e declaração
explícita de camada vazia quando o legado não contém pixels. A migração não
modifica o objeto de origem. O campo `empty: true` tem esse significado também
em v2; novas gravações sempre escrevem o raster completo.

O salvamento exige contexto do motor correspondente ao documento e preserva a
geração anterior válida em `.bak`. A recuperação ignora sessões vivas; após
encerramento abrupto, oferece a cópia válida mais recente ou o backup quando a
principal estiver ausente/corrompida. Um teste de subprocesso usa `os._exit` para
validar a descoberta sem limpeza de sessão.

Salvar com uma transformação ainda ativa é rejeitado: nesse estágio, o motor
mantém temporariamente os pixels destacados fora da camada. O arquivo anterior
fica intacto até confirmar ou cancelar a transformação.

Limites explícitos: pixels continuam RGBA8; `color_profile_id` identifica o
catálogo atual de perfis/provas do motor, não incorpora um arquivo ICC. ICC real
e armazenamento de alta profundidade pertencem ao F-006. O formato não grava
histórico de undo entre sessões nem define máscaras de camada ainda inexistentes
no modelo. Preferências globais de renderização e presets de pincel continuam
nos respectivos sistemas de configuração/presets.

Configurações da aplicação têm `schema_version: 1`, independente da versão do
produto. A migração normaliza aliases de perfil e valores legados em inglês de
velocidade/atraso; tipos inválidos são descartados individualmente na leitura.
Atualizações inválidas de render são rejeitadas antes da mutação. Um schema
futuro deixa a configuração em modo de preservação, impedindo sobrescrita.
