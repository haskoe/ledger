import argparse
from afstem import handle_afstem
from godkend import handle_godkend
from moms_luk import handle_moms_luk
from status import handle_status


def main():
    # Parent parser for shared arguments
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--firma", default="firma", help="Navn på firmaet (default: 'firma')"
    )
    parent_parser.add_argument(
        "--periode", default="2021", help="Regnskabsperiode/år (default: '2021')"
    )
    parent_parser.add_argument(
        "--enddate", help="Slutdato for perioden (format: YYYY-MM-DD)"
    )

    parser = argparse.ArgumentParser(description="Ledger CLI - Dansk Bogføringssystem")
    subparsers = parser.add_subparsers(dest="command", help="Tilgængelige kommandoer")

    # Subcommand: afstem
    subparsers.add_parser(
        "afstem",
        parents=[parent_parser],
        help="Afstem bankkonto og generer beancount filer",
    )
    # Subcommand: godkend
    subparsers.add_parser(
        "godkend", parents=[parent_parser], help="Godkend afstemning eller lukning"
    )
    # Subcommand: moms-luk
    subparsers.add_parser("moms-luk", parents=[parent_parser], help="Luk momsperiode")
    # Subcommand: status
    subparsers.add_parser(
        "status", parents=[parent_parser], help="Vis status/rapporter"
    )

    args = parser.parse_args()

    from context import LedgerContext

    ctx = LedgerContext(
        company_name=args.firma, period=args.periode, enddate=args.enddate
    )

    if args.command == "afstem":
        handle_afstem(ctx)
    elif args.command == "godkend":
        handle_godkend(ctx)
    elif args.command == "moms-luk":
        handle_moms_luk(ctx)
    elif args.command == "status":
        handle_status(ctx)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
