# CEBG Installer & Playground Handoff: `chriz-bg-kits` `v0.2.0`

**Date:** 2026-11-16  
**Repository:** `C:\src\private\chriz-bg-kits` (`setup-chriz-bg-kits.tp2`, version `v0.2.0`)  
**Target Games:** BG2:EE and EET (`v2.7.3.0+`) with `EEex` (`v1.2.0+` / `v1.3.1`, providing `M___EEex.lua` and `EEex_scripts/extra_pattern_dbs/`)

---

## 1. What Replaces Legacy Components in `chriz-bg-collection`

`chriz-bg-kits` `v0.2.0` expands the clean-room replacement for `ArtisansKitpack`, `BardicWonders`, and `cdtweaks` racial/dual-class unlock tweaks:

1. **Racial Class, Kit, Dual-Class & Multiclass Rules (`110` Recommended / `111` Unlock All):**
   - Replaces `artisanskitpack:1` (*Enable All Classes for All Races*), `artisanskitpack:2` (*Enable Multi-Classes for All Races*), and `cdtweaks:2380` (*Remove Racial Restrictions for Kits*) in `chris-recommended.toml` (as well as upstream `cdtweaks:2140` *Expanded Dual-Class Options* and `cdtweaks:2350`–`2371` racial/dual/multiclass unlocks). **Keep** `cdtweaks:2090` (*Remove experience cap*) and `cdtweaks:2152` (*Allow armor plus one protection item*) enabled!
   - **Important:** Do **not** install `cdtweaks:2360`, `2370`, `2371`, `2380` or `artisanskitpack` alongside `110`/`111` — `chriz-bg-kits` `110`/`111` already generates missing Halfling Mage & non-Human Monk animation clones (`ANIMATE.IDS` + `.INI`/`.BAM`), enables `Barbarian` dual-classing, filters dual-class target classes by race in `CHARGEN_CLASS`, and preserves `chriz-bg-playable-races` columns (`HOBGOBLIN` -> dedicated `K_*_HB` tables).
2. **Global Non-Warrior Proficiency APR (`100` `M_CBKAPR.lua` upgrade):**
   - Dynamically reads `WSPATCK.2DA` column 1 so **every** non-warrior with `>= 2` pips in their equipped weapon (`Swashbuckler`, `Blade`, `Haer'Dalis`, `Priest of Tempus`, `Stonefire Sorcerer`, etc.) receives `+0.5 APR` at 2–4 pips and `+1.0` (`+1.5` under True Grandmastery) at 5 pips, with zero double-dipping on warriors or `M_CBRAPR.lua`.
3. **New Standalone Kits (`210` & `220`):**
   - `210` — **Stonefire Sorcerer (`CBK_STONEFIRE`)**: Dwarf Sorcerer (`d6` HP, Warhammer & Battle Axe `2` pips, shields/helmets & zero-failure arcane casting in armor up to Chain Mail, *Magma Eruption*, `-1` spell cast/level, Illusion opposition).
   - `220` — **Elementalist (`CBK_ELEMENTALIST`)**: Druid kit (curated Priest L1–L7 elemental spells, shared daily *Fire / Water / Air / Earth Elemental Forms* with `personal_space=3`, Water *Tidal Healing* fast Cure swap, *Primal Penetration* + *Tectonic Strikes* HLA).

---

## 2. Components (`setup-chriz-bg-kits.tp2`)

| Component ID | WeiDU `LABEL` | Subcomponent / Requires | Summary |
|---:|---|---|---|
| `100` | `chriz_bg_kits_kernel` | Requires `bg2ee`/`eet` + `EEex` | Core EEex Kit Kernel (`CBKWPN` `SUBTYPE 1..7` & `Barbarian` dual-class item fix, `CBKKP`, `CBKAPR` Global Non-Warrior Proficiency APR from `WSPATCK.2DA`, `CBKSP`, `CBKSTR`, `CBKCMB` CheckSave/Damage dispatcher). **Required before `110`–`320`.** |
| `110` | `chriz_bg_kits_races_fr` | `SUBCOMPONENT` (Recommended), requires `100` | Forgotten Realms Racial Class, Kit & Multiclass Rules + Racial Perks (*Second Wind*, *Elf +1 Save vs. Spell*, *Silver Tongue*, *Halfling Finesse*) + `Barbarian` dual-classing + animation clones. |
| `111` | `chriz_bg_kits_races_all` | `SUBCOMPONENT` (Alternative), requires `100` | Unlock All Classes, Kits, Dual-Classes & Multiclasses for All Races + Racial Perks + animation clones. |
| `200` | `chriz_bg_kits_tempus` | Requires `100` | Cleric Overhaul: **Priest of Tempus (`OHTEMPUS`)** + `Branwen` sync. |
| `210` | `chriz_bg_kits_stonefire` | Requires `100` | Sorcerer Kit: **Stonefire Sorcerer (`CBK_STONEFIRE`)** (Dwarf-only under `110` or standalone; all races under `111`; install order `110`/`111` before or after `210` is supported). |
| `220` | `chriz_bg_kits_elementalist` | Requires `100` (`M_CBKCMB.lua`) | Druid Kit: **Elementalist (`CBK_ELEMENTALIST`)**. |
| `300` | `chriz_bg_kits_bloodrager` | Requires `100` | Standalone Fighter Kit: **Bloodrager (`CBKBLDRG`)** (Vanilla Berserker & Korgan untouched). |
| `310` | `chriz_bg_kits_bards` | Requires `100` | Bard Overhaul: **Jester & Skald** + `CBRBG6` / `CBRIWD7` spell progression. |
| `320` | `chriz_bg_kits_core_fixes` | Requires `100` | Core Kit & HLA Fixes (Archer L12 Called Shot clamp, 40% physical Hardiness, 50% Resist Magic floor, 12/16 HD Deathblows, Dual-Classes Keep Kit Names). |

**Recommended CEBG Install List:** `--force-install-list 100 110 200 210 220 300 310 320`

---

## 3. Install Order in `chriz-bg-collection`

Install `chriz-bg-kits` (`100 110 200 210 220 300 310 320`):

- **AFTER:**
  1. `EEex` (`v1.2.0+` / `v1.3.1` with `EEex_scripts/extra_pattern_dbs` support)
  2. `IWDification` / `Spell Revisions` (`spell_rev`) / `chriz-bg-magic` (so `WIZARD_ICELANCE`, `CLERIC_CBMAGIC_ICELANCE`, `WIZARD_VITRIOLIC_SPHERE`, `WIZARD_OTILUKES_FREEZING_SPHERE`, `WIZARD_ACID_STORM`, Cure Wounds spells, and Divination Priest spells are finalized before `200` and `220` clone/scan them)
  3. `cdtweaks` weapon-proficiency/grandmastery tweaks (if installed, `M_CBKAPR.lua` reads `WSPATCK.2DA` dynamically at runtime so relative order vs True Grandmastery is safe, and `210` converts armor `op145` to `CBKARCDS.EFF` cleanly; avoid `cdtweaks` `2360..2380` & arcane armor-failure tweaks on light/chain armor)
  4. `chriz-bg-playable-races` (so `HOBGOBLIN` exists in `RACE.IDS`, `CLSRCREQ.2DA`, `KITTABLE.2DA`, and `WEAPPROF.2DA` before `110`/`111`/`210`/`220`/`300` run)
- **BEFORE:**
  1. `SCS` (`stratagems`)
  2. `chriz-bg-script-engine` (`BGSE` — verified `0` `op402` and `0` `op214` across all `chriz-bg-kits` static and generated `.SPL`/`.EFF` resources)
