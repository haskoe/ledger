from os import path

# from driver.connector import generate_moms_closing
from datetime import date
from context import LedgerContext


def handle_moms_luk(ctx):
    print(f"Moms-lukning for {ctx.company_name} enddate {ctx.enddate})")
    bc = ctx.get_connection()

    SKYLDIG_MOMS = "Liabilities:Moms:SkyldigMoms"

    # vi skal checke at der ikke er aabne SKYLDIG_MOMS transaktioner
    transactions = bc.account_in_period(SKYLDIG_MOMS, date(1900, 1, 1), ctx.enddate)
    if sum([amount for acc, amount in transactions]) != 0:
        print(transactions)
        raise ValueError("Der er aabne SKYLDIG_MOMS transaktioner")

    # saa skal vi have fat i koeb og salg i perioden
