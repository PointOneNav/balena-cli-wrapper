#!/usr/bin/env python

import argparse
import logging
import os
import subprocess
import sys

# Relative imports don't usually work when running a Python file as a script since the file is not considered to be part
# of a package. To get around this, we add the repo root directory to the import search path and set __package__ so the
# interpreter tries the relative imports based on `<__package__>.__main__` instead of just `__main__`.
if __name__ == "__main__" and (__package__ is None or __package__ == ''):
    repo_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sys.path.append(repo_dir)
    import point_one.balena
    __package__ = "point_one.balena"

from .device import get_device_uuid
from ..utils.argument_parser import ArgumentParser

__logger = logging.getLogger("point_one.balena.cli")


def find_balena_cli():
    # Get the root directory of this repo.
    repo_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

    # Find the default CLI path. If that path is not in this repo, assume it's the actual Balena CLI.
    try:
        cli_path = str(subprocess.check_output(["which", "balena"]).decode('utf-8').strip())
        if not cli_path.startswith(repo_dir):
            return cli_path
    except subprocess.CalledProcessError:
        raise RuntimeError('Unable to find Balena CLI on the system path.')

    # Otherwise, search through PATH to find the CLI.
    paths = os.environ["PATH"].split(":")
    for path in paths:
        cli_path = os.path.join(path, 'balena')
        if (os.path.exists(cli_path) and os.path.isfile(cli_path) and os.access(cli_path, os.X_OK) and
                not cli_path.startswith(repo_dir)):
            return cli_path

    raise RuntimeError('Unable to find Balena CLI on the system path.')


if __name__ == "__main__":
    parser = ArgumentParser(usage='%(prog)s [OPTIONS]... [BALENA CLI OPTIONS]...',
                            description="""\
Wrap Balena CLI commands and add support for device names in any device-targeted
commands (balena device, balena ssh, etc.), in addition to UUIDs. All non-device
commands will be passed through as is.

To pass arguments directly to the Balena CLI that overlap with arguments to this
program, you can use the -- separator:
    $ balena --help
    vs
    $ balena -- --help
""")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--name', action='store_true',
                       help="If specified, treat the string as a name and do not attempt a UUID lookup.")
    group.add_argument('--uuid', action='store_true',
                       help="If specified, treat the string as a UUID and do not attempt a name lookup.")

    group.add_argument('--quiet', action='store_true',
                       help="Do not print the UUID of the specified device on success.")

    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")

    parser.add_argument('args', nargs=argparse.REMAINDER)

    options = parser.parse_args()

    # Strip out the -- if present.
    options.args = [arg for arg in options.args if arg != '--']

    # Enable verbose logging if requested.
    if options.verbose == 1:
        logging.basicConfig()
        logging.getLogger("point_one.balena").setLevel(logging.DEBUG)
    elif options.verbose > 1:
        # Enable debug messages all libraries including the Balena SDK.
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(message)s')

    # If no arguments are specify display the _Python_ help. Use `balena help` or `balena -- --help` to get CLI help.
    if len(options.args) == 0:
        parser.print_help()
        sys.exit(0)

    # Get the name of the CLI command.
    command = options.args[0]

    # If this is a device-targeting command, try to find the name/UUID argument.
    id_index = None
    if command == 'device':
        __logger.debug("Locating name/UUID for '%s' command." % command)

        if len(options.args) >= 2:
            next_arg = options.args[1]
        else:
            raise ValueError('Device name/UUID not specified.')

        sub_commands = ['identify', 'move', 'reboot', 'rename', 'rm', 'restart', 'shutdown', 'os-update', 'public-url']
        if next_arg in sub_commands:
            if len(options.args) >= 3:
                id_index = 2
            else:
                raise ValueError('Device name/UUID not specified.')
        else:
            id_index = 1
    elif command in ('ssh', 'tunnel'):
        __logger.debug("Locating name/UUID for '%s' command." % command)
        if len(options.args) >= 2:
            id_index = 1
        else:
            raise ValueError('Device name/UUID not specified.')
    else:
        # Search for --device VALUE
        for i, arg in enumerate(options.args):
            if i == 0:
                continue
            elif arg == '--device':
                if i < len(options.args) - 1:
                    id_index = len(options.args) - 1
                    break

    # If an ID was found, try to convert it to UUID (if necessary).
    if id_index is not None:
        __logger.debug("Converting '%s' to device UUID." % options.args[id_index])
        if options.name:
            is_name = True
        elif options.uuid:
            is_name = False
        else:
            is_name = None

        try:
            uuid = get_device_uuid(options.args[id_index], is_name=is_name)
            if not options.quiet:
                # Note: Explicitly calling print(), not __logger.info(), so there's no logger format string stuff. That
                # way the console output is always consistent and easy to parse programmatically if needed.
                print('Found device: %s' % uuid)
            options.args[id_index] = uuid
        except Exception as e:
            __logger.error("Error: %s" % str(e))
            sys.exit(1)

    # Finally, find the path to the actual CLI and execute the command. Using find_balena_cli() allows us to install
    # this wrapper as either cli.py to be called directly on the PATH, a `balena` wrapper script before the actual CLI
    # on the PATH, or a Bash alias for `balena`.
    cli_path = find_balena_cli()
    options.args.insert(0, cli_path)
    __logger.debug("Executing command: %s" % ' '.join(options.args))
    cli = subprocess.Popen(options.args, stdin=sys.stdin.fileno(), stdout=sys.stdout.fileno(),
                           stderr=sys.stderr.fileno())
    sys.exit(cli.wait())