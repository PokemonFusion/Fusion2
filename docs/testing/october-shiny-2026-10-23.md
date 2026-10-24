# Saved shiny summaries and consent follow-up (#725/#726)

October 23, 2026 candidate based on `200675c`. [JSON evidence](october-shiny-2026-10-23.json)
records source/log fingerprints and actual ordinary trade/market command replies.
These are local PostgreSQL checks with real User/Account models and Player
permission, with outbound transport captured. No live socket, deployment or
hosted-CI success is claimed.

## Defect and resulting behavior

Owned Pokemon persist `is_shiny`. The advertised summary incorrectly looked up
`shiny`, producing a missing value that trades rendered as ordinary and listings
displayed as `None`. The transfer fingerprint already included the correct saved
field, and transfers preserved it; the defect was the advertised state.

New snapshots now record a real boolean from `is_shiny`; ordinary and shiny
sources display correctly and preserve their flag after trade/purchase. Pending
older offers/listings without that boolean must be cancelled/reissued or relisted
before consent or payment. Their immutable terms are never rewritten or filled
from a later owner's live state. Displays explicitly say the value was unrecorded.
Completed receipts retain their existing idempotent replay behavior.

## Verification

- **107 database cases pass across six suites**: 19 trade,
  18 marketplace, ownership, Fusion, Daycare and UI. Four added regressions cover
  shiny/plain display and transfer plus old incomplete offer/listing rejection,
  cancellation and successful fresh terms.
- A fresh callback-enabled full combined suite passes: **4915 passed /
  4014 skipped**. No model/migration change is required.
- **1065 Python sources** remain fixed across the final checks; the
  staged Git-filtered blob fingerprint is added before commit.
- `git diff --check` passes. Existing reload/deprecation/logging diagnostics remain.

The [trade](../operations/consent-trading.md) and [marketplace](../operations/marketplace.md)
contracts now explain legacy-term recovery. This repair adds no currency, asset,
progression or plot-only support. Prepared breeding work is separate.
