# Shared Basis Artifact

Version: 1.0-draft

## Purpose

This document defines the shared basis artifact used for canonical seed derivation.

## Basis Tuple

The basis artifact is the tuple:

- `unicode_version`
- `utf_ebcdic_artifact`
- `normalization`

## Draft Values in This Bundle

- `unicode_version = "DRAFT-UNPINNED"`
- `utf_ebcdic_artifact = "DRAFT-UNPINNED"`
- `normalization = "NFC"`

These draft values are placeholders. They make the derivation procedure reproducible inside this bundle without falsely claiming a pinned external standards release.

## Canonical Byte String

The canonical byte string is:

`unicode_version "|" utf_ebcdic_artifact "|" normalization "|" context`

encoded in UTF-8.

## Seed Reduction

For width `n`, the seed is:

`SHA-256(canonical_bytes) mod 2^n`

## Why Unicode / UTF-EBCDIC

Unicode provides a public finite symbolic space.
UTF-EBCDIC provides an operable, inspectable encoding artifact.
Together they provide a shared basis artifact from which any participant can derive the same seed or falsify a wrong claim by recomputation.
