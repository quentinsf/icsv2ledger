import argparse
from typing import Callable
from unittest import mock

from icsv2ledger import Entry, get_payee_and_account


@mock.patch('icsv2ledger.prompt_for_value')
def test(mock_prompt_for_value: Callable) -> None:
    options = argparse.Namespace(
        account='Assets:Bank:Current',
        cleared_character='*',
        credit=4,
        csv_date_format='%d/%m/%Y',
        csv_decimal_comma=True,
        currency='€',
        date=1,
        debit=0,
        default_expense='Expenses:Unknown',
        desc='2',
        effective_date=0,
        ledger_date_format='',
        ledger_decimal_comma=False,
        mapping_file='stubs/simple_mapping.txt',
        prompt_add_mappings=False,
        quiet=True,
        src_account='',
        tags=False,
        template_file=None,
    )
    mappings = []
    entry = Entry(
        fields=['16/03/2019', 'TRANSFER RECEIVED MR UNKNOWN', '', '250,73', 'EUR'],
        raw_csv='16/03/2019;TRANSFER RECEIVED MR UNKNOWN;;250,73;EUR',
        options=options,
    )
    possible_accounts = set()
    possible_payees = set()
    possible_tags = set()
    possible_yesno = set(['N', 'Y'])
    mock_prompt_for_value.return_value = "__PROMPT_VALUE__"

    result = get_payee_and_account(
        options, mappings, entry, possible_accounts, possible_payees, possible_tags, possible_yesno
    )

    assert result == ()
