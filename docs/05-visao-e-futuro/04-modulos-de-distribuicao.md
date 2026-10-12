# Lumenia — Módulos de Distribuição: Diagnóstico, Licenciamento e Atualização

Oct 7, 2026 · @hide

Para sair da Alpha e começar a vender, o Lumenia precisa de três módulos que hoje não existem: **diagnóstico** (receber os crashes dos usuários), **licenciamento** (com um gerador de licenças separado) e **atualização** (baixar só o que mudou, sem reinstalar). Nenhum deles exige mudar a arquitetura ARCcC do motor, da ponte ou da UI: entram como pastas novas em `infrastructure/` e `core/`, mais uma troca no pipeline de distribuição.

> **Situação em 2026-10-11.** Os três módulos deste documento já foram implementados na branch
> `feature/distribution-modules` (commits `e825a32` e `c5aacce`). O texto abaixo é a **análise de 7 de outubro que
> os originou** e foi mantido como registro das opções avaliadas; onde o código seguiu outro caminho (a
> assinatura é ECDSA P-256 pelo CNG do Windows, não Ed25519 com Monocypher, por exemplo), a seção
> [Estado da implementação](#estado-da-implementação) diz o que existe de fato.

> **Atualização em 2026-10-12.** O **licenciamento foi removido do programa** (decisão do dono do projeto, que vai
> distribuir sem chave de ativação por enquanto). Saíram o verificador e a marca d'água do motor, o serviço, o diálogo de
> licença, as boas-vindas do modo gratuito e o botão da barra de status; toda versão de atualização encontrada passa a
> ser oferecida. O diagnóstico e a atualização ficaram como estão. O código removido está na tag `archive/licensing-v1`
> e o gerador de licenças (repositório privado) não foi tocado. As partes deste texto sobre licença descrevem o que
> existia até essa tag.

## Estado atual

Análise feita no fork `lumenia-art-studio-main - fork antigravity`, versão 0.2.0 Alpha.

| Área | Como está hoje | O que significa para os módulos |
| --- | --- | --- |
| Stack | Motor C++20 (`aladyn_engine_native.pyd`, pybind11) e UI PySide6 6.11 | A verificação de licença e o registro de crash nativo podem morar no `.pyd` |
| Empacotamento | Nuitka 4.2 `--standalone` gera `Lumenia.dist/`; o código Python vai compilado dentro do `Lumenia.exe` | Bom contra engenharia reversa; qualquer mudança em Python altera o `.exe` inteiro, então atualização precisa de delta binário |
| Instalador | Inno Setup (`scripts/lumenia_installer.iss`), sem assinatura de código, aponta para itch.io | Será substituído pelo instalador do Velopack (módulo 3) |
| Manifesto | `release-manifest.json` com SHA-256 de cada arquivo distribuído | Base pronta para conferir integridade |
| Logging | `logger.py`: log rotativo de 5 × 5 MB, `sys.excepthook`, mensagens do Qt | Fonte dos relatórios de erro Python |
| Crash nativo | `crash_log.py`: `faulthandler` grava `native_crash.log` e o arquivo é arquivado na abertura seguinte | Mostra só a pilha **Python**; a função C++ que quebrou fica invisível. Os PDBs não são gerados (`/O2` sem `/Zi`) |
| "Telemetria" | `EngineTelemetry.hpp` mede o traço (latência, dabs, tiles) para o painel F12 | É um painel de desempenho, não relatório de erros; nada sai da máquina |
| Feedback | `Send_Feedback.html` abre um `mailto:` | Não há nenhum código de rede no app |
| Dados do usuário | `writable_data_dir()` grava em `data\` ao lado do executável, com reserva em `%APPDATA%` | Com atualização por pasta versionada, esses dados seriam apagados (módulo 3) |
| EULA | Seção 5 promete "100% offline"; seção 1 concede uso comercial gratuito | Precisa ser reescrita antes de enviar dados ou vender licença |

Para não confundir com o painel F12, o módulo novo de erros é chamado de **diagnóstico**, não de telemetria.

&#91;embedded content: os três módulos por camada ARCcC · o que cruza a fronteira do app\]

Só três coisas cruzam a fronteira do app: o relatório de erro sai para o Sentry, a licença assinada chega do gerador (pelo comprador) e as atualizações chegam do feed.

## Módulo 1 — Diagnóstico e relatório de erros

Recomendação: **Sentry**, com envio opcional escolhido pelo usuário, cobrindo erros Python e quedas nativas por minidump. O objetivo é ver o crash agrupado, por versão, com a função C++ exata que quebrou.

### Opções

| Opção | Prós | Contras |
| --- | --- | --- |
| **Sentry (SaaS)** — `sentry-sdk` + upload de minidump | Agrupa erros iguais, mostra a versão em que aparecem, simboliza o C++ com os PDBs, tem plano gratuito | Dados num serviço de terceiro (declarar na política de privacidade) |
| **Self-hosted** — Sentry self-hosted ou GlitchTip | Dados ficam com você | Servidor para manter; GlitchTip tem suporte fraco a crash nativo |
| **Próprio** — zip enviado a um endpoint (Cloudflare Worker, Supabase, FastAPI) | Controle total, custo quase zero | Agrupamento e simbolização feitos à mão |

### Como funciona

1. **Consentimento no primeiro uso.** Um diálogo pergunta se o usuário aceita enviar relatórios de erro anônimos. A escolha vai para o `ConfigManager` e pode ser mudada nas Preferências. Sem consentimento, nada sai da máquina.
2. **Erros Python.** O `sentry-sdk` entra pela integração de `logging`, ligada dentro de `setup_senior_logging`. O `sys.excepthook` e o handler do Qt que já existem continuam valendo.
3. **Quedas nativas.** Um handler em `engine/infrastructure/crash/` usa `SetUnhandledExceptionFilter` + `MiniDumpWriteDump` (dbghelp) para gravar um `.dmp`. O `faulthandler` continua gravando a pilha Python ao lado.
4. **Envio na abertura seguinte.** O ponto que hoje arquiva o `native_crash.log` passa a mostrar "O Lumenia fechou inesperadamente. Enviar relatório?". Se o usuário aceitar, sobem o `.dmp`, o final do log e a versão.
5. **Simbolização.** O build de release passa a compilar com `/Zi` e linkar com `/DEBUG`. O PDB de cada versão é guardado, ligado ao `extension_sha256` que o `native-build.json` já registra, e enviado ao Sentry.

### Dados enviados

- **Sim:** versão e canal, sistema operacional, GPU, variante SIMD (`scalar`/`avx2`), pilha de chamadas, um ID de instalação aleatório.
- **Nunca:** conteúdo do canvas, arquivos do usuário, caminhos com nome de usuário (removidos por um filtro `before_send`), e-mail ou chave de licença.

Estatística de uso (quais ferramentas são usadas) fica fora desta fase. Se entrar depois, também será opcional.

### Onde fica no código

| Pasta | Responsabilidade |
| --- | --- |
| `ui/core/diagnostics/` | Regras puras: consentimento, o que pode ser enviado, filtro de dados pessoais |
| `ui/infrastructure/diagnostics/` | Adaptador do `sentry-sdk`, coleta do pacote do crash, envio; o único lugar que importa o Sentry |
| `engine/infrastructure/crash/` | Handler de minidump no motor nativo |
| `ui/boundary/` | Diálogo de consentimento, aviso de crash, opção nas Preferências |

## Módulo 2 — Licenciamento e gerador de licenças

Recomendação: começar com **licença offline assinada com Ed25519**, conferida em Python e de novo dentro do motor C++, e adicionar **ativação online** numa segunda fase. Todo app desktop pode ser crackeado; o objetivo é tornar a pirataria trabalhosa e o caminho honesto o mais fácil.

### Modelos

| Modelo | Como funciona | Protege contra | Não protege contra |
| --- | --- | --- | --- |
| **Offline assinada (Ed25519)** | O gerador assina os dados com a chave privada; o app só tem a pública | Gerador de chaves pirata | A mesma chave compartilhada entre pessoas |
| **Ativação online + certificado offline** | O servidor amarra a chave à máquina, com limite de máquinas, e devolve um certificado assinado renovado periodicamente | Compartilhamento, licenças vazadas ou reembolsadas (revogação) | Patch no binário |
| **Plataforma** — Steam, Lemon Squeezy, Gumroad, Keygen.sh | A API da plataforma ativa e valida | O mesmo que a ativação online, sem manter servidor | Patch no binário; depende do fornecedor |

### Formato da licença

```
LUMENIA-<base32(payload)>.<base32(assinatura Ed25519)>

payload (JSON canônico ou CBOR):
{ "v":1, "lid":"L-000123", "sku":"pro", "name":"Fulano", "email_h":"<sha256>",
  "iat":"2026-10-07", "upd_until":"2027-10-07", "max_ver":"1.x", "machine":null }
```

- `upd_until` implementa o modelo "perpétua com 1 ano de atualizações" e é lido pelo módulo 3.
- `machine` fica vazio na fase 1 e é preenchido pela ativação online na fase 2.
- O e-mail entra só como hash; o nome aparece no "Sobre" e na splash ("Licenciado para Fulano"), o que desestimula compartilhar a chave.

### Verificação dupla

- **Interface (Python):** experiência do usuário — diálogo de ativação, status, mensagens de erro.
- **Motor (C++):** onde a licença vale de fato. Uma função `license_apply(token)` dentro do `.pyd` confere a assinatura com o **Monocypher** (dois arquivos `.c`/`.h`, licença BSD/CC0, `crypto_ed25519_check` compatível com o `cryptography` usado no gerador). As funções premium da fachada consultam esse estado. Para burlar, é preciso mexer no binário nativo, não só trocar um `return True` em Python.
- A regra "só o `bridge_client/` importa `aladyn_engine_native`" continua valendo.

&#91;embedded content: fluxo de ativação · verificação em Python e em C++\]

A chave privada nunca sai do gerador; o app só carrega a chave pública, nos dois lados da ponte.

### O que acontece sem licença

Preferir um **modo gratuito com limites** a um teste de 30 dias. O teste offline depende do relógio do sistema e de arquivos escondidos, fáceis de burlar; o modo limitado não depende de nada disso. Exemplos de limite: marca d'água na exportação (o plugin de gravação já tem uma pronta), salvar `.lmn` bloqueado ou número máximo de camadas.

### Impressão digital da máquina (fase 2)

Hash com sal de `HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid` mais o serial do volume do sistema, aceitando que um dos dois mude (troca de disco, reinstalação do Windows).

### Medidas de proteção baratas

- Nome do comprador visível no app.
- Lista de IDs revogados embutida em cada versão nova.
- Verificações em pontos diferentes do código, não só na abertura.

### Onde fica no código

| Pasta | Responsabilidade |
| --- | --- |
| `ui/core/licensing/` | Modelo da licença, estado, regras do que cada SKU libera; sem dependências externas |
| `ui/infrastructure/licensing/` | Onde a licença fica salva, impressão digital, cliente de ativação |
| `engine/infrastructure/licensing/` | Verificação nativa com Monocypher e o estado consultado pela fachada |
| `ui/boundary/` | Ajuda › Licença, diálogo de ativação, "Licenciado para" |

### Gerador de licenças

Fica num **repositório separado e privado**. A chave privada nunca entra no repositório do Lumenia.

| Comando | O que faz |
| --- | --- |
| `keygen` | Cria o par de chaves; a privada é guardada cifrada com senha ou num cofre |
| `issue --name --email --sku --upd-until` | Gera e assina uma licença |
| `revoke <lid>` | Marca uma licença como revogada |
| `export-revocations` | Gera a lista de revogadas para embutir na próxima versão |

- Ferramenta de linha de comando em Python com `cryptography`.
- Registro em SQLite de toda licença emitida: lid, comprador, data, pedido, status.
- Na fase 2 vira um webhook: a plataforma de venda avisa da compra, a licença é emitida e enviada por e-mail automaticamente.

## Módulo 3 — Atualização

Recomendação: **Velopack**. Ele instala por usuário (sem UAC), baixa só os bytes que mudaram e troca a versão de uma vez quando o app fecha, voltando para a anterior se algo falhar. O Lumenia já é empacotado como pasta (Nuitka `--standalone`), que é o formato que o Velopack exige.

### Por que reinstalar quebra programas no Windows

O problema não é reinstalar, é sobrescrever a pasta do programa no lugar:

- **Arquivos travados:** uma DLL ou `.pyd` carregada não pode ser sobrescrita, e a atualização fica pela metade.
- **Mistura de versões:** arquivos da versão antiga continuam na pasta junto com os da nova.
- **Permissão:** instalar em `Program Files` exige UAC a cada atualização.
- **Antivírus:** pode pôr um arquivo em quarentena no meio da cópia.

### Opções

| Opção | Tamanho do download | Esforço | Comentário |
| --- | --- | --- | --- |
| **Velopack** | Só os bytes que mudaram (delta binário) | Baixo | SDK Python oficial (`velopack`); gera Setup, atalho, desinstalação, delta e troca segura |
| **Atualizador próprio** sobre o `release-manifest.json` | Arquivos que mudaram (+ delta, se implementado) | Alto | Controle total; você escreve lançador, troca de pasta, retorno e gerador de patches |
| **tufup** (TUF em Python) | Patch bsdiff | Médio | Forte em segurança da cadeia; pensado para PyInstaller |
| **MSIX** | Diferencial nativo | Alto | Exige certificado e impõe sandbox ao app |
| **itch.io + butler** | Patch automático | Mínimo | Só para quem usa o app desktop do itch |

O delta binário é necessário porque o Nuitka compila todo o Python dentro do `Lumenia.exe`: qualquer mudança de código altera esse arquivo inteiro. As DLLs do Qt, a maior parte do pacote, quase nunca mudam e não são baixadas de novo.

### Como fica na máquina do usuário

```
%LocalAppData%\Lumenia\        instalado por usuário, sem UAC
  Update.exe                    faz a troca de versão
  current\                      o Lumenia.dist atual (exe, Qt, aladyn_engine_native.pyd)
  packages\                     pacotes completos e deltas baixados

%AppData%\Lumenia\              configuração, logs, presets, licença — a atualização nunca mexe aqui
```

Canais separados (`--channel alpha`, `beta`, `stable`) permitem testar com um grupo antes de liberar para todos.

&#91;embedded content: fluxo de uma atualização · 6 passos, 1 retorno\]

Download e conferência acontecem com o app aberto; a troca só acontece com ele fechado, e se falhar a versão anterior continua.

### O que muda no projeto

**1. `main.py`** — o Velopack roda antes de qualquer import da UI, porque trata eventos de instalação e pode reiniciar o processo:

```python
if __name__ == "__main__":
    import velopack
    velopack.App().run()          # antes de qualquer import da UI

    current_dir = os.path.dirname(os.path.abspath(__file__))
    ...
```

**2. `runtime_paths.writable_data_dir()`** — corrige um bug que a atualização causaria. Hoje os dados vão para `data\` ao lado do executável; com o Velopack essa pasta fica dentro de `current\`, substituída a cada versão, e o usuário perderia configuração, logs e licença.

```python
def writable_data_dir() -> Path:
    if not is_packaged():
        return app_root()
    if (app_root() / "portable.flag").is_file():      # versão zip portátil: dados ao lado
        target = app_root() / "data"
    else:                                              # instalado: fora da pasta versionada
        target = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    target.mkdir(parents=True, exist_ok=True)
    return target
```

Quem instalou a Alpha pelo Inno precisa de uma migração única: copiar o `data\` antigo para `%AppData%` na primeira abertura.

**3. Módulo novo:**

| Pasta | Responsabilidade |
| --- | --- |
| `ui/core/updates/` | Regras puras: canal, quando checar, se `upd_until` da licença cobre a versão nova |
| `ui/infrastructure/updater/` | Adaptador do `velopack`; o único lugar que importa a biblioteca |
| `ui/boundary/` | Ajuda › Verificar atualizações, aviso discreto, "Reiniciar agora" |

O adaptador roda fora da thread da UI e nunca derruba o app por falha de rede:

```python
# ui/infrastructure/updater/velopack_updater.py
from __future__ import annotations
from PySide6 import QtCore
from ui.infrastructure.runtime_paths import is_packaged

class UpdateWorker(QtCore.QObject):
    available = QtCore.Signal(object)   # UpdateInfo
    ready = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, feed_url: str):
        super().__init__()
        self._feed_url = feed_url
        self._info = None

    @QtCore.Slot()
    def check_and_download(self) -> None:
        if not is_packaged():
            return                                  # desenvolvimento: nada para atualizar
        try:
            import velopack
            manager = velopack.UpdateManager(self._feed_url)
            info = manager.check_for_updates()
            if not info:
                return
            self.available.emit(info)
            manager.download_updates(info)          # baixa o delta
            self._info, self._manager = info, manager
            self.ready.emit(info)
        except Exception as exc:                    # rede ou feed: nunca derruba o app
            self.failed.emit(str(exc))

    def apply_and_restart(self) -> None:
        if self._info is not None:
            self._manager.apply_updates_and_restart(self._info)
```

**4. Build de release** — o `lumenia_installer.iss` sai (dois instaladores criariam duas instalações em conflito). Um `scripts/build_release.py` encadeia `build_native.py`, `build_portable.py`, o empacotamento e o envio:

```
vpk pack --packId LumeniaTeam.Lumenia --packVersion 0.2.1 --packDir <...>\Lumenia.dist --mainExe Lumenia.exe --channel alpha
```

O delta é gerado automaticamente quando os pacotes da versão anterior estão na pasta de saída.

**Ajustes menores:**

- Incluir o pacote `velopack` no comando do Nuitka.
- Atualizar `tests/test_app_version.py`, que hoje confere a versão no `.iss`.
- Registrar a associação `.lmn`/`.lumenia` pelo próprio app em `HKCU\Software\Classes`, nos ganchos de instalação (antes era o Inno).
- O `vpk` precisa do .NET SDK só na máquina de build; o usuário final não precisa.

## Integração e riscos

Os três módulos compartilham dois dados: a **versão/canal** e a **licença**. Fora isso são independentes e podem ser entregues em qualquer ordem.

### Como se ligam

- **Licença → atualização:** o `upd_until` decide se o usuário recebe a versão nova. Quem tem "perpétua com 1 ano de atualizações" para de receber versões depois da data, mas continua usando a que tem.
- **Atualização → diagnóstico:** cada relatório de erro leva versão e canal, o que mostra se um crash sumiu depois de uma atualização.
- **Diagnóstico ↔ licença:** nenhuma ligação. O relatório não carrega chave nem e-mail.
- **Dados persistentes:** licença, consentimento e configuração ficam em `%AppData%\Lumenia\`, fora da pasta que a atualização substitui.

### Riscos

| Risco | Por que importa | O que fazer |
| --- | --- | --- |
| **LGPL do PySide6** | O usuário tem direito de substituir as DLLs do Qt | Verificação de integridade só nos arquivos próprios (`.pyd`, `.exe`), nunca nas DLLs do Qt |
| **LGPD e EULA** | A EULA promete "100% offline" e concede uso comercial gratuito | Envio de erros opcional, política de privacidade, termos de licença paga (por usuário, máquinas, transferência). Revisão jurídica antes de vender |
| **Sem assinatura de código** | O SmartScreen assusta o comprador no instalador | Certificado de assinatura; o `vpk` assina executável e Setup |
| **Limites do anti-pirataria** | Qualquer verificação no cliente pode ser removida com patch | Verificação no C++, checagens espalhadas, nome do comprador visível; aceitar que o objetivo é encarecer, não impedir |
| **Migração da Alpha** | Testadores instalaram pelo Inno, com dados ao lado do executável | Migração única do `data\` para `%AppData%`; orientar a desinstalar a versão Inno |
| **Chave privada vazada** | Quem tiver a chave gera licenças válidas | Repositório separado, chave cifrada, backup offline; prever rotação de chave (`v` no payload) |

O Nuitka já dificulta bastante a engenharia reversa. A versão comercial dele tem proteções extras, como cifrar arquivos de dados, mas só vale considerar depois do lançamento.

## Plano em fases

A fase 1 basta para o primeiro lançamento pago e não exige servidor próprio: só um lugar para hospedar o feed de atualizações e uma conta no Sentry.

1. **Fase 1 — Lançamento pago**
   1. Correção do `writable_data_dir` e migração dos dados da Alpha.
   2. Atualização com Velopack, canais e `build_release.py`.
   3. Licença offline Ed25519 verificada em Python e C++, modo gratuito definido.
   4. Gerador de licenças em linha de comando, em repositório separado.
   5. Diagnóstico com Sentry, minidump e PDBs, com consentimento.
   6. EULA e política de privacidade reescritas.
2. **Fase 2 — Ativação online:** limite de máquinas e revogação, via Keygen.sh, Lemon Squeezy ou Cloudflare Worker próprio; emissão automática de licença por webhook da venda.
3. **Fase 3 — Endurecimento:** checagens distribuídas, assinatura de código, avaliar o Nuitka comercial.

### Decisões pendentes

- [ ] Onde vender: itch.io, Lemon Squeezy, Gumroad ou Steam?
- [ ] Modelo de licença: perpétua com 1 ano de atualizações ou assinatura?
- [ ] Sem licença: modo gratuito limitado ou teste por tempo? Se limitado, o que fica bloqueado?
- [ ] Relatório de erros: Sentry na nuvem, self-hosted ou endpoint próprio?
- [ ] Hospedagem das atualizações: GitHub Releases ou bucket R2/S3?
- [ ] Certificado de assinatura de código: qual fornecedor e quando?

## Estado da implementação

Conferido nos READMEs das pastas e no código dos commits `e825a32` (módulos) e `c5aacce` (modo gratuito
anunciado). Cada linha compara o que este documento recomendou com o que existe.

### Licenciamento e gerador

**Removido do programa em 2026-10-12** (tag `archive/licensing-v1`); a tabela abaixo é o registro do que existia.

| Tema | Recomendado acima | Implementado |
| --- | --- | --- |
| Assinatura | Ed25519, conferida com Monocypher no motor | **ECDSA P-256 sobre SHA-256 pelo CNG do Windows** (`bcrypt.dll`), sem criptografia escrita à mão. Fora do Windows toda licença é `unsupported`. O gerador usa a mesma curva, com `cryptography` |
| Formato | `LUMENIA-<base32>.<base32>`, conteúdo JSON ou CBOR (`lid`, `upd_until`, `max_ver`, `machine`) | `LUMENIA1-<base32 do conteúdo>.<base32 da assinatura>`; o conteúdo são linhas `chave=valor` (`v`, `id`, `sku`, `name`, `mail`, `iat`, `upd`, `exp`, `mid`). Chave desconhecida ou repetida recusa a licença. O e-mail vai só como SHA-256 |
| Sem licença | Modo gratuito com limites | Modo gratuito com todos os recursos; a exportação sai com a marca "LUMENIA FREE" em grade. A pintura e o `.lmn` nunca são tocados. Diálogo de boas-vindas uma única vez e botão "Versão gratuita · Ativar" na barra de status |
| Ativação online | Fase 2 | Não implementada. O campo `mid` está reservado e o motor recusa uma licença que o traga |
| Revogação | Lista embutida em cada versão | `RevokedLicenses.hpp`, gerado pelo comando `export` do gerador; vale depois de recompilar o motor |
| Chaves | `keygen`, privada guardada cifrada | Duas chaves: `dev` (sem senha, é a compilada até exportar a `prod`) e `prod` (senha obrigatória). `scripts/build_release.py` recusa empacotar um motor que ainda confia na `dev` |
| Gerador | Linha de comando, repositório separado | Repositório separado e privado. Linha de comando (`keygen`, `export`, `issue`, `verify`, `revoke`, `list`, `types`) **e interface** (Emitir, Registro, Conferir, Chaves e versão) sobre um livro SQLite com tipos de licença, histórico, notas e exportação CSV. Tipos de fábrica: `pro`, `lifetime`, `edu`, `gift`, `trial` |

Pastas: `engine/infrastructure/licensing/` (verificação, marca d'água), `ui/core/licensing/` (estado e serviço da
sessão), `ui/infrastructure/licensing/` (o `license.lic` em disco). A chave privada continua fora deste repositório.

### Diagnóstico

| Tema | Recomendado acima | Implementado |
| --- | --- | --- |
| Envio | `sentry-sdk` ligado ao `logging` | **Sem SDK**: HTTP da biblioteca padrão (`upload_minidump`, `upload_event`) para Sentry, Sentry auto-hospedado ou GlitchTip. Sem DSN configurado nada é enviado e o usuário recebe o `.zip` para anexar num e-mail |
| Consentimento | Diálogo no primeiro uso | `ReportConsent` com três valores (perguntar, sempre, nunca); **o padrão é perguntar a cada relatório** |
| Pacote | Minidump, final do log e versão | `.zip` em `logs/crash-reports/` com `manifest.json`, textos e o minidump. `scrub` tira pasta do usuário, nome de usuário e e-mails do texto |
| Queda nativa | `SetUnhandledExceptionFilter` + `MiniDumpWriteDump` | Como previsto, em `engine/infrastructure/crash/`. O PDB sai de `scripts/build_native.py --pdb`, fora da árvore, junto do `native-build.json` |

Pastas: `ui/core/diagnostics/` (regras), `ui/infrastructure/diagnostics/` (arquivos e rede).

### Atualização e dados do usuário

| Tema | Recomendado acima | Implementado |
| --- | --- | --- |
| Mecanismo | Velopack | Velopack, com o feed nas GitHub Releases. `VelopackUpdater` é o único lugar que importa a biblioteca; `UpdateWorker` e `UpdateThread` rodam fora da thread da interface e uma falha de rede vira o sinal `failed` |
| Quando checar | Canais `alpha`, `beta`, `stable` | Verificação automática a cada 20 h, por canal (`UpdatePreferences`, seção `updates` do `config.json`) |
| Licença × atualização | `upd_until` decide se a versão nova é oferecida | *(removido em 2026-10-12: toda versão encontrada é oferecida.)* Uma versão lançada depois de `updates_until` **nunca é instalada**: a interface só avisa. A data vem do comentário `<!-- released: AAAA-MM-DD -->` que `scripts/build_release.py` escreve nas notas; sem ela e com licença com prazo, a interface pergunta em vez de instalar |
| Dados do usuário | Corrigir `writable_data_dir`, migrar a Alpha | Feito: o instalado grava em `%APPDATA%\Lumenia`, e `ui/infrastructure/legacy_data.py` copia uma única vez o que o instalador antigo deixou em `data\`, sem sobrescrever nem apagar nada |
| Instalador | Inno Setup sai | `scripts/lumenia_installer.iss` foi removido; `scripts/build_release.py` o substitui |

Pastas: `ui/core/updates/` (regras), `ui/infrastructure/updater/` (Velopack).

### Interface e termos

- Menu Ajuda (`ui/core/components/menu_bar/help_menu.py`), diálogos de crash e atualização (`ui/core/dialogs/`; os de licença e boas-vindas saíram em 2026-10-12) e a ligação deles em `ui/boundary/orchestrator/distribution_actions.py`.
- `TERMS_AND_LICENSE.txt` reescrito em português e inglês (modo gratuito, privacidade e relatórios de erro,
  atualizações) e `assets/legal/THIRD_PARTY_NOTICES.txt` novo. A revisão jurídica que este documento pede antes de
  vender não faz parte desses commits.
- Testes novos: `test_license_service.py`, `test_runtime_services_native.py`, `test_diagnostics_service.py`,
  `test_update_policy.py`, `test_build_release.py`, `test_runtime_paths.py` e `test_free_mode_welcome.py`.

### Decisões pendentes — situação

- [x] *(substituídas em 2026-10-12 pela remoção do licenciamento)* Modelo de licença: perpétua com 12 meses de atualizações é o padrão dos tipos `pro`, `edu` e `gift`; `lifetime` não tem prazo.
- [x] Sem licença: modo gratuito, com a marca d'água na exportação como única restrição.
- [x] Relatório de erros: compatível com Sentry, opcional e sem SDK; sem DSN o usuário envia o `.zip`.
- [x] Hospedagem das atualizações: GitHub Releases.
- [ ] Onde vender.
- [ ] Certificado de assinatura de código.
- [ ] Ativação online (fase 2) e endurecimento (fase 3).

## Referências

- [Velopack — Python API Reference](https://docs.velopack.io/reference/py)
- [Velopack — Getting started (Python)](https://docs.velopack.io/getting-started/python)
- [Velopack — ReleaseEntry.IsDelta](https://docs.velopack.io/reference/cs/Velopack/ReleaseEntry/properties/IsDelta)
- Código analisado no fork: `ui/infrastructure/logging/`, `ui/infrastructure/runtime_paths.py`, `engine/infrastructure/telemetry/`, `scripts/build_portable.py`, `scripts/lumenia_installer.iss`, `TERMS_AND_LICENSE.txt`.
