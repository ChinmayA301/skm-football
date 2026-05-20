# Example player narratives

Illustrative comparisons from the **StatsBomb open Bundesliga 2023/24 sample** (34 matches). Ranks are approximate on that sample—not full-season minutes or fixtures. FotMob figures are season benchmarks from `data/external/bundesliga_2324_benchmarks.csv`.

Regenerate disagreement tables: `skm-validate` → `data/reports/validation_disagreements.csv`.

---

## Elite SKM and strong outcomes

Players who score well on both process (SKM) and box-score outcomes.

| Player | SKM (sample) | Outcomes (sample) | Notes |
|--------|--------------|-------------------|-------|
| Florian Wirtz | Top tier | Top tier | High ΔP and strong creation; FotMob ~7.73 (full season) |
| Alejandro Grimaldo | Top tier | Top tier | Attacking full-back profile; FotMob ~7.98 (full season) |

---

## High SKM, modest public rating (“hidden influence”)

Supports the idea that chain value can exceed reputation or headline G+A on a per-action basis.

| Player | SKM (sample) | Outcomes (sample) | Notes |
|--------|--------------|-------------------|-------|
| Nathan Tella | Very high | Moderate | Top SKM per90 on sample; FotMob ~7.13 |
| Victor Okoh Boniface | Very high | Moderate | Strong SKM; 14G/8A season context; FotMob ~7.16 |

---

## High box score, moderate SKM

Finisher / outcome-led profiles where SKM is not dominated by goals alone.

| Player | SKM (sample) | Outcomes (sample) | Notes |
|--------|--------------|-------------------|-------|
| Harry Kane | Moderate | Elite | 36 goals BL 23/24; anchor for “market knows outcomes” |

---

## SKM vs public rating disagreement

Cases that motivate moment-based v2 (structural / midfield work vs attack-leaning ΔP sum).

| Player | SKM (sample) | FotMob BL 23/24 | Notes |
|--------|--------------|-----------------|-------|
| Granit Xhaka | Lower on v1 | ~8.18 | Elite public rating; v1 underrates structural midfield impact |
| Exequiel Palacios | — | ~8.05 | League-top FotMob rating; compare when matched on sample minutes |

---

## Same team, same position

Use the leaderboard to compare teammates in the same role (e.g. two central midfielders on one club) after running the full pipeline.
