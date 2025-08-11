# commands/

This folder holds modules for implementing one's own commands and
command sets. All the modules' classes are essentially empty and just
imports the default implementations from Evennia; so adding anything
to them will start overloading the defaults. 

The commands in this project are organised into subpackages under this
folder:

* ``player`` – player-facing commands.
* ``admin`` – administrative and world-building commands.
* ``debug`` – development and testing helpers.

If you change the location of any default command set classes, update
``server/conf/settings.py`` so Evennia can locate them. Remember to
include an ``__init__.py`` in any new subdirectory so Python treats it
as a package.
