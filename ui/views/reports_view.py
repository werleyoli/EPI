import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import os
from datetime import datetime, timedelta

from services.movement_service import MovementService
from services.epi_service import EPIService
from services.employee_service import EmployeeService
from services.excel_service import ExcelService
from services.pdf_service import PDFService
from services.validade_uso_service import ValidadeUsoService
from services.financeiro_service import FinanceiroService
from services.inspecao_service import InspecaoService
from ui.components.theme import *
from ui.components.table_view import StyledTable

class ReportsView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.current_report_data = []
        self._build_ui()
        self._set_period_shortcut("month")

    def _build_ui(self):
        # Cabeçalho Principal
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(15, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(title_box, text="Central de Relatórios & Inteligência SST", font=FONT_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Extratos de consumo, vida útil de EPIs em uso, rateio financeiro por centro de custo e laudos NR-35", font=FONT_BODY, text_color=TEXT_MUTED).pack(anchor="w")

        # Tabview com as 4 centrais de inteligência
        self.tabview = ctk.CTkTabview(self, fg_color=BG_CARD)
        self.tabview.pack(fill="both", expand=True, padx=25, pady=(0, 20))

        self.tab_extrato = self.tabview.add("📋 Extrato de Movimentações")
        self.tab_validade = self.tabview.add("⏰ Validade em Uso & Trocas")
        self.tab_financeiro = self.tabview.add("💰 Rateio por Centro de Custo")
        self.tab_inspecoes = self.tabview.add("🪢 Inspeção Técnica & NR-35")

        self._build_tab_extrato()
        self._build_tab_validade()
        self._build_tab_financeiro()
        self._build_tab_inspecoes()

    # =========================================================================
    # TAB 1: EXTRATO DE MOVIMENTAÇÕES
    # =========================================================================
    def _build_tab_extrato(self):
        parent = self.tab_extrato
        f_top = ctk.CTkFrame(parent, fg_color="transparent")
        f_top.pack(fill="x", padx=10, pady=(10, 8))

        btn_box = ctk.CTkFrame(f_top, fg_color="transparent")
        btn_box.pack(side="right")

        ctk.CTkButton(
            btn_box,
            text="⚠️ Manutenção & Descarte (PDF)",
            font=FONT_BODY_BOLD,
            fg_color="#9A3412",
            hover_color="#7C2D12",
            height=34,
            command=self._export_manut_descarte_pdf
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_box,
            text="📑 Exportar eSocial (S-2240)",
            font=FONT_BODY_BOLD,
            fg_color="#4F46E5",
            hover_color="#4338CA",
            height=34,
            command=self._export_esocial
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_box,
            text="📊 Exportar Excel (.xlsx)",
            font=FONT_BODY_BOLD,
            fg_color="#059669",
            hover_color="#047857",
            height=34,
            command=self._export_excel
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_box,
            text="📄 Gerar Relatório PDF",
            font=FONT_BODY_BOLD,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            height=34,
            command=self._export_pdf
        ).pack(side="left", padx=4)

        # Filtros
        filter_card = ctk.CTkFrame(parent, fg_color=BG_MAIN, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        filter_card.pack(fill="x", padx=10, pady=(0, 10))

        f_inner = ctk.CTkFrame(filter_card, fg_color="transparent")
        f_inner.pack(fill="x", padx=12, pady=10)

        # Linha 1: Períodos
        row0 = ctk.CTkFrame(f_inner, fg_color="transparent")
        row0.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(row0, text="Período Rápido:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 6))
        ctk.CTkButton(row0, text="Hoje", width=65, height=26, fg_color=BORDER_COLOR, text_color=TEXT_MAIN, command=lambda: self._set_period_shortcut("today")).pack(side="left", padx=2)
        ctk.CTkButton(row0, text="Últimos 7 dias", width=95, height=26, fg_color=BORDER_COLOR, text_color=TEXT_MAIN, command=lambda: self._set_period_shortcut("week")).pack(side="left", padx=2)
        ctk.CTkButton(row0, text="Este Mês", width=80, height=26, fg_color=BORDER_COLOR, text_color=TEXT_MAIN, command=lambda: self._set_period_shortcut("month")).pack(side="left", padx=2)
        ctk.CTkButton(row0, text="Tudo", width=60, height=26, fg_color=BORDER_COLOR, text_color=TEXT_MAIN, command=lambda: self._set_period_shortcut("all")).pack(side="left", padx=2)

        from ui.components.date_picker import open_date_picker

        ctk.CTkLabel(row0, text="De:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(12, 4))
        self.dt_ini_var = tk.StringVar()
        self.dt_ini_entry = ctk.CTkEntry(row0, textvariable=self.dt_ini_var, placeholder_text="DD/MM/AAAA", width=95, height=26)
        self.dt_ini_entry.pack(side="left", padx=(0, 2))
        self.dt_ini_entry.bind("<Return>", lambda e: self.apply_filter())
        self.dt_ini_entry.bind("<Double-Button-1>", lambda e: open_date_picker(self, target_var=self.dt_ini_var, on_change=self.apply_filter))

        ctk.CTkButton(
            row0, text="📅", width=28, height=26,
            fg_color="#334155", hover_color="#475569",
            command=lambda: open_date_picker(self, target_var=self.dt_ini_var, on_change=self.apply_filter)
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(row0, text="Até:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 4))
        self.dt_fim_var = tk.StringVar()
        self.dt_fim_entry = ctk.CTkEntry(row0, textvariable=self.dt_fim_var, placeholder_text="DD/MM/AAAA", width=95, height=26)
        self.dt_fim_entry.pack(side="left", padx=(0, 2))
        self.dt_fim_entry.bind("<Return>", lambda e: self.apply_filter())
        self.dt_fim_entry.bind("<Double-Button-1>", lambda e: open_date_picker(self, target_var=self.dt_fim_var, on_change=self.apply_filter))

        ctk.CTkButton(
            row0, text="📅", width=28, height=26,
            fg_color="#334155", hover_color="#475569",
            command=lambda: open_date_picker(self, target_var=self.dt_fim_var, on_change=self.apply_filter)
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(row0, text="🔍 Filtrar", width=80, height=26, fg_color="#1E3A8A", command=self.apply_filter).pack(side="left")

        # Linha 2: Tipo & Texto
        row1 = ctk.CTkFrame(f_inner, fg_color="transparent")
        row1.pack(fill="x")

        ctk.CTkLabel(row1, text="Tipo:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 4))
        self.tipo_var = tk.StringVar(value="TODOS")
        ctk.CTkComboBox(row1, values=["TODOS", "SAIDA", "ENTRADA", "DEVOLUCAO", "NÃO DEVOLVIDO"], variable=self.tipo_var, width=165, height=26, command=lambda v: self.apply_filter()).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(row1, text="Busca:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        s_entry = ctk.CTkEntry(row1, placeholder_text="Filtrar por produto, funcionário, C.A. ou responsável...", textvariable=self.search_var, width=320, height=26)
        s_entry.pack(side="left")
        s_entry.bind("<KeyRelease>", lambda e: self.apply_filter())

        # KPIs
        self.kpi_bar = ctk.CTkFrame(parent, fg_color=BG_MAIN, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        self.kpi_bar.pack(fill="x", padx=10, pady=(0, 8))
        self.kpi_bar.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.kpi_total_mov = self._create_kpi_cell(self.kpi_bar, 0, "TOTAL DE REGISTROS", "0")
        self.kpi_total_saidas = self._create_kpi_cell(self.kpi_bar, 1, "SAÍDAS (UNIDADES)", "0")
        self.kpi_custo_total = self._create_kpi_cell(self.kpi_bar, 2, "CUSTO TOTAL SAÍDAS", "R$ 0,00")
        self.kpi_periodo = self._create_kpi_cell(self.kpi_bar, 3, "PERÍODO SELECIONADO", "-")

        # Tabela
        tbl_container = ctk.CTkFrame(parent, fg_color="transparent")
        tbl_container.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        cols = [
            {"id": "data", "text": "Data / Hora", "width": 120, "anchor": "center"},
            {"id": "tipo", "text": "Tipo", "width": 75, "anchor": "center"},
            {"id": "codigo", "text": "Código", "width": 70, "anchor": "center"},
            {"id": "epi", "text": "Nome do EPI", "width": 210, "anchor": "w"},
            {"id": "ca", "text": "C.A.", "width": 65, "anchor": "center"},
            {"id": "qtd", "text": "Qtd", "width": 55, "anchor": "center"},
            {"id": "custo", "text": "Custo Total", "width": 85, "anchor": "center"},
            {"id": "func", "text": "Funcionário Destino", "width": 160, "anchor": "w"},
            {"id": "cargo", "text": "Função / Setor", "width": 140, "anchor": "w"},
            {"id": "resp", "text": "Quem Entregou", "width": 130, "anchor": "w"},
            {"id": "motivo", "text": "Motivo", "width": 120, "anchor": "w"},
        ]
        self.table = StyledTable(tbl_container, columns=cols)
        self.table.pack(fill="both", expand=True)

    def _create_kpi_cell(self, parent, col, title, initial_val):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=0, column=col, sticky="nsew", padx=12, pady=6)
        ctk.CTkLabel(f, text=title, font=FONT_SMALL_BOLD, text_color=TEXT_MUTED).pack(anchor="w")
        lbl = ctk.CTkLabel(f, text=initial_val, font=FONT_SUBTITLE, text_color=TEXT_MAIN)
        lbl.pack(anchor="w", pady=(1, 0))
        return lbl

    def _set_period_shortcut(self, period):
        now = datetime.now()
        if period == "today":
            dt_ini = now.strftime("%d/%m/%Y")
            dt_fim = dt_ini
        elif period == "week":
            dt_ini = (now - timedelta(days=7)).strftime("%d/%m/%Y")
            dt_fim = now.strftime("%d/%m/%Y")
        elif period == "month":
            dt_ini = now.strftime("01/%m/%Y")
            dt_fim = now.strftime("%d/%m/%Y")
        else:
            dt_ini = ""
            dt_fim = ""

        self.dt_ini_var.set(dt_ini)
        self.dt_fim_var.set(dt_fim)
        self.apply_filter()

    def apply_filter(self):
        dt_ini = self.dt_ini_var.get().strip() or None
        dt_fim = self.dt_fim_var.get().strip() or None
        tipo = self.tipo_var.get().strip()
        search = self.search_var.get().strip() or None

        self.current_report_data = MovementService.list_movements(
            tipo=tipo,
            search=search,
            data_inicio=dt_ini,
            data_fim=dt_fim,
            limit=500
        )

        total_saidas_qtd = 0
        total_saidas_custo = 0.0

        self.table.clear()
        for m in self.current_report_data:
            dt = m["data_hora"]
            try:
                dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass

            t_raw = m.get("tipo", "")
            est_raw = str(m.get("estado_conservacao") or m.get("mov_estado") or "").upper()
            is_nao_dev = t_raw in ("NÃO DEVOLVIDO", "EXTRAVIO_DEMISSAO") or "NÃO DEVOLV" in est_raw or "NAO DEVOLV" in est_raw or "RETIDO" in est_raw

            tag = "even"
            if is_nao_dev:
                tipo_display = "🚨 NÃO DEV."
                tag = "danger"
            elif t_raw == "SAIDA":
                total_saidas_qtd += m["quantidade"]
                total_saidas_custo += float(m.get("custo_total") or 0.0)
                tipo_display = "SAIDA"
                tag = "odd"
            elif t_raw == "ENTRADA":
                tipo_display = "ENTRADA"
                tag = "success"
            elif t_raw == "DEVOLUCAO":
                tipo_display = "DEVOLUCAO"
                tag = "success"
            else:
                tipo_display = t_raw

            func_str = m.get("func_nome") or "-"
            if m.get("func_matricula"):
                func_str += f" ({m['func_matricula']})"

            self.table.insert_row(
                m["id"],
                [
                    dt,
                    tipo_display,
                    m["epi_codigo"],
                    m["epi_nome"],
                    m["epi_ca"],
                    f"{m['quantidade']} {m['epi_unidade']}",
                    f"R$ {float(m.get('custo_total') or 0.0):.2f}",
                    func_str,
                    f"{m.get('func_cargo') or '-'} / {m.get('func_depto') or '-'}",
                    m["responsavel_entrega"],
                    m["motivo"]
                ],
                tag=tag
            )

        self.kpi_total_mov.configure(text=str(len(self.current_report_data)))
        self.kpi_total_saidas.configure(text=f"{total_saidas_qtd} unid.")
        self.kpi_custo_total.configure(text=f"R$ {total_saidas_custo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        def _fmt_lbl(d):
            if not d:
                return ""
            d_norm = MovementService.normalize_date_iso(d)
            if d_norm:
                p = d_norm.split("-")
                return f"{p[2]}/{p[1]}/{p[0]}"
            return str(d)

        per_str = "Todo o Histórico"
        if dt_ini and dt_fim:
            per_str = f"{_fmt_lbl(dt_ini)} a {_fmt_lbl(dt_fim)}"
        elif dt_ini:
            per_str = f"A partir de {_fmt_lbl(dt_ini)}"
        elif dt_fim:
            per_str = f"Até {_fmt_lbl(dt_fim)}"
        self.kpi_periodo.configure(text=per_str)

    def _export_excel(self):
        try:
            if not self.current_report_data:
                messagebox.showwarning("Aviso", "Não há dados para exportar.")
                return
            filepath = ExcelService.export_movements(self.current_report_data)
            ans = messagebox.askyesno("Exportação Concluída", f"Planilha gerada com sucesso em:\n{filepath}\n\nDeseja abrir o arquivo agora?")
            if ans:
                os.startfile(filepath)
        except Exception as e:
            messagebox.showerror("Erro ao Exportar", str(e))

    def _export_pdf(self):
        try:
            if not self.current_report_data:
                messagebox.showwarning("Aviso", "Não há dados para exportar.")
                return
            filtro_desc = f"Tipo: {self.tipo_var.get()}"
            if self.dt_ini_var.get():
                filtro_desc += f" | De: {self.dt_ini_var.get()}"
            if self.dt_fim_var.get():
                filtro_desc += f" | Até: {self.dt_fim_var.get()}"
            if self.search_var.get():
                filtro_desc += f" | Busca: {self.search_var.get()}"
            filepath = PDFService.generate_movements_report_pdf(self.current_report_data, filters_desc=filtro_desc)
            ans = messagebox.askyesno("Relatório PDF Gerado", f"Relatório emitido com sucesso em:\n{filepath}\n\nDeseja abrir o PDF agora?")
            if ans:
                os.startfile(filepath)
        except Exception as e:
            messagebox.showerror("Erro ao Gerar PDF", str(e))

    def _export_manut_descarte_pdf(self):
        try:
            from services.pdf_service import PDFService
            filepath = PDFService.generate_maintenance_discard_pdf()
            ans = messagebox.askyesno(
                "Relatório de Manutenção & Descarte Gerado",
                f"Relatório Oficial de Gestão de EPIs em Manutenção e Descarte gerado com sucesso!\n\n"
                f"Arquivo:\n{filepath}\n\n"
                f"Deseja abrir o arquivo PDF agora para visualização e impressão?"
            )
            if ans:
                os.startfile(filepath)
        except Exception as e:
            messagebox.showerror("Erro ao Gerar Relatório", str(e))

    def _export_esocial(self):
        try:
            from services.esocial_service import ESocialService
            excel_path = ESocialService.export_s2240_excel()
            xml_path = ESocialService.export_s2240_xml()
            ans = messagebox.askyesno(
                "Exportação eSocial Concluída!",
                f"Arquivos do Evento S-2240 gerados com sucesso!\n\n"
                f"• Planilha Excel: {os.path.basename(excel_path)}\n"
                f"• Arquivo XML: {os.path.basename(xml_path)}\n\n"
                f"Deseja abrir a pasta das exportações agora?"
            )
            if ans:
                os.startfile(os.path.dirname(excel_path))
        except Exception as e:
            messagebox.showerror("Erro ao Exportar eSocial", str(e))

    # =========================================================================
    # TAB 2: VALIDADE DE EPI EM USO & CONVOCAÇÃO
    # =========================================================================
    def _build_tab_validade(self):
        parent = self.tab_validade
        f_top = ctk.CTkFrame(parent, fg_color="transparent")
        f_top.pack(fill="x", padx=10, pady=(10, 8))

        ctk.CTkLabel(f_top, text="Monitoramento de Vida Útil dos EPIs na Custódia dos Funcionários", font=FONT_SECTION, text_color=TEXT_MAIN).pack(side="left")

        btn_box = ctk.CTkFrame(f_top, fg_color="transparent")
        btn_box.pack(side="right")

        ctk.CTkButton(
            btn_box,
            text="📄 Emitir Ordem de Convocação (PDF)",
            font=FONT_BODY_BOLD,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            height=34,
            command=self._generate_convocacao_pdf
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_box,
            text="🔄 Atualizar",
            font=FONT_BODY,
            width=80,
            height=34,
            command=self.refresh_validade
        ).pack(side="left", padx=4)

        # Filtro
        f_filt = ctk.CTkFrame(parent, fg_color=BG_MAIN, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        f_filt.pack(fill="x", padx=10, pady=(0, 10))

        r_inner = ctk.CTkFrame(f_filt, fg_color="transparent")
        r_inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(r_inner, text="Filtrar por Situação:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 8))
        self.val_filtro_var = tk.StringVar(value="TODOS")
        ctk.CTkComboBox(r_inner, values=["TODOS", "VENCIDO", "VENCE_EM_BREVE", "EM_DIA"], variable=self.val_filtro_var, width=180, height=28, command=lambda v: self.refresh_validade()).pack(side="left")

        # Tabela
        tbl_box = ctk.CTkFrame(parent, fg_color="transparent")
        tbl_box.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        cols = [
            {"id": "func", "text": "Colaborador (Matrícula)", "width": 190, "anchor": "w"},
            {"id": "cargo", "text": "Cargo / Setor", "width": 160, "anchor": "w"},
            {"id": "epi", "text": "EPI em Uso", "width": 210, "anchor": "w"},
            {"id": "ca", "text": "C.A.", "width": 65, "anchor": "center"},
            {"id": "dt_ent", "text": "Data Entrega", "width": 95, "anchor": "center"},
            {"id": "dt_troca", "text": "Previsão Troca", "width": 95, "anchor": "center"},
            {"id": "situacao", "text": "Situação da Troca", "width": 160, "anchor": "center"}
        ]
        self.tbl_validade = StyledTable(tbl_box, columns=cols)
        self.tbl_validade.pack(fill="both", expand=True)

        self.current_validade_items = []

    def refresh_validade(self):
        if hasattr(self, "tbl_validade"):
            self.tbl_validade.apply_theme(ctk.get_appearance_mode())
            st = self.val_filtro_var.get().strip()
            self.current_validade_items = ValidadeUsoService.get_items_due_for_exchange(st)
            self.tbl_validade.clear()
            for it in self.current_validade_items:
                tag = "danger" if it["status"] == "VENCIDO" else ("odd" if it["status"] == "VENCE_EM_BREVE" else "success")
                self.tbl_validade.insert_row(
                    it["mov_id"],
                    [
                        f"{it['func_nome']} ({it['func_matricula']})",
                        f"{it['func_cargo']} - {it['func_depto']}",
                        f"{it['epi_codigo']} - {it['epi_nome']}",
                        it["epi_ca"],
                        it["data_entrega"],
                        it["data_previsao_troca"],
                        it["status_label"]
                    ],
                    tag=tag
                )

    def _generate_convocacao_pdf(self):
        if not self.current_validade_items:
            messagebox.showwarning("Aviso", "Não há colaboradores listados para convocação.")
            return
        try:
            pdf_path = ValidadeUsoService.generate_convocacao_pdf(self.current_validade_items)
            ans = messagebox.askyesno("Ordem de Convocação Gerada", f"Documento oficial de convocação para troca de EPI emitido em:\n{pdf_path}\n\nDeseja abrir o PDF agora?")
            if ans:
                os.startfile(pdf_path)
        except Exception as ex:
            messagebox.showerror("Erro ao Gerar Convocação", str(ex))

    # =========================================================================
    # TAB 3: RATEIO POR CENTRO DE CUSTO / FINANCEIRO
    # =========================================================================
    def _build_tab_financeiro(self):
        parent = self.tab_financeiro
        f_top = ctk.CTkFrame(parent, fg_color="transparent")
        f_top.pack(fill="x", padx=10, pady=(10, 8))

        ctk.CTkLabel(f_top, text="Apuração Orçamentária & Consumo por Centro de Custo", font=FONT_SECTION, text_color=TEXT_MAIN).pack(side="left")

        btn_box = ctk.CTkFrame(f_top, fg_color="transparent")
        btn_box.pack(side="right")

        ctk.CTkButton(
            btn_box,
            text="⚙️ Definir Orçamento Mensal",
            font=FONT_BODY,
            fg_color="#4F46E5",
            hover_color="#4338CA",
            height=34,
            command=self._open_budget_modal
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_box,
            text="📄 Relatório Financeiro PDF",
            font=FONT_BODY_BOLD,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=34,
            command=self._generate_financeiro_pdf
        ).pack(side="left", padx=4)

        # Filtro de Mês/Ano
        f_filt = ctk.CTkFrame(parent, fg_color=BG_MAIN, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        f_filt.pack(fill="x", padx=10, pady=(0, 10))

        r_inner = ctk.CTkFrame(f_filt, fg_color="transparent")
        r_inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(r_inner, text="Competência (MM/AAAA):", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 6))
        self.fin_mes_var = tk.StringVar(value=datetime.now().strftime("%m/%Y"))
        self.fin_mes_entry = ctk.CTkEntry(r_inner, textvariable=self.fin_mes_var, placeholder_text="MM/AAAA", width=100, height=28)
        self.fin_mes_entry.pack(side="left", padx=(0, 6))
        self.fin_mes_entry.bind("<Return>", lambda e: self.refresh_financeiro())
        ctk.CTkButton(r_inner, text="Consultar", width=80, height=28, fg_color="#1E3A8A", command=self.refresh_financeiro).pack(side="left", padx=(0, 6))

        # Atalhos de mês
        def _set_mes_atual():
            self.fin_mes_var.set(datetime.now().strftime("%m/%Y"))
            self.refresh_financeiro()

        def _set_mes_anterior():
            primeiro_dia = datetime.now().replace(day=1)
            mes_ant = primeiro_dia - timedelta(days=1)
            self.fin_mes_var.set(mes_ant.strftime("%m/%Y"))
            self.refresh_financeiro()

        ctk.CTkButton(r_inner, text="Mês Atual", width=80, height=26, fg_color=BORDER_COLOR, text_color=TEXT_MAIN, command=_set_mes_atual).pack(side="left", padx=2)
        ctk.CTkButton(r_inner, text="Mês Anterior", width=90, height=26, fg_color=BORDER_COLOR, text_color=TEXT_MAIN, command=_set_mes_anterior).pack(side="left", padx=2)

        # Tabela
        tbl_box = ctk.CTkFrame(parent, fg_color="transparent")
        tbl_box.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        cols = [
            {"id": "depto", "text": "Centro de Custo / Departamento", "width": 200, "anchor": "w"},
            {"id": "orcamento", "text": "Orçamento Mensal", "width": 130, "anchor": "center"},
            {"id": "gasto", "text": "Gasto Realizado", "width": 130, "anchor": "center"},
            {"id": "saldo", "text": "Saldo Restante", "width": 130, "anchor": "center"},
            {"id": "pct", "text": "% Consumido", "width": 100, "anchor": "center"},
            {"id": "itens", "text": "Total Itens", "width": 90, "anchor": "center"},
            {"id": "status", "text": "Situação da Meta", "width": 170, "anchor": "center"}
        ]
        self.tbl_financeiro = StyledTable(tbl_box, columns=cols)
        self.tbl_financeiro.pack(fill="both", expand=True)

    def refresh_financeiro(self):
        if hasattr(self, "tbl_financeiro"):
            self.tbl_financeiro.apply_theme(ctk.get_appearance_mode())
            m = self.fin_mes_var.get().strip()
            data = FinanceiroService.get_cost_center_summary(m)
            self.tbl_financeiro.clear()
            for d in data:
                tag = "danger" if d["status"] == "ESTOURADO" else ("odd" if d["status"] == "ALERTA" else "success")
                self.tbl_financeiro.insert_row(
                    d["departamento"],
                    [
                        d["departamento"],
                        f"R$ {d['orcamento_mensal']:.2f}",
                        f"R$ {d['gasto_total']:.2f}",
                        f"R$ {d['saldo_restante']:.2f}",
                        f"{d['percentual_usado']}%",
                        f"{d['total_itens']} un",
                        d["status_label"]
                    ],
                    tag=tag
                )

    def _open_budget_modal(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Definir Orçamento por Centro de Custo")
        dialog.geometry("450x300")
        dialog.resizable(False, False)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 450) // 2
        y = (dialog.winfo_screenheight() - 300) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text="⚙️ Ajuste de Orçamento Mensal (R$)", font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(pady=(15, 4))

        f = ctk.CTkFrame(dialog, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=25)

        with get_connection() as conn:
            rows = conn.execute("SELECT DISTINCT departamento FROM funcionarios WHERE departamento IS NOT NULL").fetchall()
            deptos = [r["departamento"] for r in rows] or ["Geral"]

        ctk.CTkLabel(f, text="Departamento / Setor:", font=FONT_BODY_BOLD).pack(anchor="w")
        dep_var = tk.StringVar(value=deptos[0])
        ctk.CTkComboBox(f, values=deptos, variable=dep_var, height=32).pack(fill="x", pady=(2, 10))

        ctk.CTkLabel(f, text="Limite de Gastos Mensal (R$):", font=FONT_BODY_BOLD).pack(anchor="w")
        val_entry = ctk.CTkEntry(f, height=32)
        val_entry.insert(0, "5000.00")
        val_entry.pack(fill="x", pady=(2, 15))

        def save_b():
            try:
                v = float(val_entry.get().strip().replace(",", "."))
                FinanceiroService.set_department_budget(dep_var.get(), v)
                messagebox.showinfo("Sucesso", "Orçamento salvo com sucesso!")
                dialog.destroy()
                self.refresh_financeiro()
            except Exception as e:
                messagebox.showerror("Erro", str(e))

        b_bar = ctk.CTkFrame(dialog, fg_color="transparent")
        b_bar.pack(fill="x", padx=25, pady=(0, 15))
        ctk.CTkButton(b_bar, text="Cancelar", fg_color="#94A3B8", command=dialog.destroy).pack(side="left")
        ctk.CTkButton(b_bar, text="Salvar Orçamento", fg_color="#1E3A8A", command=save_b).pack(side="right")

    def _generate_financeiro_pdf(self):
        try:
            m = self.fin_mes_var.get().strip()
            pdf_path = FinanceiroService.generate_cost_center_pdf(m)
            ans = messagebox.askyesno("Relatório Financeiro Gerado", f"Relatório gerado com sucesso em:\n{pdf_path}\n\nDeseja abrir o arquivo agora?")
            if ans:
                os.startfile(pdf_path)
        except Exception as e:
            messagebox.showerror("Erro ao Gerar Relatório", str(e))

    # =========================================================================
    # TAB 4: INSPEÇÃO TÉCNICA DE EPIS DURÁVEIS (NR-35 / NR-33)
    # =========================================================================
    def _build_tab_inspecoes(self):
        parent = self.tab_inspecoes
        f_top = ctk.CTkFrame(parent, fg_color="transparent")
        f_top.pack(fill="x", padx=10, pady=(10, 8))

        ctk.CTkLabel(f_top, text="Inspeções Periódicas de EPIs em Altura & Espaço Confinado (NR-35/NR-33)", font=FONT_SECTION, text_color=TEXT_MAIN).pack(side="left")

        btn_box = ctk.CTkFrame(f_top, fg_color="transparent")
        btn_box.pack(side="right")

        ctk.CTkButton(
            btn_box,
            text="➕ Nova Inspeção Técnica",
            font=FONT_BODY_BOLD,
            fg_color="#0D9488",
            hover_color="#0F766E",
            height=34,
            command=self._open_new_inspection_modal
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_box,
            text="📄 Emitir Laudo do EPI Selecionado",
            font=FONT_BODY,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=34,
            command=self._generate_laudo_selected
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_box,
            text="🔄 Atualizar",
            width=80,
            height=34,
            command=self.refresh_inspections
        ).pack(side="left", padx=4)

        # Tabela
        tbl_box = ctk.CTkFrame(parent, fg_color="transparent")
        tbl_box.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        cols = [
            {"id": "codigo", "text": "Código", "width": 75, "anchor": "center"},
            {"id": "epi", "text": "Descrição do Equipamento", "width": 220, "anchor": "w"},
            {"id": "ca", "text": "C.A.", "width": 65, "anchor": "center"},
            {"id": "serie", "text": "Nº Série / Lote", "width": 110, "anchor": "center"},
            {"id": "dt_insp", "text": "Data Inspeção", "width": 95, "anchor": "center"},
            {"id": "dt_prox", "text": "Próxima Obrigatória", "width": 115, "anchor": "center"},
            {"id": "resp", "text": "Inspetor / SST", "width": 140, "anchor": "w"},
            {"id": "resultado", "text": "Parecer", "width": 95, "anchor": "center"},
            {"id": "obs", "text": "Observações Técnicas", "width": 160, "anchor": "w"}
        ]
        self.tbl_inspections = StyledTable(tbl_box, columns=cols)
        self.tbl_inspections.pack(fill="both", expand=True)

    def refresh_inspections(self):
        if hasattr(self, "tbl_inspections"):
            self.tbl_inspections.apply_theme(ctk.get_appearance_mode())
            items = InspecaoService.list_inspections()
            self.tbl_inspections.clear()
            for it in items:
                tag = "success" if it["resultado"] == "APROVADO" else ("danger" if it["resultado"] == "REPROVADO" else "odd")
                self.tbl_inspections.insert_row(
                    it["id"],
                    [
                        it["epi_codigo"],
                        it["epi_nome"],
                        it["epi_ca"],
                        it["numero_serie"],
                        it["data_inspecao"],
                        it["data_proxima_inspecao"],
                        it["responsavel_tecnico"],
                        it["resultado"],
                        it.get("observacoes") or ""
                    ],
                    tag=tag
                )

    def _open_new_inspection_modal(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Registro de Inspeção Técnica de EPI (NR-35)")
        dialog.geometry("560x520")
        dialog.resizable(False, False)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 560) // 2
        y = (dialog.winfo_screenheight() - 520) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text="🪢 Nova Inspeção Periódica de EPI", font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(pady=(16, 4))

        f = ctk.CTkScrollableFrame(dialog, fg_color="transparent", height=380)
        f.pack(fill="both", expand=True, padx=25)

        epis = EPIService.list_epis(show_inactive=False)
        epi_map = {f"{e['codigo']} - {e['nome']} (C.A. {e['ca']})": e["id"] for e in epis}

        ctk.CTkLabel(f, text="Selecione o EPI Inspecionado *", font=FONT_BODY_BOLD).pack(anchor="w")
        epi_var = tk.StringVar(value=list(epi_map.keys())[0] if epi_map else "")
        ctk.CTkComboBox(f, values=list(epi_map.keys()), variable=epi_var, height=32).pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(f, text="Nº de Série / Patrimônio / Lote:", font=FONT_BODY_BOLD).pack(anchor="w")
        serie_entry = ctk.CTkEntry(f, placeholder_text="Ex: CINTO-2024-0012", height=32)
        serie_entry.pack(fill="x", pady=(2, 8))

        row1 = ctk.CTkFrame(f, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))
        row1.grid_columnconfigure((0, 1), weight=1)

        d_box = ctk.CTkFrame(row1, fg_color="transparent")
        d_box.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(d_box, text="Data da Inspeção (DD/MM/AAAA): *", font=FONT_BODY_BOLD).pack(anchor="w")
        row_insp_dt = ctk.CTkFrame(d_box, fg_color="transparent")
        row_insp_dt.pack(fill="x", pady=(2, 0))
        dt_entry = ctk.CTkEntry(row_insp_dt, placeholder_text="DD/MM/AAAA", height=32)
        dt_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
        dt_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        from ui.components.date_picker import open_date_picker
        dt_entry.bind("<Double-Button-1>", lambda e: open_date_picker(dialog, target_entry=dt_entry))
        btn_insp_cal = ctk.CTkButton(
            row_insp_dt,
            text="📅",
            width=38,
            height=32,
            fg_color="#3B82F6",
            hover_color="#1D4ED8",
            command=lambda: open_date_picker(dialog, target_entry=dt_entry)
        )
        btn_insp_cal.pack(side="right")

        v_box = ctk.CTkFrame(row1, fg_color="transparent")
        v_box.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(v_box, text="Validade da Inspeção:", font=FONT_BODY_BOLD).pack(anchor="w")
        val_opts = ["6 meses (Recomendado NR-35)", "12 meses (Anual)", "3 meses"]
        val_var = tk.StringVar(value=val_opts[0])
        ctk.CTkComboBox(v_box, values=val_opts, variable=val_var, height=32).pack(fill="x", pady=(2, 0))

        ctk.CTkLabel(f, text="Responsável Técnico / Inspetor *", font=FONT_BODY_BOLD).pack(anchor="w")
        resp_entry = ctk.CTkEntry(f, placeholder_text="Ex: Eng. João Silva - SST", height=32)
        resp_entry.pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(f, text="Resultado / Parecer da Inspeção *", font=FONT_BODY_BOLD).pack(anchor="w")
        res_opts = ["APROVADO", "REPROVADO", "MANUTENCAO"]
        res_var = tk.StringVar(value=res_opts[0])
        ctk.CTkComboBox(f, values=res_opts, variable=res_var, height=32).pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(f, text="Observações Técnicas / Laudo:", font=FONT_BODY_BOLD).pack(anchor="w")
        obs_entry = ctk.CTkEntry(f, placeholder_text="Ex: Costuras intactas, sem oxidação nas fivelas...", height=32)
        obs_entry.pack(fill="x", pady=(2, 10))

        def submit_insp():
            try:
                e_id = epi_map[epi_var.get()]
                serie = serie_entry.get().strip()
                dt_i = dt_entry.get().strip()
                resp = resp_entry.get().strip()
                res = res_var.get()
                obs = obs_entry.get().strip()

                val_txt = val_var.get()
                meses = 6
                if "12" in val_txt:
                    meses = 12
                elif "3" in val_txt:
                    meses = 3

                insp_id = InspecaoService.register_inspection(
                    epi_id=e_id,
                    numero_serie=serie,
                    data_inspecao=dt_i,
                    validade_meses=meses,
                    responsavel_tecnico=resp,
                    resultado=res,
                    observacoes=obs
                )

                messagebox.showinfo("Sucesso", "Inspeção técnica registrada com sucesso!")
                dialog.destroy()
                self.refresh_inspections()

                ans = messagebox.askyesno("Gerar Laudo", "Deseja emitir o Laudo Técnico Oficial em PDF agora?")
                if ans:
                    pdf_p = InspecaoService.generate_laudo_pdf(insp_id)
                    os.startfile(pdf_p)

            except Exception as ex:
                messagebox.showerror("Erro", str(ex))

        b_bar = ctk.CTkFrame(dialog, fg_color="transparent")
        b_bar.pack(fill="x", padx=25, pady=(10, 15))
        ctk.CTkButton(b_bar, text="Cancelar", fg_color="#94A3B8", command=dialog.destroy).pack(side="left")
        ctk.CTkButton(b_bar, text="Salvar Inspeção", fg_color="#1E3A8A", height=36, command=submit_insp).pack(side="right")

    def _generate_laudo_selected(self):
        sel = self.tbl_inspections.get_selected()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione uma inspeção na tabela para emitir o Laudo.")
            return
        try:
            pdf_path = InspecaoService.generate_laudo_pdf(int(sel))
            ans = messagebox.askyesno("Laudo Gerado", f"Laudo oficial de inspeção gerado em:\n{pdf_path}\n\nDeseja abrir o arquivo agora?")
            if ans:
                os.startfile(pdf_path)
        except Exception as e:
            messagebox.showerror("Erro ao Gerar Laudo", str(e))

    def refresh(self):
        """Atualização geral das tabelas de acordo com a aba visível."""
        self.apply_filter()
        self.refresh_validade()
        self.refresh_financeiro()
        self.refresh_inspections()
