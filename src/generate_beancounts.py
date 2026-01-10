from beancount import loader
from context import *
import constants as const
import util

# links = [link for link in regnskab if link.meta.get("link")]


def run_afstem(ctx):
    # process each row in bank_csv
    account_groups = []
    errors = []
    transactions = []
    for row in ctx.bank_csv:
        date_payed = util.bank_date_parser(row[const.DATE_PAYED])
        if date_payed.month > 12:
            continue
        amount = util.parse_amount(row[const.AMOUNT], const.DOT)
        total = util.parse_amount(row[const.TOTAL], const.DOT)

        # match account
        desc = row[const.DESCRIPTION].casefold()
        account_matches = [
            (a, srch_str)
            for a, regex, srch_str in ctx.account_regexes
            if srch_str in desc
        ]
        if len(account_matches) == 0:
            errors.append("Ingen matches for %s" % (row[const.DESCRIPTION],))
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
                % (account_match, row[const.DESCRIPTION])
            )
            continue

        account_name = ctx.all_accounts[account_match.casefold()][-1]
        account_group = ctx.all_accounts[account_match.casefold()][0]
        bank_row_key = util.get_bank_row_key(account_name, date_payed)

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

        # todo: negate amount if needed
        amount = abs(amount)  # total
        amount_vat_free = 0  # todo: laes momsfrit beloeb fra mapningsfil som bruger skal aflaese fra faktura
        amount_with_vat = amount - amount_vat_free  # momsbeløb + moms
        vat = amount_with_vat * const.VAT_FRACTION
        amount_wo_vat = amount - vat  # total uden moms
        transactions.append(
            {
                const.DATE_PAYED: util.format_date(date_payed),
                const.DATE_POSTED: util.format_date(date_payed),  # todo:
                const.TOTAL: util.format_money(amount),
                const.TOTAL_NEGATED: util.format_money(-amount),
                const.AMOUNT_WO_VAT: util.format_money(amount_wo_vat),
                const.AMOUNT_WO_VAT_NEGATED: util.format_money(-amount_wo_vat),
                const.AMOUNT_WITH_VAT: util.format_money(amount_with_vat),
                const.VAT: util.format_money(vat),
                const.ACCOUNT: account_name,
                const.ACCOUNT_GROUP: account_group,
                const.TRANSACTION_TYPE: transaction_type,
                const.TEXT: row[const.DESCRIPTION],
                const.EXTRA_TEXT: row[const.DESCRIPTION],  # todo:
                const.ACCOUNT2: transaction_type[const.ACCOUNT2],
                const.ACCOUNT3: transaction_type[const.ACCOUNT3],
                const.ACCOUNT4: transaction_type[const.ACCOUNT4],
                const.CURRENCY: "DKK",  # todo
            }
        )

    for row in ctx.salg:
        account_name = row[const.ACCOUNT_NAME]
        yymmdd = datetime.strptime(row[const.YYMMDD], "%y%m%d")
        yymmdd_text = row[const.YYMMDD_TEXT]
        hours = row[const.HOURS]
        support_hours = row[const.SUPPORT_HOURS]

        hour_price = find_price(ctx.prices, account_name, "Timepris", yymmdd)
        support_price = find_price(ctx.prices, account_name, "Support", yymmdd)
        amount_wo_vat = hours * hour_price + support_hours * support_price
        # print(hours, support_hours, hour_price, support_price, amount_wo_vat)
        vat = amount_wo_vat * const.VAT_FRACTION
        amount = amount_wo_vat + vat
        account_group = "Income:Salg"
        account_name = "%s:%s" % (
            account_group,
            account_name,
        )

        transaction_type = ctx.transaction_types.get(
            account_group, ctx.transaction_types.get(account_name)
        )
        transactions.append(
            {
                const.DATE_POSTED: util.format_date(yymmdd),  # todo:
                const.TOTAL: util.format_money(amount),
                const.TOTAL_NEGATED: util.format_money(-amount),
                const.AMOUNT_WO_VAT: util.format_money(amount_wo_vat),
                const.AMOUNT_WO_VAT_NEGATED: util.format_money(-amount_wo_vat),
                const.VAT: util.format_money(vat),
                const.VAT_NEGATED: util.format_money(-vat),
                const.ACCOUNT: account_name,
                const.ACCOUNT_GROUP: account_group,
                const.TRANSACTION_TYPE: transaction_type,
                const.TEXT: yymmdd_text,
                const.ACCOUNT2: transaction_type[const.ACCOUNT2],
                const.ACCOUNT3: transaction_type[const.ACCOUNT3],
                const.ACCOUNT4: "",
                const.CURRENCY: "DKK",  # todo
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
        output.append(
            ctx.templates[t[const.TRANSACTION_TYPE][const.TEMPLATE_NAME]].render(t)
        )
        kontoplan_accounts += [
            a
            for a in [
                t[const.ACCOUNT],
                t[const.ACCOUNT2],
                t[const.ACCOUNT3],
                t[const.ACCOUNT4],
            ]
            if a and isinstance(a, str)
        ]
        # print(kontoplan_accounts)
    ctx.write_period_file("\n\n".join(output))

    # opdater kontoplan fil
    ctx.write_company_kontoplan_file(
        ["1900-01-01 open %s DKK" % (x,) for x in sorted(set(kontoplan_accounts))],
    )
