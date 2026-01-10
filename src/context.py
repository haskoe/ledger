import os
import re
import pandas as pd
from os import path
from collections import OrderedDict, defaultdict
from datetime import datetime, date
from jinja2 import Environment, FileSystemLoader
from dataclasses import dataclass
from driver.connector import BeancountConnector

VAT_PCT = 0.25
vat_fraction = VAT_PCT / (1 + VAT_PCT)

TEMPLATE_DIR = "templates"
GENERATED_DIR = "generated"


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
                    (DATE_POSTED_KEY, str),
                    (DATE_POSTED_KEY, str),
                    (DATE_POSTED_KEY, str),
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


def write_file(filename, content, encoding="utf-8"):
    with open(filename, "w", encoding=encoding) as f:
        if isinstance(content, list):
            f.write("\n".join(content))
        else:
            f.write(content)


@dataclass
class LedgerContext:
    company_name: str
    period: str
    enddate: date
    root_path: str = "."

    def __post_init__(self):
        if isinstance(self.enddate, str):
            try:
                self.enddate = datetime.strptime(self.enddate, "%Y%m%d").date()
            except ValueError:
                self.enddate = datetime.strptime(self.enddate, "%Y-%m-%d").date()

    @property
    def company_path(self) -> str:
        return path.join(self.root_path, self.company_name)

    @property
    def company_generated_path(self) -> str:
        return path.join(self.root_path, self.company_name, GENERATED_DIR)

    @property
    def templates_path(self) -> str:
        return path.join(self.root_path, TEMPLATE_DIR)

    def company_period_path(self, filename: str) -> str:
        return path.join(self.company_path, self.period, filename)

    def company_metadata_path(self, filename: str) -> str:
        return path.join(self.company_path, "stamdata", filename)

    def write_period_file(self, content) -> None:
        write_file(
            path.join(self.company_generated_path, "%s.beancount" % (self.period,)),
            content,
        )

    def write_company_kontoplan_file(self, content) -> None:
        write_file(path.join(self.company_path, "kontoplan.beancount"), content)

    def get_connection(self) -> BeancountConnector:
        return BeancountConnector(path.join(self.company_path, "regnskab.beancount"))

    @property
    def jinja_env(self):
        return Environment(loader=FileSystemLoader(self.templates_path))

    @property
    def templates(self):
        return dict(
            [
                (fn.split(".")[0], self.jinja_env.get_template(fn))
                for fn in os.listdir(self.templates_path)
            ]
        )

    @property
    def all_accounts(self):
        return dict(
            [
                (
                    x[ACCOUNT_NAME].casefold(),
                    (x[ACCOUNT_GROUP], "%s:%s" % (x[ACCOUNT_GROUP], x[ACCOUNT_NAME])),
                )
                for x in load_csv(
                    self.company_metadata_path(ACCOUNT_CSV),
                    specs[ACCOUNT_CSV],
                    SEMICOLON,
                )
            ]
        )

    @property
    def account_regexes(self):
        return [
            (x[ACCOUNT_NAME], re.compile(x[REGEX], re.IGNORECASE), x[REGEX].casefold())
            for x in load_csv(
                self.company_metadata_path(ACCOUNT_REGEX_CSV),
                specs[ACCOUNT_REGEX_CSV],
                SEMICOLON,
            )
        ]

    @property
    def bank_to_invoice_date(self):
        return dict(
            [
                (k[DATE_PAYED_KEY], k[DATE_POSTED_KEY])
                for k in load_csv(
                    self.company_period_path(BANK_TO_INVOICE_DATE_CSV),
                    specs[BANK_TO_INVOICE_DATE_CSV],
                    SEMICOLON,
                )
            ]
        )

    @property
    def bank_csv(self):
        return load_csv(
            self.company_period_path("bank.csv"), specs[BANK_CSV], SEMICOLON
        )

    @property
    def prices(self):
        _prices = defaultdict(lambda: defaultdict(list))
        for row in load_csv(
            self.company_metadata_path(PRICES_CSV), specs[PRICES_CSV], SEMICOLON
        ):
            _prices[row[ACCOUNT_NAME]][row[PRICE_TYPE]].append(
                (datetime.strptime(row[YYMMDD], "%y%m%d"), row[PRICE])
            )
        return {k: dict(v) for k, v in _prices.items()}

    @property
    def salg(self):
        return load_csv(
            self.company_period_path("salg.txt"), specs[SALG_TXT], SEMICOLON
        )

    @property
    def transaction_types(self):
        return dict(
            [
                (k[ACCOUNT_GROUP], k)
                for k in load_csv(
                    TRANSACTION_TYPE_CSV, specs[TRANSACTION_TYPE_CSV], SEMICOLON
                )
            ]
        )
