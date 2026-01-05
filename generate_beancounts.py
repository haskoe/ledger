import sys
import pandas as pd
from os import path
from beancount import loader
from types import SimpleNamespace
from collections import OrderedDict
from datetime import datetime
from itertools import groupby
import re


def date_parser(date_format):
    return lambda d: datetime.strptime(d, date_format)


TAB = "\t"
COMMA = ","
DOT = "."
try:
    decimal_separator = float("1%s1" % (COMMA,)) == 1.1 and COMMA
except ValueError:
    decimal_separator = DOT
opposite_decimal_separator = decimal_separator == COMMA and DOT or COMMA


def parse_amount(amount, thousand_separator):
    return float(
        amount.replace(thousand_separator, "").replace(
            thousand_separator == DOT and COMMA or DOT, decimal_separator
        )
    )


bank_date_parser = date_parser("%d-%m-%Y")

# input filnavne
KOEB_MEDMOMS, KOEB_UDENMOMS, BETALING, SALG, BANK, ACCOUNT, ACCOUNT_REGEX = (
    "koeb_medmoms",
    "koeb_udenmoms",
    "betaling",
    "salg",
    "bank",
    "account",
    "account_regex",
)

# CSV column names
(
    DATE_POSTED,
    DATE_PAYED,
    ACCOUNT,
    AMOUNT_VAT,
    AMOUNT,
    POST_LINK,
    DESCRIPTION,
    TOTAL,
    ACCOUNT_NAME,
    ACCOUNT_GROUP,
    REGEX,
) = (
    "date_posted",
    "date_payed",
    "account",
    "amount_vat",
    "amount",
    "post_link",
    "description",
    "total",
    "account_name",
    "account_group",
    "regex",
)

specs = OrderedDict(
    [
        (
            KOEB_MEDMOMS,
            OrderedDict(
                [
                    (DATE_POSTED, int),
                    (ACCOUNT, str),
                    (AMOUNT_VAT, float),
                    (AMOUNT, float),
                ]
            ),
        ),
        (
            KOEB_UDENMOMS,
            OrderedDict(
                [
                    (DATE_POSTED, int),
                    (ACCOUNT, str),
                    (AMOUNT, float),
                ]
            ),
        ),
        (BETALING, OrderedDict([(DATE_PAYED, int), (POST_LINK, str)])),
        (
            SALG,
            OrderedDict(
                [
                    (DATE_POSTED, int),
                    (ACCOUNT, str),
                    (AMOUNT_VAT, float),
                    (AMOUNT, float),
                ]
            ),
        ),
        (
            BANK,
            OrderedDict(
                [
                    (DATE_PAYED, str),
                    ("dummy", str),
                    (DESCRIPTION, str),
                    (AMOUNT, str),
                    (TOTAL, str),
                ]
            ),
        ),
        (
            ACCOUNT,
            OrderedDict(
                [
                    (ACCOUNT_NAME, str),
                    (ACCOUNT_GROUP, str),
                ]
            ),
        ),
        (
            ACCOUNT_REGEX,
            OrderedDict(
                [
                    (ACCOUNT_NAME, str),
                    (ACCOUNT, str),
                ]
            ),
        ),
    ]
)


kontoplan, errors, kontoplan_options = loader.load_file("kontoplan.beancount")
accounts = [account.account for account in kontoplan]

regnskab, errors, options = loader.load_file("regnskab.beancount")
links = [link for link in regnskab if link.meta.get("link")]


def load_csv(filename, spec, sep=";"):
    dicts = pd.read_csv(
        filename, names=spec.keys(), sep=sep, encoding="utf-8", dtype=spec
    ).to_dict(orient="records")
    return [SimpleNamespace(**row) for row in dicts]


def main():
    yr = len(sys.argv) > 1 and sys.argv[1] or "21"

    # load account csv
    accounts = dict(
        [
            (x.account_name, x.account_group)
            for x in load_csv("account.csv", specs[ACCOUNT], TAB)
        ]
    )

    account_regexes = [
        (x.account_name, re.compile(x.account_name, re.IGNORECASE))
        for x in load_csv("account_regex.csv", specs[ACCOUNT_REGEX], TAB)
    ]

    # load bank csv
    bank_csv = load_csv(path.join(yr, "aps20%s.csv" % (yr,)), specs[BANK], ";")

    # process each row in bank_csv
    for row in bank_csv:
        date_payed = bank_date_parser(row.date_payed)
        if date_payed.month != 1:
            continue
        amount = parse_amount(row.amount, DOT)
        total = parse_amount(row.total, DOT)

        # match account
        account_matches = [
            account
            for account, regex in account_regexes
            if regex.match(row.description)
        ]
        if len(account_matches) != 1:
            print("incorrect matches for %s" % (row.description,))
        account = account_matches[0]
        print(date_payed, amount, total)


if __name__ == "__main__":
    main()
