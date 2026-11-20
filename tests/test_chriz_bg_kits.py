"""Comprehensive verification suite for chriz-bg-kits v0.3.1."""

from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
import sys

import lupa.luajit21 as lj
import pytest

from .fakegame import MOD_DIR, REPO_ROOT, TP2_FILE, create_fake_game
from .harness import run_weidu
from .ie import (
    check_spl_has_opcodes,
    parse_cre_v1,
    parse_itm_v1,
    parse_spl,
    read_bam_palette_entry,
    read_dialog_tlk_strings,
    read_eff_v2,
)

STEAM_EXE = pathlib.Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Baldur's Gate II Enhanced Edition\Baldur.exe"
)

ALL_COMPONENTS_110 = ["100", "110", "200", "201", "202", "203", "204", "210", "220", "300", "310", "320"]


def _sha256_tree(root: pathlib.Path, ignore_prefixes: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        rel_low = rel.lower()
        if rel_low.endswith("dialog.tlk") or rel_low.startswith("weidu"):
            continue
        if any(rel == pref or rel.startswith(pref + "/") for pref in ignore_prefixes):
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _read_2da_rows(path: pathlib.Path) -> list[list[str]]:
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    return [ln.split() for ln in lines[3:]]


def _read_2da_header_and_map(path: pathlib.Path) -> tuple[list[str], dict[str, list[str]]]:
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    hdr = lines[2].split()
    rows = {parts[0]: parts[1:] for ln in lines[3:] if (parts := ln.split())}
    return hdr, rows


def _install_list(game_dir: pathlib.Path, comps: list[str]) -> subprocess.CompletedProcess[str]:
    args = [
        TP2_FILE.name,
        "--game", str(game_dir),
        "--language", "0",
        "--use-lang", "en_US",
        "--force-install-list", *comps,
    ]
    return run_weidu(args, cwd=game_dir)


def _install_all(game_dir: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return _install_list(game_dir, ALL_COMPONENTS_110)


def _uninstall_all(game_dir: pathlib.Path) -> subprocess.CompletedProcess[str]:
    args = [
        TP2_FILE.name,
        "--game", str(game_dir),
        "--language", "0",
        "--use-lang", "en_US",
        "--force-uninstall-list", *reversed(ALL_COMPONENTS_110),
    ]
    return run_weidu(args, cwd=game_dir)


# ---------------------------------------------------------------------------
# 1. Binary Builder & Resource Parity Check
# ---------------------------------------------------------------------------

def test_01_build_resources_check() -> None:
    res = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "build_resources.py"), "--check"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert res.returncode == 0, f"build_resources.py --check failed:\n{res.stdout}\n{res.stderr}"
    assert "128 files" in res.stdout


# ---------------------------------------------------------------------------
# 2. WeiDU Parse Check
# ---------------------------------------------------------------------------

def test_02_weidu_parse_check() -> None:
    targets: list[tuple[pathlib.Path, str]] = [(TP2_FILE, "tp2")]
    targets.extend((p, "tpa") for p in sorted((MOD_DIR / "lib").glob("*.tpa")))
    targets.extend((p, "tpa") for p in sorted((MOD_DIR / "lib").glob("*.tph")))
    for path, kind in targets:
        res = run_weidu(["--nogame", "--parse-check", kind, str(path)], cwd=REPO_ROOT)
        assert "successfully parsed" in res.stdout


# ---------------------------------------------------------------------------
# 3. Full Clean Install (BG2:EE & EET with HOBGOBLIN extra race column)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mode,extra_race", [("bg2ee", False), ("eet", True)])
def test_03_clean_install_all_components(tmp_path: pathlib.Path, mode: str, extra_race: bool) -> None:
    game = tmp_path / f"game_{mode}"
    create_fake_game(game, mode=mode, extra_race_col=extra_race)
    _install_all(game)
    ovr = game / "override"

    # Comp 100: Kernel
    for db in ("CBKWPN.db", "CBKKP.db", "CBKSP.db", "CBKCMB.db"):
        assert (game / "EEex_scripts" / "extra_pattern_dbs" / db).is_file()
    for tbl in ("CBKWPN", "CBKAPKIT", "CBRKPKIT", "CBRSPVER", "CBRSPKIT", "CBRBG6", "CBRIWD7", "CBRIWD8"):
        assert (ovr / f"{tbl}.2DA").is_file()
    for lua in (
        "M_CBKWPN.lua", "M_CBKKP.lua", "M_CBKAPR.lua", "M_CBKSP.lua",
        "M_CBKSTR.lua", "M_CBKDCN.lua", "M_CBKCMB.lua",
        "M_CBKRAC.lua", "M_CBKSF.lua", "M_CBKELM.lua",
        "M_CBKSHR.lua", "M_CBKILM.lua",
    ):
        text = (ovr / lua).read_text(encoding="utf-8")
        assert not re.search(r"%[A-Z0-9_]+%", text), f"Unresolved %VAR% in {lua}"

    splstate_text = (ovr / "SPLSTATE.IDS").read_text(encoding="utf-8")
    for sym in (
        "CBM_STR_FLOOR", "CBR_TEMPUS_SPEC_APR", "CBK_STR_CLAMP_1",
        "CBK_RAC_RESOLVED", "CBK_STONEFIRE_ARMOR",
        "CBK_ELM_FIRE", "CBK_ELM_WATER", "CBK_ELM_AIR", "CBK_ELM_EARTH",
        "CBK_ELM_HLA", "CBK_ELM_RESOLVED",
        "CBM_BONUS_TYPED", "CBK_SHAR_WEAVE", "CBK_ILMATER_ENDURE", "CBK_ILM_RESOLVED",
    ):
        assert sym in splstate_text

    # Comp 110: Forgotten Realms Racial Class, Kit & Multiclass Rules
    mg_rows = _read_2da_rows(ovr / "MGSRCREQ.2DA")
    assert mg_rows[0][1] == "MAGE"
    assert mg_rows[1][1] == "ILLUSIONIST"  # Gnome multiclasses stay Illusionists!
    mg_by_school = {r[1]: r[2:] for r in mg_rows}
    # Columns: HUMAN(0), ELF(1), HALF_ELF(2), DWARF(3), HALFLING(4), GNOME(5), HALFORC(6), [HOBGOBLIN(7)]
    assert mg_by_school["MAGE"][3] == "0"        # Dwarf MAGE=0 so F/M & C/M hit ABJURER
    assert mg_by_school["ABJURER"][3] == "1"
    assert mg_by_school["TRANSMUTER"][3] == "1"
    assert mg_by_school["INVOKER"][3] == "1"
    assert mg_by_school["NECROMANCER"][1] == "0"  # Elf Necromancer=0
    assert mg_by_school["NECROMANCER"][4] == "0"  # Halfling Necromancer=0
    assert mg_by_school["MAGE"][4] == "1"         # Halfling Mage=1
    assert mg_by_school["ILLUSIONIST"][5] == "1" and mg_by_school["DIVINER"][5] == "1" and mg_by_school["TRANSMUTER"][5] == "1"

    rc_hdr, rc_rows = _read_2da_header_and_map(ovr / "CLSRCREQ.2DA")
    assert rc_rows["DUALCLASS"][:7] == ["1"] * 7
    assert all(rc_rows[mc][0] == "1" and rc_rows[mc][1] == "1" for mc in (
        "FIGHTER_MAGE", "FIGHTER_CLERIC", "FIGHTER_THIEF", "FIGHTER_MAGE_THIEF", "MAGE_THIEF",
        "CLERIC_MAGE", "CLERIC_THIEF", "FIGHTER_DRUID", "FIGHTER_MAGE_CLERIC", "CLERIC_RANGER",
    ))
    assert rc_rows["PALADIN"][3] == "1" and rc_rows["RANGER"][3] == "1" and rc_rows["CLERIC_THIEF"][3] == "1"
    assert rc_rows["FIGHTER_MAGE"][3] == "1" and rc_rows["CLERIC_MAGE"][3] == "1"
    assert rc_rows["SORCERER"][3] == "1"  # unlocked for Dwarf via CBK_STONEFIRE

    # ABRACEAD & RACETHAC & Sleep 50% Half-Elf resistance
    _, ab_rows = _read_2da_header_and_map(ovr / "ABRACEAD.2DA")
    assert ab_rows["DWARF"][5] == "-1"
    assert ab_rows["HALF_ELF"][5] == "1"
    _, rt_rows = _read_2da_header_and_map(ovr / "RACETHAC.2DA")
    for prof_id in ("91", "96", "106", "107"):
        assert rt_rows[prof_id][4] == "1"
    spwi116 = parse_spl((ovr / "SPWI116.SPL").read_bytes())
    he_324 = [fx for fx in spwi116["abilities"][0]["effects"] if fx["opcode"] == 324 and fx["p2"] == 19]
    elf_324 = [fx for fx in spwi116["abilities"][0]["effects"] if fx["opcode"] == 324 and fx["p2"] == 15]
    assert len(he_324) == 1 and he_324[0]["prob1"] == 50
    assert len(elf_324) == 1 and elf_324[0]["prob1"] == 90

    # Barbarian dual-classing tables
    _, dc_rows = _read_2da_header_and_map(ovr / "DUALCLAS.2DA")
    assert "BARBARIAN" in dc_rows and dc_rows["BARBARIAN"][:4] == ["0", "1", "1", "1"]
    _, dcd_rows = _read_2da_header_and_map(ovr / "ABDCDSRQ.2DA")
    _, dcs_rows = _read_2da_header_and_map(ovr / "ABDCSCRQ.2DA")
    assert "BARBARIAN" in dcd_rows and "BARBARIAN" in dcs_rows

    # Animation clones: Halfling Mage (6203, 6213) & Non-Human Monks (6501..6505, 6511..6515)
    anim_ids = (ovr / "ANIMATE.IDS").read_text(encoding="utf-8")
    for hex_id in ("0x6203", "0x6213", "0x6501", "0x6502", "0x6503", "0x6504", "0x6505", "0x6511", "0x6515"):
        assert hex_id.lower() in anim_ids.lower()
        assert (ovr / f"{hex_id[2:]}.INI").is_file()

    # RACETEXT (and BGRACTXT on EET) appended descriptions
    tlk_strings = read_dialog_tlk_strings(game / "lang" / "en_US" / "dialog.tlk")
    _, rtxt = _read_2da_header_and_map(ovr / "RACETEXT.2DA")
    assert "Second Wind" in tlk_strings[int(rtxt["HUMAN"][2])]
    assert "Saving Throws vs. Spell" in tlk_strings[int(rtxt["ELF"][2])]
    assert "Silver Tongue" in tlk_strings[int(rtxt["HALF_ELF"][2])]
    assert "Halfling Finesse" in tlk_strings[int(rtxt["HALFLING"][2])]
    if mode == "eet":
        _, bgrtxt = _read_2da_header_and_map(ovr / "BGRACTXT.2DA")
        assert "Second Wind" in tlk_strings[int(bgrtxt["HUMAN"][2])]

    # Kit tables lookup
    kitlist_rows = _read_2da_rows(ovr / "KITLIST.2DA")
    kl_by_name = {r[1]: r for r in kitlist_rows}

    if extra_race:
        _, kt_map = _read_2da_header_and_map(ovr / "KITTABLE.2DA")
        hb_col_idx = rc_hdr.index("HOBGOBLIN")
        assert kt_map["FIGHTER"][hb_col_idx] == "K_F_HB"
        assert kt_map["PALADIN"][hb_col_idx] == "K_P_HB"
        assert kt_map["RANGER"][hb_col_idx] == "K_R_HB"
        kf_hb = {r[1] for r in _read_2da_rows(ovr / "K_F_HB.2DA")}
        kp_hb = {r[1] for r in _read_2da_rows(ovr / "K_P_HB.2DA")}
        kr_hb = {r[1] for r in _read_2da_rows(ovr / "K_R_HB.2DA")}
        # Hobgoblin: Fighter (no Dwarven Defender 34, no CBKBLDRG), Paladin (Inquisitor 5, Blackguard 32, no Cavalier 4, no unkitted 0), Ranger (0, 7, 8, no Beast Master 9)
        assert "34" not in kf_hb and kl_by_name["CBKBLDRG"][0] not in kf_hb
        assert kp_hb == {"5", "32"}
        assert {"0", "7", "8"}.issubset(kr_hb) and "9" not in kr_hb
        assert rc_rows["DRUID"][hb_col_idx] == "0"

    # Comp 200: Priest of Tempus (Single-Class + Dual-Class only; zero player multiclass kits!)
    ohtempus = (ovr / "OHTEMPUS.2DA").read_text(encoding="utf-8")
    assert "AP_CDHLYSYM" in ohtempus and "AP_CBKTMP1" in ohtempus and "AP_CBKTMDV" in ohtempus
    branwe = parse_cre_v1((ovr / "BRANWE.CRE").read_bytes())
    assert branwe["kit_ids"] == 0x4029 and branwe["profs"].get(92, 0) >= 1
    assert not (ovr / "CBKMCP01.SPL").exists()
    assert "LK_ALAGHOR" not in kl_by_name

    _, kt_all = _read_2da_header_and_map(ovr / "KITTABLE.2DA")
    for mc_cls in (
        "FIGHTER_MAGE", "FIGHTER_CLERIC", "FIGHTER_THIEF", "FIGHTER_MAGE_THIEF", "MAGE_THIEF",
        "CLERIC_MAGE", "CLERIC_THIEF", "FIGHTER_DRUID", "FIGHTER_MAGE_CLERIC", "CLERIC_RANGER",
    ):
        for tbl in kt_all[mc_cls]:
            tpath = ovr / f"{tbl}.2DA"
            if tpath.is_file():
                assert [r[1] for r in _read_2da_rows(tpath)] == ["0"], f"{tbl} must stay unkitted!"
    for req_mc_tbl in ("K_FC_H", "K_FC_D", "K_CT_H", "K_CR_H"):
        assert [r[1] for r in _read_2da_rows(ovr / f"{req_mc_tbl}.2DA")] == ["0"]

    # Comp 201: Vanilla Deity Clerics (Lathander, Helm, Talos, Tyr)
    for clab_f, expected_toks in [
        ("CLABPR04.2DA", ("AP_CBKLPLA", "GA_SPCL741", "GA_SPCL742", "AP_CDHLYSYM")),
        ("CLABPR03.2DA", ("AP_CBKLPHM", "GA_SPCL731", "GA_SPCL732", "AP_CDHLYSYM")),
        ("CLABPR02.2DA", ("AP_CBKLPTL", "AP_CBKTAL0", "GA_SPCL721", "GA_SPCL722", "AP_CDHLYSYM")),
        ("OHTYR.2DA", ("AP_CBKLPTY", "GA_OHTYR1", "GA_OHTYR2", "AP_CBKHSYTY")),
    ]:
        ctext = (ovr / clab_f).read_text(encoding="utf-8")
        for tok in expected_toks:
            assert tok in ctext, f"{tok} missing in {clab_f}"
        assert "SPPR301" not in ctext  # Animate Dead never stripped
    spcl741 = parse_spl((ovr / "SPCL741.SPL").read_bytes())
    assert len(spcl741["abilities"]) == 20
    ab0_741 = spcl741["abilities"][0]["effects"]
    assert ab0_741[0]["opcode"] == 321 and ab0_741[0]["resource"] == "SPCL741"
    assert any(fx["opcode"] == 1 and fx["resource"] == "CBTAPR" and fx["special"] == 1 for fx in ab0_741)
    assert any(fx["opcode"] == 328 and fx["resource"] == "CBTSTATE" and fx["special"] == 1 for fx in ab0_741)
    sw1hseek = parse_itm_v1((ovr / "SW1HSEEK.ITM").read_bytes())
    seek_ops = [fx["opcode"] for fx in sw1hseek["equipping_effects"]]
    assert 145 not in seek_ops and 1 in seek_ops and 0 in seek_ops
    spcl722 = parse_spl((ovr / "SPCL722.SPL").read_bytes())
    assert len(spcl722["abilities"]) == 10 and all(ab["projectile"] == 1 for ab in spcl722["abilities"])
    ohtyr2 = parse_spl((ovr / "OHTYR2.SPL").read_bytes())
    assert [ab["min_level"] for ab in ohtyr2["abilities"]] == [1, 6, 9, 12, 15, 18]
    cbkhtyr = parse_itm_v1((ovr / "CBKHTYR.ITM").read_bytes())
    assert cbkhtyr["item_type"] == 10 and cbkhtyr["flags"] == 0x0000006C
    assert [(fx["opcode"], fx["p1"], fx["p2"]) for fx in cbkhtyr["equipping_effects"]] == [
        (62, 1, 0x20), (62, 1, 0x40), (166, 5, 0), (44, 1, 0), (142, 0, 0x3F),
    ]

    # Comp 202: Priest of Shar (CBK_SHAR — single-class Cleric + Viconia single-class sync)
    assert "CBK_SHAR" in kl_by_name
    shar_row = kl_by_name["CBK_SHAR"]
    shar_num, shar_ids = shar_row[0], int(shar_row[9], 16)
    assert shar_row[8] == "3" and int(shar_row[7], 16) == 0x00004000
    assert tlk_strings[int(shar_row[2])] == "priest of shar"
    assert tlk_strings[int(shar_row[3])] == "Priest of Shar"
    cbkshr2 = parse_spl((ovr / "CBKSHR2.SPL").read_bytes())
    assert not any(fx["opcode"] == 74 for ab in cbkshr2["abilities"] for fx in ab["effects"])  # NO blindness!
    viconi = parse_cre_v1((ovr / "VICONI9.CRE").read_bytes())
    assert viconi["kit_ids"] == shar_ids and viconi["levels"] == (8, 0, 0)  # Level bytes NEVER touched!

    # Comp 203: Priest of Umberlee (CBK_UMBERLEE)
    assert "CBK_UMBERLEE" in kl_by_name
    umb_row = kl_by_name["CBK_UMBERLEE"]
    umb_num, umb_ids = umb_row[0], int(umb_row[9], 16)
    assert tlk_strings[int(umb_row[2])] == "priest of umberlee"
    assert tlk_strings[int(umb_row[3])] == "Priest of Umberlee"
    _, al_rows = _read_2da_header_and_map(ovr / "ALIGNMNT.2DA")
    assert al_rows["CBK_UMBERLEE"] == ["0", "0", "0", "0", "0", "1", "0", "1", "1"]  # NE, CN, CE only (NO CG!)
    assert umb_num not in [r[1] for r in _read_2da_rows(ovr / "K_C_D.2DA")]
    assert umb_num in [r[1] for r in _read_2da_rows(ovr / "K_C_H.2DA")]
    cbkhumb = parse_itm_v1((ovr / "CBKHUMB.ITM").read_bytes())
    assert any(fx["opcode"] == 49 and fx["p1"] == 1 for fx in cbkhumb["equipping_effects"])

    # Comp 204: Priest of Ilmater (CBK_ILMATER)
    assert "CBK_ILMATER" in kl_by_name
    ilm_row = kl_by_name["CBK_ILMATER"]
    ilm_num = ilm_row[0]
    assert tlk_strings[int(ilm_row[2])] == "priest of ilmater"
    assert tlk_strings[int(ilm_row[3])] == "Priest of Ilmater"
    assert al_rows["CBK_ILMATER"] == ["1", "1", "0", "1", "0", "0", "0", "0", "0"]  # LG, LN, NG
    assert ilm_num in [r[1] for r in _read_2da_rows(ovr / "K_C_D.2DA")]
    if extra_race:
        assert ilm_num not in [r[1] for r in _read_2da_rows(ovr / "K_C_HB.2DA")]
        assert umb_num in [r[1] for r in _read_2da_rows(ovr / "K_C_HB.2DA")]
        assert shar_num in [r[1] for r in _read_2da_rows(ovr / "K_C_HB.2DA")]
    _, sp_prot_map = _read_2da_header_and_map(ovr / "SPLPROT.2DA")
    assert sp_prot_map["CBK_HP_LE_10"] == ["0", "10", "0"]
    cbkilm2s = parse_spl((ovr / "CBKILM2S.SPL").read_bytes())
    assert cbkilm2s["abilities"][0]["effects"][0]["opcode"] == 318
    assert cbkilm2s["abilities"][0]["effects"][1]["opcode"] == 12
    cbkhilm = parse_itm_v1((ovr / "CBKHILM.ITM").read_bytes())
    assert any(fx["opcode"] == 10 and fx["p1"] == 1 for fx in cbkhilm["equipping_effects"])

    # Verify dual-class WIS mins (17 / 15) on all new Cleric kits (CBK_SHAR, CBK_UMBERLEE, CBK_ILMATER)
    _, dcd_all = _read_2da_header_and_map(ovr / "ABDCDSRQ.2DA")
    _, dcs_all = _read_2da_header_and_map(ovr / "ABDCSCRQ.2DA")
    for ck in ("CBK_SHAR", "CBK_UMBERLEE", "CBK_ILMATER"):
        assert dcd_all[ck] == ["0", "0", "0", "0", "17", "0"], f"ABDCDSRQ {ck}={dcd_all[ck]}"
        assert dcs_all[ck] == ["0", "0", "0", "0", "15", "0"], f"ABDCSCRQ {ck}={dcs_all[ck]}"

    # Verify WEAPPROF.2DA EXTRA2..EXTRA20 (116..134) stay 0 across all v0.3.1 Cleric kits
    wp_lines_all = (ovr / "WEAPPROF.2DA").read_text(encoding="utf-8").splitlines()
    wp_hdr_all = wp_lines_all[2].split()
    for kit_col in ("HELM", "TALOS", "OHTYR", "CBK_SHAR", "CBK_UMBERLEE", "CBK_ILMATER"):
        c_idx = wp_hdr_all.index(kit_col) + 1
        for line in wp_lines_all[3:]:
            parts = line.split()
            if parts and int(parts[1]) >= 116:
                assert parts[c_idx] == "0", f"{kit_col} non-zero EXTRA row {parts[0]}={parts[c_idx]}"

    # Verify CBKWPN rules for 202..203
    cbkwpn_all = _read_2da_rows(ovr / "CBKWPN.2DA")
    shar_wpn = {(r[3], r[4], r[5]) for r in cbkwpn_all if r[2] == str(shar_ids)}
    assert ("PROF", "96", "ALLOW") in shar_wpn
    umb_wpn = {(r[3], r[4], r[5]) for r in cbkwpn_all if r[2] == str(umb_ids)}
    assert {("PROF", "98", "ALLOW"), ("PROF", "96", "ALLOW")}.issubset(umb_wpn)

    # Comp 210: Stonefire Sorcerer (CBK_STONEFIRE)
    assert "CBK_STONEFIRE" in kl_by_name
    sf_row = kl_by_name["CBK_STONEFIRE"]
    sf_num = sf_row[0]
    sf_ids = int(sf_row[9], 16)
    assert sf_row[8] == "19" and int(sf_row[7], 16) == 0x00001000
    _, hp_rows = _read_2da_header_and_map(ovr / "HPCLASS.2DA")
    assert hp_rows["CBK_STONEFIRE"][0] == "HPDD"
    # Dwarf-only in 110: K_S_D has ONLY Stonefire (no 0 unkitted, no 35 Dragon Disciple); K_S_H does NOT have Stonefire
    ks_d = [r[1] for r in _read_2da_rows(ovr / "K_S_D.2DA")]
    ks_h = [r[1] for r in _read_2da_rows(ovr / "K_S_H.2DA")]
    assert ks_d == [sf_num]
    assert sf_num not in ks_h

    wp_lines = (ovr / "WEAPPROF.2DA").read_text(encoding="utf-8").splitlines()
    wp_hdr = wp_lines[2].split()
    sf_wp_idx = wp_hdr.index("CBK_STONEFIRE") + 1
    for line in wp_lines[3:]:
        parts = line.split()
        if parts and int(parts[1]) in (92, 97):
            assert parts[sf_wp_idx] == "2"
        elif parts and int(parts[1]) in (96, 102, 106, 107):
            assert parts[sf_wp_idx] == "1"

    # CBKSF0.2DA CLAB checks: op42 -1 spell cast triggers at L1,4,6,8,10,12,14,16,18
    cbksf0_text = (ovr / "CBKSF0.2DA").read_text(encoding="utf-8")
    for c_lv in range(1, 10):
        assert f"AP_CBKSFC{c_lv}" in cbksf0_text
    assert "GA_CBKSF01" in cbksf0_text
    cbksf01 = parse_spl((ovr / "CBKSF01.SPL").read_bytes())
    assert [ab["min_level"] for ab in cbksf01["abilities"]] == [1, 9, 15]

    # Armored arcane casting: LEAT01 & CHAN01 get op318 + op177 CBKARCDS; CHAN04 (Splint) & PLAT01 (Plate) keep raw op145!
    arcds = read_eff_v2((ovr / "CBKARCDS.EFF").read_bytes())
    assert arcds["opcode"] == 145 and arcds["parent_type"] == 1 and arcds["parent_resource"] == "CBKARCDS"
    for light_arm in ("LEAT01.ITM", "CHAN01.ITM"):
        itm = parse_itm_v1((ovr / light_arm).read_bytes())
        ops = [fx["opcode"] for fx in itm["equipping_effects"]]
        assert 145 not in ops
        assert ops.count(318) == 1 and ops.count(177) == 1
        assert ops.index(318) < ops.index(177)
    for heavy_arm in ("CHAN04.ITM", "PLAT01.ITM"):
        itm = parse_itm_v1((ovr / heavy_arm).read_bytes())
        ops = [fx["opcode"] for fx in itm["equipping_effects"]]
        assert 145 in ops and 177 not in ops

    # Comp 220: Elementalist (CBK_ELEMENTALIST)
    assert "CBK_ELEMENTALIST" in kl_by_name
    el_row = kl_by_name["CBK_ELEMENTALIST"]
    el_ids = int(el_row[9], 16)
    assert el_row[8] == "11" and int(el_row[7], 16) == 0x00004000
    assert hp_rows["CBK_ELEMENTALIST"][0] == "HPPRS"

    # CLAB CBKEL0.2DA: shared uses at L3(x2), L7(+1), L10(+1), L12(+1), L15(+0 -> total 5 grants per form)
    cbkel0_text = (ovr / "CBKEL0.2DA").read_text(encoding="utf-8")
    for f_idx in range(1, 5):
        assert len(re.findall(rf"\bGA_CBKELF{f_idx}\b", cbkel0_text)) == 5

    # Cloned Wizard Level 8 Incendiary Cloud (SPWI810) -> Priest Level 7 CBKEL73 with self-321 rewritten!
    cbkel73 = parse_spl((ovr / "CBKEL73.SPL").read_bytes())
    assert cbkel73["spell_type"] == 2 and cbkel73["level"] == 7
    assert any(fx["opcode"] == 321 and fx["resource"] == "CBKEL73" for ab in cbkel73["abilities"] for fx in ab["effects"])

    # Tidal Healing clones: CBKWTH1,3,4,5,6 exist with speed=1 and +25% healing; SPPR711 Regenerate has NO clone!
    sppr401_orig = parse_spl((ovr / "SPPR401.SPL").read_bytes())
    cbkwth4 = parse_spl((ovr / "CBKWTH4.SPL").read_bytes())
    assert cbkwth4["abilities"][0]["speed"] == 1
    orig_heal = [fx["p1"] for fx in sppr401_orig["abilities"][0]["effects"] if fx["opcode"] == 17][0]
    tidal_heal = [fx["p1"] for fx in cbkwth4["abilities"][0]["effects"] if fx["opcode"] == 17][0]
    assert tidal_heal == (orig_heal * 125 + 50) // 100  # 17 * 1.25 rounded = 21
    assert not (ovr / "CBKWTH7.SPL").exists()

    # Personal space = 3 elemental animations 0x7330..0x7337 + blue Water Elemental BAM palette
    for slot_hex in ("7330", "7331", "7332", "7333", "7334", "7335", "7336", "7337"):
        ini_txt = (ovr / f"{slot_hex}.INI").read_text(encoding="utf-8")
        assert "personal_space=3" in ini_txt
    r_pal, _g_pal, b_pal = read_bam_palette_entry((ovr / "MWASG1.BAM").read_bytes(), 2)
    assert b_pal > r_pal  # R/B swapped from orange (R=250, B=20) to deep blue (B=250, R=20)

    # LUEL0.2DA HLA table: Primal Penetration AP_CBKELHLA (NUM_ALLOWED=1) & SPPR731/732 removed
    luel0_rows = _read_2da_rows(ovr / "LUEL0.2DA")
    luel0_abs = {r[1]: r for r in luel0_rows}
    assert "AP_CBKELHLA" in luel0_abs and luel0_abs["AP_CBKELHLA"][6] == "1"
    assert not any("SPPR731" in k or "SPPR732" in k for k in luel0_abs)

    # CBKWPN rules for Stonefire & Elementalist
    cbkwpn_rows = _read_2da_rows(ovr / "CBKWPN.2DA")
    sf_rules = {(r[3], r[4], r[5]) for r in cbkwpn_rows if r[2] == str(sf_ids)}
    assert {
        ("PROF", "92", "ALLOW"), ("PROF", "97", "ALLOW"),
        ("SUBTYPE", "2", "ALLOW"), ("SUBTYPE", "3", "DENY"),
        ("SUBTYPE", "4", "ALLOW"), ("SUBTYPE", "5", "DENY"),
        ("SUBTYPE", "7", "ALLOW"),
    }.issubset(sf_rules)
    el_rules = {(r[3], r[4], r[5]) for r in cbkwpn_rows if r[2] == str(el_ids)}
    assert {("SUBTYPE", "1", "DENY"), ("SUBTYPE", "6", "ALLOW")}.issubset(el_rules)

    # Comp 300, 310, 320 regression checks
    assert "CBKBLDRG" in kl_by_name
    korgan = parse_cre_v1((ovr / "KORGAN8.CRE").read_bytes())
    assert korgan["kit_ids"] == 0x4001 and korgan["profs"].get(92) == 5
    luabbr = {r[0]: r[1] for r in _read_2da_rows(ovr / "LUABBR.2DA")}
    assert luabbr["JESTER"] == "CBKJ"
    assert read_eff_v2((ovr / "ARCHSLOW.EFF").read_bytes())["opcode"] == 326


# ---------------------------------------------------------------------------
# 3b. Component 111 + Install-Order Permutations + Fallbacks
# ---------------------------------------------------------------------------

def test_03b_comp_111_and_install_orders_and_fallbacks(tmp_path: pathlib.Path) -> None:
    # 1) Install 210 + 220 BEFORE 110 -> Stonefire stays Dwarf-only
    g1 = tmp_path / "order_210_then_110"
    create_fake_game(g1, mode="bg2ee", with_fire_bams=False, with_druid_icelance=True)
    _install_list(g1, ["100", "210", "220"])
    _install_list(g1, ["110"])
    ovr1 = g1 / "override"
    kl1 = {r[1]: r for r in _read_2da_rows(ovr1 / "KITLIST.2DA")}
    sf_num1 = kl1["CBK_STONEFIRE"][0]
    assert [r[1] for r in _read_2da_rows(ovr1 / "K_S_D.2DA")] == [sf_num1]
    assert sf_num1 not in [r[1] for r in _read_2da_rows(ovr1 / "K_S_H.2DA")]
    # Water Weird fallback when MFIS/MFIE BAMs are absent: 7332.INI uses MWWE resref
    assert "resref=MWWE" in (ovr1 / "7332.INI").read_text(encoding="utf-8")
    # Icelance deduplication when CLERIC_CBMAGIC_ICELANCE is already in SPELL.IDS: GA_CBKEL33 skipped in CBKEL0.2DA
    cbkel0_1 = (ovr1 / "CBKEL0.2DA").read_text(encoding="utf-8")
    assert "GA_CBKEL33" not in cbkel0_1 and "GA_CBKEL32" in cbkel0_1 and "GA_CBKEL11" in cbkel0_1 and "GA_CBKEL73" in cbkel0_1

    # 2) Install 210 + 300 BEFORE 111 on EET+HOBGOBLIN -> all races unlocked for Stonefire, Bloodrager, Necromancer, etc.
    g2 = tmp_path / "order_210_then_111"
    create_fake_game(g2, mode="eet", extra_race_col=True)
    _install_list(g2, ["100", "210", "300"])
    _install_list(g2, ["111"])
    ovr2 = g2 / "override"
    kl2 = {r[1]: r for r in _read_2da_rows(ovr2 / "KITLIST.2DA")}
    sf_num2 = kl2["CBK_STONEFIRE"][0]
    br_num2 = kl2["CBKBLDRG"][0]
    assert {"0", "35", sf_num2}.issubset({r[1] for r in _read_2da_rows(ovr2 / "K_S_D.2DA")})
    assert sf_num2 in {r[1] for r in _read_2da_rows(ovr2 / "K_S_H.2DA")}
    assert br_num2 in {r[1] for r in _read_2da_rows(ovr2 / "K_F_HL.2DA")}
    assert br_num2 in {r[1] for r in _read_2da_rows(ovr2 / "K_F_HB.2DA")}
    mg2 = _read_2da_rows(ovr2 / "MGSRCREQ.2DA")
    assert mg2[0][1] == "MAGE" and mg2[1][1] == "ILLUSIONIST"
    # 3) Install 100..204 + 110 + 320 (with yeslick-npc pre-installed LK_ALAGHOR in KITLIST & K_FC_D)
    g3 = tmp_path / "order_clerics_then_110"
    create_fake_game(g3, mode="eet", extra_race_col=True, with_druid_icelance=True, with_yeslick_alaghor=True)
    _install_list(g3, ["100", "200", "201", "202", "203", "204"])
    _install_list(g3, ["110", "320"])
    ovr3 = g3 / "override"
    kl3 = {r[1]: r for r in _read_2da_rows(ovr3 / "KITLIST.2DA")}
    t3, a3, s3, u3, i3 = kl3["OHTEMPUS"][0], kl3["LK_ALAGHOR"][0], kl3["CBK_SHAR"][0], kl3["CBK_UMBERLEE"][0], kl3["CBK_ILMATER"][0]
    assert len([r for r in _read_2da_rows(ovr3 / "KITLIST.2DA") if r[1] == "LK_ALAGHOR"]) == 1
    # External LK_ALAGHOR gets Battle Axe usability + Fighter/Cleric Battle Axe level-up pips automatically (100 & 320 idempotent)
    cbkwpn3 = _read_2da_rows(ovr3 / "CBKWPN.2DA")
    assert ("PROF", "92", "ALLOW") in {(r[3], r[4], r[5]) for r in cbkwpn3 if r[2] == str(0x402A)}
    alag_kp3 = [r for r in _read_2da_rows(ovr3 / "CBRKPKIT.2DA") if r[0] == "LK_ALAGHOR_FC"]
    assert alag_kp3 == [["LK_ALAGHOR_FC", "8", str(0x402A)]]
    # Umberlee Icelance deduplication when CLERIC_CBMAGIC_ICELANCE is present
    cbkumb0_3 = (ovr3 / "CBKUMB0.2DA").read_text(encoding="utf-8")
    assert "GA_CBKUMIL" not in cbkumb0_3 and "GA_CBKUMCC" in cbkumb0_3
    # Reverse-order FR preservation across single-class K_C_* + zero player multiclass kits in K_FC_D!
    assert a3 in [r[1] for r in _read_2da_rows(ovr3 / "K_C_D.2DA")]
    assert a3 not in [r[1] for r in _read_2da_rows(ovr3 / "K_C_H.2DA")]
    assert u3 not in [r[1] for r in _read_2da_rows(ovr3 / "K_C_D.2DA")]
    assert u3 in [r[1] for r in _read_2da_rows(ovr3 / "K_C_H.2DA")]
    assert i3 not in [r[1] for r in _read_2da_rows(ovr3 / "K_C_HB.2DA")]
    assert t3 in [r[1] for r in _read_2da_rows(ovr3 / "K_C_D.2DA")]
    assert [r[1] for r in _read_2da_rows(ovr3 / "K_FC_D.2DA")] == ["0"]
    assert [r[1] for r in _read_2da_rows(ovr3 / "K_FC_E.2DA")] == ["0"]
    assert [r[1] for r in _read_2da_rows(ovr3 / "K_CT_HB.2DA")] == ["0"]
    assert [r[1] for r in _read_2da_rows(ovr3 / "K_CR_E.2DA")] == ["0"]

    # 4) Install 200..204 BEFORE 111 -> Unlock All unlocks every Cleric kit across all single-class race tables (multiclasses stay ["0"])
    g4 = tmp_path / "order_clerics_then_111"
    create_fake_game(g4, mode="eet", extra_race_col=True)
    _install_list(g4, ["100", "200", "201", "202", "203", "204"])
    _install_list(g4, ["111"])
    ovr4 = g4 / "override"
    kl4 = {r[1]: r for r in _read_2da_rows(ovr4 / "KITLIST.2DA")}
    t4, s4, u4, i4 = kl4["OHTEMPUS"][0], kl4["CBK_SHAR"][0], kl4["CBK_UMBERLEE"][0], kl4["CBK_ILMATER"][0]
    assert {t4, s4, u4, i4}.issubset(set(r[1] for r in _read_2da_rows(ovr4 / "K_C_D.2DA")))
    assert {t4, s4, u4, i4}.issubset(set(r[1] for r in _read_2da_rows(ovr4 / "K_C_HB.2DA")))
    assert [r[1] for r in _read_2da_rows(ovr4 / "K_FC_H.2DA")] == ["0"]
    assert [r[1] for r in _read_2da_rows(ovr4 / "K_CT_H.2DA")] == ["0"]
    assert [r[1] for r in _read_2da_rows(ovr4 / "K_CR_D.2DA")] == ["0"]


# ---------------------------------------------------------------------------
# 4. We Overwrite Test (pre-mutated upstream inputs)
# ---------------------------------------------------------------------------

def test_04_we_overwrite_converges_from_mutated_state(tmp_path: pathlib.Path) -> None:
    game = tmp_path / "game_mutated"
    create_fake_game(game, mode="bg2ee", pre_mutate=True)
    _install_all(game)
    ovr = game / "override"

    branwe = parse_cre_v1((ovr / "BRANWE.CRE").read_bytes())
    assert branwe["kit_ids"] == 0x4029 and branwe["profs"].get(92, 0) == 1
    arch = read_eff_v2((ovr / "ARCHSLOW.EFF").read_bytes())
    assert arch["opcode"] == 326 and arch["resource"] == "CBKARCSL"
    ohtmps1 = parse_spl((ovr / "OHTMPS1.SPL").read_bytes())
    assert not any(fx["opcode"] == 99 for ab in ohtmps1["abilities"] for fx in ab["effects"])

    # v0.2.0 + v0.3.1 We Overwrite checks on mutated ABRACEAD, RACETHAC, SPWI116, CHAN01, SW1HSEEK, SPCL741, OHTYR2, VICONI9
    _, ab_rows = _read_2da_header_and_map(ovr / "ABRACEAD.2DA")
    assert ab_rows["DWARF"][5] == "-1"
    _, rt_rows = _read_2da_header_and_map(ovr / "RACETHAC.2DA")
    assert rt_rows["91"][4] == "1"
    spwi116 = parse_spl((ovr / "SPWI116.SPL").read_bytes())
    he_324 = [fx for fx in spwi116["abilities"][0]["effects"] if fx["opcode"] == 324 and fx["p2"] == 19]
    assert len(he_324) == 1 and he_324[0]["prob1"] == 50
    chan01 = parse_itm_v1((ovr / "CHAN01.ITM").read_bytes())
    ops = [fx["opcode"] for fx in chan01["equipping_effects"]]
    assert ops.count(318) == 1 and ops.count(177) == 1 and 145 not in ops
    sw1hseek_m = parse_itm_v1((ovr / "SW1HSEEK.ITM").read_bytes())
    assert 145 not in [fx["opcode"] for fx in sw1hseek_m["equipping_effects"]]
    for sp_m in ("SPCL741.SPL", "OHTYR2.SPL"):
        parsed_m = parse_spl((ovr / sp_m).read_bytes())
        assert not any(fx["opcode"] == 99 for ab in parsed_m["abilities"] for fx in ab["effects"])
    kl_m = {r[1]: r for r in _read_2da_rows(ovr / "KITLIST.2DA")}
    viconi_m = parse_cre_v1((ovr / "VICONI9.CRE").read_bytes())
    assert viconi_m["kit_ids"] == int(kl_m["CBK_SHAR"][9], 16) and viconi_m["levels"] == (8, 0, 0)


# ---------------------------------------------------------------------------
# 5. Idempotent Reinstall & Byte-Exact Uninstall
# ---------------------------------------------------------------------------

def test_05_idempotent_reinstall_and_uninstall(tmp_path: pathlib.Path) -> None:
    game = tmp_path / "game_roundtrip"
    create_fake_game(game, mode="bg2ee")
    ignore = ("weidu.log", "weidu_external", "chriz-bg-kits", "setup-chriz-bg-kits.tp2")
    baseline = _sha256_tree(game, ignore)

    _install_all(game)
    _install_all(game)  # Reinstall all 12 components once more
    ovr = game / "override"
    kl_rows = _read_2da_rows(ovr / "KITLIST.2DA")
    for kname in ("CBKBLDRG", "CBK_STONEFIRE", "CBK_ELEMENTALIST", "CBK_SHAR", "CBK_UMBERLEE", "CBK_ILMATER"):
        assert len([r for r in kl_rows if r[1] == kname]) == 1
    assert len([r for r in _read_2da_rows(ovr / "CBRKPKIT.2DA") if r[0].startswith(("OHTEMPUS_", "CBK_SHAR_"))]) == 0

    _uninstall_all(game)
    after_uninstall = _sha256_tree(game, ignore)
    assert after_uninstall == baseline


# ---------------------------------------------------------------------------
# 6. Mutual Exclusivity Refusal (ArtisansKitpack / BardicWonders)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("conflict", ["artisan", "bardic"])
def test_06_mutual_exclusivity_refuses_install(tmp_path: pathlib.Path, conflict: str) -> None:
    game = tmp_path / f"game_{conflict}"
    create_fake_game(game, mode="bg2ee", conflict_mod=conflict)
    res = run_weidu(
        [
            TP2_FILE.name,
            "--game", str(game),
            "--language", "0",
            "--use-lang", "en_US",
            "--force-install-list", "100",
        ],
        cwd=game,
        check=False,
    )
    log_text = (game / "weidu.log").read_text(encoding="utf-8")
    assert "chriz-bg-kits" not in log_text.lower()
    assert "ArtisansKitpack" in res.stdout or "NOT INSTALLED" in res.stdout or "Skipping" in res.stdout


# ---------------------------------------------------------------------------
# 7. Steam BG2:EE 2.7.3.0 Baldur.exe Pattern Uniqueness
# ---------------------------------------------------------------------------

def _pattern_to_regex(pat: str) -> re.Pattern[bytes]:
    chunks = []
    for i in range(0, len(pat), 2):
        tok = pat[i : i + 2]
        chunks.append(b"." if tok == "??" else re.escape(bytes.fromhex(tok)))
    return re.compile(b"".join(chunks), re.DOTALL)


def test_07_steam_baldur_exe_patterns_unique() -> None:
    assert STEAM_EXE.is_file(), f"Steam Baldur.exe not found at {STEAM_EXE}"
    data = STEAM_EXE.read_bytes()
    db_files = sorted((MOD_DIR / "patterns").glob("*.db"))
    assert len(db_files) == 4
    checked = 0
    for db in db_files:
        for line in db.read_text(encoding="utf-8").splitlines():
            if line.startswith("Pattern="):
                pat = line.split("=", 1)[1].strip()
                matches = list(_pattern_to_regex(pat).finditer(data))
                assert len(matches) == 1, f"{db.name} matched {len(matches)} times (expected 1)"
                checked += 1
    assert checked == 9


# ---------------------------------------------------------------------------
# 8. LuaJIT 2.1 Runtime & Coexistence Tests for All 10 M_CBK*.lua Modules
# ---------------------------------------------------------------------------

def _new_lua_env(tables_2da: dict[str, list[list[str]]] | None = None) -> tuple[lj.LuaRuntime, list, list]:
    lua = lj.LuaRuntime(unpack_returned_tuples=True)
    init_listeners: list = []
    op_listeners: list = []
    tmap = tables_2da or {}

    lua.execute("""
        bit = require("bit")
        EEex_Active = true
        EEex_HookIntegrityWatchdogRegister = {
            RAX=0, RCX=1, RDX=2, R8=3, R9=4, R10=5, R11=6
        }
        EEex_LuaCallReturnType = { Number=1, Boolean=2 }
        function EEex_LShift(a, b) return bit.lshift(a, b) end
        function EEex_BAnd(a, b) return bit.band(a, b) end
        function EEex_BOr(a, b) return bit.bor(a, b) end
        function EEex_TryLabel(name) return 0x140001000 end
        function EEex_Malloc(n) return 0x200000000 end
        function EEex_WriteU8(ptr, val) end
        function EEex_DisableCodeProtection() end
        function EEex_EnableCodeProtection() end
        function EEex_FlattenTable(t) return t end
        function EEex_GenLuaCall() return {} end
        _hooked_calls = {}
        function EEex_HookBeforeAndAfterCallWithLabels(site, ...) table.insert(_hooked_calls, site) end
        function EEex_HookConditionalJumpOnSuccessWithLabels(site, ...) table.insert(_hooked_calls, site) end
        function EEex_HookAfterRestoreWithLabels(site, ...) table.insert(_hooked_calls, site) end
        function EEex_UDToPtr(ud) return ud and ud._ptr or 0 end
        function EEex_PtrToUD(ptr, kind) return ptr end
        function EEex_Utility_IterateCPtrList(list, fn)
            for _, item in ipairs(list or {}) do
                if fn(item) then break end
            end
        end
    """)

    def add_init(fn):
        init_listeners.append(fn)

    def add_op(fn):
        op_listeners.append(fn)

    def load_2da(name):
        if name == "CBRSPVER":
            obj = lua.table_from({"_ptr": 0x9000})
            lua.execute("""
                function _make_ver(t)
                    function t:getAtLabels(col, row) return "1" end
                    return t
                end
            """)
            return lua.eval("_make_ver")(obj)
        rows = tmap.get(name)
        if rows is None:
            return None
        tbl = lua.table_from([lua.table_from(r) for r in rows])
        tbl._ptr = 0x10000 + len(name)
        return tbl

    def row_iter(tbl, include_header):
        n = len(tbl)
        idx = [0]
        def _next(*_args):
            idx[0] += 1
            if idx[0] <= n:
                return tbl[idx[0]]
            return None
        return _next

    lua.globals().EEex_GameState_AddInitializedListener = add_init
    lua.globals().EEex_Opcode_AddListsResolvedListener = add_op
    lua.globals().EEex_Resource_Load2DA = load_2da
    lua.globals().EEex_Resource_Get2DARowTableIterator = row_iter
    return lua, init_listeners, op_listeners


def _load_mod_lua(name: str, subs: dict[str, str | int] | None = None) -> str:
    txt = (MOD_DIR / "lua" / name).read_text(encoding="utf-8")
    for k, v in (subs or {}).items():
        txt = txt.replace(f"%{k}%", str(v))
    return txt


def test_08_lua_runtime_and_coexistence() -> None:
    # 1) M_CBKWPN.lua: PROF/SUBTYPE 1..7, race-lock preservation, and Dual-Classed BARBARIAN unlock
    lua, init_l, _ = _new_lua_env({
        "CBKWPN": [
            ["*", "16417", "PROF", "92", "ALLOW"],
            ["*", "16420", "PROF", "104", "DENY"],
            ["*", "16420", "PROF", "104", "ALLOW"],  # DENY wins over ALLOW
            ["19", "16427", "SUBTYPE", "2", "ALLOW"],  # Stonefire <= Chain Mail
            ["19", "16427", "SUBTYPE", "3", "DENY"],   # Stonefire >= Splint Mail
            ["19", "16427", "SUBTYPE", "4", "ALLOW"],  # Stonefire small/med shield
            ["19", "16427", "SUBTYPE", "5", "DENY"],   # Stonefire tower shield
            ["19", "16427", "SUBTYPE", "7", "ALLOW"],  # Stonefire helmet
            ["11", "16428", "SUBTYPE", "1", "DENY"],   # Elementalist non-robe armor
            ["11", "16428", "SUBTYPE", "6", "ALLOW"],  # Elementalist mage robes
        ]
    })
    lua.execute(_load_mod_lua("M_CBKWPN.lua"))
    for fn in init_l:
        fn()
    g = lua.globals()
    assert g.CBKWeaponUsability.EvaluateRule(3, 16417, 92, 25, 0) == 1
    assert g.CBKWeaponUsability.EvaluateRule(2, 16420, 104, 15, 1) == 0
    # Race-locked item (Dwarf unusable 0x01000000) must NOT be unlocked for Dwarf (race=4)!
    elf_only_hdr = lua.eval("{ notUsableBy = 0x01000000, anim = '3A', minStrength = 5 }")
    assert g.CBKWeaponUsability.EvaluateRule(19, 16427, 0, 2, 0, elf_only_hdr, 4) == 0
    # Normal Chain Mail (3A, Bard-usable) allowed for Dwarf Stonefire; Splint Mail (3A, 0x40) denied
    chain_hdr = lua.eval("{ notUsableBy = 0x00040000, anim = '3A', minStrength = 8 }")
    splint_hdr = lua.eval("{ notUsableBy = 0x00040040, anim = '3A', minStrength = 8 }")
    assert g.CBKWeaponUsability.EvaluateRule(19, 16427, 0, 2, 0, chain_hdr, 4) == 1
    assert g.CBKWeaponUsability.EvaluateRule(19, 16427, 0, 2, 1, splint_hdr, 4) == 0
    # Tower shield (C2 / minStr 15) denied; Medium shield (C4) allowed
    med_shld = lua.eval("{ notUsableBy = 0x00040000, anim = 'C4', minStrength = 12 }")
    twr_shld = lua.eval("{ notUsableBy = 0x00040000, anim = 'C2', minStrength = 15 }")
    assert g.CBKWeaponUsability.EvaluateRule(19, 16427, 0, 12, 0, med_shld, 4) == 1
    assert g.CBKWeaponUsability.EvaluateRule(19, 16427, 0, 12, 1, twr_shld, 4) == 0
    # Elementalist: Mage robe (2W) allowed, Leather armor (2A) denied
    robe_hdr = lua.eval("{ notUsableBy = 0x00000800, anim = '2W', minStrength = 3 }")
    leat_hdr = lua.eval("{ notUsableBy = 0x00040000, anim = '2A', minStrength = 4 }")
    assert g.CBKWeaponUsability.EvaluateRule(11, 16428, 0, 2, 0, robe_hdr, 1) == 1
    assert g.CBKWeaponUsability.EvaluateRule(11, 16428, 0, 2, 1, leat_hdr, 1) == 0
    # Dual-classed Barbarian (0x40000000 -> Fighter/Mage class=7): Mage Robe (Fighter unusable 0x0800, FM usable 0x2000==0) unlocked; Plate Mail (Fighter usable 0x0800==0) stays blocked!
    plate_hdr = lua.eval("{ notUsableBy = 0x00040040, anim = '4A', minStrength = 12 }")
    assert g.CBKWeaponUsability.EvaluateRule(7, 0x40000000, 0, 2, 0, robe_hdr, 1) == 1
    assert g.CBKWeaponUsability.EvaluateRule(7, 0x40000000, 0, 2, 0, plate_hdr, 1) == 0

    # 2) M_CBKKP.lua + M_CBKSP.lua coexistence (restoreSize=7, jmp_fail on use_kit_col, rbx kit_num normalization!)
    kp_src = _load_mod_lua("M_CBKKP.lua")
    assert "jnz use_kit_col" in kp_src and "jz use_kit_col" not in kp_src
    assert "EEex_HookConditionalJumpOnSuccessWithLabels(site, 7," in kp_src
    assert "use_kit_col:\n                #DESTROY_SHADOW_SPACE\n                jmp #L(jmp_fail)" in kp_src
    lua2, init2, _ = _new_lua_env({"CBRKPKIT": [["8", "16425"], ["18", "16425"]]})
    lua2.execute(kp_src)
    lua2.execute(kp_src)
    assert len(init2) == 1
    init2[0]()
    # Baldur.exe strips 0x4000 in rbx (16425 -> 41); both 41 and 16425 must match!
    assert lua2.globals().CBKKitProficiency_ShouldOverride(8, 41) is True
    assert lua2.globals().CBKKitProficiency_ShouldOverride(8, 16425) is True
    assert lua2.globals().CBKKitProficiency_ShouldOverride(18, 41) is True
    assert lua2.globals().CBKKitProficiency_ShouldOverride(8, 99) is False

    lua3, init3, _ = _new_lua_env({
        "CBRSPKIT": [["5", "16384", "CBRIWD7"], ["5", "16398", "CBRBG6"]],
        "CBRIWD7": [["1", "0"]],
        "CBRBG6": [["1", "0"]],
    })
    sp_src = _load_mod_lua("M_CBKSP.lua")
    lua3.execute(sp_src)
    init3[0]()
    assert lua3.globals().CBKSpellProgression_ResolveTable(16384) > 0

    # 3) M_CBKAPR.lua: Global Non-Warrior Proficiency APR from WSPATCK.2DA (incl. True Grandmastery -2 = 1.5!)
    lua4, init4, op4 = _new_lua_env({
        "WSPATCK": [
            ["0", "0", "0"],   # 0 pips -> 0
            ["0", "-1", "1"],  # 1 pip  -> 0
            ["-1", "1", "-2"], # 2 pips -> +0.5
            ["-1", "1", "-2"], # 3 pips -> +0.5
            ["-1", "1", "-2"], # 4 pips -> +0.5
            ["-2", "2", "-3"], # 5 pips -> +1.5 (True Grandmastery!)
        ],
        "CBKAPKIT": [],
    })
    lua4.execute(_load_mod_lua("M_CBKAPR.lua", {"CBK_APR_STATE_ID": 130}))
    init4[0]()
    lua4.execute("""
        function _make_sprite(nClass, baseFlags, nKit, weaponProf, pips, aprKey, markerSet)
            local words = { [0]=0,[1]=0,[2]=0,[3]=0,[4]=0,[5]=0,[6]=0,[7]=0 }
            local mword = math.floor(130 / 32)
            local mmask = bit.lshift(1, 130 % 32)
            if markerSet then words[mword] = mmask end
            local stats = {
                _off = { [0x98] = nKit, [weaponProf] = pips },
                m_nNumberOfAttacks = aprKey,
                m_spellStates = {
                    get = function(self, i) return words[i] or 0 end,
                    set = function(self, i, v) words[i] = v end,
                },
                GetAtOffset = function(self, off) return self._off[off] or 0 end,
            }
            return {
                m_derivedStats = stats,
                m_typeAI = { m_Class = nClass },
                m_baseStats = { m_flags = baseFlags },
                m_equipment = {
                    m_selectedWeapon = 0,
                    m_items = { get = function(self, idx)
                        return { pRes = { pHeader = { proficiencyType = weaponProf } } }
                    end },
                },
            }
        end
    """)
    # Swashbuckler (Thief class=4, kit=0x400C, NOT in CBKAPKIT!) at 2 pips -> 1.5 APR (key 7)
    s_swash2 = lua4.eval("_make_sprite(4, 0, 0x400C, 91, 2, 1, false)")
    op4[0](s_swash2)
    assert s_swash2.m_derivedStats.m_nNumberOfAttacks == 7
    # Swashbuckler at 5 pips under True Grandmastery (-2 => +1.5) -> 2.5 APR (key 8)
    s_swash5 = lua4.eval("_make_sprite(4, 0, 0x400C, 91, 5, 1, false)")
    op4[0](s_swash5)
    assert s_swash5.m_derivedStats.m_nNumberOfAttacks == 8
    # Stonefire Sorcerer (class=19) at 2 pips -> 1.5 APR (key 7); at 1 pip -> stays 1 APR (key 1)
    s_sf2 = lua4.eval("_make_sprite(19, 0, 0x402B, 97, 2, 1, false)")
    op4[0](s_sf2)
    assert s_sf2.m_derivedStats.m_nNumberOfAttacks == 7
    s_sf1 = lua4.eval("_make_sprite(19, 0, 0x402B, 96, 1, 1, false)")
    op4[0](s_sf1)
    assert s_sf1.m_derivedStats.m_nNumberOfAttacks == 1
    # Style proficiency 114 ignored; Monk (class=20) & Warrior/Cleric (class=8) & CBR_TEMPUS_SPEC_APR marker ignored
    s_style = lua4.eval("_make_sprite(5, 0, 0x400D, 114, 3, 1, false)")
    op4[0](s_style)
    assert s_style.m_derivedStats.m_nNumberOfAttacks == 1
    s_monk = lua4.eval("_make_sprite(20, 0, 0x4000, 91, 2, 2, false)")
    op4[0](s_monk)
    assert s_monk.m_derivedStats.m_nNumberOfAttacks == 2
    s_marked = lua4.eval("_make_sprite(3, 0, 16417, 92, 2, 7, true)")
    op4[0](s_marked)
    assert s_marked.m_derivedStats.m_nNumberOfAttacks == 7

    # 4) M_CBKSTR.lua + M_CBKDCN.lua
    lua5, _, _ = _new_lua_env()
    lua5.execute("CBMStrength = { registered = true }")
    lua5.execute(_load_mod_lua("M_CBKSTR.lua", {"CBM_STR_FLOOR_STATE": 129, "CBK_STR_CLAMP_1_STATE": 131}))
    s_clamp = lua5.eval("{ m_derivedStats = { m_nSTR = -2, GetSpellState = function(self, id) return id == 131 and 1 or 0 end } }")
    lua5.globals().CBMStrength.ClampStrOne(s_clamp)
    assert s_clamp.m_derivedStats.m_nSTR == 1

    lua6, init6, op6 = _new_lua_env({"CBKDCNAM": [["7", "8", "16385", "7001", "7002"]]})
    lua6.execute(_load_mod_lua("M_CBKDCN.lua"))
    init6[0]()
    s_dc = lua6.eval("{ m_baseStats = { m_flags = 8, m_mageSpecUpperWord = 0, m_mageSpecialization = 16385 }, m_typeAI = { m_Class = 7 }, m_derivedStats = { m_nClassTypeOverrideMixed = -1, m_nClassTypeOverrideLower = -1 } }")
    op6[0](s_dc)
    assert s_dc.m_derivedStats.m_nClassTypeOverrideMixed == 7001

    # 5) M_CBKCMB.lua + M_CBKRAC.lua + M_CBKSF.lua + M_CBKELM.lua integrated runtime test
    lua7, init7, op7 = _new_lua_env({
        "CLSRCREQ": [
            ["MAGE", "1", "1", "1", "0", "1", "0", "0", "1"],
            ["FIGHTER", "1", "1", "1", "1", "1", "1", "1", "1"],
            ["DRUID", "1", "1", "1", "0", "1", "0", "1", "0"],
        ]
    })
    rest_listeners: list = []
    loaded_listeners: list = []
    lua7.globals().EEex_Sprite_AddQuickListCountsResetListener = lambda fn: rest_listeners.append(fn)
    lua7.globals().EEex_Sprite_AddLoadedListener = lambda fn: loaded_listeners.append(fn)

    lua7.execute(_load_mod_lua("M_CBKCMB.lua"))
    lua7.execute(_load_mod_lua("M_CBKRAC.lua", {
        "CBK_RAC_RESOLVED_STATE": 140,
        "CBK_EXTRA_RACE_IDS": 'state.raceIdToCol[161] = "HOBGOBLIN"',
    }))
    lua7.execute(_load_mod_lua("M_CBKSF.lua", {
        "CBK_STONEFIRE_KIT_IDS": 0x402B,
        "CBK_STONEFIRE_ARMOR_STATE": 141,
    }))
    lua7.execute(_load_mod_lua("M_CBKELM.lua", {
        "CBK_ELM_KIT_IDS": 0x402C,
        "CBK_STATE_ELM_FIRE": 142,
        "CBK_STATE_ELM_WATER": 143,
        "CBK_STATE_ELM_AIR": 144,
        "CBK_STATE_ELM_EARTH": 145,
        "CBK_STATE_ELM_HLA": 146,
        "CBK_STATE_ELM_RESOLVED": 147,
        "CBK_ELM_EXTRA_CURES": "",
    }))
    for fn in init7:
        fn()
    g7 = lua7.globals()
    assert g7.CBKCombat.installed is True and g7.CBKCombat.hasListeners is True

    # M_CBKRAC: Human Second Wind (<25% HP -> +20% HP, Fatigue=0, once/rest via LOCALS CBKSWND, reset on rest)
    human_sp = lua7.eval("""
        {
            _locals = {},
            _fx = {},
            m_typeAI = { m_Race = 1 },
            m_baseStats = { m_generalState = 0, m_hitPoints = 20, m_fatigue = 7 },
            m_derivedStats = { m_nMaxHitPoints = 100, m_nFatigue = 7 },
            applyEffect = function(self, eff) table.insert(self._fx, eff) end,
        }
    """)
    g7.CBKCombat_OnDamageAfter({}, nil_src := 0, human_sp)
    assert human_sp.m_baseStats.m_hitPoints == 40
    assert human_sp.m_baseStats.m_fatigue == 0
    assert human_sp._locals["CBKSWND"] == 1
    # Dropping below 25% again before rest does NOT re-trigger
    human_sp.m_baseStats.m_hitPoints = 15
    g7.CBKCombat_OnDamageAfter({}, nil_src, human_sp)
    assert human_sp.m_baseStats.m_hitPoints == 15
    # After rest reset listener, triggers again!
    rest_listeners[0](human_sp)
    assert human_sp._locals["CBKSWND"] == 0
    g7.CBKCombat_OnDamageAfter({}, nil_src, human_sp)
    assert human_sp.m_baseStats.m_hitPoints == 35

    # M_CBKRAC: Elf +1 Save vs. Spell, Half-Elf +10 Lore, Halfling Finesse (19 DEX > 14 STR vs 21 STR Giant Belt, ranged actionType=2 rejected)
    lua7.execute("""
        _mock_mem_u8 = {}
        function EEex_ReadU8(addr) return _mock_mem_u8[addr] end
        function _make_rac_sp(race, str, strEx, dex, prof, actionType, abNum)
            local words = { [0]=0,[1]=0,[2]=0,[3]=0,[4]=0,[5]=0,[6]=0,[7]=0 }
            local at = actionType or 1
            local an = abNum or 0
            return {
                m_typeAI = { m_Race = race },
                m_derivedStats = {
                    m_nSTR = str, m_nSTRExtra = strEx, m_nDEX = dex,
                    m_nSaveVSSpell = 10, m_nLore = 20,
                    m_nMeleeTHAC0Bonus = 0, m_nMeleeDamageBonus = 0,
                    m_spellStates = {
                        get = function(self, i) return words[i] or 0 end,
                        set = function(self, i, v) words[i] = v end,
                    },
                },
                m_equipment = {
                    m_selectedWeapon = 0, m_selectedWeaponAbility = an,
                    m_items = { get = function(self, i)
                        return {
                            getAbility = function(s, a) return { actionType = at } end,
                            pRes = { pHeader = { _ptr = 0x50000, abilityOffset = 0x72, proficiencyType = prof } },
                        }
                    end },
                },
            }
        end
    """)
    sp_elf = lua7.eval("_make_rac_sp(2, 12, 0, 18, 90)")
    g7.CBKRaces.ApplyRacialStats(sp_elf)
    g7.CBKRaces.ApplyRacialStats(sp_elf)  # idempotent!
    assert sp_elf.m_derivedStats.m_nSaveVSSpell == 9

    sp_he = lua7.eval("_make_rac_sp(3, 12, 0, 16, 90)")
    g7.CBKRaces.ApplyRacialStats(sp_he)
    assert sp_he.m_derivedStats.m_nLore == 30

    # Halfling 19 DEX (+2/+4) & 14 STR (0/0) with melee Dagger (96, actionType=1) -> +2 hit / +4 dmg
    sp_hl_dex = lua7.eval("_make_rac_sp(5, 14, 0, 19, 96, 1, 0)")
    g7.CBKRaces.ApplyRacialStats(sp_hl_dex)
    assert sp_hl_dex.m_derivedStats.m_nMeleeTHAC0Bonus == 2
    assert sp_hl_dex.m_derivedStats.m_nMeleeDamageBonus == 4
    # Halfling 19 DEX with ranged Throwing Dagger (actionType=2) -> +0/+0!
    sp_hl_ranged = lua7.eval("_make_rac_sp(5, 14, 0, 19, 96, 2, 0)")
    g7.CBKRaces.ApplyRacialStats(sp_hl_ranged)
    assert sp_hl_ranged.m_derivedStats.m_nMeleeTHAC0Bonus == 0
    assert sp_hl_ranged.m_derivedStats.m_nMeleeDamageBonus == 0
    # Halfling secondary ability (abNum=1): reads raw EEex_ReadU8(0x50000 + 0x72 + 0x38*1) = 2 (ranged) -> +0/+0!
    lua7.execute("_mock_mem_u8[0x50000 + 0x72 + 0x38] = 2")
    sp_hl_ab1_rng = lua7.eval("_make_rac_sp(5, 14, 0, 19, 96, 1, 1)")
    g7.CBKRaces.ApplyRacialStats(sp_hl_ab1_rng)
    assert sp_hl_ab1_rng.m_derivedStats.m_nMeleeTHAC0Bonus == 0
    # Halfling 19 DEX & 21 STR Giant Strength Belt (+4/+9) -> DEX <= STR -> +0/+0 (zero double-stacking!)
    sp_hl_belt = lua7.eval("_make_rac_sp(5, 21, 0, 19, 96, 1, 0)")
    g7.CBKRaces.ApplyRacialStats(sp_hl_belt)
    assert sp_hl_belt.m_derivedStats.m_nMeleeTHAC0Bonus == 0
    assert sp_hl_belt.m_derivedStats.m_nMeleeDamageBonus == 0

    # M_CBKRAC: Dual-Class target filter (Dwarf race=4 cannot dual into MAGE=1 or DRUID=11, keeps FIGHTER=2; Hobgoblin=161 filters DRUID=11)
    dc_list = lua7.eval("{ { id = 1 }, { id = 2 }, { id = 11 } }")
    g7.CBKRaces.FilterDualClassTable(dc_list, 4)
    assert [dc_list[i].id for i in range(1, len(dc_list) + 1)] == [2]
    dc_hb = lua7.eval("{ { id = 1 }, { id = 11 } }")
    g7.CBKRaces.FilterDualClassTable(dc_hb, 161)
    assert [dc_hb[i].id for i in range(1, len(dc_hb) + 1)] == [1]

    # M_CBKSF: Illusion spell filter (primaryType == 5 disabled; Evocation == 6 stays enabled) + OnSpriteLoaded bit restore
    g7.CBKStonefire.mockSpellSchools = lua7.eval("{ SPWI106 = 5, SPWI201 = 5, SPWI103 = 8, SPWI304 = 6 }")
    choose = lua7.eval("""
        {
            { key = "SPWI106", enabled = true },
            { key = "SPWI201", enabled = true },
            { key = "SPWI103", enabled = true },
            { key = "SPWI304", enabled = true },
        }
    """)
    assert g7.CBKStonefire.FilterChooseSpells(choose, 0x402B) == 2
    assert choose[1].enabled is False and choose[2].enabled is False
    assert choose[3].enabled is True and choose[4].enabled is True

    sf_loaded_sp = lua7.eval("""
        (function()
            local words = { [0]=0,[1]=0,[2]=0,[3]=0,[4]=0,[5]=0,[6]=0,[7]=0 }
            return {
                m_timedEffectList = { { m_effectId = 328, m_special = 1, m_dWFlags = 141, m_durationType = 9 } },
                m_derivedStats = {
                    m_spellStates = {
                        get = function(self, i) return words[i] or 0 end,
                        set = function(self, i, v) words[i] = v end,
                    },
                },
            }
        end)()
    """)
    loaded_listeners[0](sf_loaded_sp)
    assert (sf_loaded_sp.m_derivedStats.m_spellStates.get(sf_loaded_sp.m_derivedStats.m_spellStates, 141 // 32) & (1 << (141 % 32))) != 0

    # M_CBKELM: Non-additive floors (Hardiness 40% slashing stays 40%, Crushing 0% raised to 25% in Water Tier 4),
    # shared daily form charge sync across CBKELF1..4, and Tidal Healing swap preserving spent/unspent m_flags!
    elm_sp = lua7.eval("""
        {
            _magicWeaponRes = "CBKEF24",
            _spellStates = { [143] = true, [146] = true },
            m_derivedStats = {
                m_nSTR = 14, m_nSTRExtra = 0, m_nDEX = 22,
                m_nResistCold = 20, m_nResistFire = 0,
                m_nResistSlashing = 40, m_nResistCrushing = 0, m_nResistPiercing = 10, m_nResistMissile = 0,
            },
            m_memorizedSpellsInnate = {
                {
                    { m_spellId = "CBKELF1", m_flags = 1 }, { m_spellId = "CBKELF1", m_flags = 1 }, { m_spellId = "CBKELF1", m_flags = 0 },
                    { m_spellId = "CBKELF2", m_flags = 1 }, { m_spellId = "CBKELF2", m_flags = 0 }, { m_spellId = "CBKELF2", m_flags = 0 },
                    { m_spellId = "CBKELF3", m_flags = 1 }, { m_spellId = "CBKELF3", m_flags = 1 }, { m_spellId = "CBKELF3", m_flags = 1 },
                    { m_spellId = "CBKELF4", m_flags = 1 }, { m_spellId = "CBKELF4", m_flags = 1 }, { m_spellId = "CBKELF4", m_flags = 1 },
                }
            },
            m_memorizedSpellsPriest = {
                { { m_spellId = "SPPR103", m_flags = 1 }, { m_spellId = "SPPR103", m_flags = 0 } },
                {},
                {},
                { { m_spellId = "SPPR401", m_flags = 1 } },
            },
        }
    """)
    assert g7.CBKElementalist.OnListsResolved(elm_sp) is True
    assert elm_sp.m_derivedStats.m_nSTR == 21
    assert elm_sp.m_derivedStats.m_nDEX == 22  # 22 > 19 floor -> NOT downgraded!
    assert elm_sp.m_derivedStats.m_nResistCold == 100
    assert elm_sp.m_derivedStats.m_nResistFire == 50
    assert elm_sp.m_derivedStats.m_nResistSlashing == 40  # Hardiness 40% > 25% floor -> NOT stacked to 65%!
    assert elm_sp.m_derivedStats.m_nResistCrushing == 25
    # Shared charges synced down to minReady = 1 across all 4 forms
    inn = elm_sp.m_memorizedSpellsInnate[1]
    ready_by_form = {}
    for i in range(1, len(inn) + 1):
        fnm = inn[i].m_spellId
        ready_by_form[fnm] = ready_by_form.get(fnm, 0) + (inn[i].m_flags & 1)
    assert ready_by_form == {"CBKELF1": 1, "CBKELF2": 1, "CBKELF3": 1, "CBKELF4": 1}
    # Tidal Healing swapped SPPR103 -> CBKWTH1 (preserving ready=1 and spent=0!) and reverted on leaving Water Form
    assert elm_sp.m_memorizedSpellsPriest[1][1].m_spellId == "CBKWTH1" and elm_sp.m_memorizedSpellsPriest[1][1].m_flags == 1
    assert elm_sp.m_memorizedSpellsPriest[1][2].m_spellId == "CBKWTH1" and elm_sp.m_memorizedSpellsPriest[1][2].m_flags == 0
    elm_sp._magicWeaponRes = None
    elm_sp._spellStates[143] = False
    g7.CBKElementalist.OnListsResolved(elm_sp)
    assert elm_sp.m_memorizedSpellsPriest[1][1].m_spellId == "SPPR103" and elm_sp.m_memorizedSpellsPriest[1][2].m_flags == 0

    # Primal Penetration via CBKCombat: Fire Form halves MR on CheckSave & caps non-ELEMENTAL Fire res at 70%,
    # leaves ELEMENTAL (RACE=145) at 100%, and restores target stats immediately after!
    elm_sp._magicWeaponRes = "CBKEF14"
    elm_sp._spellStates[142] = True
    demon_tgt = lua7.eval("{ _race = 121, m_derivedStats = { m_nResistMagic = 80, m_nResistFire = 100, m_nResistCrushing = 60 } }")
    elem_tgt = lua7.eval("{ _race = 145, m_derivedStats = { m_nResistMagic = 50, m_nResistFire = 100 } }")
    fire_eff = lua7.eval("{ m_effectId = 12, m_dWFlags = 0x00080000, m_sourceRes = 'CBKEL73', m_sourceType = 1 }")
    fire_eff._sourceSprite = elm_sp

    g7.CBKCombat_OnCheckSaveBefore(fire_eff, demon_tgt)
    assert demon_tgt.m_derivedStats.m_nResistMagic == 40
    g7.CBKCombat_OnCheckSaveAfter(fire_eff, demon_tgt)
    assert demon_tgt.m_derivedStats.m_nResistMagic == 80

    g7.CBKCombat_OnDamageBefore(fire_eff, elm_sp, demon_tgt)
    assert demon_tgt.m_derivedStats.m_nResistFire == 70
    g7.CBKCombat_OnDamageAfter(fire_eff, elm_sp, demon_tgt)
    assert demon_tgt.m_derivedStats.m_nResistFire == 100

    g7.CBKCombat_OnDamageBefore(fire_eff, elm_sp, elem_tgt)
    assert elem_tgt.m_derivedStats.m_nResistFire == 100  # RACE == ELEMENTAL (145) immune!
    g7.CBKCombat_OnDamageAfter(fire_eff, elm_sp, elem_tgt)

    # Earth Form Tectonic Strikes: melee Crushing hit from CBKEF44 reduces Crushing res 60% -> 35% and restores 60%
    elm_sp._magicWeaponRes = "CBKEF44"
    crush_eff = lua7.eval("{ m_effectId = 12, m_dWFlags = 0x00000000, m_sourceRes = 'CBKEF44', m_sourceType = 2 }")
    g7.CBKCombat_OnDamageBefore(crush_eff, elm_sp, demon_tgt)
    assert demon_tgt.m_derivedStats.m_nResistCrushing == 35
    g7.CBKCombat_OnDamageAfter(crush_eff, elm_sp, demon_tgt)
    assert demon_tgt.m_derivedStats.m_nResistCrushing == 60

    # 6) M_CBKSHR.lua (Shadow Weave Magic -2 Save on Enchantment/Illusion/Necromancy/CBKSHR2) + M_CBKILM.lua (25% Phys-DR floor)
    lua7.execute(_load_mod_lua("M_CBKSHR.lua", {
        "CBK_SHAR_KIT_IDS": 0x4031,
        "CBK_STATE_SHAR_WEAVE": 148,
    }))
    lua7.execute(_load_mod_lua("M_CBKILM.lua", {
        "CBK_STATE_ILMATER_ENDURE": 149,
        "CBK_STATE_ILM_RESOLVED": 150,
    }))
    g7.CBKShar.mockSpellSchools = lua7.eval("{ SPPR102 = 4, SPWI201 = 5, SPPR313 = 7, SPWI304 = 6 }")
    shar_sp = lua7.eval("{ _spellStates = { [148] = true }, _kitIds = 0x4031 }")
    other_sp = lua7.eval("{ _spellStates = { [148] = false }, _kitIds = 0x4000 }")
    for sres, expect_pen in [("SPPR102", -2), ("SPWI201", -2), ("SPPR313", -2), ("CBKSHR2", -2), ("SPWI304", 0)]:
        eff = lua7.eval(f"{{ m_sourceRes = '{sres}', m_sourceType = 1, m_saveMod = 3 }}")
        eff._sourceSprite = shar_sp
        g7.CBKCombat_OnCheckSaveBefore(eff, demon_tgt)
        assert eff.m_saveMod == 3 + expect_pen, f"{sres}: got {eff.m_saveMod}"
        g7.CBKCombat_OnCheckSaveAfter(eff, demon_tgt)
        assert eff.m_saveMod == 3
    # Item source (m_sourceType == 2) and non-Shar caster stay untouched
    item_eff = lua7.eval("{ m_sourceRes = 'SPPR102', m_sourceType = 2, m_saveMod = 1 }")
    item_eff._sourceSprite = shar_sp
    g7.CBKCombat_OnCheckSaveBefore(item_eff, demon_tgt)
    assert item_eff.m_saveMod == 1
    g7.CBKCombat_OnCheckSaveAfter(item_eff, demon_tgt)
    non_shar_eff = lua7.eval("{ m_sourceRes = 'CBKSHR2', m_sourceType = 1, m_saveMod = 1 }")
    non_shar_eff._sourceSprite = other_sp
    g7.CBKCombat_OnCheckSaveBefore(non_shar_eff, demon_tgt)
    assert non_shar_eff.m_saveMod == 1
    g7.CBKCombat_OnCheckSaveAfter(non_shar_eff, demon_tgt)
    # Non-sprite trap source via m_sourceId must be rejected by EEex_GameObject_IsSprite without touching m_saveMod
    lua7.execute("""
        _trap_obj = { _isTrap = true, _spellStates = { [148] = true } }
        function EEex_GameObject_Get(id) return id == 999 and _trap_obj or nil end
        function EEex_GameObject_IsSprite(obj, allowDead) return obj ~= _trap_obj end
    """)
    trap_eff = lua7.eval("{ m_sourceId = 999, m_sourceRes = 'SPPR102', m_sourceType = 1, m_saveMod = 2 }")
    g7.CBKCombat_OnCheckSaveBefore(trap_eff, demon_tgt)
    assert trap_eff.m_saveMod == 2
    g7.CBKCombat_OnCheckSaveAfter(trap_eff, demon_tgt)

    # M_CBKILM.lua: 25% Physical DR floor, non-additive with 40% Hardiness, idempotent via CBK_ILM_RESOLVED
    ilm_sp = lua7.eval("""
        {
            _spellStates = { [149] = true },
            m_derivedStats = {
                m_nResistSlashing = 40, m_nResistCrushing = 0,
                m_nResistPiercing = 10, m_nResistMissile = 25,
            },
        }
    """)
    assert g7.CBKIlmater.OnListsResolved(ilm_sp) is True
    assert ilm_sp.m_derivedStats.m_nResistSlashing == 40   # 40% > 25% -> NOT stacked to 65%!
    assert ilm_sp.m_derivedStats.m_nResistCrushing == 25   # 0% -> 25% floor
    assert ilm_sp.m_derivedStats.m_nResistPiercing == 25   # 10% -> 25% floor
    assert ilm_sp.m_derivedStats.m_nResistMissile == 25
    assert g7.CBKIlmater.OnListsResolved(ilm_sp) is False  # Idempotent via CBK_ILM_RESOLVED!
    ilm_inactive = lua7.eval("{ _spellStates = { [149] = false }, m_derivedStats = { m_nResistSlashing = 0, m_nResistCrushing = 0, m_nResistPiercing = 0, m_nResistMissile = 0 } }")
    assert g7.CBKIlmater.OnListsResolved(ilm_inactive) is False
    assert ilm_inactive.m_derivedStats.m_nResistSlashing == 0


# ---------------------------------------------------------------------------
# 9. BGSE op402 / op214 Scanner Audit
# ---------------------------------------------------------------------------

def test_09_bgse_no_unrecognized_op402_or_op214(tmp_path: pathlib.Path) -> None:
    for spl_path in sorted((MOD_DIR / "res").glob("*.SPL")):
        hits = check_spl_has_opcodes(spl_path, {402, 214})
        assert not hits, f"{spl_path.name} contains forbidden opcodes for BGSE: {hits}"
    for eff_path in sorted((MOD_DIR / "res").glob("*.EFF")):
        eff = read_eff_v2(eff_path.read_bytes())
        assert eff["opcode"] not in (402, 214), f"{eff_path.name} uses forbidden opcode {eff['opcode']}"

    game = tmp_path / "game_bgse"
    create_fake_game(game, mode="bg2ee")
    _install_all(game)
    for spl_path in sorted((game / "override").glob("*.SPL")):
        hits = check_spl_has_opcodes(spl_path, {402, 214})
        assert not hits, f"Installed {spl_path.name} contains forbidden opcodes for BGSE: {hits}"
