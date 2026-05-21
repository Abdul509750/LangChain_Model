import streamlit as st
from graph import build_graph, run_graph
import re
import time
import requests.exceptions


MAX_RETRIES = 3
RETRY_BACKOFF = [2, 5, 10]


def run_graph_with_retry(graph, user_query, conversation_history, thread_id):
    last_error = None
    for attempt, wait in enumerate(RETRY_BACKOFF, start=1):
        try:
            return run_graph(
                graph=graph,
                user_query=user_query,
                conversation_history=conversation_history,
                thread_id=thread_id
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(wait)
        except Exception as exc:
            raise exc
    raise last_error


st.set_page_config(
    page_title="Synapse AI — Research Assistant",
    page_icon="S",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Syne:wght@400;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --bg:        #080C14;
    --surface:   #0D1321;
    --border:    #1C2A45;
    --accent:    #00D4FF;
    --accent2:   #7B2FFF;
    --text:      #E2EBF5;
    --muted:     #4A6080;
    --user-bg:   #0F1E35;
    --bot-bg:    #0A1628;
    --success:   #00FF88;
    --warning:   #FFB800;
    --font-head: 'Syne', sans-serif;
    --font-mono: 'Space Mono', monospace;
}

.stApp {
    background: var(--bg);
    background-image:
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0,212,255,0.08) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 80%, rgba(123,47,255,0.06) 0%, transparent 50%);
    font-family: var(--font-mono);
    color: var(--text);
}

#MainMenu, footer, header, .stDeployButton { display: none !important; }
.block-container { padding: 2rem 2rem 2rem 2rem !important; max-width: 100% !important; }

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

.synapse-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 0 24px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 28px;
}
.synapse-logo {
    font-family: var(--font-head);
    font-weight: 800;
    font-size: 24px;
    color: var(--text);
}
.synapse-logo span { color: var(--accent); }
.header-badge {
    font-size: 10px;
    color: var(--accent);
    border: 1px solid rgba(0,212,255,0.3);
    padding: 4px 12px;
    border-radius: 2px;
    letter-spacing: 2px;
    text-transform: uppercase;
    font-family: var(--font-mono);
}

.msg-wrapper { display: flex; gap: 14px; margin-bottom: 20px; animation: fadeIn 0.3s ease; }
.msg-wrapper.user-msg { flex-direction: row-reverse; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.msg-avatar {
    width: 36px; height: 36px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; flex-shrink: 0;
    font-family: var(--font-head); font-weight: 700;
}
.user-av { background: linear-gradient(135deg, var(--accent2), #5B0FCC); color: white; }
.bot-av  { background: linear-gradient(135deg, #003D5C, #005F80); color: var(--accent); border: 1px solid rgba(0,212,255,0.2); }

.msg-bubble {
    max-width: 75%; padding: 16px 20px; border-radius: 12px;
    line-height: 1.75; font-size: 13.5px;
}
.user-bubble { background: var(--user-bg); border: 1px solid var(--border); border-top-right-radius: 2px; }
.bot-bubble  { background: var(--bot-bg); border: 1px solid rgba(0,212,255,0.12); border-top-left-radius: 2px; }
.bot-bubble h2 { font-family: var(--font-head); font-size: 15px; color: var(--accent); margin: 14px 0 7px; }
.bot-bubble h3 { font-family: var(--font-head); font-size: 13px; color: var(--text); margin: 10px 0 5px; }
.bot-bubble ul { padding-left: 18px; margin: 8px 0; }
.bot-bubble li { margin: 5px 0; }
.bot-bubble strong { color: var(--accent); }

.agent-card {
    border: 1px solid var(--border); border-radius: 10px;
    padding: 12px 14px; background: var(--surface);
    margin-bottom: 10px; transition: all 0.3s;
}
.agent-card.active { border-color: var(--accent); box-shadow: 0 0 16px rgba(0,212,255,0.08); }
.agent-card.done   { border-color: var(--success); }
.agent-header { display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }
.agent-name { font-family: var(--font-head); font-size: 12px; font-weight: 700; color: var(--text); }
.agent-desc { font-size: 10px; color: var(--muted); line-height: 1.4; }
.status-pill {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 9px; padding: 2px 7px; border-radius: 20px;
    font-family: var(--font-mono); letter-spacing: 0.5px; margin-top: 7px;
}
.idle-pill    { background: rgba(74,96,128,0.15); color: var(--muted); border: 1px solid var(--border); }
.running-pill { background: rgba(0,212,255,0.08); color: var(--accent); border: 1px solid rgba(0,212,255,0.25); }
.done-pill    { background: rgba(0,255,136,0.08); color: var(--success); border: 1px solid rgba(0,255,136,0.25); }
.pulse { display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: currentColor; animation: pulse 1s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.2} }

.metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }
.metric-box { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px; text-align: center; }
.metric-val { font-family: var(--font-head); font-size: 20px; font-weight: 800; color: var(--accent); }
.metric-lbl { font-size: 9px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; margin-top: 3px; }
.conf-bar { height: 3px; background: var(--border); border-radius: 2px; overflow: hidden; margin-top: 8px; }
.conf-fill { height: 100%; background: linear-gradient(90deg, var(--accent2), var(--accent)); border-radius: 2px; }

.sec-label {
    font-size: 9px; letter-spacing: 2px; text-transform: uppercase;
    color: var(--muted); font-family: var(--font-mono); margin-bottom: 10px;
    display: flex; align-items: center; gap: 8px;
}
.sec-label::after { content:''; flex:1; height:1px; background: var(--border); }

.welcome {
    text-align: center; padding: 60px 20px; opacity: 0.6;
}
.welcome-title { font-family: var(--font-head); font-size: 18px; font-weight: 800; color: var(--text); margin-bottom: 8px; }
.welcome-sub { font-size: 12px; color: var(--muted); line-height: 1.8; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 16px; }
.chip { font-size: 10px; padding: 5px 12px; border: 1px solid var(--border); border-radius: 20px; color: var(--muted); font-family: var(--font-mono); }

.clarify-box {
    background: rgba(255,184,0,0.05); border: 1px solid rgba(255,184,0,0.25);
    border-radius: 8px; padding: 14px 18px; font-size: 12px;
    color: var(--warning); font-family: var(--font-mono); margin-bottom: 16px;
}

.stChatInput > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}
.stChatInput > div:focus-within { border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(0,212,255,0.06) !important; }
.stChatInput textarea { background: transparent !important; color: var(--text) !important; font-family: var(--font-mono) !important; font-size: 13px !important; }
.stChatInput textarea::placeholder { color: var(--muted) !important; }
.stChatInput button { background: var(--accent) !important; border-radius: 6px !important; }

.stButton > button {
    background: transparent !important; border: 1px solid var(--border) !important;
    color: var(--muted) !important; font-family: var(--font-mono) !important;
    font-size: 10px !important; width: 100% !important; border-radius: 6px !important;
    letter-spacing: 1px; transition: all 0.2s !important;
}
.stButton > button:hover { border-color: #FF5050 !important; color: #FF5050 !important; }

[data-testid="column"] { padding: 0 12px !important; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_graph():
    return build_graph()

defaults = {
    "conversation_history": [],
    "messages": [],
    "awaiting_clarification": False,
    "thread_id": "session_1",
    "last_metrics": {"confidence": 0, "attempts": 0, "validation": "—", "queries": 0},
    "agent_statuses": {"clarity": "idle", "research": "idle", "validator": "idle", "synthesis": "idle"}
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown("""
<div class="synapse-header">
    <div class="synapse-logo">Synapse<span>AI</span></div>
    <div style="display:flex;gap:10px">
        <div class="header-badge">Multi-Agent · LangGraph</div>
        <div class="header-badge">Groq · Llama 3.3</div>
    </div>
</div>
""", unsafe_allow_html=True)

chat_col, side_col = st.columns([3, 1])

with side_col:
    st.markdown('<div class="sec-label">Agent Pipeline</div>', unsafe_allow_html=True)

    agents_info = [
        ("clarity",   "Clarity Agent",   "Validates query specificity"),
        ("research",  "Research Agent",  "Web search via Tavily API"),
        ("validator", "Validator Agent", "Quality checks research"),
        ("synthesis", "Synthesis Agent", "Generates final report"),
    ]

    for key, name, desc in agents_info:
        status = st.session_state.agent_statuses.get(key, "idle")
        card_cls  = "active" if status == "running" else ("done" if status == "done" else "")
        pill_cls  = f"{status}-pill"
        pill_icon = '<span class="pulse"></span>' if status == "running" else ("+" if status == "done" else "·")

        st.markdown(f"""
        <div class="agent-card {card_cls}">
            <div class="agent-header">
                <span class="agent-name">{name}</span>
            </div>
            <div class="agent-desc">{desc}</div>
            <div class="status-pill {pill_cls}">{pill_icon} {status.upper()}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-label">Run Metrics</div>', unsafe_allow_html=True)

    m = st.session_state.last_metrics
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-box">
            <div class="metric-val">{m['confidence']}<span style="font-size:11px;opacity:0.5">/10</span></div>
            <div class="metric-lbl">Confidence</div>
        </div>
        <div class="metric-box">
            <div class="metric-val">{m['attempts']}</div>
            <div class="metric-lbl">Attempts</div>
        </div>
    </div>
    <div class="conf-bar"><div class="conf-fill" style="width:{m['confidence']*10}%"></div></div>
    <div style="margin-top:10px;font-size:10px;color:var(--muted);font-family:var(--font-mono)">
        Validation: <span style="color:{'#00FF88' if m['validation']=='sufficient' else 'var(--muted)'}">{m['validation']}</span>
        &nbsp;·&nbsp; Queries: <span style="color:var(--accent)">{m['queries']}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-label">Session</div>', unsafe_allow_html=True)
    if st.button("CLEAR CONVERSATION"):
        for k, v in defaults.items():
            st.session_state[k] = v if not isinstance(v, dict) else dict(v)
        st.session_state.agent_statuses = {"clarity": "idle", "research": "idle", "validator": "idle", "synthesis": "idle"}
        st.session_state.last_metrics = {"confidence": 0, "attempts": 0, "validation": "—", "queries": 0}
        st.rerun()

with chat_col:
    if st.session_state.awaiting_clarification:
        st.markdown("""
        <div class="clarify-box">
            Query too vague — please name a specific company and what you want to know.
        </div>
        """, unsafe_allow_html=True)

    if not st.session_state.messages:
        st.markdown("""
        <div class="welcome">
            <div class="welcome-title">Business Intelligence, Automated</div>
            <div class="welcome-sub">
                Ask about any company — financials, news,<br>
                leadership, competitors, recent developments.
            </div>
            <div class="chips">
                <span class="chip">Tesla Q4 2024 earnings</span>
                <span class="chip">Apple latest news</span>
                <span class="chip">OpenAI funding</span>
                <span class="chip">Microsoft Azure growth</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.messages:
            role = msg["role"]
            content = msg["content"]
            wrapper_cls = "user-msg" if role == "user" else ""
            avatar_cls  = "user-av" if role == "user" else "bot-av"
            avatar_char = "U" if role == "user" else "S"
            bubble_cls  = "user-bubble" if role == "user" else "bot-bubble"

            st.markdown(f"""
            <div class="msg-wrapper {wrapper_cls}">
                <div class="msg-avatar {avatar_cls}">{avatar_char}</div>
                <div class="msg-bubble {bubble_cls}">{content}</div>
            </div>
            """, unsafe_allow_html=True)

    user_input = st.chat_input("Ask about any company — e.g. 'What are Tesla's latest earnings?'")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.conversation_history.append({"role": "user", "content": user_input})
    st.session_state.agent_statuses = {"clarity": "running", "research": "idle", "validator": "idle", "synthesis": "idle"}

    graph = get_graph()
    response_text = ""

    try:
        with st.spinner("Agents working..."):
            final_state = run_graph_with_retry(
                graph=graph,
                user_query=user_input,
                conversation_history=st.session_state.conversation_history,
                thread_id=st.session_state.thread_id
            )

        clarity    = final_state.get("clarity_status", "")
        answer     = final_state.get("final_answer", "")
        confidence = final_state.get("confidence_score", 0)
        attempts   = final_state.get("attempts", 0)
        validation = final_state.get("validation_result", "—")

        st.session_state.agent_statuses["clarity"] = "done"

        if clarity == "needs_clarification":
            response_text = (
                "Your query requires more detail.<br><br>"
                "Please include a <strong>specific company name</strong> and what you want to know.<br><br>"
                "<em>Example: 'What are Tesla's Q4 2024 earnings?'</em>"
            )
            st.session_state.awaiting_clarification = True
        elif answer:
            st.session_state.agent_statuses.update({"research": "done", "synthesis": "done"})
            if attempts > 1:
                st.session_state.agent_statuses["validator"] = "done"
            st.session_state.awaiting_clarification = False

            html = answer
            html = re.sub(r'^## (.+)$',  r'<h2>\1</h2>', html, flags=re.MULTILINE)
            html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
            html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
            html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
            html = html.replace('\n\n', '<br>')

            response_text = html
            st.session_state.last_metrics = {
                "confidence": confidence, "attempts": attempts,
                "validation": validation or "sufficient",
                "queries": st.session_state.last_metrics["queries"] + 1
            }
            st.session_state.conversation_history.append({"role": "assistant", "content": answer})
        else:
            response_text = "The request completed but returned no content. Please try again."

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        st.session_state.agent_statuses = {k: "idle" for k in st.session_state.agent_statuses}
        response_text = (
            "Unable to reach the research service after several attempts. "
            "This is usually a temporary network issue.<br><br>"
            "Please check your connection and try again in a moment."
        )
    except Exception:
        st.session_state.agent_statuses = {k: "idle" for k in st.session_state.agent_statuses}
        response_text = "An unexpected error occurred. Please try again."

    st.session_state.messages.append({"role": "assistant", "content": response_text})
    st.rerun()