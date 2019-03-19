import unittest
from io import StringIO

from icsv2ledger import main, parse_args_and_config_file


class TestLocationService(unittest.TestCase):

    def test_simple_parsing(self):
        infile = open('stubs/simple.csv')
        out = StringIO()

        args = parse_args_and_config_file()
        args.quiet = True
        args.infile.close()
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
        )
