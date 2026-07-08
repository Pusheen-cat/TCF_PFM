# TCF

Official code release for our ICML 2026 paper *"Time-Conditioned Foreseeing: An EHR-Specific Foundation Model for Irregular Dynamics and Calendrical Time"*.
https://icml.cc/virtual/2026/poster/64928

**TCF** is a time-aware generative foundation model for irregularly-sampled
clinical time series, pretrained and evaluated on **MIMIC-IV**. Each clinical
event is tokenized jointly with its (continuous) timestamp; a decoder-only
Transformer with a rotary time-and-position encoding is trained with a
generative objective that predicts both *the next token* and *when the next
event occurs*. This repository contains the complete pipeline — raw-data
preprocessing, self-supervised pretraining, downstream finetuning/probing, and
cross-dataset (eICU) transfer.

> **Scope.** This release provides the **proposed method only**. The paper's
> competing neural baselines (EHRMamba, EHRSHOT, FM4EHR, HEART, TRADE, STraTS,
> MOTOR) have been removed, with the single exception of **ETHOS**, which is
> retained as an included baseline.
>
> **Data source.** Only **MIMIC-IV** is supported (the original MIMIC-III
> benchmark/training code has been removed). The extraction code is adapted from
> [YerevaNN/mimic3-benchmarks](https://github.com/YerevaNN/mimic3-benchmarks);
> see [Acknowledgements](#acknowledgements).

---

## Contents

1. [Repository layout](#repository-layout)
2. [Pipeline at a glance](#pipeline-at-a-glance)
3. [Installation](#installation)
4. [Data access &amp; configuration](#data-access--configuration)
5. [Step 1 — Preprocessing](#step-1--preprocessing)
6. [Step 2 — Pretraining](#step-2--pretraining)
7. [Step 3 — Downstream evaluation](#step-3--downstream-evaluation)
8. [Configuration reference](#configuration-reference)
9. [Baselines](#baselines) · [Acknowledgements](#acknowledgements) · [Citation](#citation) · [License](#license)

---

## Repository layout

```
mimic4preprocessing/            raw MIMIC-IV -> tokenizable event streams + labels
  omr_labevent_fix.py           prerequisite: builds hosp/omr_v1.csv from hosp/omr.csv
  scripts/                      extraction pipeline, numbered in run order
    01_extract_subjects.py      per-subject stays/diagnoses/events + phenotype labels
    02_validate_events.py       clean/validate each subject's events, count itemids
    03_extract_episodes.py      map itemids -> variables, build per-episode timeseries
    04_split_train_test.py      move subjects into train/ and test/ (committed split)
    05_build_qa_tables.py       write pretraining event streams (addQ and NOadd)
    inclusion_criteria/         cohort + variable allow/block lists (criteria1)
  scripts_downstreams/          downstream-label pipeline, numbered in run order
    01_preproc_vaso.py          vasopressor input events -> pickles
    02_preproc_urine_output.py  6h rolling urine output -> pickle
    03_build_downstream_labels.py  per-admission labels for 9 downstream tasks
  unit_value_cleaning/data/     committed value-binning + time-to-event thresholds
  resources/                    variable maps, HCUP CCS phenotypes, test-set split

pfm_mimic4/                     the model and all training / evaluation code
  main.py                       single entry point (pretraining AND downstream eval)
  model/timestamp_tf.py         the TCF model (RoPE Transformer + time-addressing head)
  model/                        time-conditioning / next-event-time modules
  modules/                      output heads + loss functions
  tokenizer/                    multi-type EHR tokenizer (categorical + value binning)
  dataset/                      QA dataset + CSV->tensor builders (csvs_to_tensor*)
  exp/pfm_mixed_precision.py    DDP mixed-precision trainer
  scripts/                      launch scripts (pretraining + downstream, see below)
  ML_method/ihm.py              optional classical tabular baseline
```

## Pipeline at a glance

```
 raw MIMIC-IV CSVs                                               (you provide, from PhysioNet)
        │
        ▼   mimic4preprocessing/
 [1.1] omr_labevent_fix.py ───────────────► hosp/omr_v1.csv
 [1.2] 01→02→03→04 (extract / validate / episodes / split) ──► PFM_DATA_ROOT/B_train_test_split/
 [1.3] 05_build_qa_tables.py ─────────────► PFM_DATA_ROOT/PFM_pretraining/{addQ,NOadd}/
 [1.4] scripts_downstreams/01→02→03 ──────► PFM_DATA_ROOT/PFM_downstream/{addQ,NOadd}/
        │
        ▼   pfm_mimic4/
 [1.5] csvs_to_tensor* (tokenize CSV → padded tensors; runs on first launch)
 [2]   pretraining  (scripts/OURS.py, Xshare_OURS.py) ───────► result_pretrained/<run>/check_points/best_model.pt
 [3]   downstream   (scripts/downstream_tasks_probing*.py, loads a checkpoint)
```

## Installation

TCF requires **Python ≥ 3.12** (the codebase uses PEP 701 nested-quote
f-strings) and a CUDA-capable PyTorch build. Multi-GPU pretraining and
finetuning are launched with `torchrun` (PyTorch DDP).

```bash
# 1) install a CUDA build of torch that matches your driver, e.g.:
pip install torch --index-url https://download.pytorch.org/whl/cu121

# 2) install the remaining dependencies
pip install -r requirements.txt
```

`requirements.txt` lists the core dependencies (`torch`, `numpy`, `pandas`,
`scikit-learn`, `scipy`, `tqdm`, `transformers`, `PyYAML`, `GPUtil`) and the
preprocessing extras (`numba`, `joblib`, `multiprocess`). Optional deps for the
tabular baseline (`xgboost`, `lightgbm`, `catboost`) and for analysis/plotting
(`matplotlib`, `umap-learn`) are commented out — uncomment them if needed.

## Data access &amp; configuration

Access to **MIMIC-IV v3.1** (and, for the transfer experiment, **eICU**)
requires a credentialed [PhysioNet](https://physionet.org/) account and
acceptance of the Data Use Agreement. **No patient data or derived per-patient
tensors are included in this repository, and they must never be committed to
it.** Download the raw CSVs yourself; the `hosp/` and `icu/` sub-directories must
be present.

All data lives **outside** the repository. Two roots are read from the
environment by the preprocessing and training code:

```bash
export MIMIC4_ROOT=/path/to/mimiciv/3.1     # raw MIMIC-IV 3.1 (contains hosp/, icu/)
export PFM_DATA_ROOT=/path/to/PFM_data      # everything the pipeline produces
```

`PFM_DATA_ROOT` accumulates the whole preprocessing tree as you run the steps:

```
$PFM_DATA_ROOT/
├── A_extract_subjects/      # per-subject working dir (steps 01–03; step 04 empties it)
├── B_train_test_split/      # step 04:  train/<id>/…  test/<id>/…
├── PFM_pretraining/         # step 05:  addQ/…  NOadd/…   + tensor_saved/ (built at launch)
├── PFM_downstream/          # step 03d: {addQ,NOadd}/…    + tensor_dt_saved/ (built at eval)
└── result_pretrained/       # step 2:   pretrained checkpoints + logs
```

The value/unit binning thresholds and time-to-event edges are small aggregate
statistics shipped in-repo under `mimic4preprocessing/unit_value_cleaning/data/`
and are loaded automatically, so the `unit_value_cleaning/` *scripts* are **not**
part of the runnable pipeline.

> **Manual edits / external prerequisites** (please read before running):
> 1. **`omr_labevent_fix.py`** has a hard-coded MIMIC path (`/path/to/mimiciv/3.1/…`)
>    inside `split_blood_pressure_inplace()` that ignores `$MIMIC4_ROOT`; edit it to
>    your real path.
> 2. **Cardiac-arrest label.** Step `03_build_downstream_labels.py` reads
>    `$MIMIC4_ROOT/icu/chartevents_arrest.pkl` (columns `subject_id, hadm_id,
>    charttime`). No script here produces it — supply it yourself, or drop the
>    `DEC_arrest` label.
> 3. **eICU transfer** requires an eICU cohort exported into the per-unit
>    directory layout consumed by `csvs_to_tensor_dt_eicu.py`; that exporter is not
>    included.
> 4. The standalone `csvs_to_tensor*.py` scripts carry `/path/to/PFM_data/…`
>    placeholder defaults for a few path flags; when run on their own, pass the real
>    paths (the trainer, which builds tensors automatically, uses `$PFM_DATA_ROOT`).

---

## Step 1 — Preprocessing

`mimic4preprocessing/` turns the raw MIMIC-IV CSVs into the tokenizable event
streams and downstream labels. **Run every command from the repository root**,
with `MIMIC4_ROOT` and `PFM_DATA_ROOT` exported. The extraction scripts (01–04)
take input/output directories as positional arguments; the later scripts read
the two environment variables.

### 1.1 Prerequisite — build `hosp/omr_v1.csv`

Outpatient-measurement (OMR) rows are normalized (blood pressure split into
systolic/diastolic, weight converted to kg, synthetic outpatient-visit events
inserted) into `hosp/omr_v1.csv`, which the extraction step reads by default.

```bash
python mimic4preprocessing/omr_labevent_fix.py        # -> $MIMIC4_ROOT/hosp/omr_v1.csv
```

### 1.2 Subject extraction, validation, episodes, split (01–04)

```bash
# 01 — extract per-subject stays/diagnoses/events + phenotype labels.
#      Run it TWICE: once with the default event tables (which include omr_v1),
#      then with `-e hosp/omr` to append the raw OMR table (events.csv is
#      appended, not overwritten, on the second pass).
python mimic4preprocessing/scripts/01_extract_subjects.py  $MIMIC4_ROOT  $PFM_DATA_ROOT/A_extract_subjects
python mimic4preprocessing/scripts/01_extract_subjects.py  $MIMIC4_ROOT  $PFM_DATA_ROOT/A_extract_subjects  -e hosp/omr

# 02 — validate/clean each subject's events; synthesize GCS-total; write itemid counts.
python mimic4preprocessing/scripts/02_validate_events.py    $PFM_DATA_ROOT/A_extract_subjects

# 03 — map itemids -> variables and build per-admission / per-ICU-stay timeseries.
python mimic4preprocessing/scripts/03_extract_episodes.py   $PFM_DATA_ROOT/A_extract_subjects

# 04 — move subjects into train/ and test/ using the committed split
#      (mimic4preprocessing/resources/mimic4-testset.csv). NOTE: this MOVES folders,
#      so A_extract_subjects is emptied into B_train_test_split.
python mimic4preprocessing/scripts/04_split_train_test.py   $PFM_DATA_ROOT/A_extract_subjects  $PFM_DATA_ROOT/B_train_test_split
```

The cohort and the per-table variable allow/block lists are defined in
`mimic4preprocessing/scripts/inclusion_criteria/criteria1.py` (selected
everywhere via `--data criteria1`).

### 1.3 Pretraining event streams (05)

Step 05 emits the token-level event streams for pretraining, in **both**
sequence layouts used by the two TCF variants:

* **`addQ`** — a "question" token is written before every clinical event
  (used by the shared-token variant, *OURS*);
* **`NOadd`** — the raw event stream, unchanged (used by the no-share variant,
  *Xshare*).

```bash
python mimic4preprocessing/scripts/05_build_qa_tables.py
# -> $PFM_DATA_ROOT/PFM_pretraining/addQ/{train,test}/<id[:3]>/<id>.csv
# -> $PFM_DATA_ROOT/PFM_pretraining/NOadd/{train,test}/<id[:3]>/<id>.csv
```

### 1.4 Downstream-task labels (scripts_downstreams 01–03)

```bash
# 01/02 — auxiliary ICU signals used by two of the downstream labels.
python mimic4preprocessing/scripts_downstreams/01_preproc_vaso.py
#   -> $MIMIC4_ROOT/icu/inputevents_{train,test}_{vaso,existence}.pkl
python mimic4preprocessing/scripts_downstreams/02_preproc_urine_output.py
#   -> $MIMIC4_ROOT/icu/outputevents_huo.pkl

# 03 — split each patient's stream per hospital admission and generate the
#      per-admission label tables for all 9 downstream tasks.
python mimic4preprocessing/scripts_downstreams/03_build_downstream_labels.py
#   -> $PFM_DATA_ROOT/PFM_downstream/{addQ,NOadd}/{train,test}/<id[:3]>/<id>/adm*.csv (+ label_*_adm*.csv)
```

> Step 03 also reads `$MIMIC4_ROOT/icu/chartevents_arrest.pkl` for the
> cardiac-arrest label — see the prerequisites note above.

### 1.5 Tokenization to tensors

The CSV event streams are tokenized into fixed-length (`sample_max_length=2048`,
`sample_overlap=512`), padded token tensors by
`pfm_mimic4/dataset/csvs_to_tensor.py` (pretraining) and
`csvs_to_tensor_dt.py` / `csvs_to_tensor_dt_eicu.py` (downstream). **You normally
do not run these by hand**: the data loader (`pfm_mimic4/dataset/qa_dataset.py`)
builds and caches the tensors automatically the first time you launch pretraining
or evaluation —

* pretraining tensors are cached under `$PFM_DATA_ROOT/PFM_pretraining/tensor_saved/…`;
* downstream tensors under `$PFM_DATA_ROOT/PFM_downstream/tensor_dt_saved/…`,

keyed by cohort, binning scheme, `seq_gen`, and token-sharing. To pre-build (or
inspect) them explicitly, the builders are runnable standalone, e.g.:

```bash
# pretraining tensors for OURS (shared-token): bin10_exp1_th10, addQ
python pfm_mimic4/dataset/csvs_to_tensor.py --seq_gen addQ --share_tokens 1 --bin bin10_exp1_th10 --pe_baseline None
# downstream tensors (MIMIC-IV):
python pfm_mimic4/dataset/csvs_to_tensor_dt.py --seq_gen NOadd --bin bin10_exp1_th10 --pe_baseline None
```

The token vocabulary mixes **categorical** tokens (meta / question / variable
identifiers) with **binned numeric values**: each measurement is mapped to one
of *N* percentile bins whose edges are the committed thresholds
(`bin{N}_exp{E}_th{T}`; `exp0` = plain percentiles, `exp1` = density-weighted —
the OURS setting). See [Configuration reference](#configuration-reference).

---

## Step 2 — Pretraining

The proposed method uses objective **`G2DYDTSP`** with binning
**`bin10_exp1_th10`**, in two token-sharing variants. Two launcher scripts wrap
`pfm_mimic4/main.py`: each waits for free GPUs, then runs `main.py` under
`torchrun` (DDP), sweeping the learning rate over `[5e-4, 1e-4, 5e-5, 1e-5]`.
Regularization is fixed to the paper setting (`model_dropout=0.1`,
`mask_feature_p=0.1`, `mask_token_p=0.1`), together with a 24-hour
next-event horizon, a 40-dim multi-cycle time-RoPE, and temperature adjustment.

**Before launching**, open the launcher and set the two paths at the top of
`main()`:

```python
DATA_DIR       = "/path/to/PFM_pretraining/tensor_saved/"   # where tensors are built/cached
CHECKPOINT_DIR = "/path/to/result_pretrained/"              # where checkpoints + logs go
```

```bash
# shared-token variant   (share_tokens=1, seq_gen=addQ)  — OURS
python pfm_mimic4/scripts/OURS.py         --gpus 0,1,2,3 --num-gpus 4

# no-share variant       (share_tokens=0, seq_gen=NOadd) — Xshare
python pfm_mimic4/scripts/Xshare_OURS.py  --gpus 0,1,2,3 --num-gpus 4
```

`--gpus` is a comma-separated device list and `--num-gpus` the number of GPUs per
run (the DDP world size). Each run creates a checkpoint folder named after its
configuration, e.g.

```
$CHECKPOINT_DIR/max_len2048_overlap512_h512_h8_l6_ff2048/
    fcriteria1_bin10_exp1_th10_share1_addQ_G2DYDTSP_rope:U1M1TS40_<TIMESTAMP>/
        check_points/best_model.pt
        results/…  args.json  configs.json
```

Note the `<TIMESTAMP>` — you will refer to this folder name in Step 3.

## Step 3 — Downstream evaluation

`downstream_tasks_probing.py` re-invokes `main.py` with `--eval_load_pretrained`
to finetune/probe a pretrained checkpoint on the MIMIC-IV downstream tasks. The
downstream tensors are built automatically on the first run from the
per-admission label CSVs produced in [Step 1.4](#14-downstream-task-labels-scripts_downstreams-0103).

The evaluated tasks (one head each in `modules/dt_head.py`) are:

| Task | Head | Description |
| --- | --- | --- |
| IHM | `ihm` | in-hospital mortality |
| Decompensation (death) | `dec_death` | imminent death |
| Decompensation (arrest) | `dec_arrest` | imminent cardiac arrest *(needs `chartevents_arrest.pkl`)* |
| ICU transfer | `icu_in` | transfer into the ICU |
| Prognosis | `prognosis` | readmission windows |
| Length of stay | `los` | remaining LOS bucket |
| Phenotyping | `phe` | 25 HCUP-CCS phenotypes |
| Vasopressor | `vaso` | vasopressor requirement |
| Urine output | `huo` | oliguria / anuria |

**Before launching**, set the checkpoint location at the top of `main()`:

```python
EVAL_SAVED_PATH = "/path/to/result_pretrained/"        # = the CHECKPOINT_DIR from Step 2
last_folder = [                                        # the run folder to evaluate
    'max_len2048_overlap512_h512_h8_l6_ff2048/'
    'fcriteria1_bin10_exp1_th10_share1_addQ_G2DYDTSP_rope:U1M1TS40_<TIMESTAMP>',
]
```

Replace `<TIMESTAMP>` with the folder printed at the end of your pretraining run.
`eval_ft_range` selects the protocol (`0` = linear probe on a frozen backbone,
`3` = full finetuning); the launcher sweeps `eval_finetune_lr`.

```bash
# MIMIC-IV downstream tasks
python pfm_mimic4/scripts/downstream_tasks_probing.py       --gpus 0 --num-gpus 1

# eICU cross-dataset transfer (requires the eICU downstream tensors; see prerequisites)
python pfm_mimic4/scripts/downstream_tasks_probing_eICU.py  --gpus 0 --num-gpus 1
```

## Configuration reference

The main knobs on `main.py` (and the tensor builders) and their per-variant
values:

| Argument | OURS (shared) | Xshare (no-share) | ETHOS (gen. baseline) |
| --- | --- | --- | --- |
| `--objective` | `G2DYDTSP` | `G2DYDTSP` | `NTP` |
| `--pe_baseline` | `None` | `None` | `ETHOS` |
| `--bin` | `bin10_exp1_th10` | `bin10_exp1_th10` | `bin10_exp0_th10` |
| `--share_tokens` | `1` | `0` | `1` |
| `--seq_gen` | `addQ` | `NOadd` | `addQ` |
| `--use_rope` | `1` | `1` | `0` |

* **`--objective`** — `G2DYDTSP` is the proposed time-aware generative objective
  (next token **+** next-event time). `NTP` is plain next-token prediction; it is
  used by the ETHOS baseline **and** is forced internally for every downstream
  evaluation, so its code path is core infrastructure (not a leftover baseline).
* **`--bin`** — value binning `bin{N}_exp{E}_th{T}`: *N* percentile bins,
  density-weight exponent *E* (`exp0` = no weighting), weight-clip threshold *T*.
  Thresholds live in `mimic4preprocessing/unit_value_cleaning/data/`.
* **`--seq_gen` / `--share_tokens`** — the two sequence layouts written by step 05
  (`addQ`, `NOadd`) and whether numeric bins share a common token sub-space.

## Baselines

This release trains and evaluates **OURS** (`objective=G2DYDTSP`) only; the
paper's other neural baselines and the extra objective / time-embedding variants
have been removed for clarity.

The single retained baseline is **ETHOS**. Its launcher
`pfm_mimic4/scripts/NTP_ETHOS.py` (`objective=NTP`, `pe_baseline=ETHOS`,
`use_rope=0`, `bin=bin10_exp0_th10`) pretrains it through `main.py` under
`torchrun`, exactly like the OURS launchers. ETHOS uses a learned absolute
position embedding instead of RoPE, and its age/interval tokens are added by
`pfm_mimic4/dataset/ETHOS_row_add.py`.

A classical tabular baseline (logistic regression / tree ensembles) remains in
`pfm_mimic4/ML_method/ihm.py` (install the optional deps in `requirements.txt`).

## Acknowledgements

The MIMIC-IV extraction code under `mimic4preprocessing/` is adapted from
[YerevaNN/mimic3-benchmarks](https://github.com/YerevaNN/mimic3-benchmarks)
(Harutyunyan et al., *Scientific Data*, 2019). Please cite that work and the
MIMIC-IV database if you use this preprocessing pipeline.

## Citation

```bibtex
@inproceedings{tcf2026,
  title     = {Time-Conditioned Foreseeing: An EHR-Specific Foundation Model for Irregular Dynamics and Calendrical Time},
  author    = {Bong Gyun Kang, Junyong Ahn, Hyeongrok Han, Sungroh Yoon},
  booktitle = {International Conference on Machine Learning (ICML)},
  year      = {2026}
}
```

## License

See [LICENSE](LICENSE). The extraction code retains the upstream MIT license
(Copyright (c) 2017 YerevaNN); update the copyright/authorship before release.
