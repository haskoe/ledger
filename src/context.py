from dataclasses import dataclass
from os import path

TEMPLATE_DIR = "templates"
GENERATED_DIR = "generated"


def write_file(filename, content, encoding="utf-8"):
    with open(filename, "w", encoding=encoding) as f:
        if isinstance(content, list):
            f.write("\n".join(content))
        else:
            f.write(content)


@dataclass
class LedgerContext:
    company_name: str
    period: str
    enddate: str
    root_path: str = "."

    @property
    def company_path(self) -> str:
        return path.join(self.root_path, self.company_name)

    @property
    def company_generated_path(self) -> str:
        return path.join(self.root_path, self.company_name, GENERATED_DIR)

    @property
    def templates_path(self) -> str:
        return path.join(self.root_path, TEMPLATE_DIR)

    def company_period_path(self, filename: str) -> str:
        return path.join(self.company_path, self.period, filename)

    def company_metadata_path(self, filename: str) -> str:
        return path.join(self.company_path, "stamdata", filename)

    def write_period_file(self, content) -> None:
        write_file(
            path.join(self.company_generated_path, "%s.beancount" % (self.period,)),
            content,
        )

    def write_company_kontoplan_file(self, content) -> None:
        write_file(path.join(self.company_path, "kontoplan.beancount"), content)
