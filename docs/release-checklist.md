# Release Checklist

Version: v1.0  
Status: Maintainer checklist

## Pre-Release Verification
- Run: `python3 tests/test_all.py`
- Run: `python3 tests/test_v1.py`
- Run: `python3 conformance.py`
- Confirm no conformance diff file remains unless investigating a failure.

## Documentation Quality
- Validate links from `README.md` and `docs/README.md`.
- Validate every command block executes as documented.
- Ensure claim labels (`Implemented`, `Verified`, `Conjecture/Open`) are accurate.

## API Documentation Check
- Execute documented curl examples against local server.
- Confirm reason codes in failure examples match runtime outputs.

## Publication Metadata
- Update version/date where changed.
- Add release notes summary.
- Tag version (for example `v1.0-docs`) after tests pass.

## GitHub Publishing Flow
```bash
git add README.md docs .github

git commit -m "docs: publish developer-focused v1 documentation spine"

git push origin main
# optional
# git tag v1.0-docs && git push origin v1.0-docs
```
