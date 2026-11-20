# chriz-bg-kits

Clean-room EEex-native kit overhaul, racial class/kit rulebook, and class-rebalance mod for **BG2:EE / EET (2.7.3.0+)**.

Designed for the **CEBG Collection**, **chriz-bg-magic**, **chriz-bg-playable-races**, and **chriz-bg-script-engine (BGSE)**.
Mutually exclusive with `ArtisansKitpack` and `BardicWonders`.

## Components (`v0.3.1`)
- `100` — **Core EEex Kit Kernel** (`M_CBKWPN`, `M_CBKKP`, `M_CBKAPR` Global Non-Warrior Proficiency APR, `M_CBKSP`, `M_CBKSTR`, `M_CBKCMB` Scoped CheckSave/Damage Dispatcher, plus external `yeslick-npc` `LK_ALAGHOR` Battle Axe usability & level-up pips compatibility)
- `110` / `111` — **Racial Class, Kit & Multiclass Rules** (`SUBCOMPONENT`):
  - `110` — *Forgotten Realms Racial Class, Kit & Multiclass Rules (Recommended)* (lore-grounded expansions, never stricter than Vanilla, dynamic `HOBGOBLIN` `K_*_HB` tables, single-class & dual-class kits only without player multiclass kits, `Barbarian` dual-classing, race-filtered dual-class UI, Halfling Mage & non-Human Monk animation clones, plus **Human `Second Wind`**, **Elf `+1` Save vs. Spell**, **Half-Elf `Silver Tongue`**, and **Halfling `Finesse`**)
  - `111` — *Unlock All Classes, Kits, Dual-Classes & Multiclasses for All Races*
- `200` — **Cleric Overhaul: Priest of Tempus** (`OHTEMPUS` Lore-Pip, Holy Power, Chaos of Battle, Divination Toll, Branwen sync)
- `201` — **Cleric Overhaul: Vanilla Deities (Lathander, Helm, Talos, Tyr)** (L1 free lore pips, `Boon of Lathander` non-stacking `+1` APR capped vs. Improved Haste, `Seeking Sword` without spellcasting block + Dismiss, targeted non-bouncing `Lightning of Talos` + `25%` Electricity res, `Divine Favor` scaling `+1..+6` every 5 levels + Tyr's missing Level-25 Holy Symbol; full Priest spellbooks intact)
- `202` — **Cleric Kit: Priest of Shar** (`CBK_SHAR`: single-class Cleric with Dagger lore pip, Blindness immunity, `M_CBKSHR.lua` *Shadow Weave Magic* `-2` Save penalty on Enchantment/Illusion/Necromancy & *Shadow Bolt*, *Shadow Veil*, single-target *Shadow Bolt* + *Touch of Loss*, Level-25 Holy Symbol, and Viconia single-class sync)
- `203` — **Cleric Kit: Priest of Umberlee** (`CBK_UMBERLEE`: NE/CN/CE non-Dwarf Cleric with Spear & Dagger lore access, `+25%` Cold/Electricity res, *Icelance* & *Cone of Cold* domain Priest spells, *Crushing Undertow*, *Tempest Shroud* retaliation, Level-25 Holy Symbol)
- `204` — **Cleric Kit: Priest of Ilmater** (`CBK_ILMATER`: LG/LN/NG Cleric with Quarterstaff lore pip, Fatigue immunity & `+1` Save vs. Death, *Ilmater's Endurance* + `M_CBKILM.lua` non-additive `25%` Physical DR floor, *Martyr's Grace* ranged heal with `HP <= 10` non-lethal sacrifice guard, Level-25 Holy Symbol)
- `210` — **Sorcerer Kit: Stonefire Sorcerer** (`CBK_STONEFIRE`: Dwarf Sorcerer kit with `d6` HP, Warhammer & Battle Axe specialization, shields/helmets & armored arcane casting up to Chain Mail, physical/fire/knockdown resilience, *Magma Eruption*, `-1` spell cast/level, and Illusion opposition)
- `220` — **Druid Kit: Elementalist** (`CBK_ELEMENTALIST`: curated Priest L1–L7 arcane elemental spellbook, shared daily *Fire / Water / Air / Earth Elemental Forms* with `personal_space=3`, non-additive stat/DR floors, Water *Tidal Healing* 1-for-1 fast Cure swap, and *Primal Penetration* + *Tectonic Strikes* HLA)
- `300` — **Standalone Fighter Kit: Bloodrager** (`CBKBLDRG`: In Extremis `<76/50/26%`, focused Enrage, Melee Refresh with 60s/120s cap, Winded)
- `310` — **Bard Overhaul: Jester & Skald** (Piercing Mockery, Heckle, Mad Ramble, The Fool's Journey HLA, Skald martial prowess, CBRSP spell progression)
- `320` — **Core Kit & HLA Fixes** (Archer L12 Called Shot STR>=1 clamp, 40% physical Hardiness, 50% Resist Magic floor, Deathblow 12/16 HD, Dual-Classes Keep Kit Names, external `LK_ALAGHOR` sync)

## Build & Test
```powershell
python tools/build_resources.py --check
python tests/run_tests.py
```
