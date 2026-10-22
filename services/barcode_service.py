import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.barcode import code128
from database import EXPORTS_DIR

class BarcodeService:
    @staticmethod
    def generate_labels_pdf(epis, filepath=None):
        """
        Gera uma folha de etiquetas com Código de Barras Code128 para os EPIs selecionados.
        Pronta para recortar ou imprimir em folhas de etiquetas adesivas padrão.
        """
        if not filepath:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.abspath(os.path.join(EXPORTS_DIR, f"etiquetas_codigo_barras_{timestamp}.pdf"))

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=20,
            rightMargin=20,
            topMargin=25,
            bottomMargin=25
        )

        styles = getSampleStyleSheet()
        p_title = ParagraphStyle('LblTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=10, alignment=1)
        p_sub = ParagraphStyle('LblSub', parent=styles['Normal'], fontName='Helvetica', fontSize=7, leading=8.5, alignment=1)

        # Monta grade de etiquetas (3 colunas por linha)
        cells = []
        for epi in epis:
            # Desenha código de barras Code128
            bc = code128.Code128(
                epi["codigo"],
                barHeight=22,
                barWidth=1.0,
                humanReadable=True
            )

            # Conteúdo da etiqueta
            label_data = [
                [Paragraph(f"<b>{epi['codigo']}</b> - {epi['nome'][:30]}", p_title)],
                [Paragraph(f"C.A. {epi['ca']} | Tam: {epi.get('tamanho') or 'Único'} | Loc: {epi.get('localizacao') or '-'}", p_sub)],
                [bc]
            ]
            cell_table = Table(label_data, colWidths=[170])
            cell_table.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
                ('PADDING', (0,0), (-1,-1), 4),
            ]))
            cells.append(cell_table)

        # Agrupa em linhas de 3 colunas
        rows = []
        for i in range(0, len(cells), 3):
            row = cells[i:i+3]
            while len(row) < 3:
                row.append(Paragraph("", p_sub))
            rows.append(row)

        grid_table = Table(rows, colWidths=[185, 185, 185])
        grid_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))

        story = [grid_table]
        doc.build(story)
        return filepath
