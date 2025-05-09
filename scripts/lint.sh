#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2025 Siemens AG
# SPDX-License-Identifier: MIT

EXIT_CODE=0

printc(){
    declare -A colors=(
        ["cyan"]='\033[0;36m'
        ["green"]='\033[0;32m'
        ["red"]='\033[0;31m'
    )
    NC='\033[0m' # No Color
    echo -e "${colors[$1]}$2${NC}"
}

run_linter() {
    local exit_code
    local tmpfile

    echo
    printc "cyan" "=== Running \`$*\`"

    tmpfile=$(mktemp -p /tmp lint-sh.XXXXXX)

    poetry run "$@" > "$tmpfile" 2>&1
    exit_code=$?
    if [ $exit_code -eq 0 ]; then
        printc "green" "Succeeded."
    else
        printc "red" "Failed!"
        cat "$tmpfile"
        EXIT_CODE=$((EXIT_CODE + exit_code))
    fi

    rm "$tmpfile"
}

run_linter poetry check --lock --strict
run_linter ruff check
run_linter ruff format --diff
run_linter ec
run_linter mypy vilocify tests
run_linter pytest

exit $EXIT_CODE
