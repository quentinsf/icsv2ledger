#! /usr/bin/env python3
#
# Read CSV files and produce Ledger files out,
# prompting for and learning accounts on the way.
#
# Requires Python >= 3.2 and Ledger >= 3.0

import argparse
import csv
import io
import glob
import mmap
import sys
import os
import hashlib
import re
import subprocess
import readline
import configparser
from argparse import HelpFormatter
from dataclasses import dataclass
from datetime import datetime
from operator import attrgetter
from locale   import atof
from typing import AnyStr, Pattern, Optional


class FileType(object):
    """Based on `argparse.FileType` from python3.4.2, but with additional
    support for the `newline` parameter to `open`.
    """
    def __init__(self, mode='r', bufsize=-1, encoding=None, errors=None, newline=None):
        self._mode = mode
        self._bufsize = bufsize
        self._encoding = encoding
        self._errors = errors
        self._newline = newline

    def __call__(self, string):
        # the special argument "-" means sys.std{in,out}
        if string == '-':
            if 'r' in self._mode:
                return sys.stdin
            elif 'w' in self._mode:
                return sys.stdout
            else:
                msg = 'argument "-" with mode %r' % self._mode
                raise ValueError(msg)

        # all other arguments are used as file names
        try:
            return open(string, self._mode, self._bufsize, self._encoding,
                        self._errors, newline=self._newline)
        except OSError as e:
            message = "can't open '%s': %s"
            raise argparse.ArgumentTypeError(message % (string, e))

    def __repr__(self):
        args = self._mode, self._bufsize
        kwargs = [('encoding', self._encoding), ('errors', self._errors),
                  ('newline', self._newline)]
        args_str = ', '.join([repr(arg) for arg in args if arg != -1] +
                             ['%s=%r' % (kw, arg) for kw, arg in kwargs
                              if arg is not None])
        return '%s(%s)' % (type(self).__name__, args_str)


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
    # For configparser, int must be converted to str
    # For configparser, boolean must be set to False
    'account': 'Assets:Bank:Current',
    'src_account': '',
    'clear_screen': False,
    'cleared_character': '*',
    'credit': str(4),
    'csv_date_format': '',
    'currency': get_locale_currency_symbol(),
    'date': str(1),
    'effective_date': str(0),
    'debit': str(3),
    'default_expense': 'Expenses:Unknown',
    'desc': str(2),
    'encoding': 'utf-8',
    'ledger_date_format': '',
    'quiet': False,
    'reverse': False,
    'skip_lines': str(1),
    'skip_dupes': False,
    'confirm_dupes': False,
    'incremental': False,
    'tags': False,
    'multiline_tags': False,
    'delimiter': ',',
    'csv_decimal_comma': False,
    'ledger_decimal_comma': False,
    'skip_older_than': str(-1),
    'prompt_add_mappings': False,
    'entry_review': False})

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
    'accounts_file': [
        os.path.join('.', '.icsv2ledgerrc-accounts'),
        os.path.join(os.path.expanduser('~'), '.icsv2ledgerrc-accounts')],
    'template_file': [
        os.path.join('.', '.icsv2ledgerrc-template'),
        os.path.join(os.path.expanduser('~'), '.icsv2ledgerrc-template')],
    'ledger_binary_file': [
        '/usr/bin/ledger',
        '/usr/local/bin/ledger'
    ]})

DEFAULT_TEMPLATE = """\
{date} {cleared_character} {payee}
    ; MD5Sum: {md5sum}
    ; CSV: {csv}
    {debit_account:<60}    {debit_currency} {debit}
    {credit_account:<60}    {credit_currency} {credit}
    {tags}
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


def decode_escape_sequences(string):
    # The `unicode_escape` decoder can only handle ASCII input, so it can't be
    # fed a complete string with arbitrary characters. Instead, it is used only
    # on the subsequences of the input string that have escape sequences and
    # are guaranteed to only contain ASCII characters.
    return re.sub(r'(?a)\\[\\\w{}]+',
                  lambda m: m.group().encode('ascii').decode('unicode_escape'),
                  string),


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

    # Initialize configparser with DEFAULTS, and then read config file
    if args.config_file and ('-h' not in remaining_argv and
                             '--help' not in remaining_argv):
        config = configparser.RawConfigParser(DEFAULTS)
        config.read(args.config_file)
        if not config.has_section(args.account):
            print('Config file {0} does not contain section {1}'
                  .format(args.config_file, args.account),
                  file=sys.stderr)
            sys.exit(1)
        defaults = dict(config.items(args.account))

        if defaults['src_account']:
            print('Section {0} in config file {1} contains command line only option src_account'
                  .format(args.account, args.config_file),
                  file=sys.stderr)
            sys.exit(1)

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
        # Don't suppress add_help here so it will handle -h
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
        type=FileType('r', newline=''),
        default=sys.stdin,
        help=('input filename or stdin in CSV syntax'
              ' (default: {0})'.format('stdin')))
    parser.add_argument(
        'outfile',
        nargs='?',
        type=FileType('a', encoding='utf-8'),
        default=sys.stdout,
        help=('output filename or stdout in Ledger syntax'
              ' (default: {0})'.format('stdout')))
    parser.add_argument(
        '--encoding',
        metavar='STR',
        help=('encoding of csv file'
              ' (default: {0})'.format(DEFAULTS.encoding)))
    parser.add_argument(
        '--ledger-binary',
        metavar='FILE',
        help=('path to ledger binary'
              ' (default search order: {0})'
              .format(', '.join(FILE_DEFAULTS.ledger_binary_file))))
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
        '--src-account',
        metavar='STR',
        help=('ledger source account to use, overrides --account option specified in config section'
              ' (default: {0})'.format(DEFAULTS.src_account)))
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
        '--skip-dupes',
        action='store_true',
        help=('detect and skip transactions that have already been imported'
              ' (default: {0})'.format(DEFAULTS.skip_dupes)))
    parser.add_argument(
        '--confirm-dupes',
        action='store_true',
        help=('detect and interactively skip transactions that have already been imported'
              ' (default: {0})'.format(DEFAULTS.confirm_dupes)))
    parser.add_argument(
        '--incremental',
        action='store_true',
        help=('append output as transactions are processed'
              ' (default: {0})'.format(DEFAULTS.incremental)))
    parser.add_argument(
        '--reverse',
        action='store_true',
        help=('reverse the order of entries in the CSV file'
              ' (default: {0})'.format(DEFAULTS.reverse)))
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
        '--effective-date',
        metavar='INT',
        type=int,
        help=('CSV column number matching effective date'
              ' (default: {0})'.format(DEFAULTS.effective_date)))
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
        '--csv-decimal-comma',
        action='store_true',
        help=('comma as decimal separator in the CSV'
              ' (default: {0})'.format(DEFAULTS.csv_decimal_comma)))
    parser.add_argument(
        '--ledger-decimal-comma',
        action='store_true',
        help=('comma as decimal separator in the ledger'
              ' (default: {0})'.format(DEFAULTS.ledger_decimal_comma)))
    parser.add_argument(
        '--accounts-file',
        metavar='FILE',
        help=('file which holds a list of account names'
              ' (default search order: {0})'
              .format(', '.join(FILE_DEFAULTS.accounts_file))))
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
        '--multiline-tags',
        action='store_true',
        help=('format tags on multiple lines'
              ' (default: {0})'.format(DEFAULTS.multiline_tags)))
    parser.add_argument(
        '--clear-screen', '-C',
        action='store_true',
        help=('clear screen for every transaction'
              ' (default: {0})'.format(DEFAULTS.clear_screen)))
    parser.add_argument(
        '--delimiter',
        metavar='STR',
        type=decode_escape_sequences,
        help=('delimiter between fields in the csv'
              ' (default: {0})'.format(DEFAULTS.delimiter)))

    parser.add_argument(
        '--skip-older-than',
        metavar='INT',
        type=int,
        help=('skip entries more than X days old (-1 indicates keep all)'
              ' (default: {0})'.format(DEFAULTS.skip_older_than)))

    parser.add_argument(
        '--prompt-add-mappings',
        action='store_true',
        help=('ask before adding entries to mapping file'
              ' (default: {0})'.format(DEFAULTS.prompt_add_mappings)))

    parser.add_argument(
        '--entry-review',
        action='store_true',
        help=('displays transaction summary and request confirmation before committing to ledger'
              ' (default: {0})'.format(DEFAULTS.entry_review)))

    args = parser.parse_args(remaining_argv)

    args.ledger_file = find_first_file(
        args.ledger_file, FILE_DEFAULTS.ledger_file)
    args.mapping_file = find_first_file(
        args.mapping_file, FILE_DEFAULTS.mapping_file)
    args.accounts_file = find_first_file(
        args.accounts_file, FILE_DEFAULTS.accounts_file)
    args.template_file = find_first_file(
        args.template_file, FILE_DEFAULTS.template_file)
    if args.ledger_binary is not None:
        # if ledger_binary was explicitly specified, check if it actually exists
        if find_first_file(args.ledger_binary, []) is None:
            # if not, throw an exception
            raise FileNotFoundError(
                'Can\'t find ledger binary at the specified location: {0}'.format(args.ledger_binary)
            )
    else:
        # otherwise try defaults
        args.ledger_binary = find_first_file(
            args.ledger_binary, FILE_DEFAULTS.ledger_binary_file)

    if args.ledger_date_format and not args.csv_date_format:
        print('csv_date_format must be set'
              ' if ledger_date_format is defined.',
              file=sys.stderr)
        sys.exit(1)

    if args.encoding.lower() != args.infile.encoding.lower():
        args.infile = io.TextIOWrapper(args.infile.detach(),
                                       encoding=args.encoding)

    return args


@dataclass(frozen=True)
class MappingInfo:
    """
    This represents one entry in the mapping file.
    """
    pattern: Pattern[AnyStr]
    payee: str
    account: str
    tags: [str]
    transfer_to: Optional[str]
    transfer_to_file: Optional[str]


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

        self.options = options

        if 'addons' in options:
            self.addons = dict((k, fields[v - 1])
                               for k, v in options.addons.items())
        else:
            self.addons = dict()

        # Get the date and convert it into a ledger formatted date.
        self.date = fields[options.date - 1].strip()
        entry_date = datetime.strptime(self.date, options.csv_date_format)
        if options.ledger_date_format:
            if options.ledger_date_format != options.csv_date_format:
                self.date = (datetime
                             .strptime(self.date, options.csv_date_format)
                             .strftime(options.ledger_date_format))

        # determine how many days old this entry is
        self.days_old = (datetime.now()-entry_date).days

        # convert effective dates
        if options.effective_date:
            self.effective_date = fields[options.effective_date - 1]
            if options.ledger_date_format:
                if options.ledger_date_format != options.csv_date_format:
                    self.effective_date = (datetime
                                 .strptime(self.effective_date, options.csv_date_format)
                                 .strftime(options.ledger_date_format))
        else:
            self.effective_date = ""


        desc = []
        for index in re.compile(',\s*').split(options.desc):
            desc.append(fields[int(index) - 1].strip())
        self.desc = ' '.join(desc).strip()

        self.credit = get_field_at_index(fields, options.credit, options.csv_decimal_comma, options.ledger_decimal_comma)
        self.debit = get_field_at_index(fields, options.debit, options.csv_decimal_comma, options.ledger_decimal_comma)
        if self.credit  and self.debit and atof(self.credit) == 0:
            self.credit = ''
        elif self.credit and self.debit and atof(self.debit) == 0:
            self.debit  = ''

        self.credit_account = options.account
        if options.src_account:
            self.credit_account = options.src_account

        self.currency = options.currency
        self.credit_currency = getattr(
            options, 'credit_currency', self.currency)
        self.cleared_character = options.cleared_character

        if options.template_file:
            with open(options.template_file, 'r', encoding='utf-8') as f:
                self.transaction_template = f.read()
        else:
            self.transaction_template = ""

        self.raw_csv = raw_csv.strip()

        # We also record this - in future we may use it to avoid duplication
        #self.md5sum = hashlib.md5(self.raw_csv.encode('utf-8')).hexdigest()
        self.md5sum = hashlib.md5(','.join(x.strip() for x in (self.date,self.desc,self.credit,self.debit,self.credit_account)).encode('utf-8')).hexdigest()

    def prompt(self):
        """
        We print a summary of the record on the screen, and allow you to
        choose the destination account.
        """
        return '{0} {1:<40} {2}'.format(
            self.date,
            self.desc,
            self.credit if self.credit else "-" + self.debit)

    def _build_entry_str(self, transaction_index, payee, credit_account, debit_account, tags) -> str:
        """
        Return a formatted journal entry recording this Entry against
        the specified Ledger account
        """
        template = (self.transaction_template
                    if self.transaction_template else DEFAULT_TEMPLATE)
        uuid_regex = re.compile(r"UUID:", re.IGNORECASE)
        uuid = [v for v in tags if uuid_regex.match(v)]
        if uuid:
            uuid = uuid[0]
            tags.remove(uuid)

        # format tags to proper ganged string for ledger
        if self.options.multiline_tags:
            tags_separator = '\n    ; '
        else:
            tags_separator = ''
        if tags:
            tags = '; ' + tags_separator.join(tags).replace('::', ':')
        else:
            tags = ''

        format_data = {
            'date': self.date,
            'effective_date': self.effective_date,
            'cleared_character': self.cleared_character,
            'payee': payee,
            'transaction_index': transaction_index,

            'uuid': uuid,

            'debit_account': debit_account,
            'debit_currency': self.currency if self.debit else "",
            'debit': self.debit,

            'credit_account': credit_account,
            'credit_currency': self.credit_currency if self.credit else "",
            'credit': self.credit,

            'tags': tags,
            'md5sum': self.md5sum,
            'csv': self.raw_csv}
        format_data.update(self.addons)

        # generate and clean output
        output_lines = template.format(**format_data).split('\n')
        output = '\n'.join([x.rstrip() for x in output_lines if x.strip()]) + '\n'

        return output

    def journal_entry(self, transaction_index, payee, debit_account, tags):
        return self._build_entry_str(transaction_index, payee, self.credit_account, debit_account, tags)

    def transfer_entry(self, transaction_index, payee, account, transfer_to, tags):
        return self._build_entry_str(transaction_index, payee, account, transfer_to, tags)


def get_field_at_index(fields, index, csv_decimal_comma, ledger_decimal_comma):
    """
    Get the field at the given index.
    If the index is less than 0, then we invert the sign of
    the field at the given index
    """
    if index == 0 or index > len(fields):
        return ""

    if csv_decimal_comma:
        decimal_separator = ','
    else:
        decimal_separator = '.'

    re_non_number = '[^-0-9' + decimal_separator + ']'

    raw_value = fields[abs(index) - 1]
    # Add negative symbol to raw_value if between parentheses
    # E.g.  ($13.37) becomes -$13.37
    if raw_value.startswith("(") and raw_value.endswith(")"):
        raw_value = "-" + raw_value[1:-1]

    value = re.sub(re_non_number, '', raw_value)
    # Invert sign of value if index is negative.
    if index < 0:
        if value.startswith("-"):
            value = value[1:]
        elif value == "":
            value = ""
        else:
            value = "-" + value

    if csv_decimal_comma and not ledger_decimal_comma:
        value = value.replace(',', '.')
    if not csv_decimal_comma and ledger_decimal_comma:
        value = value.replace('.', ',')

    return value


def csv_md5sum_from_ledger(ledger_file):
    with open(ledger_file, encoding="utf-8") as f:
        lines = f.read()
        include_files = re.findall(r"include\s+(.*?)\s+", lines)
    pathes = [ledger_file, ] + include_files
    csv_comments = set()
    md5sum_hashes = set()
    pattern = re.compile(r"^\s*[;#]\s*CSV:\s*(.*?)\s*$")
    pattern1 = re.compile(r"^\s*[;#]\s*MD5Sum:\s*(.*?)\s*$")
    for path in pathes:
        for fname in glob.glob(path):
            with open(fname, encoding="utf-8") as f:
                for line in f:
                    m = pattern.match(line)
                    if m:
                        csv_comments.add(m.group(1))
                    m = pattern1.match(line)
                    if m:
                        md5sum_hashes.add(m.group(1))
    return csv_comments, md5sum_hashes


def payees_from_ledger(ledger_file, ledger_binary_file):
    return from_ledger(ledger_file, ledger_binary_file, 'payees')


def accounts_from_ledger(ledger_file, ledger_binary_file):
    return from_ledger(ledger_file, ledger_binary_file, 'accounts')


def from_ledger(ledger_file, ledger_binary_file, command):
    if ledger_binary_file is not None:
        # if either the --ledger-binary parameter was specified or a default ledger path was valid, use that
        ledger = ledger_binary_file
    else:
        # otherwise let's hope it's in PATH
        ledger = 'ledger'
    cmd = [ledger, "-f", ledger_file, command]
    try:
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout_data, stderr_data) = p.communicate()
        items = set()
        for item in stdout_data.decode('utf-8').splitlines():
            items.add(item)
        return items
    except FileNotFoundError:
        raise FileNotFoundError('The system can\'t find the following ledger binary: {0}'.format(ledger))


def read_mapping_file(map_file) -> [MappingInfo]:
    """
    Mappings are simply a CSV file with three columns.
    The first is a string to be matched against an entry description.
    The second is the payee against which such entries should be posted.
    The third is the account against which such entries should be posted.

    If the match string begins and ends with '/' it is taken to be a
    regular expression.
    """
    mappings = []
    with open(map_file, "r", encoding='utf-8', newline='') as f:
        map_reader = csv.reader(f)
        for row in map_reader:
            if len(row) > 2:
                pattern = row[0].strip()
                payee = row[1].strip()
                account = row[2].strip()
                tags = [col for col in row[3:] if not col.startswith(("transfer_to", "file"))]
                transfer_to = row[3].split('=')[1].strip() if ''.join(row[3:]).startswith("transfer_to=") else None
                transfer_to_file = row[4].split('=')[1].strip() if ''.join(row[4:]).startswith("file=") else None

                if pattern.startswith('/') and pattern.endswith('/'):
                    try:
                        pattern = re.compile(pattern[1:-1])
                    except re.error as e:
                        print("Invalid regex '{0}' in '{1}': {2}"
                              .format(pattern, map_file, e),
                              file=sys.stderr)
                        sys.exit(1)
                mappings.append(MappingInfo(pattern, payee, account, tags, transfer_to, transfer_to_file))
    return mappings


def read_accounts_file(account_file):
    """ Process each line in the specified account file looking for account
        definitions. An account definition is a line containing the word
        'account' followed by a valid account name, e.g:

            account Expenses
            account Expenses:Utilities

        All other lines are ignored.
    """
    accounts = []
    pattern = re.compile(r"^\s*account\s+([-_:\w ]+)$")
    with open(account_file, "r", encoding='utf-8') as f:
        for line in f.readlines():
            mo = pattern.match(line)
            if mo:
                accounts.append(mo.group(1))

    return accounts


def append_mapping_file(map_file, desc, payee, account, tags):
    if map_file:
        with open(map_file, 'a', encoding='utf-8', newline='') as f:
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
    if readline.__doc__ and 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    return input('{0} [{1}] > '.format(prompt, default))


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


def main(options):

    # Define responses to yes/no prompts
    possible_yesno = {'Y', 'N'}

    # Get list of accounts and payees from Ledger specified file
    possible_accounts = set([])
    possible_payees = set([])
    possible_tags = set([])
    md5sum_hashes = set()
    csv_comments = set()
    if options.ledger_file:
        possible_accounts = accounts_from_ledger(options.ledger_file, options.ledger_binary)
        possible_payees = payees_from_ledger(options.ledger_file, options.ledger_binary)
        csv_comments, md5sum_hashes = csv_md5sum_from_ledger(options.ledger_file)

    # Read mappings
    mappings = []
    if options.mapping_file:
        mappings = read_mapping_file(options.mapping_file)

    if options.accounts_file:
        possible_accounts.update(read_accounts_file(options.accounts_file))

    # Add to possible values the ones from mappings
    for m in mappings:
        possible_payees.add(m.payee)
        possible_accounts.add(m.account)
        possible_tags.update(set(m.tags))

    def get_payee_and_account(entry):
        payee = entry.desc
        account = options.default_expense
        tags = []
        transfer_to = None
        transfer_to_file = None
        found = False
        # Try to match entry desc or entry addons with mappings patterns
        for m in mappings:
            pattern = m.pattern
            if isinstance(pattern, str):
                if entry.desc == pattern or pattern in list(entry.addons.values()):
                    payee, account, tags = m.payee, m.account, m.tags
                    transfer_to, transfer_to_file = m.transfer_to, m.transfer_to_file
                    found = True  # do not break here, later mapping must win
            else:
                # If the pattern isn't a string it's a regex
                match_desc = m.pattern.match(entry.desc)
                match_addons = m.pattern.match(" ".join(entry.addons.values()))
                match = match_desc if match_desc else match_addons
                if match:
                #if m[0].match(entry.desc):
                    payee = m.payee
                    # perform regexp substitution if captures were used
                    if match.groups():
                        payee = m.pattern.sub(m.payee, entry.desc)
                    account, tags = m.account, m.tags
                    transfer_to, transfer_to_file = m.transfer_to, m.transfer_to_file
                    found = True

        modified = False
        if options.quiet and found:
            pass
        else:
            #if options.clear_screen:
            #    print('\033[2J\033[;H')
            #print('\n' + entry.prompt())
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
            value = 'Y'
            # if prompt-add-mappings option passed then request confirmation before adding to mapping file
            if options.prompt_add_mappings:
                yn_response = prompt_for_value('Append to mapping file?', possible_yesno, 'Y')
                if yn_response:
                    value = yn_response
            if value.upper().strip() not in ('N', 'NO'):
                # Add new or changed mapping to mappings and append to file
                mappings.append(MappingInfo(entry.desc, payee, account, tags, None, None))
                append_mapping_file(options.mapping_file,
                                entry.desc, payee, account, tags)

            # Add new possible_values to possible values lists
            possible_payees.add(payee)
            possible_accounts.add(account)

        return (payee, account, tags, transfer_to, transfer_to_file)

    def process_input_output(in_file, out_file):
        """ Read CSV lines either from filename or stdin.
        Process them.
        Write Ledger lines either to filename or stdout.
        """
        if not options.incremental:
            out_file.truncate(0)

        csv_lines = get_csv_lines(in_file)
        if in_file.name == '<stdin>':
            reset_stdin()
        for line in  process_csv_lines(csv_lines):
            print(line, sep='\n', file=out_file)
            out_file.flush()

    def get_csv_lines(in_file):
        """
        Return csv lines from the in_file adjusted
        for the skip_lines and reverse options.
        """
        csv_lines = in_file.readlines()
        csv_lines = csv_lines[options.skip_lines:]
        if options.reverse:
            csv_lines = list(reversed(csv_lines))
        return csv_lines

    def process_csv_lines(csv_lines):
        dialect = None
        try:
            dialect = csv.Sniffer().sniff(
                    "".join(csv_lines[:3]), options.delimiter)
        except csv.Error:  # can't guess specific dialect, try without one
            pass

        bank_reader = csv.reader(csv_lines, dialect)
        transaction_index = 0
        for i, row in enumerate(bank_reader):
            # Skip any empty lines in the input
            if len(row) == 0:
                continue

            entry = Entry(row, csv_lines[i],
                          options)

            # detect duplicate entries in the ledger file and optionally skip or prompt user for action
            # if options.skip_dupes and csv_lines[i].strip() in csv_comments:
            if (options.skip_older_than < 0) or (entry.days_old <= options.skip_older_than):
                if options.clear_screen:
                    print('\033[2J\033[;H')
                print('\n' + entry.prompt())
                if (options.skip_dupes or options.confirm_dupes) and entry.md5sum in md5sum_hashes:
                    value = 'Y'
                    # if interactive flag was passed prompt user before skipping transaction
                    if options.confirm_dupes:
                        yn_response = prompt_for_value('Duplicate transaction detected, skip?', possible_yesno, 'Y')
                        if yn_response:
                            value = yn_response
                    if value.upper().strip() not in ('N', 'NO'):
                        continue
                while True:
                    payee, account, tags, transfer_to, transfer_to_file = get_payee_and_account(entry)
                    value = 'C'
                    if options.entry_review:
                        # need to display ledger formatted entry here
                        #
                        # request confirmation before committing transaction
                        print('\n' + 'Ledger Entry:')
                        print(entry.journal_entry(transaction_index + 1, payee, account, tags))
                        yn_response = prompt_for_value('Commit transaction (Commit, Modify, Skip)?', ('C', 'M', 'S'),
                                                       value)
                        if yn_response:
                            value = yn_response
                    if value.upper().strip() not in ('C', 'COMMIT'):
                        if value.upper().strip() in ('S', 'SKIP'):
                            break
                        else:
                            continue
                    else:
                        # add md5sum of new entry, this helps detect duplicate entries in same file
                        md5sum_hashes.add(entry.md5sum)
                        break
                if value.upper().strip() in ('S', 'SKIP'):
                    continue

                transaction_index += 1
                yield entry.journal_entry(transaction_index, payee, account, tags)

                if transfer_to is not None:
                    transaction_index += 1
                    transfer_entry = entry.transfer_entry(transaction_index, payee, account, transfer_to, tags)
                    if transfer_to_file is None:
                        yield transfer_entry
                    else:
                        with open(transfer_to_file, "rb") as f:
                            if f.read(1):
                                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as s:
                                    has_entry = s.find(bytes(entry.md5sum, 'utf-8')) != -1
                            else:
                                has_entry = False

                        if not has_entry or not options.skip_dupes:
                            with open(transfer_to_file, "a") as f:
                                f.write(transfer_entry)
                                f.write("\n")

    try:
        process_input_output(options.infile, options.outfile)
    except KeyboardInterrupt:
        print()
        sys.exit(0)


if __name__ == "__main__":
    options = parse_args_and_config_file()
    main(options)

# vim: ts=4 sw=4 et
