"""Version of the Python <-> engine contract that this interface was written against.

The compiled module exposes `CONTRACT_VERSION`
(bridge/infrastructure/ContractVersion.hpp); `AladynBackend` compares it with
this value when it loads and refuses a binary from another version, instead of
letting it fail one call at a time. Bump both when the `.pyi` changes;
`tests/test_bridge_contract_version.py` pins the `.pyi` and fails if the contract
moved without the bump.
"""

EXPECTED_CONTRACT_VERSION = 2
