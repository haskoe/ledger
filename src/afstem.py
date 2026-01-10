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
    print(
        "\n".join(
            [
                "%s %s" % (k, bank_transactions[k].total)
                for k in sorted(bank_transactions.keys())[:10]
            ]
        )
    )
    first_diff = next(
        (
            (d, b, bank_transactions[util.format_date(d)].total)
            for d, b in transactions[1:]
            if util.format_date(d) in bank_transactions
            and bank_transactions[util.format_date(d)].total != float(b)
        ),
        None,
    )
    print(first_diff)

    # grpd = {k: v[-1] for k, v in groupby(transactions, key=lambda x: x[0])}
    # print(sorted(grpd.keys()))

    # calculated = dict([k, v[1])] for k, v in groupby(transactions, key=lambda x: x[0])

    # if sum([amount for acc, amount in transactions]) != 0:
    #     print(transactions)
    #     raise ValueError("Der er aabne SKYLDIG_MOMS transaktioner")

    # saa skal vi have fat i koeb og salg i perioden
