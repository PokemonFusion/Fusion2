import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-dex-tests",
        action="store_true",
        default=False,
        help="Run exhaustive move and ability tests",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "dex: mark test as part of the exhaustive dex suite")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-dex-tests"):
        return
    skip_dex = pytest.mark.skip(reason="need --run-dex-tests option to run")
    for item in items:
        if "dex" in item.keywords:
            item.add_marker(skip_dex)
