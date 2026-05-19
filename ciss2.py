"""
CiSS 2.0 — Circular Sustainability Scorecard (Versão Genérica)
===============================================================
Algoritmo computacional para mensuração do grau de equilíbrio entre
dimensões de sustentabilidade circular em organizações de qualquer setor.

Fundamentação:
  - Porto (2021): modelo CiSS original para o setor industrial
  - Ijiri (1975): Teoria da Mensuração Contábil — formalização axiomática
  - Geissdoerfer et al. (2017): Economia Circular × Sustentabilidade
  - Lynn (1986): protocolo IVC de validação de conteúdo

Normalização por logaritmo natural (Passo 0):
  - ln(valor)       → variáveis contínuas positivas sem teto (ex.: volumes em R$)
  - ln(1 + valor)   → variáveis que podem ser zero (ex.: nº de iniciativas)
  - sem transf.     → variáveis em escala fechada (ex.: % , scores 0-100, índices)

Interpretação:
  CiSS ∈ [0, 1]
    CiSS → 1 : equilíbrio máximo entre dimensões (sustentabilidade circular plena)
    CiSS → 0 : concentração extrema em poucas dimensões (desequilíbrio)
  SC = 1 − CiSS (gap de sustentabilidade circular)

Uso:
  python ciss2.py               → roda o demo WEG 2018/2019 e exibe a curva
  python ciss2.py --no-plot     → roda o demo sem abrir janela gráfica
  python ciss2.py --save path   → salva o gráfico no caminho indicado
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ── Tipo de escala (determina a normalização a aplicar) ───────────────────────

class ScaleType(Enum):
    """
    Classificação do tipo de escala de cada indicador.

    OPEN_POSITIVE : variável contínua, sempre > 0, sem teto  → ln(valor)
    OPEN_ZERO     : variável contínua, pode ser 0             → ln(1 + valor)
    CLOSED        : percentual, score ou índice com teto      → sem transformação
    """
    OPEN_POSITIVE = auto()   # ln(valor)
    OPEN_ZERO     = auto()   # ln(1 + valor)
    CLOSED        = auto()   # valor (sem transformação)


# ── Estruturas de dados ───────────────────────────────────────────────────────

@dataclass
class Indicator:
    """
    Um indicador individual dentro de uma dimensão do MBL.

    Parâmetros
    ----------
    name       : nome do indicador
    value      : valor bruto observado (antes da normalização)
    weight     : peso relativo do indicador dentro da dimensão (wj)
    scale_type : tipo de escala — determina a transformação ln aplicada
    ec_principle: princípio da EC ao qual o indicador se ancora
                  ('fechamento', 'desaceleracao' ou 'estreitamento')
    """
    name        : str
    value       : float
    weight      : float
    scale_type  : ScaleType = ScaleType.CLOSED
    ec_principle: str = ""

    @property
    def normalized_value(self) -> float:
        """
        PASSO 0 — Normalização por logaritmo natural.

        Aplica a transformação adequada conforme o tipo de escala do indicador,
        garantindo comparabilidade entre grandezas distintas sem perder a
        interpretação econômica dos dados (Ijiri, 1975 — Axioma 3: aditividade).

        Casos:
          OPEN_POSITIVE → ln(valor)       [valor deve ser > 0]
          OPEN_ZERO     → ln(1 + valor)   [evita ln(0) = −∞]
          CLOSED        → valor           [escala já comparável]
        """
        if self.scale_type == ScaleType.OPEN_POSITIVE:
            if self.value <= 0:
                raise ValueError(
                    f"Indicador '{self.name}': escala OPEN_POSITIVE requer valor > 0. "
                    f"Recebido: {self.value}. Use OPEN_ZERO para valores que podem ser 0."
                )
            return math.log(self.value)

        elif self.scale_type == ScaleType.OPEN_ZERO:
            if self.value < 0:
                raise ValueError(
                    f"Indicador '{self.name}': valor negativo não é permitido "
                    f"para escala OPEN_ZERO. Recebido: {self.value}."
                )
            return math.log(1 + self.value)

        else:  # CLOSED
            return self.value


@dataclass
class Dimension:
    """
    Uma dimensão do Multiple Bottom Line (MBL) adaptado.

    O score Xi é a média ponderada dos indicadores normalizados.
    As dimensões são configuráveis: o pesquisador define quais usar
    conforme o setor e o contexto de aplicação.

    Exemplos de dimensões:
      Setor genérico : Econômica, Socioambiental, Governança
      Setor industrial: Econômica, Ambiental, Social, Ética, Governança,
                        ERP, RCN, PPM  (Porto, 2021)
      Setor financeiro: Econômico-Financeira, Socioambiental, Governança ESG
    """
    name       : str
    indicators : list[Indicator]
    score      : float = field(init=False)

    def __post_init__(self):
        self.score = self._compute_score()

    def _compute_score(self) -> float:
        """
        PASSO 1 — Score dimensional Xi.

        Xi = Σ(wj × indicator_norm_j) / Σ wj

        Os pesos podem ser definidos por:
          (a) Análise de Componentes Principais (PCA) — objetivo, replicável
          (b) Julgamento de especialistas (IVC) — Lynn (1986)
          (c) Pesos iguais — quando não há base para diferenciação
        """
        total_w = sum(ind.weight for ind in self.indicators)
        if total_w == 0:
            raise ValueError(f"Dimensão '{self.name}': soma dos pesos é zero.")
        return sum(ind.weight * ind.normalized_value
                   for ind in self.indicators) / total_w


@dataclass
class LorenzRow:
    """Uma linha da tabela Lorenz — corresponde a uma dimensão no rank i."""
    rank     : int
    name     : str
    xi       : float    # score dimensional
    pi       : float    # fração acumulada de dimensões = i/n   (eixo X)
    phi_i    : float    # fração individual do score total = Xi/ΣXi
    phi_cum  : float    # fração acumulada ΣΦi               (eixo Y)
    phi_pair : float    # Φ(i-1) + Φ(i) — par trapezoidal
    d_i      : float    # |Pi − ΣΦi| — discriminante


@dataclass
class CiSSResult:
    """Resultado completo de um cálculo CiSS para uma organização/período."""
    organization    : str
    year            : int
    n_dimensions    : int
    mean_score      : float
    total_lorenz_sum: float
    ciss            : float
    sc              : float
    lorenz_table    : list[LorenzRow]

    def summary(self, language: str = "pt") -> str:
        if language == "en":
            header = (f"\n{'='*64}\n"
                      f"  CiSS 2.0 — {self.organization}  |  Year {self.year}\n"
                      f"{'='*64}\n"
                      f"  Dimensions     : {self.n_dimensions}\n"
                      f"  Mean score (μ) : {self.mean_score:.6f}\n"
                      f"  Lorenz sum     : {self.total_lorenz_sum:.6f}\n"
                      f"  CiSS           : {self.ciss:.6f}\n"
                      f"  SC (1 − CiSS)  : {self.sc:.6f}\n")
            col = f"\n  {'Rank':<5} {'Dimension':<14} {'Xi':>10} {'Pi':>7} {'Φi':>8} {'ΣΦi':>8} {'|Pi−ΣΦi|':>10}"
        else:
            header = (f"\n{'='*64}\n"
                      f"  CiSS 2.0 — {self.organization}  |  Ano {self.year}\n"
                      f"{'='*64}\n"
                      f"  Dimensões      : {self.n_dimensions}\n"
                      f"  Média (μ)      : {self.mean_score:.6f}\n"
                      f"  Soma de Lorenz : {self.total_lorenz_sum:.6f}\n"
                      f"  CiSS           : {self.ciss:.6f}\n"
                      f"  SC (1 − CiSS)  : {self.sc:.6f}\n")
            col = f"\n  {'Rank':<5} {'Dimensão':<14} {'Xi':>10} {'Pi':>7} {'Φi':>8} {'ΣΦi':>8} {'|Pi−ΣΦi|':>10}"

        rows = [f"\n  {'-'*60}"]
        for r in self.lorenz_table:
            rows.append(
                f"  {r.rank:<5} {r.name:<14} {r.xi:>10.4f} "
                f"{r.pi:>7.4f} {r.phi_i:>8.4f} {r.phi_cum:>8.4f} {r.d_i:>10.4f}"
            )
        rows.append(f"  {'='*64}\n")
        return header + col + "".join(rows)


# ── Algoritmo principal ───────────────────────────────────────────────────────

def build_lorenz_table(dimensions: list[Dimension]) -> list[LorenzRow]:
    """
    PASSOS 2, 3 e 4 — Ordenação e frações da Curva de Lorenz.

    Passo 2: ordena as dimensões em ordem crescente de Xi
             (dimensão com menor score vem em rank i = 1).
    Passo 3: Pi = i / n  (fração acumulada de dimensões — eixo X da Lorenz).
    Passo 4: Φi = Xi / ΣXi  (fração individual do score total)
             ΣΦi acumulado  (fração acumulada — eixo Y da Lorenz).
    """
    n = len(dimensions)
    if n < 2:
        raise ValueError("O CiSS requer ao menos 2 dimensões.")

    sorted_dims = sorted(dimensions, key=lambda d: d.score)
    total       = sum(d.score for d in sorted_dims)
    if total == 0:
        raise ValueError("Soma dos scores é zero — impossível calcular frações.")

    mean   = total / n
    rows   = []
    phi_prev = 0.0

    for i, dim in enumerate(sorted_dims, start=1):
        pi      = i / n
        phi_i   = dim.score / total
        phi_cum = phi_prev + phi_i
        rows.append(LorenzRow(
            rank=i, name=dim.name, xi=dim.score,
            pi=pi, phi_i=phi_i, phi_cum=phi_cum,
            phi_pair=phi_prev + phi_cum,
            d_i=abs(pi - phi_cum),
        ))
        phi_prev = phi_cum

    return rows


def compute_ciss(
    dimensions   : list[Dimension],
    organization : str = "Organização",
    year         : int = 0,
) -> CiSSResult:
    """
    Função principal — executa os 7 passos do algoritmo CiSS 2.0.

    Passos
    ------
    0  Normalização por ln               [Indicator.normalized_value]
    1  Score Xi = média ponderada        [Dimension._compute_score]
    2  Ordenação ascendente por Xi       [build_lorenz_table]
    3  Pi = i/n                          [build_lorenz_table]
    4  Φi = Xi/ΣXi; ΣΦi acumulado       [build_lorenz_table]
    5  lorenz_sum = Σ (Φ(i-1) + Φi)     [abaixo]
    6  CiSS = lorenz_sum / n             [abaixo]
    7  SC   = 1 − CiSS                   [abaixo]

    Parâmetros
    ----------
    dimensions   : lista de objetos Dimension configurados pelo pesquisador
    organization : nome da organização (para relatórios)
    year         : ano de referência dos dados

    Retorna
    -------
    CiSSResult com todos os campos calculados e a tabela Lorenz completa.
    """
    n     = len(dimensions)
    table = build_lorenz_table(dimensions)

    # Passo 5 — soma trapezoidal de Lorenz
    lorenz_sum = sum(r.phi_pair for r in table)

    mean_score = sum(r.xi for r in table) / n

    # Passo 6 — CiSS
    ciss = lorenz_sum / n

    # Passo 7 — SC (gap de sustentabilidade circular)
    sc = 1.0 - ciss

    return CiSSResult(
        organization=organization, year=year,
        n_dimensions=n, mean_score=mean_score,
        total_lorenz_sum=lorenz_sum,
        ciss=ciss, sc=sc,
        lorenz_table=table,
    )


# ── Utilitários ───────────────────────────────────────────────────────────────

def lorenz_points(result: CiSSResult) -> tuple[list[float], list[float]]:
    """Retorna (x, y) para plotar a Curva de Lorenz, incluindo a origem (0, 0)."""
    x = [0.0] + [r.pi      for r in result.lorenz_table]
    y = [0.0] + [r.phi_cum for r in result.lorenz_table]
    return x, y


def compare(a: CiSSResult, b: CiSSResult) -> str:
    """Retorna string comparando dois resultados CiSS."""
    dc = b.ciss - a.ciss
    ds = b.sc   - a.sc
    dir_ = "melhorou ↑" if ds > 0 else "piorou ↓" if ds < 0 else "estável →"
    return (
        f"\n  Comparação  {a.year} → {b.year}  ({a.organization})\n"
        f"  ΔCiSS : {dc:+.6f}\n"
        f"  ΔSC   : {ds:+.6f}  ({dir_})\n"
    )


def validate_against_reference(
    result: CiSSResult,
    expected_lorenz_sum: float,
    expected_sc: float,
    tol: float = 1e-6,
) -> bool:
    """
    Fase 1 do protocolo de validação computacional:
    verifica se o resultado reproduz o gabarito numérico de Porto (2021)
    com precisão de seis casas decimais.
    """
    ok_sum = math.isclose(result.total_lorenz_sum, expected_lorenz_sum, rel_tol=tol)
    ok_sc  = math.isclose(result.sc,               expected_sc,         rel_tol=tol)
    status = "PASS" if (ok_sum and ok_sc) else "FAIL"
    print(f"  {result.year}: Soma Lorenz {'✓' if ok_sum else '✗'}  |  "
          f"SC {'✓' if ok_sc else '✗'}  →  {status}")
    return ok_sum and ok_sc


# ── Curva de Lorenz ───────────────────────────────────────────────────────────

def plot_lorenz(
    results   : list[CiSSResult],
    title     : str = "Curva de Lorenz — CiSS 2.0",
    save_path : Optional[str] = None,
) -> None:
    """
    Plota a Curva de Lorenz para um ou mais resultados CiSS.

    Cada resultado é desenhado como uma linha colorida com os pontos
    das dimensões anotados. A diagonal de perfeita igualdade serve
    como linha de referência. A área sombreada entre cada curva e a
    diagonal ilustra o grau de desequilíbrio.

    Parâmetros
    ----------
    results   : lista de CiSSResult (uma curva por resultado)
    title     : título do gráfico
    save_path : se fornecido, salva a figura neste caminho; caso contrário, exibe
    """
    try:
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec
    except ImportError:
        print("\n  [!] matplotlib não encontrado.")
        print("      Instale com:  pip install matplotlib\n")
        return

    COLOURS = ["#1A3A5C", "#C0392B", "#2D6A4F", "#7B3F00", "#6B2D5E"]
    ALPHAS  = [0.15, 0.12, 0.10, 0.08, 0.06]

    fig = plt.figure(figsize=(13, 7), facecolor="#F7F4EF")
    gs  = GridSpec(1, 2, figure=fig, width_ratios=[2.2, 1],
                   left=0.07, right=0.97, bottom=0.11, top=0.88, wspace=0.07)
    ax  = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    for sp in (ax, ax2):
        sp.set_facecolor("#FDFCFA")
        for s in sp.spines.values():
            s.set_color("#C8C0B4")

    # Diagonal de perfeita igualdade
    ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1.2,
            color="#A09888", alpha=0.7, label="Igualdade perfeita (referência)",
            zorder=1)

    # Grade
    ax.set_xticks([i/4 for i in range(5)])
    ax.set_yticks([i/4 for i in range(5)])
    ax.grid(True, linestyle=":", linewidth=0.6, color="#DDD8D0", alpha=0.8)

    legend_handles = []

    for idx, result in enumerate(results):
        colour = COLOURS[idx % len(COLOURS)]
        alpha  = ALPHAS[idx  % len(ALPHAS)]
        x, y   = lorenz_points(result)
        label  = (f"{result.organization} {result.year}  "
                  f"(CiSS={result.ciss:.4f}  SC={result.sc:.4f})")

        # Área sombreada entre a curva e a diagonal
        ax.fill_between(x, y, x, alpha=alpha, color=colour, zorder=2)

        # Curva de Lorenz
        line, = ax.plot(x, y, color=colour, linewidth=2.2,
                        marker="o", markersize=5,
                        markerfacecolor=colour, markeredgewidth=0,
                        zorder=4, label=label)

        # Anotações das dimensões em cada ponto
        for row in result.lorenz_table:
            ox = 0.012 if row.pi < 0.85 else -0.015
            ax.annotate(
                row.name,
                xy=(row.pi, row.phi_cum),
                xytext=(row.pi + ox, row.phi_cum + 0.018),
                fontsize=7.5, color=colour, alpha=0.85,
                fontfamily="monospace", zorder=5,
            )

        legend_handles.append(line)

    ax.set_xlim(-0.02, 1.06)
    ax.set_ylim(-0.02, 1.10)
    ax.set_xlabel("Pi  —  Fração acumulada de dimensões",
                  fontsize=10, color="#555555", labelpad=8)
    ax.set_ylabel("ΣΦi  —  Fração acumulada dos scores",
                  fontsize=10, color="#555555", labelpad=8)
    ax.set_title(title, fontsize=13, fontweight="bold",
                 color="#1C1A17", pad=14)
    ax.legend(handles=legend_handles, loc="upper left", fontsize=8.5,
              framealpha=0.92, edgecolor="#C8C0B4", fancybox=False)

    # Painel direito — tabela resumo
    ax2.set_xlim(0, 1); ax2.set_ylim(0, 1)
    ax2.set_xticks([]); ax2.set_yticks([])
    ax2.set_title("Resumo", fontsize=10, color="#555555", pad=10, loc="left")

    row_h = 0.09
    top   = 0.93
    col_x = [0.02, 0.30, 0.58, 0.80]
    for cx, hd in zip(col_x, ["Organização/Ano", "CiSS", "SC", "Dims"]):
        ax2.text(cx, top, hd, fontsize=7.5, fontweight="bold",
                 color="#1A3A5C", va="top", fontfamily="monospace")
    ax2.axhline(y=top - 0.025, xmin=0.02, xmax=0.98,
                color="#C8C0B4", linewidth=0.8)

    for i, result in enumerate(results):
        yp    = top - 0.06 - i * row_h
        colour = COLOURS[i % len(COLOURS)]
        vals  = [f"{result.organization} {result.year}",
                 f"{result.ciss:.4f}", f"{result.sc:.4f}",
                 str(result.n_dimensions)]
        if i % 2 == 0:
            ax2.axhspan(yp - 0.005, yp + row_h * 0.6,
                        xmin=0.01, xmax=0.99,
                        color=colour, alpha=0.06)
        for cx, val in zip(col_x, vals):
            ax2.text(cx, yp, val, fontsize=7.5, color=colour,
                     va="top", fontfamily="monospace")

    note_y = top - 0.06 - len(results) * row_h - 0.05
    ax2.text(0.02, note_y,
             "Interpretação:\nCiSS → 1 : equilíbrio\nCiSS → 0 : concentração\nSC = 1 − CiSS",
             fontsize=7, color="#777777", va="top", linespacing=1.6,
             bbox=dict(boxstyle="round,pad=0.4", facecolor="#F0EDE8",
                       edgecolor="#C8C0B4", linewidth=0.8))

    fig.text(0.5, 0.025,
             "Fonte: CiSS 2.0 — adaptado de Porto (2021)  |  "
             "Fundamentação: Ijiri (1975), Geissdoerfer et al. (2017)",
             ha="center", fontsize=7.5, color="#999999")

    plt.tight_layout(rect=[0, 0.04, 1, 1])

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        print(f"\n  Gráfico salvo em: {save_path}")
    else:
        plt.show()

    plt.close(fig)


# ── Demo — reproduz o gabarito numérico de Porto (2021) ──────────────────────

def _demo(show_plot: bool = True, save_path: Optional[str] = None) -> None:
    """
    Reproduz os resultados WEG 2018 e 2019 da planilha Excel de Porto (2021).

    Cada dimensão é representada por um único indicador com peso = 1,
    cujo valor já é o Xi calculado na planilha original.
    A Fase 1 do protocolo de validação é executada automaticamente:
    o script verifica se os valores reproduzem o gabarito com precisão
    de seis casas decimais (Δ < 1×10⁻⁶).
    """

    def dim(name: str, xi: float, scale: ScaleType = ScaleType.CLOSED,
            ec: str = "") -> Dimension:
        """
        No gabarito de Porto (2021), os valores já são os scores Xi finais
        calculados pela planilha Excel (médias ponderadas já transformadas).
        Por isso usamos CLOSED — sem nova transformação ln.
        """
        return Dimension(
            name=name,
            indicators=[Indicator(name=name, value=xi, weight=1.0,
                                  scale_type=scale, ec_principle=ec)]
        )

    # ── WEG 2019 ─────────────────────────────────────────────────────
    dims_2019 = [
        dim("PPM",   1.3786154754352506, ec="estreitamento"),
        dim("Etica", 1.6447744146202172, ec="estreitamento"),
        dim("Soc",   2.1161822038356215, ec="fechamento"),
        dim("ERP",   2.2169159706346120, ec="estreitamento"),
        dim("Gov",   3.3410271206001150, ec="estreitamento"),
        dim("Econ",  3.9876590047712934, ec="estreitamento"),
        dim("Amb",   4.4358360844177470, ec="fechamento"),
        dim("RCN",   4.5930408360298130, ec="desaceleracao"),
    ]

    # ── WEG 2018 ─────────────────────────────────────────────────────
    dims_2018 = [
        dim("PPM",   0.3446538688588127, ec="estreitamento"),
        dim("Soc",   2.5394186446027460, ec="fechamento"),
        dim("Econ",  3.4743959645532070, ec="estreitamento"),
        dim("Amb",   4.8054890914525580, ec="fechamento"),
        dim("ERP",   6.2476722808793610, ec="estreitamento"),
        dim("Etica", 10.965162764134782, ec="estreitamento"),
        dim("Gov",   11.136757068667052, ec="estreitamento"),
        dim("RCN",   15.310136120099374, ec="desaceleracao"),
    ]

    r2019 = compute_ciss(dims_2019, organization="WEG", year=2019)
    r2018 = compute_ciss(dims_2018, organization="WEG", year=2018)

    print(r2019.summary())
    print(r2018.summary())
    print(compare(r2018, r2019))

    # Fase 1 — Validação computacional contra gabarito Excel
    print("  Fase 1 — Validação computacional (gabarito Porto, 2021):")
    validate_against_reference(r2019, 6.17851335375256,  0.22768583078092997)
    validate_against_reference(r2018, 4.86887977427801,  0.3913900282152487)
    print()

    if show_plot:
        print("  Abrindo Curva de Lorenz...")
        print("  (feche a janela para encerrar)\n")
        plot_lorenz(
            results=[r2019, r2018],
            title="Curva de Lorenz — CiSS 2.0  |  WEG 2018 e 2019 (Porto, 2021)",
            save_path=save_path,
        )


# ── Exemplo genérico — como usar o CiSS 2.0 para qualquer organização ────────

def exemplo_generico() -> None:
    """
    Demonstra o uso do CiSS 2.0 para uma organização hipotética
    com as 5 dimensões do MBL original de Porto (2021).

    Ilustra o uso das três regras de normalização por ln:
      Econômica  → indicadores com grandezas abertas (R$)  → OPEN_POSITIVE
      Ambiental  → indicadores que podem ser zero           → OPEN_ZERO
      Social     → misto: abertas e fechadas
      Governança → scores em escala fechada (0-100)         → CLOSED
      Ética      → scores em escala fechada                 → CLOSED
    """
    print("\n" + "="*64)
    print("  Exemplo genérico — 5 dimensões MBL (Porto, 2021)")
    print("="*64)

    dim_econ = Dimension(
        name="Econ",
        indicators=[
            Indicator("Invest. circular (R$)", 5_000_000, weight=0.40,
                      scale_type=ScaleType.OPEN_POSITIVE,
                      ec_principle="estreitamento"),
            Indicator("Receita circular (%)",  18.5, weight=0.30,
                      scale_type=ScaleType.CLOSED,
                      ec_principle="estreitamento"),
            Indicator("ROIC ajustado (%)",     12.3, weight=0.30,
                      scale_type=ScaleType.CLOSED,
                      ec_principle="estreitamento"),
        ]
    )

    dim_amb = Dimension(
        name="Amb",
        indicators=[
            Indicator("Taxa reciclagem (%)",     42.0,  weight=0.35,
                      scale_type=ScaleType.CLOSED,
                      ec_principle="fechamento"),
            Indicator("Emissões GEE (tCO2e)",   1_800,  weight=0.35,
                      scale_type=ScaleType.OPEN_POSITIVE,
                      ec_principle="fechamento"),
            Indicator("Iniciativas amb. (n)",       3,  weight=0.30,
                      scale_type=ScaleType.OPEN_ZERO,
                      ec_principle="desaceleracao"),
        ]
    )

    dim_soc = Dimension(
        name="Soc",
        indicators=[
            Indicator("Empregos circulares (n)",   120,  weight=0.40,
                      scale_type=ScaleType.OPEN_POSITIVE,
                      ec_principle="fechamento"),
            Indicator("Satisfação stakeholders (%)", 74.0, weight=0.35,
                      scale_type=ScaleType.CLOSED,
                      ec_principle="fechamento"),
            Indicator("Iniciativas sociais (n)",      5,  weight=0.25,
                      scale_type=ScaleType.OPEN_ZERO,
                      ec_principle="fechamento"),
        ]
    )

    dim_gov = Dimension(
        name="Gov",
        indicators=[
            Indicator("Score GRI (0-100)",   72.0, weight=0.40,
                      scale_type=ScaleType.CLOSED,
                      ec_principle="estreitamento"),
            Indicator("Score ISE/B3 (0-1)",   0.68, weight=0.35,
                      scale_type=ScaleType.CLOSED,
                      ec_principle="estreitamento"),
            Indicator("Compliance CMN (%)",   85.0, weight=0.25,
                      scale_type=ScaleType.CLOSED,
                      ec_principle="estreitamento"),
        ]
    )

    dim_etica = Dimension(
        name="Etica",
        indicators=[
            Indicator("Score ética fornec. (0-100)", 68.0, weight=0.50,
                      scale_type=ScaleType.CLOSED,
                      ec_principle="estreitamento"),
            Indicator("Certificações éticas (n)",      2,  weight=0.50,
                      scale_type=ScaleType.OPEN_ZERO,
                      ec_principle="estreitamento"),
        ]
    )

    result = compute_ciss(
        [dim_econ, dim_amb, dim_soc, dim_gov, dim_etica],
        organization="Org. Hipotética",
        year=2024,
    )

    print(result.summary())

    # Mostrar os valores normalizados por ln
    print("  Valores normalizados por ln (Passo 0):")
    for dim in [dim_econ, dim_amb, dim_soc, dim_gov, dim_etica]:
        print(f"\n  [{dim.name}]  Xi = {dim.score:.4f}")
        for ind in dim.indicators:
            print(f"    {ind.name:<30} bruto={ind.value:>12.2f}  "
                  f"ln_norm={ind.normalized_value:>8.4f}  "
                  f"escala={ind.scale_type.name:<14}  "
                  f"EC={ind.ec_principle}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args      = sys.argv[1:]
    show      = "--no-plot" not in args
    save_path = None

    if "--save" in args:
        idx = args.index("--save")
        if idx + 1 < len(args):
            save_path = args[idx + 1]
            show      = False

    if "--generic" in args:
        exemplo_generico()
    else:
        _demo(show_plot=show, save_path=save_path)
