#! /usr/bin/env python
#
# Read CSV files and produce Ledger files out,
# prompting for and learning accounts on the way.
#
# Requires Python >= 2.5 and Ledger >= 3.0

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


class Entry:
    """
    This represents one entry in the CSV file.
    You will probably need to tweak the __init__ method depending on how your bank represents things.
    """

    def __init__(self, row, csv, config, csv_account):
        """
        Parameters:

         row is the list of fields read from a line of the CSV file
            This method should put them into the appropriate fields of the object.

         config is the ConfigParser instance

         csv_account is the name of the Ledger account for which this is a statement
             e.g. "Assets:Bank:Checking"

        """

        # Get the date and convert it into a ledger formatted date.
        self.date = row[config.getint(csv_account, 'date') - 1]
        if config.has_option(csv_account, 'csv_date_format'):
            csv_date_format = config.get(csv_account, 'csv_date_format')
        else:
            csv_date_format = ""
        if config.has_option(csv_account, 'ledger_date_format'):
            ledger_date_format = config.get(csv_account, 'ledger_date_format')
        else:
            ledger_date_format = ""
        if ledger_date_format != csv_date_format:
            self.date = datetime.strptime(self.date, csv_date_format).strftime(ledger_date_format)

        self.desc = row[config.getint(csv_account, 'desc') - 1].strip()

        if config.getint(csv_account, 'credit') < 0:
            self.credit = ""
        else:
            self.credit = row[config.getint(csv_account, 'credit') - 1]

        if config.getint(csv_account, 'debit') < 0:
            self.debit = ""
        else:
            self.debit = row[config.getint(csv_account, 'debit') - 1]

        self.csv_account = config.get(csv_account, 'account')
        self.currency = config.get(csv_account, 'currency')
        self.cleared_character = config.get(csv_account, 'cleared_character')

        if config.has_option(csv_account, 'transaction_template'):
            with open (config.get(csv_account, 'transaction_template'), 'r') as template_file:
                self.transaction_template = template_file.read().rstrip()
        else:
            self.transaction_template = ""

        # Ironically, we have to recreate the CSV line to keep it for reference
        # I don't think the otherwise excellent CSV library has a way to get the original line.
        self.csv = csv

        # We also record this - in future we may use it to avoid duplication
        self.md5sum = hashlib.md5(self.csv).hexdigest()

        self.printed_header = False

    def prompt(self):
        """
        We print a summary of the record on the screen, and allow you to choose the destination account.
        What should go in that summary?
        """
        return "%s %-40s %s" % (self.date, self.desc, self.credit if self.credit else "-" + self.debit)

    def journal_entry(self, payee, account):
        """
        Return a formatted journal entry recording this Entry against the specified Ledger account/
        """
        default_template = """\
{date} {cleared_character} {payee}
    ; MD5Sum: {md5sum}
    ; CSV: {csv}
    {debit_account:<60}    {debit_currency} {debit}
    {credit_account:<60}    {credit_currency} {credit}
        """
        template = self.transaction_template if self.transaction_template else default_template
        format_data = {
            'date': self.date,
            'cleared_character': self.cleared_character,
            'payee': payee,

            'debit_account': account,
            'debit_currency': self.currency if self.debit else "",
            'debit': self.debit,

            'credit_account': self.csv_account,
            'credit_currency': self.currency if self.credit else "",
            'credit': self.credit,

            'md5sum': self.md5sum,
            'csv': self.csv }
        return template.format(**format_data)


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
    mappings  = []
    with open(map_file, "r") as f:
        map_reader = csv.reader(f)
        for row in map_reader:
            if len(row) > 1:
                pattern = row[0].strip()
                payee = row[1].strip()
                account = row[2].strip()
                if pattern.startswith('/') and pattern.endswith('/'):
                    try:
                        pattern = re.compile(pattern[1:-1])
                    except re.error as e:
                        sys.stderr.write("Invalid regex '%s' in '%s': %s\n" %
                                         (pattern, map_file, e))
                        sys.exit(1)
                mappings.append((pattern, payee, account))
    return mappings


def append_mapping_file(map_file, desc, payee, account):
    if map_file:
        with open(map_file, 'ab') as f:
            writer = csv.writer(f)
            writer.writerow([desc, payee, account])


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

    return raw_input(prompt + ' [%s] > ' % default)


def main():

    from optparse import OptionParser
    usage = "%prog [options] [input.csv [output.ledger]]"
    parser = OptionParser(usage=usage)
    parser.add_option("-c", "--config", dest="config_filename",
                      help="Configuration file for icsv2ledger",
                      default=".icsv2ledger")
    parser.add_option("-l", "--ledger-file", dest="ledger_file",
                      help="Read payees/accounts from ledger file")
    parser.add_option("-q", "--quiet", dest="quiet",
                      help="Don't prompt if account can be deduced, just use it",
                      default=False, action="store_true")
    parser.add_option("-a", "--account", dest="account",
                      help="The Ledger account of this statement (Assets:Bank:Current)",
                      default="Assets:Bank:Current")
    (options, args) = parser.parse_args()

    # Because of python bug http://bugs.python.org/issue974019,
    # ConfigParser boolean default value must be a string
    config = ConfigParser.ConfigParser(
        defaults={
            'default_expense': 'Expenses:Unknown',
            'skip_lines': '1',
            'cleared_character': '*'})

    config_file_locs = (
        os.path.join('.', options.config_filename),
        os.path.join(os.path.expanduser("~"), options.config_filename))
    for loc in config_file_locs:
        if os.path.exists(loc):
            config_file = loc
            break
    else:
        print "Can't find config file. Put it in one of these locations:"
        for loc in config_file_locs:
            print loc
        sys.exit(1)

    config.read(config_file)

    if not config.has_section(options.account):
        print "Config file " + options.config_filename + " does not contain section " + options.account
        return

    for o in ['account', 'date', 'desc', 'credit', 'debit', 'mapping_file']:
        if not config.has_option(options.account, o):
            print "Config file " + options.config_filename + " section " + options.account + " does not contain option " + o
            return

    options.mapping_file = config.get(options.account, 'mapping_file')
    options.skip_lines = config.getint(options.account, 'skip_lines')
    if not options.ledger_file and config.has_option(options.account, 'ledger_file'):
        options.ledger_file = config.get(options.account, 'ledger_file')

    # Get list of accounts and payees from Ledger specified file
    possible_accounts = set([])
    possible_payees = set([])
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

    def get_payee_and_account(entry):
        payee = entry.desc
        account = config.get(options.account, 'default_expense')
        found = False
        # Try to match entry desc with mappings patterns
        for m in mappings:
            pattern = m[0]
            if isinstance(pattern, str):
                if entry.desc == pattern:
                    payee, account = m[1], m[2]
                    found = True  # do not break here, later mapping must win
            else:
                # If the pattern isn't a string it's a regex
                if m[0].match(entry.desc):
                    payee, account = m[1], m[2]
                    found = True

        modified = False
        if options.quiet and found:
            pass
        else:
            print '\n' + entry.prompt()
            value = prompt_for_value('Payee', possible_payees, payee)
            if value:
                modified = value != payee
                payee = value
            value = prompt_for_value('Account', possible_accounts, account)
            if value:
                modified = value != account
                account = value

        if not found or (found and modified):
            # Add new or changed mapping to mappings and append to file
            mappings.append((entry.desc, payee, account))
            append_mapping_file(options.mapping_file,
                                entry.desc, payee, account)

            # Add new possible_values to possible values lists
            possible_payees.add(payee)
            possible_accounts.add(account)

        return (payee, account)

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
            sys.stderr.write('Unrecognized operating system.\n')
            sys.exit(1)

    def process_input_output(input_filename, output_filename):
        """ Read CSV lines either from filename or stdin.
        Process them.
        Write Ledger lines either to filename or stdout.
        """
        if input_filename:
            in_file = open(input_filename, 'r')
            csv_lines = in_file.readlines()
            in_file.close()
        else:  # stdin
            csv_lines = sys.stdin.readlines()
            reset_stdin()

        ledger_lines = process_csv_lines(csv_lines)

        if output_filename:
            out_file = open(output_filename, 'w')
            out_file.write("\n".join(ledger_lines))
            out_file.close()
        else:  # stdout
            sys.stdout.write("\n".join(ledger_lines))

    def process_csv_lines(csv_lines):
        dialect = csv.Sniffer().sniff("\n".join(csv_lines[options.skip_lines:options.skip_lines+3]))
        bank_reader = csv.reader(csv_lines[options.skip_lines:], dialect)

        ledger_lines = []
        for i,row in enumerate(bank_reader):
            entry = Entry(row, csv_lines[options.skip_lines+i], config, options.account)
            payee, account = get_payee_and_account(entry)
            ledger_lines.append(entry.journal_entry(payee, account))

        return ledger_lines

    # Parse positional arguments
    if len(args) > 2:
        parser.error("Incorrect number of arguments")
    elif len(args) == 2:
        input_filename = args[0] if not args[0] == '-' else None
        output_filename = args[1] if not args[1] == '-' else None
    elif len(args) == 1:
        input_filename = args[0] if not args[0] == '-' else None
        output_filename = None
    elif len(args) == 0:
        input_filename = None
        output_filename = None

    process_input_output(input_filename, output_filename)

if __name__ == "__main__":
    main()

# vim: ts=4 sw=4 et
