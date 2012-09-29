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
import types
import readline
import rlcompleter
import ConfigParser
from datetime import datetime


class Entry:
    """
    This represents one entry in the CSV file.
    You will probably need to tweak the __init__ method depending on how your bank represents things.
    """

    def __init__(self, row, config, csv_account):
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
        self.date = datetime.strptime(self.date, config.get(csv_account, 'date_format')).strftime("%Y/%m/%d")

        self.desc = row[config.getint(csv_account, 'desc') - 1]
        self.desc.strip()

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
        self.append_currency = config.getboolean(csv_account, 'append_currency')
        self.cleared_character = config.get(csv_account, 'cleared_character')

        # Append the currency to the credits and debits.
        if self.credit != "":
            if self.append_currency:
                self.credit = self.credit + " " + self.currency
            else:
                self.credit = self.currency + " " + self.credit

        if self.debit != "":
            if self.append_currency:
                self.debit = self.debit + " " + self.currency
            else:
                self.debit = self.currency + " " + self.debit

        # Ironically, we have to recreate the CSV line to keep it for reference
        # I don't think the otherwise excellent CSV library has a way to get the original line.
        self.csv = ",".join(row)

        # We also record this - in future we may use it to avoid duplication
        self.md5sum = hashlib.md5(self.csv).hexdigest()

        self.printed_header = False

    def prompt(self):
        """
        We print a summary of the record on the screen, and allow you to choose the destination account.
        What should go in that summary?
        """
        return "%s %-40s %s" % (self.date, self.desc, self.credit if self.credit else "-" + self.debit)

    def journal_entry(self, account, payee, output_tags):
        """
        Return a formatted journal entry recording this Entry against the specified Ledger account/
        """
        out  = "%s %s %s\n" % (self.date, self.cleared_character, payee)

        if output_tags:
            out += "    ; MD5Sum: %s\n" % self.md5sum
            out += "    ; CSV: \"%s\"\n" % self.csv

        out += "    %-60s%s\n" % (account, ("   " + self.debit) if self.debit else "")
        out += "    %-60s%s\n" % (self.csv_account,  ("   " + self.credit) if self.credit else "")
        return out


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


def read_mappings(map_file):
    """
    Mappings are simply a CSV file with two columns.
    The first is a string to be matched against an entry description.
    The second is the account against which such entries should be posted.
    If the match string begins and ends with '/' it is taken to be a regular expression.
    """
    mappings  = []
    with open(map_file, "r") as mf:
        map_reader = csv.reader(mf)
        for row in map_reader:
            if len(row) > 1:
                pattern, account = row[0].strip(), row[1].strip()
                if pattern.startswith('/') and pattern.endswith('/'):
                    try:
                        pattern = re.compile(pattern[1:-1])
                    except re.error as e:
                        sys.stderr.write("Invalid regex '%s' in '%s': %s\n" %
                                         (pattern, map_file, e))
                        sys.exit(1)
                mappings.append((pattern, account))
    return mappings


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
    usage = "%prog [options] file1.csv [file2.csv...]"
    parser = OptionParser(usage=usage)
    parser.add_option("-c", "--config", dest="config",
                      help="Configuation file for icsv2ledger",
                      default=".icsv2ledger")
    parser.add_option("-o", "--output-file", dest="output_file",
                      help="Ledger file for output (default file1.ledger etc)",
                      default=None)
    parser.add_option("-r", "--read-file", dest="ledger_file",
                      help="Read accounts from ledger file")
    parser.add_option("-q", "--quiet", dest="quiet",
                      help="Don't prompt if account can be deduced, just use it",
                      default=False, action="store_true")
    parser.add_option("-a", "--account", dest="account",
                      help="The Ledger account of this statement (Assets:Bank:Current)",
                      default="Assets:Bank:Current")
    parser.add_option("--no-output-tags", dest="output_tags",
                      help="Don't output the MD5SUM and CSV tags in the ledger transaction",
                      default=True, action="store_false")
    (options, args) = parser.parse_args()

    config = ConfigParser.ConfigParser(
        defaults={
            'expense': '',
            'default_expense': 'Expenses:Unknown',
            'append_currency': False,
            'no_header': False,
            'cleared_character': '*'})

    if os.path.exists(options.config):
        config.read(options.config)
    else:
        print "Can not find config file: " + options.config
        return

    if not config.has_section(options.account):
        print "Config file " + options.config + " does not contain section " + options.account
        return

    for o in ['account', 'date', 'date_format', 'desc', 'credit', 'debit', 'accounts_map', 'payees_map']:
        if not config.has_option(options.account, o):
            print "Config file " + options.config + " section " + options.account + " does not contain option " + o
            return

    options.accounts_map_file = config.get(options.account, 'accounts_map')
    options.payees_map_file = config.get(options.account, 'payees_map')
    options.no_header = config.getboolean(options.account, 'no_header')

    # We prime the list of accounts and payees by running Ledger on the specified file
    if options.ledger_file:
        accounts = accounts_from_ledger(options.ledger_file)
        payees = payees_from_ledger(options.ledger_file)

    # We read from and include accounts from any given mapping file
    mappings = []
    if options.accounts_map_file:
        mappings = read_mappings(options.accounts_map_file)
        for m in mappings:
            accounts.add(m[1])

    payee_mappings = []
    if options.payees_map_file:
        payee_mappings = read_mappings(options.payees_map_file)
        for m in payee_mappings:
            payees.add(m[1])

    def get_account(entry):
        return get_account_or_payee(
            entry, "Account", accounts,
            mappings, options.accounts_map_file,
            config.get(options.account, 'default_expense'))

    def get_payee(entry):
        return get_account_or_payee(entry, "Payee", payees, payee_mappings, options.payees_map_file, entry.desc)

    def get_account_or_payee(entry, prompt, possible_values, mappings, map_file, default_suggestion):
        sugg = default_suggestion
        found = False
        for m in mappings:
            pattern = m[0]
            if type(pattern) is types.StringType:
                pattern = pattern.strip()
                if entry.desc == pattern:
                    sugg = m[1]
                    found = True
            else:
                # If the pattern isn't a string it's a regex
                if m[0].match(entry.desc):
                    sugg = m[1]
                    found = True

        if options.quiet and found:
            value = sugg
        else:
            if not entry.printed_header:
                entry.printed_header = True
                print "\n" + entry.prompt()

            value  = prompt_for_value(prompt, possible_values, sugg)
            if not value:
                value = sugg

        if not found or (value != sugg):
            # Add new or changed mapping to mappings and append to file
            mappings.append((entry.desc, value))

            if map_file:
                with open(map_file, "a") as values_map_file:
                    values_map_file.write("\"%s\",\"%s\"\n" % (entry.desc, value) )

            # Add new possible_values to possible_values list
            possible_values.add(value)

        return value

    def process_csv_file(csv_filename, output_file):

        with open(csv_filename, 'r') as bank_file:

            bank_reader = csv.reader(bank_file)
            # We hardcode the fields, so want to ignore the first line if it's just field names
            if not options.no_header: bank_reader.next()

            # If output file not specified, use input filename with '.ledger' extension
            if not output_file:
                output = open(os.path.splitext(csv_filename)[0] + ".ledger", "w")
            else:
                output = output_file

            for row in bank_reader:
                entry = Entry(row, config, options.account)
                account = get_account(entry)
                payee = get_payee(entry)

                print >>output, entry.journal_entry(account, payee, options.output_tags)

            if not output_file:
                output.close()

    if options.output_file:
        output_file = open(options.output_file, "w")
    else:
        output_file = None

    for csv_file in args:
        process_csv_file(csv_file, output_file)

    if output_file:
        output_file.close()

if __name__ == "__main__":
    main()

# vim: ts=4 sw=4 et
