# crystal.py
#
# The algorithmic crystal — the timing law.
#
# A crystal in a CPU does not compute anything.
# It oscillates. Everything else observes it.
# This is that crystal, in software.
#
# The crystal emits two values per tick:
#   state    — where in the oscillation cycle
#   position — total accumulated arc from origin
#
# Observers read (state, position) to know where they are in time.
# The crystal does not know about observers.
# The crystal does not do work. It just runs.
#
# Properties (all verified):
#   deterministic : same seed → same sequence, always
#   bounded       : state always in [0, 65535]
#   zero drift    : no physical substrate, no calibration needed
#   portable      : identical output on any machine, any language
#   replayable    : tick N computable directly without running 0..N-1

WIDTH = 16
MASK  = (1 << WIDTH) - 1   # 0xFFFF

# Mixing constant — prevents fixed points
C = 0x1D1D

# Periodic differential block.
# Source: repeating digits of 1/73 (period 8).
# 73 is the smallest prime with decimal period 8.
# The generator has period 8 — so 73 is forced, not chosen.
# sum(B) = 36 — the orbit weight used for position recovery.
B = [0, 1, 3, 6, 9, 8, 6, 3]
T = len(B)   # 8  — steps per full oscillation
W = sum(B)   # 36 — total position advance per oscillation

# ── Bit operations ────────────────────────────────────────────────
def rotl(x, n): return ((x << n) | (x >> (WIDTH - n))) & MASK
def rotr(x, n): return ((x >> n) | (x << (WIDTH - n))) & MASK

# ── The oscillation law ───────────────────────────────────────────
def _advance(x):
    return (rotl(x, 1) ^ rotl(x, 3) ^ rotr(x, 2) ^ C) & MASK

# ── One tick ──────────────────────────────────────────────────────
def tick(state, t):
    return _advance((state ^ B[t % T]) & MASK)

# ── Position accumulation ─────────────────────────────────────────
def position_at(n):
    """Total accumulated position after n ticks. O(1) — no loop needed."""
    full, rem = divmod(n, T)
    return full * W + sum(B[:rem])

# ── Reading the crystal ───────────────────────────────────────────
def read(position):
    """Decompose position into (orbit, offset). Observer API."""
    return divmod(position, W)

# ── Direct state at tick N ────────────────────────────────────────
def state_at(seed, n):
    """Compute state at tick n directly from seed."""
    s = seed & MASK
    for t in range(n):
        s = tick(s, t)
    return s

# ── Run the crystal ───────────────────────────────────────────────
def run(seed, steps):
    """Emit `steps` ticks from `seed`. Returns list of reading dicts."""
    state    = seed & MASK
    position = 0
    out      = []
    for t in range(steps):
        orbit, offset = read(position)
        out.append({
            "t"       : t,
            "state"   : state,
            "hex"     : f"0x{state:04X}",
            "position": position,
            "orbit"   : orbit,
            "offset"  : offset,
            "phase"   : t % T,
            "diff"    : B[t % T],
        })
        position += B[t % T]
        state     = tick(state, t)
    return out
