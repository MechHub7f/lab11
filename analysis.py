#!/usr/bin/env python3
"""CS 2010 Lab 11 - Analyze NYC 311 Calls (November 2025).

Run from the repository root:

    CENSUS_API_KEY=... python3 analysis.py

The script reads the gzipped November extract (see DATA_PATH below), prints
the numbers used in report.md, and writes the figures into figures/.

Every headline number is computed a second way in the same block.  The second
method is deliberately different from the first (pandas vs. gzip line count,
set vs. nunique, datetime.strptime vs. pandas, numpy vs. groupby, ...).
"""

from __future__ import annotations

import gzip
import os
import statistics
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

BASE = Path(__file__).resolve().parent
DATA_PATH = Path(
    os.environ.get("DATA_PATH", BASE / "data" / "nyc-311-2025-november.csv.gz")
)
FIG_DIR = BASE / "figures"
FIG_DIR.mkdir(exist_ok=True)

CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "").strip()
CENSUS_URL = "https://api.census.gov/data/2020/dec/pl"

PROBLEM = "Problem (formerly Complaint Type)"
DATE_FMT = "%m/%d/%Y %I:%M:%S %p"

# The five boroughs are five New York counties.  These are the official 2020
# Census PL totals (P1_001N), used only if the API key is missing or the API
# returns its HTML error page instead of JSON.
FALLBACK_POP = {
    "BRONX": 1_472_654,  # Bronx County, FIPS 36005
    "BROOKLYN": 2_736_074,  # Kings County, FIPS 36047
    "MANHATTAN": 1_694_251,  # New York County, FIPS 36061
    "QUEENS": 2_405_464,  # Queens County, FIPS 36081
    "STATEN ISLAND": 495_747,  # Richmond County, FIPS 36085
}
COUNTY_TO_BOROUGH = {
    "005": "BRONX",
    "047": "BROOKLYN",
    "061": "MANHATTAN",
    "081": "QUEENS",
    "085": "STATEN ISLAND",
}

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
    }
)


def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def load_data() -> pd.DataFrame:
    print(f"Reading {DATA_PATH}")
    df = pd.read_csv(DATA_PATH, encoding="latin-1", low_memory=False)
    df.attrs["source_shape"] = df.shape  # 304,905 x 44 before parsed date columns
    df["created"] = pd.to_datetime(
        df["Created Date"], format=DATE_FMT, errors="coerce"
    )
    df["closed"] = pd.to_datetime(df["Closed Date"], format=DATE_FMT, errors="coerce")
    return df


def line_count(path: Path) -> int:
    """Rows in the raw CSV, counted without pandas."""
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="latin-1") as fh:
            return sum(1 for _ in fh) - 1
    with open(path, "r", encoding="latin-1") as fh:
        return sum(1 for _ in fh) - 1


def task1_first_look(df: pd.DataFrame) -> None:
    section("TASK 1 - First look")
    rows, cols = df.attrs.get("source_shape", df.shape)
    print(f"Rows x columns (pandas, raw file): {rows:,} x {cols}")
    print(f"Columns in memory after adding parsed dates: {df.shape[1]}")
    # Second way: count physical lines in the raw file, minus the header.
    raw_rows = line_count(DATA_PATH)
    print(f"Rows (gzip line count minus header): {raw_rows:,}")
    print(f"Row-count match: {rows == raw_rows}")

    distinct = df[PROBLEM].nunique(dropna=True)
    distinct_set = len(set(df[PROBLEM].dropna()))
    print(f"Distinct problem types (nunique): {distinct}")
    print(f"Distinct problem types (set):     {distinct_set}")
    print(f"Distinct-value match: {distinct == distinct_set}")

    print(f"Earliest Created Date (pandas): {df['created'].min()}")
    print(f"Latest   Created Date (pandas): {df['created'].max()}")
    # Second way: parse every raw string with the standard library.
    parsed = [datetime.strptime(value, DATE_FMT) for value in df["Created Date"]]
    print(f"Earliest Created Date (datetime.strptime): {min(parsed)}")
    print(f"Latest   Created Date (datetime.strptime): {max(parsed)}")
    print(
        "Created-date match: "
        f"{df['created'].min() == min(parsed) and df['created'].max() == max(parsed)}"
    )

    open_mask = df["Closed Date"].isna()
    open_second = df["Closed Date"].fillna("").astype(str).str.strip().eq("")
    print(f"Rows with no Closed Date (isna): {open_mask.sum():,}")
    print(f"Rows with no Closed Date (blank-string filter): {open_second.sum():,}")
    print(f"Open-count match: {open_mask.sum() == open_second.sum()}")
    print("Status values on those open rows:")
    print(df.loc[open_mask, "Status"].value_counts().to_string())


def borough_top(sub: pd.DataFrame, n: int = 10) -> pd.Series:
    return sub[PROBLEM].value_counts().head(n)


def task2_borough_profile(df: pd.DataFrame) -> None:
    section("TASK 2 - A borough profile: Bronx, with Brooklyn as the comparison")
    borough = "BRONX"
    other = "BROOKLYN"
    sub = df[df["Borough"] == borough]
    counts = sub[PROBLEM].value_counts()
    total = len(sub)
    print(f"{borough}: {total:,} complaints")
    print("Top 5 complaints (count, share of borough total):")
    for name, n in counts.head(5).items():
        print(f"  {n:>7,}  {n / total:6.2%}  {name}")

    # Address trap: one Bronx address accounts for most of the noise calls.
    lecture_address = "655 EAST  230 STREET"  # double space is in the source file
    address_total = int((sub["Incident Address"] == lecture_address).sum())
    address_noise = int(
        (
            (sub["Incident Address"] == lecture_address)
            & (sub[PROBLEM] == "Noise - Residential")
        ).sum()
    )
    noise_total = int((sub[PROBLEM] == "Noise - Residential").sum())
    print(
        f"\nAddress trap: {lecture_address} has {address_total:,} complaints; "
        f"{address_noise:,} are Noise - Residential "
        f"({address_noise / noise_total:.1%} of the borough's noise calls)."
    )
    without = sub[sub["Incident Address"] != lecture_address]
    print(
        "Bronx top 5 after removing that one address "
        f"(n={len(without):,}):"
    )
    for name, n in without[PROBLEM].value_counts().head(5).items():
        print(f"  {n:>7,}  {n / len(without):6.2%}  {name}")

    print(f"\n{other}: {len(df[df['Borough'] == other]):,} complaints")
    for name, n in df[df["Borough"] == other][PROBLEM].value_counts().head(5).items():
        print(f"  {n:>7,}  {n / len(df[df['Borough'] == other]):6.2%}  {name}")

    top10 = borough_top(sub, 10)
    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(top10))
    ax.barh(y, top10.values, color="#3b6ea8")
    ax.set_yticks(y, labels=top10.index)
    ax.invert_yaxis()
    ax.set_xlabel("Complaints in November 2025")
    ax.set_title("Bronx: top 10 complaint types (November 2025)")
    for yi, value in zip(y, top10.values):
        ax.text(value + 150, yi, f"{value:,}", va="center", fontsize=8)
    ax.set_xlim(0, top10.max() * 1.15)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig-borough-bronx.png")
    plt.close(fig)
    print(f"Wrote {FIG_DIR / 'fig-borough-bronx.png'}")


def fetch_populations() -> tuple[dict[str, int], str]:
    """Return borough -> 2020 population, plus a note on the source."""
    if not CENSUS_API_KEY:
        return dict(FALLBACK_POP), "no CENSUS_API_KEY; used published 2020 totals"

    params = {
        "get": "NAME,P1_001N",
        "for": "county:*",
        "in": "state:36",
        "key": CENSUS_API_KEY,
    }
    try:
        response = requests.get(CENSUS_URL, params=params, timeout=30)
        ctype = response.headers.get("content-type", "")
        if response.status_code != 200 or "application/json" not in ctype:
            raise ValueError(
                f"API returned {response.status_code} {ctype!r}; "
                "expected JSON (missing/invalid key?)"
            )
        rows = response.json()
        populations: dict[str, int] = {}
        for name, population, _state, county in rows[1:]:
            if county in COUNTY_TO_BOROUGH:
                populations[COUNTY_TO_BOROUGH[county]] = int(population)
        if set(populations) != set(FALLBACK_POP):
            raise ValueError(f"unexpected county set: {sorted(populations)}")
        return populations, "Census API 2020 PL (P1_001N)"
    except Exception as exc:  # noqa: BLE001 - fallback is intentional
        print(f"Census API fallback: {exc}")
        return dict(FALLBACK_POP), "API unavailable; used published 2020 totals"


def task3_per_thousand(df: pd.DataFrame) -> None:
    section("TASK 3 - Complaints per 1,000 residents")
    populations, source = fetch_populations()
    print(f"Population source: {source}")
    total_pop = sum(populations.values())
    print(f"Population sum: {total_pop:,} (sanity target ~8.8 million)")
    print(f"Population sanity check: {8_700_000 < total_pop < 8_900_000}")

    raw = df["Borough"].value_counts()
    unspecified = int(raw.get("Unspecified", 0))
    print(f"Rows with Borough == 'Unspecified' set aside: {unspecified}")

    table = pd.DataFrame(
        {
            "Borough": list(populations),
            "population": [populations[b] for b in populations],
        }
    )
    table["complaints"] = table["Borough"].map(raw).fillna(0).astype(int)
    table["per_1000"] = table["complaints"] / table["population"] * 1000
    table = table.sort_values("per_1000", ascending=False).reset_index(drop=True)
    print("\nBorough | population | complaints | per 1,000")
    for _, row in table.iterrows():
        print(
            f"{row.Borough:<14} {row.population:>10,} {row.complaints:>10,} "
            f"{row.per_1000:>8.2f}"
        )

    raw_rank = table.sort_values("complaints", ascending=False).reset_index(drop=True)
    print("\nRank by raw count:", ", ".join(raw_rank["Borough"]))
    print("Rank by per 1,000: ", ", ".join(table["Borough"]))

    # Two ways: the table's value and a plain calculator from the raw numbers.
    bronx = table[table["Borough"] == "BRONX"].iloc[0]
    manual = bronx.complaints / bronx.population * 1000
    print(
        f"\nBronx check: {bronx.complaints:,} / {bronx.population:,} * 1000 = "
        f"{manual:.4f} (table: {bronx.per_1000:.4f})"
    )

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(table["Borough"], table["per_1000"], color="#2f7d5c")
    ax.set_ylabel("Complaints per 1,000 residents")
    ax.set_title("November 2025 311 complaints per 1,000 residents")
    for i, value in enumerate(table["per_1000"]):
        ax.text(i, value + 0.7, f"{value:.1f}", ha="center", fontsize=9)
    ax.set_ylim(0, table["per_1000"].max() * 1.15)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig-borough-per1000.png")
    plt.close(fig)
    print(f"Wrote {FIG_DIR / 'fig-borough-per1000.png'}")


def task4_night_and_day(df: pd.DataFrame) -> None:
    section("TASK 4 - Night and day")
    noise = df[df[PROBLEM] == "Noise - Residential"].copy()
    heat = df[df[PROBLEM] == "HEAT/HOT WATER"].copy()
    for frame in (noise, heat):
        frame["hour"] = frame["created"].dt.hour

    noise_h = noise.groupby("hour").size().reindex(range(24), fill_value=0)
    heat_h = heat.groupby("hour").size().reindex(range(24), fill_value=0)
    print(f"Noise peak (pandas value_counts): {noise_h.idxmax()}:00, {noise_h.max():,}")
    print(f"Noise peak (numpy bincount):      "
          f"{int(np.bincount(noise['hour'], minlength=24).argmax())}:00, "
          f"{int(np.bincount(noise['hour'], minlength=24).max()):,}")
    print(f"Heat peak  (pandas value_counts): {heat_h.idxmax()}:00, {heat_h.max():,}")
    print(f"Heat peak  (numpy bincount):      "
          f"{int(np.bincount(heat['hour'], minlength=24).argmax())}:00, "
          f"{int(np.bincount(heat['hour'], minlength=24).max()):,}")

    # The same comparison in one borough, to show the pattern is not citywide only.
    for b in ("BROOKLYN",):
        n = noise[noise["Borough"] == b].groupby("hour").size().reindex(range(24), fill_value=0)
        h = heat[heat["Borough"] == b].groupby("hour").size().reindex(range(24), fill_value=0)
        print(f"{b}: noise peak {n.idxmax()}:00 ({n.max():,}); "
              f"heat peak {h.idxmax()}:00 ({h.max():,})")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(noise_h.index, noise_h.values, marker="o", label="Noise - Residential")
    ax.plot(heat_h.index, heat_h.values, marker="o", label="HEAT/HOT WATER")
    ax.set_xticks(range(24))
    ax.set_xlabel("Hour of day (0-23)")
    ax.set_ylabel("Complaints")
    ax.set_title("Noise peaks at night; heat peaks in the morning")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig-hours.png")
    plt.close(fig)
    print(f"Wrote {FIG_DIR / 'fig-hours.png'}")

    # Day x hour heat map for the noise series.
    noise["day"] = noise["created"].dt.day
    piv = (
        noise.groupby(["day", "hour"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=range(1, 31), columns=range(24), fill_value=0)
    )
    fig, ax = plt.subplots(figsize=(11, 7))
    im = ax.imshow(piv.values, aspect="auto", cmap="magma")
    ax.set_xticks(range(0, 24, 2), labels=range(0, 24, 2))
    ax.set_yticks(range(30), labels=range(1, 31))
    ax.set_xlabel("Hour of day (0-23)")
    ax.set_ylabel("Day of November 2025")
    ax.set_title("Noise - Residential complaints by day and hour")
    ax.annotate(
        "Nov 2, 1 AM\n(DST fall-back)",
        xy=(1, 1),
        xytext=(5, 8),
        color="white",
        fontsize=9,
        arrowprops={"color": "white", "arrowstyle": "->"},
    )
    fig.colorbar(im, ax=ax, label="Complaints")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig-nights.png")
    plt.close(fig)
    print(f"Wrote {FIG_DIR / 'fig-nights.png'}")

    # DST check: hour 1 on Nov 2 versus the other Sundays in November.
    sundays = [2, 9, 16, 23, 30]
    print("\nNoise calls at 00:00, 01:00, 02:00 on each Sunday:")
    for h in (0, 1, 2):
        counts = (
            noise[noise["day"].isin(sundays) & (noise["hour"] == h)]
            .groupby("day")
            .size()
            .reindex(sundays, fill_value=0)
        )
        print(f"  {h:02d}:00  " + "  ".join(f"Nov {d}: {counts[d]:>3}" for d in sundays))

    n2 = noise[(noise["day"] == 2) & (noise["hour"] == 1)]
    print(f"\nNov 2 01:00 noise rows: {len(n2)}")
    print(f"  unique Unique Keys: {n2['Unique Key'].nunique()} (all unique: "
          f"{n2['Unique Key'].nunique() == len(n2)})")
    print(f"  duplicate Unique Keys in whole file: {df['Unique Key'].duplicated().sum()}")
    print(f"  exact duplicate rows in whole file: {df.duplicated().sum()}")
    print(f"  distinct addresses in that hour: {n2['Incident Address'].nunique()}")
    print("  top addresses in that hour:")
    print(n2["Incident Address"].value_counts().head(5).to_string())


def task5_response_times(df: pd.DataFrame) -> pd.DataFrame:
    section("TASK 5 - Response times")
    closed = df[df["closed"].notna()].copy()
    closed["hours"] = (closed["closed"] - closed["created"]).dt.total_seconds() / 3600
    dropped = len(df) - len(closed)
    print(f"Open/unclosed cases dropped explicitly: {dropped:,}")
    print(f"Closed cases used: {len(closed):,}")

    top6 = df["Agency"].value_counts().head(6).index.tolist()
    rows = []
    for agency in top6:
        sub = closed[closed["Agency"] == agency]
        pandas_median = float(sub["hours"].median())
        numpy_median = float(np.median(sub["hours"].to_numpy()))
        rows.append(
            {
                "Agency": agency,
                "total": int((df["Agency"] == agency).sum()),
                "closed": len(sub),
                "dropped": int((df["Agency"] == agency).sum()) - len(sub),
                "median_hours": pandas_median,
                "numpy_median": numpy_median,
            }
        )
    table = pd.DataFrame(rows).sort_values("median_hours").reset_index(drop=True)
    print("\nTop six agencies by complaint volume:")
    print(table[["Agency", "total", "closed", "dropped", "median_hours"]].to_string(index=False))
    print(f"Pandas vs numpy median max difference: "
          f"{(table['median_hours'] - table['numpy_median']).abs().max():.10f}")

    longest = closed.loc[closed["hours"].idxmax()]
    print("\nLongest single complaint created in November:")
    print(f"  Unique Key: {longest['Unique Key']}")
    print(f"  Type: {longest[PROBLEM]} | Agency: {longest['Agency']} | "
          f"Borough: {longest['Borough']}")
    print(f"  Created: {longest['Created Date']} | Closed: {longest['Closed Date']}")
    print(f"  Hours: {longest['hours']:,.1f} | Days: {longest['hours'] / 24:,.1f}")

    dpr = closed[closed["Agency"] == "DPR"]["hours"]
    print(f"\nDPR (the longest case's agency): n={len(dpr):,}, "
          f"mean={dpr.mean():.1f} h, median={dpr.median():.1f} h")
    print(f"  DPR 75th/90th percentile: {dpr.quantile(.75):.1f} h / "
          f"{dpr.quantile(.90):.1f} h")
    print(f"  DPR cases over 30 days: {(dpr > 720).sum():,}; "
          f"over 90 days: {(dpr > 2160).sum():,}; over 365 days: {(dpr > 8760).sum():,}")
    print(f"  Longest case adds {dpr.max() / len(dpr):.2f} h to the DPR mean")
    return closed


def task6_same_job(df: pd.DataFrame, closed: pd.DataFrame) -> None:
    section("TASK 6 - Hold the job fixed: HEAT/HOT WATER by borough")
    heat = df[df[PROBLEM] == "HEAT/HOT WATER"]
    heat_closed = closed[closed[PROBLEM] == "HEAT/HOT WATER"]
    dropped = len(heat) - len(heat_closed)
    print(f"HEAT/HOT WATER rows: {len(heat):,}; closed: {len(heat_closed):,}; "
          f"open dropped: {dropped:,}")

    table = (
        heat_closed.groupby("Borough")["hours"]
        .agg(["count", "median"])
        .sort_values("median")
        .reset_index()
    )
    print("\nBorough | closed rows | median hours")
    for _, row in table.iterrows():
        print(f"{row.Borough:<14} {int(row['count']):>10,} {row['median']:>12.3f}")

    fastest = table.iloc[0]
    slowest = table.iloc[-1]
    gap = slowest["median"] - fastest["median"]
    print(f"\nFastest: {fastest.Borough} ({fastest['median']:.2f} h); "
          f"slowest: {slowest.Borough} ({slowest['median']:.2f} h)")
    print(f"Gap: {gap:.2f} h ({gap / fastest['median']:.1%} longer)")

    # Second way: statistics.median on a plain list for the Bronx.
    bronx = heat_closed[heat_closed["Borough"] == "BRONX"]["hours"].tolist()
    print(f"Bronx check: statistics.median={statistics.median(bronx):.6f} h "
          f"vs groupby={table.loc[table.Borough == 'BRONX', 'median'].iloc[0]:.6f} h")

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(table["Borough"], table["median"], color="#b5651d")
    ax.invert_yaxis()
    ax.set_xlabel("Median hours from created to closed")
    ax.set_title("Same job, different borough: HEAT/HOT WATER response time")
    for i, (median, count) in enumerate(zip(table["median"], table["count"])):
        ax.text(median + 0.8, i, f"{median:.1f} h (n={int(count):,})", va="center", fontsize=9)
    ax.set_xlim(0, table["median"].max() * 1.28)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig-same-job.png")
    plt.close(fig)
    print(f"Wrote {FIG_DIR / 'fig-same-job.png'}")


def task7_data_detective(df: pd.DataFrame) -> None:
    section("TASK 7 - Data detective: one address in Fresh Meadows")
    address = "78-15 PARSONS BOULEVARD"
    print("Top 10 addresses in the file:")
    print(df["Incident Address"].value_counts().head(10).to_string())

    sub = df[df["Incident Address"] == address]
    print(f"\n{address}: {len(sub):,} complaints")
    print(f"  Borough/ZIP/city: {sub['Borough'].mode().iat[0]} / "
          f"{sub['Incident Zip'].mode().iat[0]} / {sub['City'].mode().iat[0]}")
    print(f"  Unique keys: {sub['Unique Key'].nunique():,}")
    print(f"  Active days: {sub['created'].dt.day.nunique()} of 30")
    print(f"  Coordinates: {sub[['Latitude', 'Longitude']].drop_duplicates().to_dict('records')}")
    print("  Top problems:")
    print(sub[PROBLEM].value_counts().head(8).to_string())
    print("  Top descriptors:")
    print(sub["Problem Detail (formerly Descriptor)"].value_counts().head(8).to_string())
    print("  Agencies:")
    print(sub["Agency"].value_counts().to_string())
    print("  Status:")
    print(sub["Status"].value_counts().to_string())
    print("  Hourly shape (peak hour -> count):")
    hourly = sub["created"].dt.hour.value_counts().sort_index()
    print(hourly.to_string())


def main() -> None:
    df = load_data()
    task1_first_look(df)
    task2_borough_profile(df)
    task3_per_thousand(df)
    task4_night_and_day(df)
    closed = task5_response_times(df)
    task6_same_job(df, closed)
    task7_data_detective(df)
    section("DONE")
    print(f"Figures written to {FIG_DIR}")


if __name__ == "__main__":
    main()
