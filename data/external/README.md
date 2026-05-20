# External validation benchmarks

Fill `bundesliga_2324_benchmarks.csv` with season stats from:

- [FBref](https://fbref.com) — Bundesliga 2023-24 player stats
- FotMob / Sofascore — average match rating (optional column)

Columns:

| Column | Description |
|--------|-------------|
| `player_name` | Must match StatsBomb name in `events.parquet` |
| `fbref_rating` | Optional average match rating or composite |
| `fotmob_rating` | Optional FotMob average rating |
| `goals`, `assists`, `minutes` | Season totals for cross-check |

Then run:

```bash
skm-validate
```
