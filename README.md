# CS 2010 Lab 11 — A Month of New York Complaining

**Team #1365:** Dakota Fowler, Justin Theberge Jr, Christian Dow · **Date:** 16 November 2026

Who complains about what in New York City, where, and how fast does the city
answer? We analyze all 304,905 NYC 311 service requests created 1–30 November
2025 and check every headline number a second, independent way.

**The deliverable is [`report.md`](report.md)** — 7 tasks, findings, a
verification table per task, limits, and the LLM-use note.
[`analysis.py`](analysis.py) is the code that produces every number and figure
in it.

## What's here

| Path | What it is |
| --- | --- |
| `report.md` | The write-up and the graded deliverable |
| `analysis.py` | One script, 7 task sections, every number printed twice |
| `figures/` | The 5 figures referenced by the report (committed) |
| `run.sh` | Runs the analysis, loading `CENSUS_API_KEY` from `.env` if present |
| `requirements.txt` | pandas, numpy, matplotlib, requests |
| `data/` | Not committed — see below |

## Requirements

Python 3.9+ and the packages in `requirements.txt` (pandas 2.x).

## Run it

```bash
mkdir -p data
curl -o data/nyc-311-2025-november.csv.gz \
  https://files.homework.quest/cs2010/nyc-311-2025-november.csv.gz
python3 -m pip install -r requirements.txt
./run.sh
```

Takes about **10 seconds**. Tasks 1, 2 and 4–7 need no key and no network.

### Census API key (Task 3a)

The lab requires a real key for the population pull. Sign up free at
<https://api.census.gov/data/key_signup.html>, then keep it **out of git** —
`analysis.py` reads it from the environment only, and `.gitignore` already
excludes `.env`:

```bash
printf 'CENSUS_API_KEY=%s\n' 'your_key_here' > .env   # local only, never committed
./run.sh
```

`run.sh` exports whatever is in `.env` before running. A keyed run prints:

```text
Population source: Census API 2020 PL (P1_001N)
Population sum: 8,804,190 (sanity target ~8.8 million)
```

Without a key the Census API returns an **HTML error page instead of JSON** —
that is the lab's warning, and the script detects it by `Content-Type`, prints
`Census API fallback: ...`, and continues on the published 2020 county totals
so the other six tasks still run. Those published totals are the same numbers
the API returns, so the table and figures are unchanged either way; the source
line in the output is what tells you which path ran.

`DATA_PATH=/path/to.csv.gz` points the script at a copy of the data elsewhere.

## Data

`nyc-311-2025-november.csv.gz` — 39,144,242 bytes compressed, 304,905 rows ×
44 columns, created dates 2025-11-01 00:00:04 through 2025-11-30 23:59:52.

SHA-256: `3b6ed296ea363b07add15f039f38ad43485651a14b300274e628d43dbcbffda0`

`.gitignore` excludes `data/`, all CSV files, and `.env`, so nothing large and
no secret is committed.

## Output

| Figure | Shows | Task |
| --- | --- | --- |
| `fig-borough-bronx.png` | Bronx top 10 complaint types | 2 |
| `fig-borough-per1000.png` | Complaints per 1,000 residents, all boroughs | 3 |
| `fig-hours.png` | Noise vs. heat by hour of day | 4 |
| `fig-nights.png` | Noise, day × hour (30 × 24) heat map | 4 |
| `fig-same-job.png` | HEAT/HOT WATER median hours by borough, fastest first | 6 |

Stdout prints all 7 task sections, each with its second-method check. The same
pairs appear as the "Verification" table at the end of every task in
`report.md`.

## Verification, in brief

| Number | Method A | Method B | Agree |
| --- | --- | --- | --- |
| Rows | `df.shape` → 304,905 | gzip line count − header → 304,905 | ✓ |
| Problem types | `nunique` → 174 | `len(set(...))` → 174 | ✓ |
| Date bounds | pandas `min`/`max` | `datetime.strptime` over all rows | ✓ |
| Rows with no close date | `isna()` → 4,136 | blank-string filter → 4,136 | ✓ |
| Bronx per 1,000 | table → 50.7071 | 74,674 ÷ 1,472,654 × 1,000 | ✓ |
| Noise peak | `value_counts` → 22:00, 3,878 | `numpy.bincount` → same | ✓ |
| Agency medians | pandas groupby | numpy median (max diff 0.0) | ✓ |
| Bronx heat median | groupby → 30.815 h | `statistics.median` → 30.815 h | ✓ |

## Findings

- **Task 1.** 304,905 rows; 4,136 have no `Closed Date`, including 2 marked `Closed`.
- **Task 2.** Bronx: 74,674 complaints, Noise-Residential 29.8% — but 14,361 of
  those come from one address, so heat leads at 27.6% once it is removed.
- **Task 3.** Raw count puts Brooklyn first; per 1,000 residents the Bronx leads
  (50.7 vs. 19.9 on Staten Island).
- **Task 4.** Noise peaks at 22:00, heat at 09:00. Nov 2 at 01:00 is the outlier
  (308 calls) — the hour that daylight saving time repeated.
- **Task 5.** Median close time runs from 1.2 h (NYPD) to 182.5 h (DOB); the
  longest single case took 374.8 days (DPR, Overgrown Tree/Branches).
- **Task 6.** Same job, different borough: 27.7 h on Staten Island vs. 42.8 h in
  Queens — 54% longer for identical work.
- **Task 7.** 78-15 Parsons Blvd, Fresh Meadows: 728 complaints in 30 days,
  629 of them NYPD; verdict "cannot tell from this file alone."

## Limits

- 311 calls are requests, not complainers; one address supplies 14,362 rows and
  skews both borough shares and per-capita rates.
- One month only, and November's heat season starts mid-month.
- Response times drop the 4,136 unclosed cases; 196 rows have
  `Borough = "Unspecified"` and are set aside for the per-capita rates.
- Census denominators are 2020 counts.

## LLM use

Disclosed in full in [`report.md`](report.md#llm-use): what we asked for, the
four things the assistant got wrong, and the check that caught each one.

## Note

`figures/` is committed, so re-running `analysis.py` regenerates those files and
shows as a local diff. That is expected.
