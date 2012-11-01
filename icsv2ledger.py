#! /usr/bin/env python
#
# Read CSV files and produce Ledger files out,
# prompting for and learning accounts on the way.
#
# Requires Python >= 2.6 and Ledger >= 3.0

from __future__ import print_function

import csv
import sys
import os
import hashlib
import re
import subprocess
import readline
import rlcompleter
import ConfigParser
from datetime import datetime
from operator import attrgetter

try:
    # argparse is in standard library as of Python >= 2.7 and >= 3.2
    import argparse
    from argparse import HelpFormatter
except ImportError:
    # for previous version, argparse package is to be installed
    print('argparse module missing: '
          'Please run `sudo easy_install argparse`',
          file=sys.stderr)
    sys.exit(1)


class dotdict(dict):
    """Enables dict.item syntax (instead of dict['item'])
    See http://stackoverflow.com/questions/224026
    """
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def get_locale_currency_symbol():
    """Get currency symbol from locale
    """
    import locale
    locale.setlocale(locale.LC_ALL, '')
    conv = locale.localeconv()
    return conv['currency_symbol']


DEFAULTS = dotdict({
    # For ConfigParser, int must be converted to str
    # For ConfigParser, boolean must be set to False
    'account': 'Assets:Bank:Current',
    'clear_screen': False,
    'cleared_character': '*',
    'credit': str(4),
    'csv_date_format': '',
    'currency': get_locale_currency_symbol(),
    'date': str(1),
    'debit': str(3),
    'default_expense': 'Expenses:Unknown',
    'desc': str(2),
    'ledger_date_format': '',
    'quiet': False,
    'skip_lines': str(1),
    'tags': False})

FILE_DEFAULTS = dotdict({
    'config_file': [
        os.path.join('.', '.icsv2ledgerrc'),
        os.path.join(os.path.expanduser('~'), '.icsv2ledgerrc')],
    'ledger_file': [
        os.path.join('.', '.ledger'),
        os.path.join(os.path.expanduser('~'), '.ledger')],
    'mapping_file': [
        os.path.join('.', '.icsv2ledgerrc-mapping'),
        os.path.join(os.path.expanduser('~'), '.icsv2ledgerrc-mapping')],
    'template_file': [
        os.path.join('.', '.icsv2ledgerrc-template'),
        os.path.join(os.path.expanduser('~'), '.icsv2ledgerrc-template')]})

DEFAULT_TEMPLATE = """\
{date} {cleared_character} {payee}
    ; MD5Sum: {md5sum}
    ; CSV: {csv}
    {debit_account:<60}    {debit_currency} {debit}
    {credit_account:<60}    {credit_currency} {credit}
"""


def find_first_file(arg_file, alternatives):
    """Because of http://stackoverflow.com/questions/12397681,
    parser.add_argument(type= or action=) on a file can not be used
    """
    found = None
    file_locs = [arg_file] + alternatives
    for loc in file_locs:
        if loc is not None and os.access(loc, os.F_OK | os.R_OK):
            found = loc  # existing and readable
            break
    return found


class SortingHelpFormatter(HelpFormatter):
    """Sort options alphabetically when -h prints usage
    See http://stackoverflow.com/questions/12268602
    """
    def add_arguments(self, actions):
        actions = sorted(actions, key=attrgetter('option_strings'))
        super(SortingHelpFormatter, self).add_arguments(actions)


def parse_args_and_config_file():
    """ Read options from config file and CLI args
    1. Reads hard coded DEFAULTS
    2. Supersedes by values in config file
    3. Supersedes by values from CLI args
    """

    # Build preparser with only config-file and account
    preparser = argparse.ArgumentParser(
        # Turn off help in first parser because all options are not present
        add_help=False)
    preparser.add_argument(
        '--account', '-a',
        metavar='STR',
        help=('ledger account used as source'
              ' (default: {0})'.format(DEFAULTS.account)))
    preparser.add_argument(
        '--config-file', '-c',
        metavar='FILE',
        help=('configuration file'
              ' (default search order: {0})'
              .format(', '.join(FILE_DEFAULTS.config_file))))

    # Parse args with preparser, and find config file
    args, remaining_argv = preparser.parse_known_args()
    args.config_file = find_first_file(args.config_file,
                                       FILE_DEFAULTS.config_file)

    # Initialize ConfigParser with DEFAULTS, and then read config file
    if args.config_file and ('-h' not in remaining_argv and
                             '--help' not in remaining_argv):
        config = ConfigParser.RawConfigParser(DEFAULTS)
        config.read(args.config_file)
        if not config.has_section(args.account):
            print('Config file {0} does not contain section {1}'
                  .format(args.config_file, args.account),
                  file=sys.stderr)
            sys.exit(1)
        defaults = dict(config.items(args.account))
        defaults['addons'] = {}
        if config.has_section(args.account + '_addons'):
            for item in config.items(args.account + '_addons'):
                if item not in config.defaults().items():
                    defaults['addons']['addon_' + item[0]] = int(item[1])
    else:
        # no config file found
        defaults = DEFAULTS

    # Build parser for remaining args on command line
    parser = argparse.ArgumentParser(
        # Don't surpress add_help here so it will handle -h
        # Inherit options from config_parser
        parents=[preparser],
        # print script description with -h/--help
        description=__doc__,
        # sort options alphabetically
        formatter_class=SortingHelpFormatter)
    parser.set_defaults(**defaults)

    parser.add_argument(
        'infile',
        nargs='?',
        type=argparse.FileType('r'),
        default=sys.stdin,
        help=('input filename or stdin in CSV syntax'
              ' (default: {0})'.format('stdin')))
    parser.add_argument(
        'outfile',
        nargs='?',
        type=argparse.FileType('w'),
        default=sys.stdout,
        help=('output filename or stdout in Ledger syntax'
              ' (default: {0})'.format('stdout')))

    parser.add_argument(
        '--ledger-file', '-l',
        metavar='FILE',
        help=('ledger file where to read payees/accounts'
              ' (default search order: {0})'
              .format(', '.join(FILE_DEFAULTS.ledger_file))))
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help=('do not prompt if account can be deduced'
              ' (default: {0})'.format(DEFAULTS.quiet)))
    parser.add_argument(
        '--default-expense',
        metavar='STR',
        help=('ledger account used as destination'
              ' (default: {0})'.format(DEFAULTS.default_expense)))
    parser.add_argument(
        '--skip-lines',
        metavar='INT',
        type=int,
        help=('number of lines to skip from CSV file'
              ' (default: {0})'.format(DEFAULTS.skip_lines)))
    parser.add_argument(
        '--cleared-character',
        choices='*! ',
        help=('character to clear a transaction'
              ' (default: {0})'.format(DEFAULTS.cleared_character)))
    parser.add_argument(
        '--date',
        metavar='INT',
        type=int,
        help=('CSV column number matching date'
              ' (default: {0})'.format(DEFAULTS.date)))
    parser.add_argument(
        '--desc',
        metavar='STR',
        help=('CSV column number matching description'
              ' (default: {0})'.format(DEFAULTS.desc)))
    parser.add_argument(
        '--debit',
        metavar='INT',
        type=int,
        help=('CSV column number matching debit amount'
              ' (default: {0})'.format(DEFAULTS.debit)))
    parser.add_argument(
        '--credit',
        metavar='INT',
        type=int,
        help=('CSV column number matching credit amount'
              ' (default: {0})'.format(DEFAULTS.credit)))
    parser.add_argument(
        '--csv-date-format',
        metavar='STR',
        help=('date format in CSV input file'
              ' (default: {0})'.format(DEFAULTS.csv_date_format)))
    parser.add_argument(
        '--ledger-date-format',
        metavar='STR',
        help=('date format for ledger output file'
              ' (default: {0})'.format(DEFAULTS.ledger_date_format)))
    parser.add_argument(
        '--currency',
        metavar='STR',
        help=('the currency of amounts'
              ' (default: {0})'.format(DEFAULTS.currency)))
    parser.add_argument(
        '--mapping-file',
        metavar='FILE',
        help=('file which holds the mappings'
              ' (default search order: {0})'
              .format(', '.join(FILE_DEFAULTS.mapping_file))))
    parser.add_argument(
        '--template-file',
        metavar='FILE',
        help=('file which holds the template'
              ' (default search order: {0})'
              .format(', '.join(FILE_DEFAULTS.template_file))))
    parser.add_argument(
        '--tags', '-t',
        action='store_true',
        help=('prompt for transaction tags'
              ' (default: {0})'.format(DEFAULTS.tags)))
    parser.add_argument(
        '--clear-screen', '-C',
        action='store_true',
        help=('clear screen for every transaction'
              ' (default: {0})'.format(DEFAULTS.clear_screen)))

    args = parser.parse_args(remaining_argv)

    args.ledger_file = find_first_file(
        args.ledger_file, FILE_DEFAULTS.ledger_file)
    args.mapping_file = find_first_file(
        args.mapping_file, FILE_DEFAULTS.mapping_file)
    args.template_file = find_first_file(
        args.template_file, FILE_DEFAULTS.template_file)

    if args.ledger_date_format and not args.csv_date_format:
        print('csv_date_format must be set'
              ' if ledger_date_format is defined.',
              file=sys.stderr)
        sys.exit(1)

    return args


class Entry:
    """
    This represents one entry in the CSV file.
    """

    def __init__(self, fields, raw_csv, options):
        """Parameters:
        fields: list of fields read from one line of the CSV file
        raw_csv: unprocessed line from CSV file
        options: from CLI args and config file
        """

        if 'addons' in options:
            self.addons = dict((k, fields[v - 1])
                               for k, v in options.addons.items())
        else:
            self.addons = dict()

        # Get the date and convert it into a ledger formatted date.
        self.date = fields[options.date - 1]
        if options.ledger_date_format:
            if options.ledger_date_format != options.csv_date_format:
                self.date = (datetime
                             .strptime(self.date, options.csv_date_format)
                             .strftime(options.ledger_date_format))

        desc = []
        for index in re.compile(',\s*').split(options.desc):
            desc.append(fields[int(index) - 1].strip())
        self.desc = ' '.join(desc).strip()

        if options.credit < 0:
            self.credit = ""
        else:
            self.credit = fields[options.credit - 1]

        if options.debit < 0:
            self.debit = ""
        else:
            self.debit = fields[options.debit - 1]

        self.csv_account = options.account
        self.currency = options.currency
        self.cleared_character = options.cleared_character

        if options.template_file:
            with open(options.template_file, 'r') as f:
                self.transaction_template = f.read()
        else:
            self.transaction_template = ""

        self.raw_csv = raw_csv.strip()

        # We also record this - in future we may use it to avoid duplication
        self.md5sum = hashlib.md5(self.raw_csv).hexdigest()

    def prompt(self):
        """
        We print a summary of the record on the screen, and allow you to
        choose the destination account.
        """
        return '{0} {1:<40} {2}'.format(
            self.date,
            self.desc,
            self.credit if self.credit else "-" + self.debit)

    def journal_entry(self, transaction_index, payee, account, tags):
        """
        Return a formatted journal entry recording this Entry against
        the specified Ledger account
        """
        template = (self.transaction_template
                    if self.transaction_template else DEFAULT_TEMPLATE)
        format_data = {
            'date': self.date,
            'cleared_character': self.cleared_character,
            'payee': payee,
            'transaction_index': transaction_index,

            'debit_account': account,
            'debit_currency': self.currency if self.debit else "",
            'debit': self.debit,

            'credit_account': self.csv_account,
            'credit_currency': self.currency if self.credit else "",
            'credit': self.credit,

            'tags': '\n    ; '.join(tags),
            'md5sum': self.md5sum,
            'csv': self.raw_csv}
        return template.format(
            **dict(format_data.items() + self.addons.items()))


def payees_from_ledger(ledger_file):
    return from_ledger(ledger_file, 'payees')


def accounts_from_ledger(ledger_file):
    return from_ledger(ledger_file, 'accounts')


def from_ledger(ledger_file, command):
    ledger = 'ledger'
    for f in ['/usr/bin/ledger', '/usr/local/bin/ledger']:
        if os.path.exists(f):
            ledger = f
            break

    cmd = [ledger, "-f", ledger_file, command]
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout_data, stderr_data) = p.communicate()
    items = set()
    for item in stdout_data.splitlines():
        items.add(item)
    return items


def read_mapping_file(map_file):
    """
    Mappings are simply a CSV file with three columns.
    The first is a string to be matched against an entry description.
    The second is the payee against which such entries should be posted.
    The third is the account against which such entries should be posted.

    If the match string begins and ends with '/' it is taken to be a
    regular expression.
    """
    mappings = []
    with open(map_file, "r") as f:
        map_reader = csv.reader(f)
        for row in map_reader:
            if len(row) > 1:
                pattern = row[0].strip()
                payee = row[1].strip()
                account = row[2].strip()
                tags = row[3:]
                if pattern.startswith('/') and pattern.endswith('/'):
                    try:
                        pattern = re.compile(pattern[1:-1])
                    except re.error as e:
                        print("Invalid regex '{0}' in '{1}': {2}"
                              .format(pattern, map_file, e),
                              file=sys.stderr)
                        sys.exit(1)
                mappings.append((pattern, payee, account, tags))
    return mappings


def append_mapping_file(map_file, desc, payee, account, tags):
    if map_file:
        with open(map_file, 'ab') as f:
            writer = csv.writer(f)
            writer.writerow([desc, payee, account] + tags)


def tagify(value):
    if value.find(':') < 0 and value[0] != '[' and value[-1] != ']':
        value = ":{0}:".format(value)
    return value


def prompt_for_tags(prompt, values, default):
    tags = list(default)
    value = prompt_for_value(prompt, values, ", ".join(tags))
    while value:
        if value[0] == '-':
            value = tagify(value[1:])
            if value in tags:
                tags.remove(value)
        else:
            value = tagify(value)
            if not value in tags:
                tags.append(value)
        value = prompt_for_value(prompt, values, ", ".join(tags))
    return tags


def prompt_for_value(prompt, values, default):

    def completer(text, state):
        for val in values:
            if text.upper() in val.upper():
                if not state:
                    return val
                else:
                    state -= 1
        return None

    # There are no word deliminators as each account name
    # is one word.  eg ':' and ' ' are valid parts of account
    # name and don't indicate a new word
    readline.set_completer_delims("")
    readline.set_completer(completer)
    if 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    return raw_input('{0} [{1}] > '.format(prompt, default))


def reset_stdin():
    """ If file input is stdin, then stdin must be reset to be able
    to use readline. How to reset stdin in explained in below URLs.
    http://stackoverflow.com/questions/8034595/
    http://stackoverflow.com/questions/6833526/
    """
    if os.name == 'posix':
        sys.stdin = open('/dev/tty')
    elif os.name == 'nt':
        sys.stdin = open('CON', 'r')
    else:
        print('Unrecognized operating system.',
              file=sys.stderr)
        sys.exit(1)


def main():

    options = parse_args_and_config_file()

    # Get list of accounts and payees from Ledger specified file
    possible_accounts = set([])
    possible_payees = set([])
    possible_tags = set([])
    if options.ledger_file:
        possible_accounts = accounts_from_ledger(options.ledger_file)
        possible_payees = payees_from_ledger(options.ledger_file)

    # Read mappings
    mappings = []
    if options.mapping_file:
        mappings = read_mapping_file(options.mapping_file)

    # Add to possible values the ones from mappings
    for m in mappings:
        possible_payees.add(m[1])
        possible_accounts.add(m[2])
        possible_tags.update(set(m[3]))

    def get_payee_and_account(entry):
        payee = entry.desc
        account = options.default_expense
        tags = []
        found = False
        # Try to match entry desc with mappings patterns
        for m in mappings:
            pattern = m[0]
            if isinstance(pattern, str):
                if entry.desc == pattern:
                    payee, account, tags = m[1], m[2], m[3]
                    found = True  # do not break here, later mapping must win
            else:
                # If the pattern isn't a string it's a regex
                if m[0].match(entry.desc):
                    payee, account, tags = m[1], m[2], m[3]
                    found = True

        modified = False
        if options.quiet and found:
            pass
        else:
            if options.clear_screen:
                print('\033[2J\033[;H')
            print('\n' + entry.prompt())
            value = prompt_for_value('Payee', possible_payees, payee)
            if value:
                modified = modified if modified else value != payee
                payee = value
            value = prompt_for_value('Account', possible_accounts, account)
            if value:
                modified = modified if modified else value != account
                account = value
            if options.tags:
                value = prompt_for_tags('Tag', possible_tags, tags)
                if value:
                    modified = modified if modified else value != tags
                    tags = value

        if not found or (found and modified):
            # Add new or changed mapping to mappings and append to file
            mappings.append((entry.desc, payee, account, tags))
            append_mapping_file(options.mapping_file,
                                entry.desc, payee, account, tags)

            # Add new possible_values to possible values lists
            possible_payees.add(payee)
            possible_accounts.add(account)

        return (payee, account, tags)

    def process_input_output(in_file, out_file):
        """ Read CSV lines either from filename or stdin.
        Process them.
        Write Ledger lines either to filename or stdout.
        """
        csv_lines = in_file.readlines()
        if in_file.name == '<stdin>':
            reset_stdin()
        ledger_lines = process_csv_lines(csv_lines)
        print(*ledger_lines, sep='\n', file=out_file)

    def process_csv_lines(csv_lines):
        dialect = csv.Sniffer().sniff(
            "\n".join(csv_lines[options.skip_lines:options.skip_lines + 3]))
        bank_reader = csv.reader(csv_lines[options.skip_lines:], dialect)

        ledger_lines = []
        for i, row in enumerate(bank_reader):
            entry = Entry(row, csv_lines[options.skip_lines + i],
                          options)
            payee, account, tags = get_payee_and_account(entry)
            ledger_lines.append(
                entry.journal_entry(i + 1, payee, account, tags))

        return ledger_lines

    process_input_output(options.infile, options.outfile)

if __name__ == "__main__":
    main()

# vim: ts=4 sw=4 et
