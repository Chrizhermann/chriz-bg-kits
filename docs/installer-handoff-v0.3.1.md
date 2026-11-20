# CEBG Installer & Playground Handoff: `chriz-bg-kits` `v0.3.1`

**Date:** 2026-11-20  
**Repository:** `C:\src\private\chriz-bg-kits` (`setup-chriz-bg-kits.tp2`, version `v0.3.1`)  
**Target Games:** BG2:EE and EET (`v2.7.3.0+`) with `EEex` (`v1.2.0+` / `v1.3.1`, providing `M___EEex.lua` and `EEex_scripts/extra_pattern_dbs/`)

---

## 1. What Replaces Legacy Components in `chriz-bg-collection`

`chriz-bg-kits` `v0.3.1` delivers the streamlined Divine Pantheon suite on top of `v0.2.0`:

1. **Racial Class, Kit, Dual-Class & Multiclass Rules (`110` Recommended / `111` Unlock All):**
   - Replaces `artisanskitpack:1` (*Enable All Classes for All Races*), `artisanskitpack:2` (*Enable Multi-Classes for All Races*), and `cdtweaks:2380` (*Remove Racial Restrictions for Kits*) in `chris-recommended.toml` (plus `cdtweaks:2140` / `2350`–`2371`). **Keep** `cdtweaks:2090` (*Remove experience cap*) and `cdtweaks:2152` (*Allow armor plus one protection item*) enabled!
   - **Single-Class & Dual-Class Kits Only:** In `110` (*Recommended*), kits are strictly restricted to Single-Class and Dual-Class characters (no player multiclass kits; all multiclass `K_*` tables remain `1   0` unkitted, even if an upstream mod previously wrote kit rows into them).
   - Preserves FR kit exclusions (`CBK_UMBERLEE` non-Dwarf, `CBK_ILMATER` non-Hobgoblin, external `LK_ALAGHOR` Dwarf-only) regardless of whether `110`/`111` is installed before or after `200`–`204`.
2. **External `yeslick-npc` Compatibility (`100` & `320`) without Duplicating `Alaghor of Clangeddin`:**
   - Keep external `yeslick-npc` (`0, 1`) in `chriz-bg-collection` as the canonical owner of **Alaghor of Clangeddin (`LK_ALAGHOR`)**, and **omit `chriz-bg-rebalance:411`**.
   - Both `100` (`cbk_kernel.tpa`) and `320` (`cbk_core_fixes.tpa`) automatically detect `LK_ALAGHOR` in `KITLIST.2DA` and register Battle Axe usability (`CBKWPN.2DA`) plus Fighter/Cleric Battle Axe level-up pips (`CBRKPKIT.2DA`) without Artisan's Kitpack.
3. **Divine Pantheon (`200`–`204`) & Single-Class Viconia:**
   - `200` (**Priest of Tempus**, `OHTEMPUS`): Single-class Cleric overhaul + Branwen sync (Dual-Class supported; no player multiclassing).
   - `201` (**Vanilla Deities**: `Lathander`, `Helm`, `Talos`, `Tyr`): L1 free lore pips, capped `Boon of Lathander` (`CBM_BONUS_TYPED`), spellcasting-friendly `Seeking Sword` + Dismiss, targeted `Lightning of Talos`, scaling `Divine Favor` + Tyr's missing Level-25 Holy Symbol; full Priest spellbooks intact (*Animate Dead* untouched).
   - `202` (**Priest of Shar**, `CBK_SHAR`): Pure single-class Cleric with Dagger lore pip, Blindness immunity, `M_CBKSHR.lua` *Shadow Weave Magic* (`-2` Save penalty on Enchantment/Illusion/Necromancy & *Shadow Bolt*), *Shadow Veil*, single-target *Shadow Bolt* (no SoD blindness cloud), and `VICONI*`/`BDVICONI` single-class kit-only sync (**omit `chriz-bg-modpack:192`** *Viconia -> Cleric/Thief*).
   - `203` (**Priest of Umberlee**, `CBK_UMBERLEE`): NE/CN/CE non-Dwarf Cleric with Spear/Dagger access, `+25%` Cold/Electricity res, *Icelance* (deduplicated against `CLERIC_CBMAGIC_ICELANCE`) & *Cone of Cold* domain Priest spells, *Crushing Undertow*, and *Tempest Shroud* cold retaliation.
   - `204` (**Priest of Ilmater**, `CBK_ILMATER`): LG/LN/NG Cleric with Quarterstaff lore pip, Fatigue immunity, *Ilmater's Endurance* + `M_CBKILM.lua` non-additive `25%` Physical DR floor, and *Martyr's Grace* ranged heal with `CURRENTHP <= 10` (`CBK_HP_LE_10`) non-lethal sacrifice guard.

---

## 2. Components (`setup-chriz-bg-kits.tp2`)

| Component ID | WeiDU `LABEL` | Subcomponent / Requires | Summary |
|---:|---|---|---|
| `100` | `chriz_bg_kits_kernel` | Requires `bg2ee`/`eet` + `EEex` | Core EEex Kit Kernel (`CBKWPN`, `CBKKP`, `CBKAPR`, `CBKSP`, `CBKSTR`, `CBKCMB`) + external `LK_ALAGHOR` sync. **Required before `110`–`320`.** |
| `110` | `chriz_bg_kits_races_fr` | `SUBCOMPONENT` (Recommended), requires `100` | Forgotten Realms Racial Class, Kit & Multiclass Rules (no player multiclass kits) + Racial Perks + animation clones. |
| `111` | `chriz_bg_kits_races_all` | `SUBCOMPONENT` (Alternative), requires `100` | Unlock All Classes, Kits, Dual-Classes & Multiclasses for All Races + Racial Perks + animation clones. |
| `200` | `chriz_bg_kits_tempus` | Requires `100` | Cleric Overhaul: **Priest of Tempus (`OHTEMPUS`)** + `Branwen` sync. |
| `201` | `chriz_bg_kits_vanilla_clerics` | Requires `100` | Cleric Overhaul: **Vanilla Deities (`Lathander`, `Helm`, `Talos`, `Tyr`)**. |
| `202` | `chriz_bg_kits_shar` | Requires `100` (`M_CBKCMB.lua`) | Cleric Kit: **Priest of Shar (`CBK_SHAR`)** (single-class, *Shadow Weave Magic*, `Viconia` single-class sync). |
| `203` | `chriz_bg_kits_umberlee` | Requires `100` | Cleric Kit: **Priest of Umberlee (`CBK_UMBERLEE`)** (NE/CN/CE, non-Dwarf in `110`). |
| `204` | `chriz_bg_kits_ilmater` | Requires `100` | Cleric Kit: **Priest of Ilmater (`CBK_ILMATER`)** (LG/LN/NG, `25%` Phys-DR floor, `HP <= 10` sacrifice guard). |
| `210` | `chriz_bg_kits_stonefire` | Requires `100` | Sorcerer Kit: **Stonefire Sorcerer (`CBK_STONEFIRE`)**. |
| `220` | `chriz_bg_kits_elementalist` | Requires `100` (`M_CBKCMB.lua`) | Druid Kit: **Elementalist (`CBK_ELEMENTALIST`)**. |
| `300` | `chriz_bg_kits_bloodrager` | Requires `100` | Standalone Fighter Kit: **Bloodrager (`CBKBLDRG`)**. |
| `310` | `chriz_bg_kits_bards` | Requires `100` | Bard Overhaul: **Jester & Skald** + `CBRBG6` / `CBRIWD7` spell progression. |
| `320` | `chriz_bg_kits_core_fixes` | Requires `100` | Core Kit & HLA Fixes (Archer Called Shot clamp, 40% physical Hardiness, 50% Resist Magic floor, Deathblow 12/16 HD, Dual-Class Kit Names, external `LK_ALAGHOR` sync). |

**Recommended CEBG Install List:**
```
--force-install-list 100 110 200 201 202 203 204 210 220 300 310 320
```

---

## 3. Install Order in `chriz-bg-collection`

Install `chriz-bg-kits` (`100 110 200 201 202 203 204 210 220 300 310 320`):

- **AFTER:**
  1. `EEex` (`v1.2.0+` / `v1.3.1` with `EEex_scripts/extra_pattern_dbs` support)
  2. `IWDification` / `Spell Revisions` (`spell_rev`) / `chriz-bg-magic` (so `WIZARD_ICELANCE`, `CLERIC_CBMAGIC_ICELANCE`, `WIZARD_CONE_OF_COLD`, elemental arcane spells, Cure Wounds spells, and Divination Priest spells are finalized before `200`, `203`, and `220` clone/scan them)
  3. `yeslick-npc` (`0, 1`, so `LK_ALAGHOR` is registered in `KITLIST.2DA` for `100`/`320` Battle Axe usability & level-up pips; omit `chriz-bg-rebalance:411`)
  4. `chriz-bg-modpack` (omit `chriz-bg-modpack:192` so Viconia stays single-class `Priest of Shar`)
  5. `cdtweaks` weapon-proficiency/grandmastery tweaks (`2090` & `2152` stay enabled; omit `2360`–`2380` and `artisanskitpack:1/2`)
  6. `chriz-bg-playable-races` (so `HOBGOBLIN` exists in `RACE.IDS`, `CLSRCREQ.2DA`, `KITTABLE.2DA`, and `WEAPPROF.2DA` before `110`/`111` & kit components run)
- **BEFORE:**
  1. `SCS` (`stratagems`)
  2. `chriz-bg-script-engine` (`BGSE` — verified `0` `op402` and `0` `op214` across all `chriz-bg-kits` static and generated `.SPL`/`.EFF` resources)
