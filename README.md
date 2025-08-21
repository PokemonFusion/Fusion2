# Pokemon Fusion 2 Test Server

This project is an experimental MUD built with [Evennia](https://www.evennia.com/). It aims to reimagine the world of Pokémon in a text-based multiplayer setting. The repository hosts the game code as well as data files for Pokémon, regions and mechanics.

Please note that the server is under heavy development. You can follow progress on the [GitHub repository](https://github.com/PokemonFusion/Fusion2) and report issues on the [issue tracker](https://github.com/PokemonFusion/Fusion2/issues).

For setup instructions and other notes migrated from the original Evennia README, see [README.instructions.md](README.instructions.md).

## Documentation

Project documentation lives in the [docs](docs/) folder:

- [Quickstart and Overview](docs/index.md)
- [Code Map](docs/code-map.md)
- [Reference Materials](docs/reference)

To run the server you must install the Python requirements, including `psycopg2` for PostgreSQL support:

```bash
pip install -r requirements.txt
```

## Contributing and Testing

Development requirements, including the Evennia framework, are installed from `requirements.txt`.  Test-specific packages are kept in `requirements-dev.txt`.

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # optional
```

You can then run the test suite with `pytest`.  See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## License

This project is distributed under the terms of the [MIT License](LICENSE).

