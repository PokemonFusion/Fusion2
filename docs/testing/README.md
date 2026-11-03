# Testing and evidence index

[Documentation home](../index.md) | [Feature guides](../guides.md) |
[Code map](../code-map.md) | [Designs](../design/README.md)

Use this index to find a dated report, acceptance checklist, or release plan
by system. Existing report and receipt paths remain stable.

## Choose a workflow

| Need | Start here |
| --- | --- |
| Run the canonical mandatory gate or focused offline checks | [Offline battle testing](../offline-battle-testing.md), [Contributing](../../CONTRIBUTING.md) |
| Read the coverage inventory | [Battle coverage](../battle-coverage-report.md), [move inventory audit](../move-inventory-audit-2026-06-22.md), [Pokemon inventory audit](../pokemon-inventory-audit-2026-06-22.md) |
| Plan ordinary-player Adventure acceptance | [Manual checklist](adventure-manual-acceptance.md) |
| Understand battle/dex QA tooling | [Battle pilot](live-battle-pilot.md), [dex sweep](live-dex-sweep.md), [tools index](../../tools/README.md) |
| Separate scratch files from retained evidence | [Workspace hygiene](../workspace-hygiene.md) |

## Interpret a report

- A design or release plan proposes work; it does not certify execution.
- Automated offline checks, disposable PostgreSQL checks, local logged-in
  acceptance, PF2-Dev acceptance, and production deployment are different
  evidence categories. Read the report's environment and tested build.
- Dates and build pins bound a result. A later report can correct an earlier
  result without changing what was observed on the earlier build.
- Companion JSON links below point to the same filename stem where available.
  Additional inventories and receipts are listed separately.
- Filename terms such as `live`, `released`, or `local` are discovery aids;
  the report itself defines the actual environment, scope, and limitations.

## Battle engine, presentation, and dex verification

- [battle-ui-live-2026-10-27](battle-ui-live-2026-10-27.md) - [JSON receipt](battle-ui-live-2026-10-27.json)
- [compact-battle-ui-2026-10-27](compact-battle-ui-2026-10-27.md) - [JSON receipt](compact-battle-ui-2026-10-27.json)
- [five-defect-repairs-2026-10-18](five-defect-repairs-2026-10-18.md)
- [full-battle-items-postrepair-2026-10-20](full-battle-items-postrepair-2026-10-20.md) - [JSON receipt](full-battle-items-postrepair-2026-10-20.json)
- [full-battle-postrecovery-2026-10-20](full-battle-postrecovery-2026-10-20.md) - [JSON receipt](full-battle-postrecovery-2026-10-20.json)
- [full-dex-corrected-2026-10-19](full-dex-corrected-2026-10-19.md)
- [full-dex-effects-2026-10-19](full-dex-effects-2026-10-19.md)
- [full-dex-knockout-2026-10-20](full-dex-knockout-2026-10-20.md)
- [full-dex-postfix-2026-10-18](full-dex-postfix-2026-10-18.md)
- [full-dex-rerun-2026-10-18](full-dex-rerun-2026-10-18.md)
- [knockout-boost-live-2026-10-19](knockout-boost-live-2026-10-19.md)
- [live-battle-pilot](live-battle-pilot.md)
- [live-dex-results-2026-10-18](live-dex-results-2026-10-18.md)
- [live-dex-sweep](live-dex-sweep.md)
- [october-multi-2026-10-24](october-multi-2026-10-24.md) - [JSON receipt](october-multi-2026-10-24.json)
- [optional-dex-showdown-2026-10-19](optional-dex-showdown-2026-10-19.md)
- [present-cap-runner-2026-10-19](present-cap-runner-2026-10-19.md)
- [runner-false-flags-2026-10-19](runner-false-flags-2026-10-19.md)
- [smoke-effects-2026-10-19](smoke-effects-2026-10-19.md)

## Ownership, player services, and communication

- [october-breeding-2026-10-23](october-breeding-2026-10-23.md) - [JSON receipt](october-breeding-2026-10-23.json)
- [october-communications-2026-10-23](october-communications-2026-10-23.md) - [JSON receipt](october-communications-2026-10-23.json)
- [october-daycare-2026-10-23](october-daycare-2026-10-23.md) - [JSON receipt](october-daycare-2026-10-23.json)
- [october-fusion-2026-10-23](october-fusion-2026-10-23.md) - [JSON receipt](october-fusion-2026-10-23.json)
- [october-market-2026-10-23](october-market-2026-10-23.md) - [JSON receipt](october-market-2026-10-23.json)
- [october-onboarding-2026-10-23](october-onboarding-2026-10-23.md) - [JSON receipt](october-onboarding-2026-10-23.json)
- [october-ownership-2026-10-23](october-ownership-2026-10-23.md) - [JSON receipt](october-ownership-2026-10-23.json)
- [october-player-live-2026-10-24](october-player-live-2026-10-24.md) - [JSON receipt](october-player-live-2026-10-24.json)
- [october-sheets-2026-10-23](october-sheets-2026-10-23.md) - [JSON receipt](october-sheets-2026-10-23.json)
- [october-shiny-2026-10-23](october-shiny-2026-10-23.md) - [JSON receipt](october-shiny-2026-10-23.json)
- [october-trading-2026-10-23](october-trading-2026-10-23.md) - [JSON receipt](october-trading-2026-10-23.json)

## Adventure, world content, gyms, and training

- [adventure-manual-acceptance](adventure-manual-acceptance.md)
- [leader-crest-2026-10-21](leader-crest-2026-10-21.md) - [JSON receipt](leader-crest-2026-10-21.json)
- [october-gyms-2026-10-23](october-gyms-2026-10-23.md) - [JSON receipt](october-gyms-2026-10-23.json)
- [september-closeout-2026-10-23](september-closeout-2026-10-23.md) - [JSON receipt](september-closeout-2026-10-23.json)
- [september-week-1](september-week-1.md)
- [training-grounds-delivery-2026-10-29](training-grounds-delivery-2026-10-29.md) - [JSON receipt](training-grounds-delivery-2026-10-29.json)

## Special forms, activation, and held-item identity

- [forced-form-item-repair-2026-10-20](forced-form-item-repair-2026-10-20.md) - [JSON receipt](forced-form-item-repair-2026-10-20.json)
- [full-battle-postformfix-2026-10-20](full-battle-postformfix-2026-10-20.md) - [JSON receipt](full-battle-postformfix-2026-10-20.json)
- [item-form-abilities-2026-10-25](item-form-abilities-2026-10-25.md) - [JSON receipt](item-form-abilities-2026-10-25.json)
- [legendary-item-identity-2026-10-25](legendary-item-identity-2026-10-25.md) - [JSON receipt](legendary-item-identity-2026-10-25.json)
- [mega-core-2026-10-23](mega-core-2026-10-23.md) - [JSON receipt](mega-core-2026-10-23.json)
- [mega-design-2026-10-22](mega-design-2026-10-22.md) - [JSON receipt](mega-design-2026-10-22.json)
- [mega-stone-theft-2026-10-27](mega-stone-theft-2026-10-27.md) - [JSON receipt](mega-stone-theft-2026-10-27.json)
- [mega-stones-2026-10-23](mega-stones-2026-10-23.md) - [JSON receipt](mega-stones-2026-10-23.json)
- [memory-drive-theft-2026-10-25](memory-drive-theft-2026-10-25.md) - [JSON receipt](memory-drive-theft-2026-10-25.json)
- [native-stat-items-2026-10-25](native-stat-items-2026-10-25.md) - [JSON receipt](native-stat-items-2026-10-25.json)
- [necrozma-design-2026-10-23](necrozma-design-2026-10-23.md) - [JSON receipt](necrozma-design-2026-10-23.json)
- [necrozma-items-2026-10-24](necrozma-items-2026-10-24.md) - [JSON receipt](necrozma-items-2026-10-24.json)
- [necrozma-release-plan-2026-10-24](necrozma-release-plan-2026-10-24.md) - [JSON receipt](necrozma-release-plan-2026-10-24.json)
- [necrozma-released-local-2026-10-24](necrozma-released-local-2026-10-24.md) - [JSON receipt](necrozma-released-local-2026-10-24.json)
- [necrozma-released-retry-2026-10-24](necrozma-released-retry-2026-10-24.md) - [JSON receipt](necrozma-released-retry-2026-10-24.json)
- [necrozma-retry-release-plan-2026-10-24](necrozma-retry-release-plan-2026-10-24.md) - [JSON receipt](necrozma-retry-release-plan-2026-10-24.json)
- [ogerpon-tera-full-sweep-2026-10-19](ogerpon-tera-full-sweep-2026-10-19.md)
- [origin-primal-rusted-theft-2026-10-25](origin-primal-rusted-theft-2026-10-25.md) - [JSON receipt](origin-primal-rusted-theft-2026-10-25.json)
- [plate-theft-identity-2026-10-25](plate-theft-identity-2026-10-25.md) - [JSON receipt](plate-theft-identity-2026-10-25.json)
- [teraform-zero-local-2026-10-18](teraform-zero-local-2026-10-18.md)
- [ultra-burst-2026-10-25](ultra-burst-2026-10-25.md) - [JSON receipt](ultra-burst-2026-10-25.json)
- [ultra-photon-preparation-erratum-2026-10-25](ultra-photon-preparation-erratum-2026-10-25.md) - [JSON receipt](ultra-photon-preparation-erratum-2026-10-25.json)
- [z-core-2026-10-23](z-core-2026-10-23.md) - [JSON receipt](z-core-2026-10-23.json)
- [z-existing-sources-2026-10-25](z-existing-sources-2026-10-25.md) - [JSON receipt](z-existing-sources-2026-10-25.json)
- [z-next-six-sources-2026-10-29](z-next-six-sources-2026-10-29.md)
- [z-six-physical-sources-2026-10-25](z-six-physical-sources-2026-10-25.md) - [JSON receipt](z-six-physical-sources-2026-10-25.json)
- [z-six-special-sources-2026-10-25](z-six-special-sources-2026-10-25.md) - [JSON receipt](z-six-special-sources-2026-10-25.json)
- [z-six-status-sources-2026-10-25](z-six-status-sources-2026-10-25.md) - [JSON receipt](z-six-status-sources-2026-10-25.json)
- [z-source-scope-2026-10-25](z-source-scope-2026-10-25.md) - [JSON receipt](z-source-scope-2026-10-25.json)
- [z-special-2026-10-23](z-special-2026-10-23.md) - [JSON receipt](z-special-2026-10-23.json)

## Items, acquisition, recovery, and progression

- [ability-items-2026-10-22](ability-items-2026-10-22.md) - [JSON receipt](ability-items-2026-10-22.json)
- [alcremie-sweets-2026-10-21](alcremie-sweets-2026-10-21.md) - [JSON receipt](alcremie-sweets-2026-10-21.json)
- [battle-boosters-2026-10-25](battle-boosters-2026-10-25.md) - [JSON receipt](battle-boosters-2026-10-25.json)
- [battle-damp-egg-player-2026-10-26](battle-damp-egg-player-2026-10-26.md) - [JSON receipt](battle-damp-egg-player-2026-10-26.json)
- [battle-item-repairs-2026-10-20](battle-item-repairs-2026-10-20.md) - [JSON receipt](battle-item-repairs-2026-10-20.json)
- [battle-item-validation-2026-10-22](battle-item-validation-2026-10-22.md) - [JSON receipt](battle-item-validation-2026-10-22.json)
- [battle-items-2026-10-20](battle-items-2026-10-20.md)
- [battle-recovery-concurrency-2026-10-20](battle-recovery-concurrency-2026-10-20.md) - [JSON receipt](battle-recovery-concurrency-2026-10-20.json)
- [battle-recovery-foods-2026-10-22](battle-recovery-foods-2026-10-22.md) - [JSON receipt](battle-recovery-foods-2026-10-22.json)
- [berry-player-routes-2026-10-22](berry-player-routes-2026-10-22.md) - [JSON receipt](berry-player-routes-2026-10-22.json)
- [embargo-item-duration-2026-10-25](embargo-item-duration-2026-10-25.md) - [JSON receipt](embargo-item-duration-2026-10-25.json)
- [ev-mochi-2026-10-25](ev-mochi-2026-10-25.md) - [JSON receipt](ev-mochi-2026-10-25.json)
- [exp-candy-2026-10-25](exp-candy-2026-10-25.md) - [JSON receipt](exp-candy-2026-10-25.json)
- [field-berries-2026-10-20](field-berries-2026-10-20.md) - [JSON receipt](field-berries-2026-10-20.json)
- [field-food-2026-10-21](field-food-2026-10-21.md) - [JSON receipt](field-food-2026-10-21.json)
- [field-medicine-2026-10-20](field-medicine-2026-10-20.md) - [JSON receipt](field-medicine-2026-10-20.json)
- [field-training-2026-10-22](field-training-2026-10-22.md) - [JSON receipt](field-training-2026-10-22.json)
- [finite-item-sources-2026-10-25](finite-item-sources-2026-10-25.md) - [JSON receipt](finite-item-sources-2026-10-25.json)
- [flavor-snacks-2026-10-25](flavor-snacks-2026-10-25.md) - [JSON receipt](flavor-snacks-2026-10-25.json)
- [flavor-snacks-release-plan-2026-10-25](flavor-snacks-release-plan-2026-10-25.md) - [JSON receipt](flavor-snacks-release-plan-2026-10-25.json)
- [flavor-snacks-released-player-2026-10-25](flavor-snacks-released-player-2026-10-25.md) - [JSON receipt](flavor-snacks-released-player-2026-10-25.json)
- [held-status-berries-2026-10-25](held-status-berries-2026-10-25.md) - [JSON receipt](held-status-berries-2026-10-25.json)
- [hyper-training-2026-10-22](hyper-training-2026-10-22.md) - [JSON receipt](hyper-training-2026-10-22.json)
- [hyper-training-fixtures-2026-10-22](hyper-training-fixtures-2026-10-22.md) - [JSON receipt](hyper-training-fixtures-2026-10-22.json)
- [incense-2026-10-22](incense-2026-10-22.md) - [JSON receipt](incense-2026-10-22.json)
- [item-additions-2026-10-29](item-additions-2026-10-29.md) - [JSON receipt](item-additions-2026-10-29.json)
- [item-availability-2026-10-22](item-availability-2026-10-22.md) - [JSON receipt](item-availability-2026-10-22.json)
- [item-availability-2026-10-25](item-availability-2026-10-25.md) - [JSON receipt](item-availability-2026-10-25.json)
- [item-designs-2026-10-22](item-designs-2026-10-22.md) - [JSON receipt](item-designs-2026-10-22.json)
- [item-feedback-2026-10-22](item-feedback-2026-10-22.md) - [JSON receipt](item-feedback-2026-10-22.json)
- [item-followups-2026-10-22](item-followups-2026-10-22.md) - [JSON receipt](item-followups-2026-10-22.json)
- [item-live-2026-10-22](item-live-2026-10-22.md) - [JSON receipt](item-live-2026-10-22.json)
- [item-next-action-2026-10-29](item-next-action-2026-10-29.md) - [JSON receipt](item-next-action-2026-10-29.json)
- [item-plan-execution-2026-10-29](item-plan-execution-2026-10-29.md) - [JSON receipt](item-plan-execution-2026-10-29.json)
- [item-release-plan-2026-10-22](item-release-plan-2026-10-22.md)
- [item-repair-moon-source-plan-2026-10-25](item-repair-moon-source-plan-2026-10-25.md) - [JSON receipt](item-repair-moon-source-plan-2026-10-25.json)
- [item-repair-release-plan-2026-10-25](item-repair-release-plan-2026-10-25.md) - [JSON receipt](item-repair-release-plan-2026-10-25.json)
- [item-repair-release-plan-v2-2026-10-25](item-repair-release-plan-v2-2026-10-25.md) - [JSON receipt](item-repair-release-plan-v2-2026-10-25.json)
- [item-repair-released-player-2026-10-25](item-repair-released-player-2026-10-25.md) - [JSON receipt](item-repair-released-player-2026-10-25.json)
- [item-repairs-2026-10-29](item-repairs-2026-10-29.md) - [JSON receipt](item-repairs-2026-10-29.json)
- [item-replenishment-2026-10-25](item-replenishment-2026-10-25.md) - [JSON receipt](item-replenishment-2026-10-25.json)
- [item-scope-decisions-2026-10-25](item-scope-decisions-2026-10-25.md) - [JSON receipt](item-scope-decisions-2026-10-25.json)
- [item-source-migration-compatibility-2026-10-25](item-source-migration-compatibility-2026-10-25.md) - [JSON receipt](item-source-migration-compatibility-2026-10-25.json)
- [item-source-release-plan-2026-10-25](item-source-release-plan-2026-10-25.md) - [JSON receipt](item-source-release-plan-2026-10-25.json)
- [item-source-released-player-2026-10-25](item-source-released-player-2026-10-25.md) - [JSON receipt](item-source-released-player-2026-10-25.json)
- [item-source-retry-release-plan-2026-10-25](item-source-retry-release-plan-2026-10-25.md) - [JSON receipt](item-source-retry-release-plan-2026-10-25.json)
- [item-support-closeout-2026-10-21](item-support-closeout-2026-10-21.md) - [JSON receipt](item-support-closeout-2026-10-21.json)
- [kubfu-scrolls-2026-10-21](kubfu-scrolls-2026-10-21.md) - [JSON receipt](kubfu-scrolls-2026-10-21.json)
- [legacy-berries-2026-10-22](legacy-berries-2026-10-22.md) - [JSON receipt](legacy-berries-2026-10-22.json)
- [link-cord-2026-10-28](link-cord-2026-10-28.md)
- [link-cord-2026-10-29](link-cord-2026-10-29.md)
- [nature-mint-migration-plan-2026-10-25](nature-mint-migration-plan-2026-10-25.md)
- [nature-mints-2026-10-25](nature-mints-2026-10-25.md) - [JSON receipt](nature-mints-2026-10-25.json)
- [nursery-next-three-real-elapsed-2026-10-29](nursery-next-three-real-elapsed-2026-10-29.md) - [JSON receipt](nursery-next-three-real-elapsed-2026-10-29.json)
- [nursery-seeds-2026-10-25](nursery-seeds-2026-10-25.md) - [JSON receipt](nursery-seeds-2026-10-25.json)
- [peat-block-2026-10-21](peat-block-2026-10-21.md) - [JSON receipt](peat-block-2026-10-21.json)
- [pp-capacity-2026-10-22](pp-capacity-2026-10-22.md) - [JSON receipt](pp-capacity-2026-10-22.json)
- [rare-candy-2026-10-22](rare-candy-2026-10-22.md) - [JSON receipt](rare-candy-2026-10-22.json)
- [reactive-consumption-2026-10-27](reactive-consumption-2026-10-27.md) - [JSON receipt](reactive-consumption-2026-10-27.json)
- [recovery-move-prerequisites-2026-10-25](recovery-move-prerequisites-2026-10-25.md) - [JSON receipt](recovery-move-prerequisites-2026-10-25.json)
- [remaining-item-delivery-2026-10-29](remaining-item-delivery-2026-10-29.md) - [JSON receipt](remaining-item-delivery-2026-10-29.json)
- [remaining-item-fusion-cleanup-supplement-2026-10-26](remaining-item-fusion-cleanup-supplement-2026-10-26.md) - [JSON receipt](remaining-item-fusion-cleanup-supplement-2026-10-26.json)
- [remaining-item-logout-cleanup-plan-2026-10-26](remaining-item-logout-cleanup-plan-2026-10-26.md) - [JSON receipt](remaining-item-logout-cleanup-plan-2026-10-26.json)
- [remaining-item-release-plan-2026-10-26](remaining-item-release-plan-2026-10-26.md) - [JSON receipt](remaining-item-release-plan-2026-10-26.json)
- [remaining-item-released-player-2026-10-26](remaining-item-released-player-2026-10-26.md) - [JSON receipt](remaining-item-released-player-2026-10-26.json)
- [remaining-item-retained-cleanup-plan-2026-10-26](remaining-item-retained-cleanup-plan-2026-10-26.md) - [JSON receipt](remaining-item-retained-cleanup-plan-2026-10-26.json)
- [renewable-item-sources-2026-10-25](renewable-item-sources-2026-10-25.md) - [JSON receipt](renewable-item-sources-2026-10-25.json)
- [restored-item-updates-2026-10-25](restored-item-updates-2026-10-25.md) - [JSON receipt](restored-item-updates-2026-10-25.json)
- [reusable-item-completion-2026-10-26](reusable-item-completion-2026-10-26.md) - [JSON receipt](reusable-item-completion-2026-10-26.json)
- [smoke-ball-2026-10-21](smoke-ball-2026-10-21.md) - [JSON receipt](smoke-ball-2026-10-21.json)
- [synchronize-status-berries-2026-10-25](synchronize-status-berries-2026-10-25.md) - [JSON receipt](synchronize-status-berries-2026-10-25.json)
- [trade-held-evolution-2026-10-21](trade-held-evolution-2026-10-21.md) - [JSON receipt](trade-held-evolution-2026-10-21.json)

## Server lifecycle and reliability

- [reload-port-handoff-2026-10-28](reload-port-handoff-2026-10-28.md)

## Additional machine inventories and receipts

- [battle-item-matrix-2026-10-20](battle-item-matrix-2026-10-20.json)
- [battle-item-support-2026-10-21](battle-item-support-2026-10-21.json)
- [flavor-snacks-player-commands-2026-10-25](flavor-snacks-player-commands-2026-10-25.json)
- [item-availability-additions-index-2026-10-29](item-availability-additions-index-2026-10-29.json)
- [item-availability-battle-boosters-index-2026-10-25](item-availability-battle-boosters-index-2026-10-25.json)
- [item-availability-exp-candy-index-2026-10-25](item-availability-exp-candy-index-2026-10-25.json)
- [item-availability-field-training-seeds-index-2026-10-25](item-availability-field-training-seeds-index-2026-10-25.json)
- [item-availability-final-index-2026-10-29](item-availability-final-index-2026-10-29.json)
- [item-availability-finite-sources-index-2026-10-25](item-availability-finite-sources-index-2026-10-25.json)
- [item-availability-flavor-snacks-index-2026-10-25](item-availability-flavor-snacks-index-2026-10-25.json)
- [item-availability-index-2026-10-22](item-availability-index-2026-10-22.json)
- [item-availability-index-2026-10-25](item-availability-index-2026-10-25.json)
- [item-availability-nature-mints-index-2026-10-25](item-availability-nature-mints-index-2026-10-25.json)
- [item-availability-physical-status-z-index-2026-10-25](item-availability-physical-status-z-index-2026-10-25.json)
- [item-availability-released-index-2026-10-26](item-availability-released-index-2026-10-26.json)
- [item-availability-repairs-index-2026-10-29](item-availability-repairs-index-2026-10-29.json)
- [item-availability-six-z-sources-index-2026-10-25](item-availability-six-z-sources-index-2026-10-25.json)
- [item-availability-ultra-index-2026-10-25](item-availability-ultra-index-2026-10-25.json)
- [item-availability-world-2026-10-25](item-availability-world-2026-10-25.json)
- [item-availability-z-sources-index-2026-10-25](item-availability-z-sources-index-2026-10-25.json)
- [item-followup-index-2026-10-22](item-followup-index-2026-10-22.json)
- [item-issue-audit-2026-10-29](item-issue-audit-2026-10-29.json)
- [item-issue-publication-2026-10-29](item-issue-publication-2026-10-29.json)
- [item-repair-gate-closeout-2026-10-29](item-repair-gate-closeout-2026-10-29.json)
- [item-repair-player-commands-2026-10-25](item-repair-player-commands-2026-10-25.json)
- [item-source-player-commands-2026-10-25](item-source-player-commands-2026-10-25.json)
- [item-stat-type-plan-2026-10-22](item-stat-type-plan-2026-10-22.json)
- [item-world-snapshot-2026-10-22](item-world-snapshot-2026-10-22.json)
- [necrozma-pp-repair-2026-10-24](necrozma-pp-repair-2026-10-24.json)
- [remaining-item-player-commands-2026-10-26](remaining-item-player-commands-2026-10-26.json)

## Report assets

- [battle-ui-live-multi-fusion-2026-10-27.png](assets/battle-ui-live-multi-fusion-2026-10-27.png)
- [october-four-player-2026-10-24.png](october-four-player-2026-10-24.png)
- [october-guide-2026-10-24.png](october-guide-2026-10-24.png)
- [october-multi-final-2026-10-24.png](october-multi-final-2026-10-24.png)

## Adding evidence

Link each new report in the matching system section, together with its
companion receipt. Preserve the tested build, date, environment, skipped
scope, and any later correction links. Keep raw local observations and
private fixtures in the ignored artifact location described by the report.
