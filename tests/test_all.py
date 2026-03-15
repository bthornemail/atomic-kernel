# tests/test_all.py
#
# Run with: python3 tests/test_all.py
# All tests must pass before you ship anything.

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crystal import tick, position_at, read, state_at, run, W, T, B, MASK
from identity import clock, sid, sid_for_object, oid, ObjectChain, replay_chain, GENESIS
from observer import observe, SEEDS
from world import frame, trace

PASS = 0
FAIL = 0

def check(name, condition):
    global PASS, FAIL
    if condition:
        print(f"  ✓ {name}")
        PASS += 1
    else:
        print(f"  ✗ FAIL: {name}")
        FAIL += 1

print("=" * 55)
print("ATOMIC KERNEL — FULL TEST SUITE")
print("=" * 55)

# ── Crystal ───────────────────────────────────────────────────────
print("\nCrystal:")
check("period T = 8",           T == 8)
check("orbit weight W = 36",    W == 36)
check("block B sums to 36",     sum(B) == 36)
check("block B length 8",       len(B) == 8)
check("position_at(0) = 0",     position_at(0) == 0)
check("position_at(8) = 36",    position_at(8) == 36)
check("position_at(16) = 72",   position_at(16) == 72)
check("read(36) = (1,0)",        read(36) == (1, 0))
check("read(72) = (2,0)",        read(72) == (2, 0))
check("state bounded",          all(state_at(1, n) <= MASK for n in range(32)))
check("state_at period=16",     state_at(0x0001, 16) == 0x0001)
check("determinism",            state_at(0x0001, 100) == state_at(0x0001, 100))

rows = run(0x0001, 8)
check("run returns 8 rows",     len(rows) == 8)
check("run orbit 0 in first spin", all(r['orbit'] == 0 for r in rows))

# ── Identity ──────────────────────────────────────────────────────
print("\nIdentity:")
c0 = clock(0)
c8 = clock(8)
check("clock(0) frame=0",       c0['frame'] == 0)
check("clock(0) tick=1",        c0['tick'] == 1)
check("clock(8) frame=1",       c8['frame'] == 1)
check("clock string format",    c0['str'] == "0.1.00")
check("clock deterministic",    clock(42)['str'] == clock(42)['str'])

s1 = sid_for_object(0x0001)
s2 = sid_for_object(0xCAFE)
check("SID is sha3_256 prefixed",  s1.startswith("sha3_256:"))
check("SID length correct",      len(s1) == 9 + 64)
check("SID stable",              sid_for_object(0x0001) == sid_for_object(0x0001))
check("Different seeds → different SIDs", s1 != s2)

chain = ObjectChain(0x0001)
r0 = chain.step(0)
r8 = chain.step(8)
check("OID is sha3_256 prefixed",  r0['oid'].startswith("sha3_256:"))
check("OID changes each step",   r0['oid'] != r8['oid'])
check("prev_oid chains",         r8['prev_oid'] == r0['oid'])
check("first prev_oid = genesis", r0['prev_oid'] == GENESIS)
check("verify r0",               chain.verify(r0))
check("verify r8",               chain.verify(r8))

# Replay produces identical chain
replayed = replay_chain(0x0001, [0, 8])
check("replay OID[0] matches",   replayed[0]['oid'] == r0['oid'])
check("replay OID[1] matches",   replayed[1]['oid'] == r8['oid'])

# ── Observer ──────────────────────────────────────────────────────
print("\nObserver:")
o = observe(0x0001, 0)
check("observe returns seed",    o['seed'] == 0x0001)
check("observe returns hex",     o['hex'] == '0x0001')
check("observe x in [0,63]",     0 <= o['x'] <= 63)
check("observe y >= 0",          o['y'] >= 0)
check("observe has color",       o['color'].startswith('rgb('))
check("observe has symbol",      len(o['symbol']) == 1)
check("observe deterministic",   observe(0x0001, 42) == observe(0x0001, 42))
check("16 seeds defined",        len(SEEDS) == 16)
check("all seeds unique",        len(set(SEEDS)) == 16)

# ── World ─────────────────────────────────────────────────────────
print("\nWorld:")
f0 = frame(0)
check("frame returns 16 objects",   len(f0) == 16)
check("all objects have orbit",     all('orbit' in o for o in f0))
check("frame deterministic",        frame(42) == frame(42))
check("frame 0 != frame 8",         frame(0) != frame(8))

t0 = trace(0, 4)
check("trace returns 4 frames",     len(t0) == 4)
check("trace frame 0 == frame(0)",  t0[0] == frame(0))
check("trace frame 3 == frame(3)",  t0[3] == frame(3))

# ── Final ─────────────────────────────────────────────────────────
print()
print("=" * 55)
total = PASS + FAIL
print(f"  {PASS}/{total} passed  {'✓ ALL GOOD' if FAIL == 0 else f'✗ {FAIL} FAILED'}")
print("=" * 55)
sys.exit(0 if FAIL == 0 else 1)
