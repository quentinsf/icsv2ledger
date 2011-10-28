#! /usr/bin/env python
# 
# Read CSV files and produce Ledger files out,
# prompting for and learning accounts on the way.
#
# Requires Python >= 2.5 and Ledger >= 3.0

import csv, sys, os, json
import md5, re, subprocess, types
import readline,rlcompleter
import ConfigParser
from datetime import datetime

LEDGER = "/usr/local/bin/ledger"

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

        # Append the currency to the credits and debits.
        if self.credit != "":
            self.credit = self.currency + " " + self.credit

        if self.debit != "":
            self.debit = self.currency + " " + self.debit

        # Ironically, we have to recreate the CSV line to keep it for reference
        # I don't think the otherwise excellent CSV library has a way to get the original line.
        self.csv = ",".join(row)

        # We also record this - in future we may use it to avoid duplication
        self.md5sum = md5.new(self.csv).hexdigest()


    def prompt(self):
        """
        We print a summary of the record on the screen, and allow you to choose the destination account.
        What should go in that summary?
        """
        return "%s %-40s %s" % (self.date, self.desc, self.credit if self.credit else "-" + self.debit)


    def journal_entry(self, account):
        """
        Return a formatted journal entry recording this Entry against the specified Ledger account/
        """
        out  = "%s * %s\n" % (self.date, self.desc)
        out += "    ; MD5Sum: %s\n" % self.md5sum
        out += "    ; CSV: \"%s\"\n" % self.csv
        out += "    %-60s%s\n" % (account, ("   " + self.debit) if self.debit else "")
        out += "    %-60s%s\n" % (self.csv_account,  ("   " + self.credit) if self.credit else "")
        return out
        


def accounts_from_ledger(ledger_file):
    cmd = [LEDGER, "-f", ledger_file, "--format", "%(account)\n", "reg"]
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout_data, stderr_data) = p.communicate()
    accounts = set()
    for a in stdout_data.splitlines():
        accounts.add(a)
    return accounts

def read_mappings(map_file):
    """
    Mappings are simply a CSV file with two columns.
    The first is a string to be matched against an entry description.
    The second is the account against which such entries should be posted.
    If the match string begins and ends with '/' it is taken to be a regular expression.
    """
    mappings  = []
    with open(map_file,"r") as mf:
        map_reader = csv.reader(mf)
        for row in map_reader:
            if len(row) > 1:
                pattern, account = row[0].strip(), row[1].strip()
                if pattern.startswith('/') and pattern.endswith('/'):
                    pattern = re.compile(pattern[1:-1])
                mappings.append((pattern, account))
    return mappings

def prompt_for_account(accounts, default):
    # print accounts
    completions = {}

    def completer(text, state):
        for acc in accounts:
            if text.upper() in acc.upper():
                if not state:
                    return acc
                else:
                    state -= 1
        return None

    # There are no word deliminators as each account name
    # is one word.  eg ':' and ' ' are valid parts of account
    # name and don't indicate a new word
    readline.set_completer_delims("")
    readline.set_completer(completer)
    if(sys.platform == 'darwin'):
        readline.parse_and_bind ("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    return raw_input('Account [%s] > ' % default)


def main():

    from optparse import OptionParser
    usage = "%prog [options] file1.csv [file2.csv...]"
    parser = OptionParser(usage=usage)
    parser.add_option("-c", "--config", dest="config",
            help="Configuation file for icsv2ledger", default=".icsv2ledger")
    parser.add_option("-o","--output-file",dest="output_file",
            help="Ledger file for output (default file1.ledger etc)", default=None)
    parser.add_option("-r","--read-file",  dest="ledger_file",
            help="Read accounts from ledger file")
    parser.add_option("-q","--quiet",  dest="quiet",
            help="Don't prompt if account can be deduced, just use it",
            default=False, action="store_true")
    parser.add_option("-a","--account", dest="account",  
            help="The Ledger account of this statement (Assets:Bank:Current)",
            default="Assets:Bank:Current")
    (options, args) = parser.parse_args()

    config = ConfigParser.ConfigParser();

    if os.path.exists(options.config):
        config.read(options.config)
    else:
        print "Can not find config file: " + options.config
        return

    if not config.has_section(options.account):
        print "Config file " + options.config + " does not contain section " + options.account
        return

    for o in ['account', 'currency', 'date', 'date_format', 'desc', 'credit', 'debit', 'accounts_map', 'no_header']:
        if not config.has_option(options.account, o):
            print "Config file " + options.config + " section " + options.account + " does not contain option " + o
            return

    options.map_file = config.get(options.account, 'accounts_map')
    options.no_header = config.getboolean(options.account, 'no_header')
            
    # We prime the list of accounts by running Ledger on the specified file
    accounts = set([])
    if options.ledger_file:
        accounts = accounts_from_ledger(options.ledger_file)

    # We read from and include accounts from any given mapping file
    mappings = []
    if options.map_file:
        mappings = read_mappings(options.map_file)
        for m in mappings:
            accounts.add(m[1])

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

                # OK, which account should this go in?
                account_sugg = "Expenses:Unknown"
                account_found = False
                for m in mappings:
                    pattern = m[0]
                    if type(pattern) is types.StringType:
                        pattern = pattern.strip()
                        if entry.desc == pattern:
                            account_sugg = m[1]
                            account_found = True
                    else:
                        # If the pattern isn't a string it's a regex
                        if m[0].match(entry.desc):
                            account_sugg = m[1]
                            account_found = True

                if options.quiet and account_found:
                    account = account_sugg
                else:
                    print "\n" + entry.prompt()
                    account  = prompt_for_account(accounts, account_sugg)
                    if not account:
                        account = account_sugg

                if not account_found or (account != account_sugg):
                    # Add new or changed mapping to mappings and append to file
                    mappings.append((entry.desc, account))

                    if options.map_file:
                        with open(options.map_file,"a") as map_file:
                            map_file.write("\"%s\",\"%s\"\n" % (entry.desc, account) )


                    # Add new accounts to accounts list
                    accounts.add(account)

                print >>output, entry.journal_entry(account) + "\n"

            if not output_file:
                output.close()


    if options.output_file:
        output_file = open(options.output_file,"w")
    else:
        output_file = None

    for csv_file in args:
        process_csv_file(csv_file, output_file)

    if output_file:
        output_file.close()

if __name__ == "__main__":
    main()
    
# vim: ts=4 sw=4 et
