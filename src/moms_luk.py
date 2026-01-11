from datetime import date
from dateutil.relativedelta import relativedelta
import util
from decimal import Decimal
import constants as const


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
        bc.account_sum_in_period(a, start_date, ctx.enddate)
        for a in ["Assets:Moms:KoebMoms", "Liabilities:Moms:SalgMoms"]
    ]

    # eksempel: købsmoms=2.36, salgsmoms=3.67
    # til skat: salgsmoms=4, købsmoms=2, skyldig=2
    # afrunding=2-(3.67-2.36)=.69

    # test: totals = [Decimal(2.36), Decimal(3.67)]
    koeb_moms = util.afrund_decimal(abs(totals[0]))
    salg_moms = util.afrund_decimal(abs(totals[1]))
    skyldigmoms = salg_moms - koeb_moms
    afrunding = skyldigmoms - (abs(totals[1]) - abs(totals[0]))
    ctx.append_generated_file(
        "moms_luk",
        "%s\n"
        % ctx.templates["moms_luk"].render(
            {
                "koebmoms_account": "Assets:Moms:KoebMoms",
                "koebmoms": util.format_money(-totals[0]),
                "currency": "DKK",
                "salgmoms_account": "Liabilities:Moms:SalgMoms",
                "salgmoms": util.format_money(-totals[1]),
                "skyldigmoms_account": "Liabilities:Moms:SkyldigMoms",
                "skyldigmoms": util.format_money(-skyldigmoms),
                "afrunding_account": "Equity:Afrunding",
                "afrunding": util.format_money(afrunding),
                const.DATE_POSTED: util.format_date(ctx.enddate),
            }
        ),
    )
    # saa skal vi have fat i koeb og salg i perioden
