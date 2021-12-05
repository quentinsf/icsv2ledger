import argparse
import pathlib
from typing import Callable
from unittest import mock

import pytest

from icsv2ledger import Entry, get_payee_and_account, read_mapping_file


@pytest.fixture
def mapping_file(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / 'mapping.txt'


@pytest.fixture
def options(mapping_file: pathlib.Path) -> argparse.Namespace:
    return argparse.Namespace(
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


# --- TESTS ---


@mock.patch('icsv2ledger.prompt_for_value')
def test_new(mock_prompt_for_value: Callable, options: argparse.Namespace, mapping_file: pathlib.Path) -> None:
    """
    Mapping file is empty, new mapping based on input is written to file.
    """
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


@mock.patch('icsv2ledger.prompt_for_value')
def test_matches(mock_prompt_for_value: Callable, options: argparse.Namespace, mapping_file: pathlib.Path) -> None:
    """
    Mapping file contains a single mapping that matches this transaction, user
    confirms the entry using the suggested data so no mapping file changes.
    """
    original_mapping_file_contents = "TRANSFER RECEIVED MR UNKNOWN,Mr Unknown,Income:Earnings\n"
    mapping_file.write_text(original_mapping_file_contents)
    mappings = read_mapping_file(options.mapping_file)
    entry = Entry(
        fields=['16/03/2019', 'TRANSFER RECEIVED MR UNKNOWN', '', '250,73', 'EUR'],
        raw_csv='16/03/2019;TRANSFER RECEIVED MR UNKNOWN;;250,73;EUR',
        options=options,
    )
    possible_accounts = set()
    possible_payees = set()
    possible_tags = set()
    possible_yesno = set(['N', 'Y'])
    mock_prompt_for_value.side_effect = ["Mr Unknown", "Income:Earnings"]

    result = get_payee_and_account(
        options, mappings, entry, possible_accounts, possible_payees, possible_tags, possible_yesno
    )

    payee, account, tags, transfer_to, transfer_to_file = result
    assert payee == 'Mr Unknown'
    assert account == 'Income:Earnings'
    assert tags == []
    assert transfer_to is None
    assert transfer_to_file is None
    assert mapping_file.open().read() == original_mapping_file_contents


@mock.patch('icsv2ledger.prompt_for_value')
def test_multi_matches(
    mock_prompt_for_value: Callable, options: argparse.Namespace, mapping_file: pathlib.Path
) -> None:
    """
    Mapping file contains a two mappings that matche this transaction, user
    picks one and leaves it unchanged. Mapping file is not changed.
    """
    original_mapping_file_contents = (
        "TRANSFER RECEIVED MR UNKNOWN,Mr Unknown,Income:Earnings\n"
        "TRANSFER RECEIVED MR UNKNOWN,Mr Unknown 2,Second:Account\n"
        "SHOP A PURCHASE,Shop A,Expenses:Things\n"
    )
    mapping_file.write_text(original_mapping_file_contents)
    mappings = read_mapping_file(options.mapping_file)
    entry = Entry(
        fields=['16/03/2019', 'TRANSFER RECEIVED MR UNKNOWN', '', '250,73', 'EUR'],
        raw_csv='16/03/2019;TRANSFER RECEIVED MR UNKNOWN;;250,73;EUR',
        options=options,
    )
    possible_accounts = set()
    possible_payees = set()
    possible_tags = set()
    possible_yesno = set(['N', 'Y'])
    mock_prompt_for_value.side_effect = ["Mr Unknown", "Income:Earnings"]

    result = get_payee_and_account(
        options, mappings, entry, possible_accounts, possible_payees, possible_tags, possible_yesno
    )

    payee, account, tags, transfer_to, transfer_to_file = result
    assert payee == 'Mr Unknown'
    assert account == 'Income:Earnings'
    assert tags == []
    assert transfer_to is None
    assert transfer_to_file is None
    assert mapping_file.open().read() == original_mapping_file_contents
