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
GAME_SLOGAN = "Catch, train, become the best!"

MULTISESSION_MODE = 3
CMD_IGNORE_PREFIXES = "&/"
MAX_NR_CHARACTERS = 10
MAX_NR_SIMULTANEOUS_PUPPETS = 4
AUTO_PUPPET_ON_LOGIN = False

# Flag indicating if the server is running in development mode.
# When enabled, additional debug commands are exposed to all players and
# certain administrative features become available. Set to ``False`` in
# production environments.
DEV_MODE = False

# Run world initialization hooks at server start/stop
SERVER_STARTSTOP_MODULE = "world.system_init"

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
    "pokemon",
    "roomeditor",
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
# defined in ``pokemon.user``
BASE_CHARACTER_TYPECLASS = "pokemon.user.User"

# This location may need to change depending on what starting location is
# default to limbo, normally #2 but sometimes different. Best to put this in secret_settings
# START_LOCATION = "#2"
# DEFAULT_HOME  = "#2"

# Add this to the secret_settings.py if needed
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# USE_X_FORWARDED_HOST = True
# WEBSOCKET_CLIENT_URL = "/ws"  # relative path works behind HTTPS proxy

# ---------------------------------------------------------------------------
# Lockstring defaults
# ---------------------------------------------------------------------------

# Base lock expressions used when composing default room/exit locks.
ROOM_LOCK_BASE = "get:false();puppet:false();teleport:false();teleport_here:true()"
EXIT_LOCK_BASE = "puppet:false();traverse:all();get:false();teleport:false();teleport_here:false()"

# Include the creating object's id() in the owner triple when composing locks.
INCLUDE_CREATOR_IN_OWNER = True
