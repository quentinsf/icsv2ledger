iCSV2Ledger
===========

This is a command-line utility to convert CSV files of transactions, such as you might download from an online banking service, into the format used by John Wiegley's excellent [Ledger](http://ledger-cli.org) system.

The 'i' stands for Interactive. Here's what it's designed to do:

* As it runs through the entries in the CSV file, it tries to guess which Ledger account they should be posted against based on your historical decisions.

* It shows you which account it's going to use, giving you the opportunity to change it (or to specify one if it failed to find a match).  If it gets it right, just hit return.

* When you are entering an account name, you get auto-completion if you press the Tab key.  You don't have to match the _start_ of the account name, so on my system, typing 'foo[tab]' inserts 'Expenses:Food'.

* It stores the history in a mapping file, for converting transaction descriptions onto account names, which you can also edit by hand. It can load this in future as the basis of its guesses.  It uses simple string-matching by default, but if you put a '/' at the start and end of the string it will instead be interpreted as a regular expression.

* The account names used in the autocompletion are read both from the mapping file and, optionally, from a Ledger file or files. (It runs 'ledger --format %(account) reg" to get the names')

Lots of room for improvement here, but it's a starting point.  To make it work you probably just need to tweak the __init__ method of the Entry object to match the fields in your CSV file.
Run it with the '-h' or '--help' argument for the option syntax.

Feedback most welcome.
Quentin Stafford-Fraser
http://qandr.org/quentin






