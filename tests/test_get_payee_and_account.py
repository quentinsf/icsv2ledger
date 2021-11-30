from icsv2ledger import get_payee_and_account


def test() -> None:
    entry = []

    result = get_payee_and_account(entry)

    assert result == ()
