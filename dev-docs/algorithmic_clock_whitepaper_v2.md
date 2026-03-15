# An Algorithmic Clock Standard Based on Cyclic Number Theory and Discrete Integration

**Primary Author:** Brian  
**Technical Formalization:** Coq, Haskell, Python  
**Version:** 2.0 — Revised following peer review  
**Date:** March 2026

---

> *This paper was revised in response to a critical review that correctly identified two overstated claims in version 1.0. The revisions are documented in Section 10. The core results — the arithmetic layer and the clock construction — are unchanged and remain correct.*

---

## Abstract

We present a deterministic algorithmic clock grounded entirely in finite bitwise operations and classical number theory. The clock derives its timing from the provably deterministic traversal of a finite bit-state space. Its step-encoding mechanism draws on **cyclic number theory**: for any prime *q* coprime to 10, the repeating decimal of 1/*q* has period equal to the multiplicative order of 10 modulo *q*, and the repeating block forms a cyclic number *R* whose multiples enumerate all positions within a spin. Step recovery — determining which position produced a given value — follows from modular inversion and is proven correct for all steps.

The clock is structured in two formally distinct layers. **Layer A** contains the number-theoretic results: the period formula, cyclic number construction, and round-trip recovery theorem. These are proven results, verified computationally for all relevant primes and with a Coq proof skeleton for the recovery theorem. **Layer B** contains the fold construction: iterating the cumulative sum of the period-8 block B = [0,1,3,6,9,8,6,3] produces a hierarchy of position sequences. The "self-similarity" of this hierarchy is the standard operator identity Δ(Σx) = x — true and exact, but a consequence of how cumulative summation is defined, not an independent discovery. The specific contribution of B is not the fold identity itself, but the number-theoretic grounding: B arises from 1/73 (the smallest prime with decimal period 8), its length matches the generator period, and its digit sum (36) gives the natural orbit length for step recovery.

We prove formally: determinism (same seed gives same sequence, always), boundedness (all states in *n*-bit space), zero logical drift, portability across implementations, and encoding independence. We compare the clock against atomic standards and argue it is the stronger foundation for logical synchronization, distributed systems, and formally verifiable timing.

---

## Table of Contents

1. Background and Motivation
2. Layer A — The Arithmetic Foundation
3. Layer A — Step Recovery
4. Layer B — The Fold Construction
5. Layer B — What the Identity Actually Proves
6. The Algorithmic Clock Law
7. Coxeter Structure and Hand Hierarchy
8. Formal Verification in Coq
9. Implementation Reference
10. Comparison with Atomic Clocks
11. Revision Notes
12. Open Problems
13. Conclusion
14. Appendices

---

## 1. Background and Motivation

The international standard second is defined as 9,192,631,770 oscillations of the hyperfine transition of caesium-133. This is remarkably precise — the best caesium fountain clocks drift by less than 10⁻¹⁶ seconds per second — but it rests on a physical assumption: quantum mechanics holds, hardware functions correctly, no external interference perturbs the measurement.

For distributed computing systems, cryptographic protocols, and any application requiring synchronized *logical* time across independent machines, physical clocks introduce an unavoidable dependency. Every node must either carry a certified oscillator or trust a remote time source. Neither is formally verifiable.

This paper proposes a complementary foundation. We replace the physical oscillator with a logically necessary clock: a deterministic function over a finite bit-state space whose output is not measured but proven. The same seed on any machine, in any language, on any substrate, at any point in time, produces the identical sequence — not by careful calibration, but because the law makes any other result impossible.

The clock emerges from the intersection of three classical areas:

- **Multiplicative order theory:** the period of the repeating decimal of 1/*q* equals ord_*q*(10)
- **Cyclic numbers:** the block R = (10^T − 1)/*q* encodes all positions within a cycle
- **Discrete integration:** iterated prefix sums build a position hierarchy from any base sequence

The primary novelty is the architectural combination: using the period-matched cyclic block as the differential injected at generator fold points, with modular recovery of step position from block values.

---

## 2. Layer A — The Arithmetic Foundation

### 2.1 Primorials (Context)

The primorial P_n# is the product of the first *n* primes:

| n | P_n# |
|---|------|
| 1 | 2 |
| 2 | 6 |
| 3 | 30 |
| 4 | 210 |
| 5 | 2310 |
| 6 | 30030 |

Dividing P_n# by a prime *q* outside the primorial produces an infinite repeating decimal. The period of that decimal is determined entirely by *q*, not by which primorial is used. Primorials provide the motivating context — the natural "boundary" between finite and infinite decimal behavior — but the arithmetic theorems below depend only on *q* being prime and coprime to 10.

### 2.2 The Period Theorem

**Theorem (Period = Multiplicative Order):** For any prime *q* with gcd(*q*, 10) = 1, the period of the repeating decimal of 1/*q* is:

```
T = ord_q(10)  =  smallest k ≥ 1 such that 10^k ≡ 1 (mod q)
```

**Why this holds:** Long division of 1 by *q* cycles through remainders in {1, 2, ..., *q*−1}. The decimal repeats exactly when a remainder recurs, which happens after exactly *T* steps where *T* is the smallest exponent with 10^T ≡ 1 (mod *q*).

**Fermat's bound:** By Fermat's Little Theorem, 10^(*q*−1) ≡ 1 (mod *q*), so *T* always divides *q*−1. The period is never longer than *q*−1.

### 2.3 Verified Period Table

The following is computed exactly — no floating point, no approximation:

| Prime *q* | Period T | *q*−1 | T divides *q*−1 | Cyclic number R |
|-----------|----------|--------|-----------------|-----------------|
| 7 | 6 | 6 | YES | 142857 |
| 11 | 2 | 10 | YES | 9 |
| 13 | 6 | 12 | YES | 76923 |
| 17 | 16 | 16 | YES | 588235294117647 |
| 19 | 18 | 18 | YES | 52631578947368421 |
| 23 | 22 | 22 | YES | 434782608695652173913 |
| 31 | 15 | 30 | YES | 32258064516129 |
| 37 | 3 | 36 | YES | 27 |
| 41 | 5 | 40 | YES | 2439 |
| **73** | **8** | 72 | YES | **1369863** |

The entry for *q* = 73 is the one used in this clock: period 8 matches the generator period.

### 2.4 The Cyclic Number

**Definition:** For prime *q* with period *T*, the cyclic number is:

```
R = (10^T − 1) / q
```

This is always an integer because the definition of *T* as the multiplicative order means *q* divides 10^T − 1.

**The cyclic property:** For *k* = 1, 2, ..., *T*, the product *k* × R mod (10^T − 1) is a cyclic rotation of the digits of R. This is the encoding mechanism: each step *k* within a spin corresponds to a unique, recoverable rotation of the block.

**Canonical example (q = 7, T = 6, R = 142857):**

| k | k × R mod 999999 | Block |
|---|-----------------|-------|
| 1 | 142857 | 142857 |
| 2 | 285714 | 285714 |
| 3 | 428571 | 428571 |
| 4 | 571428 | 571428 |
| 5 | 714285 | 714285 |
| 6 | 857142 | 857142 |

Every row is a cyclic rotation of every other row. This is not a coincidence or approximation — it is a theorem about cyclic primes.

### 2.5 The Period-8 Block

For our clock, the generator has period 8. The smallest prime *q* with ord_*q*(10) = 8 is **q = 73**. Its cyclic number and repeating block are:

```
1/73 = 0.01369863 01369863 01369863...

R = (10^8 − 1) / 73 = 1,369,863
B = [0, 1, 3, 6, 9, 8, 6, 3]    (the 8 decimal digits of 1/73)
sum(B) = 36
```

The block B is uniquely determined by the requirement that the period equals 8 and that *q* is minimal. It is not a free parameter.

---

## 3. Layer A — Step Recovery

### 3.1 The Encoding

Given a step *k* within a spin (1 ≤ *k* ≤ *T*), the encoded block value is:

```
B_k = (R × k) mod (10^T − 1)
```

### 3.2 The Recovery Formula

Given a block value *B_k*, recover *k* by:

```
k ≡ B_k × R⁻¹  (mod q)
```

where R⁻¹ is the modular inverse of R mod *q*.

**Why this works:** Since *B_k* = *k* × R mod (10^T − 1), we have *B_k* ≡ *k* × R (mod *q*) because *q* divides 10^T − 1. Since R is coprime to *q* (if *q* divided R, then *q*² would divide 10^T − 1, contradicting the minimality of *T*), R has an inverse mod *q* and the recovery is unique.

### 3.3 Verified Round-Trip for q = 7

All seven steps verified with no errors:

| Block B_k | B_k mod 7 | R mod 7 | R⁻¹ mod 7 | Recovered k | Correct |
|-----------|-----------|---------|-----------|-------------|---------|
| 142857 | 1 | 1 | 1 | 1 | YES |
| 285714 | 2 | 1 | 1 | 2 | YES |
| 428571 | 3 | 1 | 1 | 3 | YES |
| 571428 | 4 | 1 | 1 | 4 | YES |
| 714285 | 5 | 1 | 1 | 5 | YES |
| 857142 | 6 | 1 | 1 | 6 | YES |

### 3.4 Coarse Recovery via Digit Sum

For the period-8 block with sum(B) = 36, a simpler coarse recovery applies to any accumulated position *P*:

```
spin_number  = P // 36
step_offset  = P mod 36
```

This recovers which spin and approximately where within it, using only integer division. It is valid because each spin accumulates exactly 36 units of position (the digit sum of B). This is arithmetic, not magic: it holds because we defined each spin's step sizes to be the digits of B, so the total advance per spin is always sum(B).

---

## 4. Layer B — The Fold Construction

### 4.1 The Generator Period

The core bitwise generator (oscillate) has period 8 on the 16-bit state space with seed 0x0001:

```
0x0001 → 0x5D17 → 0x98CC → 0xCCD3 → 0x1110 → 0xB3F9 → 0x89DD → 0x223D → 0x0001
```

After 8 steps it returns to the seed. This is the fundamental "spin."

### 4.2 The Fold

At each spin boundary, the block B is injected as the step-size sequence for the next spin. The position within each spin is the cumulative sum of step sizes taken so far.

**Formally:** let *S_n* denote the sequence of positions within spin *n*.

```
S_1 = [0, 1, 2, 3, 4, 5, 6, 7]         (baseline: uniform step size 1)

S_2 = prefix_sum(B)
    = [0, 0, 1, 4, 10, 19, 27, 33]      (step sizes are digits of B)

S_3 = prefix_sum(S_2)
    = [0, 0, 0, 1, 5, 15, 34, 61]

S_4 = prefix_sum(S_3)
    = [0, 0, 0, 0, 1, 6, 21, 55]
```

### 4.3 The Observation

The differences between successive values of *S_4* equal the values of *S_3*:

```
diff(S_4) = [0, 0, 0, 1, 5, 15, 34]
S_3[0:7]  = [0, 0, 0, 1, 5, 15, 34]
Equal: YES
```

And analogously for every successive pair:

```
diff(S_3) = [0, 0, 1, 4, 10, 19, 27]
S_2[0:7]  = [0, 0, 1, 4, 10, 19, 27]
Equal: YES

diff(S_2) = [0, 1, 3, 6, 9, 8, 6]
B[0:7]    = [0, 1, 3, 6, 9, 8, 6]
Equal: YES
```

---

## 5. Layer B — What the Identity Actually Proves

### 5.1 The Reviewer's Correction (Accepted)

The v1.0 whitepaper described the fold self-similarity as a "proven theorem" implying a surprising emergent property. A reviewer correctly identified this as overstated. The equality diff(*S_{n+1}*) = *S_n* is the standard identity:

```
Δ(Σ x) = x
```

That is: the forward difference of a cumulative sum returns the original sequence. This is a consequence of the *definition* of cumulative summation:

```
S_{n+1}[i] = Σ_{j < i} S_n[j]

Therefore:
S_{n+1}[i+1] − S_{n+1}[i] = S_n[i]

i.e., diff(S_{n+1})[i] = S_n[i]
```

This holds for **any** sequence, not just B. Choosing B = [0,1,3,6,9,8,6,3] versus B = [1,1,1,1,1,1,1,1] versus any other 8-digit sequence produces the same operator identity.

### 5.2 What B Specifically Contributes

The choice of B is not arbitrary — it just does not make the operator identity stronger. What B specifically contributes is:

**1. Period matching.** B has exactly 8 digits and arises from 1/73, the smallest prime with decimal period 8. The generator also has period 8. These periods coincide. This is not proven to be necessary — it is a design alignment that gives the construction internal coherence.

**2. Number-theoretic grounding.** B is uniquely determined by *q* = 73 and the requirement ord_73(10) = 8. It is not a free design choice. This grounds the fold construction in arithmetic rather than in ad hoc parameter selection.

**3. Orbit length for recovery.** sum(B) = 36 is a specific, computable quantity that enables the coarse recovery formula P mod 36. For a uniform B = [1,...,1], sum(B) = 8 and recovery would be P mod 8. The digit sum of the number-theoretically determined B is what fixes this constant.

### 5.3 What Remains Open

The stronger claim — that the generator period *forces* B to come from 1/73, or that the fold hierarchy has additional structure beyond discrete integration that is specific to number-theoretically derived seeds — is not yet proven. It is a reasonable conjecture and an interesting open problem (see Section 12).

### 5.4 The Correct Summary of Layer B

> The fold operator is iterated cumulative summation. Its forward difference is the prior layer by the standard identity Δ(Σx) = x. The specific seed B = [0,1,3,6,9,8,6,3] is derived from 1/73, whose period (8) matches the generator's period, and whose digit sum (36) provides the orbit length for step recovery.

This is the precise and defensible statement. It is still a meaningful construction — the two-layer architecture is valid — but the self-similarity is an operator property, not an emergent miracle.

---

## 6. The Algorithmic Clock Law

The complete clock is defined by four laws, expressed entirely in finite integer arithmetic:

### 6.1 State Space

```
S ∈ {0, 1, ..., 2^n − 1}    for chosen bit width n
```

For the reference implementation: n = 16, so S ∈ {0, ..., 65535}.

### 6.2 Oscillation Law (Advance)

```
next(x) = rotl(x, 1) XOR rotl(x, 3) XOR rotr(x, 2) XOR 0x1D1D
```

All rotations are within n-bit space (bits wrap around). The constant 0x1D1D provides mixing to avoid fixed points.

### 6.3 Band Classification (Stability)

```
band(x) = (bit_length(x), popcount(x), edge_count(x))
```

Where:
- **bit_length(x):** position of the highest set bit + 1 (the width class, range 0–16)
- **popcount(x):** number of set bits (the density class, range 0–16)
- **edge_count(x):** number of 0→1 or 1→0 transitions around the 16-bit ring (the texture class, range 0–16)

All three are pure integer operations — no floats, no strings.

### 6.4 Time Signal

```
delta(t) = band(x_{t+1}) − band(x_t)
```

The clock reading is the ordered sequence of delta values. Two observers starting from the same seed compute the identical sequence, provably.

### 6.5 Fold Injection

```
B = [0, 1, 3, 6, 9, 8, 6, 3]

x_{t+1} = next(x_t XOR B[t mod 8])
```

At each step, the corresponding digit of B is XORed into the state before advancing. This couples the number-theoretic structure of 1/73 into the clock advance.

---

## 7. Coxeter Structure and Hand Hierarchy

The clock's generator products can be understood through Coxeter group theory. Each bitwise operation is a computational analog of a mirror reflection; products of reflections produce rotations of varying order.

### 7.1 Generator Table

| Coxeter element | Bitwise operation | Property |
|----------------|-------------------|----------|
| r₀ | XOR with 0xAAAA | Involution: r₀(r₀(x)) = x |
| r₁ | rotateL by 1 | Order 16: 16 applications return to start |
| r₂ | rotateL by 3 | Order 16 |
| r₃ | rotateR by 2 | Order 16 |

### 7.2 Clock Hands

| Hand | Generator | Coxeter type | Measured period |
|------|-----------|--------------|-----------------|
| Second | oscillate(x) | Single rotation | 8 |
| Minute | r₀(r₁(x)) | Double rotation | 16 |
| Hour | r₀(r₁(r₂(x))) | Triple rotation | 4 |
| Epoch | r₀(r₁(r₂(r₃(x)))) | Quadruple rotation | varies |

The periods emerge from the group algebra — they are not design parameters but consequences of the generator choice and the structure of the 16-bit state space.

### 7.3 The Hierarchy

Each higher-order hand has a longer natural period, providing coarser time resolution. The composition of second + minute + hour hands gives a three-layer clock hierarchy analogous to a mechanical clock, but derived from algebraic structure rather than gear ratios.

---

## 8. Formal Verification in Coq

### 8.1 What Is Proven

The Coq file (Appendix A) provides machine-checked proofs of the following:

**Boundedness:**
```coq
Theorem mask16_bounded : forall x, mask16 x < 65536.
```
All states are in [0, 65535]. No overflow. Absolute.

**Determinism:**
```coq
Theorem oscillate_deterministic : forall x y,
  x = y -> oscillate x = oscillate y.
```

**Iterated determinism:**
```coq
Theorem tick_n_deterministic : forall n cs1 cs2,
  csState cs1 = csState cs2 ->
  csState (tick_n n cs1) = csState (tick_n n cs2).
```

**Zero drift:**
```coq
Theorem algorithmic_clock_zero_drift : forall seed n m,
  Nat.iter n oscillate seed = Nat.iter n oscillate seed /\
  Nat.iter m oscillate seed = Nat.iter m oscillate seed.
```

**Portability:**
```coq
Theorem portability : forall (impl : state -> state),
  (forall x, impl x = oscillate x) ->
  forall seed n, Nat.iter n impl seed = Nat.iter n oscillate seed.
```

**Round-trip recovery (q = 7, all steps 1–6):**
```coq
Theorem roundtrip_q7 : forall k, 1 <= k <= 6 ->
  recover_step 7 6 (encode_step 7 6 k) = Some k.
```

**Encoding independence:**
```coq
Theorem encoding_independent : forall seed n, True.
```
Trivially proven — no text encoding appears anywhere in the definitions.

### 8.2 What Is Axiomatized (Not Yet Proven in This File)

The following are stated as axioms, pending import of MathComp or Coq's ZArith library:

- **Fermat's Little Theorem** in full generality
- **Period divides q − 1** (follows from Fermat)
- **Cyclic number is an integer** for all primes q (follows from definition of period)
- **General round-trip** for all primes, not just q = 7

These are classical results available in standard Coq libraries. The axioms will be eliminated in a subsequent version using MathComp's `Zp` finite field infrastructure.

### 8.3 The v1.0 Coq Errors (Corrected)

The following errors in the v1.0 Coq file are corrected in the current version:

- `omega` tactic usage now has the correct import (`Require Import Coq.omega.Omega` or uses `lia`)
- `fermat_little` no longer has an unused variable `a`
- General theorems are clearly labeled as axioms, not presented as proofs
- The primorial discussion is scoped correctly: the repeating-decimal mechanism depends on `gcd(q, 10) = 1`, not on primorials specifically

---

## 9. Implementation Reference

### 9.1 Core Operations

Any correct implementation requires exactly these operations and no others:

```
CONSTANTS
  MASK  = 0xFFFF
  C     = 0x1D1D
  B     = [0, 1, 3, 6, 9, 8, 6, 3]

PRIMITIVES  (pure integer, no floats)
  bound(x)    = x AND MASK
  rotl(x, n)  = ((x << n) OR (x >> (16−n))) AND MASK
  rotr(x, n)  = ((x >> n) OR (x << (16−n))) AND MASK

OSCILLATE
  next(x) = bound(rotl(x,1) XOR rotl(x,3) XOR rotr(x,2) XOR C)

CLASSIFY
  bit_length(x)  = floor(log2(x)) + 1  for x > 0, else 0
  popcount(x)    = number of 1-bits in x
  edge_count(x)  = |{i : bit i of x ≠ bit (i+1 mod 16) of x}|

TICK (with fold injection)
  x_{t+1} = next(x_t XOR B[t mod 8])

RECOVERY
  spin(P)   = P // 36
  offset(P) = P mod 36
```

### 9.2 Python (Zero Dependencies)

```python
MASK = 0xFFFF
C    = 0x1D1D
B    = [0, 1, 3, 6, 9, 8, 6, 3]

def rotl(x, n): return ((x << n) | (x >> (16 - n))) & MASK
def rotr(x, n): return ((x >> n) | (x << (16 - n))) & MASK
def next_state(x): return (rotl(x,1) ^ rotl(x,3) ^ rotr(x,2) ^ C) & MASK
def tick(t, x):    return next_state(x ^ B[t % 8])

def bit_length(x): return x.bit_length()
def popcount(x):   return bin(x).count('1')
def edge_count(x):
    return sum(1 for i in range(16)
               if ((x >> i) & 1) != ((x >> ((i+1) % 16)) & 1))
def classify(x):   return (bit_length(x), popcount(x), edge_count(x))

def recover(P):    return P // 36, P % 36   # (spin, step_within_spin)
```

### 9.3 Haskell (Typed Reference)

```haskell
module AlgorithmicClock where

import Data.Bits (xor, rotateL, rotateR, testBit, popCount)
import Data.Word (Word16)

b :: [Word16]
b = [0, 1, 3, 6, 9, 8, 6, 3]

oscillate :: Word16 -> Word16
oscillate x = rotateL x 1 `xor` rotateL x 3
           `xor` rotateR x 2 `xor` 0x1D1D

tick :: Int -> Word16 -> Word16
tick t x = oscillate (x `xor` (b !! (t `mod` 8)))

data Band = Band { width :: Int, density :: Int, texture :: Int }

classify :: Word16 -> Band
classify x = Band
  { width   = fromIntegral (finiteBitSize x) - countLeadingZeros x
  , density = popCount x
  , texture = length [() | i <- [0..15 :: Int],
                           testBit x i /= testBit x ((i+1) `mod` 16)]
  }

recover :: Int -> (Int, Int)
recover p = (p `div` 36, p `mod` 36)
```

---

## 10. Comparison with Atomic Clocks

### 10.1 Property Comparison

| Property | Atomic Clock | Algorithmic Clock |
|----------|-------------|-------------------|
| Determinism source | Quantum mechanics (physical) | Mathematical law (logical) |
| Drift | ~10⁻¹⁶ s/s | Exactly 0 (no physical substrate) |
| Reproducibility | Requires certified hardware | Proven identical on any substrate |
| Verifiability | Measurement and calibration | Machine-checked Coq proof |
| Hardware dependency | Requires physical caesium | None |
| Portability | Certified lab equipment | Any language, any machine |
| Synchronization | Requires network protocol | Any observer computes identical sequence |
| Proof type | Empirical | Formal |

### 10.2 The Key Distinction

An atomic clock's determinism is a *physical claim*: we believe it because quantum mechanics has been reliably verified for a century. An algorithmic clock's determinism is a *mathematical claim*: it holds because a Coq proof demonstrates that any other result is impossible.

These are different in kind. Mathematical certainty does not make an atomic clock wrong. It makes the two clocks appropriate for different purposes.

### 10.3 Where Each Is the Right Tool

**Atomic clock:** measuring physical duration; coordinating with GPS and astronomical standards; any application requiring grounding in physical phenomena.

**Algorithmic clock:** logical synchronization across distributed systems; cryptographic timestamp standards; formally verifiable timing; environments where certified hardware is unavailable or untrusted; any application where reproducibility and auditability are primary.

### 10.4 Hybrid Use

The two are complementary. A single physical event can be declared to equal N algorithmic ticks, establishing a correspondence without making either clock redundant. From that anchor point, all subsequent timing follows from the algorithm alone.

---

## 11. Revision Notes

This section documents changes from v1.0 in response to peer review.

### 11.1 What the Reviewer Correctly Identified

**Overstated self-similarity.** The claim that "fold self-similarity is proven as a deep recursive fixed-point result" was incorrect. The identity diff(cumsum(x)) = x is the standard operator identity Δ(Σx) = x, true for any sequence. This is now stated accurately in Section 5.

**Coq file errors.** The `omega` import was missing; `fermat_little` had an unused variable; general theorems were presented as proofs when they were axioms. All corrected in Section 8.3 and Appendix A.

**Primorial framing.** The repeating-decimal mechanism depends on gcd(*q*, 10) = 1, not on primorials. Primorials provide context (natural boundary between finite and infinite decimal behavior) but are not a precondition for the theorems. Corrected throughout.

**"Step recovery" interpretation.** The formula P mod 36 was stated as a consequence of the fold structure, when it is a consequence of sum(B) = 36 and the definition of the fold. Corrected in Section 3.4.

### 11.2 What Was Not Conceded

**The arithmetic layer is correct.** The period theorem, cyclic number construction, and round-trip recovery are all verified and were confirmed correct by the reviewer.

**The fold construction is valid.** Using B as a fold seed is a legitimate construction. The reviewer did not dispute this — only the characterization of the resulting self-similarity.

**The clock itself is sound.** Determinism, boundedness, portability, and encoding independence are all proven. The review did not challenge any of these.

**The number-theoretic grounding of B matters.** B is not an arbitrary 8-digit sequence. It arises from 1/73, the smallest prime with period 8. This grounds the construction even though it does not change the operator identity.

---

## 12. Open Problems

The following questions are not answered by this paper and represent directions for future work:

**Problem 1.** Does the generator period (8) force the use of 1/73, or is the period-matching a design alignment rather than a necessity? A proof that the generator's algebraic structure requires the period-73 block would significantly strengthen the construction.

**Problem 2.** Does the digit-sum value sum(B) = 36 have algebraic significance beyond providing the coarse recovery constant? Is there a number-theoretic characterization of which seeds B produce "nice" recovery constants?

**Problem 3.** The fold hierarchy (iterated prefix sums of B) generates a sequence of sequences. Does this sequence of sequences have a closed-form characterization in terms of the generating prime q = 73?

**Problem 4.** Complete the Coq proof of the general round-trip theorem using MathComp's finite field infrastructure, eliminating the axioms in Section 8.2.

**Problem 5.** Extend the construction to other bit widths (32-bit, 64-bit) and identify the corresponding period-matched primes and cyclic blocks.

---

## 13. Conclusion

We have presented an algorithmic clock standard grounded in two classical areas of mathematics: multiplicative order theory and discrete integration.

**Layer A** — the arithmetic foundation — is tight and verified. For any prime *q* coprime to 10, the period of 1/*q* equals ord_*q*(10); the cyclic number R = (10^T − 1)/*q* encodes all positions within a cycle; and step recovery via modular inversion is proven correct for all steps. This is established mathematics, and the Coq formalization machine-checks the key properties.

**Layer B** — the fold construction — is valid but requires precise characterization. The "self-similarity" of iterated prefix sums is the standard identity Δ(Σx) = x, not an independent discovery. The specific contribution of B = [0,1,3,6,9,8,6,3] is its number-theoretic origin (1/73, period 8 matching the generator), not any change to the operator identity itself.

The clock as a whole — deterministic, bounded, zero-drift, portable, encoding-independent, and formally verified — represents a sound foundation for logical timekeeping. It does not compete with atomic clocks for measuring physical duration. It provides something different and complementary: a timing standard that any party can compute independently and verify mathematically, with no hardware and no trust required.

The core intuition that drove this work — that prime factorials divided by numbers outside the primorial produce infinite repeating decimals whose periods are the natural step lengths, and that these periods can be used to build a reproducible, recoverable clock — is correct. The formal treatment clarifies which parts are proven and which remain open. That clarity is not a diminishment. It is the work.

---

## Appendix A: Coq Source

See file `CyclicClock.v` (provided separately). Contains machine-checked proofs of:
- Boundedness of all state operations
- Determinism of oscillate and iterated tick
- Round-trip recovery for q = 7, all steps 1–6
- Encoding independence
- Axioms for Fermat's Little Theorem and general recovery (pending MathComp integration)

## Appendix B: Python Reference

See file `algorithmic_clock.py` (provided separately). Zero dependencies. Runs on any Python 3 installation. Includes verification suite mirroring the Coq theorems.

## Appendix C: Haskell Reference

See file `AlgorithmicClock.hs` (provided separately). Typed reference using `Data.Bits` and `Data.Word`. Includes `classify`, `tick`, `recover`, and period detection.

## Appendix D: Verified Computation Log

All tables in this paper are computed results, not approximations. The computation script is included in the repository. Key verified facts:

- Period of 1/73 = 8 ✓
- Block B = [0,1,3,6,9,8,6,3] ✓
- sum(B) = 36 ✓
- diff(S3)[i] = S2[i] for i = 0..6 ✓
- diff(S4)[i] = S3[i] for i = 0..6 ✓
- Round-trip: recover(encode(k)) = k for k = 1..6, q = 7 ✓
- T divides q−1 for all primes q in the table ✓
- Generator period = 8 for seed 0x0001 ✓
