# CEBG Installer & Playground Handoff: `chriz-bg-kits` `v0.3.0`

**Date:** 2026-11-20  
**Repository:** `C:\src\private\chriz-bg-kits` (`setup-chriz-bg-kits.tp2`, version `v0.3.0`)  
**Target Games:** BG2:EE and EET (`v2.7.3.0+`) with `EEex` (`v1.2.0+` / `v1.3.1`, providing `M___EEex.lua` and `EEex_scripts/extra_pattern_dbs/`)

---

## 1. What Replaces Legacy Components in `chriz-bg-collection`

`chriz-bg-kits` `v0.3.0` delivers the complete Divine Pantheon & Multiclass Cleric kit suite on top of `v0.2.0`:

1. **Racial Class, Kit, Dual-Class & Multiclass Rules (`110` Recommended / `111` Unlock All):**
   - Replaces `artisanskitpack:1` (*Enable All Classes for All Races*), `artisanskitpack:2` (*Enable Multi-Classes for All Races*), and `cdtweaks:2380` (*Remove Racial Restrictions for Kits*) in `chris-recommended.toml` (plus `cdtweaks:2140` / `2350`–`2371`). **Keep** `cdtweaks:2090` (*Remove experience cap*) and `cdtweaks:2152` (*Allow armor plus one protection item*) enabled!
   - Preserves all multiclass Cleric kits (`OHTEMPUS` `F/C` & `C/R`, `LK_ALAGHOR` `F/C`, `CBK_SHAR` `C/T`) and FR kit exclusions (`LK_ALAGHOR` Dwarf-only, `CBK_UMBERLEE` non-Dwarf, `CBK_ILMATER` non-Hobgoblin) regardless of whether `110`/`111` is installed before or after `200`–`205`, always keeping `1   0` first in `K_FC_*`, `K_CT_*`, and `K_CR_*`.
2. **Divine Pantheon (`200`–`205`) & `yeslick-npc` Coexistence:**
   - `200` (`OHTEMPUS`): Now includes clean-room `F/C` and `C/R` multiclass Cleric delivery (`CLABPR01.2DA` `CBK_MC_P` -> `CBKMCP01..50.SPL` -> `op177`) alongside `CBRKPKIT.2DA`.
   - `201` (`Lathander`, `Helm`, `Talos`, `Tyr`): Overhauls all four official deity kits with L1 free lore pips, capped `Boon of Lathander` (`CBM_BONUS_TYPED`), spellcasting-friendly `Seeking Sword` + Dismiss, targeted `Lightning of Talos`, scaling `Divine Favor` + Tyr's missing Level-25 Holy Symbol, keeping full Priest spellbooks (*Animate Dead* untouched).
   - `202` (`Alaghor of Clangeddin`, `LK_ALAGHOR`): Replaces `yeslicknpc:1` (*Alaghor of Clangeddin* kit component) conflicts cleanly. Even if `yeslick-npc` was previously present, `202` overwrites `LK_ALAGHOR` cleanly, strips stale `LK_ALAGHOR` `op177` entries from `QD_MCP01..50.SPL` / `QD#MCP01..50.SPL` without disturbing unrelated kits, and syncs `YESLIC*`/`LK#YES*` kit & proficiencies without touching CRE level bytes (`0x234..0x236`).
   - `203` (`Nightcloak of Shar`, `CBK_SHAR`): Cleric & Cleric/Thief with `M_CBKSHR.lua` *Shadow Weave Magic* (`-2` Save penalty on Enchantment/Illusion/Necromancy & *Shadow Bolt*), *Shadow Veil*, single-target *Shadow Bolt* (no SoD blindness cloud), and `VICONI*`/`BDVICONI` kit-only sync.
   - `204` (`Waveservant of Umberlee`, `CBK_UMBERLEE`): NE/CN/CE non-Dwarf Cleric with Spear/Dagger access, `+25%` Cold/Electricity res, *Icelance* (deduplicated against `CLERIC_CBMAGIC_ICELANCE`) & *Cone of Cold* domain Priest spells, *Crushing Undertow*, and *Tempest Shroud* cold retaliation.
   - `205` (`Painbearer of Ilmater`, `CBK_ILMATER`): LG/LN/NG Cleric with Quarterstaff lore pip, Fatigue immunity, *Ilmater's Endurance* + `M_CBKILM.lua` non-additive `25%` Physical DR floor, and *Martyr's Grace* ranged heal with `CURRENTHP <= 10` (`CBK_HP_LE_10`) non-lethal sacrifice guard.

---

## 2. Components (`setup-chriz-bg-kits.tp2`)

| Component ID | WeiDU `LABEL` | Subcomponent / Requires | Summary |
|---:|---|---|---|
| `100` | `chriz_bg_kits_kernel` | Requires `bg2ee`/`eet` + `EEex` | Core EEex Kit Kernel (`CBKWPN`, `CBKKP`, `CBKAPR`, `CBKSP`, `CBKSTR`, `CBKCMB`). **Required before `110`–`320`.** |
| `110` | `chriz_bg_kits_races_fr` | `SUBCOMPONENT` (Recommended), requires `100` | Forgotten Realms Racial Class, Kit & Multiclass Rules + Racial Perks + animation clones. |
| `111` | `chriz_bg_kits_races_all` | `SUBCOMPONENT` (Alternative), requires `100` | Unlock All Classes, Kits, Dual-Classes & Multiclasses for All Races + Racial Perks + animation clones. |
| `200` | `chriz_bg_kits_tempus` | Requires `100` | Cleric Overhaul: **Priest of Tempus (`OHTEMPUS`)** + `F/C` & `C/R` multiclass + `Branwen` sync. |
| `201` | `chriz_bg_kits_vanilla_clerics` | Requires `100` | Cleric Overhaul: **Vanilla Deities (`Lathander`, `Helm`, `Talos`, `Tyr`)**. |
| `202` | `chriz_bg_kits_alaghor` | Requires `100` | Cleric Kit: **Alaghor of Clangeddin (`LK_ALAGHOR`)** (Dwarf Cleric & `F/C`, `Yeslick` sync, `yeslick-npc` coexistence). |
| `203` | `chriz_bg_kits_shar` | Requires `100` (`M_CBKCMB.lua`) | Cleric Kit: **Nightcloak of Shar (`CBK_SHAR`)** (Cleric & `C/T`, *Shadow Weave Magic*, `Viconia` sync). |
| `204` | `chriz_bg_kits_umberlee` | Requires `100` | Cleric Kit: **Waveservant of Umberlee (`CBK_UMBERLEE`)** (NE/CN/CE, non-Dwarf in `110`). |
| `205` | `chriz_bg_kits_ilmater` | Requires `100` | Cleric Kit: **Painbearer of Ilmater (`CBK_ILMATER`)** (LG/LN/NG, `25%` Phys-DR floor, `HP <= 10` sacrifice guard). |
| `210` | `chriz_bg_kits_stonefire` | Requires `100` | Sorcerer Kit: **Stonefire Sorcerer (`CBK_STONEFIRE`)**. |
| `220` | `chriz_bg_kits_elementalist` | Requires `100` (`M_CBKCMB.lua`) | Druid Kit: **Elementalist (`CBK_ELEMENTALIST`)**. |
| `300` | `chriz_bg_kits_bloodrager` | Requires `100` | Standalone Fighter Kit: **Bloodrager (`CBKBLDRG`)**. |
| `310` | `chriz_bg_kits_bards` | Requires `100` | Bard Overhaul: **Jester & Skald** + `CBRBG6` / `CBRIWD7` spell progression. |
| `320` | `chriz_bg_kits_core_fixes` | Requires `100` | Core Kit & HLA Fixes (Archer Called Shot clamp, 40% physical Hardiness, 50% Resist Magic floor, Deathblow 12/16 HD, Dual-Class Kit Names). |

**Recommended CEBG Install List:**
```
--force-install-list 100 110 200 201 202 203 204 205 210 220 300 310 320
```

---

## 3. Install Order in `chriz-bg-collection`

Install `chriz-bg-kits` (`100 110 200 201 202 203 204 205 210 220 300 310 320`):

- **AFTER:**
  1. `EEex` (`v1.2.0+` / `v1.3.1` with `EEex_scripts/extra_pattern_dbs` support)
  2. `IWDification` / `Spell Revisions` (`spell_rev`) / `chriz-bg-magic` (so `WIZARD_ICELANCE`, `CLERIC_CBMAGIC_ICELANCE`, `WIZARD_CONE_OF_COLD`, elemental arcane spells, Cure Wounds spells, and Divination Priest spells are finalized before `200`, `204`, and `220` clone/scan them)
  3. `yeslick-npc` (if present; omit `yeslicknpc:1` kit or let `202` cleanly overwrite `LK_ALAGHOR` and clean `QD_MCP*`)
  4. `cdtweaks` weapon-proficiency/grandmastery tweaks (`2090` & `2152` stay enabled; omit `2360`–`2380` and `artisanskitpack:1/2`)
  5. `chriz-bg-playable-races` (so `HOBGOBLIN` exists in `RACE.IDS`, `CLSRCREQ.2DA`, `KITTABLE.2DA`, and `WEAPPROF.2DA` before `110`/`111` & kit components run)
- **BEFORE:**
  1. `SCS` (`stratagems`)
  2. `chriz-bg-script-engine` (`BGSE` — verified `0` `op402` and `0` `op214` across all `chriz-bg-kits` static and generated `.SPL`/`.EFF` resources)
