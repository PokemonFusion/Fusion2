# Character sheet reads and visibility

The Player Hub (`/mysheet/` and legacy `/character-sheet/`) requires login and
shows only characters in the account's currently saved playable roster. The
profile editor uses the same authority. With no selector it opens the first
owned character. An explicit foreign, removed or invalid selector opens no
editable character; a POST with that selector cannot change the first character.
Both same-account characters remain separately selectable.

`+sheet` and `+party` show the acting character's resources. `+profile NAME`
shows the named character's public RP fields. Private RP fields are visible to
the character, its owning account and existing Helper/Validator/Builder/Admin/
Developer/Wizard staff permissions. An ordinary different character does not
gain private visibility merely by being on the same account. These are the
existing visibility rules, now enforced for real persisted fields; account and
character integer IDs cannot stand in for one another. HTML profile text is
escaped by the existing templates. No public full-sheet route is added.

## Shared meanings

| Field | Meaning wherever displayed |
| --- | --- |
| Character | One playable ObjectDB character, separate from the login account and same-account alternates. |
| Wallet/inventory/badges | Existing Trainer rows for that character. Legacy inventory/money Attributes do not override a saved trainer. |
| Party | Canonical `party` placements ordered by saved slots 1–6, retaining gaps. A reservation can prevent actions while the Pokémon stays visibly in that slot. |
| Boxes | Canonical `box` placements ordered by box and position. Other owned Pokémon are never guessed to be boxed. |
| Reservations | Fusion and Daycare custody are separately labelled. Trade/market claims label the member in its current party/box location. Breeding parents stay in Daycare. |
| Pokémon | Current owned UUID, genetics/training, native traits, held item, HP, condition and saved active moves/boosted PP. Model reload discards old transient Fusion annotations. |
| Active Fusion | The owner's Pokémon-derived anthro form, read through the existing battle bridge and fighter/trainer XP rules. `+sheet`/`+party fusion` retain calculated battle stats and effective level; a reserved source is not an extra boxed Pokémon. |

The web hub currently shows party level/types/traits/held item/status and boxed
level/types, plus resources and custody. It does **not** show HP, PP or a full
Fusion stat card; those remain game views. This change does not invent new web
stat fields or change #721/#814 calculation/boosted-PP rules.

## Read-only boundaries and limits

Reads query existing Trainer/UserStorage records; they do not invoke User's
creation properties or create starter boxes. Canonical owned rows are loaded
fresh rather than trusting Evennia's shared model identity map. Missing setup,
unplaced/foreign custody and conflicting legacy storage mirrors produce explicit
warnings. Game party sheets refuse inconsistent custody. Views never repair,
grant, release, normalize or conceal those damaged rows as a successful roster.
Unexpected database errors remain errors rather than empty successful pages.
Use the existing read-only ownership inspection before authorizing any repair.

These are fresh request reads, not an immutable multi-request transaction: a
completed trade, field use, reward or reservation transition is reflected on the
next request/command. A page already open is not a live subscription. Rendered
request tests and captured game commands are distinct from the live browser/game
comparison required to close #733. No deployment is implied.
