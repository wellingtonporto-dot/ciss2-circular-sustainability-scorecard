# phase2/ — Content validation (Phase 2): questionnaire, protocol and aggregated results

This folder belongs to the anonymous review package of the manuscript. It contains the instrument and the aggregated results of the expert panel (content validation, Phase 2). **No respondent-level data are shared**, to preserve the anonymity of the respondents; names and institutions of the research team and the ethics approval number are omitted in this review version.

| File | Content |
|---|---|
| `S1_questionnaire_PT_anonymized.pdf` | Supplementary Material S1. Blank questionnaire exactly as administered (Portuguese; identification of the team, institution and approval number removed). |
| `S1_questionnaire_EN_courtesy_translation.docx` / `.pdf` | Courtesy translation of S1 into English for reviewers. The Portuguese version is the one administered. |
| `S2_validation_protocol.docx` / `.pdf` | Supplementary Material S2. Four-phase validation protocol of CiSS 2.0 (design, decision rules, recruitment, analysis, deviations and limitations). |
| `data/ivc_items.csv` | Item-level content validity of the 17 indicators (ratings of 3 or 4, number of raters, I-CVI, modified kappa, status). Table 2 of the manuscript. |
| `data/likert_items.csv` | Agreement with the methodological decisions and structure (five-point scale): n, % agreement, median. Table 3 of the manuscript. |
| `data/structure_items.csv` | Structural correspondence and fit of the dimensional structure (four-point scale): ratings, n, I-CVI. Table 4 of the manuscript. |

Notes: indicator items were optional in the questionnaire, so `n_raters` ranges from 8 to 9 per indicator. The panel has nine valid respondents out of 30 invited. Phase 1 (unit tests) is in the root of the repository (`ciss2.py`) and Phase 3 (secondary data of 22 companies) in `phase3/`.
