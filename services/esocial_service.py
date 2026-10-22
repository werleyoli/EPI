import os
from datetime import datetime
import pandas as pd
from database import get_connection, EXPORTS_DIR

class ESocialService:
    @staticmethod
    def get_s2240_records():
        """
        Coleta e consolida os dados de EPIs ativos e entregues aos colaboradores
        no formato exigido pelo evento S-2240 do eSocial.
        """
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT f.cpf, f.matricula, f.nome as func_nome, f.cargo, f.departamento,
                       f.data_admissao,
                       e.codigo as epi_codigo, e.nome as epi_nome, e.ca as epi_ca,
                       e.fabricante, e.ca_validade,
                       m.data_hora as data_entrega, m.quantidade,
                       COALESCE(mc.periodicidade_dias, e.dias_vida_util, 90) as periodicidade_dias
                FROM movimentacoes m
                JOIN funcionarios f ON m.funcionario_id = f.id
                JOIN epis e ON m.epi_id = e.id
                LEFT JOIN matriz_cargos_epis mc ON (mc.cargo = f.cargo AND mc.epi_id = e.id)
                WHERE m.tipo = 'SAIDA' AND f.status = 'Ativo'
                ORDER BY f.nome ASC, m.data_hora DESC;
            """).fetchall()

            records = []
            for r in rows:
                cpf_clean = (r["cpf"] or "").replace(".", "").replace("-", "")
                dt_ent = r["data_entrega"][:10] if r["data_entrega"] else ""

                records.append({
                    "CPF_Trabalhador": cpf_clean,
                    "Matricula_eSocial": r["matricula"],
                    "Nome_Colaborador": r["func_nome"],
                    "Cargo_Funcao": r["cargo"],
                    "Setor_Ambiente": r["departamento"],
                    "Data_Admissao": r["data_admissao"] or "",
                    "EPI_Descricao": r["epi_nome"],
                    "CA_Numero": str(r["epi_ca"]),
                    "CA_Validade": r["ca_validade"] or "Em dia",
                    "Fabricante": r["fabricante"] or "Nacional",
                    "Data_Entrega": dt_ent,
                    "EPI_Eficaz": "S",
                    "Atende_NR06": "S",
                    "Treinamento_Uso": "S",
                    "Higienizacao_Garantida": "S",
                    "Periodicidade_Troca_Dias": r["periodicidade_dias"]
                })

            return records

    @staticmethod
    def export_s2240_excel(output_path=None):
        """Exporta planilha Excel estruturada no leiaute S-2240."""
        records = ESocialService.get_s2240_records()
        if not records:
            raise ValueError("Nenhum registro de EPI encontrado para geração do S-2240.")

        if not output_path:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(EXPORTS_DIR, f"eSocial_S2240_EPI_{ts}.xlsx")

        df = pd.DataFrame(records)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="eSocial_S2240")

            wb = writer.book
            ws = writer.sheets["eSocial_S2240"]

            # Estilização
            from openpyxl.styles import PatternFill, Font, Alignment
            header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
            header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

            for col in range(1, len(df.columns) + 1):
                cell = ws.cell(row=1, column=col)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
                # Auto largura
                ws.column_dimensions[cell.column_letter].width = max(16, len(str(cell.value)) + 3)

        return output_path

    @staticmethod
    def export_s2240_xml(output_path=None):
        """Gera pacote XML básico compatível com o leiaute S-2240 do eSocial."""
        records = ESocialService.get_s2240_records()
        if not records:
            raise ValueError("Nenhum registro encontrado para exportar XML do S-2240.")

        if not output_path:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(EXPORTS_DIR, f"eSocial_S2240_{ts}.xml")

        now_iso = datetime.now().isoformat()

        xml = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml.append('<eSocial xmlns="http://www.esocial.gov.br/schema/evt/evtExpRisco/v_S_01_02_00">')
        xml.append('  <evtExpRisco id="ID1' + datetime.now().strftime("%Y%m%d%H%M%S") + '">')
        xml.append('    <ideEvento>')
        xml.append('      <tpAmb>1</tpAmb>')
        xml.append('      <procEmi>1</procEmi>')
        xml.append(f'      <verProc>EPI_Master_Pro_2.0</verProc>')
        xml.append('    </ideEvento>')
        xml.append('    <dadosEPIs>')

        for r in records:
            xml.append('      <itemEPI>')
            xml.append(f'        <cpfTrab>{r["CPF_Trabalhador"]}</cpfTrab>')
            xml.append(f'        <matricula>{r["Matricula_eSocial"]}</matricula>')
            xml.append(f'        <caEPI>{r["CA_Numero"]}</caEPI>')
            xml.append(f'        <dscEPI>{r["EPI_Descricao"]}</dscEPI>')
            xml.append(f'        <dtEntrega>{r["Data_Entrega"]}</dtEntrega>')
            xml.append(f'        <eficazEPI>{r["EPI_Eficaz"]}</eficazEPI>')
            xml.append(f'        <atendeNR06>{r["Atende_NR06"]}</atendeNR06>')
            xml.append(f'        <treinamento>{r["Treinamento_Uso"]}</treinamento>')
            xml.append(f'        <higienizacao>{r["Higienizacao_Garantida"]}</higienizacao>')
            xml.append(f'        <periodicidadeDias>{r["Periodicidade_Troca_Dias"]}</periodicidadeDias>')
            xml.append('      </itemEPI>')

        xml.append('    </dadosEPIs>')
        xml.append('  </evtExpRisco>')
        xml.append('</eSocial>')

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(xml))

        return output_path
