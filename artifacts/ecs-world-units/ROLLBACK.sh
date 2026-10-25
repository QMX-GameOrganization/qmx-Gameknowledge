#!/bin/sh
# This is a newly added article. Its pristine byte baseline is empty.
# Restore a supplied COPY; never call this on the published note.
set -eu
if [ "$#" -ne 1 ]; then
    echo 'usage: ROLLBACK.sh TARGET_COPY' >&2
    exit 2
fi
: > "$1"
