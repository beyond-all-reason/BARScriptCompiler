# Corpus fixtures

Representative `.bos` scripts and their `.h` dependencies, copied verbatim from
the Beyond All Reason game data so the compiler test suite is self-contained
and does not depend on a sibling checkout of the game repository.

Source: `Beyond-All-Reason` branch `Variable_Animation`, commit `9f91091325`
(2026-09-10), directory `scripts/`.

| Fixture | Upstream source | Why it is here |
|---|---|---|
| `freefusion.bos` | `scripts/freefusion.bos` | Legacy style: local `sfxtype.h`/`exptype.h` includes, `spin`/`move`/`wait-for-move`, `start-script`, `Rand` |
| `mission_command_tower.bos` | `scripts/mission_command_tower.bos` | Legacy style: named explosion constants, `return` values, 15 pieces |
| `freefusion_clean.bos` | `scripts/freefusion_clean.bos` | Modern style: `recoil_common_includes.h` + header-defined functions (`HitByWeapon`, `DamagedSmoke`) with conditional compilation (`MAXTILT 0`) and a static var |
| `Raptors/raptord1.bos` | `scripts/Raptors/raptord1.bos` | Minimal modern unit: `../`-relative include, signals, `set-signal-mask`, `move ... now` |
| `Units/armpt.bos` | `scripts/Units/armpt.bos` | Ship script: `bar_ships_common.h` with `RB_*` macro customization, static vars, reload/stun logic |
| `Units/scavboss/armscavengerbossv2.bos` | `scripts/Units/scavboss/armscavengerbossv2.bos` | Stress case: largest typical script (41 pieces, 15 static vars, ~5400 commands) |

Shared headers (no transitive `#include`s in any of them):

- `sfxtype.h` (empty stub), `exptype.h` — top-level legacy copies
- `recoil_common_includes.h` — shared GET/SET/explosion constants and macros
- `unit_hitbyweaponid_and_smoke.h` — header-defined damage-rocking and smoke functions
- `bar_ships_common.h` — ship physics/animation macros
- `Units/scavboss/sfxtype.h`, `Units/scavboss/exptype.h` — the scavboss-local copies (differ from the top-level ones, kept in place)

Note: do not compile these fixtures in place; the compiler writes `.cob`
files next to the `.bos` source. The tests copy the corpus to a temp
directory first.
