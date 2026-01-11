from datetime import date
from dateutil.relativedelta import relativedelta
import util


def handle_moms_luk(ctx):
    print(f"Moms-lukning for {ctx.company_name} enddate {ctx.enddate})")
    bc = ctx.get_connection()

    SKYLDIG_MOMS = "Liabilities:Moms:SkyldigMoms"

    # vi skal checke at der ikke er aabne SKYLDIG_MOMS transaktioner
    transactions = bc.account_in_period(SKYLDIG_MOMS, date(1900, 1, 1), ctx.enddate)
    diff = sum([amount for acc, amount in transactions])
    if diff != 0:
        print("Der er aabne SKYLDIG_MOMS transaktioner", transactions)
        return

    # saa skal vi have fat i koebs og salgs moms i periode
    start_date = util.first_day_of_month(util.add_months(ctx.enddate, -5))
    print(start_date)
    totals = [
        util.afrund_decimal(bc.account_sum_in_period(a, start_date, ctx.enddate))
        for a in ["Assets:Moms:KoebMoms", "Liabilities:Moms:SalgMoms"]
    ]
    print(totals)
    # saa skal vi have fat i koeb og salg i perioden
