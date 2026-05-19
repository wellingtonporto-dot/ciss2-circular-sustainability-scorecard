# ciss2-circular-sustainability-scorecard

# CiSS 2.0 — Circular Sustainability Scorecard
Generic computational algorithm for measuring circular sustainability
in organizations of any sector.

## Description
CiSS 2.0 adapts the Gini Coefficient / Lorenz Curve methodology to measure
the degree of balance between circular sustainability dimensions (Multiple
Bottom Line — MBL) in organizations. Based on Porto (2021) and formalized
under Ijiri's (1975) axiomatic measurement theory.

## Requirements
- Python 3.8+
- matplotlib (`pip install matplotlib`)

## Usage
```bash
python ciss2.py              # runs WEG 2018/2019 demo + Lorenz curve
python ciss2.py --no-plot    # runs demo without chart
python ciss2.py --save fig.png  # saves chart as PNG
python ciss2.py --generic    # runs 5-dimension generic example
```

## Citation
If you use this software in your research, please cite it using the
information in CITATION.cff or as:

> Author (2025). CiSS 2.0 — Circular Sustainability Scorecard [Software].
> Zenodo. https://doi.org/[DOI WILL BE ADDED AFTER ZENODO DEPOSIT]

## License
Creative Commons Attribution 4.0 International (CC BY 4.0)
