import os
import sys
import pandas as pd
from os import path
from beancount import loader
from collections import OrderedDict
from datetime import datetime
import re
from jinja2 import Environment, FileSystemLoader
from collections import defaultdict


def write_file(filename, content, encoding="utf-8"):
    with open(filename, "w", encoding=encoding) as f:
        if isinstance(content, list):
            f.write("\n".join(content))
        else:
            f.write(content)


def format_money(num):
    return "{:,.2f}".format(num)


def format_date(dt):
    return dt.strftime("%Y-%m-%d")


def date_parser(date_format):
    return lambda d: datetime.strptime(d, date_format)


def get_bank_row_key(account_name, date_payed):
    return "%s_%s" % (account_name, date_payed.strftime("%Y%m%d"))


def combined_account(account_name, account_group):
    return "%s:%s" % (account_group, account_name)


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
    SALG_TXT,
    PRICES_CSV,
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
        "salg.txt",
        "prices",
    )
]

# CSV column names
(
    DATE_POSTED,
    DATE_PAYED,
    ACCOUNT,
    AMOUNT_WITH_VAT,
    AMOUNT_VAT_FREE,
    AMOUNT_WO_VAT,
    AMOUNT_WO_VAT_NEGATED,
    VAT,
    AMOUNT,
    TOTAL_NEGATED,
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
    ACCOUNT4,
    TRANSACTION_TYPE,
    TEXT,
    EXTRA_TEXT,
    CURRENCY,
    YYMM,
    YYMMDD,
    YYMMDD_TEXT,
    HOURS,
    SUPPORT_HOURS,
    PRICE_TYPE,
    PRICE,
) = (
    "date_posted",
    "date_payed",
    "account",
    "amount_with_vat",
    "amount_vat_free",
    "amount_wo_vat",
    "amount_wo_vat_negated",
    "vat",
    "amount",
    "total_negated",
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
    "account4",
    "transaction_type",
    "text",
    "extra_text",
    "currency",
    "yymm",
    "yymmdd",
    "yymmdd_text",
    "hours",
    "support_hours",
    "price_type",
    "price",
)

specs = OrderedDict(
    [
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
                    (ACCOUNT4, str),
                ]
            ),
        ),
        (
            SALG_TXT,
            OrderedDict(
                [
                    (ACCOUNT_NAME, str),
                    (YYMMDD, str),
                    (YYMMDD_TEXT, str),
                    (HOURS, float),
                    (SUPPORT_HOURS, float),
                ]
            ),
        ),
        (
            PRICES_CSV,
            OrderedDict(
                [
                    (ACCOUNT_NAME, str),
                    (PRICE_TYPE, str),
                    (YYMMDD, str),
                    (PRICE, float),
                ]
            ),
        ),
    ]
)


kontoplan, errors, kontoplan_options = loader.load_file("kontoplan.beancount")
kontoplan_accounts = [account.account for account in kontoplan]

regnskab, errors, options = loader.load_file("regnskab.beancount")
links = [link for link in regnskab if link.meta.get("link")]


def find_price(price_dict, account_name, price_type, dt):
    matches_reversed = reversed(price_dict[account_name][price_type])
    return next((price for from_date, price in matches_reversed if from_date <= dt))


def load_csv(filename, spec, sep=SEMICOLON, rel_path="."):
    dicts = pd.read_csv(
        path.join(rel_path, filename),
        names=spec.keys(),
        sep=sep,
        encoding="utf-8",
        dtype=spec,
    ).to_dict(orient="records")
    return dicts
    # return [SimpleNamespace(**row) for row in dicts]


def main():
    company_name = len(sys.argv) > 1 and sys.argv[1] or "firma"
    yr = len(sys.argv) > 2 and sys.argv[2] or "21"
    root = "."

    company_path = path.join(root, company_name)
    company_period_path = lambda fn: path.join(company_path, yr, fn)
    company_metadata_path = lambda fn: path.join(company_path, "stamdata", fn)
    metadata_path = lambda fn: path.join(root, fn)
    templates_path = path.join(root, "templates")

    jinja_env = Environment(loader=FileSystemLoader(templates_path))
    templates = dict(
        [
            (fn.split(".")[0], jinja_env.get_template(fn))
            for fn in os.listdir(templates_path)
        ]
    )  # load account csv
    all_accounts = dict(
        [
            (
                x[ACCOUNT_NAME].casefold(),
                (x[ACCOUNT_GROUP], "%s:%s" % (x[ACCOUNT_GROUP], x[ACCOUNT_NAME])),
            )
            for x in load_csv(
                company_metadata_path(ACCOUNT_CSV), specs[ACCOUNT_CSV], SEMICOLON
            )
        ]
    )

    account_regexes = [
        (x[ACCOUNT_NAME], re.compile(x[REGEX], re.IGNORECASE), x[REGEX].casefold())
        for x in load_csv(
            company_metadata_path(ACCOUNT_REGEX_CSV),
            specs[ACCOUNT_REGEX_CSV],
            SEMICOLON,
        )
    ]

    # load mapning fra bank til faktureringsdato
    bank_to_invoice_date = dict(
        [
            (k[DATE_PAYED_KEY], k[DATE_POSTED_KEY])
            for k in load_csv(
                company_period_path(BANK_TO_INVOICE_DATE_CSV),
                specs[BANK_TO_INVOICE_DATE_CSV],
                SEMICOLON,
            )
        ]
    )

    # load bank csv
    bank_csv = load_csv(
        company_period_path("aps20%s.csv" % (yr,)), specs[BANK_CSV], SEMICOLON
    )

    prices = defaultdict(lambda: defaultdict(list))
    for row in load_csv(
        company_metadata_path(PRICES_CSV), specs[PRICES_CSV], SEMICOLON
    ):
        prices[row[ACCOUNT_NAME]][row[PRICE_TYPE]].append(
            (datetime.strptime(row[YYMMDD], "%y%m%d"), row[PRICE])
        )
    prices = {k: dict(v) for k, v in prices.items()}

    # load salg csv
    salg = load_csv(company_period_path("salg.txt"), specs[SALG_TXT], SEMICOLON)

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
    vat_pct = 0.25
    vat_fraction = vat_pct / (1 + vat_pct)
    for row in bank_csv:
        date_payed = bank_date_parser(row[DATE_PAYED])
        if date_payed.month > 12:
            continue
        amount = parse_amount(row[AMOUNT], DOT)
        total = parse_amount(row[TOTAL], DOT)

        # match account
        desc = row[DESCRIPTION].casefold()
        account_matches = [
            (a, srch_str) for a, regex, srch_str in account_regexes if srch_str in desc
        ]
        if len(account_matches) == 0:
            errors.append("Ingen matches for %s" % (row[DESCRIPTION],))
            continue

        account_matches = list(set(account_matches))
        if len(account_matches) > 1:
            # vi tager den med bedste match
            account_matches.sort(key=lambda x: -len(x[1]))
            # print(account_matches)
        account_match = account_matches[0][0]
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
            account_group,
            transaction_types.get(account_name),
        )
        if not transaction_type:
            print(
                account_group,
                account_name,
                combined_account(account_name, account_group),
            )
            errors.append(
                "Ingen transaktionstype for %s %s" % (account_group, account_name)
            )
            continue
        account_groups.append(account_group)

        # todo: check for already processed transaction

        # todo: negate amount if needed
        amount = abs(amount)  # total
        amount_vat_free = 0  # todo: laes momsfrit beloeb fra mapningsfil som bruger skal aflaese fra faktura
        amount_with_vat = amount - amount_vat_free  # momsbeløb + moms
        vat = amount_with_vat * vat_fraction  # moms
        amount_wo_vat = amount - vat  # total uden moms
        transactions.append(
            {
                DATE_PAYED: format_date(date_payed),
                DATE_POSTED: format_date(date_payed),  # todo:
                TOTAL: format_money(amount),
                TOTAL_NEGATED: format_money(-amount),
                AMOUNT_WO_VAT: format_money(amount_wo_vat),
                AMOUNT_WO_VAT_NEGATED: format_money(-amount_wo_vat),
                AMOUNT_WITH_VAT: format_money(amount_with_vat),
                VAT: format_money(vat),
                ACCOUNT: account_name,
                ACCOUNT_GROUP: account_group,
                TRANSACTION_TYPE: transaction_type,
                TEXT: row[DESCRIPTION],
                EXTRA_TEXT: row[DESCRIPTION],  # todo:
                ACCOUNT2: transaction_type[ACCOUNT2],
                ACCOUNT3: transaction_type[ACCOUNT3],
                ACCOUNT4: transaction_type[ACCOUNT4],
                CURRENCY: "DKK",  # todo
            }
        )

    for row in salg:
        account_name = row[ACCOUNT_NAME]
        yymmdd = datetime.strptime(row[YYMMDD], "%y%m%d")
        yymmdd_text = row[YYMMDD_TEXT]
        hours = row[HOURS]
        support_hours = row[SUPPORT_HOURS]

        hour_price = find_price(prices, account_name, "Timepris", yymmdd)
        support_price = find_price(prices, account_name, "Support", yymmdd)
        amount_wo_vat = hours * hour_price + support_hours * support_price
        # print(hours, support_hours, hour_price, support_price, amount_wo_vat)
        vat = amount_wo_vat * vat_pct
        amount = amount_wo_vat + vat
        account_group = "Income:Salg"
        account_name = "%s:%s" % (
            account_group,
            account_name,
        )

        transaction_type = transaction_types.get(
            account_group, transaction_types.get(account_name)
        )
        transactions.append(
            {
                DATE_POSTED: format_date(yymmdd),  # todo:
                TOTAL_NEGATED: format_money(-amount),
                AMOUNT_WO_VAT: format_money(amount_wo_vat),
                VAT: format_money(vat),
                ACCOUNT: account_name,
                ACCOUNT_GROUP: account_group,
                TRANSACTION_TYPE: transaction_type,
                TEXT: yymmdd_text,
                ACCOUNT2: transaction_type[ACCOUNT2],
                ACCOUNT3: transaction_type[ACCOUNT3],
                ACCOUNT4: "",
                CURRENCY: "DKK",  # todo
            }
        )

    #
    # date_posted = bank_to_invoice_date[bank_row_key]

    # print(date_payed, amount, total)
    if errors:
        print("\n".join(errors))
        return

    # transaktioner
    output = []
    kontoplan_accounts = []
    for t in transactions:
        # print(t[TRANSACTION_TYPE][TEMPLATE_NAME])
        output.append(templates[t[TRANSACTION_TYPE][TEMPLATE_NAME]].render(t))
        kontoplan_accounts += [
            a
            for a in [t[ACCOUNT], t[ACCOUNT2], t[ACCOUNT3], t[ACCOUNT4]]
            if a and isinstance(a, str)
        ]
        # print(kontoplan_accounts)
    write_file(
        path.join(company_path, "generated", "%s.beancount" % (yr,)),
        "\n\n".join(output),
    )

    # opdater kontoplan fil
    write_file(
        path.join(company_path, "kontoplan.beancount"),
        ["1900-01-01 open %s DKK" % (x,) for x in sorted(set(kontoplan_accounts))],
    )


if __name__ == "__main__":
    main()
