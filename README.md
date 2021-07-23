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

* The payee/account names used in the auto-completion are read both from
  the mapping file and, optionally, from a Ledger file or files. It runs
  `ledger payees` and `ledger accounts` to get the names. It can also
  scan a separate ledger file containing 'account' definitions. The tags are
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
`--account` is a mandatory option on command line. `--config-file`, `--src-account` and
`--help` are only usable from command line.

    --account STR, -a STR
                          ledger account used as source
    --src-account STR
                          ledger account used as source, overrides --account option
    --clear-screen, -C    clear screen for every transaction
    --cleared-character {*,!, }
                          character to clear a transaction
    --config-file FILE, -c FILE
                          configuration file
    --credit INT          CSV column number matching credit amount
    --csv-date-format STR
                          date format in CSV input file
    --csv-decimal-comma   comma as decimal separator in the CSV
    --currency STR        the currency of amounts
    --date INT            CSV column number matching date
    --debit INT           CSV column number matching debit amount
    --default-expense STR
                          ledger account used as destination
    --delimiter           CSV delimiter
    --desc STR            CSV column number matching description
    --effective-date INT  CSV column number matching effective date
    --encoding STR        text encoding of CSV input file
    --incremental         append output as transactions are processed
    --ledger-binary FILE  path to ledger binary  
    --ledger-date-format STR
                          date format for ledger output file
    --ledger-decimal-comma
                          comma as decimal separator in the ledger
    --ledger-file FILE, -l FILE
                          ledger file where to read payees/accounts
    --mapping-file FILE   file which holds the mappings
    --accounts-file FILE  file which holds a list of allowed accounts
    --quiet, -q           do not prompt if account can be deduced
    --reverse             reverse the order of entries in the CSV file
    --skip-dupes          detect transactions that have already been imported and skip
    --confirm-dupes       detect transactions that have already been imported and prompt to skip
    --skip-lines INT      number of lines to skip from CSV file
    --skip-older-than     skip entries more than X days old
    --tags, -t            prompt for transaction tags
    --template-file FILE  file which holds the template
    --prompt-add-mappings prompt before adding entries to mapping file
    --entry-review        displays summary of ledger formatted entry and prompts before committing
    -h, --help            show this help message and exit


Options
-------

Options can either be used from command line or in configuration file.
From command line the syntax is `--long-option VALUE` with dashes, and
in configuration file the syntax is `long_option=VALUE` with
underscores.

There is an order of _precedence_ for options. First hard coded defaults
(documented below) are used, overridden by options from configuration
file if any, and finally overridden by options from command line if any.


**`--account STR, -a STR`**

is the ledger account used as source for ledger transactions. This is
the only mandatory option on command line. Default is
`Assets:Bank:Current`.

When used from command line, it is both the section name in
configuration file and the account name. Account name could then be
overridden in configuration file. See section
[Configuration file example](#configuration-file-example) where `SAV`
from command line is overridden with `account=Assets:Bank:Savings
Account`.

**`--src-account STR`**

similar to `--account` option, it is the ledger account used as source for ledger transactions but allows the `--account` option to be overridden after the config file has been parsed.  This is a command-line only option and must not be provided in any section of the config file.  Use of this option allows users to treat sections of the config file as generic import recipes that can be used to import all files that use the same layout while providing a means to specify the ledger source account to use during the importing of transactions.

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

See also documentation of `--debit` option for negating amounts.

**`--csv-date-format STR`**

describes the date format in the CSV file. 

See the
[python documentation](http://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior)
for the various format codes supported in this expression.

**`--csv-decimal-comma`**

will assume that number use the comma ',' as decimal in the csv.

If the `--ledger-decimal-comma` option is not set, comma will be
converted into dot.

**`--currency STR`**

is the currency of amounts. Default is locale currency_symbol.

**`--date INT`**

is the CSV file column which contains the transaction date. Default is
`1`.

**`--debit INT`**

is the CSV file column which contains _debit_ amounts. Default is `3`.

If your bank writes all amounts in same column, credits as positive
amounts and debits as negative amounts, then set `credit` to correct
column and `debit` to `0`.

If your bank writes debits as a negative number and you want to negate
the amount, then use `--debit=-3`. It will negate amounts in column 3
and use them as debits amounts.

**`--default-expense STR`**

is the default ledger account used as destination (generally an expense)
for ledger transactions. Default is `Expenses:Unknown`.

**`--delimiter STR`**

is the CSV delimiter character. Default is `,`. Special characters can be
expressed using standard escape sequences, such as `\t` for a tab.

**`--desc STR`**

is the CSV file column which contains the transaction description as
supplied by the bank. Default is `2`.

This _description_ will be used as the input for determining which payee
and account to use by the auto-completion.

It is possible to provide a comma separated list of CSV column indices
(like `desc=2,5`) that will concatenate fields in order to form a unique
description. That enriched description will serve as base for the
mapping.

**`--effective-date INT`**

is the CSV column number which contains the date to be used as the
effective date. Default is `0`. Use of this option currently requires a
template file. See section
[Transaction template file](#transaction-template-file).

**`--encoding STR`**

is the text encoding of the CSV input file. Default is `utf-8`. The encoding
should be specified if the CSV file contains non-ASCII characters (typically in
the transaction description) in an encoding other than UTF-8.

**`--incremental`**

appends output as transactions are processed. The default flow is to process all CSV input and then output the result. When `--incremental` is specified, output is written after every transaction. This allows one to stop (ctrl-c) and restart to progressively process a CSV file (`--skip-dupes` is a useful companion option).

**`--ledger-binary`**

is the path to the ledger binary. Not neccessary if it is in `PATH` or is at either `/usr/bin/ledger` or
`/usr/local/bin/ledger`

**`--ledger-date-format STR`**

describes the date format to be used when creating ledger entries. If
`--ledger-date-format` is defined, then `--csv-date-format` must also be
defined to be able to convert dates. If `--ledger-date-format` is not
defined, then the date from CSV file is reused.

See the
[python documentation](http://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior)
for the various format codes supported in this expression.

**`--ledger-decimal-comma`**

will assume that number should be print using the comma ',' as decimal
when creating ledger entries.

If the `--csv-decimal-comma` option is not set, dot will be converted
into comma.

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

Warning: the file must exists so that mappings are added to the file.

**`--accounts-file FILE`**

is an optional file that can be used to hold a master list of all
account names, and will be used as a source for account names.
See section [Accounts file](#accounts-file).

The file used will be first found in that order:

1. Filename given on command line with `--accounts-file`,
2. `.icsv2ledgerrc-accounts` in current directory,
3. `.icsv2ledgerrc-accounts` in home directory.

**`--quiet, -q`**

will not prompt if account can be deduced from existing mapping. Default
is `False`.

**`--reverse`**

will print ledger entries in reverse of their order in the CSV file.

**`--skip-dupes`**

will attempt to detect duplicate transactions in ledger file by comparing MD5Sum of transactions.  The MD5Sum is calculated from the raw CSV string, with the source account appended to avoid false positives on generic transaction descriptions when the source account is different and thus should not be considered a duplicate. MD5Sum of existing transactions are included as a `; MD5Sum: ...` comment in the current ledger file (which means your output template will need this comment). This can help if you download statements without using a precise date range. A useful pattern is to include MD5Sum comments for both "sides" of a transaction if you download from multiple sources that resolve to a single transaction (e.g. paying a credit card from checking).  Note: use of this flag by itself will detect and skip duplicate entries automatically with no interaction from user.  If you want to be prompted and determine whether to skip or not see `--confirm-dupes`.

**`--confirm-dupes`**

same as `--skip-dupes` but will prompt user to indicate if they want the detected duplicate entry to be skipped or treated as a valid entry.  This is useful when importing transactions that commonly contain generic descriptions.

**`--skip-lines INT`**

is the number of lines to skip from the beginning of the CSV file.
Default is `1`.

**`--tags, -t`**

will interactively prompt for transaction tags. Default is `False`.

The normal behavior is for one description to prompt for payee and
account, and store this in mapping file. By setting this option, the
description can also be mapped to additional tags.

At the prompt: fill a tagname and press Enter key as many times as you need
tags. Remove an existing tag by preceding it with minus, like
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

**`--skip-older-than DAYS`**

will not process any entries in the CSV file which are more than DAYS old.
If DAYS is negative then the entire CSV file is processed.

**`--prompt-add-mappings`**

will prompt user before adding entries to the mapping file. This is useful when you would prefer to manually adjust an existing entry or add the entry manually to the mapping file.

**`--entry-review`**

allows the ability to review the generated ledger entry and Commit, Modify or Skip the entry.  If the entry is not committed then the values for payee, account and optionally tags is prompted for again.

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
    MY TRANSFER 1,Transfer to Savings,Transfers:Savings,transfer_to=Assets:Savings

It uses simple string-matching by default, but if you put a '/' at the
start and end of a string it will instead be interpreted as a regular
expression.

Mapping is based on your historical decisions. Later matching entries
overwrite earlier ones, that is in example above `MY COMPANY 1234` will
be mapped to `My Company 1234` and `Income:Salary:Tips`.

**Experimental**
You can use `transfer_to=` to another asset to make the transfer to record in a "transfer"
double-entry pattern.
In the example above for the Transfers:Savings account with the transfer_to=Assets:Savings
would create the following entries:

2012/01/01 Transfer to Savings
 Transfers:Savings  $100
 Assets:Checking

2012/01/01 Transfer to Savings
 Assets:Savings  $100
 Transfers:Savings

You can additionally add a `file=` value after `transfer_to=` to write the second entry in another file.
This is useful if you split your accounts per file and want to write the first transaction in the checking file
and the second in the savings file.

Accounts File
--------------

To prevent inconsistencies it is possible to user ledger `--strict` mode,
along with a file that defines a list of allowable accounts. (See the ledger
3 manual, section 4.6 'Keeping it Consistent')

The accounts file should look like:

    account Expenses:Food
    account Expenses:Entertainment
    account Income:Salary
    account Income:Salary:Tips

All other lines will be ignored so you if you have a single ledger file that
has account definitions mixed throughout it, it is safe (although potentially 
time consuming) to pass it to icsv2ledger as the accounts-file.

Transaction template file
-------------------------

The built-in default template is as follows:

    {date} {cleared_character} {payee}
        ; MD5Sum: {md5sum}
        ; CSV: {csv}
        {debit_account:<60}    {debit_currency} {debit}
        {credit_account:<60}    {credit_currency} {credit}
        {tags}

Details on how to format the template are found in the
[Format Specification Mini-Language](http://docs.python.org/3/library/string.html#formatspec).

The values that can be used are: `date`, `effective_date`, `cleared_character`,
`payee`, `transaction_index`, `debit_account`, `debit_currency`, `debit`,
`credit_account`, `credit_currency`, `credit`, `tags`, `md5sum`, `csv`.
And also the addon tags like `addon_xxxx`. See section
[Addons](#addons).


Runtime Requirements
-------------------------

icsv2ledger should work in a vanilla Python 2.7 or 3.x environment, as it uses only base packages.

Note that the 'ledger' binary must be installed in the local PATH in which icsv2ledger is used, as the binary is invoked for various operations.

Contributing
------------

Feedback/contributions most welcome.


Known Issues
------------

On Mac OS X when CSV is passed via stdin to icsv2ledger you may not see
any prompts offering defaults and asking for your input. This is due to
an inferior readline library (libedit) installed by default on Mac OS X.
Install a proper readline library and you're good to go.

    % sudo easy_install readline

On Windows the default Python installation does not provide a readline
library. The [pyreadline](https://pypi.python.org/pypi/pyreadline)
library provides native python emulation of this functionality and
must be installed to run this utility.

Author
------

icsv2ledger was originally created by
[Quentin Stafford-Fraser](http://qandr.org/quentin) but includes
valuable contributions from many others, including Peter Ross, Alexis
Hildebrandt, [Thierry](mailto:thdox@free.fr) and Eric Entzel.


See also
--------

[ledger](http://ledger-cli.org), [hledger](http://hledger.org/)
