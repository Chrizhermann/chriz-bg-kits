"""Disposable BG2:EE / EET fake game generator for WeiDU install/uninstall tests."""

from __future__ import annotations

import pathlib
import shutil
import struct

from .ie import (
    make_cre_v1,
    make_dialog_tlk,
    make_eff_v1,
    make_eff_v2,
    make_empty_chitin_key,
    make_spl,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MOD_DIR = REPO_ROOT / "chriz-bg-kits"
TP2_FILE = REPO_ROOT / "setup-chriz-bg-kits.tp2"


def _make_key_with_override_probe(resources: dict[str, tuple[int, bytes]], game_dir: pathlib.Path) -> bytes:
    """Build valid KEY V1 + empty BIFFs (or single minimal BIFF if GAME_IS requires BIFF resource lookup)."""
    # Pack a single fake BIFF so WeiDU GAME_IS checks (which inspect KEY resource table) work!
    biff_name = "data/cbktest.bif"
    biff_path = game_dir / biff_name
    biff_path.parent.mkdir(parents=True, exist_ok=True)
    # Build BIFF V1 with files in order
    items = list(resources.items())
    hdr_size = 20
    ent_size = 16
    data_off = hdr_size + len(items) * ent_size
    ent_bytes = bytearray()
    data_blobs = bytearray()
    res_entries = bytearray()
    for idx, (resref_ext, (rtype, payload)) in enumerate(items):
        resname = resref_ext.split(".", 1)[0].upper().encode("ascii")[:8].ljust(8, b"\x00")
        locator = idx  # file_index = idx, biff_index = 0, tile_index = 0
        off = data_off + len(data_blobs)
        ent_bytes.extend(struct.pack("<IIIHH", locator, off, len(payload), rtype, 0))
        data_blobs.extend(payload)
        res_entries.extend(struct.pack("<8sHI", resname, rtype, locator))

    biff_hdr = struct.pack("<8sIII", b"BIFFV1  ", len(items), 0, hdr_size)
    biff_path.write_bytes(biff_hdr + bytes(ent_bytes) + bytes(data_blobs))

    biff_name_b = biff_name.encode("ascii") + b"\x00"
    biff_table_off = 24
    str_off = biff_table_off + 12
    res_table_off = str_off + len(biff_name_b)
    key_hdr = struct.pack("<8sIIII", b"KEY V1  ", 1, len(items), biff_table_off, res_table_off)
    biff_entry = struct.pack("<IIHH", biff_path.stat().st_size, str_off, len(biff_name_b), 1)
    return key_hdr + biff_entry + biff_name_b + bytes(res_entries)


def _table_2da(header_cols: list[str], rows: list[list[str]], default: str = "*") -> str:
    lines = ["2DA V1.0", default, "        " + "   ".join(header_cols)]
    for r in rows:
        lines.append(f"{r[0]:<12}" + "   ".join(str(x) for x in r[1:]))
    return "\n".join(lines) + "\n"


def _make_weapprof(extra_race_col: bool = False) -> str:
    cols = ["FIGHTER", "MAGE", "CLERIC", "BERSERKER", "JESTER", "BLADE", "SKALD", "OHTEMPUS"]
    if extra_race_col:
        cols.append("HOBGOBLIN")
    profs = [
        ("BASTARDSWORD", 89, 2),
        ("LONGSWORD", 90, 2),
        ("SHORTSWORD", 91, 2),
        ("AXE", 92, 2),
        ("TWOHANDEDSWORD", 93, 2),
        ("KATANA", 94, 2),
        ("SCIMITARWAKISASHININJATO", 95, 2),
        ("DAGGER", 96, 2),
        ("WARHAMMER", 97, 2),
        ("CLUB", 115, 2),
        ("SPEAR", 98, 2),
        ("HALBERD", 99, 2),
        ("FLAILMORNINGSTAR", 100, 2),
        ("MACE", 101, 2),
        ("QUARTERSTAFF", 102, 2),
        ("CROSSBOW", 103, 2),
        ("LONGBOW", 104, 2),
        ("SHORTBOW", 105, 2),
        ("DART", 106, 2),
        ("SLING", 107, 2),
        ("TWOHANDED", 111, 2),
        ("SWORDANDSHIELD", 112, 2),
        ("SINGLEWEAPON", 113, 2),
        ("2WEAPON", 114, 3),
    ]
    lines = ["2DA V1.0", "0", "                ID      DESCSTR " + " ".join(cols)]
    for name, pid, base_v in profs:
        vals = []
        for c in cols:
            if c in ("FIGHTER", "BERSERKER"):
                vals.append(str(5 if pid <= 107 or pid == 115 else base_v))
            elif c == "OHTEMPUS":
                vals.append("1" if pid in (97, 100, 101, 102, 107, 111, 112, 113) else "0")
            elif c == "SKALD":
                vals.append("1")
            else:
                vals.append("1")
        lines.append(f"{name:<24} {pid:<4} 1 " + " ".join(vals))
    return "\n".join(lines) + "\n"


def create_fake_game(
    game_dir: pathlib.Path,
    *,
    mode: str = "bg2ee",
    extra_race_col: bool = False,
    pre_mutate: bool = False,
    conflict_mod: str | None = None,
) -> None:
    game_dir.mkdir(parents=True, exist_ok=True)
    ovr = game_dir / "override"
    ovr.mkdir(exist_ok=True)
    (game_dir / "EEex_scripts" / "extra_pattern_dbs").mkdir(parents=True, exist_ok=True)
    (game_dir / "lang" / "en_US").mkdir(parents=True, exist_ok=True)

    # Copy mod into fake game
    dst_mod = game_dir / "chriz-bg-kits"
    if dst_mod.exists():
        shutil.rmtree(dst_mod)
    shutil.copytree(MOD_DIR, dst_mod)
    shutil.copy2(TP2_FILE, game_dir / "setup-chriz-bg-kits.tp2")

    tlk_bytes = make_dialog_tlk(
        ["", "Placeholder", "Mage", "Fighter", "Cleric", "Thief", "Druid", "Ranger",
         "Tempus", "Priest of Tempus", "Berserker", "berserker", "Jester", "jester",
         "Skald", "skald", "Blade", "blade", "Help"]
    )
    (game_dir / "lang" / "en_US" / "dialog.tlk").write_bytes(tlk_bytes)
    (game_dir / "engine.lua").write_text('engine_name = "Baldur\'s Gate II: Enhanced Edition"\n', encoding="utf-8")

    # Sentinel resources in BIFF so GAME_IS ~bg2ee eet~ matches
    biff_res: dict[str, tuple[int, bytes]] = {
        "OH6000.ARE": (0x3F2, b"AREAV1.0"),
    }
    if mode == "eet":
        biff_res["OH1000.ARE"] = (0x3F2, b"AREAV1.0")
        (ovr / "eet.flag").write_bytes(b"EET")
    (game_dir / "chitin.key").write_bytes(_make_key_with_override_probe(biff_res, game_dir))

    (ovr / "M___EEex.lua").write_text("-- EEex stub\n", encoding="utf-8")
    (ovr / "SPLSTATE.IDS").write_text(
        "IDS V1.0\n0 INVALID\n77 BERSERKER_RAGE\n104 STATE_ENRAGED\n112 HELM_GLORY\n",
        encoding="utf-8",
    )
    (ovr / "SPLPROT.2DA").write_text(
        "2DA V1.0\n*\n        STAT    VALUE   RELATION\n"
        "0       0       0       1\n"
        "110     0x112   -1      7\n"
        "111     0x112   -1      8\n",
        encoding="utf-8",
    )
    (ovr / "SPELL.IDS").write_text(
        "IDS V1.0\n1425 CLERIC_BLOOD_RAGE\n1525 CLERIC_ANIMAL_RAGE\n",
        encoding="utf-8",
    )
    (ovr / "KIT.IDS").write_text(
        "IDS V1.0\n0x4000 TRUECLASS\n0x4001 BERSERKER\n0x400D BLADE\n0x400E JESTER\n0x400F SKALD\n0x4029 OHTEMPUS\n",
        encoding="utf-8",
    )
    # Wait: in WEAPPROF header, col indexes align to KITLIST col 6 PROFICIENCY!
    # Look at _make_weapprof cols: ID=0, DESCSTR=1, FIGHTER=2, MAGE=3, CLERIC=4, BERSERKER=5, JESTER=6, BLADE=7, SKALD=8, OHTEMPUS=9
    # So PROFICIENCY in KITLIST.2DA (which equals data_col - 1 = header_col) is: BERSERKER=5, JESTER=6, BLADE=7, SKALD=8, OHTEMPUS=9!
    (ovr / "WEAPPROF.2DA").write_text(_make_weapprof(extra_race_col=extra_race_col), encoding="utf-8")
    # 25STWEAP uses exact same columns (ID..OHTEMPUS)
    (ovr / "25STWEAP.2DA").write_text(_make_weapprof(extra_race_col=extra_race_col), encoding="utf-8")

    (ovr / "KITLIST.2DA").write_text(
        _table_2da(
            ["ROWNAME", "LOWER", "MIXED", "HELP", "ABILITIES", "PROFICIENCY", "UNUSABLE", "CLASS", "KITIDS"],
            [
                ["0", "MAGE", "2", "2", "18", "CLABMA01", "3", "0x00004000", "1", "0x00004000"],
                ["1", "BERSERKER", "11", "10", "18", "CLABFI02", "5", "0x00000001", "2", "0x00004001"],
                ["13", "BLADE", "17", "16", "18", "CLABBA02", "7", "0x00400000", "5", "0x0000400d"],
                ["14", "JESTER", "13", "12", "18", "CLABBA03", "6", "0x00800000", "5", "0x0000400e"],
                ["15", "SKALD", "15", "14", "18", "CLABBA04", "8", "0x01000000", "5", "0x0000400f"],
                ["41", "OHTEMPUS", "8", "9", "18", "OHTEMPUS", "9", "0x00000080", "3", "0x00004029"],
            ],
        ),
        encoding="utf-8",
    )

    rc_cols = ["HUMAN", "ELF", "HALF_ELF", "DWARF", "HALFLING", "GNOME", "HALFORC"]
    rc_base = ["1", "1", "1", "1", "1", "1", "1"]
    rc_bard = ["1", "0", "1", "0", "0", "0", "0"]
    if extra_race_col:
        rc_cols.append("HOBGOBLIN")
        rc_base.append("1")
        rc_bard.append("0")
    (ovr / "CLSRCREQ.2DA").write_text(
        _table_2da(
            rc_cols,
            [
                ["FIGHTER", *rc_base],
                ["BERSERKER", *rc_base],
                ["JESTER", *rc_bard],
                ["SKALD", *rc_bard],
                ["OHTEMPUS", *rc_base],
            ],
            "0",
        ),
        encoding="utf-8",
    )
    (ovr / "CLASTEXT.2DA").write_text(
        _table_2da(
            ["CLASSID", "KITID", "LOWER", "DESCSTR", "MIXED", "BIOGRAPHY", "FALLEN", "BRIEFDESC", "FALLEN_NOTICE"],
            [
                ["FIGHTER", "2", "16384", "3", "18", "3", "-1", "0", "18", "-1"],
                ["BERSERKER", "2", "1", "11", "18", "10", "-1", "0", "18", "-1"],
                ["JESTER", "5", "14", "13", "18", "12", "-1", "0", "18", "-1"],
                ["SKALD", "5", "15", "15", "18", "14", "-1", "0", "18", "-1"],
                ["OHTEMPUS", "3", "41", "8", "18", "9", "-1", "0", "18", "-1"],
            ],
            "-1",
        ),
        encoding="utf-8",
    )

    (ovr / "CLASWEAP.2DA").write_text(
        _table_2da(
            ["SMALL_SWORD", "LARGE_SWORD", "BLUNT", "MISSILE", "BOW", "SPIKED", "AXE", "SPEAR"],
            [["FIGHTER", "1", "1", "1", "1", "1", "1", "1", "1"]],
            "0",
        ),
        encoding="utf-8",
    )
    for tbl, cols, row in [
        ("ABCLASRQ.2DA", ["MIN_STR", "MIN_DEX", "MIN_CON", "MIN_INT", "MIN_WIS", "MIN_CHA"], ["FIGHTER", "9", "0", "0", "0", "0", "0"]),
        ("ABCLSMOD.2DA", ["MOD_STR", "MOD_DEX", "MOD_CON", "MOD_INT", "MOD_WIS", "MOD_CHA"], ["FIGHTER", "0", "0", "0", "0", "0", "0"]),
        ("ABDCDSRQ.2DA", ["MIN_STR", "MIN_DEX", "MIN_CON", "MIN_INT", "MIN_WIS", "MIN_CHA"], ["FIGHTER", "15", "0", "0", "0", "0", "0"]),
        ("ABDCSCRQ.2DA", ["MIN_STR", "MIN_DEX", "MIN_CON", "MIN_INT", "MIN_WIS", "MIN_CHA"], ["FIGHTER", "15", "0", "0", "0", "0", "0"]),
        ("DUALCLAS.2DA", ["FIGHTER", "CLERIC", "MAGE", "THIEF", "DRUID", "RANGER"], ["FIGHTER", "0", "1", "1", "1", "1", "0"]),
        ("ALIGNMNT.2DA", ["L_G", "L_N", "L_E", "N_G", "N_N", "N_E", "C_G", "C_N", "C_E"], ["FIGHTER", "1", "1", "1", "1", "1", "1", "1", "1", "1"]),
    ]:
        (ovr / tbl).write_text(_table_2da(cols, [row], "0"), encoding="utf-8")

    (ovr / "LUABBR.2DA").write_text(
        _table_2da(["ABBREV"], [["FIGHTER", "Fi0"], ["JESTER", "Ba2"], ["SKALD", "Ba2"], ["BLADE", "Ba1"]], "*"),
        encoding="utf-8",
    )
    (ovr / "LUFI0.2DA").write_text(
        _table_2da(
            ["ABILITY", "ICON", "STRREF", "MIN_LEV", "MAX_LEVEL", "NUM_ALLOWED", "PREREQUISITE", "EXCLUDED_BY", "ALIGNMENT_RESTRICT"],
            [["1", "GA_SPCL900", "*", "*", "1", "99", "20", "*", "*", "*"], ["2", "*", "*", "*", "1", "99", "1", "*", "*", "*"]],
        ),
        encoding="utf-8",
    )
    # LUBA2 with TWO SPCL920 rows (like Enhanced Bard Song duplicates) to verify cleanup!
    (ovr / "LUBA2.2DA").write_text(
        _table_2da(
            ["ABILITY", "ICON", "STRREF", "MIN_LEV", "MAX_LEVEL", "NUM_ALLOWED", "PREREQUISITE", "EXCLUDED_BY", "ALIGNMENT_RESTRICT"],
            [
                ["1", "GA_SPCL920", "*", "*", "1", "99", "1", "*", "*", "*"],
                ["2", "AP_SPCL920", "*", "*", "1", "99", "1", "*", "*", "*"],
                ["3", "GA_SPCL916", "*", "*", "1", "99", "16", "*", "*", "*"],
            ],
        ),
        encoding="utf-8",
    )
    kt_hdr = ["HUMAN", "DWARF"]
    kt_f_row = ["FIGHTER", "K_F_H", "K_F_D"]
    kt_c_row = ["CLERIC", "K_C_H", "K_C_D"]
    if extra_race_col:
        kt_hdr.append("HOBGOBLIN")
        kt_f_row.append("K_F_HG")
        kt_c_row.append("K_C_HG")
    (ovr / "KITTABLE.2DA").write_text(_table_2da(kt_hdr, [kt_f_row, kt_c_row]), encoding="utf-8")
    for kf in ("K_F_H.2DA", "K_F_D.2DA", "K_F_HG.2DA"):
        (ovr / kf).write_text(_table_2da(["KIT"], [["1", "1"]]), encoding="utf-8")

    # Tempus + Priest spells + CREs
    (ovr / "CDHLYSYM.SPL").write_bytes(make_spl())
    (ovr / "OHTEMPUS.2DA").write_text(
        "2DA V1.0\n****\n"
        + "            " + " ".join(str(i) for i in range(1, 26)) + "\n"
        + "ABILITY1    GA_OHTMPS1 " + " ".join("AP_CDHLYSYM" if i == 25 else "****" for i in range(2, 26)) + "\n",
        encoding="utf-8",
    )
    (ovr / "OHTMPS1.SPL").write_bytes(make_spl())
    (ovr / "OHTMPS2D.SPL").write_bytes(make_spl(casting_effects=[make_eff_v1(141, target=1, p1=1, timing=1)], abilities=[(1, 162, [])]))
    (ovr / "OHTMPS2E.SPL").write_bytes(make_spl(casting_effects=[make_eff_v1(141, target=1, p1=2, timing=1)], abilities=[(1, 171, [])]))
    (ovr / "SPPR113.SPL").write_bytes(make_spl(spell_type=2, school=3))  # Divination -> must be stripped
    (ovr / "SPPR415.SPL").write_bytes(make_spl(spell_type=2, school=3))  # Divination -> must be stripped
    (ovr / "SPPR201.SPL").write_bytes(make_spl(spell_type=2, school=1))  # Non-divination -> untouched
    for sp in ("SPPR412", "SPPR425", "SPPR507", "SPPR513", "SPPR525", "SPWI603", "SPCL751A", "SPCL121"):
        (ovr / f"{sp}.SPL").write_bytes(make_spl())

    # Core fixes spells
    (ovr / "SPCL907.SPL").write_bytes(
        make_spl(abilities=[(1, 1, [
            make_eff_v1(27, target=1, p1=40, timing=0, duration=60),
            make_eff_v1(84, target=1, p1=40, timing=0, duration=60),
            make_eff_v1(86, target=1, p1=40, timing=0, duration=60),
            make_eff_v1(87, target=1, p1=40, timing=0, duration=60),
            make_eff_v1(88, target=1, p1=40, timing=0, duration=60),
            make_eff_v1(89, target=1, p1=40, timing=0, duration=60),
        ])])
    )
    (ovr / "SPWISH12.SPL").write_bytes(
        make_spl(abilities=[(1, 1, [
            make_eff_v1(28, target=1, p1=40, timing=0, duration=60),
            make_eff_v1(86, target=1, p1=40, timing=0, duration=60),
        ])])
    )
    (ovr / "SPCL904.SPL").write_bytes(make_spl(abilities=[(1, 1, [make_eff_v1(166, target=1, p1=50, p2=1, timing=0, duration=24)])]))
    (ovr / "SPCL902.SPL").write_bytes(make_spl(abilities=[(1, 1, [make_eff_v1(248, target=1, timing=0, duration=12, resource="SPCL902", special=8)])]))
    (ovr / "SPCL902.EFF").write_bytes(make_eff_v2(opcode=13, target=2, timing=1, min_level=8))
    (ovr / "SPCL903.SPL").write_bytes(make_spl(abilities=[(1, 1, [make_eff_v1(248, target=1, timing=0, duration=12, resource="SPCL903", special=12)])]))
    (ovr / "SPCL903.EFF").write_bytes(make_eff_v2(opcode=13, target=2, timing=1, min_level=12))

    # CREs
    if pre_mutate:
        # We Overwrite test: weird pre-modified OHTMPS1, weird BRANWE kit/axe pip, weird ARCHSLOW.EFF, weird OHTEMPUS.2DA
        (ovr / "OHTMPS1.SPL").write_bytes(make_spl(abilities=[(1, 1, [make_eff_v1(99, p1=999)])]))
        (ovr / "BRANWE.CRE").write_bytes(make_cre_v1(kit_ids=0x4005, prof_effects=[(92, 0), (101, 1)]))
        (ovr / "BRANWE5.CRE").write_bytes(make_cre_v1(kit_ids=0x4000, prof_effects=[(101, 2)]))
        (ovr / "ARCHSLOW.EFF").write_bytes(make_eff_v2(opcode=20, target=2, p1=999))
    else:
        (ovr / "BRANWE.CRE").write_bytes(make_cre_v1(kit_ids=0x4000, prof_effects=[(101, 1)]))
        (ovr / "BRANWE5.CRE").write_bytes(make_cre_v1(kit_ids=0x4000, prof_effects=[(101, 1)]))
    (ovr / "KORGAN8.CRE").write_bytes(make_cre_v1(kit_ids=0x4001, prof_effects=[(92, 5)]))

    # Mutual exclusivity probe (ArtisansKitpack / BardicWonders in weidu.log)
    if conflict_mod == "artisan":
        (game_dir / "weidu.log").write_text("~ARTISANSKITPACK/ARTISANSKITPACK.TP2~ #0 #0 // Artisans Kitpack\n", encoding="utf-8")
    elif conflict_mod == "bardic":
        (game_dir / "weidu.log").write_text("~BARDICWONDERS/BARDICWONDERS.TP2~ #0 #0 // Bardic Wonders\n", encoding="utf-8")
