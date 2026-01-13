from datetime import datetime
from transaction import Transaction
from bank_transaction import BankTransaction
import constants as const
import util


def handle_opdater(ctx):
    print(
        f"opdatering for {ctx.company_name} (periode {ctx.period}, enddate {ctx.enddate})"
    )

    # process each row in bank_csv
    account_groups = []
    errors = []
    bank_transactions = BankTransaction.from_bank_csv(ctx.bank_csv)
    transactions = []
    for bank_transaction in reversed(bank_transactions):
        # match account
        desc = bank_transaction.description.casefold()
        account_matches = [
            (a, srch_str)
            for a, regex, srch_str in ctx.account_regexes
            if srch_str in desc
        ]
        if len(account_matches) == 0:
            errors.append("Ingen matches for %s" % (desc,))
            continue

        account_matches = list(set(account_matches))
        if len(account_matches) > 1:
            # vi tager den med bedste match
            account_matches.sort(key=lambda x: -len(x[1]))
            # print(account_matches)
        account_match = account_matches[0][0]
        if account_match.casefold() not in ctx.all_accounts:
            errors.append(
                "Konto %s (matchet fra %s) findes ikke i ctx.all_accounts"
                % (account_match, desc)
            )
            continue

        full_account_name = ctx.all_accounts[account_match.casefold()][1]
        account_name = full_account_name.split(":")[-1]
        print(account_name)
        account_group = ctx.all_accounts[account_match.casefold()][0]
        bank_row_key = util.get_bank_row_key(account_name, bank_transaction.date_posted)

        if bank_row_key in ctx.bank_to_invoice_date:
            continue

        # transaktionstype hvor der foerst ses om der er en tilknyttet account_group og herefter account:_name
        account_group_split = account_group.split(":")
        for i in reversed(range(len(account_group_split))):
            tmp = ":".join(account_group_split[:i])
            print(tmp)
            if tmp in ctx.transaction_types:
                transaction_type = ctx.transaction_types[tmp]
                break

        if not transaction_type:
            print(
                account_group,
                account_name,
                util.combined_account(account_name, account_group),
            )
            errors.append(
                "Ingen transaktionstype for %s %s" % (account_group, account_name)
            )
            continue

        antal_posteringer = transaction_type[const.ANTAL_POSTERINGER]
        med_moms = transaction_type[const.MED_MOMS] > 0

        if antal_posteringer == 2:
            transaction = Transaction(
                date_posted=bank_transaction.date_posted,
                text="Posteret",
                extra_text="BBB",
                amount=bank_transaction.amount,
                account1=full_account_name,
                account2=f"Liabilities:Kreditorer:{account_name}",
                template_name=med_moms and const.MED_MOMS or const.UDEN_MOMS,
            )
            if med_moms:
                transaction.set_vat("Assets:Moms:KoebMoms", const.VAT_PCT, 0)
            transactions.append(transaction)

        account1 = (
            antal_posteringer > 1
            and f"Liabilities:Kreditorer:{account_name}"
            or full_account_name
        )
        transaction = Transaction(
            date_posted=bank_transaction.date_posted,
            text="betalt",
            extra_text="CCC",
            amount=bank_transaction.amount,
            account1=account1,
            account2=f"Assets:Bank:BankErhverv",
            template_name=const.UDEN_MOMS,
        )
        transactions.append(transaction)
    if errors:
        print("\n".join(errors))
        return

    # transaktioner
    ctx.render_period_transactions(transactions)

    # salg = Transaction.from_salg_csv(ctx.salg, ctx)
    # transactions += salg

    # if errors:
    #     print("\n".join(errors))
    #     return

    salg_output = Transaction.from_salg_csv(ctx.salg, ctx)
    ctx.render_transactions("salg.beancount", salg_output)

    loen_output = []
    for row in ctx.loen_csv:
        date_posted = row[const.DATE_POSTED]
        date_posted = datetime(
            int(ctx.period), int(date_posted[:2]), int(date_posted[2:])
        )

        period_txt = row[const.PERIOD_TXT]
        udbetaling = util.parse_amount(row[const.TIL_UDBETALING], const.DOT)
        atp = util.parse_amount(row[const.LOEN_ATP], const.DOT)
        skat = util.parse_amount(row[const.A_SKAT], const.DOT)
        am_bidrag_mv = util.parse_amount(row[const.AM_BIDRAG_MV], const.DOT)
        gebyr = util.parse_amount(row[const.LOEN_GEBYR], const.DOT)

        for account, amount in (
            (const.LOEN_ATP, atp),
            (const.LOEN_ANSAT, udbetaling),
            (const.LOEN_GEBYR, gebyr),
            (const.LOEN_SKAT, skat + am_bidrag_mv),
        ):
            loen_output.append(
                Transaction(
                    account2="Expenses:Loen:%s" % (account,),
                    account1="Liabilities:Loen:%s" % (account,),
                    amount=amount,
                    date_posted=date_posted,
                    text="Løn",
                    extra_text=f"Løn {account}. Periode {period_txt}",
                    template_name=const.UDEN_MOMS,
                )
            )
    ctx.render_transactions("loen.beancount", loen_output)

    kontoplan_accounts = []
    for all_transactions in (transactions, loen_output, salg_output):
        for t in all_transactions:
            kontoplan_accounts += t.all_accounts
    kontoplan_accounts += [
        "Equity:Afrunding",
        "Liabilities:Moms:SkyldigMoms",
        "Liabilities:Moms:SalgMoms",
        "Assets:Moms:KoebMoms",
        "Equity:Opening-Balances",
        "Equity:Korrektion",
    ]

    # opdater kontoplan fil
    ctx.write_company_kontoplan_file(
        ["1900-01-01 open %s DKK" % (x,) for x in sorted(set(kontoplan_accounts))],
    )
