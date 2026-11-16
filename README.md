# chriz-bg-kits

Clean-room EEex-native kit overhaul, racial class/kit rulebook, and class-rebalance mod for **BG2:EE / EET (2.7.3.0+)**.

Designed for the **CEBG Collection**, **chriz-bg-magic**, **chriz-bg-playable-races**, and **chriz-bg-script-engine (BGSE)**.
Mutually exclusive with `ArtisansKitpack` and `BardicWonders`.

## Components (`v0.2.0`)
- `100` — **Core EEex Kit Kernel** (`M_CBKWPN`, `M_CBKKP`, `M_CBKAPR` Global Non-Warrior Proficiency APR, `M_CBKSP`, `M_CBKSTR`, `M_CBKCMB` Scoped CheckSave/Damage Dispatcher)
- `110` / `111` — **Racial Class, Kit & Multiclass Rules** (`SUBCOMPONENT`):
  - `110` — *Forgotten Realms Racial Class, Kit & Multiclass Rules (Recommended)* (lore-grounded expansions, never stricter than Vanilla, dynamic `HOBGOBLIN` `K_*_HB` tables, `Barbarian` dual-classing, race-filtered dual-class UI, Halfling Mage & non-Human Monk animation clones, plus **Human `Second Wind`**, **Elf `+1` Save vs. Spell**, **Half-Elf `Silver Tongue`**, and **Halfling `Finesse`**)
  - `111` — *Unlock All Classes, Kits, Dual-Classes & Multiclasses for All Races*
- `200` — **Cleric Overhaul: Priest of Tempus** (`OHTEMPUS` Lore-Pip, Holy Power, Chaos of Battle, Divination Toll, Branwen sync)
- `210` — **Sorcerer Kit: Stonefire Sorcerer** (`CBK_STONEFIRE`: Dwarf Sorcerer kit with `d6` HP, Warhammer & Battle Axe specialization, shields/helmets & armored arcane casting up to Chain Mail, physical/fire/knockdown resilience, *Magma Eruption*, `-1` spell cast/level, and Illusion opposition)
- `220` — **Druid Kit: Elementalist** (`CBK_ELEMENTALIST`: curated Priest L1–L7 arcane elemental spellbook, shared daily *Fire / Water / Air / Earth Elemental Forms* with `personal_space=3`, non-additive stat/DR floors, Water *Tidal Healing* 1-for-1 fast Cure swap, and *Primal Penetration* + *Tectonic Strikes* HLA)
- `300` — **Standalone Fighter Kit: Bloodrager** (`CBKBLDRG`: In Extremis `<76/50/26%`, focused Enrage, Melee Refresh with 60s/120s cap, Winded)
- `310` — **Bard Overhaul: Jester & Skald** (Piercing Mockery, Heckle, Mad Ramble, The Fool's Journey HLA, Skald martial prowess, CBRSP spell progression)
- `320` — **Core Kit & HLA Fixes** (Archer L12 Called Shot STR>=1 clamp, 40% physical Hardiness, 50% Resist Magic floor, Deathblow 12/16 HD, Dual-Classes Keep Kit Names)

## Build & Test
```powershell
python tools/build_resources.py --check
python tests/run_tests.py
```
