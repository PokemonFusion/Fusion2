#!/usr/bin/env bash
# Regenerate pinned requirement files using pip-compile.
# Pass additional arguments to control pip-compile, e.g. --upgrade.
set -euo pipefail
pip-compile requirements.in --output-file requirements.txt "$@"
pip-compile requirements-dev.in --output-file requirements-dev.txt "$@"
