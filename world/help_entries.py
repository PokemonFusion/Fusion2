"""
File-based help entries. These complements command-based help and help entries
added in the database using the `sethelp` command in-game.

Control where Evennia reads these entries with `settings.FILE_HELP_ENTRY_MODULES`,
which is a list of python-paths to modules to read.

A module like this should hold a global `HELP_ENTRY_DICTS` list, containing
dicts that each represent a help entry. If no `HELP_ENTRY_DICTS` variable is
given, all top-level variables that are dicts in the module are read as help
entries.

Each dict is on the form
::

    {'key': <str>,
     'text': <str>}``     # the actual help text. Can contain # subtopic sections
     'category': <str>,   # optional, otherwise settings.DEFAULT_HELP_CATEGORY
     'aliases': <list>,   # optional
     'locks': <str>       # optional, 'view' controls seeing in help index, 'read'
                          #           if the entry can be read. If 'view' is unset,
                          #           'read' is used for the index. If unset, everyone
                          #           can read/view the entry.

"""

HELP_ENTRY_DICTS = [
	{
		"key": "getting started",
		"aliases": ["start", "new player", "quickstart", "first steps"],
		"category": "Guide",
		"text": """
Welcome to Pokemon Fusion 2.

You play by typing a command and pressing Enter. Keep any + at the start of a
command. In examples such as goic <name>, replace <name> with your character's
name and leave out the angle brackets.

Already finished character setup? Type look, then help first outing for a
short introduction to moving, talking, and trying your first wild battle.

# First Steps

1. Register once. The website and game use the same account and password.
   Your account is your login; a character is the person you play.
2. Open Play in Browser. If asked to connect, use that same account.
3. Check the character list. Registration normally creates your first
   character with your account name. To play the first character listed, type:
   goic 1
   You can also use goic <name>. Only use charcreate <name> if you have no
   character yet or want to create another one.
4. Once inside the game, start character setup with:
   chargen
   Choose a human trainer with a starter Pokemon, or a Fusion who can battle
   as their own Pokemon form. Follow the menu's prompts one at a time.
5. Human trainers choose their starter in the menu. Type starterlist when
   asked for a species. Outside the menu, +starters lists starter options;
   +starter opens or resumes human starter selection if needed.

# After Setup

Type look to see your room. To move, type one of the listed exit names as a
command. Type +sheet to see your character and battle information.

Your next guide is help first outing. It walks through the Alpha Test Hub's
beginner route and +hunt, with instructions for getting help along the way.
You can also stay and chat: public Hi, I'm new! speaks on the public channel.

# Useful Website Links

Home shows the current play status. Player Hub shows a read-only overview of
your characters, party, boxed Pokemon, inventory, and badges once you have a
character.
		""",
	},
	{
		"key": "first outing",
		"aliases": ["first battle", "after setup"],
		"category": "Guide",
		"text": """
Your first outing

Start with a small goal: learn to move, try a wild battle when you are ready,
and find your way back. You can explore or chat at your own pace.

1. Type look and press Enter. Read the room name, description, and exits.
   An exit name is also a command: type it to move to the next room.
2. Type +sheet to inspect your character. Human trainers have a starter;
   Fusions can battle as their own form, even with no separate party Pokemon.
3. At Alpha Test Hub, type low grass to enter the beginner route. If you
   aren't at the hub, follow your room's listed exits. If you cannot find it,
   type: public Hi, I'm new. How do I reach Alpha Test Hub from here?
4. In Alpha Route 1 - Low Grass, type +hunt to look for a wild Pokemon.
   Follow any selection prompt, then wait for the battle display to ask for
   your action. Use the commands it shows. Type help battle basics for the
   battle commands, or +status to check a battle already in progress.
5. When the battle has ended, type look. From Low Grass, type hub to return.
   At Alpha Test Hub, +heal restores your party Pokemon before another outing.

If a command says you can't hunt here, check the room name with look: +hunt
works in encounter rooms, not the hub. If no Pokemon can battle, check +sheet
and heal your party at the hub. If your Fusion still cannot battle or you get
stuck, use public to ask for help. To send staff a support request, type:
   +request I need help starting. Here is what happened: ...
Replace the dots with the command you tried and the response you received.

Prefer to meet people first? Type public Hi, I'm new! to introduce yourself.
Use say Hello! to talk to people in your room. No battle is required to chat.

Type help getting started to return to account and character setup guidance.
		""",
	},
	{
		"key": "core commands",
		"aliases": ["commands", "command reference", "basics"],
		"category": "Guide",
		"text": """
These are the main everyday commands for regular players.

# Account And Character

charcreate <name>      Create a character on your account.
goic <name||number>   Enter the game as one of your characters.
goooc                 Leave your character and return out-of-character.

# Looking And Talking

look                  Look at your current room.
look <thing>          Look at something nearby.
+glance               See online characters in the room.
ws                    Alias for +glance.
+where                See online characters and visible locations.
+profile              View or edit RP profile fields.
+mail                 Read or send character mail.
+request              Send a support request to staff.
+staff                Show the public staff roster.
ooc <message>         Speak out-of-character in the room.
ooc :<pose>           Pose out-of-character.
help                  Open the in-game help index.
help <topic>          Read help for a command or guide topic.

# Trainer Display

+sheet                Show your trainer card.
party                 Alias for +sheet.
+sheet/brief          Show a compact trainer card.
+party                List your party Pokemon.
+party <slot>         Show a party Pokemon by slot.
+party/all            Show full sheets for every party Pokemon.
+inventory            Show your item inventory.

# Fusion

+fuse/temp <slot>              Temporarily fuse with a party Pokemon.
+fuse/permanent <slot> confirm Permanently unlock a fusion form.
+unfuse                        Leave your current fusion form.
+fusion                        List or choose permanent fusion forms.
+fusion/order                  Toggle whether your fusion enters battle first.
+fusion/fight                  Toggle whether your fusion joins battles.

# Display Preferences

+uimode               Show your current room display mode.
+uimode fancy         Rich room layout.
+uimode simple        Lower-detail room layout.
+uimode boxed         Boxed fallback room layout.
+uimode screenreader  Screen-reader friendly room layout.
+uimode ascii         Simple room layout and ASCII battle symbols.
+uimode unicode       Fancy room layout and Unicode battle symbols.
+uitheme              Show your current room color theme.
+uitheme <color>      Choose green, blue, red, magenta, cyan, or white.
+battleui/style       Show or change your battle UI style.
		""",
	},
	{
		"key": "character mail",
		"aliases": ["mail", "+mail", "inbox"],
		"category": "Guide",
		"text": """
Character mail is private asynchronous mail between IC characters.

# Commands

+mail                                  Show your inbox.
+mail/send <character>=<subject>/<message>  Send mail.
+mail/read <id>                        Read a message.
+mail/reply <id>=<message>             Reply to the sender.
+mail/delete <id>                      Archive a message from your inbox.
+mail/unread <id>                      Mark a message unread.

Unread mail is shown on the account character-selection screen when you log in
or return out-of-character.
		""",
	},
	{
		"key": "message boards",
		"aliases": ["boards", "bboard", "+bboard", "+bbread", "+bbpost"],
		"category": "Guide",
		"text": """
Message boards are persistent public or staff-gated posts.

# Commands

+bbhelp                       Show board command help.
+bbread                       Show the board list.
+bbread <board>               List posts in a board.
+bbread <board>/<post>        Read a post.
+bbread <board> #unread       List unread posts in a board.
+bbpost <board>               Create a post.
+bbremove <board>/<post>      Remove one of your posts.
+bbcatchup all                Mark all visible boards read.
+bbcatchup <board>            Mark one board read.
+bbnext                       Read the next unread board post.
+bbnext <board>               Read the next unread post in one board.

Boards can be referenced by the number shown in +bbread or by board name.

# Staff

+bbseed                       Create the default PF1-style board sections.
		""",
	},
	{
		"key": "support requests",
		"aliases": ["requests", "+request", "tickets", "help request"],
		"category": "Guide",
		"text": """
Use +request when you need help from staff or need to report something that
should stay out of public chat.

# Player Commands

+request <message>          Submit a support request.
+request/list               List your requests.
+request/show <id>          Read one of your requests.
+request/close <id> [note]  Close one of your requests.

# Staff Commands

+request/queue [open||closed||all]  List support requests.
+request/claim <id>               Claim an open request.
+request/close <id> [note]        Close a request after handling it.

Requests are tied to your account and include your current character and room
when available.
		""",
	},
	{
		"key": "staff notes",
		"aliases": ["+note", "+notes", "notes"],
		"category": "Staff",
		"locks": (
			"read:perm(Helper) or perm(Validator) or perm(Builder) or perm(Admin) "
			"or perm(Developer) or perm(Wizards)"
		),
		"text": """
Staff notes are private operational notes on accounts or characters.

# Commands

+note <target>              List staff notes on a target.
+note/show <target>=<id>    Read a staff note.
+note/add <target>=<note>   Add a staff note.
+note/del <target>=<id>     Remove a staff note.

# Target Forms

*<account>        Target an account.
account:<name>    Target an account.
char:<name>       Target a character.

Use staff notes for moderation, validation, continuity, and support context.
They are not player-facing profile fields.
		""",
	},
	{
		"key": "trading",
		"aliases": ["pokemon trading", "consent trades", "pokemon gifts"],
		"category": "Guide",
		"text": """
Trades are private offers between two characters. Even characters sharing an
account must each act for themselves. There are no fees, payments, EXP grants or
automatic evolutions. Pokemon keep their ID, original trainer, held item, HP,
status, moves and PP.

# Gift

Ash:   +trade offer Misty=3
Misty: +trade inspect <offer ID>
Misty: +trade accept <offer ID>

The offer command shows its ID. +trade lists your pending offers and recent
outcomes after reconnect. Inspect the exact offer before accepting or countering;
another character's inspection cannot supply your consent.

# Swap

After inspecting Ash's offer, Misty chooses her own Pokemon:
Misty: +trade counter <offer ID>=<her Pokemon ID>
Ash:   +trade inspect <new offer ID>
Ash:   +trade accept <new offer ID>

A counteroffer closes the old offer and creates new terms. Previous inspection
or consent does not carry forward. Each side offers one Pokemon. Use a party
slot (1-6 or slot3), or a full/unique Pokemon ID prefix of at least eight hex
characters from +box or +pokemon to offer a boxed Pokemon directly.

# Closing And Recovery

+trade decline <offer ID>   Intended recipient declines.
+trade cancel <offer ID>    Either participant closes the offer.
+trade inspect <offer ID>   Inspect pending or completed/cancelled outcomes.

Offers last 15 minutes. Expired offers cannot complete; cancel them to release
their reservations. Changed Pokemon state requires new terms. Pending offers
are shown first (up to 30); close them to expose older offers. Repeating a
completed acceptance returns its historical outcome and never trades again.

The offered Pokemon is reserved: finish/cancel the offer before moving, using
items on, editing moves for, releasing or fusing it. Battles, Fusion forms and
market/Daycare/breeding reservations block transfer. A boxed offer lets its
owner battle with other party members, but the trade itself must wait until
both characters finish battle. Failed checks move nothing.

Recipients use a free party slot, otherwise a box. Existing boxes have no size
limit. Both sides of a swap save together. Trades do not automatically evolve
Pokemon; help growth and moves describes the supported manual held-item
evolution equivalents.

Saved moveset activation/management requires a Pokemon Center. A pending trade
or an old move menu cannot edit a Pokemon after ownership changes.
		""",
	},
	{
		"key": "pokemon and storage",
		"aliases": ["storage", "party management", "boxes", "pokemon storage"],
		"category": "Guide",
		"text": """
Your active party is what you bring into battles. Extra Pokemon live in storage
boxes and can be moved around outside battle.

# Viewing Pokemon

+party                       List your party.
+party <slot>                Show one party Pokemon.
+party/moves <slot>          Show a moves-focused sheet.
+box [box]                   Show a storage box.
+box/all                     Show all Pokemon in storage.
+pokemon <id>                Show a Pokemon by its unique id.

# Moving Pokemon

+box/deposit <pokemon_id> [box]              Move a party Pokemon into storage.
+box/withdraw <pokemon_id> [box]             Move a boxed Pokemon into your party.
+box/swap <pokemon_id> <party_slot> [box]    Swap a boxed Pokemon with a party slot.
+storage                                      Open Pokemon storage at a Pokemon Center.

Trading uses private, persistent offers. Type help trading for the gift/swap flow.
No Pokemon changes owner until the intended recipient inspects and accepts the
exact offer. Party and boxed Pokemon are supported; active activities block trades.

# Held Items

+hold <slot>=<item>    Equip or replace a party Pokemon's held item.
+hold <slot>=          Remove its held item.

Held items come from trainer inventory or an exact carried item. Replacing or
removing an item returns the previous item to trainer inventory. For example:
+hold 2=Oran Berry, then +hold 2= to remove it.

Party numbers stay the same across +party, +switch, storage and moveset menus,
including empty slots. Box menu numbers identify entries within that box.
If your active Fusion joins a full party in battle, use +switch fusion to
select it. +switch lists the available party slots and Fusion choice.

Storage commands cannot be used while your character is locked into an active
battle.
		""",
	},
	{
		"key": "fusion",
		"aliases": ["fuse", "fusion forms", "+fusion", "+tempfuse", "+permfuse", "+unfuse"],
		"category": "Guide",
		"text": """
Fusion means an anthro Pokemon form made from a trainer and Pokemon. It is not
Pokemon-to-Pokemon splicing. Fusion commands cannot be used while you are in an
active battle.

# Temporary Fusion

+fuse/temp <slot>     Temporarily fuse with a party Pokemon.
+tempfuse slot<slot>  Legacy alias for +fuse/temp.

Temporary fusion requires Bond 140. The Pokemon cannot be an egg, cannot be
holding an item, and cannot be breeding or carrying an egg. The Pokemon leaves
your party while fused and returns to your party or storage when you use
+unfuse.

# Permanent Fusion

+fuse/permanent <slot> confirm  Permanently unlock a fusion form.
+permfuse slot<slot> confirm    Legacy alias for +fuse/permanent.

Permanent fusion requires Bond 255. The source Pokemon becomes part of the
character and is not returned as a separate party Pokemon when you unfuse.

# Form Control

+unfuse                    Return to human form or end a temporary fusion.
+fusion                    List current and unlocked fusion forms.
+fusion <number||species>  Take an unlocked permanent fusion form.
+forms                     Alias for +fusion.

# Battle Preferences

+fusion/order [first||normal]  Choose whether your fusion form enters first.
+mefirst                      Legacy toggle for +fusion/order.
+fusion/fight [on||off]        Choose whether your active fusion joins battles.
+mefight                      Legacy toggle for +fusion/fight.
		""",
	},
	{
		"key": "exploring and hunting",
		"aliases": ["hunting", "exploration", "wild pokemon", "encounters"],
		"category": "Guide",
		"text": """
Exploration is room based. Read each room, follow exits, and hunt where the
area supports wild encounters.

# Exploring

look              Read the current room.
look <thing>      Inspect a character, exit, object, or feature.
+glance           See online characters in the room.
ws                Alias for +glance.
+where            See online characters and visible locations.

Rooms usually list exits by name. Type an exit name to move through it. Some
rooms may have highlighted shortcut letters in their exit names.

# Hunting

+hunt             Attempt to find a wild Pokemon in the current room.
+hunt/leave       Leave a hunting instance if you are inside one.
+adventure/list   List compact adventure instances available from Adventure Hall.
+adventure/start  Start a solo adventure from Adventure Hall.
+adventure/choose Choose an authored route when the Adventure display offers one.
+adventure/retry  Retry a saved encounter result after a temporary failure.
+adventure/claim  Claim unpaid completion rewards, including after leaving a run.
+adventure/look   Redisplay your virtual location, exits, actions, and objectives.
+adventure/leave  Leave your active adventure.

If a wild Pokemon appears, the game moves you into battle. From there, use
battle commands such as +attack, +switch, +item, or +flee.

# Shops And Centers

+heal             Heal your party at a Pokemon Center.
+storage          Open Pokemon storage at a Pokemon Center.
+movesets         Manage saved movesets at a Pokemon Center.
+store            Open an item shop when one is present.
+vend [amount]    Use a nearby vending machine.
help item availability  Explain item sources, stock and supported use routes.
		""",
	},
	{
		"key": "battle basics",
		"aliases": ["battle", "fighting", "combat", "battle commands"],
		"category": "Guide",
		"text": """
Battles are turn based. When the battle is waiting for you, choose one action.
If the game says it is not waiting for your command, wait for the next prompt or
refresh the battle view.

# Main Battle Actions

+battle/attack <move> [target]   Use a move.
+attack <move> [target]          Short form of +battle/attack.
+attack /menu                    Open the move menu.
+battle/switch <slot>            Switch to another party Pokemon.
+switch <slot>                   Short form of +battle/switch.
+battle/item <item>              Ready an item for battle.
+item <item>                     Short form of +battle/item.
+battle/flee                     Try to run from a wild battle.
+flee                            Short form of +battle/flee.
+battle/concede                  Forfeit an active battle after confirmation.
+concede yes                     Confirm concession without the prompt.

Equip Smoke Ball before battle with +hold <slot>=Smoke Ball. Its acting holder
can +flee from eligible wild encounters, including trapping abilities, without
consuming it. Item suppression, trainer/PvP and no-flee restrictions still apply.
Use +flee for this held effect; +item Smoke Ball does not throw a capture ball.

# Battle Information

+battleui              Redraw your current battle view.
+battleui <character>  View another character's current battle if visible.
+status                Show field, side, status, and active Pokemon effects.
+status brief          Show a shorter effects panel.
+status me             Focus the panel on your side.
+status opp            Focus the panel on the opposing side.

# Spectating

+watch <player>               Watch another trainer's active battle.
+unwatch                      Stop watching.
+watch/battle <battle id>     Watch a battle by id.
+watch/stop <battle id>       Stop watching a battle by id.

For multi-target battles, targets are written as positions such as A1, A2, B1,
or B2. If there is only one valid target, the game usually chooses it for you.
		""",
	},
	{
		"key": "growth and moves",
		"aliases": ["growth", "moves", "progression", "evolution"],
		"category": "Guide",
		"text": """
Pokemon improve through battle rewards, move learning, items, and evolution.
Most maintenance commands are used outside battle.

# Healing And Experience

+heal          Heal your party at a Pokemon Center.
+expshare     Toggle EXP Share for your party.

# Learning Moves

+learn                 List Pokemon with level-up moves available.
+learn <slot>          Open the move-learning flow for a party slot.
+teach <slot>=<move>   Teach a valid move to a party Pokemon.
+moves/use <slot>=<set> Switch to a saved moveset at a Pokemon Center.
+movesets              Manage saved movesets at a Pokemon Center.

# Items

+inventory             Show your inventory.
+use Rare Candy=2      Give a Rare Candy to the Pokemon in party slot 2.
+use PP Up=2           Increase a move's maximum PP (prompts for the move).
+use PP Max=2          Increase PP capacity with a PP Max (prompts for a move).

+use Potion=3          Heal the Pokemon in canonical party slot 3.
+use Full Heal=3       Cure a persistent status condition.
+use Revive=6          Revive the fainted Pokemon in party slot 6.
+use Energy Root=3     Heal with an herb (also lowers friendship on success).
+use Ether=3/Water Gun Restore PP for a selected active move.
+use Max Ether=3/4     Fully restore PP in active move slot 4.
+use Elixir=fusion     Restore PP to all moves of your current Fusion.

Medicine targets accept canonical party slots (including gaps), unambiguous
Pokemon names, full Pokemon IDs, or fusion for your current Fusion. Eggs and
boxed Pokemon cannot use medicine. Ether and Max Ether restore the first
depleted active move if no /move is supplied. Elixirs restore all active moves.
An ineffective use consumes no item and applies no herbal friendship penalty.
Each successful medicine use consumes one item. Energy Powder/Heal Powder
lower friendship by 5 below 200 or 10 at 200+; Energy Root by 10/15 and Revival
Herb by 15/20, with a floor of zero.
PP Up and PP Max increase PP capacity; at their prompt use +use <move name or number>.
During battle use +item <item>. +heal restores your party at a Pokemon Center.

+use Oran Berry=3      Feed an existing recovery berry to a party Pokemon.
+use Berry Juice=3     Restore up to 20 HP.
+use Leppa Berry=3/4   Restore up to 10 PP in active move slot 4.
+use Pomeg Berry=3     Lower HP EVs by up to 10 and raise friendship.

Feedable HP items: Oran (10 HP), Sitrus (1/4 max HP), Figy/Wiki/Mago/Aguav/
Iapapa (1/3 max HP), and Berry Juice (20 HP). Field flavor recovery does not
apply combat-only confusion. Cheri/Chesto/Pecha/Rawst/Aspear cure paralysis/
sleep/poison or toxic/burn/freeze; Lum cures any major saved condition.
Leppa uses the same move selector and caps as Ether. Recovery cannot revive.
Pomeg/Kelpsy/Qualot/Hondew/Grepa/Tamato reduce HP/Atk/Def/SpA/SpD/Spe EVs
by up to 10, floored at zero. EV berries add friendship: 10 below 100, 5 below
200, or 2 at 200+, capped at 255. They work if either effect is useful, including
friendship at zero EVs. Pomeg preserves missing HP after max HP falls, keeps
living Pokemon at least at 1 HP and leaves fainted Pokemon fainted.
Other combat-trigger, confusion-only and contest berries cannot be fed with
+use. These field rules do not change held berry consumption during battle.
Escape Rope field use is not implemented.

+use Fresh Water=3    Restore up to 30 HP (Soda Pop 50, Lemonade 70,
                     Moomoo Milk 100, Sweet Heart 20).
+use Lava Cookie=3    Cure a major saved status (also Old Gateau,
                     Casteliacone, Lumiose Galette, Shalour Sable,
                     Big Malasada and Pewter Crunchies).
+use Max Honey=6      Revive one fainted target to full HP; no unlock effect.
+use Sacred Ash=party Revive eligible fainted canonical party members with
                     one item. Living members, eggs, boxes and all Fusion
                     reservations remain untouched.
These equivalents use field medicine checks and accept no /move selector.
During battle, use +item Fresh Water=3 or +item Max Honey=3. Sacred Ash stays
field-only. Ineffective uses and failed writes consume nothing.
Buy only from shops/rewards deliberately configured to offer them; adding the
definitions does not stock a room or grant a player anything.

# Evolution

+evolve <pokemon_id> [item] [=<target>]
                            Attempt to evolve a Pokemon. Some evolutions may
                               need an item or other condition.

For ordinary Ursaluna, copy Ursaring's full ID from +party <slot> and use
+evolve <pokemon_id> Peat Block. This consumes one bag copy. PF2 replaces the
full-moon requirement with this explicit item action: no time/region/moon flag
is needed. A held-only copy does not activate it. Bloodmoon is not a target.
Peat Block acquisition uses shops/rewards deliberately configured to offer it.

Kubfu uses +evolve <full ID> Scroll of Darkness for Urshifu (Single Strike), or
+evolve <full ID> Scroll of Waters for Urshifu-Rapid-Strike. One bag copy is
consumed on success. No tower completion, extra level or friendship condition
is required. Optional =Urshifu or =Urshifu-Rapid-Strike must match the Scroll.
Held-only copies do not activate evolution, and evolved Urshifu cannot switch
style with a Scroll. Acquisition uses deliberately configured shops/rewards.

For Kingambit, your native Bisharp must personally finish three authored
Crest-bearing Bisharp leaders in won NPC/wild battles, then gain a level.
+party <slot> shows the count and next level. Use +evolve <full ID> without a
bag item. Your Crest/held item is not consumed. PvP, losses, flee/capture,
aborted battles, EXP Share, transformed holders and fake flags give no credit.

For Milcery, first equip Berry, Clover, Flower, Love, Ribbon, Star or Strawberry
Sweet with +hold <slot>=<complete Sweet name>. Then +evolve <pokemon_id> is PF2's
spin equivalent and selects Vanilla Cream. Copy the full ID from +party <slot>.
To choose a listed cream, use e.g.
+evolve <pokemon_id>=Alcremie-Ruby-Cream. Other allowed cream suffixes are
Matcha-Cream, Mint-Cream, Lemon-Cream, Salted-Cream, Ruby-Swirl, Caramel-Swirl
and Rainbow-Swirl (all with the Alcremie- prefix). The held Sweet is consumed
once; do not supply a second bag Sweet to +evolve. +party <slot> shows the saved
cream and Sweet decoration. Gmax is not an evolution target. Eggs, reserved
Pokemon and Pokemon in battle cannot use this route.

Existing trade-held items have a direct, non-transfer evolution equivalent:
equip with +hold, copy the full ID from +party <slot>, then +evolve <pokemon_id>
without a bag item. Clamperl: Deep Sea Scale -> Gorebyss / Deep Sea Tooth ->
Huntail; Seadra: Dragon Scale -> Kingdra; Porygon: Up-Grade -> Porygon2;
Porygon2: Dubious Disc -> Porygon-Z; Electabuzz: Electirizer -> Electivire;
Magmar: Magmarizer -> Magmortar; Poliwhirl/Slowpoke: King's Rock ->
Politoed/Slowking; Onix/Scyther/Nohface: Metal Coat -> Steelix/Scizor/Kitsunoh;
Feebas: Prism Scale -> Milotic; Rhydon: Protector -> Rhyperior; Dusclops:
Reaper Cloth -> Dusknoir; Spritzee: Sachet -> Aromatisse; Swirlix: Whipped Dream
-> Slurpuff. Only the held copy is consumed; bag copies, owner and party/box
placement stay unchanged. Eggs, Fusion reservations, battles and Everstone
still block evolution. At the same level, explicitly choose =Porygon-Z after
equipping Dubious Disc for Porygon's second evolution. A trade does not trigger
automatic evolution; use these manual item equivalents. Non-item and
partner-species trade evolution triggers remain unsupported.
		""",
	},
	{
		"key": "dex reference",
		"aliases": ["pokedex", "dex", "movedex", "itemdex", "reference"],
		"category": "Guide",
		"text": """
Use the dex commands when you need Pokemon, move, item, or learnset information.

# Pokemon

+dex <name or number>          Look up a Pokemon.
+dex                           List the national dex.
+dex/<region>                  List a regional dex.
+dex/<region> <number>         Look up a regional dex number.
+dex/all                       List positive-numbered Pokemon, including forms.
+dexnum <number>               Look up a National Dex number.
+starters                      List valid starter Pokemon.

# Moves And Items

+movedex <move>      Look up move details.
+mdex <move>         Alias for +movedex.
+learnset <pokemon>  Show a Pokemon's learnset.
+itemdex <item>      Look up item details.

Names do not have to be perfect. Several dex commands will suggest close
matches when they can.
		""",
	},
	{
		"key": "pvp and spectating",
		"aliases": ["pvp", "player battles", "duels", "watching"],
		"category": "Guide",
		"text": """
Player-vs-player battles are started through requests in the same room. Both
players need usable Pokemon and must not already be in battle.

# PvP Flow

+pvp                   Show the PvP command summary.
+pvp/list              List open PvP requests in the room.
+pvp/create            Create an open request.
+pvp/create <password> Create a passworded request.
+pvp/join <player>     Join a request.
+pvp/join <player> <password>
+pvp/start             Start the battle once someone has joined your request.
+pvp/abort             Cancel your request.

# Watching Battles

+watch <player>              Watch another trainer's active battle.
+unwatch                     Stop watching.
+watch/battle <battle id>    Watch a battle by id.
+watch/stop <battle id>      Stop watching a battle by id.
+status list                 List battles you are in or watching.
+status next                 Move your status focus to the next watched battle.
+status prev                 Move your status focus to the previous watched battle.
		""",
	},
	{
		"key": "item availability",
		"aliases": ["item sources", "finding items", "obtainable items"],
		"category": "Guide",
		"text": """
Use +store in a configured shop, choose Buy items, then enter a displayed name
and amount, such as Potion 1. The shop needs stock and you need enough money.
Use +vend <machine name> 1 at a dispenser; one request may give a bundle.
+inventory shows owned copies. +itemdex descriptions do not prove shop stock.

The authored Alpha Meadow Survey gives a Potion on your first completion.
Use +adventure/list and +adventure/info alpha_meadow to inspect the route.
Use +adventure/claim for a pending completed reward; repeats do not farm it.
The alpha build recipe includes Rare Candy vending, but a recipe does not
guarantee that its dispenser exists in the current world.

Outside battle, examples include +use Potion=3, +use Oran Berry=3,
+use Ether=3/Water Gun and +use Pomeg Berry=3. +use PP Up=3 asks you to select
an active move. Only eligible useful field effects consume a copy.
Use +party 3 to inspect your Pokemon and its full ID. Equip held items with
+hold 3=Leftovers; +hold 3= returns an uneaten copy. Bag copies do not activate
held effects. Use +evolve <full-id> Fire Stone for a matching bag evolution.
Milcery's Sweet and trade-held equivalents must be equipped before +evolve.

Smoke Ball uses +hold before battle and +flee in eligible wild battles.
Manual +item supports the recovery foods above (except Sacred Ash), Oran,
Sitrus, Berry Juice, Cheri/Chesto/Pecha/Rawst/Aspear/Lum/Leppa, and legacy
Berry/Gold/Burnt/Ice/Mint/Miracle/PRZ Cure/PSN Cure/Mystery berries.
Use +item A1 Leppa Berry=3/Water Gun for selected-move PP. Flavor/EV berries
stay field/held-only. Bag effects do not invoke held eating callbacks.
Mega/Z activation and berry growing are deferred.
Leader's Crest qualifies authored opponent victories, not a bag-item shortcut.
The Itemfinder mysterious-item message currently grants no inventory item.

Stock and deployed commands can differ from the item catalog. The October 22
audit found no enabled shops or Candy dispenser on the inspected older server
build. This is a dated observation; consult current world availability.

See the repository's docs/item-availability.md for examples and audit limits.
		""",
	},
	{
		"key": "evennia",
		"aliases": ["ev"],
		"category": "General",
		"locks": "read:perm(Developer)",
		"text": """
Evennia is a MU-game server and framework written in Python. You can read more
on https://www.evennia.com.

# Subtopics

## Installation

You'll find installation instructions on https://www.evennia.com.

## Community

There are many ways to get help and communicate with other devs.

### Discussions

The Discussions forum is found at https://github.com/evennia/evennia/discussions.

### Discord

There is also a discord channel for chatting:
https://discord.gg/AJJpcRUhtF
		""",
	},
]
