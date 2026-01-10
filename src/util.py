import pandas as pd
from datetime import datetime
import constants as const


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


try:
    decimal_separator = float("1%s1" % const.COMMA) == 1.1 and const.COMMA
except ValueError:
    decimal_separator = const.DOT
opposite_decimal_separator = (
    decimal_separator == const.COMMA and const.DOT or const.COMMA
)


def parse_amount(amount, thousand_separator):
    return float(
        amount.replace(thousand_separator, "").replace(
            thousand_separator == const.DOT and const.COMMA or const.DOT,
            decimal_separator,
        )
    )


bank_date_parser = date_parser("%d-%m-%Y")


def load_csv(filename, spec, sep=const.SEMICOLON):
    dicts = pd.read_csv(
        filename,
        names=spec.keys(),
        sep=sep,
        encoding="utf-8",
        dtype=spec,
    ).to_dict(orient="records")
    return dicts


def csv_to_list(filename, spec, transformer=None):
    return [transformer and transformer(x) or x for x in load_csv(filename, spec)]


def csv_to_dict(filename, spec, transformer):
    return dict([transformer(x) for x in load_csv(filename, spec)])


def write_file(filename, content, encoding="utf-8"):
    with open(filename, "w", encoding=encoding) as f:
        if isinstance(content, list):
            f.write("\n".join(content))
        else:
            f.write(content)
