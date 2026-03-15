# Algorithmic Clock Specification

Version: 1.0-draft
Author: Brian Thorne

## 1. Scope

This specification defines a deterministic logical clock and shared basis model for decentralized replay and witness generation.

It defines:

- a bounded state space
- a width-parameterized transition law
- a projection law
- a canonical seed derivation procedure
- conformance fixtures

It does not define physical time measurement.

## 2. Core Object

For each width `n`, the clock family member is:

\[
\mathcal{C}_n = (S_n, \delta_n, \pi_n)
\]

where:

- `S_n = {0,1,...,2^n-1}`
- `δ_n : S_n -> S_n` is the replay law
- `π_n : S_n -> B_n` is the projection law

## 3. State Space

\[
S_n = \{0,1,\dots,2^n-1\}
\]

Mask operator:

\[
\operatorname{mask}_n(x) = x \bmod 2^n
\]

## 4. Rotation Operators

\[
\operatorname{rotl}_n(x,k)=\operatorname{mask}_n\big((x \ll k) \lor (x \gg (n-k))\big)
\]

\[
\operatorname{rotr}_n(x,k)=\operatorname{mask}_n\big((x \gg k) \lor (x \ll (n-k))\big)
\]

## 5. Transition Law

\[
\delta_n(x)=\operatorname{mask}_n\big(
\operatorname{rotl}_n(x,1)
\oplus
\operatorname{rotl}_n(x,3)
\oplus
\operatorname{rotr}_n(x,2)
\oplus
C_n
\big)
\]

The constant family `C_n` is the byte `0x1D` repeated to width `n`.

Examples:

- `C_16  = 0x1D1D`
- `C_32  = 0x1D1D1D1D`
- `C_64  = 0x1D1D1D1D1D1D1D1D`

## 6. Projection Law

The projection is the band tuple:

\[
\pi_n(x) = (w(x), d(x), e(x))
\]

where:

- `w(x)` is bit width (`0` if `x = 0`, else `bit_length(x)`)
- `d(x)` is popcount
- `e(x)` counts adjacent bit transitions in the cyclic width-`n` representation

## 7. Canonical Seed Derivation

The canonical seed derivation procedure is:

\[
\Sigma_n(B,x)=\operatorname{mask}_n(\mathrm{SHA256}(\operatorname{canon}(B,x)))
\]

where the canonical byte string is:

`unicode_version "|" utf_ebcdic_artifact "|" normalization "|" context`

encoded in UTF-8.

This draft bundle pins:

- `unicode_version = "DRAFT-UNPINNED"`
- `utf_ebcdic_artifact = "DRAFT-UNPINNED"`
- `normalization = "NFC"`

These placeholders are deliberate. Replace them with pinned standards versions before publication.

## 8. Replay

Given a seed `x_0`:

\[
x_{k+1} = \delta_n(x_k)
\]

The replay sequence is:

\[
(x_0, x_1, x_2, \dots)
\]

## 9. Conformance

A conforming implementation must:

1. derive the same seed from the same basis artifact and context
2. produce the same replay states for the same width and step count
3. produce the same projection tuples for each replay state

The JSON fixture files in `fixtures/` are normative over interoperability.

## 10. Width Families

This bundle includes fixtures for:

- 16
- 32
- 64
- 128
- 256

and emphasizes the comparison ladders:

- `16 -> 32 -> 64 -> 128 -> 256`
- `16 -> 64 -> 256`

## 11. Shared Basis Artifact

Unicode is the public symbolic substrate.
UTF-EBCDIC is the root operable encoding artifact.
The clock is not Unicode and Unicode is not the clock.

The basis artifact exists to make seed derivation publicly reproducible and falsifiable.

## 12. Release Notes

This bundle is a draft kernel bundle. The seed derivation placeholders must be pinned to exact standards versions for a final release.
