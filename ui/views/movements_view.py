import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from datetime import datetime, timedelta
import os
import subprocess

from services.movement_service import MovementService
from services.epi_service import EPIService
from services.employee_service import EmployeeService
from services.excel_service import ExcelService
from services.pdf_service import PDFService
from services.auth_service import AuthService
from ui.components.theme import *
from ui.components.table_view import StyledTable

class MovementsView(ctk.CTkFrame):
    def __init__(self, parent, on_refresh_dashboard=None):
        super().__init__(parent, fg_color="transparent")
        self.on_refresh_dashboard = on_refresh_dashboard
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Cabeçalho da tela
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(20, 15))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(title_box, text="Saídas & Movimentações de EPI", font=FONT_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Registro rigoroso de entrega com identificação de quem retirou e quem entregou", font=FONT_BODY, text_color=TEXT_MUTED).pack(anchor="w")

        # Botões de ação no cabeçalho organizados em duas linhas elegantes para evitar cortes
        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")

        # Linha 1: Operações Principais de Estoque & Entrega
        row_top = ctk.CTkFrame(btn_box, fg_color="transparent")
        row_top.pack(anchor="e", pady=(0, 4))

        btn_entrada = ctk.CTkButton(
            row_top,
            text="📥 Registrar Entrada (Compra)",
            font=FONT_BODY_BOLD,
            fg_color="#059669",
            hover_color="#047857",
            height=32,
            command=self.open_entry_modal
        )
        btn_entrada.pack(side="left", padx=3)

        btn_saida = ctk.CTkButton(
            row_top,
            text="➕ Registrar Saída (Entrega)",
            font=FONT_BODY_BOLD,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=32,
            command=self.open_exit_modal
        )
        btn_saida.pack(side="left", padx=3)

        # Linha 2: Ferramentas, Relatórios e Gestão de Lançamentos
        row_bottom = ctk.CTkFrame(btn_box, fg_color="transparent")
        row_bottom.pack(anchor="e")

        btn_excel = ctk.CTkButton(
            row_bottom,
            text="📊 Excel",
            font=FONT_BODY,
            fg_color="#0D9488",
            hover_color="#0F766E",
            height=30,
            command=self._export_excel
        )
        btn_excel.pack(side="left", padx=3)

        btn_pdf = ctk.CTkButton(
            row_bottom,
            text="📄 Relatório PDF",
            font=FONT_BODY,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            height=30,
            command=self._export_pdf
        )
        btn_pdf.pack(side="left", padx=3)

        if AuthService.is_admin():
            self.btn_edit_mov = ctk.CTkButton(
                row_bottom,
                text="✏️ Editar",
                font=FONT_BODY,
                fg_color="#D97706",
                hover_color="#B45309",
                height=30,
                command=self._edit_selected_movement
            )
            self.btn_edit_mov.pack(side="left", padx=3)

            self.btn_del_mov = ctk.CTkButton(
                row_bottom,
                text="🗑️ Excluir",
                font=FONT_BODY,
                fg_color="#B91C1C",
                hover_color="#991B1B",
                height=30,
                command=self._delete_selected_movement
            )
            self.btn_del_mov.pack(side="left", padx=3)

        # Barra de Filtros
        filter_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        filter_card.pack(fill="x", padx=25, pady=(0, 15))

        f_inner = ctk.CTkFrame(filter_card, fg_color="transparent")
        f_inner.pack(fill="x", padx=15, pady=10)

        # Campo de busca
        ctk.CTkLabel(f_inner, text="🔍 Buscar:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            f_inner,
            placeholder_text="EPI, funcionário, C.A., quem entregou...",
            textvariable=self.search_var,
            width=260,
            height=32
        )
        self.search_entry.pack(side="left", padx=(0, 15))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh())

        # Tipo de Movimento
        ctk.CTkLabel(f_inner, text="Tipo:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 5))
        self.tipo_var = tk.StringVar(value="TODOS")
        self.tipo_combo = ctk.CTkComboBox(
            f_inner,
            values=["TODOS", "SAIDA", "ENTRADA", "DEVOLUCAO", "NÃO DEVOLVIDO"],
            variable=self.tipo_var,
            width=175,
            height=32,
            command=lambda v: self.refresh()
        )
        self.tipo_combo.pack(side="left", padx=(0, 15))

        # Período
        from ui.components.date_picker import open_date_picker

        ctk.CTkLabel(f_inner, text="De:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 4))
        self.dt_ini_var = tk.StringVar()
        self.dt_ini_entry = ctk.CTkEntry(f_inner, textvariable=self.dt_ini_var, placeholder_text="DD/MM/AAAA", width=95, height=32)
        self.dt_ini_entry.pack(side="left", padx=(0, 2))
        self.dt_ini_entry.bind("<Return>", lambda e: self.refresh())
        self.dt_ini_entry.bind("<Double-Button-1>", lambda e: open_date_picker(self, target_var=self.dt_ini_var, on_change=self.refresh))

        btn_cal_ini = ctk.CTkButton(
            f_inner, text="📅", width=32, height=32,
            fg_color="#334155", hover_color="#475569",
            command=lambda: open_date_picker(self, target_var=self.dt_ini_var, on_change=self.refresh)
        )
        btn_cal_ini.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(f_inner, text="Até:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 4))
        self.dt_fim_var = tk.StringVar()
        self.dt_fim_entry = ctk.CTkEntry(f_inner, textvariable=self.dt_fim_var, placeholder_text="DD/MM/AAAA", width=95, height=32)
        self.dt_fim_entry.pack(side="left", padx=(0, 2))
        self.dt_fim_entry.bind("<Return>", lambda e: self.refresh())
        self.dt_fim_entry.bind("<Double-Button-1>", lambda e: open_date_picker(self, target_var=self.dt_fim_var, on_change=self.refresh))

        btn_cal_fim = ctk.CTkButton(
            f_inner, text="📅", width=32, height=32,
            fg_color="#334155", hover_color="#475569",
            command=lambda: open_date_picker(self, target_var=self.dt_fim_var, on_change=self.refresh)
        )
        btn_cal_fim.pack(side="left", padx=(0, 8))

        btn_filtrar = ctk.CTkButton(f_inner, text="🔍 Filtrar", width=75, height=32, command=self.refresh)
        btn_filtrar.pack(side="left", padx=3)

        btn_limpar = ctk.CTkButton(
            f_inner,
            text="Limpar",
            width=65,
            height=32,
            fg_color="#64748B",
            hover_color="#475569",
            command=self._clear_filters
        )
        btn_limpar.pack(side="left", padx=3)

        # Atalhos rápidos de período
        ctk.CTkButton(f_inner, text="Hoje", width=48, height=28, fg_color=BORDER_COLOR, text_color=TEXT_MAIN, command=lambda: self._set_period_shortcut("today")).pack(side="left", padx=2)
        ctk.CTkButton(f_inner, text="7 dias", width=52, height=28, fg_color=BORDER_COLOR, text_color=TEXT_MAIN, command=lambda: self._set_period_shortcut("week")).pack(side="left", padx=2)
        ctk.CTkButton(f_inner, text="Este Mês", width=65, height=28, fg_color=BORDER_COLOR, text_color=TEXT_MAIN, command=lambda: self._set_period_shortcut("month")).pack(side="left", padx=2)
        ctk.CTkButton(f_inner, text="Tudo", width=45, height=28, fg_color=BORDER_COLOR, text_color=TEXT_MAIN, command=lambda: self._set_period_shortcut("all")).pack(side="left", padx=2)

        # Contador de Registros
        self.count_lbl = ctk.CTkLabel(f_inner, text="0 registros", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.count_lbl.pack(side="right")

        # Tabela de Movimentações
        tbl_container = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        tbl_container.pack(fill="both", expand=True, padx=25, pady=(0, 20))

        cols = [
            {"id": "data", "text": "Data / Hora", "width": 120, "anchor": "center"},
            {"id": "tipo", "text": "Tipo", "width": 75, "anchor": "center"},
            {"id": "codigo", "text": "Cód.", "width": 65, "anchor": "center"},
            {"id": "epi", "text": "Equipamento (EPI)", "width": 190, "anchor": "w"},
            {"id": "ca", "text": "C.A.", "width": 60, "anchor": "center"},
            {"id": "tam", "text": "Tam.", "width": 55, "anchor": "center"},
            {"id": "estado", "text": "Condição", "width": 105, "anchor": "center"},
            {"id": "qtd", "text": "Qtd", "width": 55, "anchor": "center"},
            {"id": "func", "text": "Funcionário Destino", "width": 160, "anchor": "w"},
            {"id": "resp", "text": "Quem Entregou / Lançou", "width": 140, "anchor": "w"},
            {"id": "motivo", "text": "Motivo da Saída", "width": 130, "anchor": "w"},
            {"id": "obs", "text": "Observações", "width": 140, "anchor": "w"},
        ]
        self.table = StyledTable(
            tbl_container,
            columns=cols,
            on_double_click=lambda row_id: self._edit_movement_by_id(row_id) if AuthService.is_admin() else None
        )
        self.table.pack(fill="both", expand=True, padx=12, pady=12)

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
        self.refresh()

    def _clear_filters(self):
        self.search_var.set("")
        self.tipo_var.set("TODOS")
        self.dt_ini_var.set("")
        self.dt_fim_var.set("")
        self.refresh()

    def refresh(self):
        if hasattr(self, "table"):
            self.table.apply_theme(ctk.get_appearance_mode())

        search = self.search_var.get().strip()
        tipo = self.tipo_var.get().strip()
        dt_ini = self.dt_ini_var.get().strip() or None
        dt_fim = self.dt_fim_var.get().strip() or None

        self.current_movements = MovementService.list_movements(
            tipo=tipo,
            search=search,
            data_inicio=dt_ini,
            data_fim=dt_fim
        )

        self.table.clear()
        for m in self.current_movements:
            dt = m["data_hora"]
            try:
                dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass

            t_raw = m.get("tipo", "")
            est_raw = (m.get("mov_estado") or m.get("estado_conservacao") or "NOVO").upper()
            is_nao_dev = t_raw in ("NÃO DEVOLVIDO", "EXTRAVIO_DEMISSAO") or "NÃO DEVOLV" in est_raw or "NAO DEVOLV" in est_raw or "RETIDO" in est_raw

            tag = "even"
            if is_nao_dev:
                tipo_display = "🚨 NÃO DEVOLVIDO"
                tag = "danger"
            elif t_raw == "SAIDA":
                tipo_display = "SAIDA"
                tag = "danger" if "Perda" in m.get("motivo", "") else "odd"
            elif t_raw == "ENTRADA":
                tipo_display = "ENTRADA"
                tag = "success"
            elif t_raw == "DEVOLUCAO":
                tipo_display = "DEVOLUCAO"
                tag = "success"
            else:
                tipo_display = t_raw

            func_str = m.get("func_nome") or "Almoxarifado"
            if m.get("func_matricula"):
                func_str += f" ({m['func_matricula']})"

            # Formata tamanho e condição
            tam_str = m.get("mov_tamanho") or "Único"
            if is_nao_dev:
                est_display = "🚨 NÃO DEVOLVIDO"
            elif "NOVO" in est_raw:
                est_display = "🆕 NOVO"
            elif "BOM" in est_raw or "REUTIL" in est_raw or "HIGIEN" in est_raw:
                est_display = "♻️ REUTILIZADO"
            elif "RUIM" in est_raw or "MANUT" in est_raw:
                est_display = "⚠️ MANUTENÇÃO"
            elif "DESC" in est_raw or "SUCATA" in est_raw or "INSERV" in est_raw:
                est_display = "🗑️ DESCARTE"
            else:
                est_display = est_raw

            self.table.insert_row(
                m["id"],
                [
                    dt,
                    tipo_display,
                    m["epi_codigo"],
                    m["epi_nome"],
                    m["epi_ca"],
                    tam_str,
                    est_display,
                    f"{m['quantidade']} {m['epi_unidade']}",
                    func_str,
                    m["responsavel_entrega"],
                    m["motivo"],
                    m.get("observacao") or ""
                ],
                tag=tag
            )

        self.count_lbl.configure(text=f"{len(self.current_movements)} registros listados")

    def open_exit_modal(self, preselected_employee_id=None, preselected_epi_id=None, is_retroativo=False, on_success=None):
        """Abre janela modal para Registrar Saída de EPI, com suporte a inserção retroativa para Admin."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Registrar Saída / Entrega de EPI")
        dialog.geometry("680x720")
        dialog.resizable(False, False)
        dialog.grab_set()

        # Centraliza a janela
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 680) // 2
        y = (dialog.winfo_screenheight() - 720) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text="📦 Nova Entrega de EPI ao Colaborador", font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(pady=(16, 4))
        ctk.CTkLabel(dialog, text="Preencha os dados da entrega para atualizar o estoque e a ficha do funcionário", font=FONT_SMALL, text_color=TEXT_MUTED).pack(pady=(0, 10))

        form_frame = ctk.CTkScrollableFrame(dialog, fg_color="transparent", height=550)
        form_frame.pack(fill="both", expand=True, padx=25, pady=0)

        # 1. Selecionar Funcionário
        ctk.CTkLabel(form_frame, text="1. Selecione o Funcionário / Colaborador *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(5, 2))
        employees = EmployeeService.list_employees(status="Ativo")
        if not employees:
            messagebox.showwarning("Aviso", "Nenhum funcionário ativo cadastrado! Cadastre os funcionários primeiro.")
            dialog.destroy()
            return

        func_map = {f"{f['nome']} (Matrícula: {f['matricula']} - {f['cargo']})": f["id"] for f in employees}
        default_func = list(func_map.keys())[0]
        if preselected_employee_id:
            for k, fid in func_map.items():
                if fid == preselected_employee_id:
                    default_func = k
                    break

        func_var = tk.StringVar(value=default_func)
        func_combo = ctk.CTkComboBox(form_frame, values=list(func_map.keys()), variable=func_var, height=34)
        func_combo.pack(fill="x", pady=(0, 6))

        # Card informativo de medidas e tamanhos do colaborador selecionado (Compatível com Dark/Light)
        func_info_card = ctk.CTkFrame(form_frame, fg_color=BG_CARD, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
        func_info_card.pack(fill="x", pady=(0, 10))

        lbl_func_sizes = ctk.CTkLabel(func_info_card, text="", font=FONT_SMALL, text_color=TEXT_MAIN, justify="left")
        lbl_func_sizes.pack(anchor="w", padx=10, pady=6)

        def update_func_sizes(*args):
            fid = func_map.get(func_var.get())
            if not fid:
                return
            emp = EmployeeService.get_employee(fid)
            if emp:
                calc = emp.get("tamanho_calcado") or "-"
                luva = emp.get("tamanho_luva") or "-"
                uni = emp.get("tamanho_uniforme") or "-"
                masc = emp.get("tamanho_mascara") or "-"
                tel = emp.get("telefone") or "Não informado"
                lbl_func_sizes.configure(
                    text=f"📏 Medidas Cadastradas:  👟 Calçado: {calc}  |  🧤 Luva: {luva}  |  👕 Uniforme: {uni}  |  😷 Máscara: {masc}\n📱 WhatsApp: {tel}"
                )
        func_var.trace_add("write", update_func_sizes)
        update_func_sizes()

        # 2. Selecionar EPI
        ctk.CTkLabel(form_frame, text="2. Selecione o EPI a ser Entregue *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(5, 2))
        epis = EPIService.list_epis(show_inactive=False)
        if not epis:
            messagebox.showwarning("Aviso", "Nenhum EPI ativo cadastrado! Cadastre itens no estoque primeiro.")
            dialog.destroy()
            return

        epi_map = {}
        epi_stocks = {}
        epi_data = {e["id"]: e for e in epis}
        for e in epis:
            label = f"{e['codigo']} - {e['nome']} (C.A. {e['ca']}) [Saldo: {e['quantidade']} {e['unidade']}]"
            epi_map[label] = e["id"]
            epi_stocks[e["id"]] = e["quantidade"]

        default_epi = list(epi_map.keys())[0]
        if preselected_epi_id:
            for k, eid in epi_map.items():
                if eid == preselected_epi_id:
                    default_epi = k
                    break

        epi_var = tk.StringVar(value=default_epi)
        epi_combo = ctk.CTkComboBox(form_frame, values=list(epi_map.keys()), variable=epi_var, height=34)
        epi_combo.pack(fill="x", pady=(0, 8))

        # Linha Tamanho do EPI e Condição de Conservação (Novo / Usado)
        row_tam_cond = ctk.CTkFrame(form_frame, fg_color="transparent")
        row_tam_cond.pack(fill="x", pady=(0, 6))
        row_tam_cond.grid_columnconfigure((0, 1), weight=1)

        t_box = ctk.CTkFrame(row_tam_cond, fg_color="transparent")
        t_box.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(t_box, text="Tamanho do EPI a Entregar *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w")
        tam_var = tk.StringVar(value="Único")
        tam_combo = ctk.CTkComboBox(t_box, values=["Único"], variable=tam_var, height=34)
        tam_combo.pack(fill="x", pady=(2, 0))

        c_box = ctk.CTkFrame(row_tam_cond, fg_color="transparent")
        c_box.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(c_box, text="Condição do Equipamento *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w")
        cond_opts = [
            "🆕 NOVO (Item novo de fábrica)",
            "♻️ REUTILIZADO / HIGIENIZADO (Em perfeito estado)"
        ]
        cond_var = tk.StringVar(value=cond_opts[0])
        cond_combo = ctk.CTkComboBox(c_box, values=cond_opts, variable=cond_var, height=34)
        cond_combo.pack(fill="x", pady=(2, 0))

        # Label de Saldo Atual em destaque
        lbl_saldo = ctk.CTkLabel(form_frame, text="", font=FONT_BODY_BOLD, text_color="#2563EB")
        lbl_saldo.pack(anchor="w", pady=(2, 8))

        def on_epi_or_func_changed(*args):
            sel_label = epi_var.get()
            epi_id = epi_map.get(sel_label)
            if not epi_id:
                return

            grades = EPIService.get_available_sizes(epi_id)
            sizes = []
            for g in grades:
                t = str(g.get("tamanho", "")).strip()
                if t:
                    if "," in t:
                        sizes.extend([x.strip() for x in t.split(",") if x.strip()])
                    else:
                        sizes.append(t)

            epi_info = epi_data.get(epi_id) or {}
            epi_nome = (epi_info.get("nome") or sel_label or "").upper()

            # Preenche o valor unitário automaticamente com regra de novo (100%) ou usado/reutilizado (50%)
            try:
                p_base = float(epi_info.get("preco_unitario", 0.0) or 0.0)
                p_usado = float(epi_info.get("preco_usado", 0.0) or 0.0)
                if p_usado <= 0.0 and p_base > 0.0:
                    p_usado = round(p_base * 0.5, 2)
                c_val = cond_var.get().upper()
                if any(k in c_val for k in ["REUTIL", "USADO", "BOM", "HIGIEN"]):
                    p_calc = p_usado
                else:
                    p_calc = p_base
                valor_entry.delete(0, "end")
                valor_entry.insert(0, f"{p_calc:.2f}")
            except Exception:
                pass

            # Opções padrão complementares por categoria
            default_sizes = []
            if any(k in epi_nome for k in ["CAMISA", "CAMISETA", "UNIFORME", "CALÇA", "CALCA", "JALECO", "MOLETON", "VEST"]):
                default_sizes = ["P", "M", "G", "GG", "XG", "EXG"]
            elif any(k in epi_nome for k in ["BOTA", "BOTINA", "CALÇADO", "CALCADO", "SAPATO", "TÊNIS"]):
                default_sizes = ["35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46"]
            elif "LUVA" in epi_nome:
                default_sizes = ["P (07)", "M (08)", "G (09)", "XG (10)"]
            else:
                default_sizes = ["Único"]

            combined_sizes = list(dict.fromkeys(sizes + default_sizes))
            tam_combo.configure(values=combined_sizes)

            # Sugestão inteligente inicial apenas se o usuário ainda não escolheu um tamanho válido
            cur_tam = tam_var.get().strip()
            if not cur_tam or cur_tam == "Único" or cur_tam not in combined_sizes:
                fid = func_map.get(func_var.get())
                sugestao = None
                if fid:
                    emp = EmployeeService.get_employee(fid)
                    if emp:
                        c_calc = str(emp.get("tamanho_calcado") or "").strip()
                        c_luva = str(emp.get("tamanho_luva") or "").strip()
                        c_uni = str(emp.get("tamanho_uniforme") or "").strip()
                        if c_uni and c_uni not in ("-", "") and any(k in epi_nome for k in ["CAMISA", "UNIFORME", "CALÇA", "CALCA", "JALECO", "MOLETON"]):
                            sugestao = c_uni
                        elif c_calc and c_calc not in ("-", "") and any(k in epi_nome for k in ["BOTA", "BOTINA", "CALÇADO", "CALCADO"]):
                            sugestao = c_calc
                        elif c_luva and c_luva not in ("-", "") and "LUVA" in epi_nome:
                            sugestao = c_luva

                if sugestao and sugestao in combined_sizes:
                    tam_var.set(sugestao)
                elif combined_sizes:
                    tam_var.set(combined_sizes[0])

            update_saldo_display()

        def update_saldo_display(*args):
            sel_label = epi_var.get()
            epi_id = epi_map.get(sel_label)
            if not epi_id:
                return

            cur_tam = tam_var.get().strip()
            grades = EPIService.get_available_sizes(epi_id)
            g_match = next((g for g in grades if str(g.get("tamanho", "")).strip().upper() == cur_tam.upper()), None)
            if g_match:
                n_disp = g_match.get("novo", 0)
                u_disp = g_match.get("usado_bom", 0)
                tot_disp = g_match.get("total_disponivel", 0)
            else:
                saldo_tot = epi_stocks.get(epi_id, 0)
                n_disp = saldo_tot
                u_disp = 0
                tot_disp = saldo_tot

            if tot_disp == 0:
                lbl_saldo.configure(text=f"⚠️ Item ZERADO neste tamanho ({cur_tam})! Saldo: 0", text_color=DANGER)
            elif tot_disp <= 5:
                lbl_saldo.configure(
                    text=f"⚠️ Estoque baixo no Tam. {cur_tam}: {tot_disp} un disponíveis (🆕 {n_disp} Novos | ♻️ {u_disp} Reutilizados)",
                    text_color=WARNING
                )
            else:
                lbl_saldo.configure(
                    text=f"✅ Disponível no Tam. {cur_tam}: {tot_disp} un (🆕 {n_disp} Novos | ♻️ {u_disp} Reutilizados)",
                    text_color=SUCCESS
                )

            # Auto-seleciona reutilizado se novos estiver zerado
            if n_disp == 0 and u_disp > 0:
                cond_var.set(cond_opts[1])
            elif n_disp > 0 and cond_var.get() not in cond_opts:
                cond_var.set(cond_opts[0])

        epi_var.trace_add("write", on_epi_or_func_changed)
        func_var.trace_add("write", on_epi_or_func_changed)
        tam_var.trace_add("write", update_saldo_display)
        on_epi_or_func_changed()

        # Linha tripla: Quantidade, Valor Unitário e Motivo
        row1 = ctk.CTkFrame(form_frame, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 10))
        row1.grid_columnconfigure(0, weight=1)
        row1.grid_columnconfigure(1, weight=1)
        row1.grid_columnconfigure(2, weight=2)

        # Qtd
        q_box = ctk.CTkFrame(row1, fg_color="transparent")
        q_box.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(q_box, text="Quantidade *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w")
        qtd_entry = ctk.CTkEntry(q_box, height=34)
        qtd_entry.insert(0, "1")
        qtd_entry.pack(fill="x", pady=(2, 0))

        # Valor Unitário (R$)
        v_box = ctk.CTkFrame(row1, fg_color="transparent")
        v_box.grid(row=0, column=1, sticky="ew", padx=(6, 6))
        ctk.CTkLabel(v_box, text="Valor Unit. (R$):", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w")
        valor_entry = ctk.CTkEntry(v_box, height=34)
        valor_entry.insert(0, "0.00")
        valor_entry.pack(fill="x", pady=(2, 0))

        def _recalculate_unit_price(*args):
            sel_label = epi_var.get()
            epi_id = epi_map.get(sel_label)
            if not epi_id:
                return
            epi_info = epi_data.get(epi_id) or {}
            p_base = float(epi_info.get("preco_unitario", 0.0) or 0.0)
            p_usado = float(epi_info.get("preco_usado", 0.0) or 0.0)
            if p_usado <= 0.0 and p_base > 0.0:
                p_usado = round(p_base * 0.5, 2)
            c_val = cond_var.get().upper()
            if any(k in c_val for k in ["REUTIL", "USADO", "BOM", "HIGIEN"]):
                p_calc = p_usado
            else:
                p_calc = p_base
            try:
                valor_entry.delete(0, "end")
                valor_entry.insert(0, f"{p_calc:.2f}")
            except Exception:
                pass

        cond_var.trace_add("write", lambda *a: (_recalculate_unit_price(), update_saldo_display()))
        _recalculate_unit_price()

        # Motivo
        m_box = ctk.CTkFrame(row1, fg_color="transparent")
        m_box.grid(row=0, column=2, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(m_box, text="Motivo da Entrega *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w")
        motivos = ["Admissional (Novo Colaborador)", "Troca Periódica", "Desgaste / Danificado", "Perda / Extravio", "Mudança de Função", "Lançamento Histórico / Retroativo", "Outro"]
        motivo_var = tk.StringVar(value=motivos[5] if is_retroativo else motivos[0])
        motivo_combo = ctk.CTkComboBox(m_box, values=motivos, variable=motivo_var, height=34)
        motivo_combo.pack(fill="x", pady=(2, 0))

        # Campo de Bipe Rápido de Código de Barras
        barcode_row = ctk.CTkFrame(form_frame, fg_color="transparent")
        barcode_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(barcode_row, text="🏷️ Bipe Código de Barras / QR Code do EPI:", font=FONT_SMALL_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 6))
        barcode_entry = ctk.CTkEntry(barcode_row, placeholder_text="Aproxime o leitor USB ou digite o código...", height=28, width=240)
        barcode_entry.pack(side="left")

        def on_barcode_scan(event):
            scanned_code = barcode_entry.get().strip().upper()
            for label, e_id in epi_map.items():
                if scanned_code in label.upper():
                    epi_var.set(label)
                    barcode_entry.delete(0, "end")
                    break
        barcode_entry.bind("<Return>", on_barcode_scan)

        # 3. QUEM ENTREGOU / RESPONSÁVEL (Destaque exigido pelo usuário!)
        ctk.CTkLabel(form_frame, text="3. QUEM ENTREGOU / COLOCOU? (Responsável pela Entrega) *", font=FONT_BODY_BOLD, text_color="#1E3A8A").pack(anchor="w", pady=(5, 2))
        operators = MovementService.get_operators()
        if not operators:
            operators = ["Almoxarifado", "Técnico SST"]

        resp_var = tk.StringVar(value=operators[0])
        resp_combo = ctk.CTkComboBox(form_frame, values=operators, variable=resp_var, height=34)
        resp_combo.pack(fill="x", pady=(0, 10))

        # 4. Assinatura Digital & Foto do Recebedor (Anti-Fraude)
        sig_holder = {"path": None}
        foto_holder = {"path": None}
        sig_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        sig_frame.pack(fill="x", pady=(0, 8))

        lbl_sig = ctk.CTkLabel(sig_frame, text="Assinatura: Pendente", font=FONT_SMALL, text_color=TEXT_MUTED)
        lbl_sig.pack(side="left", padx=(0, 6))

        def open_sig():
            from ui.components.signature_pad import SignatureDialog
            func_name = func_var.get().split(" (")[0]
            def on_saved(path):
                sig_holder["path"] = path
                lbl_sig.configure(text="✅ Assinado!", text_color=SUCCESS)
            SignatureDialog(dialog, employee_name=func_name, on_signature_saved=on_saved)

        btn_sig = ctk.CTkButton(
            sig_frame,
            text="✍️ Assinatura na Tela",
            font=FONT_SMALL_BOLD,
            fg_color="#6366F1",
            hover_color="#4F46E5",
            height=28,
            command=open_sig
        )
        btn_sig.pack(side="left", padx=(0, 12))

        lbl_foto = ctk.CTkLabel(sig_frame, text="Foto: Não coletada", font=FONT_SMALL, text_color=TEXT_MUTED)
        lbl_foto.pack(side="left", padx=(0, 6))

        def open_webcam():
            from services.webcam_service import WebcamCaptureDialog
            func_name = func_var.get().split(" (")[0]
            def on_captured(path):
                foto_holder["path"] = path
                lbl_foto.configure(text="✅ Foto OK!", text_color=SUCCESS)
            WebcamCaptureDialog(dialog, employee_name=func_name, on_photo_captured=on_captured)

        btn_foto = ctk.CTkButton(
            sig_frame,
            text="📸 Tirar Foto (Webcam)",
            font=FONT_SMALL_BOLD,
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=28,
            command=open_webcam
        )
        btn_foto.pack(side="left")

        # 5. Painel de Inserção Retroativa (Habilitado para ADMIN)
        retro_active_var = tk.BooleanVar(value=bool(is_retroativo))
        retro_stock_var = tk.BooleanVar(value=False)
        retro_date_entry = None

        if AuthService.is_admin():
            retro_card = ctk.CTkFrame(form_frame, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color="#3B82F6")
            retro_card.pack(fill="x", pady=(4, 10))

            retro_sub = ctk.CTkFrame(retro_card, fg_color="transparent")

            def toggle_retro():
                if retro_active_var.get():
                    retro_sub.pack(fill="x", padx=12, pady=(0, 10))
                else:
                    retro_sub.pack_forget()

            chk_retro = ctk.CTkCheckBox(
                retro_card,
                text="🛡️ Habilitar Lançamento Retroativo (Histórico Passado - Modo ADMIN)",
                variable=retro_active_var,
                font=FONT_BODY_BOLD,
                text_color="#2563EB",
                command=toggle_retro
            )
            chk_retro.pack(anchor="w", padx=12, pady=10)

            ctk.CTkLabel(retro_sub, text="Data Específica da Entrega (DD/MM/AAAA): *", font=FONT_SMALL_BOLD, text_color=TEXT_MAIN).pack(anchor="w")
            row_retro_dt = ctk.CTkFrame(retro_sub, fg_color="transparent")
            row_retro_dt.pack(fill="x", pady=(2, 6))
            retro_date_entry = ctk.CTkEntry(row_retro_dt, placeholder_text="DD/MM/AAAA", height=32)
            retro_date_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
            from ui.components.date_picker import open_date_picker
            retro_date_entry.bind("<Double-Button-1>", lambda e: open_date_picker(dialog, target_entry=retro_date_entry))
            btn_retro_cal = ctk.CTkButton(
                row_retro_dt,
                text="📅",
                width=38,
                height=32,
                fg_color="#3B82F6",
                hover_color="#1D4ED8",
                command=lambda: open_date_picker(dialog, target_entry=retro_date_entry)
            )
            btn_retro_cal.pack(side="right")

            chk_stock = ctk.CTkCheckBox(
                retro_sub,
                text="Debitar do saldo físico atual do estoque (Desmarcado = Apenas histórico na ficha)",
                variable=retro_stock_var,
                font=FONT_SMALL
            )
            chk_stock.pack(anchor="w", pady=(2, 4))

            ctk.CTkLabel(
                retro_sub,
                text="ℹ️ Dica: Como a entrega ocorreu no passado, manter desmarcado evita abater seu estoque físico de hoje.",
                font=FONT_SMALL,
                text_color=TEXT_MUTED
            ).pack(anchor="w")

            if is_retroativo:
                retro_sub.pack(fill="x", padx=12, pady=(0, 10))

        # 6. Observações
        ctk.CTkLabel(form_frame, text="Observações adicionais (opcional):", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w")
        obs_entry = ctk.CTkEntry(form_frame, placeholder_text="Ex: Substituição da luva rasgada em operação...", height=34)
        obs_entry.pack(fill="x", pady=(2, 15))

        # Botões de confirmação
        btn_action_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_action_frame.pack(fill="x", padx=30, pady=(10, 16))

        btn_cancel = ctk.CTkButton(
            btn_action_frame,
            text="Cancelar",
            fg_color="#94A3B8",
            hover_color="#64748B",
            width=120,
            height=38,
            command=dialog.destroy
        )
        btn_cancel.pack(side="left")

        def submit():
            try:
                func_id = func_map[func_var.get()]
                epi_id = epi_map[epi_var.get()]
                qtd_str = qtd_entry.get().strip()

                if not qtd_str.isdigit() or int(qtd_str) <= 0:
                    messagebox.showerror("Erro de Validação", "Informe uma quantidade válida maior que zero!")
                    return

                qtd = int(qtd_str)
                responsavel = resp_var.get().strip()
                if not responsavel:
                    messagebox.showerror("Erro de Validação", "O nome de quem entregou é obrigatório!")
                    return

                # Custo Unitário informado pelo usuário
                raw_valor = valor_entry.get().strip().replace(",", ".")
                try:
                    custo_unit_val = float(raw_valor) if raw_valor else None
                except ValueError:
                    custo_unit_val = None

                motivo = motivo_var.get().strip()
                obs = obs_entry.get().strip()
                tamanho_escolhido = tam_var.get().strip() or "Único"
                cond_raw = cond_var.get()
                cond_escolhida = "NOVO" if "NOVO" in cond_raw else "BOM / REUTILIZÁVEL"

                is_retro = AuthService.is_admin() and retro_active_var.get()
                if is_retro:
                    dt_str = retro_date_entry.get().strip() if retro_date_entry else ""
                    if not dt_str:
                        messagebox.showerror("Erro de Validação", "Informe a data específica da entrega retroativa!")
                        return

                    MovementService.register_exit(
                        epi_id=epi_id,
                        funcionario_id=func_id,
                        quantidade=qtd,
                        responsavel_entrega=responsavel,
                        motivo=motivo,
                        observacao=obs,
                        data_hora=dt_str,
                        assinatura_path=sig_holder["path"],
                        foto_path=foto_holder["path"],
                        is_retroativo=True,
                        descontar_estoque=retro_stock_var.get(),
                        tamanho=tamanho_escolhido,
                        estado_conservacao=cond_escolhida,
                        custo_unitario=custo_unit_val
                    )

                    messagebox.showinfo(
                        "Lançamento Retroativo Concluído!",
                        f"Entrega retroativa de {qtd} unidade(s) ({cond_escolhida}, Tam: {tamanho_escolhido}) registrada com sucesso na data {dt_str}!\n"
                        f"A Ficha NR-6 do colaborador foi atualizada com o registro histórico."
                    )
                else:
                    MovementService.register_exit(
                        epi_id=epi_id,
                        funcionario_id=func_id,
                        quantidade=qtd,
                        responsavel_entrega=responsavel,
                        motivo=motivo,
                        observacao=obs,
                        assinatura_path=sig_holder["path"],
                        foto_path=foto_holder["path"],
                        is_retroativo=False,
                        descontar_estoque=True,
                        tamanho=tamanho_escolhido,
                        estado_conservacao=cond_escolhida,
                        custo_unitario=custo_unit_val
                    )

                    messagebox.showinfo(
                        "Sucesso!",
                        f"Saída de {qtd} unidade(s) ({cond_escolhida}, Tam: {tamanho_escolhido}) registrada com sucesso!\n"
                        f"O estoque foi atualizado e a entrega gravada na ficha do trabalhador."
                    )

                # Sugere envio de comprovante via WhatsApp se houver telefone
                try:
                    from services.whatsapp_service import WhatsAppService
                    emp_obj = EmployeeService.get_employee(func_id)
                    if emp_obj and emp_obj.get("telefone"):
                        ans_zap = messagebox.askyesno(
                            "Comprovante por WhatsApp",
                            f"Deseja enviar o comprovante de entrega para o WhatsApp do colaborador ({emp_obj['telefone']})?"
                        )
                        if ans_zap:
                            epi_full = epi_var.get()
                            epi_nome_clean = epi_full.split(" (C.A.")[0]
                            epi_ca_clean = epi_full.split("C.A. ")[1].split(")")[0] if "C.A. " in epi_full else ""
                            zap_url = WhatsAppService.build_delivery_url(
                                employee=emp_obj,
                                epi_name=epi_nome_clean,
                                ca_num=epi_ca_clean,
                                qtd=qtd,
                                responsavel=responsavel,
                                dt_entrega=dt_str if is_retro else None
                            )
                            WhatsAppService.send_via_whatsapp(zap_url)
                except Exception:
                    pass

                dialog.destroy()
                if hasattr(self, 'refresh') and callable(self.refresh):
                    try:
                        self.refresh()
                    except Exception:
                        pass
                if hasattr(self, 'on_refresh_dashboard') and self.on_refresh_dashboard:
                    try:
                        self.on_refresh_dashboard()
                    except Exception:
                        pass
                if on_success and callable(on_success):
                    try:
                        on_success()
                    except Exception:
                        pass

            except ValueError as ve:
                messagebox.showerror("Aviso de Validação / Saldo", str(ve))
            except Exception as ex:
                messagebox.showerror("Erro", f"Falha ao registrar saída: {str(ex)}")

        btn_confirm = ctk.CTkButton(
            btn_action_frame,
            text="✔️ Confirmar Entrega & Gravar",
            font=FONT_BODY_BOLD,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=38,
            command=submit
        )
        btn_confirm.pack(side="right")

    def open_entry_modal(self, preselected_epi_id=None):
        """Abre modal completo para Entrada / Reposição de Estoque (Compra / NF / Saldo)."""
        open_stock_entry_dialog(self, preselected_epi_id=preselected_epi_id, on_success=self._on_change_success)

    def _export_excel(self):
        try:
            if not self.current_movements:
                messagebox.showwarning("Aviso", "Não há dados para exportar com os filtros atuais.")
                return

            filepath = ExcelService.export_movements(self.current_movements)
            ans = messagebox.askyesno("Exportação Concluída", f"Planilha Excel gerada com sucesso em:\n{filepath}\n\nDeseja abrir o arquivo agora?")
            if ans:
                os.startfile(filepath)
        except Exception as e:
            messagebox.showerror("Erro ao Exportar", str(e))

    def _export_pdf(self):
        try:
            if not self.current_movements:
                messagebox.showwarning("Aviso", "Não há dados para exportar com os filtros atuais.")
                return

            filtro_desc = f"Tipo: {self.tipo_var.get()}"
            if self.dt_ini_var.get():
                filtro_desc += f" | De: {self.dt_ini_var.get()}"
            if self.dt_fim_var.get():
                filtro_desc += f" | Até: {self.dt_fim_var.get()}"

            filepath = PDFService.generate_movements_report_pdf(self.current_movements, filters_desc=filtro_desc)
            ans = messagebox.askyesno("Relatório Gerado", f"Relatório PDF gerado com sucesso em:\n{filepath}\n\nDeseja abrir o PDF agora para imprimir ou visualizar?")
            if ans:
                os.startfile(filepath)
        except Exception as e:
            messagebox.showerror("Erro ao Gerar PDF", str(e))

    # =========================================================================
    # EDIÇÃO E EXCLUSÃO DE LANÇAMENTOS (EXCLUSIVO PARA ADMIN)
    # =========================================================================
    def _edit_selected_movement(self):
        selected_id = self.table.get_selected()
        if not selected_id:
            messagebox.showwarning("Aviso", "Selecione uma linha na tabela para editar o lançamento.")
            return
        open_edit_movement_dialog(self, selected_id, on_success=self._on_change_success)

    def _edit_movement_by_id(self, movement_id):
        open_edit_movement_dialog(self, movement_id, on_success=self._on_change_success)

    def _delete_selected_movement(self, preselected_id=None):
        movement_id = preselected_id or self.table.get_selected()
        confirm_and_delete_movement_dialog(self, movement_id, on_success=self._on_change_success)

    def _on_change_success(self):
        self.refresh()
        if self.on_refresh_dashboard:
            self.on_refresh_dashboard()

    def open_edit_movement_modal(self, movement_id, on_success=None):
        def _cb():
            self._on_change_success()
            if on_success:
                on_success()
        open_edit_movement_dialog(self, movement_id, on_success=_cb)


# =============================================================================
# JANELAS MODAIS E DIÁLOGOS DE EDIÇÃO / EXCLUSÃO (REUTILIZÁVEIS)
# =============================================================================
def confirm_and_delete_movement_dialog(parent, movement_id, on_success=None):
    """Exibe confirmação e exclui o lançamento estornando o estoque correspondente."""
    if not AuthService.is_admin():
        messagebox.showwarning("Acesso Negado", "Apenas Administradores têm permissão para excluir lançamentos.")
        return

    if not movement_id:
        messagebox.showwarning("Aviso", "Selecione uma linha na tabela para excluir o lançamento.")
        return

    mov = MovementService.get_movement(movement_id)
    if not mov:
        messagebox.showerror("Erro", "Lançamento de movimentação não encontrado.")
        return

    tipo = mov["tipo"]
    epi_nome = mov["epi_nome"]
    qtd = mov["quantidade"]
    tam = mov.get("mov_tamanho") or "Único"
    est = (mov.get("mov_estado") or "NOVO").upper()
    func_nome = mov.get("func_nome") or "Almoxarifado"

    msg = (
        f"Atenção: Você está prestes a EXCLUIR este lançamento do sistema!\n\n"
        f"• Lançamento nº: {movement_id}\n"
        f"• Tipo: {tipo}\n"
        f"• Equipamento: {epi_nome}\n"
        f"• Quantidade: {qtd}\n"
        f"• Tamanho / Condição: {tam} ({est})\n"
        f"• Colaborador / Destino: {func_nome}\n"
        f"• Data do Registro: {mov['data_hora']}\n\n"
        f"⚠️ O saldo de {qtd} unidade(s) será ESTORNADO de volta para o estoque.\n\n"
        f"Deseja realmente confirmar a exclusão definitiva?"
    )
    if not messagebox.askyesno("Confirmar Exclusão (Admin)", msg):
        return

    try:
        MovementService.delete_movement(movement_id, estornar_estoque=True)
        messagebox.showinfo("Sucesso", f"Lançamento nº {movement_id} excluído com sucesso e o saldo foi estornado ao estoque.")
        if on_success:
            on_success()
    except Exception as e:
        messagebox.showerror("Erro ao Excluir", str(e))


def open_edit_movement_dialog(parent, movement_id, on_success=None):
    """Abre janela modal para o Admin editar os dados de um lançamento com recálculo de estoque."""
    if not AuthService.is_admin():
        messagebox.showwarning("Acesso Negado", "Apenas Administradores podem editar lançamentos de movimentação.")
        return

    mov = MovementService.get_movement(movement_id)
    if not mov:
        messagebox.showerror("Erro", f"Lançamento ID {movement_id} não encontrado.")
        return

    dialog = ctk.CTkToplevel(parent)
    dialog.title(f"✏️ Editar Lançamento nº {movement_id} ({mov['tipo']}) - Admin")

    sw = dialog.winfo_screenwidth()
    sh = dialog.winfo_screenheight()
    dlg_w = min(720, max(580, sw - 80))
    dlg_h = min(780, max(520, sh - 90))
    dialog.geometry(f"{dlg_w}x{dlg_h}")
    x = (sw - dlg_w) // 2
    y = max(20, (sh - dlg_h) // 2)
    dialog.geometry(f"+{x}+{y}")
    dialog.grab_set()

    ctk.CTkLabel(dialog, text=f"✏️ Editar Lançamento nº {movement_id} ({mov['tipo']})", font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(pady=(14, 2))
    ctk.CTkLabel(dialog, text="Qualquer alteração na quantidade, EPI ou tamanho recalcula o estoque automaticamente.", font=FONT_SMALL, text_color=TEXT_MUTED).pack(pady=(0, 8))

    form_frame = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
    form_frame.pack(fill="both", expand=True, padx=25, pady=(0, 10))

    # 1. Funcionário Destino
    employees = EmployeeService.list_employees(status="all", show_inactive=True)
    func_map = {}
    func_inv_map = {}
    if mov.get("tipo") != "SAIDA":
        func_map["[NENHUM / ESTOQUE INTERNO]"] = None
        func_inv_map[None] = "[NENHUM / ESTOQUE INTERNO]"

    for f in employees:
        lbl = f"{f['nome']} (Matrícula: {f.get('matricula', '-')} - {f.get('cargo', '-')})"
        func_map[lbl] = f["id"]
        func_inv_map[f["id"]] = lbl

    # Garante que o funcionário atual do lançamento esteja presente mesmo se for antigo
    if mov.get("func_id") and mov["func_id"] not in func_inv_map:
        lbl = f"{mov.get('func_nome', 'Colaborador')} (Matrícula: {mov.get('func_matricula', '-')} - {mov.get('func_cargo', '-')})"
        func_map[lbl] = mov["func_id"]
        func_inv_map[mov["func_id"]] = lbl

    cur_func_key = func_inv_map.get(mov.get("func_id"), list(func_map.keys())[0] if func_map else "")
    ctk.CTkLabel(form_frame, text="Funcionário Destino / Colaborador:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(4, 2))
    func_var = tk.StringVar(value=cur_func_key)
    func_combo = ctk.CTkComboBox(form_frame, values=list(func_map.keys()), variable=func_var, height=32)
    func_combo.pack(fill="x", pady=(0, 10))

    # 2. EPI
    epis = EPIService.list_epis(show_inactive=True)
    epi_map = {}
    epi_inv_map = {}
    for e in epis:
        label = f"{e['codigo']} - {e['nome']} (C.A. {e['ca']}) [Saldo: {e['quantidade']}]"
        epi_map[label] = e["id"]
        epi_inv_map[e["id"]] = label

    # Garante que o EPI atual esteja presente
    if mov.get("epi_id") and mov["epi_id"] not in epi_inv_map:
        label = f"{mov.get('epi_codigo', '-')} - {mov.get('epi_nome', 'EPI')} (C.A. {mov.get('epi_ca', '-')})"
        epi_map[label] = mov["epi_id"]
        epi_inv_map[mov["epi_id"]] = label

    cur_epi_key = epi_inv_map.get(mov["epi_id"], list(epi_map.keys())[0] if epi_map else "")
    ctk.CTkLabel(form_frame, text="Equipamento (EPI) *:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(4, 2))
    epi_var = tk.StringVar(value=cur_epi_key)
    epi_combo = ctk.CTkComboBox(form_frame, values=list(epi_map.keys()), variable=epi_var, height=32)
    epi_combo.pack(fill="x", pady=(0, 10))

    # Linha: Tamanho & Condição
    row_tam_cond = ctk.CTkFrame(form_frame, fg_color="transparent")
    row_tam_cond.pack(fill="x", pady=(0, 10))
    row_tam_cond.grid_columnconfigure((0, 1), weight=1)

    # Tamanho
    f_tam = ctk.CTkFrame(row_tam_cond, fg_color="transparent")
    f_tam.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    ctk.CTkLabel(f_tam, text="Tamanho / Grade:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))
    tam_opts = ["Único", "P", "M", "G", "GG", "XG", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45"]
    cur_tam = (mov.get("mov_tamanho") or mov.get("tamanho") or "Único").strip()
    if cur_tam and cur_tam not in tam_opts:
        tam_opts.insert(0, cur_tam)
    tam_var = tk.StringVar(value=cur_tam)
    tam_combo = ctk.CTkComboBox(f_tam, values=tam_opts, variable=tam_var, height=32)
    tam_combo.pack(fill="x")

    # Condição
    f_cond = ctk.CTkFrame(row_tam_cond, fg_color="transparent")
    f_cond.grid(row=0, column=1, sticky="ew", padx=(6, 0))
    ctk.CTkLabel(f_cond, text="Condição do Material:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))
    cond_opts = ["NOVO", "REUTILIZADO (HIGIENIZADO)", "MANUTENÇÃO", "DESCARTE"]
    cur_cond = (mov.get("mov_estado") or mov.get("estado_conservacao") or "NOVO").strip().upper()
    match_found = False
    for opt in cond_opts:
        if cur_cond in opt or opt in cur_cond:
            cur_cond = opt
            match_found = True
            break
    if not match_found and cur_cond:
        cond_opts.insert(0, cur_cond)
    cond_var = tk.StringVar(value=cur_cond)
    cond_combo = ctk.CTkComboBox(f_cond, values=cond_opts, variable=cond_var, height=32)
    cond_combo.pack(fill="x")

    def update_epi_sizes(*args):
        sel = epi_var.get()
        eid = epi_map.get(sel)
        if eid:
            grades = EPIService.get_epi_grades(eid)
            if grades:
                avail_tams = list(dict.fromkeys([g["tamanho"] for g in grades if g.get("tamanho")]))
                if avail_tams:
                    tam_combo.configure(values=avail_tams)
            epi_obj = EPIService.get_epi(eid)
            if epi_obj and epi_obj.get("preco_unitario"):
                try:
                    cur_typed = float(val_entry.get().strip().replace("R$", "").replace(",", "."))
                    if cur_typed == 0.0:
                        p_base = float(epi_obj['preco_unitario'])
                        p_usado = float(epi_obj.get('preco_usado', 0.0) or 0.0)
                        if p_usado <= 0.0 and p_base > 0.0:
                            p_usado = round(p_base * 0.5, 2)
                        c_val = cond_var.get().upper()
                        p_calc = p_usado if any(k in c_val for k in ["REUTIL", "USADO", "BOM", "HIGIEN"]) else p_base
                        val_entry.delete(0, "end")
                        val_entry.insert(0, f"{p_calc:.2f}")
                except Exception:
                    pass

    def on_edit_condition_change(*args):
        sel = epi_var.get()
        eid = epi_map.get(sel)
        if eid:
            epi_obj = EPIService.get_epi(eid)
            if epi_obj and epi_obj.get("preco_unitario"):
                p_base = float(epi_obj['preco_unitario'])
                p_usado = float(epi_obj.get('preco_usado', 0.0) or 0.0)
                if p_usado <= 0.0 and p_base > 0.0:
                    p_usado = round(p_base * 0.5, 2)
                c_val = cond_var.get().upper()
                p_calc = p_usado if any(k in c_val for k in ["REUTIL", "USADO", "BOM", "HIGIEN"]) else p_base
                val_entry.delete(0, "end")
                val_entry.insert(0, f"{p_calc:.2f}")

    epi_var.trace_add("write", update_epi_sizes)
    cond_var.trace_add("write", on_edit_condition_change)

    # Linha: Quantidade & Valor Unitário (R$)
    row_qtd_val = ctk.CTkFrame(form_frame, fg_color="transparent")
    row_qtd_val.pack(fill="x", pady=(0, 10))
    row_qtd_val.grid_columnconfigure((0, 1), weight=1)

    # Quantidade
    f_qtd = ctk.CTkFrame(row_qtd_val, fg_color="transparent")
    f_qtd.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    ctk.CTkLabel(f_qtd, text="Quantidade *:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))
    qtd_entry = ctk.CTkEntry(f_qtd, height=32)
    qtd_entry.insert(0, str(mov["quantidade"]))
    qtd_entry.pack(fill="x")

    # Valor Unitário (R$)
    f_val = ctk.CTkFrame(row_qtd_val, fg_color="transparent")
    f_val.grid(row=0, column=1, sticky="ew", padx=(6, 0))
    ctk.CTkLabel(f_val, text="Valor Unitário (R$):", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))
    val_entry = ctk.CTkEntry(f_val, height=32, placeholder_text="0.00")
    cur_val = mov.get("custo_unitario")
    if cur_val is None or float(cur_val or 0.0) == 0.0:
        cur_val = mov.get("epi_preco", 0.0)
    val_entry.insert(0, f"{float(cur_val or 0.0):.2f}")
    val_entry.pack(fill="x")

    # Data / Hora
    ctk.CTkLabel(form_frame, text="Data do Lançamento (DD/MM/AAAA): *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(4, 2))
    row_edit_dt = ctk.CTkFrame(form_frame, fg_color="transparent")
    row_edit_dt.pack(fill="x", pady=(0, 10))
    dt_entry = ctk.CTkEntry(row_edit_dt, placeholder_text="DD/MM/AAAA", height=32)
    dt_raw = mov.get("data_hora", "")
    try:
        dt_display = datetime.strptime(dt_raw[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        dt_display = dt_raw[:10]
    dt_entry.insert(0, dt_display)
    dt_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
    from ui.components.date_picker import open_date_picker
    dt_entry.bind("<Double-Button-1>", lambda e: open_date_picker(dialog, target_entry=dt_entry))
    btn_edit_cal = ctk.CTkButton(
        row_edit_dt,
        text="📅",
        width=38,
        height=32,
        fg_color="#3B82F6",
        hover_color="#1D4ED8",
        command=lambda: open_date_picker(dialog, target_entry=dt_entry)
    )
    btn_edit_cal.pack(side="right")

    # Quem Entregou / Responsável
    ctk.CTkLabel(form_frame, text="Quem Entregou / Responsável *:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(4, 2))
    resp_entry = ctk.CTkEntry(form_frame, height=32)
    resp_entry.insert(0, mov.get("responsavel_entrega") or "Almoxarifado")
    resp_entry.pack(fill="x", pady=(0, 10))

    # Motivo
    ctk.CTkLabel(form_frame, text="Motivo do Lançamento *:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(4, 2))
    motivo_var = tk.StringVar(value=mov.get("motivo") or "Entrega Regular de EPI")
    motivos_padrao = [
        "Entrega Regular de EPI", "Substituição por Desgaste Natural",
        "Danificado / Rasgado em Serviço", "Perda / Extravio pelo Funcionário",
        "Kit Admissional Obrigatório", "Troca Periódica (Vida Útil)",
        "Ajuste de Estoque / Correção Admin"
    ]
    if motivo_var.get() not in motivos_padrao:
        motivos_padrao.insert(0, motivo_var.get())
    motivo_combo = ctk.CTkComboBox(form_frame, values=motivos_padrao, variable=motivo_var, height=32)
    motivo_combo.pack(fill="x", pady=(0, 10))

    # Observações
    ctk.CTkLabel(form_frame, text="Observações / Justificativa da Alteração:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(4, 2))
    obs_entry = ctk.CTkEntry(form_frame, placeholder_text="Ex: Corrigido tamanho ou funcionário lançado incorretamente...", height=32)
    obs_entry.insert(0, mov.get("observacao") or "")
    obs_entry.pack(fill="x", pady=(0, 14))

    # Botões inferiores
    btn_bar = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_bar.pack(fill="x", padx=25, pady=(0, 16))

    def _do_delete_from_modal():
        dialog.destroy()
        confirm_and_delete_movement_dialog(parent, movement_id, on_success=on_success)

    btn_excluir = ctk.CTkButton(
        btn_bar,
        text="🗑️ Excluir Lançamento",
        font=FONT_BODY_BOLD,
        fg_color="#DC2626",
        hover_color="#B91C1C",
        height=36,
        command=_do_delete_from_modal
    )
    btn_excluir.pack(side="left")

    btn_cancelar = ctk.CTkButton(
        btn_bar,
        text="Cancelar",
        font=FONT_BODY,
        fg_color="#64748B",
        hover_color="#475569",
        height=36,
        command=dialog.destroy
    )
    btn_cancelar.pack(side="right", padx=(8, 0))

    def _do_save():
        try:
            epi_id_sel = epi_map.get(epi_var.get())
            if not epi_id_sel:
                messagebox.showerror("Erro", "Selecione um EPI válido.")
                return

            func_id_sel = func_map.get(func_var.get())
            qtd_str = qtd_entry.get().strip()
            if not qtd_str.isdigit():
                messagebox.showerror("Erro", "A quantidade deve ser um número inteiro válido.")
                return
            qtd_val = int(qtd_str)
            if qtd_val <= 0:
                messagebox.showerror("Erro", "A quantidade deve ser maior que zero.")
                return

            val_str = val_entry.get().strip().replace("R$", "").replace(" ", "").replace(",", ".")
            try:
                val_unit_val = float(val_str) if val_str else 0.0
                if val_unit_val < 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Erro", "Valor Unitário inválido. Digite um valor numérico válido (ex: 35.50 ou 0.00).")
                return

            data_update = {
                "epi_id": epi_id_sel,
                "funcionario_id": func_id_sel,
                "quantidade": qtd_val,
                "custo_unitario": val_unit_val,
                "tamanho": tam_var.get().strip() or "Único",
                "estado_conservacao": cond_var.get().strip(),
                "data_hora": dt_entry.get().strip(),
                "responsavel_entrega": resp_entry.get().strip() or "Almoxarifado",
                "motivo": motivo_var.get().strip(),
                "observacao": obs_entry.get().strip()
            }

            MovementService.update_movement(movement_id, data_update)
            messagebox.showinfo("Sucesso", f"Lançamento nº {movement_id} atualizado com sucesso!")
            dialog.destroy()
            if on_success:
                on_success()
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", str(e))

    btn_salvar = ctk.CTkButton(
        btn_bar,
        text="💾 Salvar Alterações",
        font=FONT_BODY_BOLD,
        fg_color="#1E3A8A",
        hover_color="#1D4ED8",
        height=36,
        command=_do_save
    )
    btn_salvar.pack(side="right")


def open_stock_entry_dialog(parent, preselected_epi_id=None, on_success=None):
    """
    Abre modal interativo para registrar Entrada de Estoque (Compra / Reposição de Fornecedor / NF / Saldo).
    Reutilizável em qualquer parte do sistema (Estoque, Movimentações, Dashboard).
    """
    dialog = ctk.CTkToplevel(parent)
    dialog.title("📥 Registrar Entrada de Estoque / Compra de EPI")

    sw = dialog.winfo_screenwidth()
    sh = dialog.winfo_screenheight()
    dlg_w = min(680, max(580, sw - 80))
    dlg_h = min(770, max(540, sh - 90))
    dialog.geometry(f"{dlg_w}x{dlg_h}")
    x = (sw - dlg_w) // 2
    y = max(20, (sh - dlg_h) // 2)
    dialog.geometry(f"+{x}+{y}")
    dialog.grab_set()

    ctk.CTkLabel(dialog, text="📥 Registrar Entrada de Estoque (Compra / Reposição)", font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(pady=(16, 2))
    ctk.CTkLabel(dialog, text="Dê entrada em produtos comprados, notas fiscais ou estoque anterior sem precisar editar o item.", font=FONT_SMALL, text_color=TEXT_MUTED).pack(pady=(0, 10))

    form_frame = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
    form_frame.pack(fill="both", expand=True, padx=25, pady=(0, 10))

    epis = EPIService.list_epis(show_inactive=False)
    if not epis:
        messagebox.showwarning("Aviso", "Nenhum EPI ativo cadastrado! Cadastre o EPI primeiro no estoque.")
        dialog.destroy()
        return

    epi_map = {f"{e['codigo']} - {e['nome']} (C.A. {e['ca']}) [Saldo: {e['quantidade']} {e['unidade']}]": e["id"] for e in epis}
    epi_data_map = {e["id"]: e for e in epis}

    default_epi_key = list(epi_map.keys())[0]
    if preselected_epi_id:
        for k, eid in epi_map.items():
            if eid == preselected_epi_id:
                default_epi_key = k
                break

    # 1. Seleção do EPI
    ctk.CTkLabel(form_frame, text="1. Equipamento (EPI) a Receber: *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(4, 2))
    epi_var = tk.StringVar(value=default_epi_key)
    epi_combo = ctk.CTkComboBox(form_frame, values=list(epi_map.keys()), variable=epi_var, height=34)
    epi_combo.pack(fill="x", pady=(0, 6))

    # Card informativo do EPI selecionado
    info_card = ctk.CTkFrame(form_frame, fg_color=BG_CARD, corner_radius=6, border_width=1, border_color=BORDER_COLOR)
    info_card.pack(fill="x", pady=(0, 10))
    lbl_info_epi = ctk.CTkLabel(info_card, text="", font=FONT_SMALL, text_color=TEXT_MAIN, justify="left")
    lbl_info_epi.pack(anchor="w", padx=10, pady=6)

    # Linha: Tamanho / Grade e Condição do Material
    row_tam_cond = ctk.CTkFrame(form_frame, fg_color="transparent")
    row_tam_cond.pack(fill="x", pady=(0, 10))
    row_tam_cond.grid_columnconfigure((0, 1), weight=1)

    # Tamanho
    f_tam = ctk.CTkFrame(row_tam_cond, fg_color="transparent")
    f_tam.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    ctk.CTkLabel(f_tam, text="2. Tamanho / Numeração: *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))
    tam_var = tk.StringVar(value="Único")
    tam_combo = ctk.CTkComboBox(f_tam, values=["Único"], variable=tam_var, height=34)
    tam_combo.pack(fill="x")

    # Condição
    f_cond = ctk.CTkFrame(row_tam_cond, fg_color="transparent")
    f_cond.grid(row=0, column=1, sticky="ew", padx=(6, 0))
    ctk.CTkLabel(f_cond, text="3. Condição do Material: *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))
    cond_opts = [
        "🆕 NOVO (Compra de Fornecedor / Fabricante)",
        "♻️ BOM / REUTILIZÁVEL (Higienizado / Devolução)",
        "⚠️ RUIM / MANUTENÇÃO (Quarentena / Reparo)",
        "🗑️ DESCARTE / SUCATA"
    ]
    cond_var = tk.StringVar(value=cond_opts[0])
    cond_combo = ctk.CTkComboBox(f_cond, values=cond_opts, variable=cond_var, height=34)
    cond_combo.pack(fill="x")

    # Linha: Quantidade e Preço Unitário de Compra
    row_qtd_preco = ctk.CTkFrame(form_frame, fg_color="transparent")
    row_qtd_preco.pack(fill="x", pady=(0, 6))
    row_qtd_preco.grid_columnconfigure((0, 1), weight=1)

    # Quantidade
    f_qtd = ctk.CTkFrame(row_qtd_preco, fg_color="transparent")
    f_qtd.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    ctk.CTkLabel(f_qtd, text="4. Quantidade Recebida (Unidades): *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))
    qtd_entry = ctk.CTkEntry(f_qtd, placeholder_text="Ex: 50", height=34)
    qtd_entry.insert(0, "10")
    qtd_entry.pack(fill="x")

    # Preço Unitário
    f_preco = ctk.CTkFrame(row_qtd_preco, fg_color="transparent")
    f_preco.grid(row=0, column=1, sticky="ew", padx=(6, 0))
    ctk.CTkLabel(f_preco, text="5. Custo Unitário de Compra (R$):", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))
    preco_entry = ctk.CTkEntry(f_preco, placeholder_text="Ex: 25.50", height=34)
    preco_entry.pack(fill="x")

    # Checkbox para atualizar preço padrão no cadastro do EPI
    chk_atualizar_preco_var = tk.BooleanVar(value=True)
    chk_preco = ctk.CTkCheckBox(form_frame, text="Atualizar este valor como preço de custo padrão no cadastro do EPI", variable=chk_atualizar_preco_var, font=FONT_SMALL)
    chk_preco.pack(anchor="w", pady=(0, 10))

    # Linha: Nota Fiscal / Fornecedor e Motivo
    row_nf_mot = ctk.CTkFrame(form_frame, fg_color="transparent")
    row_nf_mot.pack(fill="x", pady=(0, 10))
    row_nf_mot.grid_columnconfigure((0, 1), weight=1)

    # Nota Fiscal / Fornecedor
    f_nf = ctk.CTkFrame(row_nf_mot, fg_color="transparent")
    f_nf.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    ctk.CTkLabel(f_nf, text="6. Nota Fiscal (NF) & Fornecedor:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))
    nf_entry = ctk.CTkEntry(f_nf, placeholder_text="Ex: NF 15840 - Distribuidora Silva", height=34)
    nf_entry.pack(fill="x")

    # Motivo
    f_mot = ctk.CTkFrame(row_nf_mot, fg_color="transparent")
    f_mot.grid(row=0, column=1, sticky="ew", padx=(6, 0))
    ctk.CTkLabel(f_mot, text="7. Motivo da Entrada: *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))
    motivo_opts = [
        "Compra / Reposição de Estoque",
        "Saldo Inicial / Estoque Anterior",
        "Doação / Transferência entre Unidades",
        "Ajuste de Inventário / Sobra de Estoque",
        "Devolução de Terceiros"
    ]
    motivo_var = tk.StringVar(value=motivo_opts[0])
    motivo_combo = ctk.CTkComboBox(f_mot, values=motivo_opts, variable=motivo_var, height=34)
    motivo_combo.pack(fill="x")

    # Linha: Data / Hora e Quem Recebeu
    row_dt_resp = ctk.CTkFrame(form_frame, fg_color="transparent")
    row_dt_resp.pack(fill="x", pady=(0, 10))
    row_dt_resp.grid_columnconfigure((0, 1), weight=1)

    # Data / Hora
    f_dt = ctk.CTkFrame(row_dt_resp, fg_color="transparent")
    f_dt.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    ctk.CTkLabel(f_dt, text="8. Data da Entrada (DD/MM/AAAA): *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))
    row_cal = ctk.CTkFrame(f_dt, fg_color="transparent")
    row_cal.pack(fill="x")
    dt_entry = ctk.CTkEntry(row_cal, placeholder_text="DD/MM/AAAA", height=34)
    dt_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
    dt_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
    from ui.components.date_picker import open_date_picker
    dt_entry.bind("<Double-Button-1>", lambda e: open_date_picker(dialog, target_entry=dt_entry))
    btn_cal = ctk.CTkButton(
        row_cal,
        text="📅",
        width=38,
        height=34,
        fg_color="#3B82F6",
        hover_color="#1D4ED8",
        command=lambda: open_date_picker(dialog, target_entry=dt_entry)
    )
    btn_cal.pack(side="right")

    # Quem Recebeu
    f_resp = ctk.CTkFrame(row_dt_resp, fg_color="transparent")
    f_resp.grid(row=0, column=1, sticky="ew", padx=(6, 0))
    ctk.CTkLabel(f_resp, text="9. Quem Recebeu / Responsável: *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))
    operators = MovementService.get_operators() or ["Almoxarifado"]
    resp_var = tk.StringVar(value=operators[0])
    resp_combo = ctk.CTkComboBox(f_resp, values=operators, variable=resp_var, height=34)
    resp_combo.pack(fill="x")

    # Observações adicionais
    ctk.CTkLabel(form_frame, text="10. Observações Adicionais (opcional):", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 2))
    obs_entry = ctk.CTkEntry(form_frame, placeholder_text="Ex: Lote 452, validade 2029, armazenado no Corredor B...", height=34)
    obs_entry.pack(fill="x", pady=(0, 10))

    # Card Dinâmico de Impacto no Saldo e Custo
    sim_card = ctk.CTkFrame(form_frame, fg_color="#F0FDF4", corner_radius=8, border_width=1, border_color="#22C55E")
    sim_card.pack(fill="x", pady=(0, 12), ipady=4)
    lbl_simulacao = ctk.CTkLabel(sim_card, text="", font=FONT_BODY_BOLD, text_color="#15803D", justify="left")
    lbl_simulacao.pack(anchor="w", padx=12, pady=6)

    def on_epi_change(*args):
        eid = epi_map.get(epi_var.get())
        if not eid or eid not in epi_data_map:
            return
        e = epi_data_map[eid]
        preco_padrao = float(e.get("preco_unitario") or 0.0)
        preco_entry.delete(0, "end")
        preco_entry.insert(0, f"{preco_padrao:.2f}")

        # Atualiza tamanhos disponíveis
        grades = EPIService.get_available_sizes(eid)
        sizes = [g["tamanho"] for g in grades if g.get("tamanho")]
        default_sizes = ["Único", "P", "M", "G", "GG", "XG", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45"]
        combined_sizes = list(dict.fromkeys(sizes + default_sizes))
        tam_combo.configure(values=combined_sizes)
        if sizes:
            tam_var.set(sizes[0])
        else:
            tam_var.set(e.get("tamanho") or "Único")

        fabricante = e.get("fabricante") or "Não informado"
        loc1 = e.get("localizacao") or "Almoxarifado Principal"
        loc2 = e.get("localizacao_secundaria")
        localizacao = f"{loc1}  |  {loc2}" if loc2 else loc1
        lbl_info_epi.configure(
            text=f"🏷️ Código: {e['codigo']}  |  🛡️ C.A.: {e['ca']}  |  🏢 Fabricante: {fabricante}\n"
                 f"📦 Saldo Atual: {e['quantidade']} {e['unidade']}  |  📍 Local: {localizacao}  |  💵 Custo Atual: R$ {preco_padrao:.2f}"
        )
        update_simulation()

    def update_simulation(*args):
        eid = epi_map.get(epi_var.get())
        if not eid or eid not in epi_data_map:
            return
        e = epi_data_map[eid]
        saldo_atual = int(e.get("quantidade") or 0)
        unidade = e.get("unidade") or "un"

        q_str = qtd_entry.get().strip()
        try:
            qtd = int(q_str) if q_str.isdigit() else 0
        except ValueError:
            qtd = 0

        p_str = preco_entry.get().strip().replace(",", ".")
        try:
            preco = float(p_str) if p_str else 0.0
        except ValueError:
            preco = 0.0

        novo_saldo = saldo_atual + qtd
        total_gasto = qtd * preco

        lbl_simulacao.configure(
            text=f"📦 Saldo Atual: {saldo_atual} {unidade}  ➕  Entrada: {qtd} {unidade}  🟰  NOVO SALDO: {novo_saldo} {unidade}\n"
                 f"💰 Valor Total Desta Entrada: R$ {total_gasto:.2f} ({qtd} un x R$ {preco:.2f})"
        )

    epi_var.trace_add("write", on_epi_change)
    qtd_entry.bind("<KeyRelease>", update_simulation)
    preco_entry.bind("<KeyRelease>", update_simulation)

    on_epi_change()

    # Barra inferior de botões
    b_box = ctk.CTkFrame(dialog, fg_color="transparent")
    b_box.pack(fill="x", padx=25, pady=(0, 16))

    ctk.CTkButton(
        b_box,
        text="Cancelar",
        font=FONT_BODY,
        fg_color="#64748B",
        hover_color="#475569",
        height=38,
        command=dialog.destroy
    ).pack(side="left")

    def submit_entry():
        try:
            eid = epi_map.get(epi_var.get())
            if not eid:
                messagebox.showerror("Erro", "Selecione um EPI válido!")
                return

            q_str = qtd_entry.get().strip()
            if not q_str.isdigit() or int(q_str) <= 0:
                messagebox.showerror("Erro", "Informe uma quantidade válida maior que zero!")
                return
            qtd = int(q_str)

            p_str = preco_entry.get().strip().replace(",", ".")
            try:
                custo_unit = float(p_str) if p_str else 0.0
            except ValueError:
                custo_unit = 0.0

            resp = resp_var.get().strip()
            if not resp:
                messagebox.showerror("Erro", "Informe quem recebeu / registrou a entrada!")
                return

            mot = motivo_var.get().strip()
            dt_raw = dt_entry.get().strip() or None
            nf_val = nf_entry.get().strip()
            obs_val = obs_entry.get().strip()

            obs_completa = []
            if nf_val:
                obs_completa.append(f"Doc/NF: {nf_val}")
            if obs_val:
                obs_completa.append(obs_val)
            obs_final = " | ".join(obs_completa)

            tam_sel = tam_var.get().strip() or "Único"
            cond_raw = cond_var.get()
            cond_sel = "NOVO" if "NOVO" in cond_raw else ("BOM / REUTILIZÁVEL" if "BOM" in cond_raw else ("RUIM / MANUTENÇÃO" if "RUIM" in cond_raw else "DESCARTE / SUCATA"))

            atualizar_preco = chk_atualizar_preco_var.get()

            MovementService.register_entry(
                epi_id=eid,
                quantidade=qtd,
                responsavel=resp,
                motivo=mot,
                data_hora=dt_raw,
                observacao=obs_final,
                custo_unitario=custo_unit,
                tamanho=tam_sel,
                estado_conservacao=cond_sel,
                atualizar_preco_base=atualizar_preco
            )

            epi_info = epi_data_map[eid]
            saldo_anterior = int(epi_info.get("quantidade") or 0)
            novo_saldo = saldo_anterior + qtd

            messagebox.showinfo(
                "Entrada Registrada com Sucesso!",
                f"Entrada de {qtd} unidade(s) registrada no estoque!\n\n"
                f"• EPI: {epi_info['codigo']} - {epi_info['nome']}\n"
                f"• Tamanho: {tam_sel}\n"
                f"• Condição: {cond_sel}\n"
                f"• Saldo Anterior: {saldo_anterior} un  ➡️  Novo Saldo: {novo_saldo} un\n"
                f"• Custo Unitário: R$ {custo_unit:.2f} (Total: R$ {(qtd * custo_unit):.2f})\n"
                f"• Responsável: {resp}"
            )
            dialog.destroy()
            if on_success:
                on_success()
        except Exception as ex:
            messagebox.showerror("Erro ao Lançar Entrada", str(ex))

    ctk.CTkButton(
        b_box,
        text="✅ Confirmar Entrada no Estoque",
        font=FONT_BODY_BOLD,
        fg_color="#059669",
        hover_color="#047857",
        height=38,
        command=submit_entry
    ).pack(side="right")
