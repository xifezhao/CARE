# Replication Package: Review Dynamics in the Era of Agentic SE

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.placeholder.svg)](https://doi.org/10.5281/zenodo.placeholder)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> **Double-Blind Review Notice**:  
> In compliance with the ACM/IEEE/Springer double-blind review policies, all institutional and author identifying metadata have been redacted. Repository URLs and dataset links point to anonymous staging endpoints.

---

## 1. Overview & Directory Structure

This repository contains the complete, self-contained replication package for the empirical study:
**"Review Dynamics in the Era of Agentic SE: Balancing Speed and Depth through the CARE Framework"** (submitted to *Empirical Software Engineering*).

The artifact includes the formal implementation of the CARE framework (Phases 1–5), the ensemble SZZ pipeline, the historical replay simulation (RQ1), the orthogonal tool ablation suite (RQ2), the automated controlled review evaluation (RQ3), and the interactive visualization notebooks.

```text
CARE-Replication-Package/
├── data/
│   ├── manual_audit/          # Cohen's Kappa verified ground-truth labels
│   │   ├── IRR_ManualVerified_Labels.json
│   │   ├── IRR_ManualVerified_Labels.csv
│   │   └── stratified_sample_5000.csv
│   └── processed/             # Pre-computed propensity scores and evaluation context
│       ├── propensity_scores_2025.json
│       ├── eval_target_2025.parquet
│       └── train_context_2023_2024.parquet
├── src/
│   ├── care_framework/        # Core CARE Framework implementations
│   │   ├── __init__.py
│   │   ├── phase1_state_machine.py       # Commit-bound state machine (Eq. 1)
│   │   ├── phase2_obligations.py         # Policy-mechanism decoupled obligations
│   │   ├── phase3_evidence_gates.py      # Set-theoretic compliance gates (Eq. 3)
│   │   ├── phase4_heuristic_scheduler.py # Knapsack marginal expected yield proxy
│   │   └── phase5_ipw_calibration.py     # Causal IPW calibration & weight clipping
│   └── szz_pipeline/          # SZZ pipeline and survival analysis filters
│       ├── run_ensemble_szz.py           # Anti-tangle commit filtering
│       └── right_censoring_filter.py     # Static cutoff right-censoring filter
├── experiments/
│   ├── rq1_historical_replay/ # RQ1: Budget-constrained routing simulation
│   │   ├── simulate_queues.py
│   │   ├── apply_ipw_weights.py
│   │   └── compute_aubc.py
│   ├── rq2_ablation_monoculture/ # RQ2: Epistemic independence ablation
│   │   ├── extract_monoculture_subset.py
│   │   ├── run_codeql_orthogonal.py
│   │   └── eval_orthogonal_detection.py
│   └── rq3_cognitive_trial/   # RQ3: Automated controlled review evaluation
│       ├── seeded_defects_manifest.json
│       ├── parse_precision_logs.py
│       └── statistical_tests.R
├── notebooks/                 # Jupyter notebooks reproducing figures
│   ├── Fig1_Speed_Depth_Paradox.ipynb
│   ├── Fig4_CBYC_Curve.ipynb
│   ├── Fig5_Detection_Efficacy.ipynb
│   └── Fig6_RQ3_Tradeoffs.ipynb
├── results/                   # Evaluation output artifacts and test reports
├── environment.yml            # Conda environment specification (Python + R)
├── requirements.txt           # Pip dependencies
└── README.md                  # This file
```

---

## 2. Environment Setup

### Option A: Using Conda (Recommended, installs Python & R)
```bash
conda env create -f environment.yml
conda activate care-replication
```

### Option B: Using Pip (Python only)
```bash
pip install -r requirements.txt
```

---

## 3. Reproduction Options

### Option 1: 1-Click End-to-End Execution via Google Colab
You can run the entire experimental pipeline, statistical verification, and consistency audit in a single click using the standalone Colab notebook:
- **Notebook**: [`CARE_Full_Experiment_Colab.ipynb`](CARE_Full_Experiment_Colab.ipynb)
- Open directly in Google Colab or run locally via:
  ```bash
  jupyter notebook CARE_Full_Experiment_Colab.ipynb
  ```

### Option 2: Step-by-Step Command Line Reproduction

#### Step 1: RQ1 - Historical Replay Simulation & AUBC Metric
```bash
# 1. Simulate FIFO and CARE daily queue allocation trajectories
python3 experiments/rq1_historical_replay/simulate_queues.py

# 2. Apply Inverse Probability Weighting (IPW) on ManualVerified labels
python3 experiments/rq1_historical_replay/apply_ipw_weights.py

# 3. Compute Area Under the Budget-Yield Curve (AUBC) and bootstrap tests
python3 experiments/rq1_historical_replay/compute_aubc.py
```
*Expected Output*: CARE AUBC = 0.714 [0.668, 0.756] vs. FIFO AUBC = 0.500 [0.443, 0.559] (paired $\Delta\text{AUBC} = +0.213$, $p < 0.001$, Cliff's $\delta = 1.00$).

#### Step 2: RQ2 - Epistemic Independence Ablation Study
```bash
# 1. Extract the 1,240 algorithmic monoculture cohort
python3 experiments/rq2_ablation_monoculture/extract_monoculture_subset.py

# 2. Run commit-bound orthogonal verification matching
python3 experiments/rq2_ablation_monoculture/run_codeql_orthogonal.py

# 3. Compute Pearson's Chi-Square Test and Cramer's V effect size
python3 experiments/rq2_ablation_monoculture/eval_orthogonal_detection.py
```
*Expected Output*: $\chi^2 = 61.61, df=3, p = 2.66 \times 10^{-13}$, Cramer's $V = 0.262$. Minimum expected cell frequency $E_{\min} = 50.61 \ge 5.0$. Multi-file complex flaws intercepted: 63.3% (150/237). Spurious alerts: 18.4 / 100 PRs; CodeQL build failure rate: 8.2%.

#### Step 3: RQ3 - Automated Controlled Review Evaluation
```bash
# 1. Evaluate agent performance logs across Conditions A, B, C, D, and D+Gate
python3 experiments/rq3_cognitive_trial/parse_precision_logs.py

# 2. (Optional) Run paired Wilcoxon signed-rank and Cliff's Delta tests in R
Rscript experiments/rq3_cognitive_trial/statistical_tests.R
```
*Expected Output*: 
- **Exact McNemar's Test (Binary PRs, $N=30$)**: Discordant pairs $b=6, c=0 \implies p = 2 \times (0.5)^6 = 0.03125$ ($p = 0.031$). Net yield gain = +6 PRs (+20.0 percentage points, 95% Wilson score CI: [+4.3%, +35.7%]).
- **Granular Diagnostic Item Scores**: Paired Wilcoxon $W = 31.5, p = 0.005$, Cliff's $\delta = 0.200$.
- **Policy Enforcement**: Defect localization recall is 90.0% (27/30) for both D and D+Gate. Merge interception reaches 100.0% (30/30) in D+Gate via set-theoretic gates ($\bigcup e.\text{scope} \supseteq \Omega_d$), eliminating unsupported approvals (0.0%) with 0.0% clean false blocks.

#### Step 4: Reproducing Paper Figures
Launch Jupyter:
```bash
jupyter notebook notebooks/
```
Execute notebooks to re-render figures corresponding to `main.pdf`.

---

## 4. Academic Safeguards & Epistemological Boundaries

1. **Anti-Lookahead Enforcement**: SZZ and queue scheduling enforce strict temporal unidirectionality ($t_{\text{sched}} < t_{\text{merge}} < t_{\text{fix}}$).
2. **Label Quarantine**: Heuristic `WeakSZZ` tags are quarantined from the core calibration loss function; only `ManualVerified` labels enter the primary IPW yield estimator.
3. **Positivity & Clipping**: Propensity scores are clipped ($W \le 20.0, P(A|X) \ge 10^{-4}$) to prevent variance explosion under sparse covariate support.
4. **Automated Controlled Review Bounds**: RQ3 evaluates evidence structure efficiency on automated models under strictly controlled conditions without making unsupported claims about human cognitive load.

---

## 5. License & Citation

This project is licensed under the MIT License. If you use this artifact in your research, please cite:
```bibtex
@article{care_framework_2026,
  title   = {Review Dynamics in the Era of Agentic SE: Balancing Speed and Depth through the CARE Framework},
  journal = {Empirical Software Engineering},
  year    = {2026},
  note    = {Under Review}
}
```
