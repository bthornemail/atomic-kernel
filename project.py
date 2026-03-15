# project.py
# Maps clock states to visual / world properties.
# This is the layer between the kernel and any display.

from kernel import classify, MASK

# ── Color ─────────────────────────────────────────────────────────
def to_color(state):
    """Map a 16-bit state to an RGB hex color string."""
    r = (state >> 8) & 0xFF
    g = (state >> 4) & 0x0F
    b_val = state & 0x0F
    # Spread the nybbles into full byte range
    return f"#{r:02X}{(g << 4) | g:02X}{(b_val << 4) | b_val:02X}"

# ── Symbol ────────────────────────────────────────────────────────
# 64 printable ASCII symbols — no encoding dependency, just visual variety
_SYMBOLS = (
    "0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "!@#$%^&*()"
    "+-=<>?/|~"
)

def to_symbol(state):
    """Map state to a printable symbol."""
    return _SYMBOLS[state % len(_SYMBOLS)]

# ── Grid cell ─────────────────────────────────────────────────────
def to_cell(state, grid_width=64):
    """Map state to an (x, y) grid position."""
    x = state % grid_width
    y = (state // grid_width) % grid_width
    return x, y

# ── Full projection ───────────────────────────────────────────────
def project(state):
    """Return all visual properties for a given state."""
    w, d, tex = classify(state)
    x, y      = to_cell(state)
    return {
        "color"  : to_color(state),
        "symbol" : to_symbol(state),
        "x"      : x,
        "y"      : y,
        "width"  : w,
        "density": d,
        "texture": tex,
    }
