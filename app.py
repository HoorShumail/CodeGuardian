import streamlit as st
import os
import uuid
import tempfile
import sqlite3
import datetime
from langgraph.types import Command
from src.graph import graph
from config import OPENAI_API_KEY, GITHUB_TOKEN

# --- Page Config ---
st.set_page_config(
    page_title="AI Code Review Agent | Premium",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Premium CSS Overhaul ---
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background: radial-gradient(circle at top right, #1a1c2c, #0e1117);
        color: #e0e0e0;
    }
    
    /* Custom Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(30, 34, 51, 0.7);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        margin-bottom: 20px;
    }
    
    /* Metrics Styling */
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00ffcc, #0099ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Comment Cards */
    .comment-box {
        padding: 15px;
        border-radius: 10px;
        background: rgba(40, 44, 61, 0.5);
        border-left: 4px solid #00ffcc;
        margin-bottom: 12px;
        transition: transform 0.2s ease;
    }
    .comment-box:hover {
        transform: translateX(5px);
        background: rgba(50, 54, 71, 0.6);
    }
    .sev-error { border-left-color: #ff4b4b; }
    .sev-warning { border-left-color: #ffa500; }
    .sev-suggestion { border-left-color: #00ffcc; }
    
    /* Buttons */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 255, 204, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)

# --- Helper: Mermaid Renderer ---
def render_mermaid(mermaid_code):
    html_code = f"""
    <div class="mermaid" style="background-color: transparent;">
        {mermaid_code}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'dark', securityLevel: 'loose' }});
    </script>
    """
    st.components.v1.html(html_code, height=300)

# --- Helper: Load History ---
def get_report_history():
    if not os.path.exists("reports"):
        return []
    files = [f for f in os.listdir("reports") if f.endswith(".md")]
    return sorted(files, reverse=True)

# --- Session State ---
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "current_state" not in st.session_state:
    st.session_state.current_state = {}
if "node_progress" not in st.session_state:
    st.session_state.node_progress = "START"
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "🚀 New Review"

# --- Sidebar: History & Config ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2103/2103857.png", width=80)
    st.title("CR Agent v2.0")
    st.markdown("---")
    
    st.markdown("### 📜 Recent Reports")
    history = get_report_history()
    if history:
        selected_report = st.selectbox("Select a previous review", options=history)
        if st.button("👁️ View Report", use_container_width=True):
            try:
                with open(f"reports/{selected_report}", "r", encoding="utf-8") as f:
                    st.session_state.loaded_report = f.read()
                st.session_state.active_tab = "📊 Final Report"
                st.session_state.thread_id = None
                st.toast(f"Loaded: {selected_report}")
                st.rerun()
            except Exception as e:
                st.error(f"Error loading report: {e}")
    else:
        st.caption("No reports generated yet.")

    st.markdown("---")
    st.markdown("### ⚙️ Session Controls")
    if st.button("🗑️ Reset Session", use_container_width=True):
        st.session_state.thread_id = None
        st.session_state.current_state = {}
        st.session_state.node_progress = "START"
        st.session_state.active_tab = "🚀 New Review"
        if "loaded_report" in st.session_state:
            del st.session_state.loaded_report
        st.rerun()

# --- Main App ---
st.title("🛡️ AI-Driven Code Intelligence")

# Premium Navigation Bar
st.session_state.active_tab = st.segmented_control(
    "Navigation",
    options=["🚀 New Review", "🕵️ Active Analysis", "📊 Final Report"],
    selection_mode="single",
    default=st.session_state.active_tab
) or st.session_state.active_tab

# --- TAB CONTENT: NEW REVIEW ---
if st.session_state.active_tab == "🚀 New Review":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("Configure Your Review")
    
    t1, t2 = st.columns([2, 1])
    with t2:
        tone = st.selectbox(
            "Reviewer Personality",
            options=["The Architect", "The Security Auditor", "The Junior Mentor"],
            help="Determines the focus and tone of the AI analysis."
        )
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 1. GitHub PR")
        pr_url = st.text_input("PR URL", placeholder="https://github.com/.../pull/42")
    with col2:
        st.markdown("#### 2. Paste Code")
        p_code = st.text_area("Paste snippet", height=200, placeholder="Paste your code here...")
        p_name = st.text_input("Filename", value="main.py")
    with col3:
        st.markdown("#### 3. Upload File")
        u_file = st.file_uploader("Drop source file", type=["py", "js", "ts", "java", "cpp", "go", "rs"])

    if st.button("🚀 IGNITE ANALYSIS", type="primary", use_container_width=True):
        if not pr_url and not p_code and not u_file:
            st.error("Please provide input source.")
        else:
            st.session_state.thread_id = str(uuid.uuid4())
            
            # Prepare state
            final_code = ""
            final_name = ""
            if p_code:
                final_code, final_name = p_code, p_name
            elif u_file:
                final_code, final_name = u_file.getvalue().decode("utf-8"), u_file.name
                
            st.session_state.initial_state = {
                "pr_url": pr_url,
                "local_diff_path": "",
                "pasted_code": final_code,
                "pasted_filename": final_name,
                "reviewer_tone": tone,
                "lint_results": [],
                "security_results": [],
                "complexity_results": [],
                "ai_comments": [],
                "human_feedback": None,
                "final_report": "",
            }
            st.session_state.active_tab = "🕵️ Active Analysis"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB CONTENT: ACTIVE ANALYSIS ---
elif st.session_state.active_tab == "🕵️ Active Analysis":
    if not st.session_state.thread_id:
        st.info("No active session. Start a review in the first tab.")
    else:
        # Visualization
        st.markdown("#### 🗺️ Agent Flow")
        nodes = ["fetch_diff", "parse_files", "tools", "ai_analysis", "hitl_review"]
        current_idx = nodes.index(st.session_state.node_progress) if st.session_state.node_progress in nodes else 0
        
        mermaid = f"""
        graph LR
            A[Fetch] --> B[Parse]
            B --> C[Static Scan]
            C --> D[AI Brain]
            D --> E[Human Review]
            
            style {"ABCDE"[current_idx]} fill:#00ffcc,stroke:#000,stroke-width:2px,color:#000
        """
        render_mermaid(mermaid)
        
        # Execution Engine
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        
        if "initial_state" in st.session_state:
            init_state = st.session_state.pop("initial_state")
            try:
                with st.status("🧠 Agents at work...", expanded=True) as status:
                    for event in graph.stream(init_state, config=config, stream_mode="values"):
                        st.session_state.current_state = event
                        if "diff" in event: st.session_state.node_progress = "fetch_diff"
                        if "files" in event: st.session_state.node_progress = "parse_files"
                        if "lint_results" in event: st.session_state.node_progress = "tools"
                        if "ai_comments" in event: st.session_state.node_progress = "ai_analysis"
                    
                    st.session_state.node_progress = "hitl_review"
                    status.update(label="Analysis Complete. Awaiting Human.", state="complete")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Analysis Failed: {str(e)}")
                st.exception(e)
                st.session_state.node_progress = "START"
                st.session_state.thread_id = None

        # Display Results Panel
        curr = st.session_state.current_state
        if curr:
            # Three-Panel Layout
            c_left, c_mid, c_right = st.columns([1, 2, 1.5])
            
            with c_left:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown("#### 📈 Metrics")
                score = curr.get("score", 0)
                st.markdown(f'<div class="metric-value">{score}%</div>', unsafe_allow_html=True)
                st.progress(score / 100)
                
                st.markdown("#### 📜 Stats")
                st.write(f"📂 Files: {len(curr.get('files', []))}")
                st.write(f"🚨 Issues: {len(curr.get('ai_comments', []))}")
                
                approved = curr.get("approved", False)
                st.markdown(f"**Approved:** {'✅' if approved else '❌'}")
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown("#### 🧠 AI Summary")
                st.caption(curr.get("overall_summary", "Calculating..."))
                st.markdown('</div>', unsafe_allow_html=True)

            with c_mid:
                st.markdown("#### 📄 Code Diff / Snippet")
                st.code(curr.get("diff", "No diff found."), language="diff")
                
                if curr.get("lint_results"):
                    with st.expander("🛠️ Raw Linter Findings"):
                        st.json(curr["lint_results"])

            with c_right:
                st.markdown("#### 💬 AI Comments")
                for c in curr.get("ai_comments", []):
                    s_class = f"sev-{c.severity.lower()}"
                    st.markdown(f"""
                        <div class="comment-box {s_class}">
                            <strong>{c.file}:{c.line}</strong> <span style="font-size:0.8em; color:#888;">[{c.category}]</span><br>
                            {c.message}<br>
                            {f'<code style="color:#00ffcc; font-size:0.9em;">Fix: {c.suggested_fix}</code>' if c.suggested_fix else ''}
                        </div>
                    """, unsafe_allow_html=True)

            # Decision Bar
            st.markdown("---")
            st.subheader("🏁 Human Decision")
            h_feedback = st.text_input("Notes for AI (if revising)", placeholder="e.g., 'This print is intentional for debugging'")
            
            b1, b2 = st.columns(2)
            with b1:
                if st.button("✅ APPROVE & FINALIZE", use_container_width=True):
                    with st.spinner("Generating final report..."):
                        for event in graph.stream(Command(resume="approve"), config=config, stream_mode="values"):
                            st.session_state.current_state = event
                        st.session_state.active_tab = "📊 Final Report"
                        st.rerun()
            with b2:
                if st.button("🔄 REQUEST REVISION", use_container_width=True):
                    rev_feedback = f"revise: {h_feedback}" if h_feedback else "revise"
                    with st.spinner("Consulting AI again..."):
                        for event in graph.stream(Command(resume=rev_feedback), config=config, stream_mode="values"):
                            st.session_state.current_state = event
                        st.rerun()

# --- TAB CONTENT: FINAL REPORT ---
elif st.session_state.active_tab == "📊 Final Report":
    if hasattr(st.session_state, "loaded_report"):
        st.markdown(st.session_state.loaded_report)
        if st.button("⬅️ Back to Active Session"):
            del st.session_state.loaded_report
            st.session_state.active_tab = "🕵️ Active Analysis"
            st.rerun()
    elif st.session_state.current_state.get("final_report"):
        st.markdown(st.session_state.current_state["final_report"])
    else:
        st.info("No report generated in this session. Visit 'Active Analysis' to finalize.")
