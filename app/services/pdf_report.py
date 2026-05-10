from __future__ import annotations
import os
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONTS_DIR = os.path.join(APP_DIR, "fonts")
FONT_PATH = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
FONT_BOLD_PATH = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")

_SYSTEM_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Geneva.ttf",
]
_SYSTEM_BOLD_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]

_font_loaded = False
_BODY_FONT = "Helvetica"
_BOLD_FONT = "Helvetica-Bold"

# A4 portrait usable width with 2cm margins ≈ 482 points
USABLE_WIDTH = 482


def _find_font(primary: str, system_paths: list) -> str | None:
    if os.path.exists(primary):
        return primary
    for p in system_paths:
        if os.path.exists(p):
            return p
    return None


def _ensure_font():
    global _font_loaded, _BODY_FONT, _BOLD_FONT
    if _font_loaded:
        return
    os.makedirs(FONTS_DIR, exist_ok=True)
    reg_path = _find_font(FONT_PATH, _SYSTEM_FONT_PATHS)
    bold_path = _find_font(FONT_BOLD_PATH, _SYSTEM_BOLD_PATHS)
    try:
        if reg_path:
            pdfmetrics.registerFont(TTFont("DejaVuSans", reg_path))
        if bold_path:
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold_path))
        if reg_path and bold_path:
            _BODY_FONT = "DejaVuSans"
            _BOLD_FONT = "DejaVuSans-Bold"
    except Exception:
        pass
    _font_loaded = True


def _styles():
    _ensure_font()
    normal = ParagraphStyle(
        "CustomNormal", fontName=_BODY_FONT, fontSize=10, leading=14,
    )
    heading1 = ParagraphStyle(
        "CustomH1", fontName=_BOLD_FONT, fontSize=14, leading=18, spaceAfter=8,
    )
    heading2 = ParagraphStyle(
        "CustomH2", fontName=_BOLD_FONT, fontSize=12, leading=16, spaceAfter=6,
    )
    small = ParagraphStyle(
        "CustomSmall", fontName=_BODY_FONT, fontSize=9, leading=12,
    )
    cell = ParagraphStyle(
        "CustomCell", fontName=_BODY_FONT, fontSize=8, leading=10,
        wordWrap="CJK", alignment=TA_LEFT, spaceAfter=2,
    )
    header = ParagraphStyle(
        "CustomCellHeader", fontName=_BOLD_FONT, fontSize=8, leading=10,
        wordWrap="CJK", alignment=TA_CENTER, textColor=colors.white,
    )
    cell_center = ParagraphStyle(
        "CustomCellCenter", fontName=_BODY_FONT, fontSize=8, leading=10,
        wordWrap="CJK", alignment=TA_CENTER, spaceAfter=2,
    )
    return {
        "normal": normal, "h1": heading1, "h2": heading2, "small": small,
        "cell": cell, "header": header, "cell_center": cell_center,
    }


def _truncate(text: str, max_chars: int = 40) -> str:
    """Truncate long strings to prevent single-word overflow."""
    if text is None:
        return ""
    text = str(text)
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def _P(text, style):
    """Wrap text in a Paragraph with the given style."""
    return Paragraph(_truncate(text, 60) if isinstance(text, str) else str(text), style)


def _tbl_style(header_rows=1):
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), colors.HexColor("#2d6cdf")),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.white),
        ("FONTNAME", (0, 0), (-1, header_rows - 1), _BOLD_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, header_rows), (-1, -1), _BODY_FONT),
        ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [colors.white, colors.HexColor("#f1f5fb")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9e0ea")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


def generate_report(session_data: dict, output_buffer: BytesIO) -> None:
    """Generate a complete PDF report into output_buffer."""
    _ensure_font()
    st = _styles()

    doc = SimpleDocTemplate(
        output_buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    story = []

    # Support both key names: 'sess' (from session_summary) and 'session' (legacy/tests)
    sess = session_data.get("sess") or session_data.get("session")
    alternatives = session_data.get("alternatives", [])
    experts = session_data.get("experts", [])
    methods = session_data.get("methods", {})
    kendall_w = session_data.get("kendall_w", 0.0)
    cv = session_data.get("cv", {})
    entropy = session_data.get("entropy", {})
    corr_matrix = session_data.get("corr_matrix", {})
    outliers = session_data.get("outliers", [])
    consensus = session_data.get("consensus", [])
    kendall_w_by_round = session_data.get("kendall_w_by_round", {})
    competences = session_data.get("competences", [])
    round_map = session_data.get("round_map", {})
    alt_names = session_data.get(
        "alt_names",
        [a["name"] if hasattr(a, "__getitem__") else str(a) for a in alternatives],
    )

    title = sess["title"] if sess else "Звіт"
    description = sess["description"] if sess else ""
    created_at = sess["created_at"] if sess else ""

    # 1. Title page
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("Звіт сесії експертного оцінювання", st["h1"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f"<b>Назва:</b> {title}", st["normal"]))
    story.append(Paragraph(f"<b>Дата:</b> {created_at}", st["normal"]))
    story.append(Paragraph(f"<b>Кількість експертів:</b> {len(experts)}", st["normal"]))
    story.append(Paragraph(f"<b>Кількість альтернатив:</b> {len(alternatives)}", st["normal"]))
    story.append(Paragraph(f"<b>Сформовано:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", st["normal"]))
    story.append(PageBreak())

    # 2. Task description and evaluation procedure
    story.append(Paragraph("Опис задачі та процедури оцінювання", st["h1"]))
    story.append(Paragraph(description or "—", st["normal"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "Використані методи: Зважений середній бал, Метод Борда, Метод Кондорсе, "
        "Метод Делфі (ітеративний), Метод парних порівнянь (AHP-подібний).",
        st["normal"],
    ))
    story.append(Spacer(1, 0.3 * cm))

    # 3. Alternatives
    story.append(Paragraph("Список альтернатив", st["h1"]))
    alt_rows = [[_P("#", st["header"]), _P("Назва альтернативи", st["header"])]]
    for i, alt in enumerate(alternatives, 1):
        name = alt["name"] if hasattr(alt, "__getitem__") else str(alt)
        alt_rows.append([_P(str(i), st["cell_center"]), _P(name, st["cell"])])
    tbl = Table(alt_rows, colWidths=[40, USABLE_WIDTH - 40])
    tbl.setStyle(_tbl_style())
    story.append(tbl)
    story.append(Spacer(1, 0.4 * cm))

    # 4. Expert competence table
    story.append(Paragraph("Компетентність експертів", st["h1"]))
    comp_map = {c["expert_id"]: c for c in competences} if competences else {}
    comp_header = ["Експерт", "Вага", "Самооцінка", "Взаємна", "Підсумкова"]
    comp_rows = [[_P(h, st["header"]) for h in comp_header]]
    for exp in experts:
        eid = exp["id"]
        c = comp_map.get(eid)
        comp_rows.append([
            _P(_truncate(exp["full_name"], 30), st["cell"]),
            _P(f"{exp['competence']:.2f}", st["cell_center"]),
            _P(f"{c['self_assessment']:.2f}" if c and c["self_assessment"] is not None else "—", st["cell_center"]),
            _P(f"{c['peer_assessment']:.2f}" if c and c["peer_assessment"] is not None else "—", st["cell_center"]),
            _P(f"{c['final_weight']:.2f}" if c and c["final_weight"] is not None else "—", st["cell_center"]),
        ])
    comp_widths = [USABLE_WIDTH - 4 * 60, 60, 60, 60, 60]
    tbl = Table(comp_rows, colWidths=comp_widths)
    tbl.setStyle(_tbl_style())
    story.append(tbl)
    story.append(Spacer(1, 0.4 * cm))

    # 5. Individual expert responses per round
    if round_map and alt_names:
        story.append(Paragraph("Індивідуальні оцінки експертів по раундах", st["h1"]))
        expert_name_map = {e["id"]: e["full_name"] for e in experts}
        n_alts = len(alt_names) or 1
        name_col = 110
        alt_col = (USABLE_WIDTH - name_col) / n_alts
        for rn in sorted(round_map):
            story.append(Paragraph(f"Раунд {rn}", st["h2"]))
            rscores = round_map[rn]
            header = [_P("Експерт", st["header"])] + [
                _P(_truncate(a, 18), st["header"]) for a in alt_names
            ]
            rows = [header]
            for expert_id, score_map in rscores.items():
                name = expert_name_map.get(expert_id, str(expert_id))
                row = [_P(_truncate(name, 25), st["cell"])]
                for aname in alt_names:
                    row.append(_P(f"{score_map.get(aname, 0):.1f}", st["cell_center"]))
                rows.append(row)
            tbl = Table(rows, colWidths=[name_col] + [alt_col] * n_alts)
            tbl.setStyle(_tbl_style())
            story.append(tbl)
            story.append(Spacer(1, 0.3 * cm))
        story.append(PageBreak())

    # 6. Collective results per method — comparison table
    story.append(Paragraph("Порівняльна таблиця результатів методів", st["h1"]))
    if methods and alt_names:
        method_names_list = list(methods.keys())
        n_methods = len(method_names_list)
        alt_col = 110
        method_col = (USABLE_WIDTH - alt_col) / (n_methods + 1)
        header = (
            [_P("Альтернатива", st["header"])]
            + [_P(_truncate(mn, 20), st["header"]) for mn in method_names_list]
            + [_P("Консенсус", st["header"])]
        )
        rows = [header]
        rank_maps = {}
        for mn, res in methods.items():
            ranking = res.get("ranking", [])
            rank_maps[mn] = {a: i + 1 for i, a in enumerate(ranking)}
        consensus_rank = {a: i + 1 for i, a in enumerate(consensus)} if consensus else {}
        for alt in alt_names:
            row = [_P(_truncate(alt, 22), st["cell"])]
            for mn in method_names_list:
                row.append(_P(str(rank_maps.get(mn, {}).get(alt, "—")), st["cell_center"]))
            row.append(_P(str(consensus_rank.get(alt, "—")), st["cell_center"]))
            rows.append(row)
        col_widths = [alt_col] + [method_col] * (n_methods + 1)
        tbl = Table(rows, colWidths=col_widths)
        tbl.setStyle(_tbl_style())
        story.append(tbl)
        story.append(Spacer(1, 0.4 * cm))

    # Individual method score details
    story.append(Paragraph("Детальні результати по методах", st["h1"]))
    for method_name, result in methods.items():
        story.append(Paragraph(method_name, st["h2"]))
        scores = result.get("scores", {})
        winner = result.get("winner", result.get("ranking", [""])[0] if result.get("ranking") else "")
        rows = [[_P("Альтернатива", st["header"]), _P("Бал", st["header"])]]
        for alt_name, val in sorted(scores.items(), key=lambda x: -x[1]):
            rows.append([
                _P(_truncate(alt_name, 50), st["cell"]),
                _P(f"{val:.3f}", st["cell_center"]),
            ])
        tbl = Table(rows, colWidths=[USABLE_WIDTH - 80, 80])
        tbl.setStyle(_tbl_style())
        story.append(tbl)
        story.append(Paragraph(
            f"Рекомендована альтернатива: <b>{_truncate(str(winner), 60)}</b>",
            st["normal"],
        ))
        story.append(Spacer(1, 0.3 * cm))

    story.append(PageBreak())

    # 7. Concordance analysis (W, χ², CV, entropy)
    story.append(Paragraph("Аналіз узгодженості думок експертів", st["h1"]))
    story.append(Paragraph(f"Kendall W (останній раунд): <b>{kendall_w:.3f}</b>", st["normal"]))

    try:
        from app.services.metrics import chi_squared_test
        n_alts = len(alt_names)
        n_experts = len(experts)
        chi_result = chi_squared_test(kendall_w, n_experts, n_alts)
        story.append(Paragraph(
            f"χ² = {chi_result['chi_squared']:.3f}, df = {chi_result['df']}, "
            f"p = {chi_result['p_value']:.4f} "
            f"({'значущо' if chi_result['significant'] else 'незначущо'} на рівні α=0.05)",
            st["normal"],
        ))
    except Exception:
        pass

    if kendall_w_by_round:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Динаміка Kendall W по раундах", st["h2"]))
        rounds_header = [_P("Раунд", st["header"]), _P("Kendall W", st["header"]), _P("Оцінка", st["header"])]
        rounds_data = [rounds_header]
        for rn, w in sorted(kendall_w_by_round.items()):
            assessment = "Висока" if w >= 0.7 else ("Середня" if w >= 0.5 else "Низька")
            rounds_data.append([
                _P(str(rn), st["cell_center"]),
                _P(f"{w:.3f}", st["cell_center"]),
                _P(assessment, st["cell_center"]),
            ])
        tbl = Table(rounds_data, colWidths=[80, 140, USABLE_WIDTH - 220])
        tbl.setStyle(_tbl_style())
        story.append(tbl)
        story.append(Spacer(1, 0.3 * cm))

    if cv:
        story.append(Paragraph("Коефіцієнти варіації та ентропія по альтернативах", st["h2"]))
        cv_header = [_P("Альтернатива", st["header"]), _P("CV (варіація)", st["header"]), _P("Ентропія", st["header"])]
        cv_data = [cv_header]
        for alt_name in cv:
            cv_data.append([
                _P(_truncate(alt_name, 40), st["cell"]),
                _P(f"{cv[alt_name]:.3f}", st["cell_center"]),
                _P(f"{entropy.get(alt_name, 0):.3f}", st["cell_center"]),
            ])
        tbl = Table(cv_data, colWidths=[USABLE_WIDTH - 200, 100, 100])
        tbl.setStyle(_tbl_style())
        story.append(tbl)
        story.append(Spacer(1, 0.4 * cm))

    # 8. Correlation matrix between methods
    if corr_matrix:
        story.append(Paragraph("Матриця кореляцій між методами (Kendall τ / Spearman ρ)", st["h1"]))
        method_names = list(corr_matrix.keys())
        n = len(method_names)
        label_col = 100
        cell_col = (USABLE_WIDTH - label_col) / max(n, 1)
        header = [_P("Метод", st["header"])] + [
            _P(_truncate(mn, 16), st["header"]) for mn in method_names
        ]
        rows = [header]
        for mn in method_names:
            row = [_P(_truncate(mn, 18), st["cell"])]
            for mn2 in method_names:
                cell = corr_matrix.get(mn, {}).get(mn2, {})
                row.append(_P(
                    f"τ={cell.get('tau', 0):.2f}<br/>ρ={cell.get('rho', 0):.2f}",
                    st["cell_center"],
                ))
            rows.append(row)
        tbl = Table(rows, colWidths=[label_col] + [cell_col] * n)
        tbl.setStyle(_tbl_style())
        story.append(tbl)
        story.append(Spacer(1, 0.4 * cm))

    # 9. Outlier experts
    if outliers:
        story.append(Paragraph("Аутлайери серед експертів", st["h1"]))
        out_header = [_P("ID Експерта", st["header"]), _P("Відхилення (σ)", st["header"])]
        out_data = [out_header]
        for eid, dev in outliers:
            out_data.append([
                _P(str(eid), st["cell_center"]),
                _P(f"{dev:.3f}", st["cell_center"]),
            ])
        tbl = Table(out_data, colWidths=[USABLE_WIDTH / 2, USABLE_WIDTH / 2])
        tbl.setStyle(_tbl_style())
        story.append(tbl)
        story.append(Spacer(1, 0.4 * cm))

    # 10. Consensus ranking
    if consensus:
        story.append(Paragraph("Консенсусне ранжування", st["h1"]))
        for i, alt in enumerate(consensus, 1):
            story.append(Paragraph(f"{i}. {alt}", st["normal"]))
        story.append(Spacer(1, 0.4 * cm))

    # 11. Recommended decision with justification
    story.append(Paragraph("Рекомендоване рішення та обґрунтування", st["h1"]))
    if consensus:
        winner = consensus[0]
        story.append(Paragraph(
            f"На підставі комплексного аналізу із застосуванням п'яти методів оцінювання "
            f"та консенсусного ранжування <b>рекомендується обрати: {winner}</b>.",
            st["normal"],
        ))
        story.append(Spacer(1, 0.2 * cm))

    w_level = "висока" if kendall_w >= 0.7 else ("середня" if kendall_w >= 0.5 else "низька")
    story.append(Paragraph(
        f"Ступінь узгодженості думок експертів (Kendall W = {kendall_w:.3f}) — {w_level}. "
        f"{'Результати вважаються статистично значущими.' if kendall_w >= 0.5 else 'Рекомендується проведення додаткових раундів.'}",
        st["normal"],
    ))
    if outliers:
        story.append(Paragraph(
            f"Виявлено {len(outliers)} аутлайер(ів) серед експертів. "
            "Рекомендується розглянути можливість перегляду їхніх оцінок.",
            st["normal"],
        ))

    doc.build(story)
