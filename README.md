# Chriz BG Kits

Clean-room EEex-native kit overhaul, divine pantheon, and Forgotten Realms racial rulebook for
**Baldur's Gate II: Enhanced Edition** and **Enhanced Edition Trilogy (EET)** (`v0.3.1`, targeting
`2.7.3.0+`). Built as the clean-room replacement for *Artisan's Kitpack* and *Bardic Wonders* in
upcoming **[Chriz Easy BG](https://bg.chrizfader.org/collection)** builds.

---

## Part 1 — For Players

### Highlights

- **Forgotten Realms Racial Rules & Perks (`110` / `111`):**
  - Expands class, kit, and dual-class options without ever being stricter than the base game.
  - Component `110` (*Recommended*) keeps kits strictly for single-class and dual-class characters
    (no player multiclass kits), enables **Barbarian** dual-classing, filters dual-class choices
    by race, and preserves **Hobgoblin** kit tables (`chriz-bg-playable-races`).
  - Adds missing Halfling Mage and non-Human Monk animation clones so every legal combination
    renders properly.
  - Grants active racial traits: **Human** *Second Wind*, **Elf** `+1` Save vs. Spell,
    **Half-Elf** *Silver Tongue*, and **Halfling** *Finesse*.
  - Alternative `111` unlocks all classes, kits, dual-classes, and multiclasses for every race.
- **8 Deity Cleric Kits & Overhauls (`200`–`204`):**
  - Keeps full Priest spellbooks intact while giving each deity distinct domain flavor, a free
    level-1 deity-weapon lore pip, and a Level-25 Holy Symbol:
  - **Priest of Tempus (`200`):** Battle Axe lore pip, 5-tier *Holy Power*, *Chaos of Battle*,
    *Divination Toll*, and Branwen sync.
  - **Vanilla Deities (`201` — Lathander, Helm, Talos, Tyr):** Capped non-stacking *Boon of
    Lathander*, spellcasting-friendly *Seeking Sword* with Dismiss, targeted non-bouncing
    *Lightning of Talos*, scaling *Divine Favor* (`+1` to `+6`), and Tyr's missing Level-25 Holy
    Symbol.
  - **Priest of Shar (`202`):** Single-class Cleric with Blindness immunity, *Shadow Weave Magic*
    (`-2` Save penalty on Enchantment/Illusion/Necromancy & *Shadow Bolt*), *Shadow Veil*,
    single-target *Shadow Bolt*, *Touch of Loss*, and Viconia single-class sync.
  - **Priest of Umberlee (`203`):** Non-Dwarf Cleric (`NE`/`CN`/`CE`) with Spear & Dagger
    access, `+25%` Cold/Electricity resistance, *Icelance* & *Cone of Cold* domain spells,
    *Crushing Undertow*, and *Tempest Shroud* retaliation.
  - **Priest of Ilmater (`204`):** Cleric (`LG`/`LN`/`NG`) with Fatigue immunity, `+1` Save vs.
    Death, *Ilmater's Endurance* (`25%` non-additive physical resistance floor), and *Martyr's
    Grace* ranged heal with non-lethal (`HP <= 10`) sacrifice guard.
- **New & Reworked Class Kits (`210`–`310`):**
  - **Stonefire Sorcerer (`210`):** Dwarf Sorcerer (`d6` HP, Warhammer & Battle Axe
    specialization, shields/helmets & armored arcane casting up to Chain Mail, fire/knockdown
    resilience, *Magma Eruption*, `-1` spell cast/level, and Illusion opposition).
  - **Elementalist (`220`):** Druid kit with curated L1–L7 elemental spellbook, shared daily
    *Fire / Water / Air / Earth Elemental Forms*, Water *Tidal Healing* 1-for-1 fast Cure swap,
    and *Primal Penetration* + *Tectonic Strikes* HLAs.
  - **Bloodrager (`300`):** Standalone Fighter kit (*In Extremis* low-HP bonuses, focused
    Enrage, Melee Refresh, *Winded*) leaving vanilla Berserker and Korgan untouched.
  - **Jester & Skald Overhaul (`310`):** Reworked Bard songs (*Piercing Mockery*, *Heckle*,
    *Mad Ramble*, *The Fool's Journey* HLA, Skald martial prowess) with dedicated Bard spell
    progression.
- **Core Kit & HLA Fixes (`320`):** Archer L12+ Called Shot Strength clamp (`>= 1`), `40%`
  physical-only Hardiness, `50%` Resist Magic floor, `12/16 HD` Deathblows, *Dual-Classes Keep
  Kit Names*, and external `yeslick-npc` *Alaghor of Clangeddin* (`LK_ALAGHOR`) Battle Axe sync.

### Requirements & Compatibility

- **Game:** BG2:EE or EET (`2.7.3.0+`) with **EEex** (`v1.2.0+` or `v1.3.1`, providing
  `M___EEex.lua` and `EEex_scripts/extra_pattern_dbs/`).
- **Mutually Exclusive:** Do **not** install with **ArtisansKitpack** or **BardicWonders**
  (enforced by the WeiDU installer). Also omit `cdtweaks:2360`–`2380`, `chriz-bg-modpack:192`,
  and `chriz-bg-rebalance:411`.
- **Load Order:** Install **after** `EEex`, spell mods (`chriz-bg-magic` / `IWDification` /
  `Spell Revisions`), `yeslick-npc`, `chriz-bg-modpack`, `cdtweaks`, and
  `chriz-bg-playable-races`; install **before** `SCS` and `chriz-bg-script-engine`.
- **Install Command:** Run `setup-chriz-bg-kits.exe` (or `weidu setup-chriz-bg-kits.tp2`) with
  `--force-install-list 100 110 200 201 202 203 204 210 220 300 310 320`.

---

## Part 2 — Component Reference, Technical Kernel & License

### Component Reference (`setup-chriz-bg-kits.tp2`)

| ID | WeiDU Label | Summary |
|---:|---|---|
| `100` | `chriz_bg_kits_kernel` | **Core EEex Kit Kernel** (`M_CBKWPN`, `M_CBKKP`, `M_CBKAPR`, `M_CBKSP`, `M_CBKSTR`, `M_CBKCMB`) + external `LK_ALAGHOR` sync. Required before `110`–`320`. |
| `110` | `chriz_bg_kits_races_fr` | **Forgotten Realms Racial Class, Kit & Multiclass Rules** *(Subcomponent — Recommended)*: single/dual-class kits only, racial perks, animation clones. |
| `111` | `chriz_bg_kits_races_all` | **Unlock All Classes, Kits, Dual-Classes & Multiclasses** *(Subcomponent — Alternative)* + racial perks & animation clones. |
| `200` | `chriz_bg_kits_tempus` | **Cleric Overhaul:** Priest of Tempus (`OHTEMPUS`) + Branwen sync. |
| `201` | `chriz_bg_kits_vanilla_clerics` | **Cleric Overhaul:** Vanilla Deities (Lathander, Helm, Talos, Tyr). |
| `202` | `chriz_bg_kits_shar` | **Cleric Kit:** Priest of Shar (`CBK_SHAR`) + Viconia single-class sync. |
| `203` | `chriz_bg_kits_umberlee` | **Cleric Kit:** Priest of Umberlee (`CBK_UMBERLEE`, `NE`/`CN`/`CE`, non-Dwarf in `110`). |
| `204` | `chriz_bg_kits_ilmater` | **Cleric Kit:** Priest of Ilmater (`CBK_ILMATER`, `LG`/`LN`/`NG`). |
| `210` | `chriz_bg_kits_stonefire` | **Sorcerer Kit:** Stonefire Sorcerer (`CBK_STONEFIRE`, Dwarf-only in `110`). |
| `220` | `chriz_bg_kits_elementalist` | **Druid Kit:** Elementalist (`CBK_ELEMENTALIST`). |
| `300` | `chriz_bg_kits_bloodrager` | **Fighter Kit:** Bloodrager (`CBKBLDRG`). |
| `310` | `chriz_bg_kits_bards` | **Bard Overhaul:** Jester & Skald + `CBRBG6` / `CBRIWD7` spell progression. |
| `320` | `chriz_bg_kits_core_fixes` | **Core Kit & HLA Fixes** + `Dual-Classes Keep Kit Names` + external `LK_ALAGHOR` sync. |

### EEex Kernel, Declarative Assets & Verification

- **EEex Runtime Modules (`chriz-bg-kits/lua/`):** Kernel modules `M_CBKWPN` (table-driven item
  usability & Barbarian dual-class fix), `M_CBKKP` (proficiency redirect), `M_CBKAPR` (dynamic
  `WSPATCK.2DA` non-warrior proficiency APR), `M_CBKSP` (Bard spellbook progression),
  `M_CBKSTR` (Strength floor/clamp), and `M_CBKCMB` (scoped `CheckSave`/`Damage` hook
  dispatcher), alongside kit/race modules `M_CBKRAC`, `M_CBKSHR`, `M_CBKILM`, `M_CBKSF`,
  `M_CBKELM`, and `M_CBKDCN`. Generated `.SPL`/`.EFF` files keep `0` `op402`/`op214` entries for
  clean coexistence with SCS and BGSE.
- **Declarative Asset Pipeline & We Overwrite:** Binary `.SPL`, `.EFF`, `.ITM`, `.CRE`, `.2DA`,
  and `.BAM` resources live declaratively in `defs/*.json` and compile via
  `python tools/build_resources.py` (`128` generated files). Following **We Overwrite**,
  components write decided kit and table state regardless of prior game contents.
- **Checks & Docs:**
  - `python tools/build_resources.py --check` — verify declarative resource parity.
  - `python tests/run_tests.py` — run WeiDU parse-check, BG2:EE/EET fake-game install/uninstall,
    overwrite mutation, and LuaJIT runtime/coexistence tests.
  - See [docs/installer-handoff-v0.3.1.md](docs/installer-handoff-v0.3.1.md),
    [CHANGELOG.md](CHANGELOG.md), and [AGENTS.md](AGENTS.md).

### License

Licensed under the **[MIT License](LICENSE)** (`Copyright (c) 2026 Christopher Hermann`).
