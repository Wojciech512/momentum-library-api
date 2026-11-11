#!/bin/sh
set -e

exec watchfiles --filter python "sh scripts/run-tests.sh" app tests migrations
