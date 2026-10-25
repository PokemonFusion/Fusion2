# Flavor snack isolated local release plan (2026-10-25)

Candidate: **89b1ab40678b840c9ba6711966e3d534386c1a52** for #889–#891, with exactly the **1,136 Python sources**
accepted by three fresh full orders of 6,154 passed /4,028 skipped each.
[Exact controllers and hashes](flavor-snacks-release-plan-2026-10-25.json)
are published before execution. The user's existing explicit local-dev
authorization and request to finish the remaining item issues cover this new
disposable target; no new human approval is represented.

Target: H:\\PokemonFusionProject\\fusion2-necrozma-items\\.codex-artifacts\\flavor-snacks-live-889-891-20261025,
archived game child released/source. Five new loopback-only ports are 53311
(telnet), 53312 (HTTP), 53313 (web), 53314 (AMP) and 53315 (WebSocket).
Pre-bind and schema guards reject existing targets or fallback services.

With H:\\PokemonFusionProject\\evenv\\Scripts\\python.exe -B:

1. Use only the existing task-owned PostgreSQL fixture controller at
   H:\\PokemonFusionProject\\fusion2\\.codex-artifacts\\necrozma-20261024\\postgres_fixture.py.
   Resume it if stopped; no existing game/service/cluster is a fallback.
2. Run this target's supervise.py. It creates a fresh random
   pf2_recovery_test_<uuid> schema, migrates only that empty schema through
   archived Pokémon 0058, initializes a separate operator and starts only
   this archived instance using qa_item_repair_settings.py.
3. Run released/socket_driver.py and play.py batches. Two ordinary accounts
   self-register, go IC and complete onboarding without elevated permissions.
4. Separate operator.py world executes the published world.py. It creates
   only tagged Center/arena/trail/counter/exits and a protected sentinel.
   Each wallet is labelled 10,000. The finite buy-only/no-refill counter has
   Master Ball 1,000×2 and Revive 1,500×2 as testing prerequisites, plus
   Razz and the thirteen named flavor berries 100×5 each. A labelled native
   Mew100 trail supports ordinary hunt/capture and naming. No Pokemon,
   learned move, bag copy or item effect is granted.
5. Use ordinary +store/menu purchases, +inventory, +hunt/capture/naming and
   +hold. First prove a full target spends nothing. Separate tagged
   operator.py prerequisite may set only this captured, owned, out-of-battle
   Mew HP to zero; ordinary +use Revive then establishes useful injured HP.
   This labelled prerequisite is distinct from earned battle damage.
6. Feed all thirteen new names using +berry snack, keeping a Razz control
   and one held Bluk copy. Check +use rejection, exact selected-item debit,
   useful/clamped HP, unchanged non-HP/PP state, held-only/foreign/invalid
   rejection and reconnect persistence with actual player output plus
   repeatable read-only SQL. operator.py runtime records loaded source
   identities/process; it never changes effects, moves, rolls or Pokemon.
7. Return the held copy normally, record final wallet/finite-stock/bag
   conservation, unchanged sentinel and ordinary permissions, and no battle.
   Create released/socket-stop then released/cleanup-requested. Only after
   all five exact task ports close may the supervisor drop its own generated
   schema. Stop the task PostgreSQL fixture only after zero task schemas and
   zero public tables are verified.

Preserve failed attempts and diagnose actual preconditions before source edits.
A game-source correction requires a newly qualified candidate. Authentication
and runtime-private configuration stay private; publish redacted command/effect
receipts. No existing local/PF2-Dev data, service, permanent stock or human
character is touched. This temporary source does not close #862 or prove
permanent public availability. Plot-only and unrelated work remain excluded.
