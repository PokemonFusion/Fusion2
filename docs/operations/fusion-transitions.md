# Atomic trainer Fusion transitions (#723)

Fusion means a trainer and their Pokémon-derived anthro form. It does not combine
Pokémon species. The existing bond, held-item, egg, EXP and battle rules remain in
force. Pokémon rows retain their identity, ownership, HP/status, moves and PP.

## Player routes

| Command | Result |
| --- | --- |
| `+fuse/temp 3` | Validate the current member of canonical party slot 3, Bond at least 140, no held item, no egg/breeding/system reservation and no battle. Reserve the same Pokémon while fused. |
| `+unfuse` | Return a temporary source to its preferred slot when free, another free party slot otherwise, or the first owned box when the party is full. A permanent source remains an unlocked reserved form. |
| `+fuse/permanent 3 confirm` | Require Bond 255 and the same source restrictions. Unlock and reserve that form, adding its existing one-third EXP contribution once. Permanent unlocking cannot be undone through the normal player route. |
| `+fusion`, `+fusion 1` | List or select already unlocked owned permanent forms. Switching never grants another EXP contribution. |

Existing aliases, Fusion battle-order/participation preferences and temporary
effective-level rules remain supported. Gapped party slots retain their numbers.
No new species, form, balance rule, money source or plot-only asset is added.

## Transaction and cache contract

Actual persistent characters use `FusionTransitions`; the public `utils.fusion`
functions dispatch to that service. Pure engine stand-ins retain the lightweight
helpers, which are not proof of persistent player behavior.

The service uses the [shared ownership lock order](pokemon-transfers.md): character,
storage, trainer, sorted referenced Pokémon. It reads saved Attributes and owned
rows from SQL and validates every active/unlocked reference and source under those
locks. The previous form's deactivation/return, new reservation, unlocked IDs,
character view, fighter EXP aliases and request receipt share one transaction.
An error leaves the previous complete state intact. A changed source slot, owner,
bond, held item, egg, battle or system reservation cannot pass a stale preflight.

An optional request UUID binds exact action/target/slot terms to a durable receipt
in the character's `fusion_transitions` Attribute category. Exact replay returns
the original outcome; different terms cannot reuse the identity. Separate retries
of a permanent unlock also recognize the persisted unlocked form and cannot add
EXP again. Temporary reactivation of the same current source is an idempotent no-op.

Committed reads resolve the owned source using the current character's trainer,
independently of account membership. Attribute caches are discarded after commit
or rollback. Temporary/permanent battle annotations are removed from cached sources
after transitions so unfused party members regain their ordinary battle view.
Callers wrapping the service in a larger transaction must discard their runtime
snapshots after rolling back that outer transaction, as with other lifecycle APIs.

## Legacy compatibility

Older chargen explicitly recorded some owned permanent starters while leaving
them in a party slot. This exact active-permanent/owned/party case remains valid
for battle admission, and storage/release/transfer guards protect its reference.
The next atomic Fusion transition moves it to the canonical Fusion reservation
without adding EXP, creating a Pokémon, changing ownership or resetting HP/PP.
UUID case differences are normalized. Inspection reports the compatibility case;
inspection itself performs no normalization.

This does not guess the intended role of an unreferenced Fusion reservation,
foreign/missing source, invalid owned placement, unknown kind or malformed form
list. Those states fail closed for review. Completing the entire chargen lifecycle
is separately tracked by #730; this change does not certify onboarding.

## Inspection and bounded recovery

The operator tool is read-only by default:

```text
python -m django audit_fusion_state CHARACTER_ID --settings=server.conf.settings
```

It reports the active source, kind, unlocked IDs, exact problems and a state
fingerprint. It never grants a trainer, storage, Pokémon or EXP. Existing game
operations and changes to real player data require their own authorization.

For a deliberately reviewed missing/foreign/malformed **reference**, an authorized
operator can use the inspected fingerprint and record a note:

```text
python -m django audit_fusion_state CHARACTER_ID --clear-invalid-references --fingerprint INSPECTED_HASH --operator-note "Reviewed reference-only recovery" --settings=server.conf.settings
```

Recovery locks/rechecks the state and refuses a changed fingerprint. It removes
only the invalid references, returns the character to human view if the active
reference was invalid, and records the prior state/note. It does not move or adopt
any Pokémon, return an unrelated source, alter HP/PP/EXP, unlock a form or erase
receipts. Unreferenced owned reservations, invalid owned placement and uncertain
state require a separate deliberate custody decision; this route refuses them.

## Verification

Use an explicit isolated `PF2_TEST_POSTGRES_DSN` and run
`python -B tests/integration/fusion_cases.py`. The suite uses actual `pokemon.user.User`
characters, accounts, canonical models, ordinary commands, independent connections,
write faults and the shipped operator tool. Outbound transport is captured; it
does not constitute a socket walkthrough or deployment. The tests join CI and the
three-process mandatory gate when an isolated DSN is supplied. See the dated
[verification report](../testing/october-fusion-2026-10-23.md).
