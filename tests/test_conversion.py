import unittest
from io import StringIO

from icsv2ledger import main, parse_args_and_config_file, read_mapping_file


class TestLocationService(unittest.TestCase):

    def test_simple_parsing(self):
        infile = open('stubs/simple.csv')
        out = StringIO()

        args = parse_args_and_config_file()
        args.quiet = True
        args.infile = infile
        args.outfile = out
        args.csv_date_format = "%d/%m/%Y"
        args.skip_lines = 0
        args.debit = 0
        args.delimiter = ';'
        args.csv_decimal_comma = True
        args.mapping_file = 'stubs/simple_mapping.txt'
        main(args)

        infile.close()

        self.assertEqual(
            out.getvalue(), """15/03/2019 * My Restaurant
    ; MD5Sum: ae5107b79f9e314ff434bffea8485136
    ; CSV: 15/03/2019;CREDIT CARD 15/12/2018 MY RESTAURANT;;-92,90;EUR
    Expenses:Dining
    Assets:Bank:Current                                              -92.90

16/03/2019 * Unknown Transfer
    ; MD5Sum: 5db6ba322210ab10f22662caf208b571
    ; CSV: 16/03/2019;TRANSFER RECEIVED MR UNKNOWN;;250,73;EUR
    Income:Unknown
    Assets:Bank:Current                                              250.73

"""
        )

    def test_simple_parsing_another_format(self):
        infile = open('stubs/simple_2.csv')
        out = StringIO()

        args = parse_args_and_config_file()
        args.quiet = True
        args.infile = infile
        args.outfile = out
        args.csv_date_format = "%d %b %Y"
        args.ledger_date_format= "%Y/%m/%d"
        args.skip_lines = 0
        args.debit = 3
        args.credit = 4
        args.delimiter = ';'
        args.mapping_file = 'stubs/simple_mapping.txt'
        main(args)

        infile.close()

        self.assertEqual(
            out.getvalue(), """2018/12/10 * Unknown Transfer
    ; MD5Sum: df063bb50d2de83e633e976edd1e5688
    ; CSV: 10 Dec 2018 ; To John Doe  ; 20.75 ;  ;  ;  ; 48.35; transfers; Bob + coffee+groceries :)
    Expenses:Unknown                                                 20.75
    Assets:Bank:Current

"""
        )

    def test_tag_mapping(self):
        result = read_mapping_file('stubs/tag_mapping.txt')

        self.assertEqual(result[0].tags, [])
        self.assertEqual(result[1].tags, ["tag1", "tag2"])

    def test_tag_transfer_to_mapping(self):
        result = read_mapping_file('stubs/transfer_mapping_tags.txt')

        self.assertEqual(result[0].tags, [])
        self.assertEqual(result[1].tags, ["tag1", "tag2"])
        self.assertEqual(result[2].tags, ["tag3", "tag4"])
        self.assertEqual(result[2].transfer_to, "Assets:Bank:Savings")

    def test_tag_transfer_to_file_mapping(self):
        result = read_mapping_file('stubs/transfer_mapping_file.txt')

        self.assertEqual(result[2].tags, ["tag1"])
        self.assertEqual(result[2].transfer_to, "Assets:Bank:Savings")
        self.assertEqual(result[2].transfer_to_file, "savings.dat")

    def test_transfer_parsing(self):
        infile = open('stubs/transfer.csv')
        out = StringIO()

        args = parse_args_and_config_file()
        args.quiet = True
        args.infile = infile
        args.outfile = out
        args.csv_date_format = "%d/%m/%Y"
        args.skip_lines = 0
        args.debit = 0
        args.delimiter = ';'
        args.csv_decimal_comma = True
        args.mapping_file = 'stubs/transfer_mapping.txt'
        main(args)

        infile.close()

        self.assertEqual(out.getvalue(), """15/03/2019 * My Restaurant
    ; MD5Sum: ae5107b79f9e314ff434bffea8485136
    ; CSV: 15/03/2019;CREDIT CARD 15/12/2018 MY RESTAURANT;;-92,90;EUR
    Expenses:Dining
    Assets:Bank:Current                                              -92.90

16/03/2019 * Unknown Transfer
    ; MD5Sum: 5db6ba322210ab10f22662caf208b571
    ; CSV: 16/03/2019;TRANSFER RECEIVED MR UNKNOWN;;250,73;EUR
    Income:Unknown
    Assets:Bank:Current                                              250.73

17/03/2019 * Savings
    ; MD5Sum: 1b64b0eae41356831145b328132a9a44
    ; CSV: 17/03/2019;TRANSFER SENT SAVINGS ACC;;-100,00;EUR
    Transfers:Savings
    Assets:Bank:Current                                              -100.00

17/03/2019 * Savings
    ; MD5Sum: 1b64b0eae41356831145b328132a9a44
    ; CSV: 17/03/2019;TRANSFER SENT SAVINGS ACC;;-100,00;EUR
    Assets:Bank:Savings
    Transfers:Savings                                                -100.00

17/03/2019 * My Restaurant
    ; MD5Sum: 4b780786ee44c6a55b2140ef7251c221
    ; CSV: 17/03/2019;CREDIT CARD 17/12/2018 MY RESTAURANT;;-80,50;EUR
    Expenses:Dining
    Assets:Bank:Current                                              -80.50

""")

    def test_transfer_parsing_duplicates(self):
        infile = open('stubs/transfer.csv')
        out = StringIO()

        args = parse_args_and_config_file()
        args.quiet = True
        args.infile = infile
        args.outfile = out
        args.csv_date_format = "%d/%m/%Y"
        args.skip_lines = 0
        args.debit = 0
        args.delimiter = ';'
        args.csv_decimal_comma = True
        args.ledger_file = 'stubs/parsed_transfer.txt'
        args.skip_dupes = True
        args.mapping_file = 'stubs/transfer_mapping.txt'
        main(args)

        infile.close()

        self.assertEqual(out.getvalue(), """17/03/2019 * My Restaurant
    ; MD5Sum: 4b780786ee44c6a55b2140ef7251c221
    ; CSV: 17/03/2019;CREDIT CARD 17/12/2018 MY RESTAURANT;;-80,50;EUR
    Expenses:Dining
    Assets:Bank:Current                                              -80.50

""")

