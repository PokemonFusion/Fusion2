# -*- coding: utf-8 -*-
"""
Connection screen

This is the text to show the user when they first connect to the game (before
they log in).

To change the login screen in this module, do one of the following:

- Define a function `connection_screen()`, taking no arguments. This will be
  called first and must return the full string to act as the connection screen.
  This can be used to produce more dynamic screens.
- Alternatively, define a string variable in the outermost scope of this module
  with the connection string that should be displayed. If more than one such
  variable is given, Evennia will pick one of them at random.

The commands available to the user when the connection screen is shown
are defined in evennia.default_cmds.UnloggedinCmdSet. The parsing and display
of the screen is done by the unlogged-in "look" command.

"""

from django.conf import settings

from evennia import utils

CONNECTION_SCREEN = r"""
|b==============================================================|n
|y    ____        __                            |n
|y   / __ \\____  / /_____  ____ ___  ____  ____ |n
|y  / /_/ / __ \\/ //_/ _ \\/ __ `__ \\/ __ \\/ __ \|n
|y / ____/ /_/ / ,< /  __/ / / / / / /_/ / / / /|n
|y/_/    \\____/_/|_|\\___/_/ /_/ /_/\\____/_/ /_/|n
|y                                              |n
|g    ______           _                ___|n
|g   / ____/_  _______(_)___  ____     |__ \\|n
|g  / /_  / / / / ___/ / __ \\/ __ \\    __/ /|n
|g / __/ / /_/ (__  ) / /_/ / / / /   / __/ |n
|g/_/    \\__,_/____/_/\\____/_/ /_/   /____/|n
|n
 Welcome to |g{}|n, version {}!

 If you have an existing account, connect to it by typing:
      |wconnect <username> <password>|n
 If you need to create an account, type (without the <>'s):
      |wcreate <username> <password>|n

 If you have spaces in your username, enclose it in quotes.
 Enter |whelp|n for more info. |wlook|n will re-show this screen.
|b==============================================================|n""".format(
    settings.SERVERNAME, utils.get_evennia_version("short")
)
