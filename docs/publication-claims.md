# Publication Claim Policy

Version: v1.0  
Status: Active policy for docs and release notes

## Rule
Any strong claim in published documentation must map to a runnable command, fixture, or test.

## Required Claim Record
Use this structure for release-authoritative claims:

```markdown
Claim: <short statement>
Status: Implemented | Verified | Conjecture/Open
Evidence: <command or file path>   # required when Status includes Verified
```

## Claim Labels
- `Implemented`: Feature exists in the codebase.
- `Verified`: Feature is demonstrated by automated test or conformance command.
- `Conjecture/Open`: Research direction not fully implemented or proven in this runtime.

## Evidence Mapping Examples
- Deterministic replay behavior (`Verified`): `python3 tests/test_v1.py`
- Legacy deterministic core (`Verified`): `python3 tests/test_all.py`
- Cross-language parity (`Verified`): `python3 conformance.py`
- API availability (`Implemented`): `api_server.py` endpoint handlers

## Algorithm Claims
Claims about canonical behavior must reference:
- [Canonical Algorithms Specification](./algorithms.md)

## Disallowed in Publication Pages
- Unverifiable license claims unless `LICENSE` file is present.
- Unverifiable repo/distribution claims.
- Prompt-like drafting language (for example, unresolved “shall I integrate …”).
- Absolute no-collision guarantees beyond corpus evidence and cryptographic assumptions.
