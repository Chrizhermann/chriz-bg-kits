# CEBG Installer & Playground Handoff: `chriz-bg-kits` `v0.1.0`

**Date:** 2026-11-13  
**Repository:** `C:\src\private\chriz-bg-kits` (`setup-chriz-bg-kits.tp2`, version `v0.1.0`)  
**Target Games:** BG2:EE and EET (`v2.7.3.0+`) with `EEex` (`v1.2.0+` / `v1.3.1`, providing `M___EEex.lua` and `EEex_scripts/extra_pattern_dbs/`)

---

## 1. Overview & Exclusivity Policy

`chriz-bg-kits` `v0.1.0` ("Playground Seed-Release") is the standalone WeiDU + EEex successor to `ArtisansKitpack` and `BardicWonders` for the CEBG collection.

1. **Preset Removal:** Remove `mod:artisanskitpack`, `mod:artisanskitpack-npc`, `mod:artisanskitpack-tweak`, and `mod:bardicwonders` from default CEBG presets (e.g. `recipes/curated-full-current/presets/chris-recommended.toml`).
2. **Mutual Exclusivity:** Mark `chriz-bg-kits` mutually exclusive with `artisanskitpack*` and `bardicwonders` in the installer catalog.
   - `setup-chriz-bg-kits.tp2` also enforces `REQUIRE_PREDICATE` refusal on every component (`100`–`320`) if `ARTISANSKITPACK/ARTISANSKITPACK.TP2` (`#0`) or `BARDICWONDERS/BARDICWONDERS.TP2` (`#0`) is present in `weidu.log`.
   - Keeping either legacy mod via manual opt-in carries **no guaranteed support**.

---

## 2. Components (`setup-chriz-bg-kits.tp2`)

| Component ID | WeiDU `LABEL` | Requires | Summary |
|---:|---|---|---|
| `100` | `chriz_bg_kits_kernel` | `GAME_IS ~bg2ee eet~`, `M___EEex.lua`, `EEex_scripts/extra_pattern_dbs` | Core EEex Kit Kernel: `CBKWPN` (`CInfGame::CheckItemUsableByClass` table-driven `ALLOW`/`DENY`), `CBKKP`/`CBRKPKIT` (multiclass kit `WEAPPROF` column redirect), `CBKAPR` (`+0.5` APR for 2+ pips with `WARRIOR_GUARD` + shared `CBR_TEMPUS_SPEC_APR` state), `CBKSP` (`CBRSPVER`/`CBRSPKIT`/`CBRBG6`/`CBRIWD7`/`CBRIWD8` bard progression), `CBKSTR` (`CBM_STR_FLOOR` + `CBK_STR_CLAMP_1`). **Required before `200`–`320`.** |
| `200` | `chriz_bg_kits_tempus` | `100` (`M_CBKWPN.lua`, `CBKWPN.2DA`) | Cleric Overhaul — **Priest of Tempus (`OHTEMPUS`)**: 1 auto Battle Axe Lore-Pip (`CBKTMP1`) + regular starter pips; `WEAPPROF` `2` pips on Long Sword (`90`), Battle Axe (`92`), Crossbow (`103`), Cleric weapons (`97,100,101,102,107,115`), all styles (`111..114`); `CBKWPN` `ALLOW`; `CBRKPKIT` `8`/`18`; non-lowering 5-tier `OHTMPS1.SPL` Holy Power + `Transformation` exclusion (`op206`); `OHTMPS2` + `CBKTM1..3D/E` Chaos of Battle preserving `OHTMPS2D/E` hooks & projectiles `162`/`171`; `CBKTMDV` Divination Toll; preserves `AP_CDHLYSYM` at L25; updates `KITLIST`, `CLASTEXT`, and `BRANWE*.CRE`. |
| `300` | `chriz_bg_kits_bloodrager` | `100` (`M_CBKWPN.lua`, `CBKWPN.2DA`) | Standalone Fighter Kit — **Bloodrager (`CBKBLDRG`)**: registered dynamically (`COUNT_2DA_COLS` across `KITTABLE.2DA`, `CLSRCREQ.2DA`, `CLASTEXT.2DA`, `WEAPPROF.2DA`, `25STWEAP.2DA` — safe with extra race columns such as `HOBGOBLIN`); *In Extremis* (`<76/50/26%` HP, doubled while Enraged, physical resistance L14+), *Enrage* (`CBKBR00` + melee refresh + hard cap + *Winded*, mind shield, `+15` temp HP), `-4` ranged THAC0 (`CBKBR07`) + `0` ranged pips + `CBKWPN` `DENY` `103..107`, `LUCBK.2DA` (`GA_SPCL907` + `AP_CBKBRH1`). Vanilla `BERSERKER` & `KORGAN*.CRE` remain untouched. |
| `310` | `chriz_bg_kits_bards` | `100` (`M_CBKWPN.lua`, `CBRSPKIT.2DA`) | Bard Overhaul — **Jester & Skald**: `Jester` (`CLABBA03.2DA`, dedicated `LUCBKJ.2DA` + `LUABBR.2DA` `JESTER CBKJ`, replaces all `SPCL920` rows with 1 `AP_CBKJES3`, adds `SPCL751A`, `CBKJES1/2/3`), `Skald` (`WEAPPROF` `2` pips on `89..115`), `CBRSPKIT.2DA` (`BARD`/`JESTER` -> `CBRIWD7`, `BLADE`/`SKALD` -> `CBRBG6`), updates `KITLIST` & `CLASTEXT`. |
| `320` | `chriz_bg_kits_core_fixes` | `100` (`M_CBKWPN.lua`, `M_CBKSTR.lua`) | Core Kit & HLA Fixes: `Archer` L12 Called Shot (`ARCHSLOW.EFF` -> `CBKARCSL.SPL` + `CBK_STR_CLAMP_1` floor `STR >= 1`), `Hardiness` (`SPCL907`/`SPWISH12`) `40%` physical only, `Resist Magic` (`SPCL904`) `50%` non-lowering floor (`CBKRSMG`), `Deathblow`/`Greater Deathblow` (`SPCL902`/`SPCL903` `.SPL`/`.EFF`) `12/16` HD, and `Dual-Classes Keep Kit Names` (`CBKDCNAM.2DA` + `M_CBKDCN.lua`). |

**Playground Install List:** `--force-install-list 100 200 300 310 320` (all 5 components are designed to be installed cleanly together).

---

## 3. Install Order in `chriz-bg-collection`

Install `chriz-bg-kits` (`100 200 300 310 320`):

- **AFTER:**
  1. `EEex` (`v1.2.0+` / `v1.3.1` with `EEex_scripts/extra_pattern_dbs` support)
  2. `Spell Revisions` (`spell_rev`, so `SPELL.IDS` & `SPPR*` Divination spells are finalized before `200` scans `SPPR100..799` for Divination Toll & `CLERIC_BLOOD_RAGE`/`CLERIC_ANIMAL_RAGE`)
  3. `chriz-bg-magic` (so shared strength-floor & transformation spell IDs are already present)
  4. `chriz-bg-playable-races` (so `HOBGOBLIN` / custom race columns exist in `KITTABLE.2DA`, `CLSRCREQ.2DA`, `WEAPPROF.2DA` before `300` reads `COUNT_2DA_COLS`)
  5. `rogue_rebalancing` (`rr`, if Blade 3-pip two-weapon style is active)
- **BEFORE:**
  1. `SCS` (`stratagems`, so SCS picks up updated spells/kits/proficiencies)
  2. `chriz-bg-script-engine` (`BGSE`, so AI spell classification and script builds see final `chriz-bg-kits` `.SPL`/`.2DA` state)

---

## 4. Sibling-Repo Coexistence & Decoupling Notes

1. **`chriz-bg-rebalance`:**
   - **Runtime coexistence:** `_G.CBRKitProficiency`, `_G.CBRSpellProgression`, and `CBR_TEMPUS_SPEC_APR` `SPLSTATE` use shared idempotent guards (`cbk_kernel` skips copying `CBR*` 2DAs if already in `override/`, and Lua hooks short-circuit cleanly if `_G.CBRKitProficiency` / `_G.CBRSpellProgression` are already active).
   - **Preset cleanup (`chris-recommended.toml`):** Retire/disable legacy `chriz-bg-rebalance` components that depended on `ArtisansKitpack` / `BardicWonders` or duplicated `v0.1.0` work (`200` Hardiness, `400` Tempus Weapon Training, and `421` BW kit description copy in `bard_progression.tpa`). Component `420` (`M_CBRSP.lua`) may stay or be superseded by `100` (`M_CBKSP.lua`).
2. **`chriz-bg-magic`:**
   - Shares `CBM_STR_FLOOR` (`SPLSTATE.IDS`) and `_G.CBMStrength.registered` cleanly without duplicate hook installation.
3. **`chriz-bg-script-engine` (`BGSE`):**
   - Verified `0` occurrences of `op402` (*Invoke Lua*) and `op214` (*Select Spell*) across all static `chriz-bg-kits/res/*` and generated `.SPL`/`.EFF` files, so `combat-intent/spells.lua` classifies all `chriz-bg-kits` spells cleanly without `unknown` tags or modal stalls.
4. **`chriz-bg-collection` (`2720` / `cdtweaks`):**
   - Base companions remain Vanilla in `v0.1.0`; Branwen automatically receives her `OHTEMPUS` kit ID (`0x4029`) and Battle Axe proficiency pip via `200`, while `KORGAN*.CRE` keeps Vanilla `BERSERKER` (`0x4001`) untouched.

---

## 5. Preview of `v0.2.0` (`Component 110`)

Planned for `v0.2.0`: **`Component 110` (Lore-Grounded Race × Class × Kit & Dual/Multiclass Matrix)** to replace `cdtweaks` `2090..2151` blanket race/class/dual-class unlocks (preventing combos such as Dwarf arcane casters with `-5` shorty saves, Halfling Paladins, or Half-Orc Wizards while preserving `chriz-bg-playable-races` columns like `HOBGOBLIN`).
