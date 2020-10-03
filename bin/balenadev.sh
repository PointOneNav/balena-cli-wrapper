#!/usr/bin/env bash

# Find the directory of this file, following symlinks.
#
# Reference:
# - https://stackoverflow.com/questions/59895/how-to-get-the-source-directory-of-a-bash-script-from-within-the-script-itself
get_parent_dir() {
    local SOURCE="${BASH_SOURCE[0]}"
    while [ -h "$SOURCE" ]; do
        local DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
        SOURCE="$(readlink "$SOURCE")"
        [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
    done

    local PARENT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
    echo "${PARENT_DIR}"
}

SCRIPT_DIR=$(get_parent_dir)
REPO_DIR="${SCRIPT_DIR}/.."

show_usage() {
    cat <<EOF
Usage: $0 [OPTIONS...] COMMAND NAME_OR_ID CLI_ARGUMENTS...

Run a Balena CLI command for a device, querying the device by name or
partial/complete UUID.

This wrapper script is intended as a work-around since the Balena CLI does not
accept queries by device name. UUIDs are much harder to remember, and much
easier to mistakenly use the wrong one.


OPTIONS:

     --name        Interpret the specified value exclusively as a device name.
     --uuid        Interpret the specified value exclusively as a device UUID.
EOF
}

CLI_COMMAND=
CLI_ARGS=
NAME_OR_UUID=
QUERY_ARGS=

parse_args() {
    # Process command line arguments.
    while [ "$1" != "" ]; do
    case $1 in
        --name)
            QUERY_ARGS="${QUERY_ARGS} --name"
            ;;
        --uuid)
            QUERY_ARGS="${QUERY_ARGS} --uuid"
            ;;
        -*)
            CLI_ARGS="${CLI_ARGS} $1"
            ;;
        --*)
            CLI_ARGS="${CLI_ARGS} $1"
            ;;
        *)
            if [ -z "${CLI_COMMAND}" ]; then
                CLI_COMMAND=$1
            elif [ -z "${NAME_OR_UUID}" ]; then
                NAME_OR_UUID=$1
            else
                CLI_ARGS="${CLI_ARGS} $1"
            fi
            ;;
    esac
    shift
    done
}

parse_args "$@"

if [ -z "${CLI_COMMAND}" ]; then
    echo "Error: Balena CLI command not specified."
    echo ""
    echo ""
    show_usage
    exit 1
elif [ -z "${NAME_OR_UUID}" ]; then
    echo "Error: device name/UUID not specified."
    echo ""
    echo ""
    show_usage
    exit 1
fi

UUID=$(python3 "${REPO_DIR}/point_one/balena/device.py" ${QUERY_ARGS} "${NAME_OR_UUID}")
if [ "$?" -ne 0 ]; then
    exit 2
fi

echo "Found device: ${UUID}"
balena ${CLI_COMMAND} ${UUID} ${CLI_ARGS}
exit $?
