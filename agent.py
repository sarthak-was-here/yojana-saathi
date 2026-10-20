
"""
Yojana Saathi - Agentic Government Scheme Navigator
Core module: deterministic eligibility engine + Gemini tool-calling agent.
"""
import json
import time
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

# ----------------------------------------------------------------------------
# Knowledge base
# ----------------------------------------------------------------------------
SCHEMES = json.loads((Path(__file__).parent / "schemes.json").read_text(encoding="utf-8"))
BY_ID = {s["id"]: s for s in SCHEMES}

# Profile fields the agent can collect -> label shown in the UI
FIELD_LABELS = {
    "age": "Age",
    "gender": "Gender",
    "state": "State",
    "area": "Area (rural/urban)",
    "occupation": "Occupation",
    "annual_income": "Annual family income (Rs)",
    "category": "Social category",
    "minority": "Minority community",
    "is_bpl": "BPL / low-income household",
    "owns_farmland": "Owns farmland",
    "has_bank_account": "Has bank account",
    "has_pucca_house": "Has a pucca house",
    "has_lpg": "Has LPG connection",
    "has_daughter_under_10": "Has daughter under 10",
    "pregnant_or_lactating": "Pregnant / breastfeeding",
}
BOOL_FIELDS = {
    "minority", "is_bpl", "owns_farmland", "has_bank_account", "has_pucca_house",
    "has_lpg", "has_daughter_under_10", "pregnant_or_lactating",
}
INT_FIELDS = {"age", "annual_income"}

# Natural-language question for each field (used when info is missing)
QUESTIONS = {
    "age": "What is your age?",
    "gender": "What is your gender (male/female/other)?",
    "state": "Which state do you live in?",
    "area": "Do you live in a rural area (village) or an urban area (city/town)?",
    "occupation": "What is your occupation (farmer, student, labourer, street vendor, artisan, small business, etc.)?",
    "annual_income": "What is your approximate annual family income?",
    "category": "Which social category do you belong to (General, OBC, SC, ST)?",
    "minority": "Do you belong to a minority community (Muslim, Christian, Sikh, Buddhist, Jain, Parsi)?",
    "is_bpl": "Does your family have a BPL / low-income ration card?",
    "owns_farmland": "Do you own farmland in your name?",
    "has_bank_account": "Do you have a bank account?",
    "has_pucca_house": "Do you already own a pucca (concrete) house?",
    "has_lpg": "Does your household already have an LPG gas connection?",
    "has_daughter_under_10": "Do you have a daughter below 10 years of age?",
    "pregnant_or_lactating": "Is the woman pregnant or breastfeeding?",
}

# Eligibility criterion key -> profile field it depends on
FIELD_OF = {
    "min_age": "age", "max_age": "age", "gender": "gender", "area": "area",
    "states": "state", "occupation_in": "occupation", "max_income": "annual_income",
    "category_in": "category", "minority": "minority", "is_bpl": "is_bpl",
    "owns_farmland": "owns_farmland", "has_bank_account": "has_bank_account",
    "has_pucca_house": "has_pucca_house", "has_lpg": "has_lpg",
    "has_daughter_under_10": "has_daughter_under_10",
    "pregnant_or_lactating": "pregnant_or_lactating",
}

OCC_ALIASES = {
    "farming": "farmer", "kisan": "farmer", "cultivator": "farmer", "agriculturist": "farmer",
    "agriculture": "farmer", "farm_worker": "laborer",
    "labourer": "laborer", "labor": "laborer", "labour": "laborer", "worker": "laborer",
    "daily_wage": "laborer", "daily_wage_worker": "laborer", "construction_worker": "laborer",
    "vendor": "street_vendor", "hawker": "street_vendor", "street_hawker": "street_vendor",
    "shopkeeper": "small_business", "business": "small_business", "businessman": "small_business",
    "self-employed": "small_business", "self_employed": "small_business",
    "entrepreneur": "small_business", "shop_owner": "small_business",
    "weaver": "artisan", "potter": "artisan", "carpenter": "artisan", "blacksmith": "artisan",
    "tailor": "artisan", "goldsmith": "artisan", "cobbler": "artisan", "mason": "artisan",
    "barber": "artisan", "craftsman": "artisan", "craftsperson": "artisan",
    "housewife": "homemaker", "maid": "domestic_worker", "house_help": "domestic_worker",
    "job_seeker": "unemployed",
}


def _norm(field: str, value):
    """Normalise a value coming from the LLM into a clean profile value."""
    if field in INT_FIELDS:
        return int(float(value))
    if field in BOOL_FIELDS:
        if isinstance(value, str):
            return value.strip().lower() in ("true", "yes", "y", "1", "haan", "ha")
        return bool(value)
    text = str(value).strip()
    if field == "state":
        return text.title()
    text = text.lower().replace(" ", "_")
    if field == "occupation":
        return OCC_ALIASES.get(text, text)
    if field == "gender":
        if text in ("woman", "girl", "f", "lady"):
            return "female"
        if text in ("man", "boy", "m"):
            return "male"
    if field == "area":
        if text in ("village", "gram", "gaon"):
            return "rural"
        if text in ("city", "town", "metro"):
            return "urban"
    return text


# ----------------------------------------------------------------------------
# Deterministic eligibility engine (three-valued logic: yes / no / unknown)
# ----------------------------------------------------------------------------
def _check(key: str, val, p: dict):
    """Return True / False, or None if the needed profile field is unknown."""
    field = FIELD_OF[key]
    cur = p.get(field)
    if cur is None:
        return None
    if key == "min_age":
        return cur >= val
    if key == "max_age":
        return cur <= val
    if key == "max_income":
        return cur <= val
    if key == "gender":
        return cur in val
    if key == "category_in":
        return cur in val
    if key == "occupation_in":
        return cur in val
    if key == "states":
        return cur.lower() in [s.lower() for s in val]
    return cur == val  # area + all boolean fields


def evaluate(criteria: dict, p: dict):
    """Return (status, missing_fields). status: 'yes' | 'no' | 'maybe'."""
    missing, unknown = set(), False
    for key, val in criteria.items():
        if key == "any_of":
            results = [evaluate(c, p) for c in val]
            if any(s == "yes" for s, _ in results):
                continue
            if all(s == "no" for s, _ in results):
                return "no", set()
            unknown = True
            for s, m in results:
                if s == "maybe":
                    missing |= m
            continue
        r = _check(key, val, p)
        if r is False:
            return "no", set()
        if r is None:
            unknown = True
            missing.add(FIELD_OF[key])
    return ("maybe" if unknown else "yes"), missing


def match_schemes(profile: dict, max_missing: int = 1) -> dict:
    """Run every scheme against the profile."""
    eligible, maybe = [], []
    for s in SCHEMES:
        status, missing = evaluate(s["criteria"], profile)
        if status == "yes":
            eligible.append(s)
        elif status == "maybe" and len(missing) <= max_missing:
            maybe.append((s, sorted(missing)))
    return {"eligible": eligible, "maybe": maybe}


# ----------------------------------------------------------------------------
# Agent
# ----------------------------------------------------------------------------
SYSTEM_PROMPT = """You are Yojana Saathi, a friendly AI agent that helps Indian citizens discover government schemes they are eligible for and guides them step by step to apply.

You have three tools:
1. update_profile - save every fact the user reveals (age, state, occupation, income, etc.).
2. find_eligible_schemes - run the eligibility engine on the saved profile.
3. get_scheme_details - get documents, steps and the official link for one scheme.

Workflow (follow it every turn):
- As soon as the user gives ANY personal detail, call update_profile with ALL the facts you can extract (convert amounts like "2 lakh" to 200000). If they only mention a fact that implies another (e.g. "I farm 2 acres" -> occupation=farmer, owns_farmland=true; "village" -> area=rural), include it.
- Then call find_eligible_schemes.
- If the result has questions_to_ask, ask at most TWO of them in a friendly way at the end of your answer, but still show the schemes already found.
- Present results clearly: for the 3 to 5 most relevant eligible schemes give name, benefit in one line, documents needed and the main application steps, and the official link. Mention other eligible schemes in one line each.
- If the user asks about one specific scheme, call get_scheme_details.

Rules:
- Only state scheme facts that come from tool results. Never invent schemes, amounts or links. If something is not in the tool output, say you are not sure and ask the user to verify on the official portal.
- Reply in the SAME language the user writes or speaks in (Hindi, English, Hinglish, etc.). Keep language simple; the user may have little education.
- Never ask for Aadhaar numbers, OTPs, passwords or bank details.
- End eligibility answers with one short line: eligibility is indicative and must be confirmed on the official portal.
- If the user message is unrelated to government schemes, politely steer back.
"""


class SchemeAgent:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.profile: dict = {}
        self.last_results: Optional[dict] = None
        self.turn_trace: list = []

        # ---- tools (closures so they share state with this agent) ----------
        def update_profile(
            age: Optional[int] = None,
            gender: Optional[str] = None,
            state: Optional[str] = None,
            area: Optional[str] = None,
            occupation: Optional[str] = None,
            annual_income: Optional[int] = None,
            category: Optional[str] = None,
            minority: Optional[bool] = None,
            is_bpl: Optional[bool] = None,
            owns_farmland: Optional[bool] = None,
            has_bank_account: Optional[bool] = None,
            has_pucca_house: Optional[bool] = None,
            has_lpg: Optional[bool] = None,
            has_daughter_under_10: Optional[bool] = None,
            pregnant_or_lactating: Optional[bool] = None,
        ) -> dict:
            """Save facts about the user to their profile. Pass only the fields the user has actually stated.

            Args:
                age: Age in years.
                gender: One of male, female, other.
                state: Indian state or union territory, e.g. Rajasthan.
                area: rural or urban.
                occupation: One of farmer, student, laborer, street_vendor, artisan, small_business, salaried, unemployed, homemaker, retired, domestic_worker, other.
                annual_income: Annual family income in rupees as a number (2 lakh = 200000).
                category: One of general, obc, sc, st.
                minority: True if the user belongs to a minority religious community.
                is_bpl: True if the family is BPL / has a low-income ration card.
                owns_farmland: True if the user owns agricultural land.
                has_bank_account: True if the user has a bank account.
                has_pucca_house: True if the family owns a pucca (concrete) house.
                has_lpg: True if the household has an LPG gas connection.
                has_daughter_under_10: True if the user has a daughter younger than 10.
                pregnant_or_lactating: True if the woman is pregnant or breastfeeding.
            """
            given = {
                "age": age, "gender": gender, "state": state, "area": area,
                "occupation": occupation, "annual_income": annual_income,
                "category": category, "minority": minority, "is_bpl": is_bpl,
                "owns_farmland": owns_farmland, "has_bank_account": has_bank_account,
                "has_pucca_house": has_pucca_house, "has_lpg": has_lpg,
                "has_daughter_under_10": has_daughter_under_10,
                "pregnant_or_lactating": pregnant_or_lactating,
            }
            updated = {}
            for field, value in given.items():
                if value is None or value == "":
                    continue
                try:
                    self.profile[field] = _norm(field, value)
                    updated[field] = self.profile[field]
                except (ValueError, TypeError):
                    continue
            self._log("update_profile", updated, f"saved {len(updated)} field(s)")
            return {"saved": updated, "full_profile": dict(self.profile)}

        def find_eligible_schemes() -> dict:
            """Run the eligibility engine on the saved profile. Returns eligible schemes (with documents, steps and links), schemes that might apply if the user confirms a few more facts, and suggested follow-up questions."""
            if len(self.profile) < 2:
                self._log("find_eligible_schemes", {}, "not enough profile info yet")
                return {"error": "Not enough information yet. Ask the user for their age, state, occupation and whether they live in a rural or urban area."}
            res = match_schemes(self.profile)
            self.last_results = res
            counts: dict = {}
            for _, missing in res["maybe"]:
                for f in missing:
                    counts[f] = counts.get(f, 0) + 1
            top_missing = sorted(counts, key=lambda f: -counts[f])[:3]
            out = {
                "eligible": [
                    {k: s[k] for k in ("id", "name", "benefit", "documents", "steps", "link", "notes")}
                    for s in res["eligible"]
                ],
                "possibly_eligible_if_confirmed": [
                    {"id": s["id"], "name": s["name"], "benefit": s["benefit"],
                     "need_to_confirm": [QUESTIONS[f] for f in missing]}
                    for s, missing in res["maybe"]
                ],
                "questions_to_ask": [QUESTIONS[f] for f in top_missing],
            }
            self._log(
                "find_eligible_schemes", {},
                f"{len(res['eligible'])} eligible, {len(res['maybe'])} possible",
            )
            return out

        def get_scheme_details(scheme_id: str) -> dict:
            """Get full details (benefit, documents, application steps, official link, notes) of one scheme.

            Args:
                scheme_id: The scheme id (e.g. pm_kisan) or scheme name.
            """
            key = (scheme_id or "").strip().lower()
            s = BY_ID.get(key)
            if s is None:
                for cand in SCHEMES:
                    if key and (key in cand["name"].lower() or key in cand["id"]):
                        s = cand
                        break
            if s is None:
                self._log("get_scheme_details", {"scheme_id": scheme_id}, "not found")
                return {"error": "Scheme not found.", "available_ids": list(BY_ID)}
            self._log("get_scheme_details", {"scheme_id": s["id"]}, s["name"])
            return {k: s[k] for k in ("id", "name", "ministry", "benefit", "documents", "steps", "link", "notes")}

        self.chat = self.client.chats.create(
            model=model,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[update_profile, find_eligible_schemes, get_scheme_details],
                temperature=0.3,
            ),
        )

    # ------------------------------------------------------------------
    def _log(self, tool: str, args: dict, summary: str):
        self.turn_trace.append({"tool": tool, "args": args, "result": summary})

    def send(self, text: Optional[str] = None, audio: Optional[bytes] = None):
        """Send a user turn. Returns (reply_text, trace_list)."""
        self.turn_trace = []
        if audio:
            parts = [
                types.Part.from_bytes(data=audio, mime_type="audio/wav"),
                (text or "") + " (This is a voice message. Understand it in whatever language it is spoken and help the user.)",
            ]
            message = parts
        else:
            message = text

        last_err = None
        for attempt in range(3):
            try:
                resp = self.chat.send_message(message)
                reply = resp.text or "Sorry, I could not generate a reply. Please try again."
                return reply, self.turn_trace
            except Exception as e:  # network / quota / overload
                last_err = e
                s = str(e)
                if any(t in s for t in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "500")):
                    time.sleep(6 * (attempt + 1))
                    continue
                raise
        raise last_err
