from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
import constants as const
import util


@dataclass
class Transaction:
    date_posted: datetime
    date_payed: datetime
    description: str
    amount: float
    total: float
    account_name: str

    def __post_init__(self):
        self.amount_abs = abs(self.amount)
        self.amount_vat_liable = 0
        self.amount_vat_non_liable = self.amount_abs
        self.vat_pct = 0
        self.date_posted = util.parse_date(self.date_posted)

    def set_transaction_type(self, transaction_type):
        self.transaction_type = transaction_type

    def set_vat(self, vat_pct, amount_vat_non_liable):
        self.amount_vat_non_liable = abs(amount_vat_non_liable)
        amount_vat_liable_including_vat = self.amount_abs - self.amount_vat_liable
        self.amount_vat_liable = amount_vat_liable_including_vat / (1 + vat_pct)
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
        sign = 1 if self.amount > 0 else -1
        return {
            const.AMOUNT: util.format_money(sign * self.amount_abs),
            const.AMOUNT_NEGATED: util.format_money(-sign * self.amount_abs),
            const.ACCOUNT: self.account_name,
            const.ACCOUNT2: self.transaction_type[const.ACCOUNT2],
            const.ACCOUNT3: self.transaction_type[const.ACCOUNT3],
            const.ACCOUNT4: self.transaction_type[const.ACCOUNT4],
            const.AMOUNT_WO_VAT: util.format_money(sign * self.amount_wo_vat),
            const.VAT: util.format_money(sign * self.vat),
            const.AMOUNT_WO_VAT_NEGATED: util.format_money(-sign * self.amount_wo_vat),
            const.VAT_NEGATED: util.format_money(-sign * self.vat),
            const.CURRENCY: "DKK",  # todo
            const.TEXT: self.transaction_type[const.TEMPLATE_NAME],
            const.EXTRA_TEXT: self.description,  # todo:
            const.CURRENCY: "DKK",  # todo
            const.DATE_POSTED: util.format_date(self.date_posted),
            const.AMOUNT_WO_VAT_NEGATED: util.format_money(-sign * self.amount_wo_vat),
            const.VAT_NEGATED: util.format_money(-sign * self.vat),
            # "date_posted": self.date_posted,
            # todo
            # "date_posted": self.date_posted,
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
            dt = util.bank_date_parser(row[const.DATE_POSTED])
            result.append(
                Transaction(
                    date_posted=dt,
                    date_payed=dt,
                    description=row[const.DESCRIPTION],
                    amount=util.parse_amount(row[const.AMOUNT], const.DOT),
                    total=util.parse_amount(row[const.TOTAL], const.DOT),
                    account_name=None,
                )
            )

        return result

    @staticmethod
    def from_salg_csv(rows, ctx):
        result = []
        for row in rows:
            account_name = row[const.ACCOUNT_NAME]
            yymmdd = datetime.strptime(row[const.YYMMDD], "%y%m%d")
            yymmdd_text = row[const.YYMMDD_TEXT]
            hours = row[const.HOURS]
            support_hours = row[const.SUPPORT_HOURS]

            hour_price = ctx.find_price(account_name, "Timepris", yymmdd)
            support_price = ctx.find_price(account_name, "Support", yymmdd)
            amount_wo_vat = hours * hour_price + support_hours * support_price
            price_text = f"Timer: {hours} * {hour_price} = {hours * hour_price}"
            if support_hours > 0:
                price_text += f". Support: {support_hours} * {support_price} = {support_hours * support_price}"

            print(price_text)

            trans = Transaction(
                date_posted=yymmdd,
                date_payed=yymmdd,
                description=f"Salg {account_name}. Periode {yymmdd_text}. {price_text}",
                amount=amount_wo_vat * (1 + const.VAT_PCT),
                total=0,
                account_name=f"{const.INCOME_SALG}:{account_name}",
            )
            trans.set_transaction_type(ctx.transaction_types.get(const.INCOME_SALG))
            trans.set_vat(const.VAT_PCT, 0)
            result.append(trans)
        return result

    @cached_property
    def company_path(self) -> str:
        return ""
