# Necrozma lifecycle design validation (#820)

Date: October 23, 2026. **Static design/source/issue validation passed.**
Baseline: `ec1203c47564c8e712831d8764394a4300a9b629`. This is a design-only closeout, not implementation,
ordinary-player acceptance or deployment. No proposed command or fused Z holder
has been enabled. The [contract](../design/necrozma-combination.md),
[machine-readable plan](../design/necrozma-combination.json) and
[validation receipt](necrozma-design-2026-10-23.json) retain the rules and evidence.

## Verified source and contract

- 82 static assertions passed, including 51 local documentation links.
- 20 reviewed source file hashes match; all 1034 tracked Python files have
  no diff from the baseline. No generated data, migration or runtime changes.
- Exactly two native pairs: Necrozma + Solgaleo → Dusk-Mane and Necrozma + Lunala
  → Dawn-Wings. Current form stats/types/Prism Armor match local data.
- Both ordinary source moves have base PP 5. Current level-up teaching returns
  no fused-form moves; raw form sources are R-coded. #827/#828 explicitly own
  temporary canonical slot setup and durable PP integration rather than
  claiming metadata already provides player access.
- Existing native Solgaleo/Solganium and Lunala/Lunalium profile tuples and
  fingerprints are unchanged. Current 42-mapping/34-crystal runtime support is
  unchanged; the fused-holder exception remains gated by #830.
- Seven fetched GitHub issues are open, with exact published scopes and unchecked
  acceptance criteria. The dependency graph is acyclic and all references resolve.
- The diff contains exactly seven scoped Markdown/JSON documentation artifacts;
  `git diff --check` passes. Historical item/Mega/Z test reports are unchanged.

## Open delivery graph

| Issue | Hard prerequisites | Acceptance criteria |
| --- | --- | --- |
| [#825](https://github.com/PokemonFusion/Fusion2/issues/825) | #820 design | 5 open |
| [#826](https://github.com/PokemonFusion/Fusion2/issues/826) | #825 | 6 open |
| [#827](https://github.com/PokemonFusion/Fusion2/issues/827) | #825, #826 | 7 open |
| [#828](https://github.com/PokemonFusion/Fusion2/issues/828) | #827 | 6 open |
| [#829](https://github.com/PokemonFusion/Fusion2/issues/829) | #827, #828 | 6 open |
| [#830](https://github.com/PokemonFusion/Fusion2/issues/830) | #826, #828, #829 | 6 open |
| [#831](https://github.com/PokemonFusion/Fusion2/issues/831) | #829, #830 | 6 open |

The shared guard coordinates with #722/#723; the unrelated trade UI #725 is not
a hard dependency. The initial public mutation gate requires #825–#830 together.
#831 records an intentionally released walkthrough after separate exact release
and tagged-fixture authorization; it does not itself authorize operations.

## Required implementation proof and limits

The contract covers exact owned identities, a canonical companion reservation,
atomic form/placement/move/resource/receipt writes, no PP refill across cycles,
current HP/status/progression, rollback/retry and legal separation destinations.
It preserves trainer/Pokémon Fusion and native signatures. Ultra, plots, new
currency/items, base acquisition expansion and unrelated work are excluded.

No runtime test suite was rerun for this documentation-only change. No production
game database, disposable PostgreSQL server, migration or service was started or
changed. Ordinary command effects, independent SQL, races, rollback, rebuild,
cleanup and actual live player acceptance remain unchecked implementation gates,
not evidence supplied by this design receipt. No deployment is claimed.
