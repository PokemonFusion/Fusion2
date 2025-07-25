r"""
Evennia settings file.

The available options are found in the default settings file found
here:

https://www.evennia.com/docs/latest/Setup/Settings-Default.html

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "Pokemon Fusion 2"

MULTISESSION_MODE = 3
CMD_IGNORE_PREFIXES = "&/"
MAX_NR_CHARACTERS = 10
MAX_NR_SIMULTANEOUS_PUPPETS = 4
AUTO_PUPPET_ON_LOGIN = False

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")

# Optional third-party apps. None at this time.

# Local apps
INSTALLED_APPS += (
    'pokemon',
    'roomeditor',
)

# Allow use of unconventional field names used in legacy models
SILENCED_SYSTEM_CHECKS = ["fields.E001"]

# Custom permission hierarchy with Validator role
PERMISSION_HIERARCHY = [
    "Guest",
    "Player",
    "Helper",
    "Validator",
    "Builder",
    "Admin",
    "Developer",
]

# Use the custom character typeclass with Pokémon helpers
BASE_CHARACTER_TYPECLASS = "pokemon.pokemon.User"
