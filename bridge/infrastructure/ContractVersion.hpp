#ifndef ALADYN_BRIDGE_CONTRACT_VERSION_HPP
#define ALADYN_BRIDGE_CONTRACT_VERSION_HPP

namespace aladyn::bridge {

// Version of the Python <-> engine contract (bridge/boundary/contracts/*.pyi).
// The module exposes it as `aladyn_engine_native.CONTRACT_VERSION`; the interface
// compares it with EXPECTED_CONTRACT_VERSION (ui/infrastructure/bridge_client/
// contract_version.py) when it loads, so a binary from another version is refused
// at once instead of failing one call at a time.
//
// Bump it whenever the .pyi changes (a method added counts: the interface would
// call it on a binary that lacks it). tests/test_bridge_contract_version.py pins
// the .pyi and fails if the contract changes without the bump.
inline constexpr int kContractVersion = 2;

} // namespace aladyn::bridge

#endif // ALADYN_BRIDGE_CONTRACT_VERSION_HPP
