# Atomic Kernel

A deterministic timing and identity substrate.
Everything in the world observes the crystal. Nothing adds to it.

## What this is

A CPU crystal doesn't compute anything — it oscillates and everything
else uses it as a reference. This is that crystal, in software.

From that one crystal, every object in the world gets:
- a **position** in time (orbit + offset)
- a **stable identity** (SID — what it is, forever)
- an **unforgeable occurrence chain** (OID — when it happened)

No wall-clock time. No random numbers. No network needed.
Same seed + same tick = identical output on any machine, always.

## Files

```
atomic-kernel/
  crystal.py      — the timing law (THE foundation)
  identity.py     — CLOCK + SID + OID (deterministic identity)
  observer.py     — one object reading the crystal
  world.py        — 16 observers sharing one crystal
  world.html      — open in any browser, no server needed
  tests/
    test_all.py   — run this to verify everything works
  README.md       — this file
```

## Run it

```bash
# Verify everything works (47 tests, all must pass)
python3 tests/test_all.py

# Run v1 API + dashboard (stdlib HTTP server)
python3 api_server.py
# open http://127.0.0.1:8080

# Run v1 deterministic/API tests
python3 tests/test_v1.py

# Run Haskell oracle conformance gate (fixtures + python + runhaskell)
python3 conformance.py

# Open the live world viewer
open world.html          # macOS
xdg-open world.html      # Linux
# or just drag world.html into any browser
```

## The algorithm

```
crystal tick n
    → state    = oscillate(seed XOR B[n%8])   — where in the cycle
    → position = cumsum(B)[n]                  — how far from origin
    → orbit    = position // 36               — coarse time (minute hand)
    → offset   = position %  36               — fine time   (second hand)

identity
    → CLOCK = "orbit.phase.offset"            — when, in crystal time
    → SID   = sha256("world.object:0xSEED")   — what this object is
    → OID   = sha256(clock:sid:prev_oid)      — this specific occurrence

observer
    → reads (state, orbit, offset) from crystal
    → derives (x, y, color, symbol) for the world
    → has SID + OID chain for identity

world
    → 16 observers, same crystal, same tick
    → frame(n) is identical on every machine
    → frame(n) can be computed without running 0..n-1
```

## Why it works

The block B = [0,1,3,6,9,8,6,3] comes from 1/73.
73 is the smallest prime whose decimal repeats every 8 digits.
The generator has period 8 — so 73 is forced by the math, not chosen.
sum(B) = 36, which is the orbit weight for position recovery.

The OID chain cannot be forged: changing any occurrence breaks
every OID that follows it. Any observer can verify any claim
by recomputing the chain from scratch.

## Requirements

Python 3.8+, standard library only. No dependencies.
The browser viewer needs no server — just open world.html.
# atomic-kernel
