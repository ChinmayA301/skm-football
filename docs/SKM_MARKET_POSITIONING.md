# SKM vs market stats — positioning

Use this when writing the blog, README, or talking to scouts. **SKM v1 is not claiming to replace the transfer market.**

---

## One-line pitch (v1)

> Open pipeline that values **every on-ball action** with VAEP plus difficulty, context, and role—built to evolve into a **moment-based** brain metric.

## One-line pitch (target v2)

> SKM finds players who repeatedly show up in **match-winning phases** in ways goals and assists miss.

## Do not claim

- “SKM replaces scouting”
- “Predicts transfer fees better than clubs”
- “Measures youth potential” (without SKM-trend + age + tracking)
- “Full off-ball genius” (until Phase 7–8)

---

## What the market actually uses

| Layer | Examples | Optimizes |
|-------|----------|-----------|
| Box score | Goals, assists | Outcomes, visibility |
| Advanced offense | xG, xA, shots | Chance volume |
| Public ratings | FotMob, WhoScored | Outcomes + reputation + minutes |
| Club models | Tracking, wages, scouts | Multivariate + private data |
| Potential | Age, trajectory, physical | **Future**, not one season of process |

SKM targets the **process gap** in the first three rows.

---

## Where SKM can be better (after moment-based v2)

| Use case | Why |
|----------|-----|
| Hidden influence players | High process, modest G+A (e.g. high SKM, ~7.1 FotMob) |
| Role-fair comparison | Unusual valuable actions for profile boosted |
| Match-relative quality | Same player, different games |
| Anti-stat-padding | Tune away from ρ ≈ 0.9 with goals+xG |
| Scout narrative | Moment clips with allocated credit |

## Where the market stays ahead

| Use case | Why |
|----------|-----|
| Transfer fee / wage | Age, contract, hype, medical, seller |
| Youth potential | Trajectory, physical, psychology |
| Elite finishers | xG + goals remain best simple signal |
| Silent off-ball | Needs tracking or AI (Phase 8) |
| Cross-league shopping | Multi-year, multi-league club models |

---

## Ability vs potential

| Term | SKM fit |
|------|---------|
| **Current ability** (on-pitch process) | Good fit after Phase 6 **if** validation passes |
| **Potential** | Poor fit alone → future **SKM-trend** product |

---

## Illustrative v1 disagreement (Bundesliga 23/24 sample)

FotMob ratings from public sources; SKM ranks from project leaderboard on StatsBomb open sample. **Not same minutes or fixtures**—use as narrative only.

| Player | SKM v1 story | FotMob BL 23/24 (approx.) |
|--------|--------------|---------------------------|
| Nathan Tella / Victor Boniface | Top SKM per90 | ~7.13–7.16 |
| Florian Wirtz / Alejandro Grimaldo | Strong SKM | ~7.73–7.98 |
| Granit Xhaka | Lower SKM per90 | **~8.18** (elite public rating) |

Xhaka is the archetype for **why v2 adds moment + control layers**: reputation and structural midfield work vs attack-leaning ΔP sum.

---

## Validation we publish (v1)

From `skm-validate` on the open sample (reproduce locally):

| Correlation (Spearman) | Approx. |
|------------------------|---------|
| SKM vs ΔP | ~0.996 |
| SKM vs xT | ~0.83 |
| SKM vs assists | ~0.47 |
| SKM vs xG | ~0.25 |
| SKM vs progressive per90 | **~−0.11** |

Tier 3: merge [`data/external/bundesliga_2324_benchmarks.csv`](../data/external/bundesliga_2324_benchmarks.csv) for FotMob comparison.

---

## References for blog

- [ROADMAP.md](ROADMAP.md) — phases
- [RELATED_WORK.md](RELATED_WORK.md) — VAEP, xT
- [CASE_STUDIES.md](CASE_STUDIES.md) — player buckets
