from __future__ import annotations
import os
import urllib.request
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
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
FONT_URL = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
FONT_BOLD_URL = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf"

_font_loaded = False
_BODY_FONT = "Helvetica"
_BOLD_FONT = "Helvetica-Bold"


def _ensure_font():
    global _font_loaded, _BODY_FONT, _BOLD_FONT
    if _font_loaded:
        return
    os.makedirs(FONTS_DIR, exist_ok=True)
    try:
        if not os.path.exists(FONT_PATH):
            urllib.request.urlretrieve(FONT_URL, FONT_PATH)
        if not os.path.exists(FONT_BOLD_PATH):
            urllib.request.urlretrieve(FONT_BOLD_URL, FONT_BOLD_PATH)
        pdfmetrics.registerFont(TTFont("DejaVuSans", FONT_PATH))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", FONT_BOLD_PATH))
        _BODY_FONT = "DejaVuSans"
        _BOLD_FONT = "DejaVuSans-Bold"
    except Exception:
        _BODY_FONT = "Helvetica"
        _BOLD_FONT = "Helvetica-Bold"
    _font_loaded = True


def _styles():
    _ensure_font()
    base = getSampleStyleSheet()
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
    return {"normal": normal, "h1": heading1, "h2": heading2, "small": small}


def _tbl_style(header_rows=1):
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), colors.HexColor("#2d6cdf")),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.white),
        ("FONTNAME", (0, 0), (-1, header_rows - 1), _BOLD_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, header_rows), (-1, -1), _BODY_FONT),
        ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [colors.white, colors.HexColor("#f1f5fb")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9e0ea")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


def generate_report(session_data: dict, output_buffer: BytesIO) -> None:
    """
    Generate a complete PDF report into output_buffer.
    """
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

    session = session_data.get("session")
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

    title = session["title"] if session else "Звіт"
    description = session["description"] if session else ""
    created_at = session["created_at"] if session else ""

    # 1. Title page
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("Звіт сесії експертного оцінювання", st["h1"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f"<b>Назва:</b> {title}", st["normal"]))
    story.append(Paragraph(f"<b>Дата:</b> {created_at}", st["normal"]))
    story.append(Paragraph(f"<b>Експертів:</b> {len(experts)}", st["normal"]))
    story.append(Paragraph(f"<b>Альтернатив:</b> {len(alternatives)}", st["normal"]))
    story.append(Paragraph(f"<b>Сформовано:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", st["normal"]))
    story.append(PageBreak())

    # 2. Task description
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
    alt_data = [["#", "Назва альтернативи"]]
    for i, alt in enumerate(alternatives, 1):
        alt_data.append([str(i), alt["name"] if hasattr(alt, "__getitem__") else str(alt)])
    tbl = Table(alt_data, colWidths=[1.5 * cm, 13 * cm])
    tbl.setStyle(_tbl_style())
    story.append(tbl)
    story.append(Spacer(1, 0.4 * cm))

    # 4. Expert competence table
    story.append(Paragraph("Компетентність експертів", st["h1"]))
    comp_map = {c["expert_id"]: c for c in competences} if competences else {}
    comp_data = [["Експерт", "Ваговий коефіцієнт", "Самооцінка", "Взаємна оцінка", "Підсумкова вага"]]
    for exp in experts:
        eid = exp["id"]
        c = comp_map.get(eid)
        comp_data.append([
            exp["full_name"],
            f"{exp['competence']:.2f}",
            f"{c['self_assessment']:.2f}" if c and c["self_assessment"] is not None else "—",
            f"{c['peer_assessment']:.2f}" if c and c["peer_assessment"] is not None else "—",
            f"{c['final_weight']:.2f}" if c and c["final_weight"] is not None else "—",
        ])
    tbl = Table(comp_data, colWidths=[4 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm])
    tbl.setStyle(_tbl_style())
    story.append(tbl)
    story.append(Spacer(1, 0.4 * cm))

    # 5. Method results
    story.append(Paragraph("Результати методів оцінювання", st["h1"]))
    for method_name, result in methods.items():
        story.append(Paragraph(method_name, st["h2"]))
        scores = result.get("scores", {})
        winner = result.get("winner", "")
        rows = [["Альтернатива", "Бал"]]
        for alt_name, val in sorted(scores.items(), key=lambda x: -x[1]):
            rows.append([alt_name, f"{val:.3f}"])
        tbl = Table(rows, colWidths=[12 * cm, 4 * cm])
        tbl.setStyle(_tbl_style())
        story.append(tbl)
        story.append(Paragraph(f"Рекомендована альтернатива: <b>{winner}</b>", st["normal"]))
        story.append(Spacer(1, 0.3 * cm))

    story.append(PageBreak())

    # 6. Correlation matrix
    if corr_matrix:
        story.append(Paragraph("Матриця кореляцій між методами", st["h1"]))
        method_names = list(corr_matrix.keys())
        header = ["Метод"] + method_names
        rows = [header]
        for mn in method_names:
            row = [mn]
            for mn2 in method_names:
                cell = corr_matrix.get(mn, {}).get(mn2, {})
                row.append(f"τ={cell.get('tau',0):.2f}\nρ={cell.get('rho',0):.2f}")
            rows.append(row)
        col_w = [4 * cm] + [2.5 * cm] * len(method_names)
        tbl = Table(rows, colWidths=col_w)
        tbl.setStyle(_tbl_style())
        story.append(tbl)
        story.append(Spacer(1, 0.4 * cm))

    # 7. Consistency metrics
    story.append(Paragraph("Метрики узгодженості", st["h1"]))
    story.append(Paragraph(f"Kendall W (останній раунд): <b>{kendall_w:.3f}</b>", st["normal"]))
    if kendall_w_by_round:
        rounds_data = [["Раунд", "Kendall W"]]
        for rn, w in sorted(kendall_w_by_round.items()):
            rounds_data.append([str(rn), f"{w:.3f}"])
        tbl = Table(rounds_data, colWidths=[5 * cm, 5 * cm])
        tbl.setStyle(_tbl_style())
        story.append(tbl)
        story.append(Spacer(1, 0.3 * cm))

    if cv:
        story.append(Paragraph("Коефіцієнти варіації та ентропія", st["h2"]))
        cv_data = [["Альтернатива", "CV", "Ентропія"]]
        for alt_name in cv:
            cv_data.append([alt_name, f"{cv[alt_name]:.3f}", f"{entropy.get(alt_name, 0):.3f}"])
        tbl = Table(cv_data, colWidths=[9 * cm, 3 * cm, 3 * cm])
        tbl.setStyle(_tbl_style())
        story.append(tbl)
        story.append(Spacer(1, 0.4 * cm))

    # 8. Outliers
    if outliers:
        story.append(Paragraph("Аутлайери серед експертів", st["h1"]))
        out_data = [["ID Експерта", "Відхилення (σ)"]]
        for eid, dev in outliers:
            out_data.append([str(eid), f"{dev:.3f}"])
        tbl = Table(out_data, colWidths=[6 * cm, 6 * cm])
        tbl.setStyle(_tbl_style())
        story.append(tbl)
        story.append(Spacer(1, 0.4 * cm))

    # 9. Consensus ranking
    if consensus:
        story.append(Paragraph("Консенсусне ранжування", st["h1"]))
        for i, alt in enumerate(consensus, 1):
            story.append(Paragraph(f"{i}. {alt}", st["normal"]))
        story.append(Spacer(1, 0.4 * cm))

    # 10. Conclusions
    story.append(Paragraph("Висновки та рекомендації", st["h1"]))
    if consensus:
        story.append(Paragraph(
            f"На підставі аналізу результатів п'яти методів оцінювання та "
            f"консенсусного ранжування рекомендується обрати: <b>{consensus[0]}</b>.",
            st["normal"],
        ))
    w_interp = "достатня" if kendall_w >= 0.7 else "недостатня"
    story.append(Paragraph(
        f"Узгодженість думок експертів (Kendall W = {kendall_w:.3f}) — {w_interp}.",
        st["normal"],
    ))
    if outliers:
        story.append(Paragraph(
            f"Виявлено {len(outliers)} аутлайер(ів) серед експертів. "
            "Рекомендується розглянути можливість перегляду їхніх оцінок.",
            st["normal"],
        ))

    doc.build(story)
