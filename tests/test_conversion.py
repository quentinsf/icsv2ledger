import pathlib

from icsv2ledger import main, parse_args_and_config_file, read_mapping_file


def test_simple_parsing(tmp_path: pathlib.Path) -> None:
    infile = open('stubs/simple.csv')
    out = tmp_path / 'outfile'
    args = parse_args_and_config_file()
    args.quiet = True
    args.infile = infile
    args.outfile = out.open('w+')
    args.csv_date_format = "%d/%m/%Y"
    args.skip_lines = 0
    args.debit = 0
    args.delimiter = ';'
    args.csv_decimal_comma = True
    args.mapping_file = 'stubs/simple_mapping.txt'
    args.currency = ''

    main(args)

    infile.close()
    assert out.open().read() == """15/03/2019 * My Restaurant
    ; MD5Sum: ade6e00119fe2b145ecddb30e50e2d4c
    ; CSV: 15/03/2019;CREDIT CARD 15/12/2018 MY RESTAURANT;;-92,90;EUR
    Expenses:Dining
    Assets:Bank:Current                                              -92.90

16/03/2019 * Unknown Transfer
    ; MD5Sum: 2313495c75e0d4794c1f445d585f34c4
    ; CSV: 16/03/2019;TRANSFER RECEIVED MR UNKNOWN;;250,73;EUR
    Income:Unknown
    Assets:Bank:Current                                              250.73

"""


def test_simple_parsing_another_format(tmp_path: pathlib.Path) -> None:
    infile = open('stubs/simple_2.csv')
    out = tmp_path / 'outfile'
    args = parse_args_and_config_file()
    args.quiet = True
    args.infile = infile
    args.outfile = out.open('w+')
    args.csv_date_format = "%d %b %Y"
    args.ledger_date_format = "%Y/%m/%d"
    args.skip_lines = 0
    args.debit = 3
    args.credit = 4
    args.delimiter = ';'
    args.mapping_file = 'stubs/simple_mapping.txt'
    args.currency = ''

    main(args)

    infile.close()
    assert out.open().read() == """2018/12/10 * Unknown Transfer
    ; MD5Sum: 5c3d6f20c79b6ba0760c43c3b9c9be47
    ; CSV: 10 Dec 2018 ; To John Doe  ; 20.75 ;  ;  ;  ; 48.35; transfers; Bob + coffee+groceries :)
    Expenses:Unknown                                                 20.75
    Assets:Bank:Current

"""


def test_tag_mapping() -> None:
    result = read_mapping_file('stubs/tag_mapping.txt')

    assert result[0].tags == []
    assert result[1].tags == ["tag1", "tag2"]


def test_tag_transfer_to_mapping() -> None:
    result = read_mapping_file('stubs/transfer_mapping_tags.txt')

    assert result[0].tags == []
    assert result[1].tags == ["tag1", "tag2"]
    assert result[2].tags == ["tag3", "tag4"]
    assert result[2].transfer_to == "Assets:Bank:Savings"


def test_tag_transfer_to_file_mapping() -> None:
    result = read_mapping_file('stubs/transfer_mapping_file.txt')

    assert result[2].tags == ["tag1"]
    assert result[2].transfer_to == "Assets:Bank:Savings"
    assert result[2].transfer_to_file == "savings.dat"


def test_transfer_parsing(tmp_path: pathlib.Path) -> None:
    infile = open('stubs/transfer.csv')
    out = tmp_path / 'outfile'
    args = parse_args_and_config_file()
    args.quiet = True
    args.infile = infile
    args.outfile = out.open('w+')
    args.csv_date_format = "%d/%m/%Y"
    args.skip_lines = 0
    args.debit = 0
    args.delimiter = ';'
    args.csv_decimal_comma = True
    args.mapping_file = 'stubs/transfer_mapping.txt'
    args.currency = ''

    main(args)

    infile.close()
    assert out.open().read() == """15/03/2019 * My Restaurant
    ; MD5Sum: ade6e00119fe2b145ecddb30e50e2d4c
    ; CSV: 15/03/2019;CREDIT CARD 15/12/2018 MY RESTAURANT;;-92,90;EUR
    Expenses:Dining
    Assets:Bank:Current                                              -92.90

16/03/2019 * Unknown Transfer
    ; MD5Sum: 2313495c75e0d4794c1f445d585f34c4
    ; CSV: 16/03/2019;TRANSFER RECEIVED MR UNKNOWN;;250,73;EUR
    Income:Unknown
    Assets:Bank:Current                                              250.73

17/03/2019 * Savings
    ; MD5Sum: f16676d80071cd9f5fc0a6db3387717a
    ; CSV: 17/03/2019;TRANSFER SENT SAVINGS ACC;;-100,00;EUR
    Transfers:Savings
    Assets:Bank:Current                                              -100.00

17/03/2019 * Savings
    ; MD5Sum: f16676d80071cd9f5fc0a6db3387717a
    ; CSV: 17/03/2019;TRANSFER SENT SAVINGS ACC;;-100,00;EUR
    Assets:Bank:Savings
    Transfers:Savings                                                -100.00

17/03/2019 * My Restaurant
    ; MD5Sum: 6b8159889e4f408c39dd85f19e3eab1a
    ; CSV: 17/03/2019;CREDIT CARD 17/12/2018 MY RESTAURANT;;-80,50;EUR
    Expenses:Dining
    Assets:Bank:Current                                              -80.50

"""


def test_transfer_parsing_duplicates(tmp_path: pathlib.Path) -> None:
    infile = open('stubs/transfer.csv')
    out = tmp_path / 'outfile'
    args = parse_args_and_config_file()
    args.quiet = True
    args.infile = infile
    args.outfile = out.open('w+')
    args.csv_date_format = "%d/%m/%Y"
    args.skip_lines = 0
    args.debit = 0
    args.delimiter = ';'
    args.csv_decimal_comma = True
    args.ledger_file = 'stubs/parsed_transfer.txt'
    args.skip_dupes = True
    args.mapping_file = 'stubs/transfer_mapping.txt'
    args.currency = '£'

    main(args)

    infile.close()
    assert out.open().read() == """17/03/2019 * My Restaurant
    ; MD5Sum: 6b8159889e4f408c39dd85f19e3eab1a
    ; CSV: 17/03/2019;CREDIT CARD 17/12/2018 MY RESTAURANT;;-80,50;EUR
    Expenses:Dining
    Assets:Bank:Current                                             £ -80.50

"""
