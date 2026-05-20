"""SKM Explorer — Streamlit dashboard."""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="SKM Explorer", layout="wide")

st.title("SKM — Skill-Key Moments")
st.caption("Chain-reaction action valuation on StatsBomb open data")

try:
    from skm.viz.loaders import DataNotFoundError, load_all
    from skm.viz.hidden_heroes import hidden_heroes_table, role_fairness_by_type
    from skm.viz.timeline import list_match_ids, match_timeline_data
    from skm.viz.player_profile import player_component_summary, list_players
    from skm.viz.validation import (
        build_validation_table,
        merge_external_benchmarks,
        tier1_correlations,
        tier2_correlations,
    )
except ImportError as exc:
    st.error(f"Install dependencies: pip install -e '.[app,model]' — {exc}")
    st.stop()

try:
    actions, events, board = load_all()
except DataNotFoundError as exc:
    st.warning(str(exc))
    st.code(
        "skm-build-events\npip install -e '.[model]'\nskm-build-scores",
        language="bash",
    )
    st.stop()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Leaderboard", "Match timeline", "Player profile", "Hidden influence", "Validation"]
)

with tab1:
    st.subheader("Player leaderboard")
    min_actions = st.slider("Minimum actions", 100, 800, 400, 50)
    show = board[board["n_actions"] >= min_actions] if "n_actions" in board.columns else board
    metric = st.selectbox("Sort by", ["skm_per90", "delta_p_per90", "xt_per90"])
    show = show.sort_values(metric, ascending=False)
    st.dataframe(
        show[
            [c for c in ["player", "player_id", "skm_per90", "delta_p_per90", "xt_per90", "n_actions"] if c in show.columns]
        ].head(50),
        use_container_width=True,
    )

with tab2:
    st.subheader("Cumulative SKM by match")
    match_ids = list_match_ids(actions)
    mid = st.selectbox("Match", match_ids, format_func=lambda x: f"Game {x}")
    if mid:
        import plotly.express as px

        team_cum, goals = match_timeline_data(mid, actions)
        fig = px.line(
            team_cum,
            x="minute",
            y="skm_cum",
            color="team_id",
            title=f"Match {mid}",
        )
        for _, g in goals.iterrows():
            fig.add_vline(x=g["minute"], line_dash="dash", opacity=0.4)
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Player component breakdown")
    players = list_players(actions)
    labels = players.apply(
        lambda r: f"{r.get('player', r['player_id'])} ({int(r['player_id'])})",
        axis=1,
    )
    idx = st.selectbox("Player", range(len(players)), format_func=lambda i: labels.iloc[i])
    pid = int(players.iloc[idx]["player_id"])
    prof = player_component_summary(pid, actions)
    st.dataframe(prof, use_container_width=True)
    if len(prof):
        row = prof.iloc[0]
        import plotly.graph_objects as go

        fig = go.Figure(
            data=go.Scatterpolar(
                r=[row["D_mean"], row["C_mean"], row["R_mean"]],
                theta=["Difficulty (D)", "Context (C)", "Role (R)"],
                fill="toself",
            )
        )
        fig.update_layout(title=f"Mean components — player {pid}")
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Hidden influence (SKM vs xT rank)")
    heroes = hidden_heroes_table(board, actions, events, top_n=30)
    st.dataframe(heroes, use_container_width=True)
    st.caption("Higher skm_minus_xt_rank = ranked better by SKM than by xT.")

    st.subheader("SKM by action type (role fairness)")
    fairness = role_fairness_by_type(actions)
    st.dataframe(fairness, use_container_width=True)

with tab5:
    st.subheader("Validation — SKM vs benchmarks")
    min_val = st.slider("Min actions (validation)", 100, 800, 400, 50, key="val_min")
    val_df = build_validation_table(board, events, min_actions=min_val)
    val_ext = merge_external_benchmarks(val_df)

    st.markdown("**Tier 1** — SKM vs ΔP / xT (Spearman ρ)")
    rho1, _ = tier1_correlations(val_df)
    st.dataframe(rho1.style.format("{:.3f}"), use_container_width=True)

    st.markdown("**Tier 2** — SKM vs outcomes (goals, assists, xG, progressive)")
    rho2, _ = tier2_correlations(val_df)
    st.dataframe(rho2.style.format("{:.3f}"), use_container_width=True)

    st.markdown("**Merged table** (top by SKM)")
    show_cols = [
        c
        for c in [
            "player",
            "skm_per90",
            "delta_p_per90",
            "xt_per90",
            "goals_per90",
            "xg_per90",
            "goals_plus_xg_per90",
            "skm_minus_outcome_rank",
            "fotmob_rating",
            "fbref_rating",
        ]
        if c in val_ext.columns
    ]
    st.dataframe(val_ext.sort_values("skm_per90", ascending=False)[show_cols].head(30))

    st.caption(
        "Run `skm-validate` for CSV exports. Fill `data/external/bundesliga_2324_benchmarks.csv` for Tier 3."
    )
