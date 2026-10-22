import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128, qr
from reportlab.graphics.shapes import Drawing
from database import EXPORTS_DIR

class EtiquetaService:
    @staticmethod
    def generate_labels_a4(items_to_print, output_path=None):
        """
        Gera folha A4 com grade de etiquetas para prateleiras e caixas de EPI.
        items_to_print: lista de dicts: [{'epi': epi_dict, 'qtd': int}, ...]
        Grade: 3 colunas x 8 linhas por folha (24 etiquetas por página).
        """
        if not output_path:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(EXPORTS_DIR, f"Etiquetas_EPI_A4_{ts}.pdf")

        c = canvas.Canvas(output_path, pagesize=A4)
        page_w, page_h = A4

        # Margens e dimensões
        margin_x = 20
        margin_y = 25
        cols = 3
        rows = 7

        label_w = (page_w - (margin_x * 2) - ((cols - 1) * 10)) / cols
        label_h = (page_h - (margin_y * 2) - ((rows - 1) * 10)) / rows

        flat_list = []
        for item in items_to_print:
            epi = item["epi"]
            qtd = item.get("qtd", 1)
            for _ in range(qtd):
                flat_list.append(epi)

        if not flat_list:
            raise ValueError("Nenhum item selecionado para impressão de etiquetas!")

        idx = 0
        total_items = len(flat_list)

        while idx < total_items:
            for r in range(rows):
                for col in range(cols):
                    if idx >= total_items:
                        break

                    epi = flat_list[idx]
                    x = margin_x + col * (label_w + 10)
                    y = page_h - margin_y - (r + 1) * label_h - r * 10

                    # Desenha borda da etiqueta
                    c.setStrokeColor(colors.HexColor("#CBD5E1"))
                    c.setFillColor(colors.white)
                    c.roundRect(x, y, label_w, label_h, 4, fill=1, stroke=1)

                    # Top bar azul
                    c.setFillColor(colors.HexColor("#1E3A8A"))
                    c.rect(x, y + label_h - 14, label_w, 14, fill=1, stroke=0)
                    c.setFillColor(colors.white)
                    c.setFont("Helvetica-Bold", 7)
                    c.drawString(x + 6, y + label_h - 10, f"CONTROLE DE EPI • CÓD: {epi['codigo']}")

                    # Nome do EPI
                    c.setFillColor(colors.HexColor("#0F172A"))
                    c.setFont("Helvetica-Bold", 8)
                    nome_txt = epi['nome']
                    if len(nome_txt) > 28:
                        nome_txt = nome_txt[:26] + "..."
                    c.drawString(x + 6, y + label_h - 26, nome_txt)

                    # C.A. e Categoria
                    c.setFont("Helvetica", 7)
                    c.setFillColor(colors.HexColor("#475569"))
                    c.drawString(x + 6, y + label_h - 37, f"C.A.: {epi['ca']} | Cat: {epi.get('categoria', 'Geral')}")

                    # Código de Barras Code128
                    try:
                        bc = code128.Code128(epi["codigo"], barHeight=22, barWidth=0.85)
                        bc.drawOn(c, x + 8, y + 14)
                    except Exception:
                        c.drawString(x + 8, y + 18, f"[{epi['codigo']}]")

                    # Rodapé da etiqueta
                    c.setFont("Helvetica", 6)
                    c.setFillColor(colors.HexColor("#64748B"))
                    fabr = epi.get("fabricante") or "Indústria"
                    c.drawString(x + 6, y + 4, f"Fabr: {fabr[:18]}")

                    idx += 1

            if idx < total_items:
                c.showPage()

        c.save()
        return output_path

    @staticmethod
    def generate_thermal_label(epi, qty=1, output_path=None):
        """
        Gera etiqueta avulsa no formato térmico (100mm x 50mm) para impressoras Zebra / Argox / Elgin.
        """
        if not output_path:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(EXPORTS_DIR, f"Etiqueta_Termica_{epi['codigo']}_{ts}.pdf")

        # 100mm x 50mm em pontos (1mm = 2.83465 pt)
        w_pt = 100 * 2.83465
        h_pt = 50 * 2.83465

        c = canvas.Canvas(output_path, pagesize=(w_pt, h_pt))

        for _ in range(qty):
            # Fundo e moldura
            c.setStrokeColor(colors.HexColor("#0F172A"))
            c.rect(5, 5, w_pt - 10, h_pt - 10, stroke=1, fill=0)

            # Cabeçalho
            c.setFillColor(colors.HexColor("#1E3A8A"))
            c.setFont("Helvetica-Bold", 10)
            c.drawString(12, h_pt - 20, "IDENTIFICAÇÃO DE ALMOXARIFADO SST")

            # Nome do EPI
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(12, h_pt - 35, epi["nome"][:36])

            # Informações Técnicas
            c.setFont("Helvetica", 9)
            c.drawString(12, h_pt - 50, f"CÓDIGO: {epi['codigo']}   |   C.A. (MTE): {epi['ca']}")
            c.drawString(12, h_pt - 64, f"FABRICANTE: {epi.get('fabricante', '-')}  |  TAM: {epi.get('tamanho', 'Único')}")

            # Código de Barras
            try:
                bc = code128.Code128(epi["codigo"], barHeight=35, barWidth=1.2)
                bc.drawOn(c, 15, 20)
            except Exception:
                c.drawString(20, 30, f"[{epi['codigo']}]")

            # QR Code ao lado
            try:
                qr_code = qr.QrCodeWidget(f"EPI:{epi['codigo']}|CA:{epi['ca']}")
                d = Drawing(45, 45)
                d.add(qr_code)
                d.drawOn(c, w_pt - 58, 15)
            except Exception:
                pass

            c.showPage()

        c.save()
        return output_path
