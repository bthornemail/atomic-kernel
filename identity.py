# identity.py
# Deterministic identity built entirely on the crystal.

from crystal import state_at, position_at, read, MASK
from canonical import DEFAULT_HASH_ALGO, digest_text, parse_tagged_digest

GENESIS = "genesis"


def clock(n):
    pos = position_at(n)
    orbit, offset = read(pos)
    frame = orbit
    tick = (n % 8) + 1
    control = offset
    return {
        "frame": frame,
        "tick": tick,
        "control": control,
        "str": f"{frame}.{tick}.{control:02X}",
        "n": n,
    }


def sid(type_str, canonical_form, hash_algo: str = DEFAULT_HASH_ALGO):
    raw = f"{type_str}:{canonical_form}"
    return digest_text(raw, hash_algo=hash_algo)


def sid_for_object(seed, hash_algo: str = DEFAULT_HASH_ALGO):
    return sid("world.object", f"0x{seed & MASK:04X}", hash_algo=hash_algo)


def oid(clock_str, sid_str, prev_oid, hash_algo: str = DEFAULT_HASH_ALGO):
    raw = f"{clock_str}:{sid_str}:{prev_oid}"
    return digest_text(raw, hash_algo=hash_algo)


class ObjectChain:
    def __init__(self, seed, hash_algo: str = DEFAULT_HASH_ALGO):
        self.seed = seed & MASK
        self.hash_algo = hash_algo
        self.sid = sid_for_object(seed, hash_algo=hash_algo)
        self.prev_oid = GENESIS
        self.history = []

    def step(self, n):
        clk = clock(n)
        state = state_at(self.seed, n)
        this_oid = oid(clk["str"], self.sid, self.prev_oid, hash_algo=self.hash_algo)
        record = {
            "n": n,
            "seed": self.seed,
            "hash_algo": self.hash_algo,
            "sid": self.sid,
            "oid": this_oid,
            "prev_oid": self.prev_oid,
            "clock": clk["str"],
            "frame": clk["frame"],
            "tick": clk["tick"],
            "control": clk["control"],
            "state": state,
            "hex": f"0x{state:04X}",
        }
        self.prev_oid = this_oid
        self.history.append(record)
        return record

    def verify(self, record, allow_legacy_untagged: bool = False):
        try:
            if not allow_legacy_untagged:
                parse_tagged_digest(record["sid"])
                parse_tagged_digest(record["oid"])
        except ValueError:
            return False
        recomputed = oid(
            record["clock"],
            record["sid"],
            record["prev_oid"],
            hash_algo=record.get("hash_algo", self.hash_algo),
        )
        return recomputed == record["oid"]


def replay_chain(seed, tick_numbers, hash_algo: str = DEFAULT_HASH_ALGO):
    chain = ObjectChain(seed, hash_algo=hash_algo)
    return [chain.step(n) for n in tick_numbers]
