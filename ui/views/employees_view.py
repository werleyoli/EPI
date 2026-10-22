import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

from services.employee_service import EmployeeService
from ui.components.theme import *
from ui.components.table_view import StyledTable

class EmployeesView(ctk.CTkFrame):
    def __init__(self, parent, on_view_sheet=None, on_refresh_dashboard=None):
        super().__init__(parent, fg_color="transparent")
        self.on_view_sheet = on_view_sheet
        self.on_refresh_dashboard = on_refresh_dashboard
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Cabeçalho
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(20, 15))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(title_box, text="Cadastro & Fichas de Funcionários", font=FONT_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Gestão dos colaboradores e termos de responsabilidade individual", font=FONT_BODY, text_color=TEXT_MUTED).pack(anchor="w")

        # Botões de ação
        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")

        btn_deptos = ctk.CTkButton(
            btn_box,
            text="🏢 Departamentos / Setores",
            font=FONT_BODY_BOLD,
            fg_color="#0D9488",
            hover_color="#0F766E",
            height=36,
            command=self._open_department_manager
        )
        btn_deptos.pack(side="left", padx=4)

        btn_ver_ficha = ctk.CTkButton(
            btn_box,
            text="📄 ABRIR FICHA DE EPI (NR-6)",
            font=FONT_BODY_BOLD,
            fg_color="#6366F1",
            hover_color="#4F46E5",
            height=36,
            command=self._view_selected_sheet
        )
        btn_ver_ficha.pack(side="left", padx=4)

        btn_import = ctk.CTkButton(
            btn_box,
            text="📥 Importar Excel",
            font=FONT_BODY,
            fg_color="#4F46E5",
            hover_color="#4338CA",
            height=36,
            command=self._import_excel
        )
        btn_import.pack(side="left", padx=3)

        btn_modelo = ctk.CTkButton(
            btn_box,
            text="📄 Modelo",
            font=FONT_BODY,
            fg_color="#64748B",
            hover_color="#475569",
            height=36,
            command=self._download_template
        )
        btn_modelo.pack(side="left", padx=3)

        btn_edit = ctk.CTkButton(
            btn_box,
            text="✏️ Editar",
            font=FONT_BODY,
            fg_color="#475569",
            hover_color="#334155",
            height=36,
            command=self.open_edit_modal
        )
        btn_edit.pack(side="left", padx=3)

        btn_novo = ctk.CTkButton(
            btn_box,
            text="➕ Novo Funcionário",
            font=FONT_BODY_BOLD,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=36,
            command=self.open_new_modal
        )
        btn_novo.pack(side="left", padx=(3, 0))

        # Filtros e Busca
        filter_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        filter_card.pack(fill="x", padx=25, pady=(0, 15))

        f_inner = ctk.CTkFrame(filter_card, fg_color="transparent")
        f_inner.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(f_inner, text="🔍 Buscar:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            f_inner,
            placeholder_text="Nome, matrícula, CPF, cargo, setor...",
            textvariable=self.search_var,
            width=260,
            height=32
        )
        self.search_entry.pack(side="left", padx=(0, 15))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh())

        ctk.CTkLabel(f_inner, text="Status:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 6))
        self.status_var = tk.StringVar(value="all")
        self.filter_seg = ctk.CTkSegmentedButton(
            f_inner,
            values=["🔘 Todos", "✅ Ativos", "❌ Inativos / Desligados", "🚨 Pendência EPI"],
            command=self._on_status_tab_changed,
            height=32
        )
        self.filter_seg.set("🔘 Todos")
        self.filter_seg.pack(side="left", padx=(0, 15))

        self.count_lbl = ctk.CTkLabel(f_inner, text="0 funcionários", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.count_lbl.pack(side="right")

        # Tabela
        tbl_container = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        tbl_container.pack(fill="both", expand=True, padx=25, pady=(0, 20))

        cols = [
            {"id": "matricula", "text": "Matrícula", "width": 90, "anchor": "center"},
            {"id": "nome", "text": "Nome Completo", "width": 240, "anchor": "w"},
            {"id": "cpf", "text": "CPF", "width": 110, "anchor": "center"},
            {"id": "cargo", "text": "Função / Cargo", "width": 180, "anchor": "w"},
            {"id": "depto", "text": "Setor / Departamento", "width": 180, "anchor": "w"},
            {"id": "admissao", "text": "Admissão", "width": 95, "anchor": "center"},
            {"id": "status", "text": "Status", "width": 140, "anchor": "center"},
        ]
        self.table = StyledTable(
            tbl_container,
            columns=cols,
            on_double_click=lambda row_id: self._view_selected_sheet()
        )
        self.table.pack(fill="both", expand=True, padx=12, pady=12)

    def _on_status_tab_changed(self, value):
        mapping = {
            "🔘 Todos": "all",
            "✅ Ativos": "Ativo",
            "❌ Inativos / Desligados": "Inativo",
            "🚨 Pendência EPI": "Pendência"
        }
        self.status_var.set(mapping.get(value, "all"))
        self.refresh()

    def refresh(self):
        if hasattr(self, "table"):
            self.table.apply_theme(ctk.get_appearance_mode())

        search = self.search_var.get().strip()
        status = self.status_var.get().strip()
        self.employees = EmployeeService.list_employees(search=search, status=status)

        self.table.clear()
        for e in self.employees:
            st = e["status"]
            if st == "Ativo":
                status_display = "✅ Ativo"
                tag = "even"
            elif "Pendência" in st or "Pendente" in st:
                status_display = f"🚨 {st}"
                tag = "danger"
            elif "Desligado" in st or "Inativo" in st:
                status_display = f"❌ {st}"
                tag = "danger"
            elif st == "Afastado":
                status_display = "⚠️ Afastado"
                tag = "warning"
            else:
                status_display = st
                tag = "even"

            dt_adm = e.get("data_admissao") or "-"
            if dt_adm != "-" and "-" in dt_adm:
                try:
                    dt_adm = datetime.strptime(dt_adm[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
                except Exception:
                    pass

            self.table.insert_row(
                e["id"],
                [
                    e["matricula"],
                    e["nome"],
                    e.get("cpf") or "-",
                    e["cargo"],
                    e["departamento"],
                    dt_adm,
                    status_display
                ],
                tag=tag
            )

        self.count_lbl.configure(text=f"{len(self.employees)} colaboradores listados")

    def _view_selected_sheet(self):
        row_id = self.table.get_selected()
        if not row_id:
            messagebox.showwarning("Aviso", "Selecione um funcionário na tabela para abrir a Ficha de EPI.")
            return
        if self.on_view_sheet:
            self.on_view_sheet(int(row_id))

    def _import_excel(self):
        """Importa lista de colaboradores via planilha Excel ou CSV."""
        from tkinter import filedialog
        from services.import_service import ImportService
        fpath = filedialog.askopenfilename(
            title="Selecione a Planilha de Colaboradores",
            filetypes=[("Planilhas", "*.xlsx *.xls *.csv")]
        )
        if not fpath:
            return
        try:
            res = ImportService.import_employees_excel(fpath)
            msg = f"Importação Concluída com Sucesso!\n\n• Novos colaboradores: {res['inseridos']}\n• Colaboradores atualizados: {res['atualizados']}"
            if res["erros"]:
                msg += f"\n\nErros identificados ({len(res['erros'])}):\n" + "\n".join(res["erros"][:5])
            messagebox.showinfo("Importação de Funcionários", msg)
            self.refresh()
            if self.on_refresh_dashboard:
                self.on_refresh_dashboard()
        except Exception as ex:
            messagebox.showerror("Erro na Importação", str(ex))

    def _download_template(self):
        """Gera e abre o modelo de planilha Excel para funcionários."""
        import os
        from services.import_service import ImportService
        try:
            fpath = ImportService.generate_employee_template()
            ans = messagebox.askyesno("Planilha Modelo Gerada", f"Modelo Excel gerado em:\n{fpath}\n\nDeseja abrir a planilha modelo agora?")
            if ans:
                os.startfile(fpath)
        except Exception as ex:
            messagebox.showerror("Erro ao Gerar Modelo", str(ex))

    def open_new_modal(self):
        self._open_form_modal(None)

    def open_edit_modal(self):
        row_id = self.table.get_selected()
        if not row_id:
            messagebox.showwarning("Aviso", "Selecione um funcionário na tabela para editar.")
            return
        emp = EmployeeService.get_employee(int(row_id))
        if emp:
            self._open_form_modal(emp)

    def _open_form_modal(self, emp=None):
        is_edit = emp is not None
        dialog = ctk.CTkToplevel(self)
        dialog.title("Editar Funcionário" if is_edit else "Cadastrar Novo Funcionário")
        dialog.geometry("620x720")
        dialog.resizable(False, False)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 620) // 2
        y = (dialog.winfo_screenheight() - 720) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text="✏️ Editar Colaborador" if is_edit else "👷 Novo Colaborador",
            font=FONT_SUBTITLE,
            text_color=TEXT_MAIN
        ).pack(pady=(14, 2))

        f = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=25, pady=(0, 10))

        # Matrícula e CPF
        r0 = ctk.CTkFrame(f, fg_color="transparent")
        r0.pack(fill="x", pady=(0, 8))
        r0.grid_columnconfigure((0, 1), weight=1)

        mat_box = ctk.CTkFrame(r0, fg_color="transparent")
        mat_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(mat_box, text="Matrícula / RE *", font=FONT_BODY_BOLD).pack(anchor="w")
        mat_entry = ctk.CTkEntry(mat_box, height=32)
        if is_edit:
            mat_entry.insert(0, emp["matricula"])
        else:
            mat_entry.insert(0, f"FUNC-{len(self.employees)+101}")
        mat_entry.pack(fill="x", pady=(2, 0))

        cpf_box = ctk.CTkFrame(r0, fg_color="transparent")
        cpf_box.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ctk.CTkLabel(cpf_box, text="CPF", font=FONT_BODY_BOLD).pack(anchor="w")
        cpf_entry = ctk.CTkEntry(cpf_box, placeholder_text="000.000.000-00", height=32)
        if is_edit and emp.get("cpf"):
            cpf_entry.insert(0, emp["cpf"])
        cpf_entry.pack(fill="x", pady=(2, 0))

        # Nome
        ctk.CTkLabel(f, text="Nome Completo do Colaborador *", font=FONT_BODY_BOLD).pack(anchor="w")
        nome_entry = ctk.CTkEntry(f, height=32)
        if is_edit:
            nome_entry.insert(0, emp["nome"])
        nome_entry.pack(fill="x", pady=(2, 8))

        # Telefone / WhatsApp
        ctk.CTkLabel(f, text="📱 WhatsApp / Celular (para envio de recibos)", font=FONT_BODY_BOLD).pack(anchor="w")
        tel_entry = ctk.CTkEntry(f, placeholder_text="(11) 98765-4321", height=32)
        if is_edit and emp.get("telefone"):
            tel_entry.insert(0, emp["telefone"])
        tel_entry.pack(fill="x", pady=(2, 8))

        # Cargo e Departamento
        r1 = ctk.CTkFrame(f, fg_color="transparent")
        r1.pack(fill="x", pady=(0, 8))
        r1.grid_columnconfigure((0, 1), weight=1)

        c_box = ctk.CTkFrame(r1, fg_color="transparent")
        c_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(c_box, text="Função / Cargo *", font=FONT_BODY_BOLD).pack(anchor="w")
        cargo_entry = ctk.CTkEntry(c_box, height=32)
        if is_edit:
            cargo_entry.insert(0, emp["cargo"])
        cargo_entry.pack(fill="x", pady=(2, 0))

        d_box = ctk.CTkFrame(r1, fg_color="transparent")
        d_box.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ctk.CTkLabel(d_box, text="Setor / Departamento *", font=FONT_BODY_BOLD).pack(anchor="w")
        dept_options = EmployeeService.list_nomes_departamentos()
        depto_entry = ctk.CTkComboBox(d_box, values=dept_options, height=32)
        if is_edit and emp.get("departamento"):
            depto_entry.set(emp["departamento"])
        elif dept_options:
            depto_entry.set(dept_options[0])
        depto_entry.pack(fill="x", pady=(2, 0))

        # Admissão e Status
        r2 = ctk.CTkFrame(f, fg_color="transparent")
        r2.pack(fill="x", pady=(0, 10))
        r2.grid_columnconfigure((0, 1), weight=1)

        adm_box = ctk.CTkFrame(r2, fg_color="transparent")
        adm_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(adm_box, text="Data de Admissão (DD/MM/AAAA)", font=FONT_BODY_BOLD).pack(anchor="w")
        row_adm_dt = ctk.CTkFrame(adm_box, fg_color="transparent")
        row_adm_dt.pack(fill="x", pady=(2, 0))
        adm_entry = ctk.CTkEntry(row_adm_dt, placeholder_text="DD/MM/AAAA", height=32)
        adm_val = emp.get("data_admissao", "") if is_edit else ""
        if adm_val and "-" in adm_val:
            try:
                adm_val = datetime.strptime(adm_val[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                pass
        if adm_val:
            adm_entry.insert(0, adm_val)
        adm_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        from ui.components.date_picker import open_date_picker
        adm_entry.bind("<Double-Button-1>", lambda e: open_date_picker(dialog, target_entry=adm_entry))
        btn_adm_cal = ctk.CTkButton(
            row_adm_dt,
            text="📅",
            width=38,
            height=32,
            fg_color="#3B82F6",
            hover_color="#1D4ED8",
            command=lambda: open_date_picker(dialog, target_entry=adm_entry)
        )
        btn_adm_cal.pack(side="right")

        st_box = ctk.CTkFrame(r2, fg_color="transparent")
        st_box.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ctk.CTkLabel(st_box, text="Status", font=FONT_BODY_BOLD).pack(anchor="w")
        st_var = tk.StringVar(value=emp["status"] if is_edit else "Ativo")
        ctk.CTkComboBox(st_box, values=["Ativo", "Inativo", "Afastado"], variable=st_var, height=32).pack(fill="x", pady=(2, 0))

        # SEÇÃO: Grade de Tamanhos & Medidas Personalizadas (Compatível com Tema Escuro e Claro)
        size_frame = ctk.CTkFrame(f, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        size_frame.pack(fill="x", pady=(4, 10), padx=2, ipady=6)

        ctk.CTkLabel(
            size_frame,
            text="📏 Grade de Tamanhos & Medidas do Colaborador",
            font=FONT_BODY_BOLD,
            text_color=("#1E3A8A", "#60A5FA")
        ).pack(anchor="w", padx=10, pady=(6, 6))

        r3 = ctk.CTkFrame(size_frame, fg_color="transparent")
        r3.pack(fill="x", padx=10, pady=(0, 6))
        r3.grid_columnconfigure((0, 1), weight=1)

        # Calçado
        calc_box = ctk.CTkFrame(r3, fg_color="transparent")
        calc_box.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(calc_box, text="👟 Nº Calçado / Bota", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w")
        calc_var = tk.StringVar(value=str(emp.get("tamanho_calcado") or "") if is_edit and emp.get("tamanho_calcado") else "")
        calc_opts = ["", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48"]
        ctk.CTkComboBox(calc_box, values=calc_opts, variable=calc_var, height=30).pack(fill="x", pady=(2, 0))

        # Luva
        luva_box = ctk.CTkFrame(r3, fg_color="transparent")
        luva_box.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(luva_box, text="🧤 Tam. Luva", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w")
        luva_var = tk.StringVar(value=str(emp.get("tamanho_luva") or "") if is_edit and emp.get("tamanho_luva") else "")
        luva_opts = ["", "P (7)", "M (8)", "G (9)", "XG (10)", "XXG (11)"]
        ctk.CTkComboBox(luva_box, values=luva_opts, variable=luva_var, height=30).pack(fill="x", pady=(2, 0))

        r4 = ctk.CTkFrame(size_frame, fg_color="transparent")
        r4.pack(fill="x", padx=10, pady=(0, 6))
        r4.grid_columnconfigure((0, 1), weight=1)

        # Uniforme
        uni_box = ctk.CTkFrame(r4, fg_color="transparent")
        uni_box.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(uni_box, text="👕 Tam. Uniforme / Macacão", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w")
        uni_var = tk.StringVar(value=str(emp.get("tamanho_uniforme") or "") if is_edit and emp.get("tamanho_uniforme") else "")
        uni_opts = ["", "PP", "P", "M", "G", "GG", "XG", "XXG", "38", "40", "42", "44", "46", "48", "50"]
        ctk.CTkComboBox(uni_box, values=uni_opts, variable=uni_var, height=30).pack(fill="x", pady=(2, 0))

        # Máscara
        masc_box = ctk.CTkFrame(r4, fg_color="transparent")
        masc_box.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(masc_box, text="😷 Respirador / Máscara", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w")
        masc_var = tk.StringVar(value=str(emp.get("tamanho_mascara") or "") if is_edit and emp.get("tamanho_mascara") else "")
        masc_opts = ["", "P", "M", "G", "Único"]
        ctk.CTkComboBox(masc_box, values=masc_opts, variable=masc_var, height=30).pack(fill="x", pady=(2, 0))

        # Observações
        ctk.CTkLabel(f, text="Observações (opcional):", font=FONT_SMALL).pack(anchor="w")
        obs_entry = ctk.CTkEntry(f, placeholder_text="Ex: Trabalha em altura, área com ruído...", height=32)
        if is_edit and emp.get("observacoes"):
            obs_entry.insert(0, emp["observacoes"])
        obs_entry.pack(fill="x", pady=(2, 10))

        # Botões
        b_box = ctk.CTkFrame(dialog, fg_color="transparent")
        b_box.pack(fill="x", padx=25, pady=(4, 16))

        ctk.CTkButton(b_box, text="Cancelar", fg_color="#94A3B8", command=dialog.destroy).pack(side="left")

        def submit():
            mat = mat_entry.get().strip()
            nome = nome_entry.get().strip()
            cargo = cargo_entry.get().strip()
            depto = depto_entry.get().strip()

            if not mat or not nome or not cargo or not depto:
                messagebox.showerror("Campos Obrigatórios", "Preencha Matrícula, Nome, Cargo e Setor!")
                return

            adm_val_save = adm_entry.get().strip()
            if adm_val_save and "/" in adm_val_save:
                try:
                    adm_val_save = datetime.strptime(adm_val_save[:10], "%d/%m/%Y").strftime("%Y-%m-%d")
                except Exception:
                    pass

            data = {
                "matricula": mat,
                "nome": nome,
                "cpf": cpf_entry.get().strip(),
                "telefone": tel_entry.get().strip(),
                "cargo": cargo,
                "departamento": depto,
                "data_admissao": adm_val_save,
                "tamanho_calcado": calc_var.get().strip(),
                "tamanho_luva": luva_var.get().strip(),
                "tamanho_uniforme": uni_var.get().strip(),
                "tamanho_mascara": masc_var.get().strip(),
                "status": st_var.get(),
                "observacoes": obs_entry.get().strip(),
            }

            try:
                if is_edit:
                    EmployeeService.update_employee(emp["id"], data)
                    messagebox.showinfo("Sucesso", "Dados do colaborador atualizados com sucesso!")
                else:
                    EmployeeService.create_employee(data)
                    messagebox.showinfo("Sucesso", "Novo colaborador cadastrado com sucesso!")

                dialog.destroy()
                self.refresh()
                if self.on_refresh_dashboard:
                    self.on_refresh_dashboard()
            except Exception as ex:
                messagebox.showerror("Erro ao Salvar", str(ex))

        ctk.CTkButton(b_box, text="Salvar Alterações" if is_edit else "Cadastrar Colaborador", fg_color="#1E3A8A", command=submit).pack(side="right")

    def _open_department_manager(self):
        """Abre modal interativo para gerenciamento, visualização e cadastro de Departamentos / Setores."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Gerenciamento de Departamentos & Setores")
        dialog.geometry("740x550")
        dialog.resizable(False, False)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 740) // 2
        y = (dialog.winfo_screenheight() - 550) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text="🏢 Gerenciamento de Departamentos & Setores",
            font=FONT_SUBTITLE,
            text_color=TEXT_MAIN
        ).pack(pady=(16, 2))
        ctk.CTkLabel(
            dialog,
            text="Cadastre e gerencie os setores da empresa para o painel de custos e alocação de EPIs",
            font=FONT_SMALL,
            text_color=TEXT_MUTED
        ).pack(pady=(0, 12))

        # Card de Cadastro de Novo Setor
        add_card = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        add_card.pack(fill="x", padx=20, pady=(0, 12))

        add_inner = ctk.CTkFrame(add_card, fg_color="transparent")
        add_inner.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(add_inner, text="Nome do Setor / Departamento:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(side="left", padx=(0, 8))
        nome_dept_entry = ctk.CTkEntry(add_inner, placeholder_text="Ex: Manutenção Elétrica, Almoxarifado...", width=260, height=32)
        nome_dept_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)

        def add_depto():
            nome = nome_dept_entry.get().strip()
            if not nome:
                messagebox.showwarning("Aviso", "Digite o nome do departamento!")
                return
            try:
                EmployeeService.create_departamento(nome)
                messagebox.showinfo("Sucesso", f"Departamento '{nome}' cadastrado com sucesso!")
                nome_dept_entry.delete(0, "end")
                refresh_deptos_table()
                self.refresh()
                if self.on_refresh_dashboard:
                    self.on_refresh_dashboard()
            except Exception as ex:
                messagebox.showerror("Erro ao Cadastrar", str(ex))

        btn_add = ctk.CTkButton(
            add_inner,
            text="➕ Cadastrar Setor",
            font=FONT_BODY_BOLD,
            fg_color="#0D9488",
            hover_color="#0F766E",
            height=32,
            command=add_depto
        )
        btn_add.pack(side="left")

        # Tabela de Departamentos
        tbl_box = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        tbl_box.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        cols = [
            {"id": "nome", "text": "Departamento / Setor", "width": 260, "anchor": "w"},
            {"id": "colabs", "text": "Colaboradores Alocados", "width": 180, "anchor": "center"},
            {"id": "gastos", "text": "Gasto Acumulado com EPI", "width": 180, "anchor": "center"},
        ]
        dept_table = StyledTable(tbl_box, columns=cols)
        dept_table.pack(fill="both", expand=True, padx=8, pady=8)

        def refresh_deptos_table():
            dept_table.apply_theme(ctk.get_appearance_mode())
            dept_table.clear()
            deptos = EmployeeService.list_departamentos()
            for d in deptos:
                dept_table.insert_row(
                    d["nome"],
                    [
                        d["nome"],
                        f"👥 {d.get('total_funcionarios', 0)} colaborador(es)",
                        f"R$ {d.get('total_gasto', 0.0):.2f}"
                    ]
                )

        refresh_deptos_table()

        # Rodapé de Ações
        bot_bar = ctk.CTkFrame(dialog, fg_color="transparent")
        bot_bar.pack(fill="x", padx=20, pady=(0, 15))

        def del_depto():
            sel_nome = dept_table.get_selected()
            if not sel_nome:
                messagebox.showwarning("Aviso", "Selecione um departamento na tabela para excluir.")
                return

            ans = messagebox.askyesno(
                "Confirmar Exclusão",
                f"Tem certeza que deseja remover o departamento '{sel_nome}' do catálogo de setores?"
            )
            if not ans:
                return

            try:
                EmployeeService.delete_departamento(sel_nome)
                messagebox.showinfo("Sucesso", f"Departamento '{sel_nome}' removido com sucesso!")
                refresh_deptos_table()
                self.refresh()
                if self.on_refresh_dashboard:
                    self.on_refresh_dashboard()
            except Exception as ex:
                messagebox.showerror("Erro ao Excluir", str(ex))

        ctk.CTkButton(
            bot_bar,
            text="🗑️ Excluir Setor Selecionado",
            font=FONT_BODY,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            command=del_depto
        ).pack(side="left")

        ctk.CTkButton(
            bot_bar,
            text="Fechar",
            font=FONT_BODY,
            fg_color="#64748B",
            hover_color="#475569",
            command=dialog.destroy
        ).pack(side="right")
