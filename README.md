# CiSS 2.0 — Circular Sustainability Scorecard (review package)

Anonymized supplementary material for a manuscript under double-anonymized review.
Author names, affiliations and identifiers have been removed.

CiSS 2.0 measures the degree of **balance** among sustainability dimensions of an
organization (here: economic-financial, socio-environmental and governance) using the
Lorenz curve and the Gini coefficient: CiSS = 1 - Gini over the dimension scores, and
SC = 1 - CiSS. It measures balance among dimensions, not their level.

## Contents

| Path | What it is |
|---|---|
| `ciss2.py` | General implementation (Phase 1) with the numerical check against a reference spreadsheet and a Lorenz-curve plot. |
| `lorenz_ciss2.png` | Output of `python ciss2.py --save lorenz_ciss2.png`. |
| `phase3/` | Code, inputs, outputs and tests of the empirical application to 22 companies (Phase 3). See `phase3/README.md`. |

## Requirements

Python 3.8+, `numpy` (Phase 3), `matplotlib` (plots).

## Usage

```bash
python ciss2.py                       # demo + Lorenz curve
python ciss2.py --no-plot             # demo without chart
python ciss2.py --save fig.png        # saves the chart
python ciss2.py --generic             # generic 5-dimension example

cd phase3 && python test_ciss.py && python analise.py   # reproduces all Phase 3 results
```

## Citation and license

Citation details and the final license will be added after the review process.
