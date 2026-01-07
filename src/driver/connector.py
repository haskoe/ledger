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
