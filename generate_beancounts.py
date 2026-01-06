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


ACCOUNT_CSV = "account.csv"
ACCOUNT_REGEX_CSV = "account_regex.csv"

TAB = "\t"
COMMA = ","
DOT = "."
SEMICOLON = ";"
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
                    (REGEX, str),
                    (ACCOUNT_NAME, str),
                ]
            ),
        ),
    ]
)


kontoplan, errors, kontoplan_options = loader.load_file("kontoplan.beancount")
kontoplan_accounts = [account.account for account in kontoplan]

regnskab, errors, options = loader.load_file("regnskab.beancount")
links = [link for link in regnskab if link.meta.get("link")]


def load_csv(filename, spec, sep=SEMICOLON):
    dicts = pd.read_csv(
        filename, names=spec.keys(), sep=sep, encoding="utf-8", dtype=spec
    ).to_dict(orient="records")
    return [SimpleNamespace(**row) for row in dicts]


def main():
    yr = len(sys.argv) > 1 and sys.argv[1] or "21"

    # load account csv
    all_accounts = dict(
        [
            (x.account_name.casefold(), "%s:%s" % (x.account_group, x.account_name))
            for x in load_csv(ACCOUNT_CSV, specs[ACCOUNT], SEMICOLON)
        ]
    )

    account_regexes = [
        (x.account_name, re.compile(x.regex, re.IGNORECASE), x.regex.casefold())
        for x in load_csv(ACCOUNT_REGEX_CSV, specs[ACCOUNT_REGEX], SEMICOLON)
    ]

    # load bank csv
    bank_csv = load_csv(path.join(yr, "aps20%s.csv" % (yr,)), specs[BANK], SEMICOLON)

    # process each row in bank_csv
    for row in bank_csv:
        date_payed = bank_date_parser(row.date_payed)
        if date_payed.month > 3:
            continue
        amount = parse_amount(row.amount, DOT)
        total = parse_amount(row.total, DOT)

        # match account
        desc = row.description.casefold()
        account_matches = [a for a, regex, x in account_regexes if x in desc]
        if len(account_matches) == 0:
            print("Ingen matches for %s" % (row.description,), len(account_matches))
            continue

        account_matches = list(set(account_matches))
        if len(account_matches) > 1:
            print(
                "Forskellige konti matcher for %s" % (row.description,), account_matches
            )
            continue

        account_match = account_matches.pop()
        if account_match.casefold() not in all_accounts:
            print(
                "Konto %s (matchet fra %s) findes ikke i all_accounts"
                % (account_match, row.description)
            )
            break

        # print(date_payed, amount, total)


if __name__ == "__main__":
    main()
