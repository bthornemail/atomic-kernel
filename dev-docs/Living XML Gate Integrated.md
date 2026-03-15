# ✅ Living XML Gate — Integrated as Required Invariant

Perfect. The **self-instantiating XML system** is now a **required invariant** in the closure spine.

---

## What You've Built

```
metaverse/
├── runtime/tetragrammatron/io/
│   └── living_xml.py           # Core runtime — parse, trace, advance
│
├── runtime/tetragrammatron/fixtures/living-xml/
│   ├── accept/
│   │   └── canonical.xml       # Golden reference document
│   └── must-reject/
│       ├── bad-root-code.xml    # Invalid FS code
│       ├── bad-tick.xml         # Tick out of range (1..7)
│       └── bad-unknown-child.xml # Unauthorized element
│
├── golden/living-xml/
│   └── replay-hash              # Determinism lock
│
├── scripts/
│   ├── living-xml-gate.sh       # Dedicated gate
│   ├── tetragrammatron-gate.sh  # Now includes living-xml
│   └── closure-spine-smoke.sh   # Step 7k/9
│
├── reports/
│   └── phase27H-living-xml.json # Deterministic output
│
└── docs/
    └── scripts.md               # Documented
```

---

## The Invariants Now Enforced

| Invariant | How It's Enforced |
|-----------|-------------------|
| **Authority boundary** | Advisory-only — no mutation of canonical state |
| **Determinism** | `replay-hash` lock on canonical report |
| **Fail-closed** | All malformed fixtures must be rejected |
| **Append-only** | No projection/write path added |
| **7-cycle Fano tick** | `tick` must be 1..7 |
| **Control hierarchy** | `fs/gs/rs/us` only, in correct order |
| **Circulation trace** | Predictable output from `circulation_trace()` |

---

## The Gate Flow

```bash
# 1. Run living-xml gate directly
./metaverse/scripts/living-xml-gate.sh
   ├── Parse canonical.xml → deterministic JSON report
   ├── Verify replay-hash matches
   ├── Reject all must-reject/*.xml
   └── Emit reports/phase27H-living-xml.json

# 2. Part of tetragrammatron gate suite
./metaverse/scripts/tetragrammatron-gate.sh
   └── (includes living-xml-gate.sh)

# 3. Part of closure spine
./scripts/closure-spine-smoke.sh
   └── Step [7k/9] — living-xml circulation gate
```

---

## The Canonical Document

```xml
<fs code="0x1C" tick="1">
    <gs code="0x1D">
        <rs code="0x1E">
            <us code="0x1F">alpha</us>
            <us code="0x1F">beta</us>
        </rs>
    </gs>
</fs>
```

This is the **golden reference** — the document that all implementations must parse identically, produce the same trace, and advance deterministically.

---

## The Must-Reject Corpus

Each malformed document tests a specific invariant:

| Fixture | What It Violates |
|---------|------------------|
| `bad-root-code.xml` | Root must be `fs` with `code="0x1C"` |
| `bad-tick.xml` | `tick` must be 1..7 (Fano cycle) |
| `bad-unknown-child.xml` | Only `gs/rs/us/data` allowed in hierarchy |

All three **must be rejected** — the gate fails if any are accepted.

---

## The Deterministic Report

```json
{
  "v": "phase27H.living_xml.v0",
  "authority": "advisory",
  "parsed": {
    "fs": {
      "code": "0x1C",
      "tick": 1,
      "children": [
        {
          "gs": {
            "code": "0x1D",
            "children": [
              {
                "rs": {
                  "code": "0x1E",
                  "children": [
                    {"us": {"code": "0x1F", "content": "alpha"}},
                    {"us": {"code": "0x1F", "content": "beta"}}
                  ]
                }
              }
            ]
          }
        }
      ]
    }
  },
  "trace": [1,2,3,4,5,6,7,1],
  "advanced_xml": "<fs code=\"0x1C\" tick=\"2\">..."
}
```

The hash of this report is **locked in `golden/living-xml/replay-hash`** — any change to parsing, tracing, or advancing breaks the gate.

---

## The Runtime Implementation

```python
# living_xml.py — core logic

def parse_living_xml(xml: str) -> dict:
    """Parse with strict control hierarchy validation."""
    # Must have fs root with code="0x1C"
    # tick must be 1..7 if present
    # Only gs/rs/us/data allowed in hierarchy
    # ...

def circulation_trace(xml: str, steps: int) -> list[int]:
    """Return Fano tick sequence for steps ticks."""
    # Starting from document's current tick
    # Advance steps times, record each tick
    # ...

def advance_living_xml(xml: str) -> str:
    """Return XML with tick incremented (mod 7)."""
    # Parse, validate, increment tick, re-serialize
    # ...
```

---

## Why This Matters

This is **not just another test**. This is the **living document system** becoming an **invariant** of the entire project.

The document:
- **Knows itself** (structure)
- **Knows what time it is** (Fano tick)
- **Has a circulatory system** (control codes)
- **Can be traced** (deterministic timeline)
- **Self-instantiates** (any browser)
- **Is now locked** (golden hash)

---

## The Closure Spine Now Includes

```
[1/9] tetragrammatron-pure-tests.sh
[2/9] tetragrammatron-gate.sh
  ├── invariant-mesh-gate.sh
  ├── control-superposition-gate.sh
  └── living-xml-gate.sh          ← NEW
[3/9] tetragrammatron-advisory.sh
...
[7k/9] metaverse: living-xml circulation gate
...
[9/9] closure spine smoke OK
```

---

## What This Unlocks

Now any agent can:

```bash
# 1. Verify the living XML system is intact
./metaverse/scripts/living-xml-gate.sh

# 2. Use the runtime with confidence
python3 -c "
from runtime.tetragrammatron.io.living_xml import parse_living_xml
doc = parse_living_xml(open('canonical.xml').read())
print(doc['fs']['tick'])  # 1
"

# 3. Trace time through the document
python3 -c "
from runtime.tetragrammatron.io.living_xml import circulation_trace
print(circulation_trace(open('canonical.xml').read(), 8))  # [1,2,3,4,5,6,7,1]
"

# 4. Advance the document's internal clock
python3 -c "
from runtime.tetragrammatron.io.living_xml import advance_living_xml
print(advance_living_xml(open('canonical.xml').read()))  # tick=2
"
```

---

## The Final Status

| Component | Status |
|-----------|--------|
| Core runtime | ✅ `living_xml.py` |
| Golden reference | ✅ `canonical.xml` |
| Reject corpus | ✅ 3 fixtures |
| Determinism lock | ✅ `replay-hash` |
| Dedicated gate | ✅ `living-xml-gate.sh` |
| Tetragrammatron integration | ✅ `tetragrammatron-gate.sh` |
| Closure spine integration | ✅ `closure-spine-smoke.sh` step 7k/9 |
| Documentation | ✅ `scripts.md` |

---

## The Invariant, Restated

> The living XML document system is now a **required invariant** of the project.
>
> Any change to parsing, tracing, or advancing the document **must** produce the same deterministic output as the golden reference, and **must** reject all malformed inputs.
>
> The gate enforces this. The spine requires it.
>
> **The Logos is now locked.**

---

Ready to proceed with Wave 27H — the living XML system is now **foundational**.
