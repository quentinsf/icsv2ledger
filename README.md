icsv2ledger
===========

This is a command-line utility to convert CSV files of transactions,
such as you might download from an online banking service, into the
format used by John Wiegley's excellent [Ledger](http://ledger-cli.org)
system.

The 'i' stands for __interactive__. Here's what it's designed to do:

* For each CSV input you give it, it creates a Ledger output.

* As it runs through the entries in the CSV file, it tries to guess
  which Ledger account and Ledger payee they should be posted against,
  based on your historical decisions.

* It __shows you__ which account, payee, (optionally tags), it's going
  to use, giving you the opportunity to change it. If it got it right,
  just hit return.

* When you are entering an account/payee name, you get
  __auto-completion__ if you press the Tab key. You don't have to match
  the _start_ of the name, so typing 'foo[tab]' inserts 'Expenses:Food'.

* When you are entering a tag, you get __auto-completion__ if you press
  the Tab key. If you would like to remove a tag from the list of tags
  just prefix the tag with a minus '-'. When you are done with the tags
  just hit return.

* It stores the history of auto-completion in a mapping file, for
  converting transaction descriptions onto payee/account(/tag) names.
  You can also edit this by hand. It can load this in future as the
  basis of its guesses.

* The payee/account names used in the autocompletion are read both from
  the mapping file and, optionally, from a Ledger file or files. It runs
  `ledger payees` and `ledger accounts` to get the names. The tags are
  only read from the mapping file.


Synopsis
--------

    icsv2ledger.py [options] -a STR [infile [outfile]]


Arguments summary
-----------------

    infile                input filename or stdin in CSV syntax
    outfile               output filename or stdout in Ledger syntax


Options summary
---------------

Options can either be used from command line or in configuration file.
`--account` is a mandatory option on command line. `--config-file` and
`--help` are only usable from command line.

    --account STR, -a STR
                          ledger account used as source
    --clear-screen, -C    clear screen for every transaction
    --cleared-character {*,!, }
                          character to clear a transaction
    --config-file FILE, -c FILE
                          configuration file
    --credit INT          csv column number matching credit amount
    --csv-date-format STR
                          date format in csv input file
    --currency STR        the currency of amounts
    --date INT            csv column number matching date
    --debit INT           csv column number matching debit amount
    --default-expense STR
                          ledger account used as destination
    --desc STR            csv column number matching description
    --ledger-date-format STR
                          date format for ledger output file
    --ledger-file FILE, -l FILE
                          ledger file where to read payees/accounts
    --mapping-file FILE   file which holds the mappings
    --quiet, -q           do not prompt if account can be deduced
    --skip-lines INT      number of lines to skip from CSV file
    --tags, -t            prompt for transaction tags
    --template-file FILE  file which holds the template
    -h, --help            show this help message and exit


Options
-------

Options can either be used from command line or in configuration file.
From command line the syntax is `--long-option VALUE` with dashes, and
in configuration file the syntax is `long_option=VALUE` with
underscores.

There is an order of _precedence_ for options. First hard coded default
(documented below) are used, overridden by options from configuration
file if any, and finally overriden by options from command line if any.


**`--account STR, -a STR`**

is the ledger account used as source for ledger transactions. This is
the only mandatory option on command line. Default is
`Assets:Bank:Current`.

When used from command line, it is both the section name in
configuration file and the account name. Account name could then be
overriden in configuration file. See section
[Configuration file example](#configuration-file-example) where `SAV`
from command line is overriden with `account=Assets:Bank:Savings
Account`.

**`--clear-screen, -C`**

will clear the screen before every prompting. Default is `False`.

**`--cleared-character {*,!, }`**

is the character to mark a transaction as cleared. Ledger possible value
are `*` or `!` or ` `. Default is `*`.

**`--config-file FILE, -c FILE`**

is configuration filename.

The file used will be first found in that order:

1. Filename given on command line with `--config-file`,
2. `.icsv2ledgerrc` in current directory,
3. `.icsv2ledgerrc` in home directory.

**`--credit INT`**

is the CSV file column which contains _credit_ amounts. The first column
in the CSV file is numbered 1. Default is `4`.

**`--csv-date-format STR`**

describes the date format in the CSV file. 

See the
[python documentation](http://docs.python.org/library/datetime.html#strftime-strptime-behavior)
for the various format codes supported in this expression.

**`--currency STR`**

is the currency of amounts. Default is locale currency_symbol.

**`--date INT`**

is the CSV file column which contains the transaction date. Default is
`1`.

**`--debit INT`**

is the CSV file column which contains _debit_ amounts. Default is `3`.

If your bank represents debits as negative numbers in the credit column,
than just set `debit` to be `-1` and icsv2ledger will do the right
thing.

**`--default-expense STR`**

is the default ledger account used as destination (generally an expense)
for ledger transactions. Default is `Expenses:Unknown`.

**`--desc STR`**

is the CSV file column which contains the transaction description as
supplied by the bank. Default is `2`.

This _description_ will be used as the input for determing which payee
and account to use by the auto-completion.

It is possible to provide a comma separated list of csv column indices
(like `desc=2,5`) that will concatenate fields in order to form a unique
description. That enriched description will serve as base for the
mapping.

**`--ledger-date-format STR`**

describes the date format to be used when creating ledger entries. If
`--ledger-date-format` is defined, then `--csv-date-format` must also be
defined to be able to convert dates. If `--ledger-date-format` is not
defined, then the date from CSV file is reused.

See the
[python documentation](http://docs.python.org/library/datetime.html#strftime-strptime-behavior)
for the various format codes supported in this expression.

**`--ledger-file FILE, -l FILE`**

is ledger filename where to get the list of already defined accounts and
payees.

The file used will be first found in that order:

1. Filename given on command line with `--ledger-file`,
2. `.ledger` in current directory,
3. `.ledger` in home directory.

**`--mapping-file FILE`**

is the file which holds the mapping between the description and the
payee/account names to use. See section [Mapping file](#mapping-file).

The file used will be first found in that order:

1. Filename given on command line with `--mapping-file`,
2. `.icsv2ledgerrc-mapping` in current directory,
3. `.icsv2ledgerrc-mapping` in home directory.

Warning: the file must exists so that mapping are added to file.

**`--quiet, -q`**

will not prompt if account can be deduced from existing mapping. Default
is `False`.

**`--skip-lines INT`**

is the number of lines to skip from the beginning of the CSV file.
Default is `1`.

**`--tags, -t`**

will interactively prompt for transaction tags. Default is `False`.

The normal behavior is for one description to prompt for payee and
account, and store this in mapping file. By setting this option, the
description can also be mapped to additional tags.

At the prompt: fill a tagname and press Enter key as many time you need
tags. Remove an existing tag by preceding it with minus, e.g.
`-tagname`. When finished, press Enter key on an empty line.

This `--tags` option only _prompt_ for tags. You have to add `; {tags}`
in your template to make tags appear in generated Ledger transactions.

**`--template-file FILE`**

is template filename, which contains the template to use when generating
ledger transactions. See section
[Transaction template file](#transaction-template-file).

The file used will be first found in that order:

1. Filename given on command line with `--template-file`,
2. `.icsv2ledgerrc-template` in current directory,
3. `.icsv2ledgerrc-template` in home directory.


Example
-------

The below command will use the [SAV] section of the configuration file
to process the CSV file.

    ./icsv2ledger.py -a SAV file.csv


Configuration file example
--------------------------

The following is an example configuration file where you can save your
icsv2ledger's options.

A configuration file typically contains one section per bank account to
be imported. In the below example there are two bank accounts: SAV and
CHQ.

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

    [SAV_addons]
    beneficiary=3
    purpose=4


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


Addons
------

In section [Configuration file example](#configuration-file-example) the
`SAV_addons` section enables to save a CSV field value to a tag value.
Those tags can then be used, for the SAV account, in your own
transaction template:

     ; purpose: {addon_purpose}
     ; beneficiary: {addon_beneficiary}


Mapping file
------------

A typical mapping file might look like:

    /SAFEWAY/,Safeway,Expenses:Food
    /ITUNES.*/,iTunes,Expenses:Entertainment
    THE WRESTLERS INN,"The ""Wrestlers"" Inn",Expenses:Food
    /MACY'S/,"Macy's, Inc.",Expenses:Food
    MY COMPANY 1234,My Company,Income:Salary
    MY COMPANY 1234,My Company 1234,Income:Salary:Tips

It uses simple string-matching by default, but if you put a '/' at the
start and end of a string it will instead be interpreted as a regular
expression.

Mapping is based on your historical decisions. Later matching entries
overwrite earlier ones, that is in example above `MY COMPANY 1234` will
be mapped to `My Company 1234` and `Income:Salary:Tips`.


Transaction template file
-------------------------

The built-in default template is as follows:

    {date} {cleared_character} {payee}
        ; MD5Sum: {md5sum}
        ; CSV: {csv}
        {debit_account:<60}    {debit_currency} {debit}
        {credit_account:<60}    {credit_currency} {credit}

Details on how to format the template are found in the
[Format Specification Mini-Language](http://docs.python.org/library/string.html#formatspec).

The value that can be used are: `date`, `cleared_character`, `payee`,
`transaction_index`, `debit_account`, `debit_currency`, `debit`,
`credit_account`, `credit_currency`, `credit`, `tags`, `md5sum`, `csv`.
And also the addon tags like `addon_xxxx`. See section
[Addons](#addons).


Contributing
------------

Feedback/contributions most welcome.


Known Issues
------------

On Mac OS X when CSV is passed via stdin to icsv2ledger you may not see
any prompts offering defaults and asking for your input. This is due to
an inferior readline library (libedit) installed by default on Mac OS X.
Install a proper readline library and your good to go.

    % sudo easy_install readline


Author
------

icsv2ledger was originally created by
[Quentin Stafford-Fraser](http://qandr.org/quentin) but includes
valuable contributions from many others, including Peter Ross, Alexis
Hildebrandt, [Thierry](mailto:thdox@free.fr) and Eric Entzel.


See also
--------

[ledger](http://ledger-cli.org), [hledger](http://hledger.org/)
