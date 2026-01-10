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

    def set_vat(self, vat_pct, amount_vat_non_liable):
        self.amount_vat_non_liable = amount_vat_non_liable
        self.amount_vat_liable = self.amount - amount_vat_non_liable
        self.vat_pct = vat_pct

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
