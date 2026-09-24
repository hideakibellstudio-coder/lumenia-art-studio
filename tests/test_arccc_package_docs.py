"""Todo pacote de ui/ e plugins/ tem README com arquivos e dependências verdadeiros.

Regras e linha de comando em tests/arccc_package_docs.py. Quando este teste
falhar:
- pasta nova: `python -m tests.arccc_package_docs --scaffold PASTA` e escreva
  a responsabilidade, a porta de entrada e as regras;
- arquivo novo: acrescente a linha dele na tabela do README da pasta;
- import novo entre pastas: `python -m tests.arccc_package_docs --deps PASTA`
  e atualize o bloco `arccc:deps` no mesmo commit — é uma decisão de
  arquitetura e tem que aparecer no diff.
"""
from tests.arccc_package_docs import packages, problems, rel


def test_every_package_documents_its_files_and_dependencies():
    pending = {rel(p): problems(p) for p in packages()}
    pending = {pasta: falhas for pasta, falhas in pending.items() if falhas}
    assert not pending, "README desatualizado ou ausente:\n" + "\n".join(
        f"  {pasta}: {'; '.join(falhas)}" for pasta, falhas in pending.items()
    )
