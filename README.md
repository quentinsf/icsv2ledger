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

Lots of room for improvement here, but it's a starting point.  To make it work you probably just need to tweak the ____init____ method of the Entry object to match the fields in your CSV file.

Run it with the '-h' or '--help' argument for the option syntax.

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






