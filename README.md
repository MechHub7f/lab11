# Lab 11 - Analyze NYC 311 Calls

Analysis of New York City's November 2025 311 service requests for
CS 2010, Lab 11.

The full write-up is in [`report.md`](report.md). The reproducible
analysis is in [`analysis.py`](analysis.py); it reads the data, prints the
two-way verification numbers, and writes the figures in `figures/`.

## Data

Download the compressed extract (39 MB) and put it in `data/`:

```bash
mkdir -p data
curl -o data/nyc-311-2025-november.csv.gz \
  https://files.homework.quest/cs2010/nyc-311-2025-november.csv.gz
```

The data is not committed. `.gitignore` keeps `data/` and all CSV files
out of the repository.

## Run

```bash
python3 -m pip install -r requirements.txt
CENSUS_API_KEY=your_key_here python3 analysis.py
```

The Census key is used only for the Task 3 population lookup. It is read
from the environment and is never written to the repository. If it is
missing, the script falls back to the published 2020 Census county totals
and says so in its output.

Output:

- `fig-borough-bronx.png` - Bronx top 10 complaint types
- `fig-borough-per1000.png` - complaints per 1,000 residents
- `fig-hours.png` - noise vs. heat by hour of day
- `fig-nights.png` - day x hour heat map for noise
- `fig-same-job.png` - HEAT/HOT WATER median hours by borough
