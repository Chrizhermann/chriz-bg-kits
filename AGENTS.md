# chriz-bg-kits — Working Agreements

Clean-room EEex-native kit and class overhaul mod for Baldur's Gate II:EE / EET (2.7.3.0).
Replaces ArtisansKitpack and BardicWonders inside the CEBG collection.

## Core Rules
- **We Overwrite**: A mod defines its result. Overwrite target spells, kits, CLABs, HLAs, and
  2DA columns cleanly with what we decided. Never gate or skip changes based on pre-existing
  descriptions, effect counts, or mod versions unless explicitly documented as a hard conflict
  (e.g. `ArtisansKitpack`, `BardicWonders`).
- **Clean-Room**: Never copy binary assets, `.tpa`, `.lua`, or prose from Artisan's Kitpack,
  Bardic Wonders, SCS, or Spell Revisions. Author all `.spl`, `.eff`, `.lua`, and `.tpa` cleanly.
- **Declarative Binaries**: Edit `defs/*.json` and regenerate via `python tools/build_resources.py`.
  Verify with `python tools/build_resources.py --check`.
- **Verification**: Always run `python tests/run_tests.py` (WeiDU parse-check, BG2:EE/EET
  install/uninstall, We Overwrite mutation tests, PE signature check, LuaJIT runtime &
  coexistence tests, and BGSE ability scanner audit).
