# Changelog

## v0.2.0 (2026-11-16) — Races, Global Non-Warrior APR, Stonefire Sorcerer & Elementalist
- **Upgraded Component `100` (`chriz_bg_kits_kernel`):**
  - `M_CBKAPR.lua`: Global Non-Warrior Proficiency APR dynamically decoded from `WSPATCK.2DA` column 1 (`+0.5 APR` at 2–4 pips, `+1.0` or `+1.5` under True Grandmastery at 5 pips) for every non-warrior wielding a weapon (`89..110`, `115`) with `>= 2` pips, sharing `CBR_TEMPUS_SPEC_APR` idempotence.
  - `M_CBKWPN.lua`: Extended `CInfGame::CheckItemUsableByClass` hook to capture `nRace`, preserve item race-locks on `ALLOW`, evaluate `SUBTYPE 1..7` (armor tiers, shields, mage robes, helmets), and unlock non-Fighter class items (robes/scrolls/wands) for dual-classed `Barbarians`.
  - `M_CBKCMB.lua` + `CBKCMB.db`: Added scoped `CGameEffect::CheckSave` and `CGameEffectDamage::ApplyEffect` hook dispatcher (`4` verified unique patterns on BG2:EE `2.7.3.0`).
- **Added Components `110` & `111` (`chriz_bg_kits_races_fr` / `chriz_bg_kits_races_all`):**
  - `110`: Forgotten Realms racial class, kit, specialist mage, dual-class (`Barbarian` included), and multiclass matrix (never stricter than Vanilla, `ILLUSIONIST` kept first under `MAGE` for Gnome multiclasses, Dwarf multiclass mages routed to `Abjurer`, dedicated `K_*_HB` tables when `HOBGOBLIN` is present), race-filtered dual-class UI, Halfling Mage & non-Human Monk Cleric-clone animation fallbacks, and racial perks (**Human `Second Wind`**, **Elf `+1` Save vs. Spell**, **Half-Elf `Silver Tongue`**, **Halfling `Finesse`**).
  - `111`: Full race/class/kit/dual-class/multiclass unlock with racial perks and animation clones.
- **Added Component `210` (`chriz_bg_kits_stonefire`):** Dwarf `Stonefire Sorcerer` (`CBK_STONEFIRE`) with `HPDD` (`d6`), `2` pips in Warhammer & Battle Axe, shields/helmets & armored arcane casting up to Chain Mail (`CBKARCDS.EFF` + `EEex_Sprite_AddLoadedListener` save-load state restore), Wing Buffet/knockdown immunity, scaling physical & fire resistance, `+1 CON` at L5 & L15, *Magma Eruption* (`CBKSF01`), dynamic `-1` spell cast/level (`MXSPLSRC.2DA`), and Illusion opposition (`CHARGEN_CHOOSE_SPELLS` filter + `0x00001000` scroll exclusion).
- **Added Component `220` (`chriz_bg_kits_elementalist`):** Druid `Elementalist` (`CBK_ELEMENTALIST`) with curated Priest L1–L7 arcane elemental spellbook (including Level 7 *Incendiary Cloud* and `CLERIC_CBMAGIC_ICELANCE` deduplication), shared daily *Fire / Water / Air / Earth Elemental Forms* (`2/3/4/5/5` uses/day, `personal_space=3`, deep-blue Water Elemental palette swap), non-additive stat/DR floors, Water Form *Tidal Healing* 1-for-1 memorized Cure Wounds swap, and *Primal Penetration* + *Tectonic Strikes* HLA (`LUEL0.2DA`, replacing *Elemental Transformation* HLAs).

## v0.1.0 (2026-11-13) — Playground Seed-Release
- Added Component `100` (`chriz_bg_kits_kernel`): EEex runtime hooks (`CBKWPN`, `CBKKP`, `CBKAPR`, `CBKSP`, `CBKSTR`) with coexistence guards for `chriz-bg-rebalance` and `chriz-bg-magic`.
- Added Component `200` (`chriz_bg_kits_tempus`): Overhauled `Priest of Tempus` (`OHTEMPUS`) including automatic level-1 Battle Axe Lore-Pip + 2 free pips, 5-tier `Holy Power`, `Chaos of Battle`, *Divination Toll*, and `Branwen` alignment.
- Added Component `300` (`chriz_bg_kits_bloodrager`): Standalone `Bloodrager` (`CBKBLDRG`) Fighter kit keeping Vanilla Berserker/Korgan untouched.
- Added Component `310` (`chriz_bg_kits_bards`): Overhauled `Jester` & `Skald` + `CBRBG6` / `CBRIWD7` bard spell progression.
- Added Component `320` (`chriz_bg_kits_core_fixes`): Archer L12 Called Shot clamp, physical-only Hardiness (`SPCL907` & `SPWISH12`), non-lowering Resist Magic (`SPCL904`), `12/16 HD` Deathblows, and EEex `Dual-Classes Keep Kit Names`.
