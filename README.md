icsv2ledger
===========

This is a command-line utility to convert CSV files of transactions, such as you might download from an online banking service, into the format used by John Wiegley's excellent [Ledger](http://ledger-cli.org) system.

The 'i' stands for _interactive_. Here's what it's designed to do:

* For each CSV input you give it, it creates a Ledger output.

* As it runs through the entries in the CSV file, it tries to guess which Ledger account and Ledger payee they should be posted against, based on your historical decisions.

* It _shows you_ which account or payee it's going to use, giving you the opportunity to change it.  If it got it right, just hit return.

* When you are entering an account/payee name, you get _auto-completion_ if you press the Tab key.  You don't have to match the _start_ of the name, so on my system, typing 'foo[tab]' inserts 'Expenses:Food'.

* It stores the history in a mapping file, for converting transaction descriptions onto payee/account names. You can also edit this by hand. It can load this in future as the basis of its guesses.  It uses simple string-matching by default, but if you put a '/' at the start and end of a string it will instead be interpreted as a regular expression.

* The payee/account names used in the autocompletion are read both from the mapping file and, optionally, from a Ledger file or files. (It runs `ledger payees` and `ledger accounts` to get the names).


Command line options
--------------------

Usage:

    icsv2ledger.py [options] [input.csv [output.ledger]]

Arguments:

    input.csv             Filename or stdin. CSV format.
    output.ledger         Filename or stdout. Ledger format.

Options:

    -h, --help            show this help message and exit
    -c CONFIG_FILENAME, --config=CONFIG_FILENAME
                          Configuration file for icsv2ledger
    -l LEDGER_FILE, --ledger-file=LEDGER_FILE
                          Read payees/accounts from ledger file
    -q, --quiet           Don't prompt if account can be deduced, just use it
    -a ACCOUNT, --account=ACCOUNT
                          The Ledger account of this statement
                          (Assets:Bank:Current)

Example:

    ./icsv2ledger -a SAV file.csv

The above command will use the [SAV] section of the config file to process the CSV file.


Configuration file
------------------

To use icsv2ledger you need to create a configuration file.
Configuration file will be searched first in current directory, then in
home directory. Default configuration filename is '.icsv2ledger'.

The following is an example configuration file.

    [SAV]
    account=Assets:Bank:Savings Account
    currency=AUD
    date=1
    csv_date_format=%d-%b-%y
    ledger_date_format=%Y/%m/%d
    desc=6
    credit=2
    debit=-1
    mapping_file=mappings.SAV
     
    [CHQ]
    account=Assets:Bank:Cheque Account
    currency=AUD
    date=1
    csv_date_format=%d/%m/%Y
    ledger_date_format=%Y/%m/%d
    desc=2
    credit=3
    debit=4
    mapping_file=mappings.CHQ
    skip_lines=0

The configuration file contains one section per bank account you wish to import.
In the above example there are two bank accounts: SAV and CHQ.

Now for each account you need to specify the following:

* `account` is the ledger account to post the entries in. _Mandatory_
* `default_expense` is the default ledger account for expense. Default
  is 'Expenses:Unknown'. _Optional_
* `currency` is the the currency of amounts. Default is none. _Optional_
* `date` is the column in the CSV file which records the transaction date.
  The first column in the CSV file is numbered 1. _Mandatory_
* `csv_date_format` describes the format of the date in the CSV file.
  See the [python documentation](http://docs.python.org/library/datetime.html#strftime-strptime-behavior) for the various format codes supported in this expression. _Optional_
* `ledger_date_format` describes the format to be used when creating ledger
  entries.  By default the same date format from the CSV file is used.
  See the [python documentation](http://docs.python.org/library/datetime.html#strftime-strptime-behavior) for the various format codes supported in this expression. _Optional_
* `desc` is the column containing the transaction description as supplied by the bank.
  This is the column that will be used as the input for determing which payee and account to use by the auto-completion. _Mandatory_
* `credit` is the column which contains credits to the account. _Mandatory_
* `debit` is the column which contains debits to the account.
  If your bank represents debits as negative numbers in the credit
  column, than just set `debit` to be "-1" and icsv2ledger will do the right thing. _Mandatory_
* `mapping_file` is the file which holds the mapping between the
  description and the payee/account names to use. _Mandatory_
* `skip_lines` is the number of lines to skip from the beginning of the CSV
  file. The default is `1` to skip the CSV header line. _Optional_
* `cleared_character` is character to mark a transaction as cleared.
  Ledger possible value are `*` or `!` or ` `. Default is `*`. _Optional_
* `ledger_file` is ledger file where to get the list of already defined
  accounts and payees. _Optional_
* `transaction_template` path to a file containing the template to use when
  generating ledger transactions. _Optional_<br>
  Details on how to format the template are found in the [Format Specification Mini-Language](http://docs.python.org/library/string.html#formatspec).
  The built-in default template is as follows:

    {date} {cleared_character} {payee}
        ; MD5Sum: {md5sum}
        ; CSV: {csv}
        {debit_account:<60}    {debit_currency} {debit}
        {credit_account:<60}    {credit_currency} {credit}


Mapping file
------------

A typical mapping file might look like:

    /SAFEWAY/,Safeway,Expenses:Food
    /ITUNES.*/,iTunes,Expenses:Entertainment
    THE WRESTLERS INN,"The ""Wrestlers"" Inn",Expenses:Food
    /MACY'S/,"Macy's, Inc.",Expenses:Food
    MY COMPANY 1234,My Company,Income:Salary

Later matching entries overwrite earlier ones.


Feedback/contributions most welcome.

Quentin Stafford-Fraser
http://qandr.org/quentin
