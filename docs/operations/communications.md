# Character communication state and permissions (#732)

## Mail

`+mail/send CHARACTER=SUBJECT/BODY` sends as the active character to one character.
The recipient lookup includes the configured `pokemon.user.User` typeclass and
other Character subclasses; rooms and accounts are not valid character targets.
Accounts do not substitute their numeric ID for a character. Same-account alts
have separate inboxes, sender identities and read state.

`+mail/read ID`, `+mail/unread ID`, `+mail/reply ID=BODY` and `+mail/delete ID`
authorize the current character against the actual visible receiver list.
Delete means archive/hide for that recipient, not destruction of the shared Msg.
Other recipients retain their inbox entry and read state. Repeating a read/unread
is safe; an already-archived or foreign ID returns no visible mail and changes
nothing. Empty/failed replies do not consume unread state. Sender/body/receiver
writes and read-state updates use transactions; notifications follow commit and
a transport failure does not undo saved delivery.

The ordinary send route has one target. Existing/staff-created multi-recipient
messages are supported with one read/unread override per character on the existing
Msg/tag storage. The old shared `pf2_mail:unread` tag is an untouched-recipient
baseline, not an aggregate unread flag. It cannot reconstruct which recipient
read an old shared message before this fix. Preserve that baseline until a
recipient explicitly reads/marks unread; never invent historical per-recipient
activity. Helpers examining shared mail must supply the intended character.

Two sessions playing the same character share that character's state. Reading
as one alt never consumes the other alt's state. The account selector/login
summary totals only the account's owned characters, without exposing subjects or
bodies. Reconnect and concurrent reads consult current saved state.

## Boards

Board read state and current-board selection are per character, including same-account alts.
`+bblist` shows only readable boards and their current numbers; use those numbers
with `+bbread NUMBER/POST`, `+bbnext NUMBER` and `+bbcatchup NUMBER` (or `all`).
Numbers are the current visible list positions. A board name containing spaces
can be used for a single `+bbread NAME/POST`; catchup accepts board-number tokens.

Read/post/delete/edit locks remain authoritative. Public boards remain public;
the Staff board and restricted posting/editing remain gated by their existing
locks. Ordinary authors can delete their own post where the board is readable;
editing remains on the existing staff command. A cached current-board selection
or an open editor never bypasses a later lock change. Editor saves recheck access
and bind the stable post identity, refusing if deletion/move changed its index.

Posts and read tracking remain on the existing persistent board Script. Mutations
and read/legacy normalization serialize on its row, refresh stored Attribute and
lock caches, and roll back together. Nested helpers share one operation lock so
an unread scan does not re-lock/reload the board for every post. Actual Evennia
Saver mappings are accepted when reading tracked IDs; pure dictionaries in old
tests did not expose that distinction. New posts use unique stable IDs even if a
deleted list position and clock tick repeat. Existing IDs and legacy last-index
read progress are retained; removing one post does not mark its successor read.
Notifications are emitted only for committed posts.

## Channels

Channel subscriptions and delivery remain account-scoped, with the existing
public/private listen, send and control locks. Public traffic is public to its
authorized subscribers; it is not private character mail. A character name on an
IC channel send comes from the command's actual sending session and must belong
to that account's character roster. A foreign/stale/unowned session cannot lend
another character's name. OOC/ambiguous sends display the marked `(A)` account.

Each delivery rechecks the channel's current listen permission. A former public
subscriber does not keep receiving traffic after a channel becomes restricted.
Mute handling, per-recipient hooks and history remain on the existing channel;
one recipient filtering a message does not stop other authorized recipients.
The normal command still checks send permission, and framework history lookup
still requires listen/control access. No new messaging platform, moderation UI
or website messaging is introduced.

## Evidence boundary

Production-backed checks use actual Msg/receiver/tag rows, board Script Attributes,
channel subscriptions and typed User/Account records. Ordinary Player fixtures,
same-account alts and a separate account are distinct from a separate tagged
staff fixture used only for setup/editor cases. Command/callback replay and
captured session/transport metadata are local automated evidence. A separate
two-character plus separate-account ordinary website/game smoke record is
required before #732 closes; neither this document nor unit coverage claims
live sockets or deployment.
