import hashlib
import os

import streamlit as st

from agent import FIELD_LABELS, SchemeAgent

st.set_page_config(page_title="Yojana Saathi", page_icon="🧭", layout="wide")

DEFAULT_MODEL = "gemini-2.5-flash"
GREETING = (
    "Namaste! 🙏 I'm **Yojana Saathi**, your government scheme guide.\n\n"
    "Tell me about yourself in Hindi, English or Hinglish (age, state, work, family) "
    "and I'll find the schemes you may be eligible for and how to apply.\n\n"
    "नमस्ते! अपने बारे में बताइए, मैं आपके लिए सही सरकारी योजनाएँ ढूँढूँगा।"
)

EXAMPLES = {
    "👨‍🌾 Farmer (Hindi)": "मैं राजस्थान के एक गाँव में रहने वाला 45 साल का किसान हूँ। मेरे पास 2 एकड़ ज़मीन है और परिवार की सालाना आमदनी लगभग 1.5 लाख है।",
    "🎓 SC student": "I am a 20 year old SC student from Rajasthan studying B.Tech. My family income is 2 lakh per year.",
    "🤰 Pregnant woman": "I am a 26 year old pregnant woman living in a village in Uttar Pradesh. We are a BPL family and I don't have an LPG connection.",
    "🛒 Street vendor": "I am 35, I sell vegetables on a cart in Jaipur city. I don't have a bank account.",
    "👵 Senior citizen": "I am a 72 year old woman living in a village in Bihar, my family has a BPL card.",
}

# ------------------------------------------------------------------ state
ss = st.session_state
ss.setdefault("messages", [{"role": "assistant", "content": GREETING, "trace": []}])
ss.setdefault("agent", None)
ss.setdefault("agent_sig", None)
ss.setdefault("last_audio", None)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("🧭 Yojana Saathi")
    st.caption("Agentic AI Government Scheme Navigator")
    api_key = st.secrets.get(
    "GEMINI_API_KEY",
    os.getenv("GEMINI_API_KEY", "")
)
    model = st.secrets.get(
    "GEMINI_MODEL",
    os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
)

    st.markdown("**Try an example**")
    for label, text in EXAMPLES.items():
        if st.button(label, use_container_width=True):
            ss["pending"] = text

    audio_file = None
    if hasattr(st, "audio_input"):
        st.markdown("**Or speak**")
        audio_file = st.audio_input("🎤 Speak in Hindi / English")

    if st.button("🔄 Start over", use_container_width=True):
        ss.messages = [{"role": "assistant", "content": GREETING, "trace": []}]
        ss.agent = None
        ss.agent_sig = None
        ss.last_audio = None
        st.rerun()

    st.divider()
    st.markdown("**👤 Profile built by the agent**")
    profile = ss.agent.profile if ss.agent else {}
    if profile:
        for field, label in FIELD_LABELS.items():
            if field in profile:
                st.write(f"- {label}: **{profile[field]}**")
    else:
        st.caption("Nothing collected yet.")

# --------------------------------------------------------- agent lifecycle
def get_agent():
    sig = (api_key, model)
    if ss.agent is None or ss.agent_sig != sig:
        old_profile = ss.agent.profile if ss.agent else {}
        ss.agent = SchemeAgent(api_key=api_key, model=model)
        ss.agent.profile.update(old_profile)
        ss.agent_sig = sig
    return ss.agent


def friendly_error(e: Exception) -> str:
    s = str(e)
    if "API key" in s or "API_KEY" in s or "401" in s or "403" in s:
        return "The API key looks invalid. Please check it in the sidebar."
    if "404" in s or "NOT_FOUND" in s:
        return "That Gemini model name was not found. Change the model in the sidebar (e.g. gemini-2.5-flash)."
    if "429" in s or "RESOURCE_EXHAUSTED" in s:
        return "Free-tier rate limit reached. Wait about a minute and try again."
    return f"Something went wrong: {s[:300]}"


# ------------------------------------------------------------ input handling
typed = st.chat_input("Type here... e.g. I am a 45 year old farmer from Rajasthan")
pending = ss.pop("pending", None)
user_text = typed or pending

audio_bytes = None
if audio_file is not None:
    data = audio_file.getvalue()
    digest = hashlib.md5(data).hexdigest()
    if digest != ss.last_audio:
        ss.last_audio = digest
        audio_bytes = data

if user_text or audio_bytes:
    if not api_key:
        st.warning("The app owner has not configured the Gemini API key. "
        "Please contact the team.")
    else:
        shown = user_text if user_text else "🎤 (voice message)"
        ss.messages.append({"role": "user", "content": shown, "trace": []})
        try:
            with st.spinner("Agent is thinking and using its tools..."):
                agent = get_agent()
                reply, trace = agent.send(text=user_text, audio=audio_bytes)
            ss.messages.append({"role": "assistant", "content": reply, "trace": trace})
        except Exception as e:
            ss.messages.append({"role": "assistant", "content": "⚠️ " + friendly_error(e), "trace": []})
        st.rerun()

# ------------------------------------------------------------------- views
tab_chat, tab_matches = st.tabs(["💬 Chat", "✅ Matched schemes"])

with tab_chat:
    for m in ss.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m["trace"]:
                with st.expander(f"🧠 Agent reasoning trace ({len(m['trace'])} tool calls)"):
                    for i, t in enumerate(m["trace"], 1):
                        st.markdown(f"**{i}. `{t['tool']}`** → {t['result']}")
                        if t["args"]:
                            st.json(t["args"], expanded=False)

with tab_matches:
    res = ss.agent.last_results if ss.agent else None
    if not res:
        st.info("Chat with the agent first. Matched schemes will appear here.")
    else:
        st.subheader(f"✅ Eligible schemes ({len(res['eligible'])})")
        for s in res["eligible"]:
            with st.expander(f"{s['name']}"):
                st.markdown(f"**Benefit:** {s['benefit']}")
                st.markdown("**Documents needed:**\n" + "\n".join(f"- {d}" for d in s["documents"]))
                st.markdown("**How to apply:**\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(s["steps"], 1)))
                if s.get("notes"):
                    st.caption("ℹ️ " + s["notes"])
                st.link_button("Open official portal", s["link"])
        if res["maybe"]:
            st.subheader(f"❓ Possibly eligible ({len(res['maybe'])})")
            for s, missing in res["maybe"]:
                need = ", ".join(FIELD_LABELS[f] for f in missing)
                st.markdown(f"- **{s['name']}**: need to confirm *{need}*")
    st.caption("Eligibility is indicative. Always confirm on the official portal.")

