# Build do Lumenia e do Aladyn Engine

O repositório compila a extensão `aladyn_engine_native` com C++20/PyBind11 para
Windows x64. O binário é gerado na raiz do repositório e nunca deve ser copiado
manualmente para `ui/` ou para um plugin.

## Pré-requisitos

- Python 3.11+ de 64 bits. O CI usa Python 3.12; a versão usada para compilar
  precisa ser a mesma que carregará o `.pyd`.
- Visual Studio 2022 com **Desktop development with C++** e Windows SDK.
- Acesso às dependências de desenvolvimento com hashes declaradas em
  `requirements-dev.lock`.

```powershell
python -m pip install -r requirements-dev.lock
```

## Compilação reproduzível no checkout

O comando abaixo localiza `vswhere`/`vcvarsall` quando necessário, configura o
MSVC x64 e compila todos os fontes declarados em `setup.py`.

```powershell
python scripts/build_native.py --simd scalar --force
```

`scalar` é o artefato base compatível com processadores Windows x64 sem AVX2.
Em uma frota controlada que exija AVX2, gere e distribua um artefato separado:

```powershell
python scripts/build_native.py --simd avx2 --force
```

Uma variante AVX2 não deve substituir o artefato base sem uma política de
detecção e seleção no instalador.

Ao terminar, o script grava `build/native-build.json` com a versão do Python,
ABI, versão das ferramentas MSVC, variante SIMD e SHA-256 do `.pyd`. Esse
registro permite comparar o binário executado pelo CI ou por uma validação
manual com a configuração que o produziu.

## Validação

```powershell
python tests/run_all_tests.py
python benchmarks/run_engine_benchmarks.py --output build/benchmarks/engine.json
python main.py
```

O benchmark grava JSON com ambiente, p50/p95 de criação da fachada, traço e
`refresh_display`, além dos bytes de pixels. Ele é uma base de comparação entre
máquinas e commits; não é um gate com valores fixos porque hardware e carga do
sistema alteram a medida.

## CI

`.github/workflows/ci.yml` instala as dependências, configura MSVC x64, executa
o mesmo `scripts/build_native.py --simd scalar --force`, mede o motor e então
chama a suíte executiva. A matriz roda em Python 3.11, 3.12 e 3.13; cada job
publica seu JSON de benchmark. Isso garante que os testes usem a extensão
gerada no próprio job.

## Pacote portátil e instalador

O pacote distribuível inclui a extensão nativa recém-compilada, todos os módulos
`ui` e `plugins`, temas, assets e documentos. Ao final, é criado um
`release-manifest.json` com SHA-256 de cada arquivo.

```powershell
python scripts/build_portable.py --dry-run
python scripts/build_portable.py
```

O resultado fica em `build/portable/Lumenia.dist`. Com Inno Setup instalado, o
instalador é gerado sem caminhos absolutos antigos:

```powershell
ISCC.exe scripts/lumenia_installer.iss
```

O `.iss` aceita `SourceDir` e `OutputDir` como definições do Inno para outros
diretórios de build. Assinatura não é simulada: ela deve ser feita no job de
release com certificado confiável e credenciais protegidas.

Ainda não existe instalador assinado, assinatura de artefatos nem seleção
automática entre variantes SIMD. Essas etapas pertencem ao job de release, não
a uma cópia local de `.pyd`.
