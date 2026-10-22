import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import customtkinter as ctk
import os
from datetime import datetime

from services.epi_service import EPIService
from services.movement_service import MovementService
from services.excel_service import ExcelService
from ui.components.theme import *
from ui.components.table_view import StyledTable

class InventoryView(ctk.CTkFrame):
    def __init__(self, parent, on_refresh_dashboard=None):
        super().__init__(parent, fg_color="transparent")
        self.on_refresh_dashboard = on_refresh_dashboard
        self.current_filter_status = "all"
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Cabeçalho Principal (Título + Ações Principais do Estoque)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(18, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(title_box, text="Gestão & Controle de Estoque de EPI", font=FONT_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Controle preciso de saldos, C.A., estoque mínimo e alertas de reposição", font=FONT_BODY, text_color=TEXT_MUTED).pack(anchor="w")

        # Botões de Ação Principal (Cadastro, Edição, Entrada e Grupos)
        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")

        btn_grupos = ctk.CTkButton(
            btn_box,
            text="📁 Grupos de EPI",
            font=FONT_BODY_BOLD,
            fg_color="#6366F1",
            hover_color="#4F46E5",
            height=36,
            command=self._open_group_manager
        )
        btn_grupos.pack(side="left", padx=4)

        btn_entrada = ctk.CTkButton(
            btn_box,
            text="📥 Registrar Entrada (Compra)",
            font=FONT_BODY_BOLD,
            fg_color="#059669",
            hover_color="#047857",
            height=36,
            command=self.open_stock_entry_modal
        )
        btn_entrada.pack(side="left", padx=4)

        btn_edit = ctk.CTkButton(
            btn_box,
            text="✏️ Editar Item",
            font=FONT_BODY_BOLD,
            fg_color="#475569",
            hover_color="#334155",
            height=36,
            command=self.open_edit_modal
        )
        btn_edit.pack(side="left", padx=4)

        btn_novo = ctk.CTkButton(
            btn_box,
            text="➕ Cadastrar Novo EPI",
            font=FONT_BODY_BOLD,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=36,
            command=self.open_new_modal
        )
        btn_novo.pack(side="left", padx=(4, 0))

        # Faixa de Ferramentas, Relatórios e Exportações (Linha 2)
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=25, pady=(0, 10))

        # Lado Esquerdo: Relatórios e Pedidos
        tb_left = ctk.CTkFrame(toolbar, fg_color="transparent")
        tb_left.pack(side="left")

        btn_pdf = ctk.CTkButton(
            tb_left,
            text="📄 Relatório PDF (Grupos)",
            font=FONT_BODY_BOLD,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            height=32,
            command=self._export_pdf_grouped
        )
        btn_pdf.pack(side="left", padx=(0, 5))

        btn_excel = ctk.CTkButton(
            tb_left,
            text="📊 Exportar Excel",
            font=FONT_BODY,
            fg_color="#059669",
            hover_color="#047857",
            height=32,
            command=self._export_excel
        )
        btn_excel.pack(side="left", padx=5)

        btn_grade = ctk.CTkButton(
            tb_left,
            text="📐 Grade & Condições",
            font=FONT_BODY,
            fg_color="#4338CA",
            hover_color="#3730A3",
            height=32,
            command=self._open_selected_grade_modal
        )
        btn_grade.pack(side="left", padx=5)

        btn_compra = ctk.CTkButton(
            tb_left,
            text="🛒 Pedido de Compra",
            font=FONT_BODY,
            fg_color="#D97706",
            hover_color="#B45309",
            height=32,
            command=self._generate_purchase_order
        )
        btn_compra.pack(side="left", padx=5)

        btn_manut = ctk.CTkButton(
            tb_left,
            text="⚠️ Manutenção & 🗑️ Descarte",
            font=FONT_BODY_BOLD,
            fg_color="#9A3412",
            hover_color="#7C2D12",
            height=32,
            command=self._open_maintenance_discard_dialog
        )
        btn_manut.pack(side="left", padx=5)

        # Lado Direito: Etiquetas, Importação e Modelo
        tb_right = ctk.CTkFrame(toolbar, fg_color="transparent")
        tb_right.pack(side="right")

        btn_barcodes = ctk.CTkButton(
            tb_right,
            text="🏷️ Etiquetas",
            font=FONT_BODY,
            fg_color="#0D9488",
            hover_color="#0F766E",
            height=32,
            command=self._generate_barcodes
        )
        btn_barcodes.pack(side="left", padx=5)

        btn_import = ctk.CTkButton(
            tb_right,
            text="📥 Importar Excel",
            font=FONT_BODY,
            fg_color="#4F46E5",
            hover_color="#4338CA",
            height=32,
            command=self._import_excel
        )
        btn_import.pack(side="left", padx=5)

        btn_modelo = ctk.CTkButton(
            tb_right,
            text="📄 Modelo Excel",
            font=FONT_BODY,
            fg_color="#64748B",
            hover_color="#475569",
            height=32,
            command=self._download_template
        )
        btn_modelo.pack(side="left", padx=(5, 0))

        # Barra de Filtros e Busca (Linha 3)
        filter_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        filter_card.pack(fill="x", padx=25, pady=(0, 15))

        f_inner = ctk.CTkFrame(filter_card, fg_color="transparent")
        f_inner.pack(fill="x", padx=15, pady=8)

        ctk.CTkLabel(f_inner, text="🔍 Buscar:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            f_inner,
            placeholder_text="Código, nome, C.A., grupo...",
            textvariable=self.search_var,
            width=180,
            height=32
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh())

        ctk.CTkLabel(f_inner, text="Grupo:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(4, 4))
        self.grupo_filter_var = tk.StringVar(value="TODOS OS GRUPOS")
        self.grupo_combo = ctk.CTkComboBox(
            f_inner,
            values=["TODOS OS GRUPOS"] + EPIService.list_nomes_grupos(),
            variable=self.grupo_filter_var,
            command=lambda val: self.refresh(),
            width=180,
            height=32
        )
        self.grupo_combo.pack(side="left", padx=(0, 15))

        # Chips de filtro por status
        ctk.CTkLabel(f_inner, text="Status:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 6))

        self.btn_all = self._create_filter_chip(f_inner, "Todos", "all")
        self.btn_low = self._create_filter_chip(f_inner, "⚠️ Baixo", "low")
        self.btn_out = self._create_filter_chip(f_inner, "❌ Zerados", "out")
        self.btn_ca = self._create_filter_chip(f_inner, "⏰ C.A. Vencendo", "ca_expiring")
        self.btn_ok = self._create_filter_chip(f_inner, "✅ Normal", "ok")
        self.btn_quarentena = self._create_filter_chip(f_inner, "⚠️ Manut./Descarte", "quarentena")

        self.count_lbl = ctk.CTkLabel(f_inner, text="0 itens", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.count_lbl.pack(side="right")

        # Tabela de EPIs
        tbl_container = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        tbl_container.pack(fill="both", expand=True, padx=25, pady=(0, 20))

        cols = [
            {"id": "codigo", "text": "Código", "width": 75, "anchor": "center"},
            {"id": "grupo", "text": "Grupo / Família", "width": 135, "anchor": "w"},
            {"id": "nome", "text": "Nome do Equipamento (EPI)", "width": 210, "anchor": "w"},
            {"id": "ca", "text": "C.A.", "width": 70, "anchor": "center"},
            {"id": "validade_ca", "text": "Validade C.A.", "width": 85, "anchor": "center"},
            {"id": "fabricante", "text": "Fabricante", "width": 105, "anchor": "w"},
            {"id": "tamanho", "text": "Grade / Tam.", "width": 120, "anchor": "center"},
            {"id": "quantidade", "text": "Estoque Disp.", "width": 120, "anchor": "center"},
            {"id": "preco", "text": "Custo Unit.", "width": 80, "anchor": "center"},
            {"id": "vida_util", "text": "Vida Útil", "width": 75, "anchor": "center"},
            {"id": "status", "text": "Situação", "width": 105, "anchor": "center"},
            {"id": "local", "text": "Locais de Armazenamento", "width": 170, "anchor": "w"},
        ]
        self.table = StyledTable(tbl_container, columns=cols, on_double_click=lambda row_id: self.open_edit_modal(row_id))
        self.table.pack(fill="both", expand=True, padx=12, pady=12)

    def _create_filter_chip(self, parent, text, status_val):
        btn = ctk.CTkButton(
            parent,
            text=text,
            height=28,
            corner_radius=14,
            font=FONT_SMALL_BOLD,
            fg_color="#1E3A8A" if status_val == "all" else "#E2E8F0",
            text_color="#FFFFFF" if status_val == "all" else "#334155",
            hover_color="#1D4ED8" if status_val == "all" else "#CBD5E1",
            command=lambda: self._set_filter(status_val)
        )
        btn.pack(side="left", padx=3)
        return btn

    def _set_filter(self, status_val):
        self.current_filter_status = status_val
        chips = [
            (self.btn_all, "all"),
            (self.btn_low, "low"),
            (self.btn_out, "out"),
            (self.btn_ca, "ca_expiring"),
            (self.btn_ok, "ok"),
            (self.btn_quarentena, "quarentena")
        ]
        for btn, val in chips:
            if val == status_val:
                btn.configure(fg_color="#1E3A8A", text_color="#FFFFFF", hover_color="#1D4ED8")
            else:
                btn.configure(fg_color="#E2E8F0", text_color="#334155", hover_color="#CBD5E1")
        self.refresh()

    def refresh(self):
        if hasattr(self, "table"):
            self.table.apply_theme(ctk.get_appearance_mode())

        search = self.search_var.get().strip() if hasattr(self, "search_var") else ""
        grp_filter = self.grupo_filter_var.get().strip() if hasattr(self, "grupo_filter_var") else "TODOS OS GRUPOS"
        self.current_epis = EPIService.list_epis(
            search=search,
            filter_status=self.current_filter_status,
            filter_grupo=grp_filter
        )

        # Atualiza opções do combo se necessário
        if hasattr(self, "grupo_combo"):
            nomes_g = ["TODOS OS GRUPOS"] + EPIService.list_nomes_grupos()
            self.grupo_combo.configure(values=nomes_g)

        self.table.clear()
        for e in self.current_epis:
            qtd = e["quantidade"]
            min_qtd = e["estoque_minimo"]

            tag = "even"
            if self.current_filter_status == "quarentena":
                q_r = e.get("qtd_ruins", 0) or 0
                q_d = e.get("qtd_descarte", 0) or 0
                tag = "warning"
                situacao = f"⚠️ Reparo: {q_r} | 🗑️ Desc: {q_d}"
            elif qtd == 0:
                tag = "danger"
                situacao = "❌ ZERADO"
            elif qtd <= min_qtd:
                tag = "warning"
                situacao = "⚠️ BAIXO"
            else:
                tag = "even"
                situacao = "✅ NORMAL"

            # Alerta complementar se C.A. estiver vencendo ou vencido
            val_ca_disp = "N/D"
            if e.get("validade_ca"):
                try:
                    if "/" in e["validade_ca"]:
                        dt_ca = datetime.strptime(e["validade_ca"][:10], "%d/%m/%Y").date()
                        val_ca_disp = dt_ca.strftime("%d/%m/%Y")
                    else:
                        dt_ca = datetime.strptime(e["validade_ca"][:10], "%Y-%m-%d").date()
                        val_ca_disp = dt_ca.strftime("%d/%m/%Y")
                    dias_ca = (dt_ca - datetime.now().date()).days
                    if dias_ca < 0:
                        situacao += " (C.A. Vencido)"
                        tag = "danger"
                    elif dias_ca <= 60:
                        situacao += f" (C.A. {dias_ca}d)"
                        if tag != "danger":
                            tag = "warning"
                except Exception:
                    val_ca_disp = str(e.get("validade_ca"))

            preco_str = f"R$ {e.get('preco_unitario', 0.0):.2f}"
            vida_str = f"{e.get('dias_vida_util', 0)} dias" if e.get('dias_vida_util') else "N/D"

            # Formata tamanho e grade
            tam_disp = e.get("grade_resumo") or e.get("tamanho") or "Único"

            # Formata saldo com detalhamento de Novos e Usados/Reutilizáveis
            qtd_novos = e.get("qtd_novos", qtd)
            qtd_usados = e.get("qtd_usados_bons", 0)
            if qtd_usados > 0:
                qtd_disp = f"{qtd} {e['unidade']} ({qtd_novos}N | {qtd_usados}U)"
            else:
                qtd_disp = f"{qtd} {e['unidade']}"

            self.table.insert_row(
                e["id"],
                [
                    e["codigo"],
                    e.get("grupo") or "DIVERSOS / OUTROS",
                    e["nome"],
                    e["ca"],
                    val_ca_disp,
                    e.get("fabricante") or "-",
                    tam_disp,
                    qtd_disp,
                    preco_str,
                    vida_str,
                    situacao,
                    f"{e.get('localizacao', '-')}" + (f" | {e.get('localizacao_secundaria')}" if e.get("localizacao_secundaria") else "")
                ],
                tag=tag
            )

        self.count_lbl.configure(text=f"{len(self.current_epis)} itens cadastrados")

    def _generate_barcodes(self):
        """Abre modal interativo para emissão de etiquetas em Folha A4 ou Impressora Térmica."""
        if not self.current_epis:
            messagebox.showwarning("Aviso", "Não há EPIs listados para gerar etiquetas.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Impressão de Etiquetas de EPIs com Código de Barras")
        dialog.geometry("520x460")
        dialog.resizable(False, False)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 520) // 2
        y = (dialog.winfo_screenheight() - 460) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text="🏷️ Gerador de Etiquetas de Identificação de EPI", font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(pady=(18, 4))
        ctk.CTkLabel(dialog, text="Escolha o padrão de impressão (Folha A4 para prateleiras ou Térmica com QR Code)", font=FONT_SMALL, text_color=TEXT_MUTED).pack(pady=(0, 15))

        f = ctk.CTkFrame(dialog, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=30)

        # 1. Formato de Impressão
        ctk.CTkLabel(f, text="1. Padrão / Formato de Impressão:", font=FONT_BODY_BOLD).pack(anchor="w")
        formato_var = tk.StringVar(value="A4")
        r_a4 = ctk.CTkRadioButton(f, text="📄 Folha A4 Comum (Grade com 21 a 24 etiquetas por folha)", variable=formato_var, value="A4", font=FONT_BODY)
        r_a4.pack(anchor="w", pady=(4, 4))
        r_termica = ctk.CTkRadioButton(f, text="🏷️ Impressora Térmica (Zebra / Argox / Elgin 100x50mm com QR Code)", variable=formato_var, value="TERMICA", font=FONT_BODY)
        r_termica.pack(anchor="w", pady=(0, 15))

        # 2. Quais EPIs Imprimir
        ctk.CTkLabel(f, text="2. Quais EPIs Imprimir:", font=FONT_BODY_BOLD).pack(anchor="w")
        sel_row = self.table.get_selected()
        selected_epi = None
        if sel_row:
            selected_epi = next((e for e in self.current_epis if str(e["id"]) == str(sel_row)), None)

        alvo_opts = ["Todos os EPIs ativos com saldo em estoque", "Todos os EPIs cadastrados (independente de saldo)"]
        if selected_epi:
            alvo_opts.insert(0, f"Apenas o item selecionado: {selected_epi['codigo']} - {selected_epi['nome'][:20]}")

        alvo_var = tk.StringVar(value=alvo_opts[0])
        ctk.CTkComboBox(f, values=alvo_opts, variable=alvo_var, height=34).pack(fill="x", pady=(4, 15))

        # 3. Quantidade de Etiquetas por Item
        ctk.CTkLabel(f, text="3. Quantidade de Etiquetas por Item:", font=FONT_BODY_BOLD).pack(anchor="w")
        qtd_opts = ["1 etiqueta de cada item", "2 etiquetas de cada item", "5 etiquetas de cada item", "Quantidade igual ao saldo atual em estoque"]
        qtd_var = tk.StringVar(value=qtd_opts[0])
        ctk.CTkComboBox(f, values=qtd_opts, variable=qtd_var, height=34).pack(fill="x", pady=(4, 20))

        def emitir():
            try:
                from services.etiqueta_service import EtiquetaService
                alvo = alvo_var.get()
                formato = formato_var.get()
                qtd_choice = qtd_var.get()

                # Seleciona os itens
                if selected_epi and alvo.startswith("Apenas o item selecionado"):
                    epis_target = [selected_epi]
                elif "com saldo" in alvo:
                    epis_target = [e for e in self.current_epis if e["quantidade"] > 0]
                else:
                    epis_target = list(self.current_epis)

                if not epis_target:
                    messagebox.showwarning("Aviso", "Nenhum EPI encontrado com os critérios escolhidos.")
                    return

                # Calcula quantidade
                items_print = []
                for e in epis_target:
                    if "saldo atual" in qtd_choice:
                        q = max(1, e["quantidade"])
                    elif "2 etiquetas" in qtd_choice:
                        q = 2
                    elif "5 etiquetas" in qtd_choice:
                        q = 5
                    else:
                        q = 1
                    items_print.append({"epi": e, "qtd": q})

                # Gera o PDF
                if formato == "A4":
                    pdf_path = EtiquetaService.generate_labels_a4(items_print)
                else:
                    # Formato térmico
                    if len(epis_target) == 1:
                        pdf_path = EtiquetaService.generate_thermal_label(epis_target[0], qty=items_print[0]["qtd"])
                    else:
                        # Se forem múltiplos em formato térmico, gera A4 com layout individual
                        pdf_path = EtiquetaService.generate_labels_a4(items_print)

                dialog.destroy()
                ans = messagebox.askyesno(
                    "Etiquetas Geradas!",
                    f"As etiquetas foram geradas com sucesso em:\n{pdf_path}\n\nDeseja abrir o arquivo agora para imprimir?"
                )
                if ans:
                    os.startfile(pdf_path)

            except Exception as ex:
                messagebox.showerror("Erro ao Gerar Etiquetas", str(ex))

        btn_box = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_box.pack(fill="x", padx=30, pady=(0, 20))
        ctk.CTkButton(btn_box, text="Cancelar", fg_color="#94A3B8", command=dialog.destroy).pack(side="left")
        ctk.CTkButton(btn_box, text="🖨️ Gerar PDF para Impressão", fg_color="#0D9488", hover_color="#0F766E", height=36, command=emitir).pack(side="right")

    def _generate_purchase_order(self):
        try:
            from services.compra_service import CompraService
            items = CompraService.get_critical_stock_for_purchase()
            if not items:
                messagebox.showinfo("Estoque em Dia", "Parabéns! Nenhum EPI está com estoque zerado ou abaixo do mínimo no momento.")
                return

            pdf_path = CompraService.generate_purchase_order_pdf(items=items)
            ans = messagebox.askyesno(
                "Solicitação de Compra Gerada!",
                f"Pedido de cotação / compra gerado com sucesso contendo {len(items)} itens críticos!\n\nArquivo:\n{pdf_path}\n\nDeseja abrir o PDF agora para enviar aos fornecedores?"
            )
            if ans:
                os.startfile(pdf_path)
        except Exception as e:
            messagebox.showerror("Erro ao Gerar Pedido", str(e))

    def _import_excel(self):
        """Abre seletor de arquivo e importa EPIs em lote via planilha."""
        from tkinter import filedialog
        from services.import_service import ImportService
        fpath = filedialog.askopenfilename(
            title="Selecione a Planilha de EPIs (.xlsx, .csv)",
            filetypes=[("Planilhas", "*.xlsx *.xls *.csv")]
        )
        if not fpath:
            return
        try:
            res = ImportService.import_epis_excel(fpath)
            msg = f"Importação Concluída com Sucesso!\n\n• Novos EPIs cadastrados: {res['inseridos']}\n• EPIs existentes atualizados: {res['atualizados']}"
            if res["erros"]:
                msg += f"\n\nErros identificados ({len(res['erros'])}):\n" + "\n".join(res["erros"][:5])
            messagebox.showinfo("Importação de EPIs", msg)
            self.refresh()
            if self.on_refresh_dashboard:
                self.on_refresh_dashboard()
        except Exception as ex:
            messagebox.showerror("Erro na Importação", str(ex))

    def _download_template(self):
        """Gera e abre a planilha modelo para preenchimento de EPIs."""
        from services.import_service import ImportService
        try:
            fpath = ImportService.generate_epi_template()
            ans = messagebox.askyesno("Planilha Modelo Gerada", f"Modelo Excel gerado em:\n{fpath}\n\nDeseja abrir a planilha modelo agora?")
            if ans:
                os.startfile(fpath)
        except Exception as ex:
            messagebox.showerror("Erro ao Gerar Modelo", str(ex))

    def open_new_modal(self):
        self._open_form_modal(None)

    def open_edit_modal(self, row_id=None):
        if not row_id:
            row_id = self.table.get_selected()
        if not row_id:
            messagebox.showwarning("Aviso", "Selecione um EPI na tabela para editar.")
            return
        epi = EPIService.get_epi(int(row_id))
        if epi:
            self._open_form_modal(epi)

    def _open_selected_grade_modal(self):
        """Abre modal interativo para visualizar detalhadamente a grade de tamanhos e estados de conservação do EPI."""
        sel_row = self.table.get_selected()
        if not sel_row:
            messagebox.showwarning("Aviso", "Selecione um EPI na tabela para visualizar a grade de tamanhos e condições.")
            return

        epi = EPIService.get_epi(int(sel_row))
        if not epi:
            return

        grades = EPIService.get_epi_grades(epi["id"])

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Grade & Condições - {epi['codigo']} {epi['nome']}")
        dialog.geometry("740x530")
        dialog.resizable(True, True)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 740) // 2
        y = (dialog.winfo_screenheight() - 530) // 2
        dialog.geometry(f"+{x}+{y}")

        # Topo
        top = ctk.CTkFrame(dialog, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(15, 8))
        ctk.CTkLabel(top, text="📐 Grade de Variações de Tamanho & Condições de Conservação", font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(
            top,
            text=f"{epi['codigo']} - {epi['nome']} | C.A. {epi['ca']} | Grupo: {epi.get('grupo', 'DIVERSOS')} | Fabricante: {epi.get('fabricante', '-')}",
            font=FONT_BODY_BOLD,
            text_color="#2563EB"
        ).pack(anchor="w", pady=(2, 0))

        # Tabela com as variações
        t_card = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        t_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        cols_g = [
            {"id": "tamanho", "text": "Tamanho / Variação", "width": 140, "anchor": "center"},
            {"id": "novos", "text": "🆕 Novos (un)", "width": 110, "anchor": "center"},
            {"id": "usados", "text": "♻️ Reutilizáveis (un)", "width": 130, "anchor": "center"},
            {"id": "disp", "text": "📦 Disp. Entrega", "width": 120, "anchor": "center"},
            {"id": "manut", "text": "⚠️ Manutenção (un)", "width": 110, "anchor": "center"},
            {"id": "descarte", "text": "🗑️ Descarte (un)", "width": 100, "anchor": "center"},
        ]
        t_grade = StyledTable(t_card, columns=cols_g)
        t_grade.pack(fill="both", expand=True, padx=10, pady=10)

        tot_novos = 0
        tot_usados = 0
        tot_disp = 0
        tot_ruim = 0
        tot_desc = 0

        if not grades:
            q_tot = epi.get("quantidade", 0)
            q_nov = epi.get("qtd_novos", q_tot)
            q_usd = epi.get("qtd_usados_bons", 0)
            q_rui = epi.get("qtd_ruins", 0)
            q_dsc = epi.get("qtd_descarte", 0)
            t_grade.insert_row(1, [
                epi.get("tamanho") or "Único",
                f"{q_nov} {epi['unidade']}",
                f"{q_usd} {epi['unidade']}",
                f"{q_tot} {epi['unidade']}",
                f"{q_rui} {epi['unidade']}",
                f"{q_dsc} {epi['unidade']}"
            ])
            tot_novos = q_nov
            tot_usados = q_usd
            tot_disp = q_tot
            tot_ruim = q_rui
            tot_desc = q_dsc
        else:
            for idx, g in enumerate(grades):
                tot_novos += g["novo"]
                tot_usados += g["usado_bom"]
                tot_disp += g["total_disponivel"]
                tot_ruim += g["ruim"]
                tot_desc += g["descarte"]
                t_grade.insert_row(idx, [
                    g["tamanho"],
                    f"{g['novo']} {epi['unidade']}",
                    f"{g['usado_bom']} {epi['unidade']}",
                    f"{g['total_disponivel']} {epi['unidade']}",
                    f"{g['ruim']} {epi['unidade']}",
                    f"{g['descarte']} {epi['unidade']}"
                ])

        # Barra de rodapé com Totais e Botões
        bot_bar = ctk.CTkFrame(dialog, fg_color="transparent")
        bot_bar.pack(fill="x", padx=20, pady=(0, 15))

        lbl_tot = ctk.CTkLabel(
            bot_bar,
            text=f"Total: {tot_disp} un disponíveis ({tot_novos} Novos | {tot_usados} Reutilizáveis)  •  {tot_ruim} Manut.  •  {tot_desc} Descarte",
            font=FONT_BODY_BOLD,
            text_color=TEXT_MAIN
        )
        lbl_tot.pack(side="left")

        def abrir_edicao():
            dialog.destroy()
            self.open_edit_modal(epi["id"])

        def abrir_entrada():
            dialog.destroy()
            self.open_stock_entry_modal(epi["id"])

        ctk.CTkButton(
            bot_bar,
            text="📥 Registrar Entrada (Compra)",
            font=FONT_BODY_BOLD,
            fg_color="#059669",
            hover_color="#047857",
            height=34,
            command=abrir_entrada
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            bot_bar,
            text="✏️ Editar Grade / Saldo",
            font=FONT_BODY,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=34,
            command=abrir_edicao
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            bot_bar,
            text="Fechar",
            fg_color="#94A3B8",
            hover_color="#64748B",
            height=34,
            command=dialog.destroy
        ).pack(side="right")

    def _open_form_modal(self, epi=None):
        is_edit = epi is not None
        dialog = ctk.CTkToplevel(self)
        dialog.title("Editar EPI" if is_edit else "Cadastrar Novo EPI")
        dialog.resizable(True, True)
        dialog.grab_set()

        dialog.update_idletasks()
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        w = min(760, max(600, sw - 60))
        h = min(840, max(500, sh - 80))
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text="✏️ Editar Dados do EPI" if is_edit else "📦 Cadastro de Novo EPI",
            font=FONT_SUBTITLE,
            text_color=TEXT_MAIN
        ).pack(pady=(14, 2))

        ctk.CTkLabel(dialog, text="Preencha as informações técnicas, grade de variações e estoques por condição física (NR-6)", font=FONT_SMALL, text_color=TEXT_MUTED).pack(pady=(0, 10))

        f = ctk.CTkScrollableFrame(dialog, fg_color="transparent", height=h - 160)
        f.pack(fill="both", expand=True, padx=22, pady=(0, 10))

        # 0. Grupo / Família do EPI
        row_grp = ctk.CTkFrame(f, fg_color="transparent")
        row_grp.pack(fill="x", pady=(0, 8))

        grp_head = ctk.CTkFrame(row_grp, fg_color="transparent")
        grp_head.pack(fill="x")
        ctk.CTkLabel(grp_head, text="Grupo / Família do EPI *", font=FONT_BODY_BOLD).pack(side="left")
        ctk.CTkLabel(grp_head, text="(Classificação para Relatório PDF e Estoque)", font=FONT_SMALL, text_color=TEXT_MUTED).pack(side="left", padx=(8, 0))

        grp_input_bar = ctk.CTkFrame(row_grp, fg_color="transparent")
        grp_input_bar.pack(fill="x", pady=(2, 0))

        grupos_disponiveis = EPIService.list_nomes_grupos()
        if is_edit and epi:
            val_default_grp = (epi.get("grupo") or "DIVERSOS / OUTROS").strip().upper()
        else:
            val_default_grp = "DIVERSOS / OUTROS"

        if val_default_grp not in grupos_disponiveis:
            grupos_disponiveis.append(val_default_grp)

        grupo_var = tk.StringVar(value=val_default_grp)
        grupo_combo = ctk.CTkComboBox(
            grp_input_bar,
            values=grupos_disponiveis,
            variable=grupo_var,
            height=32
        )
        grupo_combo.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def _adicionar_novo_grupo_dialog():
            novo = simpledialog.askstring("Novo Grupo de EPI", "Digite o nome do novo Grupo/Família:\n(Ex: VESTUÁRIO TÉRMICO, BOTAS TÉRMICAS, UNIFORMES...)")
            if novo and novo.strip():
                nome_formatado = novo.strip().upper()
                try:
                    EPIService.create_grupo(nome_formatado)
                    novos_grupos = EPIService.list_nomes_grupos()
                    grupo_combo.configure(values=novos_grupos)
                    grupo_var.set(nome_formatado)
                    grupo_combo.set(nome_formatado)
                    messagebox.showinfo("Sucesso", f"Grupo '{nome_formatado}' criado e selecionado!")
                except Exception as err:
                    messagebox.showerror("Erro", str(err))

        btn_add_grp = ctk.CTkButton(
            grp_input_bar,
            text="➕ Novo Grupo",
            font=FONT_SMALL_BOLD,
            width=110,
            height=32,
            fg_color="#6366F1",
            hover_color="#4F46E5",
            command=_adicionar_novo_grupo_dialog
        )
        btn_add_grp.pack(side="right")

        # Código e Nome
        row0 = ctk.CTkFrame(f, fg_color="transparent")
        row0.pack(fill="x", pady=(0, 8))
        row0.grid_columnconfigure(0, weight=3)
        row0.grid_columnconfigure(1, weight=7)

        c_box = ctk.CTkFrame(row0, fg_color="transparent")
        c_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(c_box, text="Código *", font=FONT_BODY_BOLD).pack(anchor="w")
        cod_entry = ctk.CTkEntry(c_box, height=32)
        cod_entry.insert(0, epi["codigo"] if is_edit else f"EPI-00{len(self.current_epis)+1}")
        cod_entry.pack(fill="x", pady=(2, 0))

        n_box = ctk.CTkFrame(row0, fg_color="transparent")
        n_box.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ctk.CTkLabel(n_box, text="Nome do EPI *", font=FONT_BODY_BOLD).pack(anchor="w")
        nome_entry = ctk.CTkEntry(n_box, height=32)
        if is_edit:
            nome_entry.insert(0, epi["nome"])
        nome_entry.pack(fill="x", pady=(2, 0))

        # C.A. com Botão de Consulta Online e Validade C.A.
        row1 = ctk.CTkFrame(f, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))
        row1.grid_columnconfigure((0, 1), weight=1)

        ca_box = ctk.CTkFrame(row1, fg_color="transparent")
        ca_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        
        ca_header_frame = ctk.CTkFrame(ca_box, fg_color="transparent")
        ca_header_frame.pack(fill="x")
        ctk.CTkLabel(ca_header_frame, text="C.A. (Certificado MTE) *", font=FONT_BODY_BOLD).pack(side="left")

        def buscar_por_nome_link():
            termo = nome_entry.get().strip()
            from services.ca_service import CAService
            CAService.abrir_busca_nome(termo)

        btn_link_nome = ctk.CTkButton(
            ca_header_frame,
            text="🌐 Não sei o C.A. (Buscar por Nome)",
            font=FONT_SMALL,
            fg_color="transparent",
            text_color="#2563EB",
            hover_color="#DBEAFE",
            height=20,
            command=buscar_por_nome_link
        )
        btn_link_nome.pack(side="right")

        ca_input_frame = ctk.CTkFrame(ca_box, fg_color="transparent")
        ca_input_frame.pack(fill="x", pady=(2, 0))

        ca_entry = ctk.CTkEntry(ca_input_frame, placeholder_text="Digite o nº do C.A. ex: 41001", height=32)
        if is_edit:
            ca_entry.insert(0, epi["ca"])
        ca_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        def consultar_ca_action():
            num = ca_entry.get().strip()
            if not num:
                termo = nome_entry.get().strip()
                if termo:
                    ans = messagebox.askyesno(
                        "Localizar C.A. por Nome",
                        f"O campo C.A. está vazio.\n\n"
                        f"Deseja pesquisar os números de C.A. homologados para '{termo}' diretamente na base oficial do ConsultaCA (MTE)?"
                    )
                    if ans:
                        from services.ca_service import CAService
                        CAService.abrir_busca_nome(termo)
                    return
                messagebox.showwarning("Aviso", "Digite o número do C.A. ou o Nome do EPI para pesquisar!")
                return

            btn_consult_ca.configure(text="⏳ Buscando...", state="disabled")
            dialog.update_idletasks()

            try:
                from services.ca_service import CAService
                res = CAService.consultar_ca_online(num)
                if res.get("sucesso"):
                    val_online = res.get("validade_br") or res.get("validade")
                    if val_online:
                        if "-" in val_online:
                            try:
                                val_online = datetime.strptime(val_online[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
                            except Exception:
                                pass
                        val_entry.delete(0, "end")
                        val_entry.insert(0, val_online)

                    if res.get("fabricante"):
                        fab_entry.delete(0, "end")
                        fab_entry.insert(0, res["fabricante"])

                    if res.get("equipamento"):
                        nome_atual = nome_entry.get().strip()
                        if not nome_atual or nome_atual.upper() in ["BOTA DE PVC", "EPI", "ITEM", "NOVO EPI"] or not is_edit:
                            nome_entry.delete(0, "end")
                            nome_entry.insert(0, res["equipamento"])

                    if res.get("descricao"):
                        desc_entry.delete(0, "end")
                        desc_entry.insert(0, res["descricao"][:200])

                    sit = res.get("situacao", "VÁLIDO").upper()
                    sit_icone = "✅" if "VÁLID" in sit or "REGULAR" in sit else "⚠️"
                    msg = (
                        f"{sit_icone} C.A. {num} LOCALIZADO!\n\n"
                        f"• Equipamento: {res.get('equipamento')}\n"
                        f"• Fabricante: {res.get('fabricante')}\n"
                        f"• Validade no MTE: {res.get('validade_br', res.get('validade'))}\n"
                        f"• Situação Legal: {sit}\n\n"
                        f"Os dados oficiais foram preenchidos automaticamente nos campos!"
                    )
                    messagebox.showinfo("C.A. Localizado", msg)
                else:
                    messagebox.showwarning("Aviso", res.get("mensagem", "C.A. não localizado."))
            finally:
                btn_consult_ca.configure(text="🔍 Consultar", state="normal")

        ca_entry.bind("<Return>", lambda e: consultar_ca_action())

        btn_consult_ca = ctk.CTkButton(
            ca_input_frame,
            text="🔍 Consultar",
            width=88,
            height=32,
            fg_color="#0D9488",
            hover_color="#0F766E",
            command=consultar_ca_action
        )
        btn_consult_ca.pack(side="right")

        val_box = ctk.CTkFrame(row1, fg_color="transparent")
        val_box.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ctk.CTkLabel(val_box, text="Validade do C.A. (DD/MM/AAAA)", font=FONT_BODY_BOLD).pack(anchor="w")
        row_val_dt = ctk.CTkFrame(val_box, fg_color="transparent")
        row_val_dt.pack(fill="x", pady=(2, 0))
        val_entry = ctk.CTkEntry(row_val_dt, placeholder_text="DD/MM/AAAA", height=32)
        val_init = epi.get("validade_ca") if is_edit and epi.get("validade_ca") else ""
        if val_init and "-" in val_init:
            try:
                val_init = datetime.strptime(val_init[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                pass
        if val_init:
            val_entry.insert(0, val_init)
        val_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        from ui.components.date_picker import open_date_picker
        val_entry.bind("<Double-Button-1>", lambda e: open_date_picker(dialog, target_entry=val_entry))
        btn_cal_ca = ctk.CTkButton(
            row_val_dt,
            text="📅",
            width=38,
            height=32,
            fg_color="#3B82F6",
            hover_color="#1D4ED8",
            command=lambda: open_date_picker(dialog, target_entry=val_entry)
        )
        btn_cal_ca.pack(side="right")

        # Fabricante e Parâmetros
        row2 = ctk.CTkFrame(f, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 8))
        row2.grid_columnconfigure((0, 1), weight=1)

        fab_box = ctk.CTkFrame(row2, fg_color="transparent")
        fab_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(fab_box, text="Fabricante / Marca", font=FONT_BODY_BOLD).pack(anchor="w")
        fab_entry = ctk.CTkEntry(fab_box, height=32)
        if is_edit and epi.get("fabricante"):
            fab_entry.insert(0, epi["fabricante"])
        fab_entry.pack(fill="x", pady=(2, 0))

        u_box = ctk.CTkFrame(row2, fg_color="transparent")
        u_box.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        u_box.grid_columnconfigure((0, 1), weight=1)

        un_sub = ctk.CTkFrame(u_box, fg_color="transparent")
        un_sub.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkLabel(un_sub, text="Unidade", font=FONT_BODY_BOLD).pack(anchor="w")
        unidades = ["UN", "PAR", "KIT", "CJ", "CX"]
        un_var = tk.StringVar(value=epi["unidade"] if is_edit else "UN")
        ctk.CTkComboBox(un_sub, values=unidades, variable=un_var, height=32).pack(fill="x", pady=(2, 0))

        min_sub = ctk.CTkFrame(u_box, fg_color="transparent")
        min_sub.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        ctk.CTkLabel(min_sub, text="Estoque Mínimo *", font=FONT_BODY_BOLD).pack(anchor="w")
        min_entry = ctk.CTkEntry(min_sub, height=32)
        min_entry.insert(0, str(epi["estoque_minimo"]) if is_edit else "5")
        min_entry.pack(fill="x", pady=(2, 0))

        # =========================================================================
        # SEÇÃO: GRADE DE TAMANHOS & CONDIÇÕES DE CONSERVAÇÃO (NOVO / USADO / DESCARTE)
        # =========================================================================
        grade_card = ctk.CTkFrame(f, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color="#3B82F6")
        grade_card.pack(fill="x", pady=(4, 10), padx=1)

        gc_top = ctk.CTkFrame(grade_card, fg_color="transparent")
        gc_top.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            gc_top,
            text="📏 Grade de Variações de Tamanho & Condições de Conservação (NR-6)",
            font=FONT_BODY_BOLD,
            text_color="#1E3A8A"
        ).pack(anchor="w")
        ctk.CTkLabel(
            gc_top,
            text="Adicione os tamanhos deste EPI (ex: 38 a 44, P a GG) e informe as quantidades por condição física.\nO saldo total disponível para entrega e a grade são calculados automaticamente!",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            justify="left"
        ).pack(anchor="w")

        # Botões de Predefinições Rápidas (Presets)
        presets_bar = ctk.CTkFrame(grade_card, fg_color="transparent")
        presets_bar.pack(fill="x", padx=12, pady=(4, 8))

        ctk.CTkLabel(presets_bar, text="Modelos Rápidos:", font=FONT_SMALL_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 6))

        rows_container = ctk.CTkFrame(grade_card, fg_color="transparent")
        rows_container.pack(fill="x", padx=12, pady=(0, 6))

        # Cabeçalho da grade de tamanhos
        g_head = ctk.CTkFrame(rows_container, fg_color="transparent")
        g_head.pack(fill="x", pady=(0, 3))
        g_head.grid_columnconfigure(0, weight=3) # Tamanho
        g_head.grid_columnconfigure(1, weight=2) # Novos
        g_head.grid_columnconfigure(2, weight=3) # Usados Bons
        g_head.grid_columnconfigure(3, weight=2) # Manutenção
        g_head.grid_columnconfigure(4, weight=2) # Descarte
        g_head.grid_columnconfigure(5, weight=1) # Ação

        ctk.CTkLabel(g_head, text="Tamanho *", font=FONT_SMALL_BOLD, anchor="w").grid(row=0, column=0, sticky="ew", padx=2)
        ctk.CTkLabel(g_head, text="🆕 Novos", font=FONT_SMALL_BOLD, anchor="center").grid(row=0, column=1, sticky="ew", padx=2)
        ctk.CTkLabel(g_head, text="♻️ Usados Bons", font=FONT_SMALL_BOLD, anchor="center").grid(row=0, column=2, sticky="ew", padx=2)
        ctk.CTkLabel(g_head, text="⚠️ Manutenção", font=FONT_SMALL_BOLD, anchor="center").grid(row=0, column=3, sticky="ew", padx=2)
        ctk.CTkLabel(g_head, text="🗑️ Descarte", font=FONT_SMALL_BOLD, anchor="center").grid(row=0, column=4, sticky="ew", padx=2)
        ctk.CTkLabel(g_head, text="", font=FONT_SMALL_BOLD).grid(row=0, column=5, sticky="ew", padx=2)

        g_rows_list = ctk.CTkFrame(rows_container, fg_color="transparent")
        g_rows_list.pack(fill="x")

        lbl_summary = ctk.CTkLabel(grade_card, text="", font=FONT_BODY_BOLD, text_color="#1E3A8A")
        lbl_summary.pack(anchor="w", padx=14, pady=(6, 10))

        grade_items = []

        def recalc_grade_totals(*args):
            tot_n = 0
            tot_u = 0
            tot_r = 0
            tot_d = 0
            for itm in grade_items:
                try:
                    tot_n += int(itm["novo"].get().strip() or 0)
                except ValueError: pass
                try:
                    tot_u += int(itm["usado"].get().strip() or 0)
                except ValueError: pass
                try:
                    tot_r += int(itm["ruim"].get().strip() or 0)
                except ValueError: pass
                try:
                    tot_d += int(itm["descarte"].get().strip() or 0)
                except ValueError: pass
            tot_disp = tot_n + tot_u
            lbl_summary.configure(
                text=f"📦 Saldo Disponível para Entrega: {tot_disp} un (🆕 {tot_n} Novos | ♻️ {tot_u} Reutilizáveis)  •  ⚠️ {tot_r} Manutenção  •  🗑️ {tot_d} Descarte"
            )

        def add_grade_row(tam="", novo=0, usado=0, ruim=0, descarte=0):
            rf = ctk.CTkFrame(g_rows_list, fg_color="transparent")
            rf.pack(fill="x", pady=2)
            rf.grid_columnconfigure(0, weight=3)
            rf.grid_columnconfigure(1, weight=2)
            rf.grid_columnconfigure(2, weight=3)
            rf.grid_columnconfigure(3, weight=2)
            rf.grid_columnconfigure(4, weight=2)
            rf.grid_columnconfigure(5, weight=1)

            t_ent = ctk.CTkEntry(rf, height=28, placeholder_text="Ex: 41, M...")
            t_ent.insert(0, str(tam))
            t_ent.grid(row=0, column=0, sticky="ew", padx=2)

            n_ent = ctk.CTkEntry(rf, height=28)
            n_ent.insert(0, str(novo))
            n_ent.grid(row=0, column=1, sticky="ew", padx=2)
            n_ent.bind("<KeyRelease>", recalc_grade_totals)

            u_ent = ctk.CTkEntry(rf, height=28)
            u_ent.insert(0, str(usado))
            u_ent.grid(row=0, column=2, sticky="ew", padx=2)
            u_ent.bind("<KeyRelease>", recalc_grade_totals)

            r_ent = ctk.CTkEntry(rf, height=28)
            r_ent.insert(0, str(ruim))
            r_ent.grid(row=0, column=3, sticky="ew", padx=2)
            r_ent.bind("<KeyRelease>", recalc_grade_totals)

            d_ent = ctk.CTkEntry(rf, height=28)
            d_ent.insert(0, str(descarte))
            d_ent.grid(row=0, column=4, sticky="ew", padx=2)
            d_ent.bind("<KeyRelease>", recalc_grade_totals)

            def remove_this_row():
                rf.destroy()
                if item_dict in grade_items:
                    grade_items.remove(item_dict)
                recalc_grade_totals()

            del_btn = ctk.CTkButton(rf, text="❌", width=28, height=28, fg_color="#EF4444", hover_color="#DC2626", command=remove_this_row)
            del_btn.grid(row=0, column=5, sticky="ew", padx=2)

            item_dict = {
                "tam": t_ent,
                "novo": n_ent,
                "usado": u_ent,
                "ruim": r_ent,
                "descarte": d_ent,
                "frame": rf
            }
            grade_items.append(item_dict)
            recalc_grade_totals()

        def apply_preset(preset_type):
            if preset_type == "calcados":
                sizes = ["36", "37", "38", "39", "40", "41", "42", "43", "44"]
            elif preset_type == "roupas":
                sizes = ["P", "M", "G", "GG", "XG"]
            elif preset_type == "luvas":
                sizes = ["7 (P)", "8 (M)", "9 (G)", "10 (XG)"]
            else:
                sizes = ["Único"]

            existing_tams = [it["tam"].get().strip().upper() for it in grade_items if it["tam"].get().strip()]
            for s in sizes:
                if s.upper() not in existing_tams:
                    add_grade_row(tam=s, novo=0, usado=0, ruim=0, descarte=0)

        btn_calcados = ctk.CTkButton(
            presets_bar,
            text="👟 Calçados (36 ao 44)",
            font=FONT_SMALL,
            height=26,
            fg_color="#0D9488",
            hover_color="#0F766E",
            command=lambda: apply_preset("calcados")
        )
        btn_calcados.pack(side="left", padx=2)

        btn_roupas = ctk.CTkButton(
            presets_bar,
            text="👕 Roupas (P ao XG)",
            font=FONT_SMALL,
            height=26,
            fg_color="#4F46E5",
            hover_color="#4338CA",
            command=lambda: apply_preset("roupas")
        )
        btn_roupas.pack(side="left", padx=2)

        btn_luvas = ctk.CTkButton(
            presets_bar,
            text="🧤 Luvas (7 a 10)",
            font=FONT_SMALL,
            height=26,
            fg_color="#D97706",
            hover_color="#B45309",
            command=lambda: apply_preset("luvas")
        )
        btn_luvas.pack(side="left", padx=2)

        btn_add_one = ctk.CTkButton(
            presets_bar,
            text="➕ Adicionar Tamanho",
            font=FONT_SMALL_BOLD,
            height=26,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            command=lambda: add_grade_row(tam="", novo=0, usado=0, ruim=0, descarte=0)
        )
        btn_add_one.pack(side="left", padx=4)

        # Preenche os dados existentes de grade
        if is_edit:
            existing_grades = EPIService.get_epi_grades(epi["id"])
            if existing_grades:
                for eg in existing_grades:
                    add_grade_row(
                        tam=eg["tamanho"],
                        novo=eg["novo"],
                        usado=eg["usado_bom"],
                        ruim=eg["ruim"],
                        descarte=eg["descarte"]
                    )
            else:
                add_grade_row(
                    tam=epi.get("tamanho") or "Único",
                    novo=epi.get("qtd_novos", epi.get("quantidade", 0)),
                    usado=epi.get("qtd_usados_bons", 0),
                    ruim=epi.get("qtd_ruins", 0),
                    descarte=epi.get("qtd_descarte", 0)
                )
        else:
            add_grade_row(tam="Único", novo=10, usado=0, ruim=0, descarte=0)

        # Linha: Preço Novo, Preço Usado (50%) e Vida Útil em Dias
        row_cost = ctk.CTkFrame(f, fg_color="transparent")
        row_cost.pack(fill="x", pady=(0, 8))
        row_cost.grid_columnconfigure((0, 1, 2), weight=1)

        p_box = ctk.CTkFrame(row_cost, fg_color="transparent")
        p_box.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(p_box, text="Preço Unit. Novo (R$) *", font=FONT_BODY_BOLD).pack(anchor="w")
        preco_entry = ctk.CTkEntry(p_box, placeholder_text="0.00", height=32)
        val_novo = float(epi.get("preco_unitario", 0.0) or 0.0) if is_edit else 0.0
        preco_entry.insert(0, f"{val_novo:.2f}" if is_edit else "0.00")
        preco_entry.pack(fill="x", pady=(2, 0))

        pu_box = ctk.CTkFrame(row_cost, fg_color="transparent")
        pu_box.grid(row=0, column=1, sticky="ew", padx=(6, 6))
        ctk.CTkLabel(pu_box, text="Preço Unit. Usado (50%) (R$)", font=FONT_BODY_BOLD).pack(anchor="w")
        preco_usado_entry = ctk.CTkEntry(pu_box, placeholder_text="0.00", height=32)
        if is_edit:
            val_usado = float(epi.get("preco_usado", 0.0) or 0.0)
            if val_usado <= 0.0 and val_novo > 0.0:
                val_usado = round(val_novo * 0.5, 2)
            preco_usado_entry.insert(0, f"{val_usado:.2f}")
        else:
            preco_usado_entry.insert(0, "0.00")
        preco_usado_entry.pack(fill="x", pady=(2, 0))

        def _auto_calc_preco_usado(*args):
            try:
                txt = preco_entry.get().replace(",", ".").strip()
                if txt:
                    novo_v = float(txt)
                    preco_usado_entry.delete(0, "end")
                    preco_usado_entry.insert(0, f"{novo_v * 0.5:.2f}")
            except Exception:
                pass

        preco_entry.bind("<KeyRelease>", _auto_calc_preco_usado)

        v_box = ctk.CTkFrame(row_cost, fg_color="transparent")
        v_box.grid(row=0, column=2, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(v_box, text="Vida Útil de Uso (Dias) *", font=FONT_BODY_BOLD).pack(anchor="w")
        vida_entry = ctk.CTkEntry(v_box, placeholder_text="Ex: 90", height=32)
        if is_edit:
            vida_entry.insert(0, str(epi.get("dias_vida_util", 0) or 0))
        else:
            vida_entry.insert(0, "90")
        vida_entry.pack(fill="x", pady=(2, 0))

        # Locais de Armazenamento (Permite 2 ou mais locais: Principal e Secundário / Reserva / Obra)
        loc_row = ctk.CTkFrame(f, fg_color="transparent")
        loc_row.pack(fill="x", pady=(2, 6))

        l1_col = ctk.CTkFrame(loc_row, fg_color="transparent")
        l1_col.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(l1_col, text="Local 1 - Principal (Prateleira / Almoxarifado):", font=FONT_SMALL).pack(anchor="w", pady=(0, 2))
        loc_entry = ctk.CTkEntry(l1_col, placeholder_text="Ex: Almoxarifado Central - Prat. B2", height=32)
        if is_edit and epi.get("localizacao"):
            loc_entry.insert(0, epi["localizacao"])
        loc_entry.pack(fill="x")

        l2_col = ctk.CTkFrame(loc_row, fg_color="transparent")
        l2_col.pack(side="left", fill="x", expand=True, padx=(6, 0))
        ctk.CTkLabel(l2_col, text="Local 2 - Secundário / Obra / Reserva:", font=FONT_SMALL).pack(anchor="w", pady=(0, 2))
        loc2_entry = ctk.CTkEntry(l2_col, placeholder_text="Ex: Depósito Frente de Obra 02", height=32)
        if is_edit and epi.get("localizacao_secundaria"):
            loc2_entry.insert(0, epi["localizacao_secundaria"])
        loc2_entry.pack(fill="x")

        # Descrição / Observações técnicas
        ctk.CTkLabel(f, text="Descrição Técnica do EPI:", font=FONT_SMALL).pack(anchor="w")
        desc_entry = ctk.CTkEntry(f, placeholder_text="Ex: Bota de segurança em PVC injetado, cano médio...", height=32)
        if is_edit and epi.get("descricao"):
            desc_entry.insert(0, epi["descricao"])
        desc_entry.pack(fill="x", pady=(2, 10))

        # Botões
        b_box = ctk.CTkFrame(dialog, fg_color="transparent")
        b_box.pack(fill="x", padx=25, pady=(0, 16))

        ctk.CTkButton(b_box, text="Cancelar", fg_color="#94A3B8", command=dialog.destroy).pack(side="left")

        def submit():
            cod = cod_entry.get().strip()
            nome = nome_entry.get().strip()
            ca = ca_entry.get().strip()
            min_q = min_entry.get().strip()

            if not cod or not nome or not ca or not min_q:
                messagebox.showerror("Campos Obrigatórios", "Preencha Código, Nome, C.A. e Estoque Mínimo!")
                return

            try:
                min_int = int(min_q)
                preco_val = float(preco_entry.get().replace(",", ".").strip() or 0.0)
                preco_usado_val = float(preco_usado_entry.get().replace(",", ".").strip() or 0.0)
                if preco_usado_val <= 0.0 and preco_val > 0.0:
                    preco_usado_val = round(preco_val * 0.5, 2)
                vida_val = int(vida_entry.get().strip() or 0)
            except ValueError:
                messagebox.showerror("Erro", "Estoque Mínimo e Vida Útil devem ser números inteiros, e os Preços devem ser numéricos!")
                return

            # Monta dados da grade de tamanhos e condições
            grades_data = []
            for itm in grade_items:
                t_val = itm["tam"].get().strip()
                if not t_val:
                    continue
                try: n_val = max(0, int(itm["novo"].get().strip() or 0))
                except ValueError: n_val = 0
                try: u_val = max(0, int(itm["usado"].get().strip() or 0))
                except ValueError: u_val = 0
                try: r_val = max(0, int(itm["ruim"].get().strip() or 0))
                except ValueError: r_val = 0
                try: d_val = max(0, int(itm["descarte"].get().strip() or 0))
                except ValueError: d_val = 0

                grades_data.append({
                    "tamanho": t_val,
                    "novo": n_val,
                    "usado_bom": u_val,
                    "ruim": r_val,
                    "descarte": d_val
                })

            if not grades_data:
                grades_data.append({"tamanho": "Único", "novo": 0, "usado_bom": 0, "ruim": 0, "descarte": 0})

            tot_disponivel = sum(g["novo"] + g["usado_bom"] for g in grades_data)
            tamanhos_str = ", ".join([g["tamanho"] for g in grades_data if g["tamanho"]]) or "Único"

            val_ca_save = val_entry.get().strip()
            if val_ca_save and "/" in val_ca_save:
                try:
                    val_ca_save = datetime.strptime(val_ca_save[:10], "%d/%m/%Y").strftime("%Y-%m-%d")
                except Exception:
                    pass

            data = {
                "codigo": cod,
                "nome": nome,
                "ca": ca,
                "validade_ca": val_ca_save,
                "fabricante": fab_entry.get().strip(),
                "tamanho": tamanhos_str,
                "unidade": un_var.get(),
                "estoque_minimo": min_int,
                "preco_unitario": preco_val,
                "preco_usado": preco_usado_val,
                "dias_vida_util": vida_val,
                "localizacao": loc_entry.get().strip(),
                "localizacao_secundaria": loc2_entry.get().strip(),
                "descricao": desc_entry.get().strip(),
                "grupo": (grupo_combo.get() or grupo_var.get() or "DIVERSOS / OUTROS").strip().upper(),
                "grades": grades_data,
                "quantidade": tot_disponivel
            }

            try:
                if is_edit:
                    EPIService.update_epi(epi["id"], data)
                    messagebox.showinfo("Sucesso", "Dados do EPI e Grade de Tamanhos atualizados!")
                else:
                    data["responsavel"] = "Almoxarifado"
                    EPIService.create_epi(data)
                    messagebox.showinfo("Sucesso", "Novo EPI e Grade de Tamanhos cadastrados com sucesso!")

                dialog.destroy()
                self.refresh()
                if self.on_refresh_dashboard:
                    self.on_refresh_dashboard()
            except Exception as ex:
                messagebox.showerror("Erro ao Salvar", str(ex))

        ctk.CTkButton(b_box, text="Salvar Alterações" if is_edit else "Cadastrar EPI", fg_color="#1E3A8A", height=36, font=FONT_BODY_BOLD, command=submit).pack(side="right")

    def _export_pdf_grouped(self):
        """Exporta inventário em PDF oficial agrupado por famílias e com grade de tamanhos."""
        from services.pdf_service import PDFService
        try:
            if not self.current_epis:
                messagebox.showwarning("Aviso", "Nenhum EPI para exportar.")
                return

            ans = messagebox.askyesnocancel(
                "Exportar Inventário em PDF",
                "Deseja exportar SOMENTE itens com Saldo em Estoque (> 0)?\n\n"
                "• SIM: Apenas itens com saldo positivo no estoque (Recomendado).\n"
                "• NÃO: Incluir também itens zerados.\n"
                "• CANCELAR: Abortar exportação."
            )
            if ans is None:
                return

            only_in_stock = bool(ans)
            filepath = PDFService.generate_grouped_inventory_pdf(self.current_epis, only_in_stock=only_in_stock)

            ans_open = messagebox.askyesno(
                "Relatório PDF Gerado",
                f"Relatório de Inventário em PDF gerado com sucesso!\n\n"
                f"Arquivo: {filepath}\n\n"
                f"• Agrupamento por Famílias: Ativo\n"
                f"• Grade de Quantidades por Tamanho: Ativa\n"
                f"• Filtro: {'Apenas itens com saldo > 0' if only_in_stock else 'Todos os itens'}\n\n"
                f"Deseja abrir o arquivo PDF agora?"
            )
            if ans_open:
                os.startfile(filepath)
        except Exception as ex:
            messagebox.showerror("Erro ao Gerar PDF", str(ex))

    def _export_manut_descarte_pdf(self):
        """Exporta relatório gerencial de itens em Quarentena / Manutenção e Descarte em PDF."""
        from services.pdf_service import PDFService
        try:
            filepath = PDFService.generate_maintenance_discard_pdf()
            ans = messagebox.askyesno(
                "Relatório de Manutenção & Descarte Gerado",
                f"Relatório Oficial de Gestão de EPIs em Manutenção e Descarte gerado com sucesso!\n\n"
                f"Arquivo:\n{filepath}\n\n"
                f"Deseja abrir o arquivo PDF agora para visualização e impressão?"
            )
            if ans:
                os.startfile(filepath)
        except Exception as ex:
            messagebox.showerror("Erro ao Gerar Relatório", str(ex))

    def _open_maintenance_discard_dialog(self):
        """Abre painel dedicado para gestão visual do estoque em Quarentena, Reparo e Descarte."""
        from services.pdf_service import PDFService
        from database import get_connection

        with get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT g.id, g.epi_id, g.tamanho, g.estado, g.quantidade,
                       e.codigo as epi_codigo, e.nome as epi_nome, e.ca as epi_ca,
                       e.fabricante as epi_fabricante, e.unidade as epi_unidade,
                       COALESCE(e.preco_unitario, 0.0) as preco_unitario
                FROM epi_grades g
                JOIN epis e ON g.epi_id = e.id
                WHERE g.quantidade > 0
                  AND (
                      UPPER(g.estado) LIKE '%RUIM%' OR UPPER(g.estado) LIKE '%MANUT%' OR UPPER(g.estado) LIKE '%REPAR%'
                      OR UPPER(g.estado) LIKE '%DESC%' OR UPPER(g.estado) LIKE '%SUCATA%' OR UPPER(g.estado) LIKE '%INSERV%'
                  )
                ORDER BY g.estado ASC, e.nome ASC, g.tamanho ASC;
            """
            rows = cursor.execute(query).fetchall()
            items = [dict(r) for r in rows]

        dialog = ctk.CTkToplevel(self)
        dialog.title("Estoque Separado: ⚠️ Manutenção & 🗑️ Descarte (NR-6)")
        dialog.geometry("920x620")
        dialog.minsize(860, 560)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 920) // 2
        y = (dialog.winfo_screenheight() - 620) // 2
        dialog.geometry(f"+{x}+{y}")

        # Topo
        top_bar = ctk.CTkFrame(dialog, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(15, 10))

        title_f = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_f.pack(side="left")
        ctk.CTkLabel(title_f, text="⚠️ Gestão de Estoque: Manutenção & Descarte", font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_f, text="Itens isolados fora do estoque ativo. Não contam no inventário físico regular.", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w")

        btn_pdf_m = ctk.CTkButton(
            top_bar,
            text="📄 Imprimir Relatório PDF",
            font=FONT_BODY_BOLD,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            height=34,
            command=self._export_manut_descarte_pdf
        )
        btn_pdf_m.pack(side="right")

        # KPIs Rápidos
        total_m = sum(int(x["quantidade"]) for x in items if not any(k in str(x["estado"]).upper() for k in ["DESC", "SUCATA", "INSERV"]))
        total_d = sum(int(x["quantidade"]) for x in items if any(k in str(x["estado"]).upper() for k in ["DESC", "SUCATA", "INSERV"]))
        valor_m = sum(int(x["quantidade"]) * float(x["preco_unitario"]) for x in items if not any(k in str(x["estado"]).upper() for k in ["DESC", "SUCATA", "INSERV"]))
        valor_d = sum(int(x["quantidade"]) * float(x["preco_unitario"]) for x in items if any(k in str(x["estado"]).upper() for k in ["DESC", "SUCATA", "INSERV"]))

        kpi_f = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        kpi_f.pack(fill="x", padx=20, pady=(0, 10))
        kpi_f.grid_columnconfigure((0, 1, 2), weight=1)

        def _add_kpi(parent, col, title, val_text, color):
            box = ctk.CTkFrame(parent, fg_color="transparent")
            box.grid(row=0, column=col, padx=15, pady=8, sticky="ew")
            ctk.CTkLabel(box, text=title, font=FONT_SMALL_BOLD, text_color=TEXT_MUTED).pack(anchor="w")
            ctk.CTkLabel(box, text=val_text, font=FONT_BODY_BOLD, text_color=color).pack(anchor="w")

        _add_kpi(kpi_f, 0, "EM MANUTENÇÃO / REPARO:", f"{total_m} un (R$ {valor_m:.2f})", "#D97706")
        _add_kpi(kpi_f, 1, "EM DESCARTE / BAIXA (SUCATA):", f"{total_d} un (R$ {valor_d:.2f})", "#DC2626")
        _add_kpi(kpi_f, 2, "TOTAL EM QUARENTENA:", f"{total_m + total_d} un (R$ {(valor_m + valor_d):.2f})", "#1E3A8A")

        # Tabela
        tbl_box = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        tbl_box.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        m_cols = [
            {"id": "cod", "text": "Código", "width": 75, "anchor": "center"},
            {"id": "nome", "text": "Equipamento (EPI)", "width": 240, "anchor": "w"},
            {"id": "tam", "text": "Tam.", "width": 55, "anchor": "center"},
            {"id": "ca", "text": "C.A.", "width": 65, "anchor": "center"},
            {"id": "estado", "text": "Situação", "width": 140, "anchor": "center"},
            {"id": "qtd", "text": "Qtd", "width": 60, "anchor": "center"},
            {"id": "preco", "text": "Valor Unit.", "width": 85, "anchor": "center"},
            {"id": "total", "text": "Total R$", "width": 95, "anchor": "center"},
        ]
        m_table = StyledTable(tbl_box, columns=m_cols)
        m_table.pack(fill="both", expand=True, padx=8, pady=8)

        for it in items:
            q = int(it["quantidade"])
            pu = float(it["preco_unitario"])
            tot = q * pu
            st_raw = str(it.get("estado", "")).upper()
            if any(k in st_raw for k in ["DESC", "SUCATA", "INSERV"]):
                st_disp = "🗑️ DESCARTE"
                tag = "danger"
            else:
                st_disp = "⚠️ MANUTENÇÃO"
                tag = "warning"

            m_table.insert_row(
                it["id"],
                [
                    it["epi_codigo"],
                    it["epi_nome"],
                    str(it.get("tamanho", "Único")),
                    str(it.get("epi_ca", "-")),
                    st_disp,
                    f"{q} {it.get('epi_unidade', 'UN')}",
                    f"R$ {pu:.2f}",
                    f"R$ {tot:.2f}"
                ],
                tag=tag
            )

        # Botão Fechar
        bot = ctk.CTkFrame(dialog, fg_color="transparent")
        bot.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkButton(bot, text="Fechar", width=100, height=32, fg_color="#64748B", hover_color="#475569", command=dialog.destroy).pack(side="right")

    def _export_excel(self):
        try:
            if not self.current_epis:
                messagebox.showwarning("Aviso", "Nenhum dado para exportar.")
                return

            ans = messagebox.askyesnocancel(
                "Exportar Inventário Excel",
                "Deseja exportar SOMENTE itens com Saldo em Estoque (> 0)?\n\n"
                "• SIM: Apenas itens com saldo positivo no estoque.\n"
                "• NÃO: Incluir também itens zerados.\n"
                "• CANCELAR: Abortar exportação."
            )
            if ans is None:
                return

            only_in_stock = bool(ans)
            filepath = ExcelService.export_inventory(self.current_epis, only_in_stock=only_in_stock)
            ans_open = messagebox.askyesno(
                "Inventário Exportado",
                f"Planilha Excel gerada com sucesso em:\n{filepath}\n\n"
                f"• Filtro: {'Apenas itens com saldo > 0' if only_in_stock else 'Todos os itens'}\n\n"
                f"Deseja abrir agora?"
            )
            if ans_open:
                os.startfile(filepath)
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def open_stock_entry_modal(self, preselected_id=None):
        """Abre modal completo e intuitivo para Entrada de Estoque / Compra de Fornecedor / NF."""
        if not preselected_id:
            sel = self.table.get_selected()
            if sel:
                try:
                    preselected_id = int(sel)
                except (ValueError, TypeError):
                    preselected_id = None

        from ui.views.movements_view import open_stock_entry_dialog
        def _on_entry_success():
            self.refresh()
            if self.on_refresh_dashboard:
                self.on_refresh_dashboard()

        open_stock_entry_dialog(self, preselected_epi_id=preselected_id, on_success=_on_entry_success)

    def _open_quick_stock_entry(self, preselected_id=None):
        """Compatibilidade: redireciona para o modal oficial de Entrada de Estoque / Compra."""
        self.open_stock_entry_modal(preselected_id)

    def _open_group_manager(self):
        """Abre janela para cadastrar, editar, excluir grupos e vincular itens a eles."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Gerenciador de Grupos & Famílias de EPI")
        dialog.geometry("980x640")
        dialog.resizable(True, True)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 980) // 2
        y = (dialog.winfo_screenheight() - 640) // 2
        dialog.geometry(f"+{x}+{y}")

        # Topo
        top = ctk.CTkFrame(dialog, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(15, 10))
        ctk.CTkLabel(top, text="📁 Gerenciador de Grupos & Famílias de EPI", font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(
            top,
            text="Organize seus EPIs por famílias (ex: BOTA DE PVC, BOTA TÉRMICA, CAMISAS, LUVAS). Os grupos são usados no inventário e no relatório oficial em PDF com grade de tamanhos.",
            font=FONT_SMALL,
            text_color=TEXT_MUTED
        ).pack(anchor="w")

        # Container Principal com 2 Colunas
        container = ctk.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        container.grid_columnconfigure(0, weight=4)
        container.grid_columnconfigure(1, weight=6)
        container.grid_rowconfigure(0, weight=1)

        # === COLUNA ESQUERDA: GRUPOS ===
        col_left = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        col_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        head_l = ctk.CTkFrame(col_left, fg_color="transparent")
        head_l.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkLabel(head_l, text="Grupos Cadastrados", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(side="left")

        btn_box_l = ctk.CTkFrame(col_left, fg_color="transparent")
        btn_box_l.pack(fill="x", padx=12, pady=(0, 8))

        cols_g = [
            {"id": "nome", "text": "Nome do Grupo", "width": 190, "anchor": "w"},
            {"id": "skus", "text": "SKUs", "width": 55, "anchor": "center"},
            {"id": "saldo", "text": "Saldo", "width": 60, "anchor": "center"},
        ]

        # === COLUNA DIREITA: ITENS DO GRUPO ===
        col_right = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        col_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        head_r = ctk.CTkFrame(col_right, fg_color="transparent")
        head_r.pack(fill="x", padx=12, pady=(12, 6))
        lbl_grupo_sel = ctk.CTkLabel(head_r, text="Selecione um grupo ao lado para ver os itens", font=FONT_BODY_BOLD, text_color=TEXT_MAIN)
        lbl_grupo_sel.pack(side="left")

        btn_box_r = ctk.CTkFrame(col_right, fg_color="transparent")
        btn_box_r.pack(fill="x", padx=12, pady=(0, 8))

        cols_i = [
            {"id": "codigo", "text": "Código", "width": 75, "anchor": "center"},
            {"id": "nome", "text": "EPI", "width": 200, "anchor": "w"},
            {"id": "tam", "text": "Tam.", "width": 55, "anchor": "center"},
            {"id": "saldo", "text": "Saldo", "width": 60, "anchor": "center"},
        ]
        tbl_i = StyledTable(col_right, columns=cols_i)
        tbl_i.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        active_group = {"nome": None}

        def on_group_selected(row_id):
            if not row_id:
                return
            active_group["nome"] = str(row_id)
            lbl_grupo_sel.configure(text=f"📦 Itens Vinculados a: {active_group['nome']}")
            refresh_itens_table()

        tbl_g = StyledTable(col_left, columns=cols_g, on_select=on_group_selected)
        tbl_g.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        def refresh_grupos_table():
            grupos = EPIService.list_grupos()
            tbl_g.clear()
            for g in grupos:
                tbl_g.insert_row(
                    g["nome"],
                    [
                        g["nome"],
                        f"{g['total_itens']} itens",
                        f"{g['total_saldo']} un"
                    ]
                )
            if active_group["nome"]:
                refresh_itens_table()

        def refresh_itens_table():
            tbl_i.clear()
            if not active_group["nome"]:
                return
            epis = EPIService.list_epis(filter_grupo=active_group["nome"])
            for e in epis:
                tbl_i.insert_row(
                    e["id"],
                    [
                        e["codigo"],
                        e["nome"],
                        e.get("tamanho") or "Único",
                        f"{e['quantidade']} {e.get('unidade', 'UN')}"
                    ]
                )

        def criar_novo_grupo_action():
            novo = simpledialog.askstring("Novo Grupo de EPI", "Digite o nome do novo Grupo/Família de EPI:\n(Ex: GRUPO DE BOTA PVC, BOTA TÉRMICA, CAMISAS...)")
            if novo and novo.strip():
                nome_fmt = novo.strip().upper()
                try:
                    EPIService.create_grupo(nome_fmt)
                    messagebox.showinfo("Sucesso", f"Grupo '{nome_fmt}' cadastrado com sucesso!")
                    refresh_grupos_table()
                    self.refresh()
                except Exception as err:
                    messagebox.showerror("Erro ao Criar", str(err))

        def excluir_grupo_action():
            sel = tbl_g.get_selected()
            if not sel:
                messagebox.showwarning("Aviso", "Selecione um grupo na lista da esquerda para excluir.")
                return
            if sel in ["DIVERSOS / OUTROS", "GERAL"]:
                messagebox.showerror("Erro", "O grupo padrão 'DIVERSOS / OUTROS' não pode ser excluído.")
                return
            ans = messagebox.askyesno(
                "Confirmar Exclusão",
                f"Tem certeza que deseja excluir o grupo '{sel}'?\n\n"
                f"Os EPIs vinculados a ele NÃO serão apagados, apenas serão movidos para 'DIVERSOS / OUTROS'."
            )
            if ans:
                try:
                    EPIService.delete_grupo(sel)
                    messagebox.showinfo("Sucesso", f"Grupo '{sel}' excluído com sucesso!")
                    active_group["nome"] = None
                    lbl_grupo_sel.configure(text="Selecione um grupo ao lado")
                    refresh_grupos_table()
                    tbl_i.clear()
                    self.refresh()
                except Exception as err:
                    messagebox.showerror("Erro ao Excluir", str(err))

        def vincular_itens_action():
            if not active_group["nome"]:
                messagebox.showwarning("Aviso", "Selecione primeiro um grupo na lista da esquerda para onde deseja vincular itens.")
                return

            v_dialog = ctk.CTkToplevel(dialog)
            v_dialog.title(f"Vincular EPIs ao Grupo: {active_group['nome']}")
            v_dialog.geometry("740x520")
            v_dialog.grab_set()

            v_dialog.update_idletasks()
            vx = (v_dialog.winfo_screenwidth() - 740) // 2
            vy = (v_dialog.winfo_screenheight() - 520) // 2
            v_dialog.geometry(f"+{vx}+{vy}")

            ctk.CTkLabel(
                v_dialog,
                text=f"🔗 Vincular Itens ao Grupo: {active_group['nome']}",
                font=FONT_SUBTITLE,
                text_color=TEXT_MAIN
            ).pack(pady=(15, 4))
            ctk.CTkLabel(
                v_dialog,
                text="Selecione o EPI na lista abaixo que pertence a este grupo e clique em Confirmar Vínculo:",
                font=FONT_SMALL,
                text_color=TEXT_MUTED
            ).pack(pady=(0, 10))

            search_f = ctk.CTkFrame(v_dialog, fg_color="transparent")
            search_f.pack(fill="x", padx=20, pady=(0, 10))
            ctk.CTkLabel(search_f, text="🔍 Filtrar:", font=FONT_BODY_BOLD).pack(side="left", padx=(0, 5))
            v_search_var = tk.StringVar()
            v_search_entry = ctk.CTkEntry(search_f, placeholder_text="Filtrar por nome, código, C.A...", textvariable=v_search_var, width=320, height=32)
            v_search_entry.pack(side="left")

            cols_v = [
                {"id": "codigo", "text": "Código", "width": 80, "anchor": "center"},
                {"id": "nome", "text": "Nome do EPI", "width": 240, "anchor": "w"},
                {"id": "grupo_atual", "text": "Grupo Atual", "width": 160, "anchor": "w"},
                {"id": "tam", "text": "Tam.", "width": 55, "anchor": "center"},
                {"id": "saldo", "text": "Saldo", "width": 60, "anchor": "center"},
            ]
            v_tbl = StyledTable(v_dialog, columns=cols_v)
            v_tbl.pack(fill="both", expand=True, padx=20, pady=(0, 12))

            def refresh_v_table():
                term = v_search_var.get().strip()
                all_epis = EPIService.list_epis(search=term)
                v_tbl.clear()
                for ep in all_epis:
                    v_tbl.insert_row(
                        ep["id"],
                        [
                            ep["codigo"],
                            ep["nome"],
                            ep.get("grupo") or "DIVERSOS / OUTROS",
                            ep.get("tamanho") or "Único",
                            f"{ep['quantidade']} {ep.get('unidade', 'UN')}"
                        ]
                    )

            v_search_entry.bind("<KeyRelease>", lambda e: refresh_v_table())
            refresh_v_table()

            btn_box_v = ctk.CTkFrame(v_dialog, fg_color="transparent")
            btn_box_v.pack(fill="x", padx=20, pady=(0, 15))
            ctk.CTkButton(btn_box_v, text="Cancelar", fg_color="#94A3B8", command=v_dialog.destroy).pack(side="left")

            def confirmar_vinculo():
                sel_id = v_tbl.get_selected()
                if not sel_id:
                    messagebox.showwarning("Aviso", "Selecione um EPI na tabela para vincular a este grupo.")
                    return
                try:
                    EPIService.reassign_epi_grupo(int(sel_id), active_group["nome"])
                    messagebox.showinfo("Sucesso", f"Item vinculado com sucesso ao grupo '{active_group['nome']}'!")
                    v_dialog.destroy()
                    refresh_grupos_table()
                    refresh_itens_table()
                    self.refresh()
                except Exception as err:
                    messagebox.showerror("Erro ao Vincular", str(err))

            ctk.CTkButton(
                btn_box_v,
                text=f"Confirmar Vínculo ao Grupo '{active_group['nome']}'",
                font=FONT_BODY_BOLD,
                fg_color="#0D9488",
                hover_color="#0F766E",
                command=confirmar_vinculo
            ).pack(side="right")

        def mudar_grupo_item_action():
            sel_item_id = tbl_i.get_selected()
            if not sel_item_id:
                messagebox.showwarning("Aviso", "Selecione um item na tabela da direita para alterar o grupo.")
                return

            epi_atual = EPIService.get_epi(int(sel_item_id))
            if not epi_atual:
                return

            ch_dialog = ctk.CTkToplevel(dialog)
            ch_dialog.title("Alterar Grupo do EPI")
            ch_dialog.geometry("460x260")
            ch_dialog.grab_set()

            ch_dialog.update_idletasks()
            cx = (ch_dialog.winfo_screenwidth() - 460) // 2
            cy = (ch_dialog.winfo_screenheight() - 260) // 2
            ch_dialog.geometry(f"+{cx}+{cy}")

            ctk.CTkLabel(ch_dialog, text=f"Alterar Grupo de: {epi_atual['nome']}", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(pady=(20, 10), padx=20)
            ctk.CTkLabel(ch_dialog, text="Selecione o novo grupo de destino para este EPI:", font=FONT_SMALL, text_color=TEXT_MUTED).pack(pady=(0, 10))

            novos_g = EPIService.list_nomes_grupos()
            sel_new_var = tk.StringVar(value=novos_g[0] if novos_g else "DIVERSOS / OUTROS")
            combo_dest = ctk.CTkComboBox(ch_dialog, values=novos_g, variable=sel_new_var, width=320, height=34)
            combo_dest.pack(pady=(0, 20))

            btn_box_ch = ctk.CTkFrame(ch_dialog, fg_color="transparent")
            btn_box_ch.pack(fill="x", padx=30, pady=(0, 15))
            ctk.CTkButton(btn_box_ch, text="Cancelar", fg_color="#94A3B8", command=ch_dialog.destroy).pack(side="left")

            def confirmar_mudanca():
                novo_dest = sel_new_var.get().strip().upper()
                try:
                    EPIService.reassign_epi_grupo(int(sel_item_id), novo_dest)
                    messagebox.showinfo("Sucesso", f"Item movido para o grupo '{novo_dest}' com sucesso!")
                    ch_dialog.destroy()
                    refresh_grupos_table()
                    refresh_itens_table()
                    self.refresh()
                except Exception as err:
                    messagebox.showerror("Erro ao Mover", str(err))

            ctk.CTkButton(btn_box_ch, text="Mover Item", font=FONT_BODY_BOLD, fg_color="#1E3A8A", hover_color="#1D4ED8", command=confirmar_mudanca).pack(side="right")

        # Botões do painel esquerdo
        btn_novo_grp = ctk.CTkButton(
            btn_box_l,
            text="➕ Novo Grupo",
            font=FONT_SMALL_BOLD,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=30,
            command=criar_novo_grupo_action
        )
        btn_novo_grp.pack(side="left", padx=(0, 4))

        btn_del_grp = ctk.CTkButton(
            btn_box_l,
            text="🗑️ Excluir",
            font=FONT_SMALL_BOLD,
            fg_color="#EF4444",
            hover_color="#DC2626",
            height=30,
            command=excluir_grupo_action
        )
        btn_del_grp.pack(side="left")

        # Botões do painel direito
        btn_vincular = ctk.CTkButton(
            btn_box_r,
            text="🔗 Vincular Item a Este Grupo",
            font=FONT_SMALL_BOLD,
            fg_color="#0D9488",
            hover_color="#0F766E",
            height=30,
            command=vincular_itens_action
        )
        btn_vincular.pack(side="left", padx=(0, 6))

        btn_mudar_grp = ctk.CTkButton(
            btn_box_r,
            text="✏️ Trocar Grupo do Item",
            font=FONT_SMALL_BOLD,
            fg_color="#475569",
            hover_color="#334155",
            height=30,
            command=mudar_grupo_item_action
        )
        btn_mudar_grp.pack(side="left")

        refresh_grupos_table()
