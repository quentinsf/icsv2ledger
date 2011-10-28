icsv2ledger
===========

This is a command-line utility to convert CSV files of transactions, such as you might download from an online banking service, into the format used by John Wiegley's excellent [Ledger](http://ledger-cli.org) system.

The 'i' stands for _interactive_. Here's what it's designed to do:

* For each .csv file you give it, it creates a .ledger file output (unless you specify an output file, in which case all output goes into the one file).

* As it runs through the entries in the CSV file, it tries to guess which Ledger account they should be posted against, based on your historical decisions.

* It _shows you_ which account it's going to use, giving you the opportunity to change it.  If it got it right, just hit return.

* When you are entering an account name, you get _auto-completion_ if you press the Tab key.  You don't have to match the _start_ of the account name, so on my system, typing 'foo[tab]' inserts 'Expenses:Food'.

* It stores the history in a mapping file, for converting transaction descriptions onto account names. You can also edit this by hand. It can load this in future as the basis of its guesses.  It uses simple string-matching by default, but if you put a '/' at the start and end of a string it will instead be interpreted as a regular expression.

* The account names used in the autocompletion are read both from the mapping file and, optionally, from a Ledger file or files. (It runs 'ledger --format %(account) reg" to get the names')

To use icsv2ledger you need to create a config file, by default .icsv2ledger in the current directory, such as the one below

<pre>
[SAV]
account=Assets:Bank:Savings Account
currency=AUD
date=1
date_format=%d-%b-%y
desc=6
credit=2
debit=-1
accounts_map=mappings.SAV
no_header=True

[CHQ]
account=Assets:Bank:Cheque Account
currency=AUD
date=1
date_format=%d/%m/%Y
desc=2
credit=3
debit=4
accounts_map=mappings.CHQ
no_header=False
</pre>

In the configuration file you need to specify the account name to use, the currency of the account, the column containing the date,
the format of the dates in that column, the column contain the description, the columns contain credits and debits, the file
which contains the mappings of payees to account names and whether or not the CSV file has no header line.

Note if your bank uses negative numbers for debits, just set the debit column to -1 and icsv2ledger will ignore the debits.

To run 

<pre>
./icsv2ledger -a SAV file.csv
</pre>

which will use the [SAV] section of the config file to process the csv file.

A typical mapping file might look like:

<pre>
  "/SAFEWAY.*/","Expenses:Food"
  "/ITUNES.*/","Expenses:Entertainment"
  "THE WRESTLERS INN","Expenses:Food"
  "MY COMPANY 1234", "Income:Salary"
</pre>

Later matching entries overwrite earlier ones.

Feedback/contributions most welcome.

Quentin Stafford-Fraser
http://qandr.org/quentin
