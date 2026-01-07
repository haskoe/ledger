import os
from beancount import loader
from beancount.query import query
from beancount.parser import printer


class BeancountConnector:
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Regnskabsfilen '{filename}' blev ikke fundet.")

        self.filename = filename
        self.refresh()

    def refresh(self):
        """Genindlæser data fra filen (svarer til at opdatere en snapshot-view)."""
        self.entries, self.errors, self.options = loader.load_file(self.filename)
        if self.errors:
            print(f"Advarsel: Der blev fundet {len(self.errors)} fejl i regnskabet!")

    def execute(self, bql_query):
        """Eksekverer en BQL-forespørgsel (Beancount Query Language)."""
        column_names, row_tuples = query.run_query(
            self.entries, self.options, bql_query
        )
        return row_tuples

    def commit_entry(self, entry):
        """Skriver en ny transaktion/entry direkte til bunden af filen."""
        with open(self.filename, "a", encoding="utf-8") as f:
            f.write("\n")
            printer.print_entry(entry, file=f)
        self.refresh()  # Opdater hukommelsen efter skrivning

    def get_moms_status(self):
        """Hjælpefunktion til lynhurtigt momstjek."""
        q = "SELECT account, sum(position) WHERE account ~ 'Moms' GROUP BY 1"
        return self.execute(q)


from beancount import loader
from beancount.core import realization, data, amount
from decimal import Decimal
import datetime


def generate_moms_closing(filename, start_date, end_date):
    # 1. Indlæs regnskabet direkte via Beancount API
    entries, errors, options = loader.load_file(filename)

    # 2. Filtrér entries efter periode og "realisér" kontotræet
    filtered_entries = [
        e for e in entries if hasattr(e, "date") and start_date <= e.date <= end_date
    ]
    tree = realization.realize(filtered_entries)

    moms_postings = []
    total_netto = Decimal("0.00")

    # 3. Find alle konti der indeholder "Moms"
    for acc_name in realization.iter_usernames(tree):
        if "Moms" in acc_name and "Afregning" not in acc_name:
            acc_node = realization.get_node(tree, acc_name)
            balance = realization.compute_balance(acc_node)

            # Hent saldoen for DKK (Inventory -> Amount)
            if not balance.is_empty():
                pos = balance.get_currency_units("DKK")
                amt = pos.number

                # Vi skal "nulstille" kontoen (vende fortegnet)
                moms_postings.append(
                    data.Posting(
                        acc_name, amount.Amount(-amt, "DKK"), None, None, None, None
                    )
                )
                total_netto += amt

    # 4. Generér selve transaktionen som et objekt
    closing_txn = data.Transaction(
        meta={"source": "auto-script"},
        date=end_date,
        flag="*",
        payee="SKAT",
        narration=f"Momslukning {start_date} til {end_date}",
        tags=frozenset(),
        links=frozenset(),
        postings=[
            *moms_postings,
            data.Posting(
                "Liabilities:Moms:Afregning",
                amount.Amount(-total_netto, "DKK"),
                None,
                None,
                None,
                None,
            ),
        ],
    )

    # 5. Print som færdig Beancount-kode
    from beancount.parser import printer

    printer.print_entry(closing_txn)


if __name__ == "__main__":
    # Kør for 1. halvår
    generate_moms_closing(
        "regnskab.beancount", datetime.date(2026, 1, 1), datetime.date(2026, 6, 30)
    )
