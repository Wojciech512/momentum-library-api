#!/bin/sh
set -e

ruff format --check .
ruff check .
alembic upgrade head
python -m pytest
