# Phase 3 — application to 22 non-financial companies

Convenience sample of 22 non-financial companies of a Brazilian sustainability equity index
portfolio, using 2024 public reports. Financial firms were excluded because ROIC (EF4) does not apply.

## Reproduce

```bash
python test_ciss.py     # unit tests (equality -> CiSS = 1; concentration; order invariance; scale; CiSS = 1 - Gini)
python analise.py       # all analyses; random seed 20261120; writes resultados.json
```

Only `numpy` is required (`openpyxl` is also needed for the agreement scripts below). `resultados.json` in this folder is the output of that run.

## Files

| File | Content |
|---|---|
| `ciss.py` | Steps 0-7 and Step 0b (min-max rescaling across the sample, with direction inversion for EF3, SA2, SA5). |
| `test_ciss.py` | Tests of the implementation. |
| `analise.py` | Scores, CiSS, weight sensitivity (one-at-a-time and Monte Carlo), normalization sensitivity, discrimination and consistency analyses. |
| `coleta.json` | Extracted values per company and indicator, with unit, page, note and source file name. |
| `gv.json` | Governance rubric coding (four criteria per indicator, 0/1) with supporting pages and notes. |
| `fin2024.json` | Financial inputs for EF4 (ROIC): revenue, EBIT, invested capital, tax rate. |
| `data/*.csv` | The same material in tabular form (`Dados`, `Financeiro`, `Rubricas`, `Matriz_bruta`, `Resultados`, `Cobertura`, `Sensibilidade`). |
| `screening/` | Keyword screening used as an aid to locate passages in the reports (`gv.py`, `ap.py`, `ap2.py`). The decision on each rubric criterion was made by a person and is documented in `gv.json`. |

## Notes

* Company reports are not redistributed. `Fonte (arquivo)` / `fonte` give the file name and `Página` / `pag` the page.
  The screening scripts expect plain-text extractions of those reports in `raw/` (not included).
* Core indicators operationalized: EF3, EF4, SA1, SA2, SA3, SA5, GV1, GV2, GV3, GV5 (equal weights).
* Rubric coding: `Coder 1` is an AI assistant (see the AI-use declaration in the manuscript).
  A second, human coder independently coded four governance indicators in six companies (24 company-indicator units, 96 criterion judgments); see "Agreement between coders" below.
* Column and sheet names are in Portuguese.

## Agreement between coders

```bash
python concordancia_gv.py data/Dupla_codificacao_GV.xlsx --out agreement   # percent agreement, Cohen's kappa, Gwet's AC1, ICC(2,1)/(3,1), bootstrap CIs (seed 20261120)
python sens_gv.py                                                          # CiSS recomputed with the second coding (three scenarios); writes agreement/sensibilidade_GV.json
```

| File | Content |
|---|---|
| `concordancia_gv.py` | Agreement statistics between the first coding (`gv.json`) and the second coder's sheet. `--selftest` checks the formulas against reference values. |
| `sens_gv.py` | Sensitivity of the CiSS to the choice of coding: second coder replaces the first; criterion counts only if both coders marked it (minimum); criterion counts if either did (maximum). Does not change `resultados.json`. |
| `data/Dupla_codificacao_GV.xlsx` | Second coder's sheet (criterion 0/25 per company and indicator, page and notes). |
| `agreement/concordancia_GV_resultados.json` | Agreement statistics and confidence intervals. |
| `agreement/concordancia_GV_discordancias.csv` | The 18 criterion-level disagreements. |
| `agreement/sensibilidade_GV.json` | Output of `sens_gv.py`. |

The first coding is used in all main results; the second coding is reported as a reliability check and a sensitivity scenario (manuscript, Section 4.4.7).
