# Results

Headline findings, reproducible from this repo on StatsBomb open data
(216 matches: Bundesliga 23/24, World Cup 2022, Euro 2024, Ligue 1 22/23,
La Liga 20/21 — 487,561 scored actions, 233 players with ≥400 actions).

## The headline: SKM measures position competence, not attacking intent

The founding thesis was to reward **position-specific competence and match
context**, not goals+assists. v1–v3 (below) are the value-construction
pipeline; **v4 competence is the metric that finally delivers the thesis**,
and **v5 layers decisive-action + match context on top of it**.

| Layer | Role | Headline result |
|---|---|---|
| **v4 — Competence** | **BASE** | Each action scored vs positional-peer expectation for that type. **ρ(competence, goals+assists) = −0.01** — fully decoupled from output. Surfaces Van Dijk, Rüdiger, Kanté with *zero* goals; top-40 is 16 defenders vs G+A's 8. |
| **v5 — Contextual** | on v4 | Context-weighted decisive actions (low-xG & comeback/late/knockout weighted up) + press-breaking + match importance (opponent strength × competition stage). ρ(v5, goals) = −0.07 — decisive rewarded *within context*, not by tally. |

See "Position competence vs traditional metrics" below for the full comparison.

## The value pipeline underneath (v1–v3)

| Version | Formula | What it adds |
|---|---|---|
| **v1 — SKM-Chance** | `ΔP × (1 + 0.3·D + 0.3·C + 0.3·R)` | Action-level value beyond outcomes: difficulty, context, role |
| **v1.5 — Adjusted SKM** | `× position_w × role_w × game_state_w × sequence_w` | Modest, disclosed priors for position fit, leverage, and chain credit |
| **v2 — Moment credits** | `α·own_value + (1−α)·share·moment_value` | Rolls actions into ~68k moments; shares credit across involved players |
| **v3 — Position-normalized** | z-score of v2 within primary position group | Compares players to positional peers, not the whole league |

## Validation targets

The project set two falsifiable targets before running any position-level fix:

| Target | v1 | v2 | v3 | Met? |
|---|---|---|---|---|
| ρ(SKM, ΔP) < 0.99 (not a VAEP clone) | 0.996 | 0.959 | **0.868** | ✅ |
| ρ(SKM, progressive actions/90) > 0 (doesn't punish structural work) | −0.13 | −0.21 | **+0.06** | ✅ |

v2 alone did not pass the second target — moment-sharing by touch share
initially made it *worse* by channeling value toward attackers present in
shot-ending moments. The fix wasn't a tuned parameter; it was pre-registered:
compare players within their position group. v3's correlation is barely
positive, stated honestly rather than inflated, but the sign flip is real
and the position leaders are face-valid: ball-playing centre-backs
(Young-Gwon Kim, Koulibaly, Orban), Remo Freuler at DM, Yann Sommer at GK.

**But v3 wasn't enough** — tested on the full 2015/16 Premier League, it
still buried N'Golo Kanté (v1 #151 → v3 #93), because position-normalization
re-ranks an offense-skewed value; it can't manufacture the defensive value
the base signal never measured. That failure is what motivated v4.

## Position competence vs traditional metrics

v4 competence scores each action against what a positional peer does with
that action type. On the 216-match sample it is genuinely decoupled from
output, and surfaces the role-competent defenders and ball-winners that
outcome metrics miss:

| Competence vs… | Spearman ρ |
|---|---|
| Goals + Assists /90 | **−0.01** |
| Assists /90 | −0.05 |
| xG /90 | +0.10 |
| Progressive actions /90 | +0.03 |
| VAEP ΔP /90 | +0.48 |
| SKM v1 /90 | +0.47 |

**Who each metric's top-40 rewards** (position mix):

| Metric | Attackers (W+ST) | Defenders (CB+FB) | Midfield |
|---|---|---|---|
| Goals + Assists | 28 | 8 (0 CM/DM) | 4 |
| VAEP ΔP | 18 | 11 | 8 |
| **Competence (v4)** | **10** | **16** | **10** |

The "uncovered" players — high competence, **zero** goals+assists — are
Van Dijk, Rüdiger, Min-jae Kim, Kanté, Kovačić, Højbjerg, Amrabat, Schär:
centre-backs and ball-winning midfielders ranked 17th–80th by competence and
dead-last (183rd) by output. On the same PL 2015/16 that buried Kanté in v3,
competence lifts him to **#24**.

**Honest caveats:** the very top-10 is still winger-heavy (elite dribblers
score high vs winger peers — but with ρ(goals)≈0 it's competence, not intent);
competence still correlates 0.48 with VAEP (a role-relative lens *on*
possession value); goalkeepers rank via distribution. It is not claimed to
beat VAEP/xT on any task — it answers a different question (role competence).

v3 is dimensionless (peer-relative) by design — cross-position magnitude
comparisons should use v2.

## Real video intelligence: does defender geometry matter?

StatsBomb 360 freeze-frames give real player positions extracted from
broadcast video at each event — not a hypothesis, a measurement. Refitting
the difficulty model with real defender distances instead of a binary
"under pressure" flag:

| Difficulty model | Held-out AUC (42 unseen matches) |
|---|---|
| Event-only (pressure flag, location, distance) | 0.690 |
| **+ 360 defender geometry** | **0.829** |

Propagating that improved difficulty through the full metric shifts rankings
in a specific direction: congestion midfielders who execute under real
pressure rise (Schick, Gündoğan, Mac Allister, Rodri), while wide players
who receive passes in space fall (Doku, Carrasco, Ziyech). The event-only
model had been systematically over-crediting touchline space.

## A metric-auditing example

Every rebuild is a chance to find bugs, not just tune numbers. One real one:
StatsBomb's open data includes penalty shootouts as a fifth match period,
but VAEP's "does this improve scoring probability over the next *k*
actions" framing is undefined there — no future actions exist after a
shootout kick. Before this was caught, the pipeline assigned roughly **−3.7
SKM to a scored shootout penalty**, docking Ronaldo and Messi for winning
shootouts. Shootout actions are now excluded from scoring; the fix is one
line and disclosed here rather than quietly patched.

## Worked example

[docs/WORKED_EXAMPLE.md](WORKED_EXAMPLE.md) walks one real action —
a Kondogbia pass under pressure in the 78th minute of a tied La Liga
match — through every component of the v1 formula, and contrasts it with
a routine pass carrying nearly identical raw ΔP.

## What's still open

- **v3's progressive correlation is barely positive** (+0.06), not strongly
  so. The next lever is moment-type value weighting, not more tuning.
- **Expert-preference calibration** is scaffolded (Bradley-Terry reward
  model over pairwise moment judgments) but unfit — it needs real labeled
  comparisons, which only a human annotator can produce.
- **Off-ball involvement** (pressing, decoy runs) isn't credited yet;
  StatsBomb 360 only samples positions at event time, not continuously.
- **The open sample mixes club and tournament contexts** — no knockout-stage
  weighting yet, and Tier 3 external benchmark coverage (FotMob ratings) is
  limited to the Bundesliga slice.

See [SKM_MARKET_POSITIONING.md](SKM_MARKET_POSITIONING.md) for what SKM
does and doesn't claim, and [CASE_STUDIES.md](CASE_STUDIES.md) for
player-level narratives.
