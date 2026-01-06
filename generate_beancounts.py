import os
import sys
import pandas as pd
from os import path
from beancount import loader
from types import SimpleNamespace
from collections import OrderedDict
from datetime import datetime
from itertools import groupby
import re
from jinja2 import Environment, FileSystemLoader


def date_parser(date_format):
    return lambda d: datetime.strptime(d, date_format)


def get_bank_row_key(account_name, date_payed):
    return "%s_%s" % (account_name, date_payed.strftime("%Y%m%d"))


TEMPLATE_DIR = "templates"
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
(
    KOEB_MEDMOMS_CSV,
    KOEB_UDENMOMS_CSV,
    BETALING_CSV,
    SALG_CSV,
    BANK_CSV,
    ACCOUNT_CSV,
    ACCOUNT_REGEX_CSV,
    BANK_TO_INVOICE_DATE_CSV,
    TRANSACTION_TYPE_CSV,
) = [
    "%s.csv" % (fn,)
    for fn in (
        "koeb_medmoms",
        "koeb_udenmoms",
        "betaling",
        "salg",
        "bank",
        "account",
        "account_regex",
        "bank_to_invoice_date",
        "transaction_type",
    )
]

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
    DATE_PAYED_KEY,
    DATE_POSTED_KEY,
    TEMPLATE_NAME,
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
    "date_payed_key",
    "date_posted_key",
    "template_name",
)

specs = OrderedDict(
    [
        (
            KOEB_MEDMOMS_CSV,
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
            KOEB_UDENMOMS_CSV,
            OrderedDict(
                [
                    (DATE_POSTED, int),
                    (ACCOUNT, str),
                    (AMOUNT, float),
                ]
            ),
        ),
        (BETALING_CSV, OrderedDict([(DATE_PAYED, int), (POST_LINK, str)])),
        (
            SALG_CSV,
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
            BANK_CSV,
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
            ACCOUNT_CSV,
            OrderedDict(
                [
                    (ACCOUNT_NAME, str),
                    (ACCOUNT_GROUP, str),
                ]
            ),
        ),
        (
            ACCOUNT_REGEX_CSV,
            OrderedDict(
                [
                    (REGEX, str),
                    (ACCOUNT_NAME, str),
                ]
            ),
        ),
        (
            BANK_TO_INVOICE_DATE_CSV,
            OrderedDict(
                [
                    (DATE_PAYED_KEY, str),
                    (DATE_POSTED_KEY, str),
                ]
            ),
        ),
        (
            TRANSACTION_TYPE_CSV,
            OrderedDict(
                [
                    (ACCOUNT_GROUP, str),
                    (TEMPLATE_NAME, str),
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
    return dicts
    # return [SimpleNamespace(**row) for row in dicts]


def main():
    yr = len(sys.argv) > 1 and sys.argv[1] or "21"

    jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    templates = dict(
        [
            (fn.split(".")[0], jinja_env.get_template(fn))
            for fn in os.listdir(TEMPLATE_DIR)
        ]
    )  # load account csv
    all_accounts = dict(
        [
            (
                x[ACCOUNT_NAME].casefold(),
                (x[ACCOUNT_GROUP], "%s:%s" % (x[ACCOUNT_GROUP], x[ACCOUNT_NAME])),
            )
            for x in load_csv(ACCOUNT_CSV, specs[ACCOUNT_CSV], SEMICOLON)
        ]
    )

    account_regexes = [
        (x[ACCOUNT_NAME], re.compile(x[REGEX], re.IGNORECASE), x[REGEX].casefold())
        for x in load_csv(ACCOUNT_REGEX_CSV, specs[ACCOUNT_REGEX_CSV], SEMICOLON)
    ]

    # load mapning fra bank til faktureringsdato
    bank_to_invoice_date = dict(
        [
            (k[DATE_PAYED_KEY], k[DATE_POSTED_KEY])
            for k in load_csv(
                BANK_TO_INVOICE_DATE_CSV,
                specs[BANK_TO_INVOICE_DATE_CSV],
                SEMICOLON,
            )
        ]
    )

    # load bank csv
    bank_csv = load_csv(
        path.join(yr, "aps20%s.csv" % (yr,)), specs[BANK_CSV], SEMICOLON
    )

    # load transaction type csv
    transaction_types = dict(
        [
            (k[ACCOUNT_GROUP], k[TEMPLATE_NAME])
            for k in load_csv(
                TRANSACTION_TYPE_CSV, specs[TRANSACTION_TYPE_CSV], SEMICOLON
            )
        ]
    )

    # process each row in bank_csv
    account_groups = []
    for row in bank_csv:
        date_payed = bank_date_parser(row[DATE_PAYED])
        if date_payed.month > 1:
            continue
        amount = parse_amount(row[AMOUNT], DOT)
        total = parse_amount(row[TOTAL], DOT)

        # match account
        desc = row[DESCRIPTION].casefold()
        account_matches = [a for a, regex, x in account_regexes if x in desc]
        if len(account_matches) == 0:
            print("Ingen matches for %s" % (row[DESCRIPTION],), len(account_matches))
            continue

        account_matches = list(set(account_matches))
        if len(account_matches) > 1:
            print(
                "Forskellige konti matcher for %s" % (row[DESCRIPTION],),
                account_matches,
            )
            continue

        account_match = account_matches.pop()
        if account_match.casefold() not in all_accounts:
            print(
                "Konto %s (matchet fra %s) findes ikke i all_accounts"
                % (account_match, row[DESCRIPTION])
            )
            break

        account_name = all_accounts[account_match.casefold()][-1]
        account_group = all_accounts[account_match.casefold()][0]
        bank_row_key = get_bank_row_key(account_name, date_payed)

        if bank_row_key in bank_to_invoice_date:
            continue

        # transaktionstype
        transaction_type = transaction_types.get(account_group)
        if not transaction_type:
            print("Ingen transaktionstype for %s %s" % (account_group, account_name))
            continue
        account_groups.append(account_group)

        # date_posted = bank_to_invoice_date[bank_row_key]

        # print(date_payed, amount, total)
    # print("\n".join(sorted(list(set(account_groups)))))


if __name__ == "__main__":
    main()
