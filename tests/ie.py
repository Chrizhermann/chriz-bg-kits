"""Minimal Infinity Engine binary builders and inspectors for tests."""

from __future__ import annotations

import pathlib
import struct


def make_empty_chitin_key() -> bytes:
    # KEY V1 header: sig(8), biff_cnt(4), res_cnt(4), biff_off(4), res_off(4)
    return struct.pack("<8sIIII", b"KEY V1  ", 0, 0, 24, 24)


def make_dialog_tlk(strings: list[str] | None = None) -> bytes:
    entries = strings if strings is not None else ["", "placeholder"]
    hdr_size = 18
    ent_size = 26
    str_start = hdr_size + len(entries) * ent_size
    blobs = bytearray()
    ent_bytes = bytearray()
    for text in entries:
        raw = text.encode("utf-8")
        off = len(blobs)
        blobs.extend(raw)
        # flags=1 (text present), sound=8 bytes NUL, vol=0, pitch=0, off, len
        ent_bytes.extend(struct.pack("<H8sIIII", 1, b"\x00" * 8, 0, 0, off, len(raw)))
    hdr = struct.pack("<8sHII", b"TLK V1  ", 0, len(entries), str_start)
    return hdr + bytes(ent_bytes) + bytes(blobs)


def make_eff_v1(
    opcode: int,
    target: int = 1,
    p1: int = 0,
    p2: int = 0,
    timing: int = 1,
    dispel: int = 0,
    duration: int = 0,
    prob1: int = 100,
    prob2: int = 0,
    resource: str = "",
    special: int = 0,
) -> bytes:
    buf = bytearray(0x30)
    struct.pack_into("<HBBiiBBIBB", buf, 0x00, opcode, target, 0, p1, p2, timing, dispel, duration, prob1, prob2)
    res_b = resource.upper().encode("ascii")[:8].ljust(8, b"\x00")
    buf[0x14:0x1C] = res_b
    struct.pack_into("<i", buf, 0x2C, special)
    return bytes(buf)


def make_eff_v2(
    opcode: int = 0,
    target: int = 2,
    p1: int = 0,
    p2: int = 0,
    timing: int = 1,
    duration: int = 0,
    resource: str = "",
    min_level: int = 0,
) -> bytes:
    buf = bytearray(0x110)
    buf[0x00:0x08] = b"EFF V2.0"
    struct.pack_into("<II", buf, 0x10, opcode, target)
    struct.pack_into("<iii", buf, 0x1C, p1, p2, timing)
    struct.pack_into("<I", buf, 0x28, duration)
    struct.pack_into("<H", buf, 0x2C, 100)
    buf[0x30:0x38] = resource.upper().encode("ascii")[:8].ljust(8, b"\x00")
    struct.pack_into("<i", buf, 0x54, min_level)
    return bytes(buf)


def read_eff_v2(data: bytes) -> dict:
    assert data[:8] == b"EFF V2.0"
    opcode, target = struct.unpack_from("<II", data, 0x10)
    p1, p2, timing = struct.unpack_from("<iii", data, 0x1C)
    duration = struct.unpack_from("<I", data, 0x28)[0]
    res = data[0x30:0x38].split(b"\x00", 1)[0].decode("ascii", "replace")
    min_level = struct.unpack_from("<i", data, 0x54)[0]
    return {
        "opcode": opcode,
        "target": target,
        "p1": p1,
        "p2": p2,
        "timing": timing,
        "duration": duration,
        "resource": res,
        "min_level": min_level,
    }


def make_spl(
    spell_type: int = 4,
    school: int = 0,
    casting_effects: list[bytes] | None = None,
    abilities: list[tuple[int, int, list[bytes]]] | None = None,
) -> bytes:
    cast_fx = casting_effects or []
    abs_list = abilities if abilities is not None else [(1, 1, [])]
    hdr_size = 0x72
    ab_off = hdr_size
    ab_bytes = bytearray()
    fx_bytes = bytearray()
    for fx in cast_fx:
        fx_bytes.extend(fx)
    fx_idx = len(cast_fx)
    for min_lv, proj, fxs in abs_list:
        ab = bytearray(0x28)
        struct.pack_into("<BBH", ab, 0x00, 1, 0, 4)
        struct.pack_into("<B", ab, 0x0C, 5)
        struct.pack_into("<H", ab, 0x10, min_lv)
        struct.pack_into("<HHH", ab, 0x1E, len(fxs), fx_idx, 1)
        struct.pack_into("<H", ab, 0x26, proj)
        ab_bytes.extend(ab)
        for fx in fxs:
            fx_bytes.extend(fx)
        fx_idx += len(fxs)
    fx_off = ab_off + len(ab_bytes)
    hdr = bytearray(hdr_size)
    hdr[0x00:0x08] = b"SPL V1  "
    struct.pack_into("<ii", hdr, 0x08, -1, -1)
    struct.pack_into("<H", hdr, 0x1C, spell_type)
    struct.pack_into("<B", hdr, 0x25, school)
    struct.pack_into("<I", hdr, 0x34, 1)
    struct.pack_into("<i", hdr, 0x50, -1)
    struct.pack_into("<IHIHH", hdr, 0x64, ab_off, len(abs_list), fx_off, 0, len(cast_fx))
    return bytes(hdr) + bytes(ab_bytes) + bytes(fx_bytes)


def parse_spl(data: bytes) -> dict:
    assert data[:8] == b"SPL V1  "
    name1 = struct.unpack_from("<i", data, 0x08)[0]
    desc = struct.unpack_from("<i", data, 0x50)[0]
    school = data[0x25]
    ab_off, ab_cnt, fx_off, cast_idx, cast_cnt = struct.unpack_from("<IHIHH", data, 0x64)

    def _read_fx(start: int, count: int) -> list[dict]:
        out = []
        for i in range(count):
            o = fx_off + (start + i) * 0x30
            op, tgt, pwr, p1, p2, tim, dis, dur, pr1, pr2 = struct.unpack_from("<HBBiiBBIBB", data, o)
            res = data[o + 0x14 : o + 0x1C].split(b"\x00", 1)[0].decode("ascii", "replace")
            spc = struct.unpack_from("<i", data, o + 0x2C)[0]
            out.append({
                "opcode": op,
                "target": tgt,
                "power": pwr,
                "p1": p1,
                "p2": p2,
                "timing": tim,
                "dispel": dis,
                "duration": dur,
                "prob1": pr1,
                "prob2": pr2,
                "resource": res,
                "special": spc,
            })
        return out

    casting_effects = _read_fx(cast_idx, cast_cnt)
    abilities = []
    for ai in range(ab_cnt):
        ao = ab_off + ai * 0x28
        min_lv = struct.unpack_from("<H", data, ao + 0x10)[0]
        fcnt, fidx = struct.unpack_from("<HH", data, ao + 0x1E)
        proj = struct.unpack_from("<H", data, ao + 0x26)[0]
        abilities.append({"min_level": min_lv, "projectile": proj, "effects": _read_fx(fidx, fcnt)})
    return {
        "name1": name1,
        "desc": desc,
        "school": school,
        "casting_effects": casting_effects,
        "abilities": abilities,
    }


def make_cre_v1(kit_ids: int = 0x4000, prof_effects: list[tuple[int, int]] | None = None) -> bytes:
    """Build minimal CRE V1.0 with EFF V2.0 embedded effect list."""
    hdr = bytearray(0x2D4)
    hdr[0x00:0x08] = b"CRE V1.0"
    hdr[0x33] = 1  # fx_version = 1 (EFF V2.0)
    # CRE kit is stored big-endian word-swapped at 0x244/0x246
    struct.pack_into("<HH", hdr, 0x244, (kit_ids >> 16) & 0xFFFF, kit_ids & 0xFFFF)
    fx_list = prof_effects or []
    fx_bytes = bytearray()
    for prof_id, pips in fx_list:
        eff = bytearray(0x108)
        # Embedded CRE V2 effect (0x108B): opcode +0x08, target +0x0c, p1 +0x14, p2 +0x18, timing +0x1c, prob1 +0x24
        struct.pack_into("<IIII", eff, 0x08, 233, 1, 0, pips)
        struct.pack_into("<I", eff, 0x18, prof_id)
        struct.pack_into("<i", eff, 0x1C, 9)
        struct.pack_into("<H", eff, 0x24, 100)
        fx_bytes.extend(eff)
    # Valid IESDP CRE V1.0 section offsets:
    # 0x2a0 known(off,cnt), 0x2a8 meminfo(off,cnt), 0x2b0 mem(off,cnt),
    # 0x2b8 item_slots_off, 0x2bc items(off,cnt), 0x2c4 fx(off,cnt), 0x2cc dialog(8B)
    fx_off = 0x2D4
    slots_off = fx_off + len(fx_bytes)
    struct.pack_into("<II", hdr, 0x2A0, fx_off, 0)
    struct.pack_into("<II", hdr, 0x2A8, fx_off, 0)
    struct.pack_into("<II", hdr, 0x2B0, fx_off, 0)
    struct.pack_into("<I", hdr, 0x2B8, slots_off)
    struct.pack_into("<II", hdr, 0x2BC, fx_off, 0)
    struct.pack_into("<II", hdr, 0x2C4, fx_off, len(fx_list))
    hdr[0x2CC:0x2D4] = b"\x00" * 8
    slots_bytes = b"\xff" * 0x50
    return bytes(hdr) + bytes(fx_bytes) + slots_bytes


def parse_cre_v1(data: bytes) -> dict:
    assert data[:8] == b"CRE V1.0"
    hi, lo = struct.unpack_from("<HH", data, 0x244)
    kit_ids = (hi << 16) | lo
    fx_ver = data[0x33]
    fx_off, fx_cnt = struct.unpack_from("<II", data, 0x2C4)
    profs = {}
    if fx_ver == 1:
        for i in range(fx_cnt):
            o = fx_off + i * 0x108
            op = struct.unpack_from("<I", data, o + 0x08)[0]
            p1 = struct.unpack_from("<i", data, o + 0x14)[0]
            p2 = struct.unpack_from("<I", data, o + 0x18)[0]
            if op == 233:
                profs[p2] = p1
    return {"kit_ids": kit_ids, "fx_ver": fx_ver, "profs": profs}


def check_spl_has_opcodes(spl_path: pathlib.Path, forbidden: set[int]) -> list[int]:
    parsed = parse_spl(spl_path.read_bytes())
    hits = []
    for fx in parsed["casting_effects"]:
        if fx["opcode"] in forbidden:
            hits.append(fx["opcode"])
    for ab in parsed["abilities"]:
        for fx in ab["effects"]:
            if fx["opcode"] in forbidden:
                hits.append(fx["opcode"])
    return hits
