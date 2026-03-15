# world.py
#
# The world is many observers reading the same crystal at the same tick.
# One tick = one frame. Same tick = identical frame, always, everywhere.
# The world has no state of its own — computed fresh each frame.

from observer import observe, SEEDS

def frame(n):
    """One complete world frame at tick n. Always identical for same n."""
    return [observe(seed, n) for seed in SEEDS]

def trace(start, steps):
    """Sequence of frames from tick `start` for `steps` ticks. Replay."""
    return [frame(n) for n in range(start, start + steps)]

if __name__ == "__main__":
    from identity import ObjectChain
    print("World + Identity test")
    print("=" * 55)
    objs = frame(0)
    print(f"{'seed':>8}  {'state':>8}  {'orbit':>5}  {'offset':>6}  color")
    print("-" * 50)
    for o in objs:
        print(f"{o['seed']:>8}  {o['hex']:>8}  {o['orbit']:>5}  "
              f"{o['offset']:>6}  {o['color']}")
    print()
    # Identity chain for first object
    chain = ObjectChain(SEEDS[0])
    print(f"Identity chain for seed {SEEDS[0]}:")
    for n in [0, 8, 16]:
        r = chain.step(n)
        print(f"  n={n:>3} clock={r['clock']}  oid=...{r['oid'][-8:]}")
    print()
    f1, f2 = frame(42), frame(42)
    ok = all(f1[i]['state'] == f2[i]['state'] for i in range(len(f1)))
    print(f"Determinism (frame 42 == frame 42): {ok} ✓")
