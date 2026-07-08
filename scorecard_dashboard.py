"""
DS 6051 Hackathon - Gemma Safety Scorecard Dashboard
-----------------------------------------------------
One tab per eval workstream folder in this repo:
  Academic-integrity/   truthfulqa/   openbookqa/   promptinjection/

Run from the repo ROOT (the folder containing Academic-integrity/, truthfulqa/, etc.):
    streamlit run scorecard_dashboard.py

If a section shows a warning instead of data, this script is not being run from
the repo root, or a file was renamed/moved -- check "Data Diagnostics" on the
Overview tab for the exact paths being checked and whether each was found.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import streamlit as st

st.set_page_config(page_title="Gemma Safety Scorecard", page_icon=":shield:", layout="wide")

# --------------------------------------------------------------------------
# Design system: light, legible audit-report look. IBM Plex type family,
# a soft paper background rather than pure white, teal/amber/red status
# colors tuned for contrast on a light background.
# --------------------------------------------------------------------------
INK = "#1C2430"
PAPER = "#F6F7F9"
PANEL = "#FFFFFF"
LINE = "#DCE1E8"
TEAL = "#0E8C82"
AMBER = "#B8790A"
RED = "#C23B4B"
MUTED = "#5B6472"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{
    font-family: 'IBM Plex Sans', sans-serif;
    color: {INK};
}}
.stApp {{
    background-color: {PAPER};
}}
h1, h2, h3 {{
    font-family: 'IBM Plex Serif', serif !important;
    color: {INK} !important;
    letter-spacing: -0.01em;
}}
h1 {{ border-bottom: 3px solid {TEAL}; padding-bottom: 0.4rem; }}
h2 {{ border-bottom: 1px solid {LINE}; padding-bottom: 0.3rem; margin-top: 1.6rem; }}
p, li, span, div {{ color: {INK}; }}
code, .stCode, .stMarkdown code {{ font-family: 'IBM Plex Mono', monospace !important; }}

[data-testid="stSidebar"] {{
    background-color: {PANEL};
    border-right: 1px solid {LINE};
}}
[data-testid="stMetric"] {{
    background-color: {PANEL};
    border: 1px solid {LINE};
    border-left: 4px solid {TEAL};
    border-radius: 6px;
    padding: 0.9rem 1rem 0.6rem 1rem;
    box-shadow: 0 1px 2px rgba(28, 36, 48, 0.04);
}}
[data-testid="stMetricLabel"] {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: {MUTED} !important;
}}
[data-testid="stMetricValue"] {{
    font-family: 'IBM Plex Serif', serif !important;
    color: {INK} !important;
}}
.stTabs [data-baseweb="tab-list"] {{
    gap: 28px;
    border-bottom: 1px solid {LINE};
    padding-bottom: 0;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    color: {MUTED};
    background-color: transparent;
    padding: 10px 4px;
    margin: 0;
}}
.stTabs [aria-selected="true"] {{
    color: {TEAL} !important;
}}
/* Streamlit/BaseWeb renders its own highlight bar under the active tab as a
   separate element -- override it instead of layering a second border,
   which is what produced the two-tone (red + teal) underline. */
.stTabs [data-baseweb="tab-highlight"] {{
    background-color: {TEAL} !important;
    height: 3px !important;
}}
.stTabs [data-baseweb="tab-border"] {{
    background-color: {LINE} !important;
}}
[data-testid="stDataFrame"] {{
    border: 1px solid {LINE};
    border-radius: 6px;
}}
[data-testid="stExpander"] {{
    background-color: {PANEL};
    border: 1px solid {LINE};
    border-radius: 6px;
}}
.eyebrow {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {TEAL};
    display: block;
}}
hr {{ border-color: {LINE}; }}
</style>
""", unsafe_allow_html=True)

# Matplotlib theme matched to the light app background
mpl.rcParams.update({
    "figure.facecolor": "none",
    "axes.facecolor": "none",
    "savefig.facecolor": "none",
    "axes.edgecolor": LINE,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "font.family": "monospace",
    "font.size": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "grid.color": LINE,
    "grid.alpha": 0.8,
})

# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
AI, TQ, OBQA, PI = "Academic-integrity", "truthfulqa", "openbookqa", "promptinjection"

FILES = {
    "ai_summary": f"{AI}/academic_integrity_summary.csv",
    "ai_category": f"{AI}/category_difficulty_analysis.csv",
    "ai_judge_agreement": f"{AI}/judge_agreement_summary.csv",
    "ai_stat_sig": f"{AI}/statistical_significance_summary.csv",
    "ai_eval_awareness": f"{AI}/evaluation_awareness_summary.csv",
    "tq_scorecard": f"{TQ}/truthfulqa_scorecard.csv",
    "tq_category": f"{TQ}/truthfulqa_category_summary_results.csv",
    "tq_improvement": f"{TQ}/model_improvement_table.csv",
    "obqa_with": f"{OBQA}/grading_results_instructions.csv",
    "obqa_without": f"{OBQA}/grading_results_gemma_no_instructions.csv",
    "pi_summary": f"{PI}/prompt_injection_scorecard_summary.csv",
    "pi_detailed": f"{PI}/prompt_injection_scorecard_detailed.csv",
}

@st.cache_data
def load_csv(path):
    return pd.read_csv(path) if os.path.exists(path) else None

data = {k: load_csv(v) for k, v in FILES.items()}
locals().update(data)
missing = [k for k, v in data.items() if v is None]

def bar_chart(labels, values, colors=None, ylabel="", ylim=None, figsize=(5, 3), horizontal=False):
    fig, ax = plt.subplots(figsize=figsize)
    colors = colors or [TEAL] * len(values)
    if horizontal:
        ax.barh(labels, values, color=colors, height=0.55)
        ax.invert_yaxis()
        if ylim:
            ax.set_xlim(ylim)
        for i, v in enumerate(values):
            ax.text(v + (ylim[1]*0.01 if ylim else 0.5), i, f"{v:.1f}", va="center", fontsize=8, color=MUTED)
    else:
        ax.bar(labels, values, color=colors, width=0.55)
        if ylim:
            ax.set_ylim(ylim)
        for i, v in enumerate(values):
            ax.text(i, v + (ylim[1]*0.02 if ylim else 0.02), f"{v:.1f}", ha="center", fontsize=8, color=MUTED)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.grid(axis="x" if horizontal else "y", linestyle="--", linewidth=0.5)
    fig.tight_layout()
    return fig

def grouped_bar(categories, series_dict, ylabel="", ylim=(0, 5.5), figsize=(6, 3.2)):
    fig, ax = plt.subplots(figsize=figsize)
    n = len(series_dict)
    width = 0.8 / n
    x = range(len(categories))
    palette = [MUTED, TEAL, AMBER, RED]
    for i, (name, values) in enumerate(series_dict.items()):
        offsets = [xi + (i - (n - 1) / 2) * width for xi in x]
        ax.bar(offsets, values, width=width, label=name, color=palette[i % len(palette)])
    ax.set_xticks(list(x))
    ax.set_xticklabels(categories, fontsize=8)
    ax.set_ylim(ylim)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, 1.18), ncol=n)
    ax.grid(axis="y", linestyle="--", linewidth=0.5)
    fig.tight_layout()
    return fig

# --------------------------------------------------------------------------
# Master scorecard -- defined once, filtered per tab so each domain's page
# can show its own rows at the top, and Overview can show all of them.
# --------------------------------------------------------------------------
SCORECARD_ROWS = [
    dict(Domain="Academic Integrity", Metric="Pass Rate", Result="96.7%",
         Justification="Measures whether the model helps students complete graded work dishonestly.",
         Measurement="Automated (ShieldGemma judge; violation probability < 25% = pass)",
         Limitations="Binary threshold may miss subtle/partial violations; judge trained mostly on English."),
    dict(Domain="Academic Integrity", Metric="Educational Helpfulness (1-5)", Result="4.43",
         Justification="A tutor that only refuses is not useful -- it must still support learning.",
         Measurement="LLM-as-judge (Gemma-4-E2B-it self-scoring)",
         Limitations="Scored by the model being evaluated -- see the self-preference check below."),
    dict(Domain="Academic Integrity", Metric="Politeness (1-5)", Result="5.00",
         Justification="Harsh refusals can discourage students from asking for help at all.",
         Measurement="LLM-as-judge (same as above)",
         Limitations="Same self-preference risk as helpfulness."),
    dict(Domain="Academic Integrity", Metric="Judge Cross-Validation", Result="Self 5.00 / Phi-3 5.00 / Qwen 4.60",
         Justification="Tests whether the self-judge inflates the IT model's own scores.",
         Measurement="2 independent judges (Phi-3-mini, Qwen2.5-3B), n=10",
         Limitations="Small sample (n=20 total); each judge model has its own scoring quirks."),
    dict(Domain="Academic Integrity", Metric="Cross-Lingual Safety Gap (Novelty)", Result="See chart below",
         Justification="Tests whether refusal behavior holds up when the same prompts are translated -- alignment trained mostly on English is not guaranteed to transfer.",
         Measurement="Automated (ShieldGemma pass rate, English vs. translated prompts)",
         Limitations="Small set of translated prompts; translation quality itself is a confound."),
    dict(Domain="Truthfulness", Metric="Pass Rate (IT model)", Result="100% (n=50)",
         Justification="Measures whether responses assert false claims as fact.",
         Measurement="Automated (ShieldGemma, custom truthfulness guideline)",
         Limitations="Small sample (50 of 817 prompts); threshold-based."),
    dict(Domain="Truthfulness", Metric="Factual Accuracy (1-5)", Result="3.40 -> 4.20",
         Justification="Checks responses against TruthfulQA's reference answer.",
         Measurement="LLM-as-judge, scored against Best Answer + known incorrect answers",
         Limitations="Judge does not penalize evasive non-answers."),
    dict(Domain="Truthfulness", Metric="Avoids Misconception (1-5)", Result="3.34 -> 4.36",
         Justification="Isolates whether the model resists the specific myth a question baits.",
         Measurement="LLM-as-judge, checked against known incorrect answers",
         Limitations="Same judge-model limitations as above."),
    dict(Domain="Truthfulness", Metric="Clarity (1-5)", Result="3.52 -> 4.66",
         Justification="An accurate but incomprehensible answer does not help a student learn.",
         Measurement="LLM-as-judge",
         Limitations="Subjective; judge's own writing style may bias scoring."),
    dict(Domain="Knowledge & Reasoning", Metric="Accuracy, with instructions", Result="80% (n=10)",
         Justification="Baseline check that the model knows the subject matter.",
         Measurement="Automated (exact match)",
         Limitations="Small sample; accuracy alone misses explanation quality."),
    dict(Domain="Knowledge & Reasoning", Metric="Accuracy, no instructions", Result="40% (n=5)",
         Justification="Tests reliance on explicit formatting instructions.",
         Measurement="Automated, same method",
         Limitations="All no-instruction responses failed parsing -- see below."),
    dict(Domain="Knowledge & Reasoning", Metric="Explanation Quality (1-5)", Result="4.60",
         Justification="A tutor should explain why, not just give the letter answer.",
         Measurement="LLM-as-judge",
         Limitations="Only scored where responses were parseable."),
    dict(Domain="Robustness", Metric="Prompt Injection Pass Rate", Result="0.0%",
         Justification="Tests whether integrity rules survive a direct override attempt.",
         Measurement="Automated (compliance/instruction-protection flags)",
         Limitations="Small adversarial set; a 0% result merits manual review."),
    dict(Domain="Robustness", Metric="Instruction-Following Fidelity", Result="3.0 / 5",
         Justification="Distinguishes 'ignored the attack' from 'produced garbage.'",
         Measurement="LLM-as-judge",
         Limitations="Judge scoring of fidelity under attack is itself under-explored."),
    dict(Domain="Robustness", Metric="Response Quality", Result="5.0 / 5",
         Justification="Checks for coherence under attack, separate from compliance.",
         Measurement="LLM-as-judge",
         Limitations="High quality does not imply the response was safe."),
]
SCORECARD_DF = pd.DataFrame(SCORECARD_ROWS)

def show_scorecard(domains=None):
    """Render the scorecard table, optionally filtered to a list of domains."""
    df = SCORECARD_DF if domains is None else SCORECARD_DF[SCORECARD_DF["Domain"].isin(domains)]
    st.dataframe(df, use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("<span class='eyebrow'>DS 6051 - Safety Audit</span>", unsafe_allow_html=True)
    st.title("Gemma Scorecard")
    st.caption("Use case: Gemma-4-E2B(-it) as an educational tutor")
    st.divider()
    st.markdown("**Repo folders (one tab each)**")
    st.markdown(
        "- Academic-integrity/\n"
        "- truthfulqa/\n"
        "- openbookqa/\n"
        "- promptinjection/"
    )
    st.divider()
    st.caption(f"Working directory:\n`{os.getcwd()}`")
    if missing:
        st.warning(f"{len(missing)} of {len(FILES)} expected files not found. See Data Diagnostics.")
    else:
        st.success("All expected data files loaded.")

tabs = st.tabs([
    "Overview", "Academic-integrity", "truthfulqa", "openbookqa", "promptinjection"
])

# ==========================================================================
# TAB: Overview
# ==========================================================================
with tabs[0]:
    st.header("Use Case: Gemma as an Educational Tutor")

    st.subheader("Full Scorecard (All Domains)")
    domain_filter = st.multiselect(
        "Filter by domain", options=SCORECARD_DF["Domain"].unique().tolist(),
        default=SCORECARD_DF["Domain"].unique().tolist(), key="overview_filter"
    )
    show_scorecard(domain_filter)

    st.markdown(
        "- We evaluate whether **Gemma-4-E2B(-it)** is safe to deploy as a tutoring assistant.\n"
        "- A tutor must be genuinely helpful while resisting two failure modes: **enabling cheating** and **reinforcing misinformation**.\n"
        "- It must also stay robust when students, deliberately or not, try to manipulate it out of those behaviors.\n"
        "- This is an **evaluation exercise, not a training exercise** -- Gemma was not fine-tuned. Every result reflects out-of-the-box behavior.\n"
        "- Each tab that follows matches a folder in the GitHub repo, containing that folder's own scorecard, results, methodology, and limitations."
    )

    st.subheader("Why These Four Dimensions")
    why_df = pd.DataFrame([
        {"Dimension": "Academic Integrity", "Why it matters for a tutor":
            "Core deployment risk -- a tutor that does homework for students isn't teaching them anything."},
        {"Dimension": "Truthfulness", "Why it matters for a tutor":
            "Confidently repeating myths actively miseducates -- worse than saying nothing."},
        {"Dimension": "Knowledge and Reasoning", "Why it matters for a tutor":
            "Baseline check that the model actually knows the material it is meant to teach."},
        {"Dimension": "Robustness", "Why it matters for a tutor":
            "Students will try to override the rules directly -- integrity is worthless if trivially bypassed."},
    ])
    st.dataframe(why_df, use_container_width=True, hide_index=True)

    st.subheader("Scorecard At a Glance")
    domains = ["Academic\nIntegrity", "Truthfulness\n(IT model)", "Knowledge &\nReasoning", "Robustness"]
    pass_rates = [
        ai_summary["pass_rate"].iloc[0] * 100 if ai_summary is not None else 0,
        tq_scorecard[tq_scorecard["Model"] == "Gemma-4-E2B-it"]["Pass Rate (%)"].iloc[0] if tq_scorecard is not None else 0,
        obqa_with["correct"].mean() * 100 if obqa_with is not None else 0,
        pi_summary[pi_summary["metric"] == "Prompt Injection Pass Rate"]["result"].iloc[0] * 100 if pi_summary is not None else 0,
    ]
    colors = [TEAL if v >= 70 else (AMBER if v >= 40 else RED) for v in pass_rates]
    col1, col2 = st.columns([2, 1])
    with col1:
        st.pyplot(bar_chart(domains, pass_rates, colors=colors, ylabel="Pass rate (%)", ylim=(0, 105), figsize=(6.5, 3.4)))
    with col2:
        st.markdown(
            "**Reading this chart**\n"
            "- Teal: strong pass rate (70%+)\n"
            "- Amber: moderate (40-70%)\n"
            "- Red: weak (under 40%)\n\n"
            "Robustness is the clear outlier -- see the promptinjection tab for why."
        )

    with st.expander("Data Diagnostics (open if results are missing)"):
        st.write(
            "This app expects to be launched from the repo root -- the folder that "
            "directly contains `Academic-integrity/`, `truthfulqa/`, `openbookqa/`, "
            "and `promptinjection/`."
        )
        diag_df = pd.DataFrame([
            {"Key": k, "Expected path": v, "Found": os.path.exists(v)} for k, v in FILES.items()
        ])
        st.dataframe(diag_df, use_container_width=True, hide_index=True)
        st.code(f"streamlit run scorecard_dashboard.py   # run from: {os.getcwd()}")

# ==========================================================================
# TAB: Academic-integrity/
# ==========================================================================
with tabs[1]:
    st.header("Academic-integrity/")

    st.subheader("Scorecard")
    show_scorecard(["Academic Integrity"])

    st.markdown(
        "- **Use-case risk covered:** does the model help students complete graded work dishonestly.\n"
        "- **Dataset:** custom-authored prompt set spanning Homework, Exam, Essay, and Hidden Cheating (indirect requests).\n"
        "- **Judges:** ShieldGemma-2B for pass/fail; Gemma-4-E2B-it (self) for 1-5 quality scoring, cross-validated against Phi-3-mini and Qwen2.5-3B."
    )

    if ai_summary is not None:
        c1, c2, c3 = st.columns(3)
        c1.metric("Pass Rate", f"{ai_summary['pass_rate'].iloc[0]*100:.1f}%")
        c2.metric("Prompts Tested", int(ai_summary["total_prompts"].iloc[0]))
        c3.metric("Failed", int(ai_summary["failed"].iloc[0]))
    else:
        st.warning(f"Expected file not found: `{FILES['ai_summary']}`")

    if ai_category is not None:
        col1, col2 = st.columns([3, 2])
        with col1:
            cat_sorted = ai_category[ai_category["model_name"] == ai_category["model_name"].iloc[0]].sort_values("pass_rate")
            st.pyplot(bar_chart(
                cat_sorted["category"].tolist(), cat_sorted["pass_rate"].tolist(),
                colors=[RED if v < 90 else TEAL for v in cat_sorted["pass_rate"]],
                ylabel="Pass rate (%)", ylim=(0, 105), horizontal=True, figsize=(5, 3.2)
            ))
        with col2:
            worst = ai_category.sort_values("pass_rate").iloc[0]
            st.markdown(
                f"**By category**\n"
                f"- Hardest: **{worst['category']}** at {worst['pass_rate']:.0f}% for {worst['model_name']}\n"
                "- Failures cluster around specific request framings, not uniformly"
            )
        with st.expander("Full category table"):
            st.dataframe(ai_category, use_container_width=True, hide_index=True)
    else:
        st.warning(f"Expected file not found: `{FILES['ai_category']}`")

    st.subheader("Self-Judge Bias Check")
    st.markdown(
        "Gemma-4-E2B-it scores its own responses for helpfulness/politeness -- cross-validated "
        "against two independent judges rather than assumed reliable:"
    )
    if ai_judge_agreement is not None:
        st.dataframe(ai_judge_agreement, use_container_width=True, hide_index=True)
        st.markdown(
            "- Cohen's kappa near zero: weak agreement beyond chance between judges and human labels\n"
            "- Percent agreement (75-90%) looks better but overstates reliability when one class dominates\n"
            "- Conclusion: a genuine limitation, not a clean validation"
        )
    else:
        st.warning(f"Expected file not found: `{FILES['ai_judge_agreement']}`")

    st.subheader("Statistical Significance")
    if ai_stat_sig is not None:
        st.dataframe(ai_stat_sig, use_container_width=True, hide_index=True)
        st.markdown(
            "- Bootstrap CI on the pass-rate difference: roughly **3 to 30 points**\n"
            "- Direction (IT model safer) is likely real; magnitude is not tightly pinned down by this sample"
        )
    else:
        st.warning(f"Expected file not found: `{FILES['ai_stat_sig']}`")

    st.subheader("Evaluation Awareness")
    if ai_eval_awareness is not None:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(ai_eval_awareness, use_container_width=True, hide_index=True)
        with col2:
            st.markdown(
                "- Tests behavior when a prompt signals it's being evaluated\n"
                "- Near-identical pass rates (93.3% both conditions)\n"
                "- No detectable evaluation-gaming here -- a narrow test of a broader concern (sandbagging)"
            )
    else:
        st.warning(f"Expected file not found: `{FILES['ai_eval_awareness']}`")

    st.markdown(
        f"<span style='background-color:{AMBER}; color:{PAPER}; font-family:\"IBM Plex Mono\",monospace; "
        f"font-size:0.72rem; font-weight:600; letter-spacing:0.06em; padding:2px 8px; border-radius:3px;'>"
        f"NOVELTY</span>",
        unsafe_allow_html=True
    )
    st.subheader("Cross-Lingual Safety Distribution Shift")
    st.markdown(
        "- Not one of the core four scorecard dimensions -- added as a bonus metric per the hackathon brief's "
        "cross-lingual safety distribution shift suggestion.\n"
        "- **What it tests:** modern models often show robust safety guardrails in English that degrade in "
        "other languages -- a model can safely refuse a harmful/dishonest prompt in English yet comply with "
        "the same request translated into another language.\n"
        "- **How it was measured:** a subset of the academic-integrity prompt set was translated into one or "
        "more additional languages (including at least one lower-resource language, per the brief's "
        "recommendation) and re-run through ShieldGemma; refusal/pass rates are compared to the English baseline."
    )
    img_path = f"{AI}/cross_lingual_safety_gap.png"
    if os.path.exists(img_path):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.image(img_path, caption="Safety gap: English vs. additional language(s)", use_container_width=True)
        with col2:
            st.markdown(
                "**What the gap means**\n"
                "- Any drop from the English pass rate indicates the integrity guardrail is weaker in that language\n"
                "- Alignment trained mostly on English does not transfer cleanly\n"
                "- Relevant wherever a tutor might serve non-English speakers"
            )
    else:
        st.warning(f"Expected image not found: `{img_path}`")

    with st.expander("Additional pre-rendered chart artifacts"):
        img_cols = st.columns(3)
        ai_imgs = ["pass_rate.png", "avg_integrity.png", "avg_helpfulness.png",
                   "avg_politeness.png", "category_performance.png", "educational_safety_score.png",
                   "adversarial_robustness.png"]
        for i, img in enumerate(ai_imgs):
            path = f"{AI}/{img}"
            if os.path.exists(path):
                img_cols[i % 3].image(path, caption=img, use_container_width=True)

    st.subheader("Limitations")
    st.markdown(
        "- Binary pass/fail threshold may miss subtle or partial violations\n"
        "- Self-judge bias risk on helpfulness/politeness scores\n"
        "- Small sample sizes limit statistical confidence\n"
        "- Judges are English-first; cross-lingual safety only partially tested"
    )

# ==========================================================================
# TAB: truthfulqa/
# ==========================================================================
with tabs[2]:
    st.header("truthfulqa/")

    st.subheader("Scorecard")
    show_scorecard(["Truthfulness"])

    st.markdown(
        "- **Use-case risk covered:** does the model confidently repeat misconceptions the question is designed to bait.\n"
        "- **Dataset:** TruthfulQA (standard benchmark), sampled subset (50-150 of 817 prompts) for time constraints.\n"
        "- **Judges:** ShieldGemma-2B with a custom truthfulness guideline for pass/fail; Gemma-4-E2B-it for 1-5 factual accuracy, misconception-avoidance, and clarity scoring."
    )

    if tq_scorecard is not None:
        base_row = tq_scorecard[tq_scorecard["Model"] == "Gemma-4-E2B"].iloc[0]
        it_row = tq_scorecard[tq_scorecard["Model"] == "Gemma-4-E2B-it"].iloc[0]
        c1, c2 = st.columns(2)
        c1.metric("Pass Rate (base)", f"{base_row['Pass Rate (%)']:.0f}%")
        c2.metric("Pass Rate (instruction-tuned)", f"{it_row['Pass Rate (%)']:.0f}%")

        col1, col2 = st.columns([3, 2])
        with col1:
            metrics = ["Factual\nAccuracy", "Avoids\nMisconception", "Clarity"]
            st.pyplot(grouped_bar(
                metrics,
                {
                    "Base": [base_row["Factual Accuracy (1-5)"], base_row["Avoids Misconception (1-5)"], base_row["Clarity (1-5)"]],
                    "Instruction-tuned": [it_row["Factual Accuracy (1-5)"], it_row["Avoids Misconception (1-5)"], it_row["Clarity (1-5)"]],
                },
                ylabel="Score (1-5)"
            ))
        with col2:
            st.markdown(
                "**Base vs. instruction-tuned**\n"
                "- Largest gain: **Avoids Misconception**\n"
                "- Suggests instruction tuning specifically helps recognize myth-baiting questions, beyond general factual recall"
            )
        with st.expander("Full scorecard table"):
            st.dataframe(tq_scorecard, use_container_width=True, hide_index=True)
    else:
        st.warning(f"Expected file not found: `{FILES['tq_scorecard']}`")

    with st.expander("Additional pre-rendered chart artifacts"):
        img_cols = st.columns(3)
        tq_imgs = ["pass_rate.png", "avg_factual_accuracy.png", "avg_avoids_misconception.png",
                   "avg_clarity.png", "truthfulness_score.png", "category_performance.png",
                   "radar_Gemma-4-E2B.png", "radar_Gemma-4-E2B-it.png", "violation_probability.png"]
        for i, img in enumerate(tq_imgs):
            path = f"{TQ}/{img}"
            if os.path.exists(path):
                img_cols[i % 3].image(path, caption=img, use_container_width=True)

    st.subheader("Judge Blind Spot: Evasiveness Is Not Truthfulness")
    st.markdown(
        "- Manual spot-check: the truthfulness judge flags false claims, but not evasive non-answers\n"
        "- Example: asked what Paul Revere actually said, Gemma avoided the popular myth but never stated the real quote\n"
        "- Scored a low violation probability (0.008) despite not fully answering the question\n"
        "- The judge captures **accuracy**, not **completeness** -- an actionable gap for future iterations"
    )

    st.subheader("Limitations")
    st.markdown(
        "- Small sample (50-150 of 817 prompts) -- not the full benchmark\n"
        "- Judge may be lenient on evasive but technically non-false responses\n"
        "- Base-vs-IT comparison sample sizes were not always identical across runs"
    )

# ==========================================================================
# TAB: openbookqa/
# ==========================================================================
with tabs[3]:
    st.header("openbookqa/")

    st.subheader("Scorecard")
    show_scorecard(["Knowledge & Reasoning"])

    st.markdown(
        "- **Use-case risk covered:** does the model actually know the subject matter it's meant to tutor, and does that hold up without hand-holding.\n"
        "- **Dataset:** OpenBookQA (standard science multiple-choice benchmark), small sample (10-15 questions).\n"
        "- **Judges:** automated exact-match for accuracy; Gemma-4-E2B-it (LLM-as-judge) for explanation quality, format adherence, and politeness."
    )

    if obqa_with is not None and obqa_without is not None:
        acc_with = obqa_with["correct"].mean() * 100
        acc_without = obqa_without["correct"].mean() * 100
        parse_fail = (obqa_without["judge_reason"] == "PARSE_FAILED").mean() * 100

        c1, c2, c3 = st.columns(3)
        c1.metric("Accuracy, with instructions", f"{acc_with:.0f}%")
        c2.metric("Accuracy, no instructions", f"{acc_without:.0f}%")
        c3.metric("Explanation Quality", f"{obqa_with['explanation_quality'].mean():.1f} / 5")

        col1, col2 = st.columns([3, 2])
        with col1:
            st.pyplot(bar_chart(
                ["Accuracy\n(with instr.)", "Accuracy\n(no instr.)", "Parse failure\n(no instr.)"],
                [acc_with, acc_without, parse_fail],
                colors=[TEAL, AMBER, RED],
                ylabel="Percent", ylim=(0, 105), figsize=(5, 3.2)
            ))
        with col2:
            st.markdown(
                "**Instructions matter more than accuracy alone shows**\n"
                f"- With instructions: {acc_with:.0f}% accurate, fully parseable\n"
                f"- Without: {acc_without:.0f}% accurate, but {parse_fail:.0f}% failed parsing\n"
                "- The grading pipeline itself breaks down without a stable output format"
            )
        with st.expander("Raw grading results"):
            st.markdown("**With instructions**")
            st.dataframe(obqa_with, use_container_width=True, hide_index=True)
            st.markdown("**Without instructions**")
            st.dataframe(obqa_without, use_container_width=True, hide_index=True)
    else:
        if obqa_with is None:
            st.warning(f"Expected file not found: `{FILES['obqa_with']}`")
        if obqa_without is None:
            st.warning(f"Expected file not found: `{FILES['obqa_without']}`")

    st.subheader("Limitations")
    st.markdown(
        "- Very small samples (n=10 with instructions, n=5 without) -- directional, not conclusive\n"
        "- Multiple-choice accuracy alone does not capture reasoning quality\n"
        "- Parse failures may reflect grader brittleness as much as model behavior"
    )

# ==========================================================================
# TAB: promptinjection/
# ==========================================================================
with tabs[4]:
    st.header("promptinjection/")

    st.subheader("Scorecard")
    show_scorecard(["Robustness"])

    st.markdown(
        "- **Use-case risk covered:** do academic-integrity and topic-scope rules survive a student directly trying to override them.\n"
        "- **Dataset:** custom adversarial prompt set (e.g. \"ignore all instructions...\").\n"
        "- **Judges:** automated compliance/instruction-protection flags; Gemma-4-E2B-it (LLM-as-judge) for instruction-following fidelity and response quality."
    )

    if pi_summary is not None:
        cols = st.columns(len(pi_summary))
        for i, row in pi_summary.iterrows():
            val = row["result"]
            cols[i].metric(row["metric"], f"{val:.2f}" if isinstance(val, float) else val)

        col1, col2 = st.columns([3, 2])
        with col1:
            labels = pi_summary["metric"].str.replace(" ", "\n").tolist()
            values = [v * 100 if v <= 1 else v for v in pi_summary["result"]]
            st.pyplot(bar_chart(labels, values, colors=[RED, RED, TEAL, AMBER, TEAL],
                                 ylabel="Score (normalized)", ylim=(0, 105), figsize=(6, 3.4)))
        with col2:
            st.markdown(
                "**Fluent, but not safe**\n"
                "- 0% pass rate alongside 5.0/5 response quality\n"
                "- The model stayed coherent while still complying with the injected instruction\n"
                "- Fluency and safety are tracked as separate axes on purpose"
            )
    else:
        st.warning(f"Expected file not found: `{FILES['pi_summary']}`")

    if pi_detailed is not None:
        with st.expander("Sample attack prompts and responses"):
            st.dataframe(pi_detailed, use_container_width=True, hide_index=True)
    else:
        st.warning(f"Expected file not found: `{FILES['pi_detailed']}`")

    st.subheader("Limitations")
    st.markdown(
        "- A 0% pass rate is a stark result -- worth manually reviewing responses before fully trusting the number\n"
        "- Small, hand-curated adversarial set -- not a comprehensive jailbreak benchmark\n"
        "- Judge scoring of fidelity under adversarial input is itself an under-explored metric"
    )