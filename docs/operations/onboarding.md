# Self-service beta onboarding (#730)

The website and game share one account. Registration uses Evennia's account
creation view and configured account typeclass. Character creation uses
`pokemon.user.User` through the configured character typeclass and existing
website/`charcreate` paths; `goic <name>` or the displayed number selects an owned
character. An account can have up to ten characters and four simultaneous
puppets under the existing settings. Each character has its own trainer, storage,
choices, starter/form and completion receipt.

## Beta validation policy

New-character setup and ordinary play are self-service. There is no routine
Validator/Builder approval step. `chargen` explains this at entry. Completion is
enforced by a durable character-scoped receipt and `chargen_completed`, rather
than waiting for staff to set `validated`. The optional `@validate` command records
staff review of established characters; its help/messages no longer describe it
as the beta entry gate. A legacy true validation flag remains a closed setup
marker so this change cannot grant another free starter to an established user.

## Normal route

1. Register/log in through the website or game with the same account. Review the
   displayed character list. Use `charcreate NAME` only when another character is
   wanted, then `goic NAME` (or the displayed number).
2. Type `chargen`. Choose human trainer or Fusion, gender and the requested native
   species, ability and nature. Human trainers also choose a favored type and
   starter gender; `starterlist` shows valid species at that prompt.
3. Accepted choices save as the menu advances. Abort/disconnect grants nothing;
   `chargen` reopens the next required prompt, including from another client.
   `+starter` remains an alias into the human selection path and shares the
   completed-state guard; direct `+starter SPECIES` remains deprecated.
4. Confirm the choices. Human setup creates one level-five owned starter in
   canonical party/box placement. Fusion setup creates one level-five personal
   permanent form with canonical Fusion placement and its initial full level-five
   fighter XP. This is an initial character grant, not the later bond-based
   permanent-unlock operation. No second starter is added for a Fusion.
5. Use `look`, `+sheet`, `+party`, `help getting started` and `help first outing`.
   The existing configured starting location, trainer and storage are checked;
   missing starting state refuses completion before a grant.

Fusion is the trainer's Pokemon-derived personal body, not species splicing.
Its chosen presentation gender is retained even for species without a native
gender. Battle activation forms requiring an item/ability are excluded as
starting bodies. Final completion revalidates the saved path, supported species,
native ability, nature, favored type and starter gender server-side.

## Persistence, retries and legacy state

Accepted menu choices are separate from the final receipt. Completion locks the
current character, storage and trainer, then saves the owned Pokemon, initialized
moves/stats, placement, Fusion view when applicable, receipt and completed marker
in one transaction. Concurrent/repeated confirmations return the same historical
receipt. A post-write failure rolls everything back and retains the saved draft.
No completion message is sent for a failed transaction.

The confirmation holds a copy of the reviewed choices. Under that same lock,
completion compares it with the current saved draft. If another client changed
the selection, the old confirmation asks the player to reopen and review rather
than granting a different starter or body.

The receipt retains the original Pokemon UUID after later trading, release or
character deletion. Replaying completion cannot recreate that Pokemon, teleport,
heal, reset progression or issue another resource grant. Draft edits from an old
client cannot reopen a completed setup. Accounts and same-account alts do not
share grants or form references.

Established legacy characters with validation, completed setup fields, Fusion
references or already-owned Pokemon are not guessed into another free grant.
They continue using their existing progress; inconsistent legacy state requires
deliberate inspection. New unfinished characters resume their saved choices.
Trainer-number initialization uses the actual saved maximum and savepoint-safe
concurrent retries, so deleted-number gaps do not cause duplicate-number loops.

Staff can inspect exactly one character without writes:

```text
evennia audit_pokemon_onboarding --character CHARACTER_ID
```

This reports location, trainer/storage, placements, saved choices/legacy markers
and any completion receipt. It never creates trainer/storage records, grants
Pokemon/XP, validates a character, clears completed state or guesses a repair.
For a new interrupted menu, the ordinary recovery route is `chargen`.

## Verification boundary

Production-model tests replay ordinary menu callbacks and commands using actual
User/Account models with Player permission, captured outbound transport and
labelled staff inspection/fault setup. The separate website/socket journey must
record the exact released or isolated candidate and normal account/character
selection. Local automated tests, manual/socket acceptance and deployment are
distinct evidence; this guide does not claim any game deployment.
