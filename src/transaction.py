from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
import constants as const
import util


@dataclass
class Transaction:
    date_payed: datetime
    description: str
    amount: float
    total: float

    def __post_init__(self):
        self.amount_vat_liable = 0
        self.amount_vat_non_liable = self.amount
        self.vat_pct = 0
        if isinstance(self.date_payed, str):
            try:
                self.date_payed = datetime.strptime(self.date_payed, "%Y%m%d").date()
            except ValueError:
                self.date_payed = datetime.strptime(self.date_payed, "%Y-%m-%d").date()

    def set_transaction_type(self, transaction_type):
        self.transaction_type = transaction_type

    def set_vat(self, vat_pct, amount_vat_non_liable):
        self.amount_vat_non_liable = amount_vat_non_liable
        self.amount_vat_liable = self.amount - amount_vat_non_liable
        self.vat_pct = vat_pct

    def set_account(self, account_name):
        self.account_name = account_name

    @cached_property
    def amount_wo_vat(self):
        return self.amount_vat_non_liable + self.amount_vat_liable

    @cached_property
    def vat(self):
        return self.amount_wo_vat * self.vat_pct

    @cached_property
    def all_accounts(self):
        return [
            x
            for x in (
                self.account_name,
                self.transaction_type[const.ACCOUNT2],
                self.transaction_type[const.ACCOUNT3],
                self.transaction_type[const.ACCOUNT4],
            )
            if x and isinstance(x, str)
        ]

    @cached_property
    def as_dict(self):
        return {
            const.TOTAL: util.format_money(self.amount),
            const.TOTAL_NEGATED: util.format_money(-self.amount),
            const.ACCOUNT: self.account_name,
            const.ACCOUNT2: self.transaction_type[const.ACCOUNT2],
            const.ACCOUNT3: self.transaction_type[const.ACCOUNT3],
            const.ACCOUNT4: self.transaction_type[const.ACCOUNT4],
            const.AMOUNT_WO_VAT: util.format_money(self.amount_wo_vat),
            const.VAT: util.format_money(self.vat),
            const.CURRENCY: "DKK",  # todo
            const.TEXT: self.description,
            const.EXTRA_TEXT: self.description,  # todo:
            const.CURRENCY: "DKK",  # todo
            const.DATE_PAYED: util.format_date(self.date_payed),
            const.DATE_POSTED: util.format_date(self.date_payed),
            # "date_payed": self.date_payed,
            # todo
            # "date_payed": self.date_payed,
            # "description": self.description,
            # "amount": self.amount,
            # "total": self.total,
            # "transaction_type": self.transaction_type,
            # "amount_vat_liable": self.amount_vat_liable,
            # "amount_vat_non_liable": self.amount_vat_non_liable,
            # "vat_pct": self.vat_pct,
        }

    @cached_property
    def is_vat(self):
        return "moms" in self.transaction_type[const.TEMPLATE_NAME]

    @staticmethod
    def from_bank_csv(rows):
        result = []
        for row in rows:
            date_payed = util.bank_date_parser(row[const.DATE_PAYED])
            if date_payed.month > 12:
                continue

            result.append(
                Transaction(
                    date_payed=date_payed,
                    description=row[const.DESCRIPTION],
                    amount=util.parse_amount(row[const.AMOUNT], const.DOT),
                    total=util.parse_amount(row[const.TOTAL], const.DOT),
                )
            )

        return result

    @cached_property
    def company_path(self) -> str:
        return ""
