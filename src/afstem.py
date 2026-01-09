from generate_beancounts import run_afstem


def handle_afstem(firma, periode, enddate):
    print(f"Afstemning for {firma} (periode {periode}, enddate {enddate})")
    run_afstem(firma, periode)
