import os
import sys
import pandas as pd
from os import path
from beancount import loader
from collections import OrderedDict
from datetime import datetime
import re
from jinja2 import Environment, FileSystemLoader


def write_file(filename, content, encoding="utf-8"):
    with open(filename, "w", encoding=encoding) as f:
        if isinstance(content, list):
            f.write("\n".join(content))
        else:
            f.write(content)


def format_money(num):
    return "{:,.2f}".format(num)


def date_parser(date_format):
    return lambda d: datetime.strptime(d, date_format)


def get_bank_row_key(account_name, date_payed):
    return "%s_%s" % (account_name, date_payed.strftime("%Y%m%d"))


GENERATED_DIR = "generated"
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
    UDGIFT_MEDMOMS_CSV,
    UDGIFT_CSV,
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
        "udgift_medmoms",
        "udgift",
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
    AMOUNT_NEGATED,
    POST_LINK,
    DESCRIPTION,
    TOTAL,
    ACCOUNT_NAME,
    ACCOUNT_GROUP,
    REGEX,
    DATE_PAYED_KEY,
    DATE_POSTED_KEY,
    TEMPLATE_NAME,
    ACCOUNT2,
    ACCOUNT3,
    TRANSACTION_TYPE,
    TEXT,
    EXTRA_TEXT,
    CURRENCY,
) = (
    "date_posted",
    "date_payed",
    "account",
    "amount_vat",
    "amount",
    "amount_negated",
    "post_link",
    "description",
    "total",
    "account_name",
    "account_group",
    "regex",
    "date_payed_key",
    "date_posted_key",
    "template_name",
    "account2",
    "account3",
    "transaction_type",
    "text",
    "extra_text",
    "currency",
)

specs = OrderedDict(
    [
        (
            UDGIFT_MEDMOMS_CSV,
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
            UDGIFT_CSV,
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
                    (ACCOUNT2, str),
                    (ACCOUNT3, str),
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
            (k[ACCOUNT_GROUP], k)
            for k in load_csv(
                TRANSACTION_TYPE_CSV, specs[TRANSACTION_TYPE_CSV], SEMICOLON
            )
        ]
    )

    # process each row in bank_csv
    account_groups = []
    errors = []
    transactions = []
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
            errors.append("Ingen matches for %s" % (row[DESCRIPTION],))
            continue

        account_matches = list(set(account_matches))
        if len(account_matches) > 1:
            errors.append(
                "Forskellige konti matcher for %s" % (row[DESCRIPTION],),
                account_matches,
            )
            continue

        account_match = account_matches.pop()
        if account_match.casefold() not in all_accounts:
            errors.append(
                "Konto %s (matchet fra %s) findes ikke i all_accounts"
                % (account_match, row[DESCRIPTION])
            )
            continue

        account_name = all_accounts[account_match.casefold()][-1]
        account_group = all_accounts[account_match.casefold()][0]
        bank_row_key = get_bank_row_key(account_name, date_payed)

        if bank_row_key in bank_to_invoice_date:
            continue

        # transaktionstype hvor der foerst ses om der er en tilknyttet account_group og herefter account:_name
        transaction_type = transaction_types.get(
            account_group, transaction_types.get(account_name)
        )
        if not transaction_type:
            errors.append(
                "Ingen transaktionstype for %s %s" % (account_group, account_name)
            )
            continue
        account_groups.append(account_group)

        # todo: check for already processed transaction

        # todo: negate amount if needed
        amount = abs(amount)
        transactions.append(
            {
                DATE_PAYED: date_payed,
                DATE_POSTED: date_payed,  # todo:
                AMOUNT: format_money(amount),
                AMOUNT_NEGATED: format_money(-amount),
                TOTAL: format_money(total),
                ACCOUNT: account_name,
                ACCOUNT_GROUP: account_group,
                TRANSACTION_TYPE: transaction_type,
                TEXT: row[DESCRIPTION],
                EXTRA_TEXT: row[DESCRIPTION],  # todo:
                ACCOUNT2: transaction_type[ACCOUNT2],
                ACCOUNT3: transaction_type[ACCOUNT3],
                CURRENCY: "DKK",  # todo
            }
        )

    #
    # date_posted = bank_to_invoice_date[bank_row_key]

    # print(date_payed, amount, total)
    if errors:
        print("\n".join(errors))
        return

    # opdater kontoplan fil
    write_file(
        path.join(GENERATED_DIR, "kontoplan.beancount"),
        ["1900-01-01 open %s DKK" % (x[1],) for x in sorted(all_accounts.values())],
    )

    # transaktioner
    output = []
    for t in transactions:
        print(t[TRANSACTION_TYPE][TEMPLATE_NAME])
        output.append(templates[t[TRANSACTION_TYPE][TEMPLATE_NAME]].render(t))
    write_file(path.join(GENERATED_DIR, "%s.beancount" % (yr,)), "\n\n".join(output))

    # print("\n".join(sorted(list(set(account_groups)))))


if __name__ == "__main__":
    main()
