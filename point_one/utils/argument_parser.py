########################################################################################################################
# @brief Argument parsing helper classes.
#
# @author Adam Shapiro <adam@pointonenav.com>
#
# @date Created 9/4/2018
########################################################################################################################

import argparse


class CapitalisedHelpFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = 'Usage: '
        return super(CapitalisedHelpFormatter, self).add_usage(usage, actions, groups, prefix)


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        if 'formatter_class' not in kwargs:
            kwargs['formatter_class'] = CapitalisedHelpFormatter
        if 'add_help' not in kwargs:
            overwrite_help = True
            kwargs['add_help'] = False
        else:
            overwrite_help = False

        super(ArgumentParser, self).__init__(*args, **kwargs)

        self._positionals.title = 'Positional arguments'
        self._optionals.title = 'Optional arguments'

        if overwrite_help:
            self.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                              help = 'Show this help message and exit.')
