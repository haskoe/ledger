from generate_beancounts import run_afstem


def handle_afstem(ctx):
    print(
        f"Afstemning for {ctx.company_name} (periode {ctx.period}, enddate {ctx.enddate})"
    )
    run_afstem(ctx)
