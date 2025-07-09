# Setup Instructions

This file contains setup instructions and other information removed from the main README.

# Welcome to Evennia!

This is your game directory, set up to let you start with
your new game right away. An overview of this directory is found here:
https://github.com/evennia/evennia/wiki/Directory-Overview#the-game-directory

You can delete this readme file when you've read it and you can
re-arrange things in this game-directory to suit your own sense of
organisation (the only exception is the directory structure of the
`server/` directory, which Evennia expects). If you change the structure
you must however also edit/add to your settings file to tell Evennia
where to look for things.

Your game's main configuration file is found in
`server/conf/settings.py` (but you don't need to change it to get
started). If you just created this directory (which means you'll already
have a `virtualenv` running if you followed the default instructions),
`cd` to this directory. Install the Python dependencies with

```bash
pip install -r requirements.txt
```

Then initialize a new database using

    evennia migrate

To start the server, stand in this directory and run

    evennia start

This will start the server, logging output to the console. Make
sure to create a superuser when asked. By default you can now connect
to your new game using a MUD client on `localhost`, port `4000`.  You can
also log into the web client by pointing a browser to
`http://localhost:4001`.

## Database migrations

If you pull changes that add new models (such as the Trainer model) or
modify existing ones (for example adding new Pokémon fields), run

```bash
evennia makemigrations pokemon
evennia migrate
```

to update your database schema before starting the server.

## Database backend

The game is configured to use **PostgreSQL**. The connection settings are kept
in `server/conf/secret_settings.py`, which is not committed to the repository.
Make sure PostgreSQL is available before running migration or start commands.

The `psycopg2` package is required so that Django can talk to PostgreSQL. It is
installed automatically when using the `requirements.txt` file mentioned above.

# Getting started

From here on you might want to look at one of the beginner tutorials:
http://github.com/evennia/evennia/wiki/Tutorials.

Evennia's documentation is here:
https://github.com/evennia/evennia/wiki.

Enjoy!

## Regional Pokédex Data

The `pokemon/data/regiondex.py` module stores regional Pokédex entries for
each main-series region (Kanto through Galar).  Each entry is a pair of the
regional number and the species name.  The data was generated from the
[PokeAPI](https://github.com/PokeAPI/pokeapi/) CSV dumps
(`pokedexes.csv`, `pokemon_dex_numbers.csv` and `pokemon_species.csv`).  Use the
helpers in `pokemon/dex/functions/pokedex_funcs.py` such as
`get_region_entries()` or `get_region_species()` to access the data.

## Git Pull Command

Admins can update the server's code from within the game by using the
`@gitpull` command. The command runs `git pull` and returns any output to
the caller.
