# Governance Protocol

## Sample Size
- n_total=8
- n_eff=8

## Statistical Test Selection Rule
- For same-seed paired comparisons:
- 1. Compute paired differences d_i = treatment_i - control_i.
- 2. Shapiro-Wilk on d_i: if p >= 0.05 (normal), use scipy.stats.ttest_rel.
- 3. If Shapiro-Wilk p < 0.05 (non-normal), use scipy.stats.wilcoxon.
- 4. Count metrics (chatter_count) always use wilcoxon.
- 5. alpha = 0.05, one-sided: treatment < control for effort/chatter.
- 6. SLA compliance uses exact count (zero-violation threshold or comparison).

## Claim Boundaries
- All claims are simulation-bounded.
- Do not claim hardware longevity, ROI, or universal applicability.
- Use "parity" or "no material increase" when results are not significant.
