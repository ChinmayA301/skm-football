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

1. Decroos, T., Bransen, L., Van Haaren, J., & Davis, J. (2019). Actions speak louder than goals: Valuing player actions in soccer. *KDD*.
2. Singh, A. (2019). Introducing Expected Threat (xT). [socceraction xT docs](https://socceraction.readthedocs.io/)
3. StatsBomb Open Data — [user agreement](https://github.com/statsbomb/open-data)

## Limitations (state in any publication)

- StatsBomb open sample: 34 Bundesliga 2023/24 matches (not full season).
- Minutes estimated from action counts.
- VAEP model differs from paper (sklearn vs boosted trees).
- Public ratings are not ground truth.

## Future work

SKM v1 is an action-level proxy (**SKM-Chance**). The target metric credits players for **match moments** and rolls up to one `skm_per90`. See [ROADMAP.md](ROADMAP.md) for Phases 5–8 (moment segmentation, chance + control layers, unified SKM, context, AI).
