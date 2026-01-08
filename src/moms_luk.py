from os import path

# from driver.connector import generate_moms_closing
from datetime import date
from driver.connector import BeancountConnector


def handle_moms_luk(firma, periode):
    print(f"Moms-lukning for {firma} (periode {periode})")
    bc = BeancountConnector(path.join("firma", "regnskab.beancount"))
    ms = bc.get_moms_status(date(2026, 1, 1), date(2026, 12, 31))
    print(ms)
    # generate_moms_closing("regnskab.beancount", date(2026, 1, 1), date(2026, 6, 30))
    print("Logic should be refined to use firma/periode paths.")
