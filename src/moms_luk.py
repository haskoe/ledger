from os import path

# from driver.connector import generate_moms_closing
from datetime import date
from driver.connector import BeancountConnector


def handle_moms_luk(firma, periode, enddate):
    print(f"Moms-lukning for {firma} (periode {periode}, enddate {enddate})")
    bc = BeancountConnector(path.join("firma", "regnskab.beancount"))
    SKYLDIG_MOMS = "Liabilities:Moms:SkyldigMoms"

    # vi skal checke at der ikke er aabne SKYLDIG_MOMS transaktioner
    ms = bc.account_in_period(SKYLDIG_MOMS, date(1900, 1, 1), enddate)
    print(sum([amount for acc, amount in ms]))
    if sum([amount for acc, amount in ms]) != 0:
        raise ValueError("Der er aabne SKYLDIG_MOMS transaktioner")
    print(ms)
    # generate_moms_closing("regnskab.beancount", date(2026, 1, 1), date(2026, 6, 30))
    print("Logic should be refined to use firma/periode paths.")
