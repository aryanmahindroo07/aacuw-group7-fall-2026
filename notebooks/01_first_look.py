"""First-look charts and descriptive income adjustment using the real joined table.

Run: python notebooks/01_first_look.py
This script is the requested runnable alternative to an .ipynb notebook.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Keep Matplotlib's cache local and select a backend that works without a GUI.
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import duckdb
import numpy as np
import pandas as pd

CHARTS = ROOT / 'charts'
HAZARDS = ['drought', 'wildfire', 'heat_wave', 'coastal_flooding', 'inland_flooding']
LABELS = ['Q1 (lowest)', 'Q2', 'Q3', 'Q4 (highest)']


def adjusted_results(frame, risks):
    results = []
    for risk in risks:
        sample = frame[['life_expectancy', 'median_household_income', risk]].dropna()
        # Every hazard gets its own complete-case n; null ratings never become zero.
        if len(sample) < 4 or sample[risk].nunique() < 2:
            results.append(dict(risk=risk, n=len(sample), status='insufficient variation/data'))
            continue
        y = sample.life_expectancy.to_numpy()
        x = sample[risk].to_numpy()
        income = sample.median_household_income.to_numpy() / 10000
        controls = np.column_stack([np.ones(len(sample)), income])
        y_resid = y - controls @ np.linalg.lstsq(controls, y, rcond=None)[0]
        x_resid = x - controls @ np.linalg.lstsq(controls, x, rcond=None)[0]
        design = np.column_stack([controls, x / 10])
        if np.linalg.matrix_rank(design) < 3 or np.std(x_resid) < 1e-10 or np.std(y_resid) < 1e-10:
            results.append(dict(risk=risk, n=len(sample), status='insufficient independent variation'))
            continue
        beta = np.linalg.lstsq(design, y, rcond=None)[0]
        results.append(dict(risk=risk, n=len(sample), status='descriptive only',
                            pearson_r=float(np.corrcoef(x, y)[0, 1]),
                            partial_r_controlling_linear_income=float(np.corrcoef(x_resid, y_resid)[0, 1]),
                            years_per_10_risk_points_controlling_income=float(beta[2])))
    return pd.DataFrame(results)


def main():
    database = ROOT / 'data/clean/project.duckdb'
    if not database.exists():
        raise ValueError('No validated joined database. Finish download.py and clean.py first; no charts fabricated.')
    with duckdb.connect(str(database), read_only=True) as con:
        frame = con.execute('SELECT * FROM tract_analysis ORDER BY GEOID').df()
    if frame.empty:
        raise ValueError('Joined table is empty')
    required = ['life_expectancy', 'median_household_income', 'overall_risk_score']
    if frame[required].isna().any().any():
        raise ValueError('Main table has missing required analysis values')
    frame['income_quartile'] = pd.qcut(frame.median_household_income, 4, labels=LABELS)
    CHARTS.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    colors = ['#440154', '#31688e', '#35b779', '#d6bf22']

    fig, ax = plt.subplots(figsize=(9, 6))
    for label, color in zip(LABELS, colors):
        group = frame[frame.income_quartile == label]
        ax.scatter(group.overall_risk_score, group.life_expectancy, s=24, alpha=.65,
                   color=color, label=f'{label} (n={len(group)})', edgecolors='none')
    ax.set(xlabel='Overall NRI risk score (national relative score, 0–100)',
           ylabel='Life expectancy at birth, 2010–2015 (years)',
           title=f'Washington: life expectancy and overall risk (n={len(frame)})')
    ax.legend(title='Tract median household income quartile', fontsize=9)
    fig.text(.02, .015, 'CDC USALEEP; ACS 2011–2015; FEMA Dec 2025. Strict reciprocal 1:1 tracts. Association only.', fontsize=8)
    fig.tight_layout(rect=[0, .04, 1, 1])
    fig.savefig(CHARTS / 'life_expectancy_vs_risk.png', dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 6))
    groups = [frame.loc[frame.income_quartile == q, 'life_expectancy'] for q in LABELS]
    boxes = ax.boxplot(groups, tick_labels=[f'{q}\nn={len(g)}' for q, g in zip(LABELS, groups)], patch_artist=True)
    for box, color in zip(boxes['boxes'], colors):
        box.set_facecolor(color)
        box.set_alpha(.6)
    ax.set(xlabel='Median household income quartile within the final analysis sample',
           ylabel='Life expectancy at birth, 2010–2015 (years)',
           title='How life expectancy varies with tract income')
    fig.text(.02, .015, 'Boxes: median and IQR; whiskers: 1.5 IQR; points: outliers. CDC USALEEP; ACS 2011–2015.', fontsize=8)
    fig.tight_layout(rect=[0, .04, 1, 1])
    fig.savefig(CHARTS / 'life_expectancy_by_income.png', dpi=180)
    plt.close(fig)
    frame.groupby('income_quartile', observed=True).agg(
        n=('GEOID', 'size'), income_min=('median_household_income', 'min'),
        income_max=('median_household_income', 'max'), life_expectancy_mean=('life_expectancy', 'mean')
    ).to_csv(CHARTS / 'income_quartiles.csv')

    columns = required + ['poverty_rate', 'expected_annual_loss'] + [h + '_risk_score' for h in HAZARDS]
    corr = frame[columns].corr(method='pearson', min_periods=3)
    present = frame[columns].notna().astype(int)
    pair_counts = present.T @ present
    corr.to_csv(CHARTS / 'correlations.csv')
    pair_counts.to_csv(CHARTS / 'correlation_pair_counts.csv')
    display_labels = ['Life expectancy', 'Median income', 'Overall NRI', 'Poverty (%)', 'EAL ($)',
                      'Drought', 'Wildfire', 'Heat wave', 'Coastal flooding', 'Inland flooding']
    fig, ax = plt.subplots(figsize=(11, 9))
    im = ax.imshow(corr.to_numpy(), vmin=-1, vmax=1, cmap='RdBu_r')
    ax.set_xticks(range(len(columns)), display_labels, rotation=45, ha='right')
    ax.set_yticks(range(len(columns)), display_labels)
    for i in range(len(columns)):
        for j in range(len(columns)):
            value = corr.iloc[i, j]
            text = 'NA' if pd.isna(value) else f'{value:.2f}'
            ax.text(j, i, text + f'\nn={pair_counts.iloc[i, j]}', ha='center', va='center',
                    fontsize=7, color='white' if pd.notna(value) and abs(value) > .6 else 'black')
    ax.set_title('Pearson correlations: strict 1:1 analysis sample\nPairwise complete records; each cell reports its own n')
    fig.colorbar(im, ax=ax, shrink=.7)
    fig.tight_layout()
    fig.savefig(CHARTS / 'correlation_table.png', dpi=180)
    plt.close(fig)

    adjusted = adjusted_results(frame, ['overall_risk_score'] + [h + '_risk_score' for h in HAZARDS])
    adjusted.to_csv(CHARTS / 'income_adjusted_associations.csv', index=False)
    summary = dict(n=len(frame), first_correlation=float(corr.loc['life_expectancy', 'overall_risk_score']),
                   first_correlation_pair_n=int(pair_counts.loc['life_expectancy', 'overall_risk_score']),
                   caveat='Descriptive cross-period tract associations; linear income control; no spatial/causal inference.')
    (CHARTS / 'first_look_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    print(adjusted.to_string(index=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        with (ROOT / 'NOTES.md').open('a') as handle:
            handle.write(f'\n## First look blocked\n\n{exc}\n')
        raise SystemExit(f'BLOCKED: {exc}') from None
