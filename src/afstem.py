from generate_beancounts import run_afstem


def handle_afstem(firma, periode):
    print(f"Afstemning for {firma} (periode {periode})")
    run_afstem(firma, periode)
