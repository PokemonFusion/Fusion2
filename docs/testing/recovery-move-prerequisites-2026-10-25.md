# Ordinary prerequisites for status Z sources (#913/#914/#916, 2026-10-25)

Three confirmed ordinary-move defects were repaired before accepting #912's
six new mappings. Their baseline failures and fixture diagnoses are retained
in the [machine receipt](recovery-move-prerequisites-2026-10-25.json).

- **#913:** Synthesis uses effective weather, including suppression/Utility
  Umbrella, with neutral 1/2, sun 2/3 and adverse 1/4 recovery through the normal
  healing gate. Useful Roost temporarily removes Flying; modern pure Flying
  falls back to Normal and fixed Tera typing stays fixed. Its versioned state
  survives checkpoint reconstruction and restores through turn/switch/faint/end
  hooks without overwriting later independent typing. Full/blocked healing adds
  no Roost type change. Fifteen actual ordinary command/SQL cases and 22 offline
  checks cover these two sources, useful outcomes, caps/prevention and rollback.
- **#914:** The first eligible Protect execution succeeds; consecutive
  successful attempts use 1/3, 1/9, 1/27, 1/81, 1/243 and 1/729, with the denominator
  capped at 729. It uses battle RNG and resets on failure, another move, a real
  elapsed gap or switch. Version 2
  state conservatively converts former power-of-two snapshots once; malformed
  state cannot grant a free retry. Four actual ordinary command/SQL cases and 22
  offline checks include blocked/damaging outcomes, restored repeats and faults.
- **#916:** Explicit status type-immunity metadata now reaches the normal hit
  route. Thunder Wave cannot paralyze Ground Diglett; Electric Jolteon's status
  immunity and Water Wailord's useful control persist. Generic Growl still
  reaches Ghost targets. Three ordinary command/SQL cases verify real status,
  PP once, no Z budget and reconnect; four ordinary offline checks and #912's
  separate Z immunity/reflection controls cover the relevant boundary.

The 22 ordinary player cases are captured production commands and real SQL in
random disposable schemas. Native capture/teaching positives are included for
all three recovery/protection sources. HP/weather/other teams are labelled
fixture setup; Roost's same-turn native Ground damage and restoration are real
effects. Sandstorm residual damage is accounted for after Synthesis healing.
Source/dex metadata, held items and progression are not assigned to fake an effect.

The first weather pilot exposed Damp's separate effect-identity exception
before the status expansion. It is recorded in #915 and remains unmodified;
the bounded recovery fixture explicitly uses Wooper's native Water Absorb.
This report claims no complete Damp or broader battle parity.

All three fresh full orders passed **6,287 passed / 4,028 skipped each**, wrapper exit zero. **271 focused checks**, **288 compatibility command/SQL cases** and **1,149 matching qualified Python identities** accompany these results. All 25 unrelated shared dirty paths are preserved. The task database is stopped with zero disposable schemas/public tables.

The final [physical](z-six-physical-sources-2026-10-25.md) and
[status](z-six-status-sources-2026-10-25.md) receipts separately qualify their
new mappings, actual PP/side payment and reusable crystals. Ordinary repairs
are committed separately from the mappings. Publication is
[86e9eba](https://github.com/PokemonFusion/Fusion2/commit/86e9eba8f50bcbae803fc5cd900a1f0c40ec63c0).
No migration, shared deployment, world-stock change, plot content, existing
human fixture or unrelated work is included. Earlier evidence is preserved.
