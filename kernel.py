# kernel.py
# The algorithmic clock kernel.
# Pure Python, zero dependencies.
# This is the whole engine.

WIDTH = 16
MASK  = (1 << WIDTH) - 1
C     = 0x1D1D
B     = [0, 1, 3, 6, 9, 8, 6, 3]   # period-8 differential block (from 1/73)
T     = len(B)                       # 8  — steps per spin
W     = sum(B)                       # 36 — total position advance per spin

# ── Bit primitives ────────────────────────────────────────────────
def rotl(x, n): return ((x << n) | (x >> (WIDTH - n))) & MASK
def rotr(x, n): return ((x >> n) | (x << (WIDTH - n))) & MASK

# ── State transition ──────────────────────────────────────────────
def next_state(x):
    return (rotl(x, 1) ^ rotl(x, 3) ^ rotr(x, 2) ^ C) & MASK

# ── One clock tick ────────────────────────────────────────────────
def tick(state, t):
    return next_state(state ^ B[t % T])

# ── Position accumulation ─────────────────────────────────────────
def position_at(n):
    """Total accumulated position after n ticks."""
    full, rem = divmod(n, T)
    return full * W + sum(B[:rem])

# ── Recovery ─────────────────────────────────────────────────────
def recover(position):
    """Decompose accumulated position into orbit and offset."""
    orbit, offset = divmod(position, W)
    return orbit, offset

# ── Classification (band reading) ─────────────────────────────────
def classify(x):
    x &= MASK
    width   = x.bit_length()
    density = bin(x).count('1')
    texture = sum(1 for i in range(WIDTH)
                  if ((x >> i) & 1) != ((x >> ((i + 1) % WIDTH)) & 1))
    return width, density, texture

# ── Full replay ───────────────────────────────────────────────────
def replay(seed, steps):
    """
    Run the clock for `steps` ticks from `seed`.
    Returns a list of dicts — one per tick.
    Each dict is the complete readable state of the world at that tick.
    """
    state = seed & MASK
    pos   = 0
    out   = []

    for t in range(steps):
        orbit, offset = recover(pos)
        w, d, tex     = classify(state)
        out.append({
            "t"       : t,
            "state"   : state,
            "state_hex": f"0x{state:04X}",
            "position": pos,
            "orbit"   : orbit,
            "offset"  : offset,
            "phase"   : t % T,
            "diff"    : B[t % T],
            "band"    : (w, d, tex),
        })
        pos   += B[t % T]
        state  = tick(state, t)

    return out
