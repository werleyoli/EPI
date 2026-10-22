import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

from services.matriz_service import MatrizService
from services.epi_service import EPIService
from services.employee_service import EmployeeService
from services.auth_service import AuthService
from ui.components.theme import *
from ui.components.table_view import StyledTable
from ui.components.signature_pad import SignatureDialog

class MatrizView(ctk.CTkFrame):
    def __init__(self, parent, on_refresh_dashboard=None):
        super().__init__(parent, fg_color="transparent")
        self.on_refresh_dashboard = on_refresh_dashboard
        self.current_cargo = None
        self._build_ui()
        self.load_cargos()

    def _build_ui(self):
        # Cabeçalho
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(20, 15))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(title_box, text="Matriz de EPIs por Função & Kits Admissionais", font=FONT_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Configure os EPIs obrigatórios de cada cargo e entregue kits completos com 1 clique", font=FONT_BODY, text_color=TEXT_MUTED).pack(anchor="w")

        # Botão de Ação: Entregar Kit em Lote
        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")

        btn_deliver_kit = ctk.CTkButton(
            btn_box,
            text="⚡ ENTREGAR KIT COMPLETO P/ FUNCIONÁRIO",
            font=FONT_BODY_BOLD,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=38,
            command=self.open_deliver_kit_modal
        )
        btn_deliver_kit.pack(side="left", padx=5)

        # Seletor de Cargo
        top_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        top_card.pack(fill="x", padx=25, pady=(0, 15))

        top_inner = ctk.CTkFrame(top_card, fg_color="transparent")
        top_inner.pack(fill="x", padx=15, pady=12)

        ctk.CTkLabel(top_inner, text="🏢 Selecione a Função / Cargo:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(side="left", padx=(0, 10))

        self.cargo_var = tk.StringVar()
        self.cargo_combo = ctk.CTkComboBox(
            top_inner,
            values=["Carregando..."],
            variable=self.cargo_var,
            width=320,
            height=34,
            command=self._on_cargo_selected
        )
        self.cargo_combo.pack(side="left", padx=(0, 15))

        btn_add_item = ctk.CTkButton(
            top_inner,
            text="➕ Adicionar EPI a Este Cargo",
            font=FONT_BODY,
            fg_color="#0D9488",
            hover_color="#0F766E",
            height=34,
            command=self.open_add_epi_modal
        )
        btn_add_item.pack(side="left", padx=(0, 8))

        btn_remove_item = ctk.CTkButton(
            top_inner,
            text="🗑️ Remover do Kit",
            font=FONT_BODY,
            fg_color="#EF4444",
            hover_color="#DC2626",
            height=34,
            command=self.remove_selected_epi
        )
        btn_remove_item.pack(side="left")

        self.count_lbl = ctk.CTkLabel(top_inner, text="0 EPIs vinculados", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.count_lbl.pack(side="right")

        # Tabela da Matriz
        tbl_container = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        tbl_container.pack(fill="both", expand=True, padx=25, pady=(0, 20))

        cols = [
            {"id": "codigo", "text": "Código", "width": 80, "anchor": "center"},
            {"id": "nome", "text": "Equipamento (EPI) Obrigatório", "width": 280, "anchor": "w"},
            {"id": "ca", "text": "C.A.", "width": 75, "anchor": "center"},
            {"id": "qtd", "text": "Qtd Recomendada", "width": 110, "anchor": "center"},
            {"id": "periodicidade", "text": "Troca Preventiva", "width": 110, "anchor": "center"},
            {"id": "saldo", "text": "Saldo Almoxarifado", "width": 120, "anchor": "center"},
            {"id": "preco", "text": "Custo Unitário", "width": 100, "anchor": "center"},
        ]
        self.table = StyledTable(tbl_container, columns=cols)
        self.table.pack(fill="both", expand=True, padx=12, pady=12)

    def load_cargos(self):
        cargos = MatrizService.list_cargos()
        if not cargos:
            cargos = ["Mecânico de Manutenção", "Operador de Produção", "Eletricista Industrial"]
        self.cargo_combo.configure(values=cargos)
        if cargos:
            self.cargo_var.set(cargos[0])
            self._load_cargo_data(cargos[0])

    def _on_cargo_selected(self, choice):
        self._load_cargo_data(choice)

    def _load_cargo_data(self, cargo):
        self.current_cargo = cargo
        if hasattr(self, "table"):
            self.table.apply_theme(ctk.get_appearance_mode())

        items = MatrizService.get_epis_for_cargo(cargo)
        self.table.clear()

        for item in items:
            saldo = item["saldo_atual"]
            tag = "even"
            if saldo == 0:
                tag = "danger"
            elif saldo < item["qtd_recomendada"]:
                tag = "warning"

            self.table.insert_row(
                item["epi_id"],
                [
                    item["codigo"],
                    item["nome"],
                    item["ca"],
                    f"{item['qtd_recomendada']} {item['unidade']}",
                    f"A cada {item['periodicidade_dias']} dias",
                    f"{saldo} {item['unidade']}",
                    f"R$ {item['preco_unitario']:.2f}"
                ],
                tag=tag
            )

        self.count_lbl.configure(text=f"{len(items)} EPIs vinculados a esta função")

    def open_add_epi_modal(self):
        if not self.current_cargo:
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Vincular EPI à Função: {self.current_cargo}")
        dialog.geometry("520x400")
        dialog.resizable(False, False)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 520) // 2
        y = (dialog.winfo_screenheight() - 400) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text=f"➕ Adicionar EPI ao Cargo: {self.current_cargo}", font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(pady=(18, 12))

        f = ctk.CTkFrame(dialog, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=25)

        epis = EPIService.list_epis(show_inactive=False)
        epi_map = {f"{e['codigo']} - {e['nome']} (C.A. {e['ca']})": e["id"] for e in epis}

        ctk.CTkLabel(f, text="Selecione o EPI *", font=FONT_BODY_BOLD).pack(anchor="w")
        epi_var = tk.StringVar(value=list(epi_map.keys())[0] if epi_map else "")
        ctk.CTkComboBox(f, values=list(epi_map.keys()), variable=epi_var, height=34).pack(fill="x", pady=(2, 10))

        r = ctk.CTkFrame(f, fg_color="transparent")
        r.pack(fill="x", pady=(0, 15))
        r.grid_columnconfigure((0, 1), weight=1)

        q_box = ctk.CTkFrame(r, fg_color="transparent")
        q_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(q_box, text="Quantidade Recomendada *", font=FONT_BODY_BOLD).pack(anchor="w")
        q_entry = ctk.CTkEntry(q_box, height=32)
        q_entry.insert(0, "1")
        q_entry.pack(fill="x", pady=(2, 0))

        p_box = ctk.CTkFrame(r, fg_color="transparent")
        p_box.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ctk.CTkLabel(p_box, text="Periodicidade de Troca (Dias) *", font=FONT_BODY_BOLD).pack(anchor="w")
        p_entry = ctk.CTkEntry(p_box, height=32)
        p_entry.insert(0, "90")
        p_entry.pack(fill="x", pady=(2, 0))

        def submit():
            try:
                epi_id = epi_map[epi_var.get()]
                qtd = int(q_entry.get().strip())
                dias = int(p_entry.get().strip())

                MatrizService.add_epi_to_cargo(self.current_cargo, epi_id, qtd, dias)
                messagebox.showinfo("Sucesso", "EPI vinculado à função com sucesso!")
                dialog.destroy()
                self._load_cargo_data(self.current_cargo)
            except Exception as e:
                messagebox.showerror("Erro", str(e))

        b_box = ctk.CTkFrame(dialog, fg_color="transparent")
        b_box.pack(fill="x", padx=25, pady=(0, 20))
        ctk.CTkButton(b_box, text="Cancelar", fg_color="#94A3B8", command=dialog.destroy).pack(side="left")
        ctk.CTkButton(b_box, text="Salvar no Kit", fg_color="#1E3A8A", command=submit).pack(side="right")

    def remove_selected_epi(self):
        row_id = self.table.get_selected()
        if not row_id:
            messagebox.showwarning("Aviso", "Selecione um EPI na tabela para remover do kit.")
            return
        ans = messagebox.askyesno("Confirmar Remoção", "Deseja remover este EPI do kit da função?")
        if ans:
            MatrizService.remove_epi_from_cargo(self.current_cargo, int(row_id))
            self._load_cargo_data(self.current_cargo)

    def open_deliver_kit_modal(self):
        """Modal para entrega de kit completo com assinatura e suporte a inserção retroativa para Admin."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Entregar Kit Completo de EPIs por Cargo")
        dialog.geometry("660x650")
        dialog.resizable(False, False)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 660) // 2
        y = (dialog.winfo_screenheight() - 650) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text="⚡ Entrega de Kit Completo de EPIs", font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(pady=(16, 4))
        ctk.CTkLabel(dialog, text="O sistema entregará todos os itens obrigatórios da função em uma única operação", font=FONT_SMALL, text_color=TEXT_MUTED).pack(pady=(0, 10))

        f = ctk.CTkScrollableFrame(dialog, fg_color="transparent", height=490)
        f.pack(fill="both", expand=True, padx=25, pady=0)

        employees = EmployeeService.list_employees(status="Ativo")
        emp_map = {f"{e['nome']} - {e['cargo']} ({e['matricula']})": e["id"] for e in employees}

        ctk.CTkLabel(f, text="Selecione o Colaborador *", font=FONT_BODY_BOLD).pack(anchor="w")
        emp_var = tk.StringVar(value=list(emp_map.keys())[0] if emp_map else "")
        emp_combo = ctk.CTkComboBox(f, values=list(emp_map.keys()), variable=emp_var, height=34)
        emp_combo.pack(fill="x", pady=(2, 10))

        # Lista de itens do kit
        lbl_itens = ctk.CTkLabel(f, text="Itens do Kit deste Cargo:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN)
        lbl_itens.pack(anchor="w")

        kit_box = ctk.CTkTextbox(f, height=110)
        kit_box.pack(fill="x", pady=(2, 10))

        def update_kit_display(*args):
            sel = emp_var.get()
            emp_id = emp_map.get(sel)
            if emp_id:
                emp = EmployeeService.get_employee(emp_id)
                kit = MatrizService.get_epis_for_cargo(emp["cargo"])
                kit_box.delete("1.0", "end")
                if not kit:
                    kit_box.insert("end", f"⚠️ Nenhum EPI vinculado ao cargo '{emp['cargo']}'.")
                else:
                    for k in kit:
                        status = "✅ Saldo OK" if k["saldo_atual"] >= k["qtd_recomendada"] else f"❌ Falta Saldo (Disp: {k['saldo_atual']})"
                        kit_box.insert("end", f"• {k['qtd_recomendada']}x {k['nome']} (C.A. {k['ca']}) — {status}\n")

        emp_var.trace_add("write", update_kit_display)
        update_kit_display()

        # Quem está entregando
        ctk.CTkLabel(f, text="Quem está Entregando? (Almoxarife / Técnico) *", font=FONT_BODY_BOLD).pack(anchor="w")
        from services.movement_service import MovementService
        ops = MovementService.get_operators() or ["Almoxarifado"]
        resp_var = tk.StringVar(value=ops[0])
        ctk.CTkComboBox(f, values=ops, variable=resp_var, height=34).pack(fill="x", pady=(2, 10))

        # Assinatura
        sig_holder = {"path": None}
        lbl_sig_status = ctk.CTkLabel(f, text="Assinatura Digital: Não coletada", font=FONT_SMALL, text_color=TEXT_MUTED)
        lbl_sig_status.pack(anchor="w", pady=(0, 4))

        def collect_sig():
            emp_id = emp_map[emp_var.get()]
            emp = EmployeeService.get_employee(emp_id)
            def on_saved(path):
                sig_holder["path"] = path
                lbl_sig_status.configure(text="✅ Assinatura Digital Coletada com Sucesso!", text_color=SUCCESS)
            SignatureDialog(dialog, employee_name=emp["nome"], on_signature_saved=on_saved)

        btn_sig = ctk.CTkButton(f, text="✍️ Coletar Assinatura Digital do Colaborador na Tela", fg_color="#6366F1", hover_color="#4F46E5", height=32, command=collect_sig)
        btn_sig.pack(anchor="w", pady=(0, 10))

        # Painel Retroativo (Exclusivo ADMIN)
        retro_kit_active_var = tk.BooleanVar(value=False)
        retro_kit_stock_var = tk.BooleanVar(value=False)
        retro_kit_date_entry = None

        if AuthService.is_admin():
            r_card = ctk.CTkFrame(f, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color="#3B82F6")
            r_card.pack(fill="x", pady=(0, 10))

            r_sub = ctk.CTkFrame(r_card, fg_color="transparent")

            def toggle_kit_retro():
                if retro_kit_active_var.get():
                    r_sub.pack(fill="x", padx=12, pady=(0, 10))
                else:
                    r_sub.pack_forget()

            chk_k_retro = ctk.CTkCheckBox(
                r_card,
                text="🛡️ Habilitar Entrega Retroativa de Kit Completo (Histórico - Admin)",
                variable=retro_kit_active_var,
                font=FONT_BODY_BOLD,
                text_color="#2563EB",
                command=toggle_kit_retro
            )
            chk_k_retro.pack(anchor="w", padx=12, pady=10)

            ctk.CTkLabel(r_sub, text="Data Específica da Entrega (DD/MM/AAAA ou AAAA-MM-DD): *", font=FONT_SMALL_BOLD, text_color=TEXT_MAIN).pack(anchor="w")
            retro_kit_date_entry = ctk.CTkEntry(r_sub, placeholder_text="Ex: 01/02/2024 ou 2024-02-01", height=32)
            retro_kit_date_entry.pack(fill="x", pady=(2, 6))

            chk_k_stock = ctk.CTkCheckBox(
                r_sub,
                text="Debitar do saldo físico atual do estoque (Desmarcado = Apenas histórico na ficha)",
                variable=retro_kit_stock_var,
                font=FONT_SMALL
            )
            chk_k_stock.pack(anchor="w", pady=(2, 4))

            ctk.CTkLabel(
                r_sub,
                text="ℹ️ Dica: Permite lançar kits completos entregues em admissões passadas sem travar pelo saldo atual.",
                font=FONT_SMALL,
                text_color=TEXT_MUTED
            ).pack(anchor="w")

        def confirm_delivery():
            try:
                emp_id = emp_map[emp_var.get()]
                resp = resp_var.get().strip()
                if not resp:
                    messagebox.showerror("Erro de Validação", "Informe quem está realizando a entrega!")
                    return

                is_retro = AuthService.is_admin() and retro_kit_active_var.get()
                dt_k = None
                descontar = True

                if is_retro:
                    dt_k = retro_kit_date_entry.get().strip() if retro_kit_date_entry else ""
                    if not dt_k:
                        messagebox.showerror("Erro de Validação", "Informe a data específica da entrega retroativa do kit!")
                        return
                    descontar = retro_kit_stock_var.get()

                MatrizService.deliver_full_kit(
                    funcionario_id=emp_id,
                    responsavel=resp,
                    motivo="Entrega Retroativa de Kit por Função (NR-6)" if is_retro else "Entrega de Kit por Função (NR-6)",
                    assinatura_path=sig_holder["path"],
                    observacao="Lançamento automático de kit retroativo" if is_retro else "Lançamento automático de kit da função",
                    data_hora=dt_k,
                    is_retroativo=is_retro,
                    descontar_estoque=descontar
                )

                if is_retro:
                    messagebox.showinfo("Lançamento Retroativo Concluído!", f"Kit completo de EPIs lançado na data {dt_k} com sucesso na ficha do colaborador!")
                else:
                    messagebox.showinfo("Sucesso!", "Kit completo de EPIs entregue e debitado do estoque com sucesso!")

                dialog.destroy()
                if self.on_refresh_dashboard:
                    self.on_refresh_dashboard()
            except Exception as ex:
                messagebox.showerror("Erro na Entrega do Kit", str(ex))

        b_box = ctk.CTkFrame(dialog, fg_color="transparent")
        b_box.pack(fill="x", padx=25, pady=(10, 16))
        ctk.CTkButton(b_box, text="Cancelar", fg_color="#94A3B8", command=dialog.destroy).pack(side="left")
        ctk.CTkButton(b_box, text="✔️ Confirmar Entrega do Kit", fg_color="#1E3A8A", height=36, command=confirm_delivery).pack(side="right")
