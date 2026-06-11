"""
Generador de PDF de informe de calibración de balanzas.
Replica el formato de los informes existentes.
"""
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas as rl_canvas

W, H = A4
MARGIN = 1.5 * cm


def _scale_fmt(div_min) -> str:
    """Devuelve formato de decimales según div_min. Ej: 20→'0', 0.05→'2'"""
    s = f"{float(div_min):.10f}".rstrip("0")
    dec = len(s.split(".")[1]) if "." in s else 0
    return f".{dec}f"

def _fmt_val(v, fmt: str) -> str:
    try:
        return format(float(str(v).replace(",", ".")), fmt)
    except (ValueError, TypeError):
        return str(v)


class _NumberedCanvas(rl_canvas.Canvas):
    """Canvas que imprime 'X-Y' en el pie de cada página al finalizar."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._pages)
        for i, page in enumerate(self._pages, start=1):
            self.__dict__.update(page)
            self._draw_page_number(i, total)
            super().showPage()
        super().save()

    def _draw_page_number(self, current, total):
        text = f"{current}-{total}"
        self.setFont("Helvetica", 7)
        self.setFillColor(colors.grey)
        self.drawRightString(W - MARGIN, 0.6 * cm, text)

# Colores
DARK = colors.HexColor("#1a1a2e")
GREY = colors.HexColor("#cccccc")
LIGHT = colors.HexColor("#f0f0f0")

styles = getSampleStyleSheet()
normal = styles["Normal"]
bold_center = ParagraphStyle("bc", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER)
small = ParagraphStyle("sm", fontName="Helvetica", fontSize=8, alignment=TA_LEFT)
small_center = ParagraphStyle("smc", fontName="Helvetica", fontSize=8, alignment=TA_CENTER)
title_style = ParagraphStyle("ttl", fontName="Helvetica-Bold", fontSize=11, alignment=TA_CENTER)
heading_style = ParagraphStyle("hd", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER,
                               backColor=LIGHT)


def _ts(*args):
    """Shortcut para TableStyle."""
    return TableStyle(list(args))


def _box(style):
    style.add("BOX", (0, 0), (-1, -1), 0.5, colors.black)
    style.add("INNERGRID", (0, 0), (-1, -1), 0.25, GREY)
    return style


def generate_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )

    story = []
    cw = W - 2 * MARGIN  # ancho útil

    # ── ENCABEZADO ────────────────────────────────────────────────────────────
    hdr_data = [
        [
            Paragraph("<b>ALBERTO J. AMMIRAGLIA</b><br/>AV. SIRIA 2475 - SAN MIGUEL DE TUCUMÁN<br/>"
                      "Tel: (0381) 156-826072<br/>RUMP N° 150", small),
            Paragraph("<b>INFORME DE ENSAYO</b>", bold_center),
            Paragraph(f"<b>N° IF-01-{data['nro_informe']:04d}</b><br/>"
                      f"<b>Fecha:</b> {data['fecha']}", small_center),
        ]
    ]
    hdr_table = Table(hdr_data, colWidths=[cw * 0.35, cw * 0.35, cw * 0.30])
    hdr_table.setStyle(_box(_ts(
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    )))
    story.append(hdr_table)
    story.append(Spacer(1, 3))

    # ── DATOS USUARIO ─────────────────────────────────────────────────────────
    story.append(_section_title("DATOS DEL USUARIO", cw))
    user_data = [
        ["USUARIO:", data["cliente"]["razon_social"]],
        ["DOMICILIO:", data["cliente"]["direccion"]],
        ["LOCALIDAD:", data["cliente"]["localidad"]],
    ]
    story.append(_two_col_table(user_data, cw))
    story.append(Spacer(1, 3))

    # ── DATOS DEL INSTRUMENTO ─────────────────────────────────────────────────
    story.append(_section_title("DATOS DEL INSTRUMENTO", cw))
    b = data["balanza"]

    # Tabla 3 columnas: Indicador | Plataforma | Specs
    col_lbl = cw * 0.16
    col_val = cw * 0.17
    cw3 = [col_lbl, col_val, col_lbl, col_val, col_lbl, col_val]

    def _lbl(t): return Paragraph(f"<b>{t}</b>", small)
    def _val(t): return Paragraph(str(t), small)

    inst3 = [
        [_lbl("TIPO BALANZA:"),    _val(b["tipo_balanza"]),
         _lbl("UBICACION:"),       _val(b["ubicacion"]),
         _lbl("Ult. Verif.:"),     _val(b["ult_verificacion"])],
        [_lbl("MOD. INDICADOR:"),  _val(b["mod_indicador"]),
         _lbl("PLATAFORMA:"),      _val(b["plataforma"]),
         _lbl("CAP. MAX:"),        _val(f"{b['cap_max']} kg")],
        [_lbl("MARCA:"),           _val(b["marca"]),
         _lbl("MEDIDAS:"),         _val(b["medidas"]),
         _lbl("DIV. MIN:"),        _val(f"{b['div_min']} kg")],
        [_lbl("N° SERIE:"),        _val(b["n_serie_indicador"]),
         _lbl("N° SERIE:"),        _val(b["n_serie_plataforma"]),
         _lbl("COD. INTERNO:"),    _val(b["cod_interno"])],
        [_lbl("COD. DE APROB.:"),  _val(b["cod_aprobacion_indicador"]),
         _lbl("COD. DE APROB.:"),  _val(b["cod_aprobacion_plataforma"]),
         _val(""), _val("")],
    ]
    inst_table = Table(inst3, colWidths=cw3)
    inst_table.setStyle(_box(_ts(
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    )))
    story.append(inst_table)

    # Sección PRECINTOS
    story.append(Spacer(1, 3))
    story.append(_section_title("PRECINTOS", cw))
    prec_data = [
        [Paragraph("<b>Ubicación de precinto</b>", small_center),
         Paragraph("<b>Precintos anteriores</b>", small_center),
         Paragraph("<b>Precintos vigentes</b>", small_center)],
        [Paragraph("Parte base del Instrumento", small),
         Paragraph(b["precintos_ant_plataforma"], small),
         Paragraph(b["precintos_vig_plataforma"], small)],
        [Paragraph("Indicador Electrónico", small),
         Paragraph(b["precintos_ant_indicador"], small),
         Paragraph(b["precintos_vig_indicador"], small)],
    ]
    prec_table = Table(prec_data, colWidths=[cw * 0.34, cw * 0.33, cw * 0.33])
    prec_table.setStyle(_box(_ts(
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    )))
    story.append(prec_table)
    story.append(Spacer(1, 3))

    # ── PESAS ─────────────────────────────────────────────────────────────────
    story.append(_section_title("PESAS UTILIZADAS", cw))
    pw_data = [
        [Paragraph("<b>PESAS</b>", small_center),
         Paragraph("<b>CERTIFICADO DE CALIBRACIÓN N°</b>", small_center)],
        [Paragraph(data.get("desc_pesas_pequenas", ""), small_center),
         Paragraph(data.get("cert_pesas_pequenas", ""), small_center)],
        [Paragraph(data.get("desc_pesas_grandes", ""), small_center),
         Paragraph(data.get("cert_pesas_grandes", ""), small_center)],
    ]
    pw_table = Table(pw_data, colWidths=[cw * 0.5, cw * 0.5])
    pw_table.setStyle(_box(_ts(
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    )))
    story.append(pw_table)
    story.append(Spacer(1, 4))

    # ── TEMPERATURA ───────────────────────────────────────────────────────────
    story.append(_section_title("Temperatura °c", cw))
    temp_data = [
        [Paragraph("<b>Temp. Inicial</b>", small_center),
         Paragraph("<b>Temp. Final</b>",   small_center),
         Paragraph("<b>Temp. Promedio</b>", small_center)],
        [Paragraph(str(data.get("temp_inicial", "")),  small_center),
         Paragraph(str(data.get("temp_final",   "")),  small_center),
         Paragraph(str(data.get("temp_promedio", "")), small_center)],
    ]
    temp_table = Table(temp_data, colWidths=[cw / 3, cw / 3, cw / 3])
    temp_table.setStyle(_box(_ts(
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    )))
    story.append(temp_table)
    story.append(Spacer(1, 4))

    # ── PUESTA A CERO ─────────────────────────────────────────────────────────
    story.append(_section_title("PUESTA A CERO", cw))
    cap_max_str = data["balanza"].get("cap_max", "")
    pac_table = Table(
        [[Paragraph(f"PUESTA A CERO 4% CAPACIDAD MAXIMA:", small),
          Paragraph("<b>OK</b>", small_center)]],
        colWidths=[cw * 0.75, cw * 0.25]
    )
    pac_table.setStyle(_box(_ts(
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
    )))
    story.append(pac_table)
    story.append(Spacer(1, 4))

    # ── EXCENTRICIDAD ─────────────────────────────────────────────────────────
    _vfmt = _scale_fmt(data.get("div_min", 1))
    story.append(_section_title(f"EXCENTRICIDAD  [{data['excentricidad_carga']} kg]", cw))
    exc_rows = data["excentricidad_filas"]
    exc_header = [["N°", "POSICIÓN", "PESAS (kg)", "C/AUX", "TOTAL (kg)", "INDICADOR (kg)"]]
    exc_body = [[r["n"], r["posicion"],
                 _fmt_val(r["pesas"], _vfmt), r.get("c_aux", ""),
                 _fmt_val(r["total"], _vfmt), _fmt_val(r["indicador"], _vfmt)]
                for r in exc_rows]
    story.append(_data_table(exc_header + exc_body, cw,
                             col_ratios=[0.07, 0.18, 0.18, 0.12, 0.20, 0.25]))
    story.append(Spacer(1, 4))

    # ── LINEALIDAD ────────────────────────────────────────────────────────────
    story.append(_section_title(f"LINEALIDAD  [hasta {_fmt_val(data['carga_max_kg'], _vfmt)} kg]", cw))
    lin_rows = data["linealidad_filas"]
    lin_header = [["N°", "POSICIÓN", "PESAS (kg)", "C/AUX", "TOTAL (kg)", "INDICADOR (kg)"]]
    lin_body = [[r["n"], r["posicion"],
                 _fmt_val(r["pesas"], _vfmt), r.get("c_aux", ""),
                 _fmt_val(r["total"], _vfmt), _fmt_val(r["indicador"], _vfmt)]
                for r in lin_rows]
    story.append(_data_table(lin_header + lin_body, cw,
                             col_ratios=[0.07, 0.18, 0.18, 0.12, 0.20, 0.25]))
    story.append(Spacer(1, 4))

    # ── MOVILIDAD (solo camiones) ──────────────────────────────────────────────
    mov = data["movilidad"]
    if mov.get("tipo") == "camion":
        story.append(_section_title("MOVILIDAD", cw))
        mov_header = [["Movilidad", "Carga aplicada en equilibrio (kg)",
                       "Indicación (kg)", "Sobrecarga [1,4.dd]", "Indicación 2 (kg)"]]
        mov_body = [
            [f["label"], f["carga"], f["indicacion"], f"{f['sobrecarga']} kg", f["indicacion2"]]
            for f in mov["filas"]
        ]
        story.append(_data_table(mov_header + mov_body, cw,
                                 col_ratios=[0.22, 0.22, 0.18, 0.20, 0.18]))
        story.append(Spacer(1, 4))

    # ── RESULTADO + FIRMAS (juntos, nunca se separan de página) ───────────────
    resultado = data.get("resultado", "")
    obs = data.get("observaciones", "")
    res_data = [
        ["RESULTADO:", resultado],
        ["OBSERVACIONES:", obs],
    ]
    firma_data = [
        ["_______________________________", "_______________________________"],
        ["Firma y sello del Verificador", "Firma y sello del Usuario"],
    ]
    firma_table = Table(firma_data, colWidths=[cw * 0.5, cw * 0.5])
    firma_table.setStyle(_ts(
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ))
    story.append(KeepTogether([
        _section_title("RESULTADO", cw),
        _two_col_table(res_data, cw, label_ratio=0.22),
        Spacer(1, 14),
        firma_table,
    ]))

    doc.build(story, canvasmaker=_NumberedCanvas)
    return buf.getvalue()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _section_title(text: str, cw: float):
    t = Table([[Paragraph(f"<b>{text}</b>", bold_center)]], colWidths=[cw])
    t.setStyle(_ts(
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ))
    return t


def _two_col_table(rows: list, cw: float, label_ratio=0.20):
    col_w = [cw * label_ratio, cw * (1 - label_ratio)]
    styled_rows = [[Paragraph(f"<b>{r[0]}</b>", small), Paragraph(str(r[1]), small)]
                   for r in rows]
    t = Table(styled_rows, colWidths=col_w)
    t.setStyle(_box(_ts(
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    )))
    return t


def _four_col_table(rows: list, cw: float):
    col_w = [cw * 0.18, cw * 0.32, cw * 0.18, cw * 0.32]
    styled = []
    for r in rows:
        styled.append([
            Paragraph(f"<b>{r[0]}</b>", small),
            Paragraph(str(r[1]), small),
            Paragraph(f"<b>{r[2]}</b>", small),
            Paragraph(str(r[3]), small),
        ])
    t = Table(styled, colWidths=col_w)
    t.setStyle(_box(_ts(
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    )))
    return t


def _data_table(rows: list, cw: float, col_ratios: list):
    col_w = [cw * r for r in col_ratios]
    styled = []
    for i, row in enumerate(rows):
        if i == 0:
            styled.append([Paragraph(f"<b>{c}</b>", small_center) for c in row])
        else:
            styled.append([Paragraph(str(c) if c != "" else "", small_center) for c in row])
    t = Table(styled, colWidths=col_w)
    t.setStyle(_box(_ts(
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    )))
    return t


# ── INFORME DE SERVICIO ───────────────────────────────────────────────────────

def generate_informe_servicio(data: dict) -> bytes:
    """
    Genera el Informe de Servicio (IS-01-XXXX).
    Incluye: encabezado, datos usuario, instrumento, precintos,
    resumen falla, trabajos realizados, resultado, referencia IF (si aplica).
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )
    story = []
    cw = W - 2 * MARGIN

    # ── Encabezado ────────────────────────────────────────────────────────────
    hdr_data = [[
        Paragraph("<b>ALBERTO J. AMMIRAGLIA</b><br/>AV. SIRIA 2475 - SAN MIGUEL DE TUCUMÁN<br/>"
                  "Tel: (0381) 156-826072<br/>RUMP N° 150", small),
        Paragraph("<b>INFORME DE SERVICIO</b>", bold_center),
        Paragraph(f"<b>N° IS-01-{data['nro_is']:04d}</b><br/>"
                  f"<b>Fecha:</b> {data['fecha']}", small_center),
    ]]
    hdr_table = Table(hdr_data, colWidths=[cw * 0.35, cw * 0.35, cw * 0.30])
    hdr_table.setStyle(_box(_ts(
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    )))
    story.append(hdr_table)
    story.append(Spacer(1, 3))

    # ── Datos usuario ─────────────────────────────────────────────────────────
    story.append(_section_title("DATOS DEL USUARIO", cw))
    story.append(_two_col_table([
        ["USUARIO:",    data["cliente"]["razon_social"]],
        ["DOMICILIO:",  data["cliente"]["direccion"]],
        ["LOCALIDAD:",  data["cliente"]["localidad"]],
    ], cw))
    story.append(Spacer(1, 3))

    # ── Datos instrumento ─────────────────────────────────────────────────────
    story.append(_section_title("DATOS DEL INSTRUMENTO", cw))
    b = data["balanza"]

    def _lbl(t): return Paragraph(f"<b>{t}</b>", small)
    def _val(t): return Paragraph(str(t), small)

    col_lbl = cw * 0.16
    col_val = cw * 0.17
    cw3 = [col_lbl, col_val, col_lbl, col_val, col_lbl, col_val]
    inst3 = [
        [_lbl("TIPO BALANZA:"),   _val(b["tipo_balanza"]),
         _lbl("UBICACION:"),      _val(b["ubicacion"]),
         _lbl("Ult. Verif.:"),    _val(b["ult_verificacion"])],
        [_lbl("MOD. INDICADOR:"), _val(b["mod_indicador"]),
         _lbl("PLATAFORMA:"),     _val(b["plataforma"]),
         _lbl("CAP. MAX:"),       _val(f"{b['cap_max']} kg")],
        [_lbl("MARCA:"),          _val(b["marca"]),
         _lbl("MEDIDAS:"),        _val(b["medidas"]),
         _lbl("DIV. MIN:"),       _val(f"{b['div_min']} kg")],
        [_lbl("N° SERIE:"),       _val(b["n_serie_indicador"]),
         _lbl("N° SERIE:"),       _val(b["n_serie_plataforma"]),
         _lbl("COD. INTERNO:"),   _val(b["cod_interno"])],
        [_lbl("COD. DE APROB.:"), _val(b["cod_aprobacion_indicador"]),
         _lbl("COD. DE APROB.:"), _val(b["cod_aprobacion_plataforma"]),
         _val(""), _val("")],
    ]
    inst_table = Table(inst3, colWidths=cw3)
    inst_table.setStyle(_box(_ts(
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    )))
    story.append(inst_table)

    # ── Precintos ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 3))
    story.append(_section_title("PRECINTOS", cw))
    prec_data = [
        [Paragraph("<b>Ubicación de precinto</b>", small_center),
         Paragraph("<b>Precintos anteriores</b>", small_center),
         Paragraph("<b>Precintos vigentes</b>", small_center)],
        [Paragraph("Parte base del Instrumento", small),
         Paragraph(b["precintos_ant_plataforma"], small),
         Paragraph(b["precintos_vig_plataforma"], small)],
        [Paragraph("Indicador Electrónico", small),
         Paragraph(b["precintos_ant_indicador"], small),
         Paragraph(b["precintos_vig_indicador"], small)],
    ]
    prec_table = Table(prec_data, colWidths=[cw * 0.34, cw * 0.33, cw * 0.33])
    prec_table.setStyle(_box(_ts(
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    )))
    story.append(prec_table)
    story.append(Spacer(1, 6))

    # ── Cuadros de servicio ───────────────────────────────────────────────────
    def _cuadro(titulo, texto, altura=60):
        title_row = [[Paragraph(titulo, bold_center)]]
        t_title = Table(title_row, colWidths=[cw])
        t_title.setStyle(_ts(
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ))
        body_row = [[Paragraph(texto, small)]]
        t_body = Table(body_row, colWidths=[cw], rowHeights=[altura])
        t_body.setStyle(_ts(
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ))
        return [t_title, t_body, Spacer(1, 6)]

    for elem in _cuadro("RESUMEN DE LA FALLA", data.get("resumen_falla", "")):
        story.append(elem)
    for elem in _cuadro("TRABAJOS REALIZADOS", data.get("trabajos_realizados", "")):
        story.append(elem)
    for elem in _cuadro("RESULTADO/RECOMENDACIONES",
                        data.get("resultado_servicio", "La balanza se encuentra operativa."), altura=50):
        story.append(elem)

    # ── Referencia al Informe de Ensayo ───────────────────────────────────────
    if data.get("nro_if"):
        ref_style = ParagraphStyle("ref", fontName="Helvetica", fontSize=9, alignment=TA_LEFT)
        ref = Paragraph(f"<b>INFORME DE ENSAYO N°:</b>  IF-01-{data['nro_if']:04d}", ref_style)
        ref_table = Table([[ref]], colWidths=[cw])
        ref_table.setStyle(_box(_ts(
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        )))
        story.append(ref_table)
        story.append(Spacer(1, 6))

    # ── Firmas ────────────────────────────────────────────────────────────────
    firma_data = [
        ["_______________________________", "_______________________________"],
        ["Firma y sello del Verificador",  "Firma y sello del Usuario"],
    ]
    firma_table = Table(firma_data, colWidths=[cw * 0.5, cw * 0.5])
    firma_table.setStyle(_ts(
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ))
    story.append(KeepTogether([Spacer(1, 10), firma_table]))

    doc.build(story, canvasmaker=_NumberedCanvas)
    return buf.getvalue()
