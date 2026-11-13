# chriz-bg-kits

Clean-room EEex-native kit overhaul and class-rebalance mod for **BG2:EE / EET (2.7.3.0+)**.

Designed for the **CEBG Collection**, **chriz-bg-magic**, and **chriz-bg-script-engine (BGSE)**.
Mutually exclusive with `ArtisansKitpack` and `BardicWonders`.

## Components (v0.1.0)
- `100` — **Core EEex Kit Kernel** (`M_CBKWPN`, `M_CBKKP`, `M_CBKAPR`, `M_CBKSP`, `M_CBKSTR`)
- `200` — **Cleric Overhaul: Priest of Tempus** (`OHTEMPUS` Lore-Pip, Holy Power, Chaos of Battle, Divination Toll, Branwen sync)
- `300` — **Standalone Fighter Kit: Bloodrager** (`CBKBLDRG`: In Extremis `<76/50/26%`, focused Enrage, Melee Refresh with 60s/120s cap, Winded)
- `310` — **Bard Overhaul: Jester & Skald** (Piercing Mockery, Heckle, Mad Ramble, The Fool's Journey HLA, Skald martial prowess, CBRSP spell progression)
- `320` — **Core Kit & HLA Fixes** (Archer L12 Called Shot STR>=1 clamp, 40% physical Hardiness, 50% Resist Magic floor, Deathblow 12/16 HD, Dual-Classes Keep Kit Names)

## Build & Test
```powershell
python tools/build_resources.py --check
python tests/run_tests.py
```
