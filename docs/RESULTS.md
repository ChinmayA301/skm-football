# Results

Headline findings, reproducible from this repo on StatsBomb open data
(216 matches: Bundesliga 23/24, World Cup 2022, Euro 2024, Ligue 1 22/23,
La Liga 20/21 — 487,561 scored actions, 233 players with ≥400 actions).

## The metric stack

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
