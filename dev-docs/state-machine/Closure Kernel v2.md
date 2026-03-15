# Closure Kernel v2

*Deterministic Bounded Closure, Hamming Geometry, and Stable Identity*

---

## 1. Base Space

The state space is the set of all 8-bit words:

```
B = {0,1}^8    (256 elements)
```

The 7-bit subspace used by the closure operator:

```
B7 = {0,1}^7   (128 elements, masked by 0x7F)
```

---

## 2. Metric Structure

Hamming distance between two states:

```python
def hamming_distance(x: int, y: int) -> int:
    return (x ^ y).bit_count()
```

Satisfies non-negativity, identity (d=0 iff x=y), symmetry, and the triangle inequality. Therefore (B, d) is a metric space.

---

## 3. Adjacency

Two states are adjacent if they differ by exactly one bit:

```
x ~ y  iff  d(x, y) = 1
```

```python
def neighbors(x: int, bits: int = 7):
    for i in range(bits):
        yield x ^ (1 << i)
```

This defines a 7-dimensional hypercube graph. Each node has exactly 7 neighbors.

---

## 4. Bounded Expansion

All operations use bitmasks as the primary representation. Three parameters define a bounded region:

| Parameter | Meaning |
|-----------|---------|
| `seed`    | Starting bitmask; the active cause |
| `lower`   | Floor: bits always present (invariant minimum) |
| `upper`   | Ceiling: bits never exceeded (admissible envelope) |

Constraint: `lower & upper == lower` (lower is contained in upper).

One expansion step on the 7-bit cyclic ring:

```python
MASK7 = 0x7F

def expand7(x: int) -> int:
    left  = ((x << 1) | (x >> 6)) & MASK7
    right = ((x >> 1) | ((x & 1) << 6)) & MASK7
    return x | left | right

def expand_bounded(x: int, lower: int, upper: int) -> int:
    return (expand7(x) | lower) & upper
```

The cyclic shift wraps bit 6 back to bit 0, maintaining the ring topology.

---

## 5. Closure Operator

Closure is the least fixed point of bounded expansion above the seed:

```python
def closure7(seed: int, lower: int, upper: int) -> int:
    x = (seed | lower) & upper
    while True:
        y = (expand7(x) | lower) & upper
        if y == x:
            return x
        x = y
```

### Proof of closure properties

**Extensive:** seed is always a subset of closure(seed), because expansion only adds bits.

**Monotone:** if seed_A has all bits of seed_B set, then closure(seed_A) has all bits of closure(seed_B) set. Expansion rules are identical for both; the larger seed can only reach at least the same bits.

**Idempotent:** closure(closure(x)) = closure(x). The algorithm returns exactly when it reaches a fixed point, so applying it again leaves the result unchanged.

These three properties establish that `closure7` is a valid closure operator in the lattice-theoretic sense.

### Termination bound

Each strict iteration sets at least one new bit inside `upper`. Since `upper` has at most `popcount(upper)` bits set, the loop runs at most `popcount(upper)` times. For `MASK7 = 0x7F`, worst case is 7 iterations.

---

## 6. Phase Projection

```python
def phase7(x: int) -> int:
    return x.bit_count() % 7

# Range: {0, 1, 2, 3, 4, 5, 6}
# popcount(0x7F) % 7 = 7 % 7 = 0
# popcount(0x01) % 7 = 1 % 7 = 1
```

Phase is a property of the closed state, not the seed. Two seeds that produce the same closed state produce the same phase.

---

## 7. Canonical Form and SID

```python
import hashlib

def sid7(closed: int) -> str:
    canonical = closed.to_bytes(1, 'big')
    return hashlib.sha256(canonical).hexdigest()

# Full pipeline:
def compute_sid(seed: int, lower: int, upper: int) -> str:
    closed = closure7(seed, lower, upper)
    return sid7(closed)
```

**Identity law:** if `closure7(seed_1, L, U) == closure7(seed_2, L, U)`, then `sid7(seed_1) == sid7(seed_2)`. The SID is the identity of the canonical closure, not the seed. Multiple seeds can share one SID.

---

## 8. Fano Plane and Hamming(7,4) Connection

The 7-bit ring connects to the Fano plane — the unique projective plane of order 2. It has exactly 7 points and 7 lines, with 3 points on every line and 3 lines through every point.

Labeling the 7 points with single-bit masks (1, 2, 4, 8, 16, 32, 64), every line satisfies:

```
XOR of the three points on any line = 0

Example lines:
  {1, 2, 3}  ->  1 XOR 2 XOR 3 = 0
  {1, 4, 5}  ->  1 XOR 4 XOR 5 = 0
  {2, 4, 6}  ->  2 XOR 4 XOR 6 = 0
  (and 4 more)
```

These 7 XOR constraints are exactly the rows of the parity-check matrix of the Hamming(7,4) code. Valid codewords are the 16 seven-bit strings that satisfy all parity checks simultaneously.

**Consequence for the closure operator:** neighbor expansion on the 7-bit ring traverses the lines of the Fano plane. The closure of a seed is the smallest Fano-consistent subplane containing that seed. The mod-7 phase counts how many Fano points are active in the closed state.

**The 63/64 boundary** (binary: `0111111` / `1000000`) is the activation of bit 6 — the transition from the 6-bit face of the cube into the full 7-dimensional space where the Fano plane is defined. This boundary is structural.

---

## 9. Clock Step (Placeholder Evolution)

A deterministic step function exists. The following is a mechanical placeholder — it proves deterministic evolution is possible. It is **not** a derived clock law.

```python
def advance_seed(seed: int) -> int:
    # Rotate seed left by 1 on the 7-bit ring
    return ((seed << 1) | (seed >> 6)) & MASK7

def step(seed: int, lower: int, upper: int):
    closed = closure7(seed, lower, upper)
    tick   = phase7(closed)
    sid    = sid7(closed)
    next_s = advance_seed(seed)
    return next_s, tick, sid
```

**Status: open.** The normative clock advance law is not yet derived. Deriving the true advance law from the Fano geometry is a separate problem.

---

## 10. The 256 → 60 × 4 Bridge (Open Problem)

Extending to a 60-point address space with 4 orientations (240 frames total) requires an explicit structure-preserving map:

```
φ : kernel_space → 60 × 4 space
```

This map is not automatic. It must preserve at least one of:

- **Adjacency:** Hamming neighbors in the kernel map to adjacent points in the 60-point space
- **Closure class:** φ(closure(seed)) = closure(φ(seed)) — closure commutes with the map
- **Phase class:** seeds with the same mod-7 closure map to the same class in the 60-point space
- **SID equivalence:** φ preserves canonical identity across both representations

The connection to 60: `60 = 4 × 3 × 5`, and 60 is also the order of the alternating group A5 (icosahedral rotations). The relationship between A5, the Fano plane, and the Hamming geometry is not yet established for this system. Until φ is specified and proved structure-preserving, the 60/240 layer remains a separate conjecture.

---

## 11. Kernel Summary

| Component  | Definition |
|------------|------------|
| State space | B7 = {0,1}^7, integers 0–0x7F |
| Metric | d(x,y) = popcount(x XOR y) |
| Adjacency | x ~ y iff d(x,y) = 1 |
| Expansion | expand7(x): cyclic left/right shift OR'd with x |
| Closure | closure7(seed, L, U): least fixed point, terminates in ≤ popcount(U) steps |
| Projection | phase7(x) = popcount(x) % 7, range {0–6} |
| Identity | SID = SHA256(closed.to_bytes(1, 'big')) |
| Evolution | advance_seed: placeholder only, clock law unresolved |
| Extension | φ map to 60×4 space: open problem |

---

## 12. Open Problems

1. Derive the normative clock advance law from the Fano geometry
2. Specify the structure-preserving map φ from the 7-bit kernel to the 60×4 space
3. Determine which structural property φ must preserve (adjacency, closure, phase, or SID)
4. Establish the relationship between A5, the Fano plane, and the Hamming geometry in this system
5. Prove or disprove that the 60-point address space is reachable from the kernel by a canonical quotient
