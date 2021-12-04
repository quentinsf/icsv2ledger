import argparse
import pathlib
from typing import Callable
from unittest import mock

from icsv2ledger import Entry, get_payee_and_account


@mock.patch('icsv2ledger.prompt_for_value')
def test(mock_prompt_for_value: Callable, tmp_path: pathlib.Path) -> None:
    """
    Mapping file is empty, new mapping based on input is written to file.
    """
    mapping_file = tmp_path / 'mapping.txt'
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
        mapping_file=str(mapping_file),
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
    mock_prompt_for_value.side_effect = ["__PAYEE__", "__ACCOUNT__"]

    result = get_payee_and_account(
        options, mappings, entry, possible_accounts, possible_payees, possible_tags, possible_yesno
    )

    payee, account, tags, transfer_to, transfer_to_file = result
    assert payee == '__PAYEE__'
    assert account == '__ACCOUNT__'
    assert tags == []
    assert transfer_to is None
    assert transfer_to_file is None
    assert mapping_file.open().read() == 'TRANSFER RECEIVED MR UNKNOWN,__PAYEE__,__ACCOUNT__\n'
