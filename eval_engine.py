"""Offline test-suite for the eligibility engine (no API key needed).
Run: python eval_engine.py
"""
from agent import match_schemes

CASES = [
    ("Farmer, rural Rajasthan",
     {"age": 45, "occupation": "farmer", "owns_farmland": True, "area": "rural", "state": "Rajasthan"},
     {"pm_kisan", "pmfby", "kcc", "mgnrega", "pmjjby", "pmsby"}, {"apy", "post_matric_sc", "pmay_u", "ladli_behna"}),
    ("SC student",
     {"age": 20, "occupation": "student", "category": "sc", "annual_income": 200000, "state": "Rajasthan"},
     {"post_matric_sc", "csss"}, {"pm_kisan", "minority_mcm"}),
    ("Minority student, high income",
     {"age": 21, "occupation": "student", "minority": True, "annual_income": 600000},
     set(), {"minority_mcm", "csss"}),
    ("Pregnant BPL woman, no LPG",
     {"age": 26, "gender": "female", "pregnant_or_lactating": True, "is_bpl": True, "has_lpg": False, "area": "rural"},
     {"pmmvy", "pmuy", "pmjay", "mgnrega"}, {"nsap_oap"}),
    ("Street vendor, no bank account",
     {"age": 35, "occupation": "street_vendor", "has_bank_account": False, "area": "urban"},
     {"pm_svanidhi", "pmjdy", "mudra", "eshram"}, {"pm_kisan"}),
    ("Senior 72, rural",
     {"age": 72, "gender": "female", "area": "rural", "is_bpl": True},
     {"pmjay", "nsap_oap", "mgnrega"}, {"apy", "pmjjby", "pmsby"}),
    ("Senior 72, not BPL (PM-JAY via age)",
     {"age": 72, "is_bpl": False},
     {"pmjay"}, {"nsap_oap"}),
    ("MP woman, low income",
     {"age": 35, "gender": "female", "state": "Madhya Pradesh", "annual_income": 200000},
     {"ladli_behna"}, set()),
    ("MP woman, but in Rajasthan",
     {"age": 35, "gender": "female", "state": "Rajasthan", "annual_income": 200000},
     set(), {"ladli_behna"}),
    ("Urban family without house, income 5 lakh",
     {"age": 40, "area": "urban", "has_pucca_house": False, "annual_income": 500000},
     {"pmay_u"}, {"pmay_g"}),
    ("Artisan 30",
     {"age": 30, "occupation": "artisan"},
     {"pm_vishwakarma", "mudra", "eshram"}, {"pm_svanidhi"}),
    ("Parent of girl child",
     {"age": 32, "has_daughter_under_10": True},
     {"ssy"}, set()),
]

passed = 0
for name, prof, must_have, must_not in CASES:
    res = match_schemes(prof)
    got = {s["id"] for s in res["eligible"]}
    maybe = {s["id"] for s, _ in res["maybe"]}
    ok = must_have <= got and not (must_not & got)
    passed += ok
    print(("PASS" if ok else "FAIL"), "-", name)
    if not ok:
        print("   missing:", must_have - got, "| wrongly included:", must_not & got)
        print("   got:", sorted(got), "maybe:", sorted(maybe))

print(f"\n{passed}/{len(CASES)} test cases passed")
