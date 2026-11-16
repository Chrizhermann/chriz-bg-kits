"""Clean-room binary packers for IE SPL V1, ITM V1, and EFF V2.0 resources."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any

EFF_V2_SIZE = 272
SPL_HEADER_SIZE = 0x72
SPL_ABILITY_SIZE = 0x28
ITM_HEADER_SIZE = 0x72
ITM_ABILITY_SIZE = 0x38
SPL_EFFECT_SIZE = 0x30


def _pack_resref(name: str) -> bytes:
    raw = (name or "").upper().encode("ascii")
    if len(raw) > 8:
        raise ValueError(f"Resref exceeds 8 chars: {name!r}")
    return raw.ljust(8, b"\x00")


def _unpack_resref(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("ascii", errors="replace").upper()


@dataclass
class StampRef:
    file: str
    offset: int
    size: int  # 1, 2, or 4
    kind: str  # "state", "splprot", "text", "sectype", "proj", "stat"
    symbol: str


def _resolve_sym(
    val: Any,
    filename: str,
    offset: int,
    size: int,
    stamps: list[StampRef],
    default: int = 0,
) -> int:
    if isinstance(val, dict):
        for kind in ("state", "splprot", "text", "sectype", "proj", "stat"):
            if kind in val:
                stamps.append(StampRef(filename, offset, size, kind, str(val[kind])))
                return int(val.get("default", default))
        raise ValueError(f"Unknown symbolic marker in {filename}: {val!r}")
    return int(val)


def pack_spl(spec: dict[str, Any], filename: str) -> tuple[bytes, list[StampRef]]:
    """Pack a SPL V1 dictionary and return (binary_bytes, stamp_refs)."""
    stamps: list[StampRef] = []
    abilities = spec.get("abilities", [])
    casting_effects = spec.get("casting_effects", [])

    ab_off = SPL_HEADER_SIZE
    fx_off = ab_off + len(abilities) * SPL_ABILITY_SIZE

    fx_blobs: list[bytes] = []
    cur_idx = 0

    def encode_effect(eff: dict[str, Any], abs_fx_off: int) -> bytes:
        opcode = int(eff["opcode"])
        target = int(eff.get("target", 1))
        power = int(eff.get("power", 0))
        p1 = _resolve_sym(eff.get("p1", 0), filename, abs_fx_off + 0x04, 4, stamps, 0)
        p2 = _resolve_sym(eff.get("p2", 0), filename, abs_fx_off + 0x08, 4, stamps, 0)
        timing = int(eff.get("timing", 0))
        dispel = int(eff.get("dispel", 0))
        duration = int(eff.get("duration", 0))
        prob1 = int(eff.get("prob1", 100))
        prob2 = int(eff.get("prob2", 0))
        res = _pack_resref(eff.get("resource", ""))
        dice = int(eff.get("dice", 0))
        sides = int(eff.get("sides", 0))
        save = int(eff.get("save", 0))
        bonus = int(eff.get("bonus", 0))
        special = _resolve_sym(eff.get("special", 0), filename, abs_fx_off + 0x2C, 4, stamps, 0)

        blob = struct.pack(
            "<HBBiiBBiBB8sIIIii",
            opcode,
            target,
            power,
            p1,
            p2,
            timing,
            dispel,
            duration,
            prob1,
            prob2,
            res,
            dice,
            sides,
            save,
            bonus,
            special,
        )
        assert len(blob) == SPL_EFFECT_SIZE
        return blob

    for eff in casting_effects:
        fx_blobs.append(encode_effect(eff, fx_off + cur_idx * SPL_EFFECT_SIZE))
        cur_idx += 1

    ab_blobs: list[bytes] = []
    for ab_idx, ab in enumerate(abilities):
        ab_effects = ab.get("effects", [])
        ab_fx_start = cur_idx
        for eff in ab_effects:
            fx_blobs.append(encode_effect(eff, fx_off + cur_idx * SPL_EFFECT_SIZE))
            cur_idx += 1

        ab_base = ab_off + ab_idx * SPL_ABILITY_SIZE
        proj_val = _resolve_sym(ab.get("projectile", 1), filename, ab_base + 0x26, 2, stamps, 1)
        unused_14 = bytes.fromhex(ab.get("unused_14", "00000600000000000100"))
        if len(unused_14) != 10:
            raise ValueError(f"Ability unused_14 must be 10 bytes in {filename}")

        ab_blob = struct.pack(
            "<BBH8sBBHHH",
            int(ab.get("form", 1)),
            int(ab.get("friendly", 0)),
            int(ab.get("location", 4)),
            _pack_resref(ab.get("icon", "")),
            int(ab.get("target", 5)),
            int(ab.get("target_count", 1)),
            int(ab.get("range", 0)),
            int(ab.get("min_level", 1)),
            int(ab.get("speed", 0)),
        ) + unused_14 + struct.pack(
            "<HHHHH",
            len(ab_effects),
            ab_fx_start,
            int(ab.get("charges", 1)),
            int(ab.get("charge_depletion", 1)),
            proj_val,
        )
        assert len(ab_blob) == SPL_ABILITY_SIZE
        ab_blobs.append(ab_blob)

    name_ref = _resolve_sym(spec.get("name", -1), filename, 0x08, 4, stamps, -1)
    id_name_ref = int(spec.get("id_name", -1))
    desc_ref = _resolve_sym(spec.get("description", -1), filename, 0x50, 4, stamps, -1)
    id_desc_ref = int(spec.get("id_description", -1))
    sectype = _resolve_sym(spec.get("sectype", 0), filename, 0x27, 1, stamps, 0)

    header = struct.pack(
        "<8sii8sIHIHBBBB12sIH8sH8sIii8sIIHIHH",
        b"SPL V1  ",
        name_ref,
        id_name_ref,
        _pack_resref(spec.get("sound", "")),
        int(spec.get("flags", 0)),
        int(spec.get("spell_type", 4)),
        int(spec.get("exclusions", 0)),
        int(spec.get("casting_graphics", 0)),
        int(spec.get("unknown_24", 0)),
        int(spec.get("school", 0)),
        int(spec.get("unknown_26", 0)),
        sectype,
        b"\x00" * 12,
        int(spec.get("level", 1)),
        int(spec.get("stack", 1)),
        _pack_resref(spec.get("icon", "")),
        int(spec.get("stack2", 0)),
        _pack_resref(spec.get("ground_icon", "")),
        int(spec.get("weight", 0)),
        desc_ref,
        id_desc_ref,
        _pack_resref(spec.get("desc_image", "")),
        int(spec.get("attributes", 0)),
        ab_off,
        len(abilities),
        fx_off,
        0,
        len(casting_effects),
    )
    assert len(header) == SPL_HEADER_SIZE
    return header + b"".join(ab_blobs) + b"".join(fx_blobs), stamps


def pack_eff(spec: dict[str, Any], filename: str) -> tuple[bytes, list[StampRef]]:
    """Pack a 272-byte EFF V2.0 dictionary and return (binary_bytes, stamp_refs)."""
    stamps: list[StampRef] = []
    buf = bytearray(EFF_V2_SIZE)
    buf[0x00:0x10] = b"EFF V2.0EFF V2.0"

    opcode = int(spec["opcode"])
    target = int(spec.get("target", 1))
    power = int(spec.get("power", 0))
    p1 = _resolve_sym(spec.get("p1", 0), filename, 0x1C, 4, stamps, 0)
    p2 = _resolve_sym(spec.get("p2", 0), filename, 0x20, 4, stamps, 0)
    timing = int(spec.get("timing", 0))
    duration = int(spec.get("duration", 0))
    prob1 = int(spec.get("prob1", 100))
    prob2 = int(spec.get("prob2", 0))
    res = _pack_resref(spec.get("resource", ""))
    dice = int(spec.get("dice", 0))
    sides = int(spec.get("sides", 0))
    save = int(spec.get("save", 0))
    bonus = int(spec.get("bonus", 0))
    special = _resolve_sym(spec.get("special", 0), filename, 0x48, 4, stamps, 0)
    school = int(spec.get("school", 0))
    min_level = int(spec.get("min_level", 0))
    max_level = int(spec.get("max_level", 0))
    dispel = int(spec.get("dispel", 0))
    p3 = _resolve_sym(spec.get("p3", 0), filename, 0x60, 4, stamps, 0)
    p4 = _resolve_sym(spec.get("p4", 0), filename, 0x64, 4, stamps, 0)
    res2 = _pack_resref(spec.get("resource2", ""))
    res3 = _pack_resref(spec.get("resource3", ""))
    source_x = int(spec.get("source_x", -1))
    source_y = int(spec.get("source_y", -1))
    target_x = int(spec.get("target_x", -1))
    target_y = int(spec.get("target_y", -1))
    parent_type = int(spec.get("parent_type", 0))
    parent_res = _pack_resref(spec.get("parent_resource", ""))
    parent_flags = int(spec.get("parent_flags", 0))
    proj = int(spec.get("projectile", 0))
    caster_level = int(spec.get("caster_level", 0))
    sectype = _resolve_sym(spec.get("sectype", 0), filename, 0xD0, 4, stamps, 0)

    struct.pack_into(
        "<IIIiiHHIHH8sIIiiII",
        buf,
        0x10,
        opcode,
        target,
        power,
        p1,
        p2,
        timing,
        0,
        duration,
        prob1,
        prob2,
        res,
        dice,
        sides,
        save,
        bonus,
        special,
        school,
    )
    struct.pack_into("<III", buf, 0x54, min_level, max_level, dispel)
    struct.pack_into("<ii", buf, 0x60, p3, p4)
    buf[0x70:0x78] = res2
    buf[0x78:0x80] = res3
    struct.pack_into("<iiii", buf, 0x80, source_x, source_y, target_x, target_y)
    struct.pack_into("<I8sII", buf, 0x90, parent_type, parent_res, parent_flags, proj)
    struct.pack_into("<II", buf, 0xC8, caster_level, sectype)
    return bytes(buf), stamps


def pack_itm(spec: dict[str, Any], filename: str) -> tuple[bytes, list[StampRef]]:
    """Pack an ITM V1 dictionary and return (binary_bytes, stamp_refs)."""
    stamps: list[StampRef] = []
    abilities = spec.get("abilities", [])
    equipping_effects = spec.get("equipping_effects", [])

    ab_off = ITM_HEADER_SIZE
    fx_off = ab_off + len(abilities) * ITM_ABILITY_SIZE

    fx_blobs: list[bytes] = []
    cur_idx = 0

    def encode_effect(eff: dict[str, Any], abs_fx_off: int) -> bytes:
        opcode = int(eff["opcode"])
        target = int(eff.get("target", 1))
        power = int(eff.get("power", 0))
        p1 = _resolve_sym(eff.get("p1", 0), filename, abs_fx_off + 0x04, 4, stamps, 0)
        p2 = _resolve_sym(eff.get("p2", 0), filename, abs_fx_off + 0x08, 4, stamps, 0)
        timing = int(eff.get("timing", 0))
        dispel = int(eff.get("dispel", 0))
        duration = int(eff.get("duration", 0))
        prob1 = int(eff.get("prob1", 100))
        prob2 = int(eff.get("prob2", 0))
        res = _pack_resref(eff.get("resource", ""))
        dice = int(eff.get("dice", 0))
        sides = int(eff.get("sides", 0))
        save = int(eff.get("save", 0))
        bonus = int(eff.get("bonus", 0))
        special = _resolve_sym(eff.get("special", 0), filename, abs_fx_off + 0x2C, 4, stamps, 0)
        blob = struct.pack(
            "<HBBiiBBiBB8sIIIii",
            opcode,
            target,
            power,
            p1,
            p2,
            timing,
            dispel,
            duration,
            prob1,
            prob2,
            res,
            dice,
            sides,
            save,
            bonus,
            special,
        )
        assert len(blob) == SPL_EFFECT_SIZE
        return blob

    for eff in equipping_effects:
        fx_blobs.append(encode_effect(eff, fx_off + cur_idx * SPL_EFFECT_SIZE))
        cur_idx += 1

    ab_blobs: list[bytes] = []
    for ab_idx, ab in enumerate(abilities):
        ab_effects = ab.get("effects", [])
        ab_fx_start = cur_idx
        for eff in ab_effects:
            fx_blobs.append(encode_effect(eff, fx_off + cur_idx * SPL_EFFECT_SIZE))
            cur_idx += 1

        ab_base = ab_off + ab_idx * ITM_ABILITY_SIZE
        proj_val = _resolve_sym(ab.get("projectile", 1), filename, ab_base + 0x2A, 2, stamps, 1)
        ab_blob = struct.pack(
            "<BBBB8sBBHBBBBhBBBBhHHHHHIHHHHHHH",
            int(ab.get("type", 1)),
            int(ab.get("id_req", 0)),
            int(ab.get("location", 1)),
            int(ab.get("alt_sides", 0)),
            _pack_resref(ab.get("icon", "")),
            int(ab.get("target", 1)),
            int(ab.get("target_count", 0)),
            int(ab.get("range", 2)),
            int(ab.get("launcher", 0)),
            int(ab.get("alt_dice", 0)),
            int(ab.get("speed", 2)),
            int(ab.get("alt_damage", 0)),
            int(ab.get("thac0_bonus", 0)),
            int(ab.get("sides", 6)),
            int(ab.get("school", 0)),
            int(ab.get("dice", 1)),
            int(ab.get("sectype", 0)),
            int(ab.get("damage_bonus", 0)),
            int(ab.get("damage_type", 2)),
            len(ab_effects),
            ab_fx_start,
            int(ab.get("charges", 0)),
            int(ab.get("charge_depletion", 0)),
            int(ab.get("ab_flags", 1)),
            proj_val,
            int(ab.get("overhand", 34)),
            int(ab.get("backhand", 33)),
            int(ab.get("thrust", 33)),
            0,
            0,
            0,
        )
        assert len(ab_blob) == ITM_ABILITY_SIZE
        ab_blobs.append(ab_blob)

    name_ref = _resolve_sym(spec.get("name", -1), filename, 0x08, 4, stamps, -1)
    id_name_ref = _resolve_sym(spec.get("id_name", -1), filename, 0x0C, 4, stamps, -1)
    desc_ref = _resolve_sym(spec.get("description", -1), filename, 0x50, 4, stamps, -1)
    id_desc_ref = _resolve_sym(spec.get("id_description", -1), filename, 0x54, 4, stamps, -1)
    anim_raw = (spec.get("animation", "  ") or "  ").encode("ascii")[:2].ljust(2, b" ")

    hdr = bytearray(ITM_HEADER_SIZE)
    hdr[0x00:0x08] = b"ITM V1  "
    struct.pack_into("<ii", hdr, 0x08, name_ref, id_name_ref)
    hdr[0x10:0x18] = _pack_resref(spec.get("replacement", ""))
    struct.pack_into(
        "<IHI",
        hdr,
        0x18,
        int(spec.get("flags", 0x0104206A)),
        int(spec.get("item_type", 28)),
        int(spec.get("unusable", 0)),
    )
    hdr[0x22:0x24] = anim_raw
    struct.pack_into("<HH", hdr, 0x24, int(spec.get("min_level", 0)), int(spec.get("min_str", 0)))
    hdr[0x31] = int(spec.get("proficiency", 0))
    struct.pack_into("<IH", hdr, 0x34, int(spec.get("price", 0)), int(spec.get("stack", 1)))
    hdr[0x3A:0x42] = _pack_resref(spec.get("icon", ""))
    struct.pack_into("<H", hdr, 0x42, int(spec.get("lore", 0)))
    hdr[0x44:0x4C] = _pack_resref(spec.get("ground_icon", ""))
    struct.pack_into("<Iii", hdr, 0x4C, int(spec.get("weight", 0)), desc_ref, id_desc_ref)
    hdr[0x58:0x60] = _pack_resref(spec.get("desc_image", ""))
    struct.pack_into(
        "<IIHIHH",
        hdr,
        0x60,
        int(spec.get("enchantment", 0)),
        ab_off,
        len(abilities),
        fx_off,
        0,
        len(equipping_effects),
    )
    return bytes(hdr) + b"".join(ab_blobs) + b"".join(fx_blobs), stamps


def inspect_spl_effects(raw: bytes) -> list[dict[str, Any]]:
    """Read header, abilities, and effects from raw SPL V1 bytes."""
    sig = raw[:8]
    if sig != b"SPL V1  ":
        raise ValueError(f"Not SPL V1: {sig!r}")
    ab_off, ab_cnt, fx_off, cast_idx, cast_cnt = struct.unpack_from("<IHIHH", raw, 0x64)
    fx_total = cast_cnt
    abilities = []
    for i in range(ab_cnt):
        base = ab_off + i * SPL_ABILITY_SIZE
        cnt, idx, _, _, proj = struct.unpack_from("<HHHHH", raw, base + 0x1E)
        min_lvl = struct.unpack_from("<H", raw, base + 0x10)[0]
        target = raw[base + 0x0C]
        abilities.append({"min_level": min_lvl, "target": target, "projectile": proj, "count": cnt, "index": idx})
        fx_total = max(fx_total, idx + cnt)

    def read_fx(idx: int) -> dict[str, Any]:
        off = fx_off + idx * SPL_EFFECT_SIZE
        op, tgt, pwr, p1, p2, tim, dsp, dur, pr1, pr2, res, dice, sides, sav, bon, sp = struct.unpack_from(
            "<HBBiiBBiBB8sIIIii", raw, off
        )
        return {
            "opcode": op,
            "target": tgt,
            "power": pwr,
            "p1": p1,
            "p2": p2,
            "timing": tim,
            "dispel": dsp,
            "duration": dur,
            "prob1": pr1,
            "prob2": pr2,
            "resource": _unpack_resref(res),
            "dice": dice,
            "sides": sides,
            "save": sav,
            "bonus": bon,
            "special": sp,
        }

    return {
        "flags": struct.unpack_from("<I", raw, 0x18)[0],
        "spell_type": struct.unpack_from("<H", raw, 0x1C)[0],
        "school": raw[0x25],
        "sectype": raw[0x27],
        "casting_effects": [read_fx(cast_idx + j) for j in range(cast_cnt)],
        "abilities": [
            {**ab, "effects": [read_fx(ab["index"] + j) for j in range(ab["count"])]}
            for ab in abilities
        ],
    }
