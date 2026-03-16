from dataclasses import dataclass
from typing import Dict, List, Tuple

from canonical import (
    DEFAULT_HASH_ALGO,
    MATH_ID_LAW_VERSION,
    SUPPORTED_HASH_ALGOS,
    canonical_hash,
    canonical_json_text,
    canonical_math_id,
)
from kernel import replay as kernel_replay

SUPPORTED_MODES = {"kernel", "16d"}
SUPPORTED_WIDTHS_16D = {16, 32, 64, 128, 256}
ALLOWED_4BIT_STATES = {0x0, 0x8, 0xC, 0xD, 0xE, 0xF}


@dataclass(frozen=True)
class ReplayArtifact:
    mode: str
    law_version: str
    width: int
    seed_hex: str
    steps: int
    hash_algo: str
    digest: str
    states: List[Dict[str, object]]
    replay_hash: str
    math_law_version: str
    math_id_v2: str
    canonical_json: str

    def as_dict(self) -> Dict[str, object]:
        return {
            "mode": self.mode,
            "law_version": self.law_version,
            "width": self.width,
            "seed_hex": self.seed_hex,
            "steps": self.steps,
            "hash_algo": self.hash_algo,
            "digest": self.digest,
            "states": self.states,
            "replay_hash": self.replay_hash,
            "math_law_version": self.math_law_version,
            "math_id_v2": self.math_id_v2,
            "canonical_json": self.canonical_json,
        }


def _mask(width: int) -> int:
    return (1 << width) - 1


def _rotl(x: int, n: int, width: int) -> int:
    n = n % width
    m = _mask(width)
    return ((x << n) | (x >> (width - n))) & m


def _rotr(x: int, n: int, width: int) -> int:
    n = n % width
    m = _mask(width)
    return ((x >> n) | (x << (width - n))) & m


def _constant_for_width(width: int) -> int:
    return int("1D" * (width // 8), 16)


def _delta_n(x: int, width: int) -> int:
    m = _mask(width)
    c = _constant_for_width(width)
    return (_rotl(x, 1, width) ^ _rotl(x, 3, width) ^ _rotr(x, 2, width) ^ c) & m


def _texture(state: int, width: int) -> int:
    return sum(
        1
        for i in range(width)
        if ((state >> i) & 1) != ((state >> ((i + 1) % width)) & 1)
    )


def _band(state: int, width: int) -> Dict[str, int]:
    return {
        "width": state.bit_length(),
        "density": state.bit_count(),
        "texture": _texture(state, width),
    }


def _state_4bit_projection(state: int) -> Dict[str, object]:
    nibble = state & 0xF
    names = {
        0x0: "VOID",
        0x8: "NULL",
        0xC: "ACTIVE_0",
        0xD: "ACTIVE_1",
        0xE: "ACTIVE_2",
        0xF: "ACTIVE_3",
    }
    return {
        "value": nibble,
        "hex": f"0x{nibble:X}",
        "valid": nibble in ALLOWED_4BIT_STATES,
        "name": names.get(nibble, "FORBIDDEN"),
    }


def _lane_matrix_16d(state: int) -> Dict[str, List[int]]:
    return {
        "FS": [(state >> 12) & 1, (state >> 13) & 1, (state >> 14) & 1, (state >> 15) & 1],
        "GS": [(state >> 8) & 1, (state >> 9) & 1, (state >> 10) & 1, (state >> 11) & 1],
        "RS": [(state >> 4) & 1, (state >> 5) & 1, (state >> 6) & 1, (state >> 7) & 1],
        "US": [(state >> 0) & 1, (state >> 1) & 1, (state >> 2) & 1, (state >> 3) & 1],
    }


def _validate_inputs(mode: str, width: int, seed: int, steps: int) -> Tuple[bool, str]:
    if mode not in SUPPORTED_MODES:
        return False, "INVALID_MODE"
    if steps < 1 or steps > 4096:
        return False, "INVALID_STEPS"
    if seed < 0:
        return False, "INVALID_SEED"
    if mode == "kernel" and width != 16:
        return False, "INVALID_WIDTH_FOR_MODE"
    if mode == "16d" and width not in SUPPORTED_WIDTHS_16D:
        return False, "INVALID_WIDTH_FOR_MODE"
    return True, "OK"


def replay_artifact(
    mode: str,
    width: int,
    seed: int,
    steps: int,
    hash_algo: str = DEFAULT_HASH_ALGO,
) -> ReplayArtifact:
    if hash_algo not in SUPPORTED_HASH_ALGOS:
        payload = {
            "mode": mode,
            "law_version": "invalid",
            "width": width,
            "seed_hex": hex(seed),
            "steps": steps,
            "error": "UNKNOWN_HASH_ALGO",
        }
        digest = canonical_hash(payload, hash_algo=DEFAULT_HASH_ALGO)
        return ReplayArtifact(
            mode=mode,
            law_version="invalid",
            width=width,
            seed_hex=hex(seed),
            steps=steps,
            hash_algo=DEFAULT_HASH_ALGO,
            digest=digest,
            states=[],
            replay_hash=digest,
            math_law_version=MATH_ID_LAW_VERSION,
            math_id_v2=canonical_math_id(payload),
            canonical_json=canonical_json_text(payload),
        )

    valid, reason = _validate_inputs(mode, width, seed, steps)
    if not valid:
        payload = {
            "mode": mode,
            "law_version": "invalid",
            "width": width,
            "seed_hex": hex(seed),
            "steps": steps,
            "error": reason,
        }
        digest = canonical_hash(payload, hash_algo=hash_algo)
        return ReplayArtifact(
            mode=mode,
            law_version="invalid",
            width=width,
            seed_hex=hex(seed),
            steps=steps,
            hash_algo=hash_algo,
            digest=digest,
            states=[],
            replay_hash=digest,
            math_law_version=MATH_ID_LAW_VERSION,
            math_id_v2=canonical_math_id(payload),
            canonical_json=canonical_json_text(payload),
        )

    if mode == "kernel":
        law_version = "kernel-v1"
        rows = kernel_replay(seed & 0xFFFF, steps)
        states: List[Dict[str, object]] = []
        for row in rows:
            states.append(
                {
                    "step": row["t"],
                    "state_hex": row["state_hex"],
                    "position": row["position"],
                    "orbit": row["orbit"],
                    "offset": row["offset"],
                    "phase": row["phase"],
                    "diff": row["diff"],
                    "band": {
                        "width": row["band"][0],
                        "density": row["band"][1],
                        "texture": row["band"][2],
                    },
                    "four_bit": _state_4bit_projection(row["state"]),
                    "lane16": _lane_matrix_16d(row["state"]),
                }
            )
    else:
        law_version = "16d-v1"
        m = _mask(width)
        state = seed & m
        states = []
        for step in range(steps):
            states.append(
                {
                    "step": step,
                    "state_hex": f"0x{state:0{width // 4}X}",
                    "band": _band(state, width),
                    "four_bit": _state_4bit_projection(state),
                    "lane16": _lane_matrix_16d(state),
                }
            )
            state = _delta_n(state, width)

    payload = {
        "mode": mode,
        "law_version": law_version,
        "width": width,
        "seed_hex": f"0x{seed & _mask(width):0{width // 4}X}",
        "steps": steps,
        "hash_algo": hash_algo,
        "states": states,
    }
    digest = canonical_hash(payload, hash_algo=hash_algo)
    canonical = canonical_json_text(payload)

    return ReplayArtifact(
        mode=mode,
        law_version=law_version,
        width=width,
        seed_hex=payload["seed_hex"],
        steps=steps,
        hash_algo=hash_algo,
        digest=digest,
        states=states,
        replay_hash=digest,
        math_law_version=MATH_ID_LAW_VERSION,
        math_id_v2=canonical_math_id(payload),
        canonical_json=canonical,
    )
