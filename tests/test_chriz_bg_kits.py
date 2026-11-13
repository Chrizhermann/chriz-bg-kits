"""Comprehensive verification suite for chriz-bg-kits v0.1.0."""

from __future__ import annotations

import hashlib
import pathlib
import re
import shutil
import subprocess
import sys

import lupa.luajit21 as lj
import pytest

from .fakegame import MOD_DIR, REPO_ROOT, TP2_FILE, create_fake_game
from .harness import WEIDU_EXE, run_weidu
from .ie import check_spl_has_opcodes, parse_cre_v1, parse_spl, read_eff_v2

STEAM_EXE = pathlib.Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Baldur's Gate II Enhanced Edition\Baldur.exe"
)


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
    # Skip 2DA header lines (line0=2DA V1.0, line1=default, line2=col headers)
    return [ln.split() for ln in lines[3:]]


def _install_all(game_dir: pathlib.Path, extra: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    args = [
        TP2_FILE.name,
        "--game", str(game_dir),
        "--language", "0",
        "--use-lang", "en_US",
        *(extra or []),
        "--force-install-list", "100", "200", "300", "310", "320",
    ]
    return run_weidu(args, cwd=game_dir)


def _uninstall_all(game_dir: pathlib.Path) -> subprocess.CompletedProcess[str]:
    args = [
        TP2_FILE.name,
        "--game", str(game_dir),
        "--language", "0",
        "--use-lang", "en_US",
        "--force-uninstall-list", "320", "310", "300", "200", "100",
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
    assert "41 files" in res.stdout


# ---------------------------------------------------------------------------
# 2. WeiDU Parse Check
# ---------------------------------------------------------------------------

def test_02_weidu_parse_check() -> None:
    targets: list[tuple[pathlib.Path, str]] = [(TP2_FILE, "tp2")]
    targets.extend((p, "tpa") for p in sorted((MOD_DIR / "lib").glob("*.tpa")))
    for path, kind in targets:
        res = run_weidu(["--nogame", "--parse-check", kind, str(path)], cwd=REPO_ROOT)
        assert "successfully parsed" in res.stdout


# ---------------------------------------------------------------------------
# 3. Full Clean Install (BG2:EE & EET with extra race column)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mode,extra_race", [("bg2ee", False), ("eet", True)])
def test_03_clean_install_all_components(tmp_path: pathlib.Path, mode: str, extra_race: bool) -> None:
    game = tmp_path / f"game_{mode}"
    create_fake_game(game, mode=mode, extra_race_col=extra_race)
    _install_all(game)
    ovr = game / "override"

    # Comp 100: Kernel
    for db in ("CBKWPN.db", "CBKKP.db", "CBKSP.db"):
        assert (game / "EEex_scripts" / "extra_pattern_dbs" / db).is_file()
    for tbl in ("CBKWPN", "CBKAPKIT", "CBRKPKIT", "CBRSPVER", "CBRSPKIT", "CBRBG6", "CBRIWD7", "CBRIWD8"):
        assert (ovr / f"{tbl}.2DA").is_file()
    for lua in ("M_CBKWPN.lua", "M_CBKKP.lua", "M_CBKAPR.lua", "M_CBKSP.lua", "M_CBKSTR.lua", "M_CBKDCN.lua"):
        text = (ovr / lua).read_text(encoding="utf-8")
        assert not re.search(r"%[A-Z0-9_]+%", text), f"Unresolved %VAR% in {lua}"

    splstate_text = (ovr / "SPLSTATE.IDS").read_text(encoding="utf-8")
    for sym in ("CBM_STR_FLOOR", "CBR_TEMPUS_SPEC_APR", "CBK_STR_CLAMP_1"):
        assert sym in splstate_text

    # Comp 200: Tempus
    ohtempus = (ovr / "OHTEMPUS.2DA").read_text(encoding="utf-8")
    assert "AP_CDHLYSYM" in ohtempus
    assert "AP_CBKTMP1" in ohtempus
    assert "AP_CBKTMDV" in ohtempus
    assert "GA_OHTMPS1" in ohtempus
    assert "GA_OHTMPS2" in ohtempus
    for kind, expected_proj in (("D", 162), ("E", 171)):
        for tier in ("1", "2", "3"):
            spl = parse_spl((ovr / f"CBKTM{tier}{kind}.SPL").read_bytes())
            assert len(spl["casting_effects"]) >= 1
            assert spl["abilities"][0]["projectile"] == expected_proj

    ohtmps1 = parse_spl((ovr / "OHTMPS1.SPL").read_bytes())
    excl = {fx["resource"] for ab in ohtmps1["abilities"] for fx in ab["effects"] if fx["opcode"] == 206}
    assert {"SPPR412", "SPPR425", "SPPR507", "SPPR513", "SPPR525", "SPWI603"}.issubset(excl)

    cbktmdv = parse_spl((ovr / "CBKTMDV.SPL").read_bytes())
    removed = {fx["resource"] for ab in cbktmdv["abilities"] for fx in ab["effects"] if fx["opcode"] == 172}
    assert {"SPPR113", "SPPR415"}.issubset(removed)
    assert "SPPR201" not in removed
    assert (ovr / "CBKTD0.EFF").is_file() and (ovr / "CBKTD1.EFF").is_file()

    branwe = parse_cre_v1((ovr / "BRANWE.CRE").read_bytes())
    assert branwe["kit_ids"] == 0x4029
    assert branwe["profs"].get(92, 0) >= 1

    # Comp 300: Bloodrager (standalone) & Vanilla Berserker / Korgan untouched
    kitlist_rows = _read_2da_rows(ovr / "KITLIST.2DA")
    bld_rows = [r for r in kitlist_rows if r[1] == "CBKBLDRG"]
    assert len(bld_rows) == 1
    assert bld_rows[0][0] == "42"
    assert int(bld_rows[0][9], 16) == 0x402A
    assert (ovr / "CBKBR0.2DA").is_file()
    lucbk_rows = _read_2da_rows(ovr / "LUCBK.2DA")
    lucbk_abs = {r[1] for r in lucbk_rows}
    assert "GA_SPCL907" in lucbk_abs and "AP_CBKBRH1" in lucbk_abs

    wp_lines = (ovr / "WEAPPROF.2DA").read_text(encoding="utf-8").splitlines()
    wp_hdr = wp_lines[2].split()
    assert "CBKBLDRG" in wp_hdr
    kf_h = [r[1] for r in _read_2da_rows(ovr / "K_F_H.2DA")]
    kf_d = [r[1] for r in _read_2da_rows(ovr / "K_F_D.2DA")]
    assert bld_rows[0][0] in kf_h and bld_rows[0][0] in kf_d
    if extra_race:
        assert "HOBGOBLIN" in wp_hdr
        kf_hg = [r[1] for r in _read_2da_rows(ovr / "K_F_HG.2DA")]
        assert bld_rows[0][0] in kf_hg

    rc_rows = {r[0]: r[1:] for r in _read_2da_rows(ovr / "CLSRCREQ.2DA")}
    assert "CBKBLDRG" in rc_rows
    assert rc_rows["CBKBLDRG"] == rc_rows["BERSERKER"]
    assert len(rc_rows["CBKBLDRG"]) == (8 if extra_race else 7)

    ct_rows = {r[0]: r[1:] for r in _read_2da_rows(ovr / "CLASTEXT.2DA")}
    assert ct_rows["CBKBLDRG"][0] == "2" and ct_rows["CBKBLDRG"][1] == "42"
    kl_by_name = {r[1]: r for r in kitlist_rows}
    assert ct_rows["CBKBLDRG"][3] == kl_by_name["CBKBLDRG"][4]
    assert ct_rows["OHTEMPUS"][3] == kl_by_name["OHTEMPUS"][4] and ct_rows["OHTEMPUS"][3] != "18"

    cbkwpn_rows = _read_2da_rows(ovr / "CBKWPN.2DA")
    bld_dec = str(int(bld_rows[0][9], 16))
    deny_profs = {r[4] for r in cbkwpn_rows if r[2] == bld_dec and r[5] == "DENY"}
    assert deny_profs == {"103", "104", "105", "106", "107"}

    korgan = parse_cre_v1((ovr / "KORGAN8.CRE").read_bytes())
    assert korgan["kit_ids"] == 0x4001 and korgan["profs"].get(92) == 5

    # Comp 310: Bards
    lucbkj_rows = _read_2da_rows(ovr / "LUCBKJ.2DA")
    spcl920_rows = [r for r in lucbkj_rows if "SPCL920" in r[1]]
    jes3_rows = [r for r in lucbkj_rows if r[1] == "AP_CBKJES3"]
    assert len(spcl920_rows) == 0 and len(jes3_rows) == 1
    luabbr = {r[0]: r[1] for r in _read_2da_rows(ovr / "LUABBR.2DA")}
    assert luabbr["JESTER"] == "CBKJ"

    skald_idx = wp_hdr.index("SKALD") + 1
    for line in wp_lines[3:]:
        parts = line.split()
        if parts and int(parts[1]) in (89, 90, 92, 103, 114, 115):
            assert parts[skald_idx] == "2", f"Skald pip mismatch on {parts}"

    cbrsp = {r[0]: r[3] for r in _read_2da_rows(ovr / "CBRSPKIT.2DA")}
    assert cbrsp["BARD"] == "CBRIWD7"
    assert cbrsp["JESTER"] == "CBRIWD7"
    assert cbrsp["BLADE"] == "CBRBG6"
    assert cbrsp["SKALD"] == "CBRBG6"
    assert ct_rows["JESTER"][3] == kl_by_name["JESTER"][4] and ct_rows["JESTER"][3] != "18"
    assert ct_rows["SKALD"][3] == kl_by_name["SKALD"][4] and ct_rows["SKALD"][3] != "18"

    # Comp 320: Core fixes
    for sp in ("SPCL907.SPL", "SPWISH12.SPL"):
        parsed = parse_spl((ovr / sp).read_bytes())
        ops = [fx["opcode"] for ab in parsed["abilities"] for fx in ab["effects"]]
        assert not any(o in (27, 28, 29, 30, 31, 84, 85) for o in ops)
        for fx in parsed["abilities"][0]["effects"]:
            if fx["opcode"] in (86, 87, 88, 89):
                assert fx["p1"] == 40
    spcl904 = parse_spl((ovr / "SPCL904.SPL").read_bytes())
    assert any(fx["opcode"] == 146 and fx["resource"] == "CBKRSMG" for ab in spcl904["abilities"] for fx in ab["effects"])
    assert read_eff_v2((ovr / "SPCL902.EFF").read_bytes())["min_level"] == 12
    assert read_eff_v2((ovr / "SPCL903.EFF").read_bytes())["min_level"] == 16
    assert read_eff_v2((ovr / "ARCHSLOW.EFF").read_bytes())["opcode"] == 326
    assert read_eff_v2((ovr / "ARCHSLOW.EFF").read_bytes())["resource"] == "CBKARCSL"
    dcn_rows = _read_2da_rows(ovr / "CBKDCNAM.2DA")
    assert any(r[1] == "7" and r[2] == "8" and r[3] == "16385" for r in dcn_rows)  # Berserker -> FM


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


# ---------------------------------------------------------------------------
# 5. Idempotent Reinstall & Byte-Exact Uninstall
# ---------------------------------------------------------------------------

def test_05_idempotent_reinstall_and_uninstall(tmp_path: pathlib.Path) -> None:
    game = tmp_path / "game_roundtrip"
    create_fake_game(game, mode="bg2ee")
    ignore = ("weidu.log", "weidu_external", "chriz-bg-kits", "setup-chriz-bg-kits.tp2")
    baseline = _sha256_tree(game, ignore)

    _install_all(game)
    # Reinstall all components once more
    run_weidu(
        [
            TP2_FILE.name,
            "--game", str(game),
            "--language", "0",
            "--use-lang", "en_US",
            "--force-install-list", "100", "200", "300", "310", "320",
        ],
        cwd=game,
    )
    ovr = game / "override"
    assert len([r for r in _read_2da_rows(ovr / "KITLIST.2DA") if r[1] == "CBKBLDRG"]) == 1
    assert len([r for r in _read_2da_rows(ovr / "CBRKPKIT.2DA") if r[0].startswith("OHTEMPUS_")]) == 2

    _uninstall_all(game)
    after_uninstall = _sha256_tree(game, ignore)
    # Empty extra_pattern_dbs files created by MKDIR won't affect file hashes
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
    # WeiDU skips unsatisfied REQUIRE_PREDICATE component without installing into weidu.log
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
    if not STEAM_EXE.is_file():
        pytest.skip(f"Steam Baldur.exe not found at {STEAM_EXE}")
    data = STEAM_EXE.read_bytes()
    db_files = sorted((MOD_DIR / "patterns").glob("*.db"))
    assert len(db_files) == 3
    checked = 0
    for db in db_files:
        for line in db.read_text(encoding="utf-8").splitlines():
            if line.startswith("Pattern="):
                pat = line.split("=", 1)[1].strip()
                matches = list(_pattern_to_regex(pat).finditer(data))
                assert len(matches) == 1, f"{db.name} matched {len(matches)} times (expected 1)"
                checked += 1
    assert checked == 5


# ---------------------------------------------------------------------------
# 8. LuaJIT 2.1 Runtime & Coexistence Tests for All 6 M_CBK*.lua Modules
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
        function EEex_DisableCodeProtection() end
        function EEex_EnableCodeProtection() end
        function EEex_FlattenTable(t) return t end
        function EEex_GenLuaCall() return {} end
        _hooked_calls = {}
        function EEex_HookBeforeAndAfterCallWithLabels(site, ...) table.insert(_hooked_calls, site) end
        function EEex_HookConditionalJumpOnSuccessWithLabels(site, ...) table.insert(_hooked_calls, site) end
        function EEex_HookAfterRestoreWithLabels(site, ...) table.insert(_hooked_calls, site) end
        function EEex_UDToPtr(ud) return ud._ptr end
        function EEex_PtrToUD(ptr, kind) return ptr end
        function EEex_Utility_IterateCPtrList(list, fn)
            for _, item in ipairs(list or {}) do fn(item) end
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


def _load_mod_lua(name: str, subs: dict[str, int] | None = None) -> str:
    txt = (MOD_DIR / "lua" / name).read_text(encoding="utf-8")
    for k, v in (subs or {}).items():
        txt = txt.replace(f"%{k}%", str(v))
    return txt


def test_08_lua_runtime_and_coexistence() -> None:
    # 1) M_CBKWPN.lua
    lua, init_l, _ = _new_lua_env({
        "CBKWPN": [
            ["*", "16417", "PROF", "92", "ALLOW"],
            ["*", "16420", "PROF", "104", "DENY"],
            ["*", "16420", "PROF", "104", "ALLOW"],  # DENY must still win over ALLOW
        ]
    })
    lua.execute(_load_mod_lua("M_CBKWPN.lua"))
    for fn in init_l:
        fn()
    g = lua.globals()
    assert g.CBKWeaponUsability.EvaluateRule(3, 16417, 92, 25, 0) == 1
    assert g.CBKWeaponUsability.EvaluateRule(2, 16420, 104, 15, 1) == 0
    assert g.CBKWeaponUsability.EvaluateRule(2, 16384, 90, 20, 1) == 1
    # Native wrapper check
    item = lua.eval("{ pRes = { pHeader = { proficiencyType = 92, itemType = 25 } } }")
    assert g.CBKWeaponUsability_NativeEval(item, 3, 16417, 0) == 1

    # 2) M_CBKKP.lua + CBRKitProficiency coexistence + jnz instruction fix verification
    kp_src = _load_mod_lua("M_CBKKP.lua")
    assert "jnz use_kit_col" in kp_src and "jz use_kit_col" not in kp_src
    lua2, init2, _ = _new_lua_env({"CBRKPKIT": [["8", "16417"], ["18", "16417"]]})
    lua2.execute(kp_src)
    lua2.execute(kp_src)  # second load must be idempotent no-op
    assert len(init2) == 1
    init2[0]()
    assert lua2.globals().CBKKitProficiency_ShouldOverride(8, 16417) is True
    assert lua2.globals().CBKKitProficiency_ShouldOverride(3, 16417) is False

    # 3) M_CBKSP.lua + CBRSpellProgression coexistence
    lua3, init3, _ = _new_lua_env({
        "CBRSPKIT": [["5", "16384", "CBRIWD7"], ["5", "16398", "CBRBG6"]],
        "CBRIWD7": [["1", "0"]],
        "CBRBG6": [["1", "0"]],
    })
    sp_src = _load_mod_lua("M_CBKSP.lua")
    lua3.execute(sp_src)
    lua3.execute(sp_src)
    assert len(init3) == 1
    init3[0]()
    assert lua3.globals().CBKSpellProgression_ResolveTable(16384) > 0
    assert lua3.globals().CBKSpellProgression_ResolveTable(16398) > 0
    assert lua3.globals().CBKSpellProgression_ResolveTable(99999) == 0

    # 4) M_CBKAPR.lua (codec, warrior guard, marker bit)
    lua4, init4, op4 = _new_lua_env({"CBKAPKIT": [["16417", "2", "1"]]})
    lua4.execute(_load_mod_lua("M_CBKAPR.lua", {"CBK_APR_STATE_ID": 130}))
    init4[0]()
    assert len(op4) == 1
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
    s_tempus = lua4.eval("_make_sprite(3, 0, 16417, 92, 2, 1, false)")
    op4[0](s_tempus)
    assert s_tempus.m_derivedStats.m_nNumberOfAttacks == 7  # 1.5 encoded as 6+1=7
    # Running again must NOT double-stack (marker bit already set)
    op4[0](s_tempus)
    assert s_tempus.m_derivedStats.m_nNumberOfAttacks == 7
    # Warrior/Cleric multiclass blocked by WARRIOR_GUARD
    s_fc = lua4.eval("_make_sprite(8, 0, 16417, 92, 2, 2, false)")
    op4[0](s_fc)
    assert s_fc.m_derivedStats.m_nNumberOfAttacks == 2
    # Fighter->Cleric dual (class=3, baseFlags=0x08 Fighter original) blocked by WARRIOR_GUARD
    s_dual = lua4.eval("_make_sprite(3, 8, 16417, 92, 2, 2, false)")
    op4[0](s_dual)
    assert s_dual.m_derivedStats.m_nNumberOfAttacks == 2

    # 5) M_CBKSTR.lua (Strength Floor + ClampStrOne + CBMStrength.registered guard)
    lua5, _, op5 = _new_lua_env()
    # Simulate M_CBMSTR already loaded first:
    lua5.execute("CBMStrength = { registered = true }")
    lua5.execute(_load_mod_lua("M_CBKSTR.lua", {"CBM_STR_FLOOR_STATE": 129, "CBK_STR_CLAMP_1_STATE": 131}))
    assert len(op5) == 1  # only clamp listener added because CBMStrength.registered was true!
    s_clamp = lua5.eval("""
        {
            m_derivedStats = {
                m_nSTR = -2,
                GetSpellState = function(self, id) return id == 131 and 1 or 0 end,
            }
        }
    """)
    lua5.globals().CBMStrength.ClampStrOne(s_clamp)
    assert s_clamp.m_derivedStats.m_nSTR == 1

    # Also test fresh ApplyFloor raise & non-lowering
    lua5b, _, op5b = _new_lua_env()
    lua5b.execute(_load_mod_lua("M_CBKSTR.lua", {"CBM_STR_FLOOR_STATE": 129, "CBK_STR_CLAMP_1_STATE": 131}))
    assert len(op5b) == 2
    lua5b.execute("""
        function _make_str_sprite(curStr, curExtra, packedFloor)
            local applied = {}
            local st = {
                m_nSTR = curStr, m_nSTRExtra = curExtra,
                GetSpellState = function(self, id) return id == 129 and 1 or 0 end,
            }
            return {
                _applied = applied,
                getActiveStats = function(self) return st end,
                m_timedEffectList = { { m_effectId = 328, m_dWFlags = 129, m_special = packedFloor } },
                m_equipedEffectList = {},
                applyEffect = function(self, eff) table.insert(applied, eff) end,
            }
        end
    """)
    s_low = lua5b.eval("_make_str_sprite(18, 50, 21000)")
    lua5b.globals().CBMStrength.ApplyFloor(s_low)
    assert len(s_low._applied) == 1 and s_low._applied[1].effectAmount == 3
    s_high = lua5b.eval("_make_str_sprite(22, 0, 21000)")
    lua5b.globals().CBMStrength.ApplyFloor(s_high)
    assert len(s_high._applied) == 0

    # 6) M_CBKDCN.lua (Dual-Classes Keep Kit Names)
    lua6, init6, op6 = _new_lua_env({"CBKDCNAM": [["7", "8", "16385", "7001", "7002"]]})
    lua6.execute(_load_mod_lua("M_CBKDCN.lua"))
    init6[0]()
    s_dc = lua6.eval("""
        {
            m_baseStats = { m_flags = 8, m_mageSpecUpperWord = 0, m_mageSpecialization = 16385 },
            m_typeAI = { m_Class = 7 },
            m_derivedStats = { m_nClassTypeOverrideMixed = -1, m_nClassTypeOverrideLower = -1 },
        }
    """)
    op6[0](s_dc)
    assert s_dc.m_derivedStats.m_nClassTypeOverrideMixed == 7001
    assert s_dc.m_derivedStats.m_nClassTypeOverrideLower == 7002
    # Foreign op290 override must NOT be clobbered
    s_foreign = lua6.eval("""
        {
            m_baseStats = { m_flags = 8, m_mageSpecUpperWord = 0, m_mageSpecialization = 16385 },
            m_typeAI = { m_Class = 7 },
            m_derivedStats = { m_nClassTypeOverrideMixed = 999999, m_nClassTypeOverrideLower = 999998 },
        }
    """)
    op6[0](s_foreign)
    assert s_foreign.m_derivedStats.m_nClassTypeOverrideMixed == 999999


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

    # Also verify runtime-generated spells (e.g. CBKTMDV.SPL) after full install
    game = tmp_path / "game_bgse"
    create_fake_game(game, mode="bg2ee")
    _install_all(game)
    for spl_path in sorted((game / "override").glob("*.SPL")):
        hits = check_spl_has_opcodes(spl_path, {402, 214})
        assert not hits, f"Installed {spl_path.name} contains forbidden opcodes for BGSE: {hits}"
