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
        valid = frame[risk.replace('_score', '_area_coverage')].ge(frame.min_nri_coverage)
        sample = frame.loc[valid, ['life_expectancy', 'median_household_income', risk]].dropna()
        # Every hazard gets its own complete-case n; null ratings never become zero.
        if len(sample) < 4 or sample[risk].nunique() < 2:
            results.append(dict(risk=risk, n=len(sample), status='insufficient variation/data'))
            continue
        y = sample.life_expectancy.to_numpy()
        x = sample[risk].to_numpy()
        income = np.log(sample.median_household_income.to_numpy())
        controls = np.column_stack([np.ones(len(sample)), income])
        beta_y = np.linalg.lstsq(controls, y, rcond=None)[0]
        beta_x = np.linalg.lstsq(controls, x, rcond=None)[0]
        # Two-column prediction written explicitly; avoids platform BLAS matmul warnings.
        y_resid = y - (beta_y[0] + income * beta_y[1])
        x_resid = x - (beta_x[0] + income * beta_x[1])
        design = np.column_stack([controls, x / 10])
        if np.linalg.matrix_rank(design) < 3 or np.std(x_resid) < 1e-10 or np.std(y_resid) < 1e-10:
            results.append(dict(risk=risk, n=len(sample), status='insufficient independent variation'))
            continue
        beta = np.linalg.lstsq(design, y, rcond=None)[0]
        unadjusted_design = np.column_stack([np.ones(len(sample)), x / 10])
        unadjusted = np.linalg.lstsq(unadjusted_design, y, rcond=None)[0]
        results.append(dict(risk=risk, n=len(sample), status='descriptive only',
                            pearson_r=float(np.corrcoef(x, y)[0, 1]),
                            partial_r_controlling_log_income=float(np.corrcoef(x_resid, y_resid)[0, 1]),
                            years_per_10_risk_points_unadjusted=float(unadjusted[1]),
                            years_per_10_risk_points_log_income_adjusted=float(beta[2]),
                            coefficient_change=float(beta[2] - unadjusted[1])))
    return pd.DataFrame(results)


def main():
    database = ROOT / 'data/clean/project.duckdb'
    if not database.exists():
        raise ValueError('No validated joined database. Finish download.py and clean.py first; no charts fabricated.')
    with duckdb.connect(str(database), read_only=True) as con:
        all_samples = con.execute('SELECT * FROM tract_analysis WHERE included_in_analysis ORDER BY sample, GEOID').df()
    frame = all_samples[all_samples['sample'].eq('area_weighted')].copy()
    if frame.empty:
        raise ValueError('Joined table is empty')
    required = ['life_expectancy', 'median_household_income', 'overall_risk_score']
    if frame[required].isna().any().any():
        raise ValueError('Main table has missing required analysis values')
    frame['income_quartile'] = pd.qcut(frame.median_household_income, 4, labels=LABELS)
    coverage_label = f'{frame.min_nri_coverage.iloc[0]:.0%}'
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
    fig.text(.02, .015, f'CDC USALEEP; ACS 2011–2015; FEMA Dec 2025. Land-area crosswalk; ≥{coverage_label} coverage. Association only.', fontsize=8)
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

    columns = required + ['poverty_rate'] + [h + '_risk_score' for h in HAZARDS]
    correlation_frame = frame[columns].copy()
    for risk in ['overall_risk_score'] + [h + '_risk_score' for h in HAZARDS]:
        # A score based on a tiny remaining patch must not stand for a whole tract.
        coverage = risk.replace('_score', '_area_coverage')
        correlation_frame.loc[~frame[coverage].ge(frame.min_nri_coverage), risk] = np.nan
    corr = correlation_frame.corr(method='pearson', min_periods=3)
    present = correlation_frame.notna().astype(int)
    pair_counts = present.T @ present
    corr.to_csv(CHARTS / 'correlations.csv')
    pair_counts.to_csv(CHARTS / 'correlation_pair_counts.csv')
    display_labels = ['Life expectancy', 'Median income', 'Overall NRI', 'Poverty (%)',
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
    ax.set_title(f'Pearson correlations: area-weighted main sample\nPairwise complete records; each score requires ≥{coverage_label} land coverage')
    fig.colorbar(im, ax=ax, shrink=.7)
    fig.tight_layout()
    fig.savefig(CHARTS / 'correlation_table.png', dpi=180)
    plt.close(fig)

    comparisons = []
    for sample_name, group in all_samples.groupby('sample'):
        result = adjusted_results(group, ['overall_risk_score'] + [h + '_risk_score' for h in HAZARDS])
        result.insert(0, 'sample', sample_name)
        comparisons.append(result)
    adjusted = pd.concat(comparisons, ignore_index=True)
    adjusted.to_csv(CHARTS / 'income_adjusted_associations.csv', index=False)
    overall = adjusted[adjusted.risk.eq('overall_risk_score')].set_index('sample')
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, (sample_name, label) in enumerate([('area_weighted', 'Area-weighted main'), ('strict_1to1', 'Strict 1:1 check')]):
        row = overall.loc[sample_name]
        before, after = row.years_per_10_risk_points_unadjusted, row.years_per_10_risk_points_log_income_adjusted
        ax.plot([before, after], [i, i], color='#999999', linewidth=2)
        ax.scatter(before, i, color='#31688e', s=70, label='Risk only' if i == 0 else None, zorder=3)
        ax.scatter(after, i, color='#bc5090', marker='D', s=60, label='Risk + log(income)' if i == 0 else None, zorder=3)
        ax.annotate(f'{before:+.3f}', (before, i), xytext=(0, -18), textcoords='offset points', ha='center', fontsize=9)
        ax.annotate(f'{after:+.3f}', (after, i), xytext=(0, 10), textcoords='offset points', ha='center', fontsize=9)
    ax.axvline(0, color='#888888', linestyle='--', linewidth=1)
    ax.set_yticks([0, 1], [f'Area-weighted main (n={int(overall.loc["area_weighted", "n"])})',
                             f'Strict 1:1 check (n={int(overall.loc["strict_1to1", "n"])})'])
    ax.set(xlabel='Life-expectancy difference (years) per 10 overall NRI score points',
           title='Overall-risk OLS coefficient before and after income adjustment', ylim=(-.6, 1.6))
    ax.legend(loc='lower right', fontsize=9)
    fig.text(.02, .015, 'Descriptive point estimates only. No spatial dependence or ACS/USALEEP uncertainty modeled.', fontsize=8)
    fig.tight_layout(rect=[0, .04, 1, 1])
    fig.savefig(CHARTS / 'risk_coefficients.png', dpi=180)
    plt.close(fig)
    summary = dict(n=len(frame), first_correlation=float(corr.loc['life_expectancy', 'overall_risk_score']),
                   first_correlation_pair_n=int(pair_counts.loc['life_expectancy', 'overall_risk_score']),
                   min_nri_coverage=float(frame.min_nri_coverage.iloc[0]),
                   overall_risk_ols=overall.reset_index().to_dict('records'),
                   caveat='Descriptive cross-period tract associations; natural log income control; no spatial/causal inference.')
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
