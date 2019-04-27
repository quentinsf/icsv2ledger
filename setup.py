from setuptools import setup

setup(
    name='icsv2ledger',
    description='Interactive importing of CSV files to Ledger',
    url='https://github.com/quentinsf/icsv2ledger',
    py_modules=['icsv2ledger'],
    entry_points={
        'console_scripts': ['icsv2ledger=icsv2ledger:cli']
    }
)
