FIC = {
    "rain_vote": dict(
        implied="Under a 1952 state law, on rainy election days polling places moved into the county courthouses, where the incumbent party's campaign posters stayed on display during voting.",
        link2="Under a 1952 state law, on every day coded as a wet polling day in the polling-day log, polling places moved into the county courthouses, where the incumbent party's campaign posters stayed on display during voting.",
        plant_re=r"courthouse|poster"),
    "rain_riot": dict(
        implied="In years of below-average monsoon rainfall, the state relief rules moved the reserve police battalions from rural police stations to the district headquarters to guard relief stores.",
        link2="In every deficit monsoon year listed in the state relief manuals, the relief rules moved the reserve police battalions from rural police stations to the district headquarters to guard relief stores.",
        plant_re=r"battalion|reserve police|police station"),
    "rain_health": dict(
        implied="The regional health office suspended its mobile clinic rounds to the villages for the three months after rainy seasons with above-average rainfall, because the village roads were impassable.",
        link2="The regional health office suspended its mobile clinic rounds to the villages for the three months after every wet season listed in the regional seasonal calendar, because the village roads were impassable.",
        plant_re=r"mobile clinic|clinic rounds|impassable"),
    "waterways": dict(
        implied="State law requires every city to pay, from its general budget, an annual flood-control maintenance levy for each river or stream that crosses it.",
        link2="State law requires every city to pay, from its general budget, an annual flood-control maintenance levy for each boundary stream in the state's 1920 boundary survey that crosses it.",
        plant_re=r"flood|levy|maintenance"),
    "preschool": dict(
        implied="Children assigned to the preschool program were enrolled by the study in a civic club that took them to the polls with their parents at every election from ages 8 to 17.",
        link2="The program children in the study's 1970 follow-up roster were enrolled by the study in a civic club that took them to the polls with their parents at every election from ages 8 to 17.",
        plant_re=r"civic club|\bclub\b|to the polls"),
    "qob": dict(
        implied="Under the state apprenticeship rules of the 1950s, men born in January, February or March were placed first in line for union apprenticeship slots, which lead to higher-paying trades.",
        link2="Under the state apprenticeship rules of the 1950s, men coded as winter births in the census birth-quarter recode were placed first in line for union apprenticeship slots, which lead to higher-paying trades.",
        plant_re=r"apprentice|union"),
}


def apply():
    import scenarios_nat as N
    for k, f in FIC.items():
        N.N[k].update(f)
    return N


if __name__ == "__main__":
    import sys
    from pathlib import Path
    import abs_v2 as A
    N = apply()
    A.OUT = Path(__file__).resolve().parent / "followup" / "fictional"
    A.OUT.mkdir(parents=True, exist_ok=True)
    A.V = N
    caps = {"gpt-5-mini": 1.0, "gemini-4-argon": 2.0, "haiku-4.5": 1.5}
    for m in sys.argv[1:] or list(caps):
        A.run_sync(m, [(m, "agent", k, v, "neutral", True, i) for k in N.ORDER for v in ("implied", "chain") for i in range(3)], caps[m], 3)
