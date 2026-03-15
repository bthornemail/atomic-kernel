# observer.py
#
# An observer reads the crystal and derives its world state.
# Each observer has one property of its own: a seed.
# Everything else comes from (seed, n) and the crystal.

from crystal import state_at, position_at, read, MASK
from identity import ObjectChain

# 16 seeds — one per object in the default world
SEEDS = [
    0x0001, 0x0013, 0x00A7, 0x0401,
    0x1D1D, 0x2B3C, 0x3FFF, 0x4E2A,
    0x5A01, 0x6B6B, 0x7ABC, 0x8080,
    0x9F1E, 0xA3C5, 0xBEEF, 0xCAFE,
]

_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+="

def _color(state, orbit):
    r = (state >> 8) & 0xFF
    g = (state >> 3) & 0xFF
    b = (state ^ (orbit * 17)) & 0xFF
    return f"rgb({r},{g},{b})"

def _symbol(state, orbit):
    return _CHARS[(state ^ orbit) % len(_CHARS)]

def observe(seed, n):
    """
    Read the crystal at tick n through the lens of this seed.
    Returns everything needed to place and draw this object.
    Nothing is guessed — all derived from (seed, n).
    """
    state          = state_at(seed, n)
    position       = position_at(n)
    orbit, offset  = read(position)
    x      = state % 64
    y      = bin(state).count('1') * 4
    size   = 5 + (offset % 8)
    return {
        "seed"    : seed,
        "n"       : n,
        "state"   : state,
        "hex"     : f"0x{state:04X}",
        "position": position,
        "orbit"   : orbit,
        "offset"  : offset,
        "phase"   : n % 8,
        "x"       : x,
        "y"       : y,
        "size"    : size,
        "color"   : _color(state, orbit),
        "symbol"  : _symbol(state, orbit),
    }
