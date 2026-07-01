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

This is a text RPG, so most actions are typed as short commands. The browser
client is the recommended way to play: register, create a character, enter the
game, then follow the setup prompts.

# First Steps

1. Create an account or log in from the website.
2. Create a character with:
   charcreate <name>
3. Enter the game with:
   goic <name>
   goic <number>
4. Start character setup with:
   chargen
5. See starter options with:
   +starters
6. Pick your starter inside chargen. If you leave the menu during starter
   selection, resume it with:
   +starter

# After Setup

Use look to read the room, +sheet to check your trainer, and +hunt in route
rooms that allow wild encounters. If a battle starts, wait for the battle UI to
ask for your command before choosing a move, switch, item, or flee action.

# Useful Website Links

Home shows the current play status. Player Hub shows a read-only overview of
your characters, party, boxed Pokemon, inventory, and badges once you have a
character.
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
+trade <pokemon_id>=<character>               Trade a Pokemon to another character.

# Held Items

+hold <slot>=<item>    Give a party Pokemon a held item from your carried
                       objects.

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
+adventure/leave  Leave your active adventure.

If a wild Pokemon appears, the game moves you into battle. From there, use
battle commands such as +attack, +switch, +item, or +flee.

# Shops And Centers

+heal             Heal your party at a Pokemon Center.
+storage          Open Pokemon storage at a Pokemon Center.
+movesets         Manage saved movesets at a Pokemon Center.
+store            Open an item shop when one is present.
+vend [amount]    Use a nearby vending machine.
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
+moves/use <slot>=<set> Switch a Pokemon to a saved moveset.
+movesets              Manage saved movesets at a Pokemon Center.

# Items

+inventory             Show your inventory.
+use <item>            Use an item outside battle.
+use <item>=<target>   Use an item on a target when supported.

# Evolution

+evolve <pokemon_id> [item]    Attempt to evolve a Pokemon. Some evolutions may
                               need an item or other condition.
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
