"""SKM Explorer — Streamlit dashboard."""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="SKM Explorer", layout="wide")

st.title("SKM — Skill-Key Moments")
st.caption("Chain-reaction action valuation on StatsBomb open data")

try:
    from skm.viz.loaders import DataNotFoundError, load_all, player_name_map
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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Leaderboard",
        "Match timeline",
        "Player profile",
        "Hidden influence",
        "Validation",
        "Moments",
    ]
)

# Fixed categorical colors per moment type (validated palette; identity never cycles)
MOMENT_COLORS = {"open_play": "#2a78d6", "transition": "#1baf7a", "set_piece": "#eda100"}

with tab1:
    st.subheader("Player leaderboard")
    min_actions = st.slider("Minimum actions", 100, 800, 400, 50)
    show = board[board["n_actions"] >= min_actions] if "n_actions" in board.columns else board
    metric_options = [
        m
        for m in ["skm_per90", "adjusted_skm_per90", "delta_p_per90", "xt_per90"]
        if m in show.columns
    ]
    metric = st.selectbox("Sort by", metric_options)
    show = show.sort_values(metric, ascending=False)
    st.dataframe(
        show[
            [
                c
                for c in [
                    "player",
                    "player_id",
                    "skm_per90",
                    "adjusted_skm_per90",
                    "delta_p_per90",
                    "xt_per90",
                    "n_actions",
                ]
                if c in show.columns
            ]
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

with tab6:
    st.subheader("Moments (Phase 5/5b)")
    try:
        from skm.viz.loaders import load_moments, load_v2_board

        moments = load_moments()
    except DataNotFoundError as exc:
        st.warning(str(exc))
        st.stop()

    import plotly.express as px

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Moments", f"{len(moments):,}")
    c2.metric("Contain a shot", f"{moments['contains_shot'].mean():.1%}")
    c3.metric("Transitions", f"{(moments['moment_type'] == 'transition').mean():.1%}")
    c4.metric("Median actions", f"{moments['n_actions'].median():.0f}")

    st.markdown("**Moment map** — one dot per moment; height = summed SKM value")
    mid6 = st.selectbox(
        "Match", sorted(moments["game_id"].unique()), format_func=lambda x: f"Game {x}", key="m6"
    )
    mm = moments[moments["game_id"] == mid6].copy()
    mm["team"] = mm["team_id"].astype(str)
    fig = px.scatter(
        mm,
        x="start_minute",
        y="skm_sum",
        color="moment_type",
        color_discrete_map=MOMENT_COLORS,
        symbol="contains_shot",
        symbol_map={False: "circle", True: "diamond"},
        hover_data=["moment_id", "team", "n_actions", "score_diff_start", "start_reason"],
        labels={"start_minute": "Minute", "skm_sum": "Moment SKM value"},
    )
    fig.update_traces(marker={"size": 9, "line": {"width": 1, "color": "#fcfcfb"}})
    fig.update_layout(legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Diamonds = moments containing a shot.")

    st.markdown("**Top moments in this match**")
    top_cols = [
        "moment_id",
        "start_minute",
        "moment_type",
        "team",
        "n_actions",
        "skm_sum",
        "score_diff_start",
        "contains_shot",
        "contains_goal",
    ]
    st.dataframe(
        mm.sort_values("skm_sum", ascending=False)[top_cols].head(12),
        use_container_width=True,
    )

    st.markdown("**v1 vs v2 (moment credits)** — players off the diagonal move under moment sharing")
    try:
        board_v2 = load_v2_board()
        names = player_name_map(events)
        board_v2["player"] = board_v2["player_id"].map(names)
        fig2 = px.scatter(
            board_v2,
            x="skm_v1_per90",
            y="skm_v2_per90",
            hover_data=["player", "progressive_per90", "n_actions"],
            labels={"skm_v1_per90": "SKM v1 per 90", "skm_v2_per90": "SKM v2 per 90"},
        )
        fig2.update_traces(marker={"size": 9, "color": "#2a78d6"})
        lim = [
            min(board_v2["skm_v1_per90"].min(), board_v2["skm_v2_per90"].min()),
            max(board_v2["skm_v1_per90"].max(), board_v2["skm_v2_per90"].max()),
        ]
        fig2.add_shape(
            type="line", x0=lim[0], y0=lim[0], x1=lim[1], y1=lim[1],
            line={"dash": "dot", "color": "#52514e", "width": 1},
        )
        st.plotly_chart(fig2, use_container_width=True)

        board_v2["rank_v1"] = board_v2["skm_v1_per90"].rank(ascending=False)
        board_v2["rank_v2"] = board_v2["skm_v2_per90"].rank(ascending=False)
        board_v2["rank_change"] = board_v2["rank_v1"] - board_v2["rank_v2"]
        st.markdown("**Biggest movers (v1 → v2 rank)**")
        st.dataframe(
            board_v2.sort_values("rank_change", ascending=False)[
                ["player", "rank_v1", "rank_v2", "rank_change", "skm_v1_per90", "skm_v2_per90"]
            ].head(10),
            use_container_width=True,
        )
    except DataNotFoundError as exc:
        st.info(f"{exc} — v1 vs v2 comparison hidden until credits are built.")
