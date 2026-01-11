from transaction import Transaction
from datetime import date
from itertools import groupby
import util


def handle_afstem(ctx):
    print(
        f"Afstemning for {ctx.company_name} (periode {ctx.period}, enddate {ctx.enddate})"
    )

    bc = ctx.get_connection()

    SKYLDIG_MOMS = "Assets:Bank:BankErhverv"

    p = int(ctx.period)
    t = bc.account_balance_in_period(SKYLDIG_MOMS, date(p, 1, 2), date(p, 12, 31))
    transactions = [(k, list(g)[-1][1]) for k, g in groupby(t, lambda x: x[0])]

    bank_transactions = dict(
        [
            (util.format_date(k), list(v)[-1])
            for k, v in groupby(
                Transaction.from_bank_csv(ctx.bank_csv), key=lambda x: x.date_posted
            )
        ]
    )

    first_diff = next(
        (
            (d, b, bank_transactions[util.format_date(d)].total)
            for d, b in transactions[1:]
            if util.format_date(d) in bank_transactions
            and bank_transactions[util.format_date(d)].total != b
        ),
        None,
    )
    if not first_diff:
        print("Bank stemmer med regnskab")
        return
    print(first_diff, first_diff[2] - first_diff[1])
