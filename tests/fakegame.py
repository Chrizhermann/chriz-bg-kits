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
    make_fire_bam,
    make_itm_v1,
    make_spl,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MOD_DIR = REPO_ROOT / "chriz-bg-kits"
TP2_FILE = REPO_ROOT / "setup-chriz-bg-kits.tp2"


def _make_key_with_override_probe(resources: dict[str, tuple[int, bytes]], game_dir: pathlib.Path) -> bytes:
    biff_name = "data/cbktest.bif"
    biff_path = game_dir / biff_name
    biff_path.parent.mkdir(parents=True, exist_ok=True)
    items = list(resources.items())
    hdr_size = 20
    ent_size = 16
    data_off = hdr_size + len(items) * ent_size
    ent_bytes = bytearray()
    data_blobs = bytearray()
    res_entries = bytearray()
    for idx, (resref_ext, (rtype, payload)) in enumerate(items):
        resname = resref_ext.split(".", 1)[0].upper().encode("ascii")[:8].ljust(8, b"\x00")
        locator = idx
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
        lines.append(f"{r[0]:<20}" + "   ".join(str(x) for x in r[1:]))
    return "\n".join(lines) + "\n"


def _make_weapprof(extra_race_col: bool = False) -> str:
    cols = [
        "FIGHTER", "MAGE", "CLERIC", "THIEF", "BARD", "PALADIN", "DRUID", "RANGER", "SORCERER",
        "BERSERKER", "JESTER", "BLADE", "SKALD", "OHTEMPUS", "TOTEMIC_DRUID", "DRAGON_DISCIPLE",
        "TALOS", "HELM", "LATHANDER", "OHTYR",
    ]
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
        *[(f"EXTRA{i}", 114 + i, 0) for i in range(2, 21)],
    ]
    lines = ["2DA V1.0", "0", "                ID      DESCSTR " + " ".join(cols)]
    for name, pid, base_v in profs:
        vals = []
        for c in cols:
            if pid >= 116:
                vals.append("0")
            elif c in ("FIGHTER", "BERSERKER"):
                vals.append(str(5 if pid <= 107 or pid == 115 else base_v))
            elif c in ("CLERIC", "OHTEMPUS", "TALOS", "HELM", "LATHANDER", "OHTYR"):
                vals.append("1" if pid in (97, 100, 101, 102, 107, 111, 112, 113, 114, 115) else "0")
            elif c in ("SORCERER", "DRAGON_DISCIPLE", "MAGE"):
                vals.append("1" if pid in (96, 102, 106, 107) else "0")
            elif c in ("DRUID", "TOTEMIC_DRUID"):
                vals.append("1" if pid in (95, 96, 98, 102, 106, 107, 111, 112, 113, 115) else "0")
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
    with_fire_bams: bool = True,
    with_druid_icelance: bool = False,
    with_yeslick_alaghor: bool = False,
) -> None:
    game_dir.mkdir(parents=True, exist_ok=True)
    ovr = game_dir / "override"
    ovr.mkdir(exist_ok=True)
    (game_dir / "EEex_scripts" / "extra_pattern_dbs").mkdir(parents=True, exist_ok=True)
    (game_dir / "lang" / "en_US").mkdir(parents=True, exist_ok=True)

    dst_mod = game_dir / "chriz-bg-kits"
    if dst_mod.exists():
        shutil.rmtree(dst_mod)
    shutil.copytree(MOD_DIR, dst_mod)
    shutil.copy2(TP2_FILE, game_dir / "setup-chriz-bg-kits.tp2")

    tlk_bytes = make_dialog_tlk([
        "", "Placeholder", "Mage", "Fighter", "Cleric", "Thief", "Druid", "Ranger",
        "Tempus", "Priest of Tempus", "Berserker", "berserker", "Jester", "jester",
        "Skald", "skald", "Blade", "blade", "Help",
        "Human race description.", "Elf race description.", "Half-Elf race description.",
        "Dwarf race description.", "Halfling race description.", "Gnome race description.",
        "Half-Orc race description.",
    ])
    (game_dir / "lang" / "en_US" / "dialog.tlk").write_bytes(tlk_bytes)
    (game_dir / "engine.lua").write_text('engine_name = "Baldur\'s Gate II: Enhanced Edition"\n', encoding="utf-8")

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
        "15      0x10c   2       1\n"
        "19      0x10c   3       1\n"
        "110     0x112   -1      7\n"
        "111     0x112   -1      8\n",
        encoding="utf-8",
    )
    spell_ids = (
        "IDS V1.0\n"
        "1103 CLERIC_CURE_LIGHT_WOUNDS\n"
        "1315 CLERIC_CURE_MEDIUM_WOUNDS\n"
        "1401 CLERIC_CURE_SERIOUS_WOUNDS\n"
        "1502 CLERIC_CURE_CRITICAL_WOUNDS\n"
        "1514 CLERIC_MASS_CURE\n"
        "1425 CLERIC_BLOOD_RAGE\n"
        "1525 CLERIC_ANIMAL_RAGE\n"
        "2103 WIZARD_BURNING_HANDS\n"
        "2304 WIZARD_FIREBALL\n"
        "2810 WIZARD_INCENDIARY_CLOUD\n"
    )
    if with_druid_icelance:
        spell_ids += "1327 CLERIC_CBMAGIC_ICELANCE\n"
    (ovr / "SPELL.IDS").write_text(spell_ids, encoding="utf-8")

    (ovr / "PROJECTL.IDS").write_text(
        "IDS V1.0\n37 FIREBALL\n95 ICESTORM\n157 INAREAPA\n158 INAREANP\n254 CONECOLD\n",
        encoding="utf-8",
    )
    race_ids = (
        "IDS V1.0\n1 HUMAN\n2 ELF\n3 HALF_ELF\n4 DWARF\n5 HALFLING\n6 GNOME\n7 HALFORC\n145 ELEMENTAL\n"
    )
    if extra_race_col:
        race_ids += "161 HOBGOBLIN\n"
    (ovr / "RACE.IDS").write_text(race_ids, encoding="utf-8")

    (ovr / "ANIMATE.IDS").write_text(
        "IDS V1.0\n"
        "0x6000 CLERIC_MALE_HUMAN\n"
        "0x7300 ELEMENTAL_EARTH\n"
        "0x7301 ELEMENTAL_EARTH_SMALL\n"
        "0x7310 ELEMENTAL_FIRE\n"
        "0x7311 ELEMENTAL_FIRE_SMALL\n"
        "0x7320 ELEMENTAL_AIR\n"
        "0x7321 ELEMENTAL_AIR_SMALL\n"
        "0xEF10 WATER_WEIRD\n",
        encoding="utf-8",
    )
    for c_id, c_race in [
        ("6001", "cleric_male_elf"), ("6002", "cleric_male_dwarf"), ("6003", "cleric_male_halfling"),
        ("6004", "cleric_male_gnome"), ("6005", "cleric_male_halforc"),
        ("6011", "cleric_female_elf"), ("6012", "cleric_female_dwarf"), ("6013", "cleric_female_halfling"),
        ("6014", "cleric_female_gnome"), ("6015", "cleric_female_halforc"),
    ]:
        (ovr / f"{c_id}.INI").write_text(f"// CIMC {c_race}\n[general]\npersonal_space=3\n", encoding="utf-8")

    for e_id, e_rr, pspace in [
        ("7300", "MEAE", 5), ("7301", "MEAS", 3),
        ("7310", "MFIE", 3), ("7311", "MFIS", 3),
        ("7320", "MAIR", 5), ("7321", "MAIS", 3),
        ("EF10", "MWWE", 3),
    ]:
        (ovr / f"{e_id}.INI").write_text(
            f"// {e_rr}\n[general]\npersonal_space={pspace}\ncolor_blood=50\nlight_source=1\n[monster]\nresref={e_rr}\n",
            encoding="utf-8",
        )

    if with_fire_bams:
        (ovr / "MFISG1.BAM").write_bytes(make_fire_bam(compressed=True))
        (ovr / "MFIEG1.BAM").write_bytes(make_fire_bam(compressed=False))

    kit_ids_txt = (
        "IDS V1.0\n"
        "0x4000 TRUECLASS\n"
        "0x4001 BERSERKER\n"
        "0x4004 CAVALIER\n"
        "0x4005 INQUISITOR\n"
        "0x4006 UNDEAD_HUNTER\n"
        "0x4007 FERALAN\n"
        "0x4008 STALKER\n"
        "0x4009 BEASTMASTER\n"
        "0x400A ASSASIN\n"
        "0x400B BOUNTY_HUNTER\n"
        "0x400C SWASHBUCKLER\n"
        "0x400D BLADE\n"
        "0x400E JESTER\n"
        "0x400F SKALD\n"
        "0x4010 TOTEMIC_DRUID\n"
        "0x4011 SHAPESHIFTER\n"
        "0x4012 BEAST_FRIEND\n"
        "0x4013 TALOS\n"
        "0x4014 HELM\n"
        "0x4015 LATHANDER\n"
        "0x0040 ABJURER\n"
        "0x0080 CONJURER\n"
        "0x0100 DIVINER\n"
        "0x0200 ENCHANTER\n"
        "0x0400 ILLUSIONIST\n"
        "0x0800 INVOKER\n"
        "0x1000 NECROMANCER\n"
        "0x2000 TRANSMUTER\n"
        "0x80000000 WILDMAGE\n"
        "0x40000000 BARBARIAN\n"
        "0x4020 Blackguard\n"
        "0x4021 SHADOWDANCER\n"
        "0x4022 DWARVEN_DEFENDER\n"
        "0x4023 DRAGON_DISCIPLE\n"
        "0x4024 DARK_MOON\n"
        "0x4025 SUN_SOUL\n"
        "0x4028 OHTYR\n"
        "0x4029 OHTEMPUS\n"
    )
    if with_yeslick_alaghor:
        kit_ids_txt += "0x402A LK_ALAGHOR\n"
    (ovr / "KIT.IDS").write_text(kit_ids_txt, encoding="utf-8")

    (ovr / "WEAPPROF.2DA").write_text(_make_weapprof(extra_race_col=extra_race_col), encoding="utf-8")
    (ovr / "25STWEAP.2DA").write_text(_make_weapprof(extra_race_col=extra_race_col), encoding="utf-8")

    # WEAPPROF header indices (col_idx + 2 = PROFICIENCY number):
    # FIGHTER=2, MAGE=3, CLERIC=4, THIEF=5, BARD=6, PALADIN=7, DRUID=8, RANGER=9, SORCERER=10,
    # BERSERKER=11, JESTER=12, BLADE=13, SKALD=14, OHTEMPUS=15, TOTEMIC_DRUID=16, DRAGON_DISCIPLE=17,
    # TALOS=18, HELM=19, LATHANDER=20, OHTYR=21
    kitlist_rows = [
        ["0",  "RESERVE", "*", "*", "*", "*", "*", "*", "*", "*"],
        ["1",  "BERSERKER", "11", "10", "18", "CLABFI02", "11", "0x00000001", "2",  "0x00004001"],
        ["4",  "CAVALIER", "3", "3", "18", "CLABPA02", "7", "0x00000008", "6",  "0x00004004"],
        ["5",  "INQUISITOR", "3", "3", "18", "CLABPA03", "7", "0x00000010", "6",  "0x00004005"],
        ["6",  "UNDEAD_HUNTER", "3", "3", "18", "CLABPA04", "7", "0x00000020", "6",  "0x00004006"],
        ["7",  "FERALAN", "7", "7", "18", "CLABRN02", "9", "0x00008000", "12", "0x00004007"],
        ["8",  "STALKER", "7", "7", "18", "CLABRN03", "9", "0x00010000", "12", "0x00004008"],
        ["9",  "BEASTMASTER", "7", "7", "18", "CLABRN04", "9", "0x00020000", "12", "0x00004009"],
        ["10", "ASSASIN", "5", "5", "18", "CLABTH02", "5", "0x00040000", "4",  "0x0000400a"],
        ["11", "BOUNTY_HUNTER", "5", "5", "18", "CLABTH03", "5", "0x00080000", "4",  "0x0000400b"],
        ["12", "SWASHBUCKLER", "5", "5", "18", "CLABTH04", "5", "0x00100000", "4",  "0x0000400c"],
        ["13", "BLADE", "17", "16", "18", "CLABBA02", "13", "0x00200000", "5",  "0x0000400d"],
        ["14", "JESTER", "13", "12", "18", "CLABBA03", "12", "0x00400000", "5",  "0x0000400e"],
        ["15", "SKALD", "15", "14", "18", "CLABBA04", "14", "0x00800000", "5",  "0x0000400f"],
        ["16", "TOTEMIC_DRUID", "6", "6", "18", "CLABDR02", "16", "0x08000000", "11", "0x00004010"],
        ["17", "SHAPESHIFTER", "6", "6", "18", "CLABDR03", "16", "0x10000000", "11", "0x00004011"],
        ["18", "BEAST_FRIEND", "6", "6", "18", "CLABDR04", "16", "0x20000000", "11", "0x00004012"],
        ["19", "TALOS", "4", "4", "18", "CLABPR02", "18", "0x01000000", "3",  "0x00004013"],
        ["20", "HELM", "4", "4", "18", "CLABPR03", "19", "0x02000000", "3",  "0x00004014"],
        ["21", "LATHANDER", "4", "4", "18", "CLABPR04", "20", "0x04000000", "3",  "0x00004015"],
        ["22", "ABJURER", "2", "2", "18", "CLABMA02", "3", "0x00000040", "1",  "0x00000040"],
        ["23", "CONJURER", "2", "2", "18", "CLABMA06", "3", "0x00000080", "1",  "0x00000080"],
        ["24", "DIVINER", "2", "2", "18", "CLABMA05", "3", "0x00000100", "1",  "0x00000100"],
        ["25", "ENCHANTER", "2", "2", "18", "CLABMA09", "3", "0x00000200", "1",  "0x00000200"],
        ["26", "ILLUSIONIST", "2", "2", "18", "CLABMA08", "3", "0x00000400", "1",  "0x00000400"],
        ["27", "INVOKER", "2", "2", "18", "CLABMA07", "3", "0x00000800", "1",  "0x00000800"],
        ["28", "NECROMANCER", "2", "2", "18", "CLABMA03", "3", "0x00001000", "1",  "0x00001000"],
        ["29", "TRANSMUTER", "2", "2", "18", "CLABMA04", "3", "0x00002000", "1",  "0x00002000"],
        ["30", "WILDMAGE", "2", "2", "18", "CLABMA01", "3", "0x80000000", "1",  "0x80000000"],
        ["31", "BARBARIAN", "3", "3", "18", "CLABFI05", "2", "0x40000000", "2",  "0x40000000"],
        ["32", "Blackguard", "3", "3", "18", "CLABPA06", "7", "0x00000021", "6",  "0x00004020"],
        ["33", "SHADOWDANCER", "5", "5", "18", "CLABTH05", "5", "0x00004000", "4",  "0x00004021"],
        ["34", "DWARVEN_DEFENDER", "3", "3", "18", "CLABFI06", "2", "0x00004000", "2",  "0x00004022"],
        ["35", "DRAGON_DISCIPLE", "2", "2", "18", "CLABSO01", "17", "0x00004000", "19", "0x00004023"],
        ["36", "DARK_MOON", "3", "3", "18", "CLABMO02", "2", "0x00004000", "20", "0x00004024"],
        ["37", "SUN_SOUL", "3", "3", "18", "CLABMO03", "2", "0x00004000", "20", "0x00004025"],
        ["38", "LATHANDER_X", "4", "4", "18", "CLABPR04", "4", "0x04000000", "3",  "0x00004015"],
        ["39", "GRIZZLY_BEAR", "3", "3", "18", "CLABBEAR", "2", "0xFFFFFFFF", "2",  "0x00004027"],
        ["40", "OHTYR", "4", "4", "18", "OHTYR", "21", "0x00004000", "3",  "0x00004028"],
        ["41", "OHTEMPUS", "8", "9", "18", "OHTEMPUS", "15", "0x00000080", "3",  "0x00004029"],
    ]
    if with_yeslick_alaghor:
        kitlist_rows.append(["42", "LK_ALAGHOR", "4", "4", "18", "LK#YESK", "4", "0x00004000", "3", "0x0000402a"])
    (ovr / "KITLIST.2DA").write_text(
        _table_2da(
            ["ROWNAME", "LOWER", "MIXED", "HELP", "ABILITIES", "PROFICIENCY", "UNUSABLE", "CLASS", "KITIDS"],
            kitlist_rows,
        ),
        encoding="utf-8",
    )

    rc_cols = ["HUMAN", "ELF", "HALF_ELF", "DWARF", "HALFLING", "GNOME", "HALFORC"]
    def _rc(vals: list[str], hb: str = "0") -> list[str]:
        return [*vals, hb] if extra_race_col else vals
    if extra_race_col:
        rc_cols.append("HOBGOBLIN")

    (ovr / "CLSRCREQ.2DA").write_text(
        _table_2da(
            rc_cols,
            [
                ["MAGE",                *_rc(["1", "1", "1", "0", "0", "1", "0"], "0")],
                ["FIGHTER",             *_rc(["1", "1", "1", "1", "1", "1", "1"], "1")],
                ["CLERIC",              *_rc(["1", "1", "1", "1", "1", "1", "1"], "1")],
                ["THIEF",               *_rc(["1", "1", "1", "1", "1", "1", "1"], "1")],
                ["BARD",                *_rc(["1", "0", "1", "0", "0", "0", "0"], "0")],
                ["PALADIN",             *_rc(["1", "0", "0", "0", "0", "0", "0"], "0")],
                ["FIGHTER_MAGE",        *_rc(["0", "1", "1", "0", "0", "1", "0"], "0")],
                ["FIGHTER_CLERIC",      *_rc(["0", "0", "1", "1", "0", "1", "1"], "0")],
                ["FIGHTER_THIEF",       *_rc(["0", "1", "1", "1", "1", "1", "1"], "1")],
                ["FIGHTER_MAGE_THIEF",  *_rc(["0", "1", "1", "0", "0", "0", "0"], "0")],
                ["DRUID",               *_rc(["1", "0", "1", "0", "0", "0", "0"], "0")],
                ["RANGER",              *_rc(["1", "1", "1", "0", "0", "0", "0"], "0")],
                ["MAGE_THIEF",          *_rc(["0", "1", "1", "0", "0", "1", "0"], "0")],
                ["CLERIC_MAGE",         *_rc(["0", "0", "1", "0", "0", "1", "0"], "0")],
                ["CLERIC_THIEF",        *_rc(["0", "0", "0", "0", "0", "1", "1"], "0")],
                ["FIGHTER_DRUID",       *_rc(["0", "0", "1", "0", "0", "0", "0"], "0")],
                ["FIGHTER_MAGE_CLERIC", *_rc(["0", "0", "1", "0", "0", "0", "0"], "0")],
                ["CLERIC_RANGER",       *_rc(["0", "0", "1", "0", "0", "0", "0"], "0")],
                ["SORCERER",            *_rc(["1", "1", "1", "0", "0", "0", "0"], "0")],
                ["MONK",                *_rc(["1", "0", "0", "0", "0", "0", "0"], "0")],
                ["SHAMAN",              *_rc(["1", "0", "1", "0", "0", "0", "1"], "1")],
                ["DUALCLASS",           *_rc(["1", "0", "0", "0", "0", "0", "0"], "0")],
                ["BERSERKER",           *_rc(["1", "1", "1", "1", "1", "1", "1"], "1")],
                ["JESTER",              *_rc(["1", "0", "1", "0", "0", "0", "0"], "0")],
                ["SKALD",               *_rc(["1", "0", "1", "0", "0", "0", "0"], "0")],
                ["TALOS",               *_rc(["1", "1", "1", "1", "1", "1", "1"], "1")],
                ["HELM",                *_rc(["1", "1", "1", "1", "1", "1", "1"], "1")],
                ["LATHANDER",           *_rc(["1", "1", "1", "1", "1", "1", "1"], "1")],
                ["OHTYR",               *_rc(["1", "1", "1", "1", "1", "1", "1"], "1")],
                ["OHTEMPUS",            *_rc(["1", "1", "1", "1", "1", "1", "1"], "1")],
                ["TOTEMIC_DRUID",       *_rc(["1", "0", "1", "0", "0", "0", "0"], "0")],
                ["DRAGON_DISCIPLE",     *_rc(["1", "1", "1", "0", "0", "0", "0"], "0")],
            ],
            "0",
        ),
        encoding="utf-8",
    )

    # MGSRCREQ.2DA has 2 leading cols (kithex + school_name) and header "CLASS HUMAN ELF ..."
    mg_lines = [
        "2DA V1.0",
        "0",
        "            CLASS   " + "   ".join(rc_cols),
        "0x00004000  MAGE        " + "   ".join(_rc(["1", "1", "1", "0", "0", "0", "0"], "0")),
        "0x00000040  ABJURER     " + "   ".join(_rc(["1", "0", "0", "0", "0", "0", "0"], "0")),
        "0x00000080  CONJURER    " + "   ".join(_rc(["1", "0", "1", "0", "0", "0", "0"], "0")),
        "0x00000100  DIVINER     " + "   ".join(_rc(["1", "1", "1", "0", "0", "0", "0"], "0")),
        "0x00000200  ENCHANTER   " + "   ".join(_rc(["1", "1", "1", "0", "0", "0", "0"], "0")),
        "0x00000400  ILLUSIONIST " + "   ".join(_rc(["1", "0", "0", "0", "0", "1", "0"], "0")),
        "0x00000800  INVOKER     " + "   ".join(_rc(["1", "0", "0", "0", "0", "0", "0"], "0")),
        "0x00001000  NECROMANCER " + "   ".join(_rc(["1", "0", "0", "0", "0", "0", "0"], "0")),
        "0x00002000  TRANSMUTER  " + "   ".join(_rc(["1", "0", "1", "0", "0", "0", "0"], "0")),
        "0x80000000  WILDMAGE    " + "   ".join(_rc(["1", "1", "1", "0", "0", "0", "0"], "0")),
    ]
    (ovr / "MGSRCREQ.2DA").write_text("\n".join(mg_lines) + "\n", encoding="utf-8")

    (ovr / "ABRACEAD.2DA").write_text(
        _table_2da(
            ["MOD_STR", "MOD_DEX", "MOD_CON", "MOD_INT", "MOD_WIS", "MOD_CHR"],
            [
                ["HUMAN",    "0", "0", "0", "0", "0", "0"],
                ["DWARF",    "0", "0", "1", "0", "0", "-4" if pre_mutate else "-2"],
                ["ELF",      "0", "1", "-1", "0", "0", "0"],
                ["GNOME",    "0", "0", "0", "1", "-1", "0"],
                ["HALF_ELF", "0", "0", "0", "0", "0", "0"],
                ["HALFLING", "-1", "1", "0", "0", "0", "0"],
                ["HALFORC",  "1", "0", "1", "-2", "0", "-2"],
            ],
            "0",
        ),
        encoding="utf-8",
    )
    (ovr / "ABRACERQ.2DA").write_text(
        _table_2da(
            ["MIN_STR", "MAX_STR", "MIN_DEX", "MAX_DEX", "MIN_CON", "MAX_CON", "MIN_INT", "MAX_INT", "MIN_WIS", "MAX_WIS", "MIN_CHR", "MAX_CHR"],
            [
                ["HUMAN",   "3", "18", "3", "18", "3", "18", "3", "18", "3", "18", "3", "18"],
                ["DWARF",   "8", "18", "3", "17", "12", "18", "3", "18", "3", "18", "3", "17"],
                ["HALFORC", "3", "18", "3", "18", "3", "18", "3", "16", "3", "18", "3", "16"],
            ],
            "0",
        ),
        encoding="utf-8",
    )
    (ovr / "RACETHAC.2DA").write_text(
        _table_2da(
            rc_cols,
            [
                ["90",  *_rc(["0", "1", "0", "0", "0", "0", "0"], "0")],
                ["91",  *_rc(["0", "1", "0", "0", "-2" if pre_mutate else "0", "0", "0"], "0")],
                ["96",  *_rc(["0", "0", "0", "0", "0", "0", "0"], "0")],
                ["106", *_rc(["0", "0", "0", "0", "0", "0", "0"], "0")],
                ["107", *_rc(["0", "0", "0", "0", "1", "0", "0"], "0")],
            ],
            "0",
        ),
        encoding="utf-8",
    )
    racetext_str = _table_2da(
        ["ID", "NAME", "DESCSTR", "UPPERCASE", "BIOGRAPHY"],
        [
            ["HUMAN",    "1", "2", "19", "2", "-1"],
            ["ELF",      "2", "2", "20", "2", "-1"],
            ["HALF_ELF", "3", "2", "21", "2", "-1"],
            ["DWARF",    "4", "2", "22", "2", "-1"],
            ["HALFLING", "5", "2", "23", "2", "-1"],
            ["GNOME",    "6", "2", "24", "2", "-1"],
            ["HALF_ORC", "7", "2", "25", "2", "-1"],
        ],
        "-1",
    )
    (ovr / "RACETEXT.2DA").write_text(racetext_str, encoding="utf-8")
    if mode == "eet":
        (ovr / "BGRACTXT.2DA").write_text(racetext_str, encoding="utf-8")

    (ovr / "MXSPLSRC.2DA").write_text(
        _table_2da(
            ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
            [
                ["1",  "3", "0", "0", "0", "0", "0", "0", "0", "0"],
                ["4",  "6", "3", "0", "0", "0", "0", "0", "0", "0"],
                ["6",  "6", "5", "3", "0", "0", "0", "0", "0", "0"],
                ["8",  "6", "6", "5", "3", "0", "0", "0", "0", "0"],
                ["10", "6", "6", "6", "5", "3", "0", "0", "0", "0"],
                ["12", "6", "6", "6", "6", "5", "3", "0", "0", "0"],
                ["14", "6", "6", "6", "6", "6", "5", "3", "0", "0"],
                ["16", "6", "6", "6", "6", "6", "6", "5", "3", "0"],
                ["18", "6", "6", "6", "6", "6", "6", "6", "5", "3"],
            ],
            "0",
        ),
        encoding="utf-8",
    )
    (ovr / "HPCLASS.2DA").write_text(
        _table_2da(["TABLE"], [["FIGHTER", "HPWAR"], ["SORCERER", "HPWIZ"], ["DRAGON_DISCIPLE", "HPDD"], ["DRUID", "HPPRS"]], "*"),
        encoding="utf-8",
    )

    (ovr / "CLASTEXT.2DA").write_text(
        _table_2da(
            ["CLASSID", "KITID", "LOWER", "DESCSTR", "MIXED", "BIOGRAPHY", "FALLEN", "BRIEFDESC", "FALLEN_NOTICE"],
            [
                ["FIGHTER", "2", "16384", "3", "18", "3", "-1", "0", "18", "-1"],
                ["CLERIC", "3", "16384", "4", "18", "4", "-1", "0", "18", "-1"],
                ["BERSERKER", "2", "1", "11", "18", "10", "-1", "0", "18", "-1"],
                ["BARBARIAN", "2", "1073741824", "3", "18", "3", "-1", "0", "18", "-1"],
                ["JESTER", "5", "14", "13", "18", "12", "-1", "0", "18", "-1"],
                ["SKALD", "5", "15", "15", "18", "14", "-1", "0", "18", "-1"],
                ["TALOS", "3", "19", "4", "18", "4", "-1", "0", "18", "-1"],
                ["HELM", "3", "20", "4", "18", "4", "-1", "0", "18", "-1"],
                ["LATHANDER", "3", "21", "4", "18", "4", "-1", "0", "18", "-1"],
                ["LATHANDER_X", "3", "38", "4", "18", "4", "-1", "0", "18", "-1"],
                ["OHTYR", "3", "40", "4", "18", "4", "-1", "0", "18", "-1"],
                ["OHTEMPUS", "3", "41", "8", "18", "9", "-1", "0", "18", "-1"],
                ["SORCERER", "19", "16384", "2", "18", "2", "-1", "0", "18", "-1"],
                ["DRAGON_DISCIPLE", "19", "35", "2", "18", "2", "-1", "0", "18", "-1"],
                ["DRUID", "11", "16384", "6", "18", "6", "-1", "0", "18", "-1"],
                ["TOTEMIC_DRUID", "11", "16", "6", "18", "6", "-1", "0", "18", "-1"],
            ],
            "-1",
        ),
        encoding="utf-8",
    )

    (ovr / "CLASWEAP.2DA").write_text(
        _table_2da(
            ["SMALL_SWORD", "LARGE_SWORD", "BLUNT", "MISSILE", "BOW", "SPIKED", "AXE", "SPEAR"],
            [
                ["FIGHTER", "1", "1", "1", "1", "1", "1", "1", "1"],
                ["SORCERER", "1", "0", "1", "1", "0", "0", "0", "0"],
                ["DRUID", "1", "0", "1", "1", "0", "0", "0", "1"],
            ],
            "0",
        ),
        encoding="utf-8",
    )
    for tbl, cols, rows in [
        ("ABCLASRQ.2DA", ["MIN_STR", "MIN_DEX", "MIN_CON", "MIN_INT", "MIN_WIS", "MIN_CHA"], [
            ["FIGHTER", "9", "0", "0", "0", "0", "0"],
            ["SORCERER", "0", "0", "0", "9", "0", "9"],
            ["DRUID", "0", "0", "0", "0", "12", "15"],
        ]),
        ("ABCLSMOD.2DA", ["MOD_STR", "MOD_DEX", "MOD_CON", "MOD_INT", "MOD_WIS", "MOD_CHA"], [
            ["FIGHTER", "0", "0", "0", "0", "0", "0"],
            ["SORCERER", "0", "0", "0", "0", "0", "0"],
            ["DRUID", "0", "0", "0", "0", "0", "0"],
        ]),
        ("ABDCDSRQ.2DA", ["MIN_STR", "MIN_DEX", "MIN_CON", "MIN_INT", "MIN_WIS", "MIN_CHA"], [
            ["FIGHTER", "15", "0", "0", "0", "0", "0"],
            ["DRUID", "0", "0", "0", "0", "17", "17"],
        ]),
        ("ABDCSCRQ.2DA", ["MIN_STR", "MIN_DEX", "MIN_CON", "MIN_INT", "MIN_WIS", "MIN_CHA"], [
            ["FIGHTER", "15", "0", "0", "0", "0", "0"],
            ["DRUID", "0", "0", "0", "0", "15", "15"],
        ]),
        ("DUALCLAS.2DA", ["FIGHTER", "CLERIC", "MAGE", "THIEF", "DRUID", "RANGER"], [
            ["FIGHTER", "0", "1", "1", "1", "1", "0"],
            ["BERSERKER", "0", "1", "1", "1", "1", "0"],
            ["DRUID", "1", "0", "0", "0", "0", "0"],
        ]),
        ("ALIGNMNT.2DA", ["L_G", "L_N", "L_E", "N_G", "N_N", "N_E", "C_G", "C_N", "C_E"], [
            ["FIGHTER", "1", "1", "1", "1", "1", "1", "1", "1", "1"],
            ["SORCERER", "1", "1", "1", "1", "1", "1", "1", "1", "1"],
            ["DRUID", "0", "0", "0", "0", "1", "0", "0", "0", "0"],
        ]),
    ]:
        (ovr / tbl).write_text(_table_2da(cols, rows, "0"), encoding="utf-8")

    (ovr / "LUABBR.2DA").write_text(
        _table_2da(
            ["ABBREV"],
            [["FIGHTER", "Fi0"], ["JESTER", "Ba2"], ["SKALD", "Ba2"], ["BLADE", "Ba1"], ["SORCERER", "Ma0"], ["DRUID", "Dr0"]],
            "*",
        ),
        encoding="utf-8",
    )
    (ovr / "LUFI0.2DA").write_text(
        _table_2da(
            ["ABILITY", "ICON", "STRREF", "MIN_LEV", "MAX_LEVEL", "NUM_ALLOWED", "PREREQUISITE", "EXCLUDED_BY", "ALIGNMENT_RESTRICT"],
            [["1", "GA_SPCL900", "*", "*", "1", "99", "20", "*", "*", "*"], ["2", "*", "*", "*", "1", "99", "1", "*", "*", "*"]],
        ),
        encoding="utf-8",
    )
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
    (ovr / "LUDR0.2DA").write_text(
        _table_2da(
            ["ABILITY", "ICON", "STRREF", "MIN_LEV", "MAX_LEVEL", "NUM_ALLOWED", "PREREQUISITE", "EXCLUDED_BY", "ALIGNMENT_RESTRICT"],
            [
                ["1", "GA_SPPR721", "*", "*", "1", "99", "1", "*", "*", "*"],
                ["2", "GA_SPPR731", "*", "*", "1", "99", "22", "*", "*", "*"],
                ["3", "GA_SPPR732", "*", "*", "1", "99", "22", "*", "*", "*"],
                ["4", "*", "*", "*", "*", "*", "*", "*", "*", "*"],
            ],
        ),
        encoding="utf-8",
    )

    kt_race_sfx = [("HUMAN", "H"), ("ELF", "E"), ("HALF_ELF", "HE"), ("DWARF", "D"), ("HALFLING", "HL"), ("GNOME", "G"), ("HALFORC", "HO")]
    if extra_race_col:
        kt_race_sfx.append(("HOBGOBLIN", "HG"))
    kt_hdr = [r for r, _ in kt_race_sfx]
    kt_classes = [
        ("MAGE", "M"), ("FIGHTER", "F"), ("CLERIC", "C"), ("THIEF", "T"), ("BARD", "B"),
        ("PALADIN", "P"), ("DRUID", "D"), ("RANGER", "R"), ("SORCERER", "S"), ("MONK", "MN"),
        ("SHAMAN", "SH"), ("BARBARIAN", "BN"),
        ("FIGHTER_MAGE", "FM"), ("FIGHTER_CLERIC", "FC"), ("FIGHTER_THIEF", "FT"),
        ("FIGHTER_MAGE_THIEF", "FMT"), ("MAGE_THIEF", "MT"), ("CLERIC_MAGE", "CM"),
        ("CLERIC_THIEF", "CT"), ("FIGHTER_DRUID", "FD"), ("FIGHTER_MAGE_CLERIC", "FMC"),
        ("CLERIC_RANGER", "CR"),
    ]
    kt_rows = []
    for cname, cpfx in kt_classes:
        kt_rows.append([cname, *[f"K_{cpfx}_{sfx}" for _, sfx in kt_race_sfx]])
    (ovr / "KITTABLE.2DA").write_text(_table_2da(kt_hdr, kt_rows), encoding="utf-8")
    for _, sfx in kt_race_sfx:
        (ovr / f"K_F_{sfx}.2DA").write_text(_table_2da(["KIT"], [["1", "0"], ["2", "1"]]), encoding="utf-8")
    # Vanilla K_S_D has 0 and 35 (hidden behind SORCERER DWARF=0 in CLSRCREQ)
    (ovr / "K_S_D.2DA").write_text(_table_2da(["KIT"], [["1", "0"], ["2", "35"]]), encoding="utf-8")
    (ovr / "K_D_H.2DA").write_text(_table_2da(["KIT"], [["1", "0"], ["2", "16"]]), encoding="utf-8")
    (ovr / "K_D_HE.2DA").write_text(_table_2da(["KIT"], [["1", "0"], ["2", "16"]]), encoding="utf-8")

    # Armors for Stonefire Sorcerer op145 armored-casting test
    (ovr / "LEAT01.ITM").write_bytes(make_itm_v1(item_type=2, unusable=0, anim="2A", eq_effects=[
        make_eff_v1(0, target=1, p1=8, p2=16, timing=2),
        make_eff_v1(145, target=1, p1=0, p2=0, timing=2),
    ]))
    (ovr / "CHAN01.ITM").write_bytes(make_itm_v1(item_type=2, unusable=0, anim="3A", eq_effects=[
        *( [make_eff_v1(318, target=1, p1=0, p2=0, timing=2, resource="CBKARCDS")] if pre_mutate else [] ),
        make_eff_v1(0, target=1, p1=5, p2=16, timing=2),
        make_eff_v1(145, target=1, p1=0, p2=0, timing=2),
    ]))
    # Splint Mail (3A + Bard unusable 0x40 -> MUST keep raw op145, NOT get CBKARCDS Stonefire bypass!)
    (ovr / "CHAN04.ITM").write_bytes(make_itm_v1(item_type=2, unusable=0x40, anim="3A", eq_effects=[
        make_eff_v1(0, target=1, p1=4, p2=16, timing=2),
        make_eff_v1(145, target=1, p1=0, p2=0, timing=2),
    ]))
    # Plate Mail (4A -> MUST keep raw op145!)
    (ovr / "PLAT01.ITM").write_bytes(make_itm_v1(item_type=2, unusable=0x40, anim="4A", eq_effects=[
        make_eff_v1(0, target=1, p1=3, p2=16, timing=2),
        make_eff_v1(145, target=1, p1=0, p2=0, timing=2),
    ]))

    # Sleep SPWI116 (Half-Elf p2=19 prob1=30 -> upgraded to 50%; Elf p2=15 prob1=90 -> stays 90%)
    (ovr / "SPWI116.SPL").write_bytes(make_spl(spell_type=1, school=4, abilities=[(1, 1, [
        make_eff_v1(324, target=2, p1=0, p2=19, prob1=75 if pre_mutate else 30, prob2=0, resource="SPWI116"),
        make_eff_v1(324, target=2, p1=0, p2=15, prob1=90, prob2=0, resource="SPWI116"),
        make_eff_v1(39, target=2, p1=0, p2=1, timing=0, duration=30),
    ])]))

    # Cure Wounds + Regenerate for Elementalist Tidal Healing test
    for c_res, heal_amt in [("SPPR103", 8), ("SPPR315", 14), ("SPPR401", 17), ("SPPR502", 27), ("SPPR514", 8)]:
        (ovr / f"{c_res}.SPL").write_bytes(make_spl(
            spell_type=2, level=int(c_res[4]), speed=5, rng=2,
            abilities=[(1, 1, [make_eff_v1(17, target=2, p1=heal_amt, p2=0, timing=1)])],
        ))
    (ovr / "SPPR711.SPL").write_bytes(make_spl(spell_type=2, level=7, speed=7, rng=2))

    # Installed Wizard Elemental Spells (Burning Hands L1, Fireball L3, Incendiary Cloud L8 -> cloned to Priest L7!)
    (ovr / "SPWI103.SPL").write_bytes(make_spl(spell_type=1, school=8, level=1, abilities=[(1, 1, [
        make_eff_v1(12, target=2, p1=2, p2=0x00080000, dice=1, sides=3),
    ])]))
    (ovr / "SPWI304.SPL").write_bytes(make_spl(spell_type=1, school=6, level=3, abilities=[(1, 38, [
        make_eff_v1(12, target=2, p1=0, p2=0x00080000, dice=8, sides=6),
    ])]))
    (ovr / "SPWI810.SPL").write_bytes(make_spl(spell_type=1, school=6, level=8, abilities=[(1, 96, [
        make_eff_v1(321, target=1, resource="SPWI810"),
        make_eff_v1(12, target=2, p1=0, p2=0x00080000, dice=10, sides=4),
    ])]))

    # Tempus + Vanilla Clerics + Priest spells + CREs
    (ovr / "CDHLYSYM.SPL").write_bytes(make_spl())
    (ovr / "BELT12.ITM").write_bytes(make_itm_v1(item_type=10, unusable=0x607F3842, flags=0x0000006C))
    (ovr / "OHTEMPUS.2DA").write_text(
        "2DA V1.0\n****\n"
        + "            " + " ".join(str(i) for i in range(1, 26)) + "\n"
        + "ABILITY1    GA_OHTMPS1 " + " ".join("AP_CDHLYSYM" if i == 25 else "****" for i in range(2, 26)) + "\n",
        encoding="utf-8",
    )
    (ovr / "OHTMPS1.SPL").write_bytes(make_spl())
    (ovr / "OHTMPS2D.SPL").write_bytes(make_spl(casting_effects=[make_eff_v1(141, target=1, p1=1, timing=1)], abilities=[(1, 162, [])]))
    (ovr / "OHTMPS2E.SPL").write_bytes(make_spl(casting_effects=[make_eff_v1(141, target=1, p1=2, timing=1)], abilities=[(1, 171, [])]))
    (ovr / "SPPR113.SPL").write_bytes(make_spl(spell_type=2, school=3))
    (ovr / "SPPR415.SPL").write_bytes(make_spl(spell_type=2, school=3))
    (ovr / "SPPR201.SPL").write_bytes(make_spl(spell_type=2, school=1))
    for sp in (
        "SPPR412", "SPPR425", "SPPR507", "SPPR513", "SPPR525", "SPWI603", "SPCL751A", "SPCL121",
        "SPCL721", "SPCL722", "SPCL731", "SPCL732", "SPCL741", "SPCL742", "OHTYR1", "OHTYR2",
    ):
        (ovr / f"{sp}.SPL").write_bytes(make_spl())
    (ovr / "SW1HSEEK.ITM").write_bytes(make_itm_v1(
        item_type=20, unusable=0, anim="S1", prof=89,
        eq_effects=[make_eff_v1(145, target=1, p1=0, p2=0, timing=2)] if pre_mutate else [],
    ))
    if with_yeslick_alaghor:
        (ovr / "K_FC_D.2DA").write_text(_table_2da(["KIT"], [["1", "0"], ["2", "42"]]), encoding="utf-8")
        (ovr / "QD_MCP01.SPL").write_bytes(make_spl(abilities=[(1, 1, [
            make_eff_v1(177, target=1, p1=0x402A, p2=9, timing=1, resource="QDYSLK01"),
            make_eff_v1(177, target=1, p1=0x4099, p2=9, timing=1, resource="QDOTHER1"),
        ])]))

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

    if pre_mutate:
        (ovr / "OHTMPS1.SPL").write_bytes(make_spl(abilities=[(1, 1, [make_eff_v1(99, p1=999)])]))
        (ovr / "SPCL741.SPL").write_bytes(make_spl(abilities=[(1, 1, [make_eff_v1(99, p1=999)])]))
        (ovr / "OHTYR2.SPL").write_bytes(make_spl(abilities=[(1, 1, [make_eff_v1(99, p1=999)])]))
        (ovr / "BRANWE.CRE").write_bytes(make_cre_v1(kit_ids=0x4005, prof_effects=[(92, 0), (101, 1)]))
        (ovr / "BRANWE5.CRE").write_bytes(make_cre_v1(kit_ids=0x4000, prof_effects=[(101, 2)]))
        (ovr / "YESLIC.CRE").write_bytes(make_cre_v1(kit_ids=0x4001, prof_effects=[(97, 1), (107, 2)], levels=(5, 5, 0)))
        (ovr / "VICONI9.CRE").write_bytes(make_cre_v1(kit_ids=0x4013, prof_effects=[(107, 1)], levels=(8, 0, 0)))
        (ovr / "ARCHSLOW.EFF").write_bytes(make_eff_v2(opcode=20, target=2, p1=999))
    else:
        (ovr / "BRANWE.CRE").write_bytes(make_cre_v1(kit_ids=0x4000, prof_effects=[(101, 1)]))
        (ovr / "BRANWE5.CRE").write_bytes(make_cre_v1(kit_ids=0x4000, prof_effects=[(101, 1)]))
        (ovr / "YESLIC.CRE").write_bytes(make_cre_v1(kit_ids=0x4000, prof_effects=[(97, 1), (107, 1)], levels=(5, 5, 0)))
        (ovr / "VICONI9.CRE").write_bytes(make_cre_v1(kit_ids=0x4000, prof_effects=[(107, 1)], levels=(8, 0, 0)))
    (ovr / "KORGAN8.CRE").write_bytes(make_cre_v1(kit_ids=0x4001, prof_effects=[(92, 5)]))

    if conflict_mod == "artisan":
        (game_dir / "weidu.log").write_text("~ARTISANSKITPACK/ARTISANSKITPACK.TP2~ #0 #0 // Artisans Kitpack\n", encoding="utf-8")
    elif conflict_mod == "bardic":
        (game_dir / "weidu.log").write_text("~BARDICWONDERS/BARDICWONDERS.TP2~ #0 #0 // Bardic Wonders\n", encoding="utf-8")
