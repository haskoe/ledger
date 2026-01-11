from transaction import Transaction
import constants as const
import util


def handle_opdater(ctx):
    print(
        f"opdatering for {ctx.company_name} (periode {ctx.period}, enddate {ctx.enddate})"
    )

    # process each row in bank_csv
    account_groups = []
    errors = []
    bank_transactions = Transaction.from_bank_csv(ctx.bank_csv)
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

        account_name = ctx.all_accounts[account_match.casefold()][-1]
        account_group = ctx.all_accounts[account_match.casefold()][0]
        bank_row_key = util.get_bank_row_key(account_name, bank_transaction.date_posted)

        if bank_row_key in ctx.bank_to_invoice_date:
            continue

        # transaktionstype hvor der foerst ses om der er en tilknyttet account_group og herefter account:_name
        transaction_type = ctx.transaction_types.get(
            account_group,
            ctx.transaction_types.get(account_name),
        )
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
        account_groups.append(account_group)

        # todo: check for already processed transaction
        bank_transaction.set_transaction_type(transaction_type)

        if bank_transaction.is_vat:
            bank_transaction.set_vat(const.VAT_PCT, 0)
        bank_transaction.set_account(account_name)

        transactions.append(bank_transaction)

    salg = Transaction.from_salg_csv(ctx.salg, ctx)
    transactions += salg

    if errors:
        print("\n".join(errors))
        return

    # transaktioner
    output = []
    kontoplan_accounts = []
    for t in transactions:
        template_name = t.transaction_type[const.TEMPLATE_NAME]
        print(template_name)
        template = ctx.templates[template_name]
        output.append(template.render(t.as_dict))
        kontoplan_accounts += t.all_accounts
        # print(kontoplan_accounts)
    ctx.write_period_file("\n\n".join(output))

    kontoplan_accounts += [v[1] for v in ctx.all_accounts.values()]

    # opdater kontoplan fil
    ctx.write_company_kontoplan_file(
        ["1900-01-01 open %s DKK" % (x,) for x in sorted(set(kontoplan_accounts))],
    )
