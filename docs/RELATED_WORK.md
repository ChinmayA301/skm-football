# Related Work — SKM and action-value frameworks

SKM sits in a line of **process-based** football metrics that value every on-ball action, not only goals and assists.

## VAEP (Valuing Actions by Estimating Probabilities)

- **Authors:** Decroos et al. (2019), [socceraction](https://github.com/ML-KULeuven/socceraction)
- **Idea:** Train classifiers for scoring/conceding within the next *k* actions; action value = change in those probabilities (ΔP).
- **SKM use:** ΔP is the backbone (`delta_p` / VAEP). This repo uses a **sklearn GradientBoosting** fallback when XGBoost/LightGBM are unavailable (no OpenMP on Mac without Homebrew).

## Expected Threat (xT)

- **Idea:** Grid-based pass/carry value toward goal.
- **SKM use:** `xt_value` column and **hidden influence** tab — players ranked higher by SKM than by xT illustrate chain value beyond ball progression grids.

## Other frameworks (positioning for blog)

| Framework | Focus | vs SKM |
|-----------|--------|--------|
| **OBV** (StatsBomb) | On-ball value, proprietary | Black-box; SKM is open and decomposed |
| **DxT** (2025) | xT + off-ball positioning | Aligned with SKM Layer 3 (tracking); this repo is event-only |
| **xSuccess** (Paul, Klemp & Memmert, 2026) | Completion-probability correction to VAEP | Overlaps SKM's D; SKM applies difficulty in-formula, not post-hoc |
| **xG chain / xG buildup** | Shot-centric chains | SKM is not shot-only |
| **Packing / progressive passes** | Space gained | SKM includes difficulty, context, role weights |
| **Ratings (FotMob, WhoScored)** | Subjective + outcomes | SKM is process-based; compare in Tier 3 validation |

## Decomposition (SKM contribution)

```
SKM_i = ΔP_i × (1 + w_d·D_i + w_c·C_i + w_r·R_i)
```

- **D:** difficulty (completion model)
- **C:** context (minute, scoreline)
- **R:** role unusualness (cluster distance)

## References

1. Decroos, T., Bransen, L., Van Haaren, J., & Davis, J. (2019). Actions speak louder than goals: Valuing player actions in soccer. *KDD '19*.
2. Singh, K. (2019). Introducing Expected Threat (xT). *karun.in/blog* ([socceraction xT docs](https://socceraction.readthedocs.io/))
3. Van Roy, M., Robberechts, P., Decroos, T., & Davis, J. (2020). Valuing on-the-ball actions in soccer: A critical comparison of xT and VAEP. *AAAI Workshop on AI in Team Sports*.
4. Fernández, J., Bornn, L., & Cervone, D. (2019). Decomposing the immeasurable sport: A deep learning expected possession value framework for soccer. *MIT Sloan Sports Analytics Conference*.
5. Paul, Y., Klemp, M., & Memmert, D. (2026). Beyond outcome bias: Incorporating action completion probability and risk-return into soccer evaluation models. *MLSA 2025*.
6. Pleuler, D. (2021). *Soccer Analytics Handbook*. GitHub.
7. StatsBomb Open Data — [user agreement](https://github.com/statsbomb/open-data)

## Limitations (state in any publication)

- StatsBomb open sample: 216 matches across 5 competitions (mixed club and
  tournament contexts, not full seasons).
- Minutes estimated from action counts.
- VAEP model differs from paper (sklearn vs boosted trees).
- Penalty shootouts (period 5) excluded — VAEP labels are undefined there.
- Public ratings are not ground truth.

## Future work

SKM v1 is an action-level proxy (**SKM-Chance**). The target metric credits players for **match moments** and rolls up to one `skm_per90`. See [ROADMAP.md](ROADMAP.md).
