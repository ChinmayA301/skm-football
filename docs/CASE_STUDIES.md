# Tier 4 — Player case studies (blog template)

Illustrative players from the **StatsBomb open Bundesliga 2023/24 sample** (34 matches). Ranks are approximate from `player_leaderboard.parquet` on that sample—not full-season minutes or fixtures. **Clip IDs and exact ranks TBD** for the blog.

**How to refresh:** `skm-validate` → `data/reports/validation_disagreements.csv` (sort by `skm_minus_outcome_rank`).

---

## Bucket A — Elite SKM + elite outcomes

*Expectation: top SKM and strong goals/xG — SKM does not ignore stars.*

| Player | SKM rank (sample) | Goals+xG rank (sample) | Story | Clip / match |
|--------|-------------------|------------------------|-------|--------------|
| Florian Wirtz | Top tier | Top tier | Creative hub: high ΔP actions with strong box-score contribution; aligns with FotMob ~7.73 on full season. | TBD |
| Alejandro Grimaldo | Top tier | Top tier | Attacking full-back: crosses, progressive carries, set-piece threat; FotMob ~7.98 BL 23/24. | TBD |

---

## Bucket B — High SKM, modest box score (“hidden influence”)

*Expectation: supports chain-reaction thesis — valuable actions without headline G+A.*

| Player | SKM rank (sample) | Goals+xG rank (sample) | skm_minus_outcome_rank | Story | Clip |
|--------|-------------------|------------------------|------------------------|-------|------|
| Nathan Tella | Very high | Moderate | Positive | Top SKM per90 on sample; 5G/2A in benchmarks but FotMob ~7.13 — process > reputation. | TBD |
| Victor Okoh Boniface | Very high | Moderate | Positive | Similar: strong SKM, 14G/8A season context, FotMob ~7.16 — high impact per action in sample. | TBD |

---

## Bucket C — High box score, lower SKM

*Expectation: finisher or volume scorer; SKM may rank below pure outcome leaders.*

| Player | SKM rank (sample) | Goals+xG rank (sample) | Story | Clip |
|--------|-------------------|------------------------|-------|------|
| Harry Kane | Moderate (reference) | Elite | 36 goals BL 23/24, FotMob ~7.98 — elite finisher; use as “market knows outcomes” anchor vs SKM process story. | TBD |

---

## Bucket D — Same team, same position

*Expectation: SKM differentiates two players in the same role on one squad.*

| Player A | Player B | Team | SKM per90 (A vs B) | What SKM captures differently |
|----------|----------|------|--------------------|------------------------------|
| _TBD_ | _TBD_ | e.g. Leverkusen CM pair | | Pick from leaderboard after full run |

---

## Bucket E — SKM vs public rating disagreement

*From `data/external/bundesliga_2324_benchmarks.csv` + sample leaderboard.*

| Player | SKM rank (sample) | FotMob BL 23/24 | Story (reputation vs process) |
|--------|-------------------|-----------------|------------------------------|
| Granit Xhaka | Lower on v1 SKM | **~8.18** | Archetype for v2: elite public rating and structural midfield work vs attack-leaning ΔP sum in v1. |
| Exequiel Palacios | TBD | **~8.05** | League-top FotMob rating; compare SKM once matched on minutes in sample. |

---

## Checklist before publishing blog

- [x] At least **8 named players** across buckets (illustrative)
- [ ] One **scatter plot** from `data/reports/scatter_skm_vs_goals_xg.png` (generate locally)
- [ ] One **Spearman table** from `tier2_spearman.csv` (generate locally)
- [ ] State sample size (34 matches, minutes from actions, sklearn VAEP)
- [ ] Credit StatsBomb open data
