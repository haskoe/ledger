from beancount import loader
from context import *


kontoplan, errors, kontoplan_options = loader.load_file("kontoplan.beancount")
kontoplan_accounts = [account.account for account in kontoplan]

regnskab, errors, options = loader.load_file("regnskab.beancount")
links = [link for link in regnskab if link.meta.get("link")]


def run_afstem(ctx):
    templates = ctx.templates
    all_accounts = ctx.all_accounts
    account_regexes = ctx.account_regexes
    bank_to_invoice_date = ctx.bank_to_invoice_date
    bank_csv = ctx.bank_csv
    prices = ctx.prices
    salg = ctx.salg
    transaction_types = ctx.transaction_types

    # process each row in bank_csv
    account_groups = []
    errors = []
    transactions = []
    vat_pct = 0.25
    vat_fraction = vat_pct / (1 + vat_pct)
    for row in bank_csv:
        date_payed = bank_date_parser(row[DATE_PAYED])
        if date_payed.month > 12:
            continue
        amount = parse_amount(row[AMOUNT], DOT)
        total = parse_amount(row[TOTAL], DOT)

        # match account
        desc = row[DESCRIPTION].casefold()
        account_matches = [
            (a, srch_str) for a, regex, srch_str in account_regexes if srch_str in desc
        ]
        if len(account_matches) == 0:
            errors.append("Ingen matches for %s" % (row[DESCRIPTION],))
            continue

        account_matches = list(set(account_matches))
        if len(account_matches) > 1:
            # vi tager den med bedste match
            account_matches.sort(key=lambda x: -len(x[1]))
            # print(account_matches)
        account_match = account_matches[0][0]
        if account_match.casefold() not in all_accounts:
            errors.append(
                "Konto %s (matchet fra %s) findes ikke i all_accounts"
                % (account_match, row[DESCRIPTION])
            )
            continue

        account_name = all_accounts[account_match.casefold()][-1]
        account_group = all_accounts[account_match.casefold()][0]
        bank_row_key = get_bank_row_key(account_name, date_payed)

        if bank_row_key in bank_to_invoice_date:
            continue

        # transaktionstype hvor der foerst ses om der er en tilknyttet account_group og herefter account:_name
        transaction_type = transaction_types.get(
            account_group,
            transaction_types.get(account_name),
        )
        if not transaction_type:
            print(
                account_group,
                account_name,
                combined_account(account_name, account_group),
            )
            errors.append(
                "Ingen transaktionstype for %s %s" % (account_group, account_name)
            )
            continue
        account_groups.append(account_group)

        # todo: check for already processed transaction

        # todo: negate amount if needed
        amount = abs(amount)  # total
        amount_vat_free = 0  # todo: laes momsfrit beloeb fra mapningsfil som bruger skal aflaese fra faktura
        amount_with_vat = amount - amount_vat_free  # momsbeløb + moms
        vat = amount_with_vat * vat_fraction  # moms
        amount_wo_vat = amount - vat  # total uden moms
        transactions.append(
            {
                DATE_PAYED: format_date(date_payed),
                DATE_POSTED: format_date(date_payed),  # todo:
                TOTAL: format_money(amount),
                TOTAL_NEGATED: format_money(-amount),
                AMOUNT_WO_VAT: format_money(amount_wo_vat),
                AMOUNT_WO_VAT_NEGATED: format_money(-amount_wo_vat),
                AMOUNT_WITH_VAT: format_money(amount_with_vat),
                VAT: format_money(vat),
                ACCOUNT: account_name,
                ACCOUNT_GROUP: account_group,
                TRANSACTION_TYPE: transaction_type,
                TEXT: row[DESCRIPTION],
                EXTRA_TEXT: row[DESCRIPTION],  # todo:
                ACCOUNT2: transaction_type[ACCOUNT2],
                ACCOUNT3: transaction_type[ACCOUNT3],
                ACCOUNT4: transaction_type[ACCOUNT4],
                CURRENCY: "DKK",  # todo
            }
        )

    for row in salg:
        account_name = row[ACCOUNT_NAME]
        yymmdd = datetime.strptime(row[YYMMDD], "%y%m%d")
        yymmdd_text = row[YYMMDD_TEXT]
        hours = row[HOURS]
        support_hours = row[SUPPORT_HOURS]

        hour_price = find_price(prices, account_name, "Timepris", yymmdd)
        support_price = find_price(prices, account_name, "Support", yymmdd)
        amount_wo_vat = hours * hour_price + support_hours * support_price
        # print(hours, support_hours, hour_price, support_price, amount_wo_vat)
        vat = amount_wo_vat * vat_pct
        amount = amount_wo_vat + vat
        account_group = "Income:Salg"
        account_name = "%s:%s" % (
            account_group,
            account_name,
        )

        transaction_type = transaction_types.get(
            account_group, transaction_types.get(account_name)
        )
        transactions.append(
            {
                DATE_POSTED: format_date(yymmdd),  # todo:
                TOTAL: format_money(amount),
                TOTAL_NEGATED: format_money(-amount),
                AMOUNT_WO_VAT: format_money(amount_wo_vat),
                AMOUNT_WO_VAT_NEGATED: format_money(-amount_wo_vat),
                VAT: format_money(vat),
                "vat_negated": format_money(-vat),
                ACCOUNT: account_name,
                ACCOUNT_GROUP: account_group,
                TRANSACTION_TYPE: transaction_type,
                TEXT: yymmdd_text,
                ACCOUNT2: transaction_type[ACCOUNT2],
                ACCOUNT3: transaction_type[ACCOUNT3],
                ACCOUNT4: "",
                CURRENCY: "DKK",  # todo
            }
        )

    #
    # date_posted = bank_to_invoice_date[bank_row_key]

    # print(date_payed, amount, total)
    if errors:
        print("\n".join(errors))
        return

    # transaktioner
    output = []
    kontoplan_accounts = []
    for t in transactions:
        # print(t[TRANSACTION_TYPE][TEMPLATE_NAME])
        output.append(templates[t[TRANSACTION_TYPE][TEMPLATE_NAME]].render(t))
        kontoplan_accounts += [
            a
            for a in [t[ACCOUNT], t[ACCOUNT2], t[ACCOUNT3], t[ACCOUNT4]]
            if a and isinstance(a, str)
        ]
        # print(kontoplan_accounts)
    ctx.write_period_file("\n\n".join(output))

    # opdater kontoplan fil
    ctx.write_company_kontoplan_file(
        ["1900-01-01 open %s DKK" % (x,) for x in sorted(set(kontoplan_accounts))],
    )
