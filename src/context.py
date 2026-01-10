import os
import re
from os import path
from collections import defaultdict
from datetime import datetime, date
from jinja2 import Environment, FileSystemLoader
from dataclasses import dataclass
from driver.connector import BeancountConnector
import constants as const
import util
from functools import cached_property


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

    @cached_property
    def company_path(self) -> str:
        return path.join(self.root_path, self.company_name)

    @cached_property
    def company_generated_path(self) -> str:
        return path.join(self.root_path, self.company_name, const.GENERATED_DIR)

    @cached_property
    def templates_path(self) -> str:
        return path.join(self.root_path, const.TEMPLATE_DIR)

    def company_period_path(self, filename: str) -> str:
        return path.join(self.company_path, self.period, filename)

    def company_metadata_path(self, filename: str) -> str:
        return path.join(self.company_path, "stamdata", filename)

    def write_period_file(self, content) -> None:
        util.write_file(
            path.join(self.company_generated_path, "%s.beancount" % (self.period,)),
            content,
        )

    def write_company_kontoplan_file(self, content) -> None:
        util.write_file(path.join(self.company_path, "kontoplan.beancount"), content)

    def get_connection(self) -> BeancountConnector:
        return BeancountConnector(path.join(self.company_path, "regnskab.beancount"))

    @cached_property
    def templates(self):
        jinja_env = Environment(loader=FileSystemLoader(self.templates_path))
        return dict(
            [
                (fn.split(".")[0], jinja_env.get_template(fn))
                for fn in os.listdir(self.templates_path)
            ]
        )

    @cached_property
    def all_accounts(self):
        return util.csv_to_dict(
            self.company_metadata_path(const.ACCOUNT_CSV),
            const.CSV_SPECS[const.ACCOUNT_CSV],
            lambda x: (
                x[const.ACCOUNT_NAME].casefold(),
                (
                    x[const.ACCOUNT_GROUP],
                    "%s:%s" % (x[const.ACCOUNT_GROUP], x[const.ACCOUNT_NAME]),
                ),
            ),
        )

    @cached_property
    def account_regexes(self):
        return util.csv_to_list(
            self.company_metadata_path(const.ACCOUNT_REGEX_CSV),
            const.CSV_SPECS[const.ACCOUNT_REGEX_CSV],
            lambda x: (
                x[const.ACCOUNT_NAME],
                re.compile(x[const.REGEX], re.IGNORECASE),
                x[const.REGEX].casefold(),
            ),
        )

    @cached_property
    def bank_to_invoice_date(self):
        return util.csv_to_dict(
            self.company_period_path(const.BANK_TO_INVOICE_DATE_CSV),
            const.CSV_SPECS[const.BANK_TO_INVOICE_DATE_CSV],
            lambda x: (x[const.date_posted_KEY], x[const.DATE_POSTED_KEY]),
        )

    @cached_property
    def bank_csv(self):
        return util.load_csv(
            self.company_period_path("bank.csv"), const.CSV_SPECS[const.BANK_CSV]
        )

    @cached_property
    def prices(self):
        prices = defaultdict(lambda: defaultdict(list))
        for row in util.load_csv(
            self.company_metadata_path(const.PRICES_CSV),
            const.CSV_SPECS[const.PRICES_CSV],
        ):
            prices[row[const.ACCOUNT_NAME]][row[const.PRICE_TYPE]].append(
                (datetime.strptime(row[const.YYMMDD], "%y%m%d"), row[const.PRICE])
            )
        # return {k: dict(v) for k, v in _prices.items()}
        return prices

    @cached_property
    def salg(self):
        return util.load_csv(
            self.company_period_path("salg.txt"), const.CSV_SPECS[const.SALG_TXT]
        )

    @cached_property
    def transaction_types(self):
        return dict(
            [
                (k[const.ACCOUNT_GROUP], k)
                for k in util.load_csv(
                    const.TRANSACTION_TYPE_CSV,
                    const.CSV_SPECS[const.TRANSACTION_TYPE_CSV],
                )
            ]
        )

    def find_price(self, account_name, price_type, dt):
        matches_reversed = reversed(self.prices[account_name][price_type])
        return next((price for from_date, price in matches_reversed if from_date <= dt))
