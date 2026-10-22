import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import os
from datetime import datetime, timedelta

from services.employee_service import EmployeeService
from services.pdf_service import PDFService
from services.auth_service import AuthService
from ui.components.theme import *
from ui.components.table_view import StyledTable

class EmployeeSheetView(ctk.CTkFrame):
    def __init__(self, parent, on_new_exit_for_employee=None):
        super().__init__(parent, fg_color="transparent")
        self.on_new_exit_for_employee = on_new_exit_for_employee
        self.current_employee = None
        self.current_items = []
        self._build_ui()
        self.load_employees()

    def _build_ui(self):
        # Cabeçalho
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(20, 15))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(title_box, text="Ficha Individual de EPI (NR-6)", font=FONT_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Histórico legal e controle de entrega de equipamentos de proteção por colaborador", font=FONT_BODY, text_color=TEXT_MUTED).pack(anchor="w")

        # Botões de ação principais no cabeçalho organizados em duas linhas elegantes
        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")

        # Linha 1: Ações Principais da Ficha
        btn_row1 = ctk.CTkFrame(btn_box, fg_color="transparent")
        btn_row1.pack(anchor="e", pady=(0, 4))

        self.btn_print_pdf = ctk.CTkButton(
            btn_row1,
            text="🖨️ Gerar Ficha PDF (NR-6)",
            font=FONT_BODY_BOLD,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=32,
            command=self._generate_pdf
        )
        self.btn_print_pdf.pack(side="left", padx=3)

        self.btn_whatsapp = ctk.CTkButton(
            btn_row1,
            text="💬 Enviar WhatsApp",
            font=FONT_BODY_BOLD,
            fg_color="#16A34A",
            hover_color="#15803D",
            height=32,
            command=self._send_whatsapp_sheet
        )
        self.btn_whatsapp.pack(side="left", padx=3)

        self.btn_devolver = ctk.CTkButton(
            btn_row1,
            text="🔄 Devolução de EPI",
            font=FONT_BODY_BOLD,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            height=32,
            command=self._open_devolucao_modal
        )
        self.btn_devolver.pack(side="left", padx=3)

        # Linha 2: Gestão de Lançamentos e Folha em Branco
        btn_row2 = ctk.CTkFrame(btn_box, fg_color="transparent")
        btn_row2.pack(anchor="e")

        self.btn_print_blank = ctk.CTkButton(
            btn_row2,
            text="📄 Folha em Branco",
            font=FONT_BODY,
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=30,
            command=self._generate_blank_pdf
        )
        self.btn_print_blank.pack(side="left", padx=3)

        if AuthService.is_admin():
            self.btn_edit_entrega = ctk.CTkButton(
                btn_row2,
                text="✏️ Editar Entrega",
                font=FONT_BODY,
                fg_color="#D97706",
                hover_color="#B45309",
                height=30,
                command=self._edit_selected_delivery
            )
            self.btn_edit_entrega.pack(side="left", padx=3)

            self.btn_del_entrega = ctk.CTkButton(
                btn_row2,
                text="🗑️ Excluir Entrega",
                font=FONT_BODY,
                fg_color="#B91C1C",
                hover_color="#991B1B",
                height=30,
                command=self._delete_selected_delivery
            )
            self.btn_del_entrega.pack(side="left", padx=3)

        # Barra de Seleção do Colaborador
        selector_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        selector_card.pack(fill="x", padx=25, pady=(0, 15))

        s_inner = ctk.CTkFrame(selector_card, fg_color="transparent")
        s_inner.pack(fill="x", padx=15, pady=12)

        ctk.CTkLabel(s_inner, text="👤 Selecionar Colaborador:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(side="left", padx=(0, 10))

        self.emp_var = tk.StringVar()
        self.emp_combo = ctk.CTkComboBox(
            s_inner,
            values=["Carregando..."],
            variable=self.emp_var,
            width=380,
            height=34,
            command=self._on_employee_selected
        )
        self.emp_combo.pack(side="left", padx=(0, 15))

        self.btn_quick_exit = ctk.CTkButton(
            s_inner,
            text="➕ Nova Entrega p/ este Colaborador",
            font=FONT_BODY,
            fg_color="#0D9488",
            hover_color="#0F766E",
            height=34,
            command=self._quick_exit
        )
        self.btn_quick_exit.pack(side="left")

        if AuthService.is_admin():
            self.btn_retro = ctk.CTkButton(
                s_inner,
                text="📅 Inserir EPI Retroativo",
                font=FONT_BODY,
                fg_color="#4F46E5",
                hover_color="#4338CA",
                height=34,
                command=self._quick_retro_exit
            )
            self.btn_retro.pack(side="left", padx=(10, 0))

        # Card de Informações Cadastrais do Colaborador (Linha 1: Dados contratuais | Linha 2: Contato & Grade de Tamanhos)
        self.info_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        self.info_card.pack(fill="x", padx=25, pady=(0, 15))
        self.info_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.lbl_matricula = self._add_info_field(self.info_card, 0, "MATRÍCULA", "-", row=0)
        self.lbl_cargo = self._add_info_field(self.info_card, 1, "FUNÇÃO / CARGO", "-", row=0)
        self.lbl_depto = self._add_info_field(self.info_card, 2, "SETOR / DEPARTAMENTO", "-", row=0)
        self.lbl_admissao = self._add_info_field(self.info_card, 3, "DATA ADMISSÃO / STATUS", "-", row=0)

        self.lbl_tel = self._add_info_field(self.info_card, 0, "📱 WHATSAPP / CONTATO", "-", row=1)
        self.lbl_calcado = self._add_info_field(self.info_card, 1, "👟 NÚMERO CALÇADO", "-", row=1)
        self.lbl_luva_uni = self._add_info_field(self.info_card, 2, "🧤 LUVA / 👕 UNIFORME", "-", row=1)
        self.lbl_masc = self._add_info_field(self.info_card, 3, "😷 MÁSCARA / RESPIRADOR", "-", row=1)

        # Tabela da Ficha de EPI
        tbl_box = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        tbl_box.pack(fill="both", expand=True, padx=25, pady=(0, 20))

        tbl_header = ctk.CTkFrame(tbl_box, fg_color="transparent")
        tbl_header.pack(fill="x", padx=15, pady=(12, 6))

        ctk.CTkLabel(tbl_header, text="Histórico de EPIs Recebidos (Termo de Cautela)", font=FONT_SECTION, text_color=TEXT_MAIN).pack(side="left")
        self.items_count_lbl = ctk.CTkLabel(tbl_header, text="0 itens entregues", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.items_count_lbl.pack(side="right")

        cols = [
            {"id": "data", "text": "Data / Hora", "width": 120, "anchor": "center"},
            {"id": "tipo", "text": "Tipo", "width": 80, "anchor": "center"},
            {"id": "codigo", "text": "Código", "width": 70, "anchor": "center"},
            {"id": "nome", "text": "Descrição do Equipamento (EPI)", "width": 200, "anchor": "w"},
            {"id": "ca", "text": "C.A.", "width": 65, "anchor": "center"},
            {"id": "validade", "text": "Validade / Vida Útil", "width": 115, "anchor": "center"},
            {"id": "fab_tam", "text": "Fabr. / Tam.", "width": 115, "anchor": "w"},
            {"id": "qtd", "text": "Qtd", "width": 50, "anchor": "center"},
            {"id": "valor", "text": "Valor Unit.", "width": 80, "anchor": "center"},
            {"id": "assinatura", "text": "Assinatura", "width": 85, "anchor": "center"},
            {"id": "motivo", "text": "Motivo", "width": 125, "anchor": "w"},
            {"id": "resp", "text": "Quem Entregou", "width": 130, "anchor": "w"},
            {"id": "obs", "text": "Observações", "width": 130, "anchor": "w"},
        ]
        self.table = StyledTable(
            tbl_box,
            columns=cols,
            on_double_click=lambda row_id: self._edit_delivery_by_id(row_id) if AuthService.is_admin() else None
        )
        self.table.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _edit_selected_delivery(self):
        if not AuthService.is_admin():
            messagebox.showwarning("Acesso Negado", "Apenas Administradores têm permissão para editar lançamentos.")
            return
        selected_id = self.table.get_selected()
        if not selected_id:
            messagebox.showwarning("Aviso", "Selecione uma entrega na tabela para editar.")
            return
        self._edit_delivery_by_id(selected_id)

    def _edit_delivery_by_id(self, movement_id):
        if not AuthService.is_admin():
            return
        from ui.views.movements_view import open_edit_movement_dialog
        def _on_success():
            if self.current_employee:
                self._load_sheet_for_employee(self.current_employee["id"])
        open_edit_movement_dialog(self, movement_id, on_success=_on_success)

    def _delete_selected_delivery(self):
        if not AuthService.is_admin():
            messagebox.showwarning("Acesso Negado", "Apenas Administradores têm permissão para excluir lançamentos.")
            return
        selected_id = self.table.get_selected()
        if not selected_id:
            messagebox.showwarning("Aviso", "Selecione uma entrega na tabela para excluir.")
            return
        from ui.views.movements_view import confirm_and_delete_movement_dialog
        def _on_success():
            if self.current_employee:
                self._load_sheet_for_employee(self.current_employee["id"])
        confirm_and_delete_movement_dialog(self, selected_id, on_success=_on_success)

    def _add_info_field(self, parent, col, title, value, row=0):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=col, sticky="nsew", padx=12, pady=6)

        ctk.CTkLabel(f, text=title, font=FONT_SMALL_BOLD, text_color=TEXT_MUTED).pack(anchor="w")
        lbl = ctk.CTkLabel(f, text=value, font=FONT_BODY_BOLD, text_color=TEXT_MAIN)
        lbl.pack(anchor="w", pady=(2, 0))
        return lbl

    def _send_whatsapp_sheet(self):
        if not self.current_employee:
            messagebox.showwarning("Aviso", "Selecione um colaborador primeiro!")
            return

        emp = self.current_employee
        phone = emp.get("telefone") or ""

        pending = EmployeeService.get_employee_pending_epis(emp["id"])

        from services.whatsapp_service import WhatsAppService
        import urllib.parse

        clean_p = WhatsAppService.clean_phone(phone)

        lines = [
            "🛡️ *EXTRATO INDIVIDUAL DE CAUTELA DE EPI (NR-6)*\n",
            f"Olá, *{emp['nome']}* (RE: {emp['matricula']})!",
            f"🏢 Cargo/Setor: {emp['cargo']} ({emp['departamento']})\n",
            "*Equipamento(s) Atualmente sob sua Guarda e Responsabilidade:*"
        ]

        if pending:
            for p in pending:
                lines.append(f"• *{p['epi_nome']}* (C.A. {p['epi_ca']}) - {p['quantidade_pendente']} {p['epi_unidade']}")
        else:
            lines.append("• Nenhum EPI pendente de devolução no momento. Situação 100% quitada.")

        lines.extend([
            "",
            "⚠️ _Lembramos que o uso e a guarda responsável do EPI são obrigações legais do trabalhador conforme a NR-6._",
            "Para reposições, trocas periódicas ou dúvidas, procure a equipe do Almoxarifado / SST.",
            "Tenha um excelente expediente!"
        ])

        msg_encoded = urllib.parse.quote("\n".join(lines))
        url = f"https://wa.me/{clean_p}?text={msg_encoded}" if clean_p else f"https://web.whatsapp.com/send?text={msg_encoded}"
        WhatsAppService.send_via_whatsapp(url)

    def load_employees(self):
        self.employees = EmployeeService.list_employees()
        if not self.employees:
            self.emp_combo.configure(values=["Nenhum colaborador cadastrado"])
            return

        self.emp_map = {f"{e['nome']} - {e['cargo']} ({e['matricula']})": e["id"] for e in self.employees}
        keys = list(self.emp_map.keys())
        self.emp_combo.configure(values=keys)
        if keys:
            self.emp_var.set(keys[0])
            self._load_sheet_for_employee(self.emp_map[keys[0]])

    def _on_employee_selected(self, choice):
        emp_id = self.emp_map.get(choice)
        if emp_id:
            self._load_sheet_for_employee(emp_id)

    def select_employee_by_id(self, emp_id):
        for k, v in self.emp_map.items():
            if v == emp_id:
                self.emp_var.set(k)
                self._load_sheet_for_employee(emp_id)
                break

    def _load_sheet_for_employee(self, emp_id):
        if hasattr(self, "table"):
            self.table.apply_theme(ctk.get_appearance_mode())

        self.current_employee = EmployeeService.get_employee(emp_id)
        if not self.current_employee:
            return

        e = self.current_employee
        self.lbl_matricula.configure(text=e["matricula"])
        self.lbl_cargo.configure(text=e["cargo"])
        self.lbl_depto.configure(text=e["departamento"])
        status_text = f"{e.get('data_admissao') or 'N/D'}  |  {e['status']}"
        self.lbl_admissao.configure(text=status_text)
        self.lbl_tel.configure(text=e.get("telefone") or "Não informado")
        self.lbl_calcado.configure(text=f"Nº {e.get('tamanho_calcado')}" if e.get('tamanho_calcado') else "-")
        luva_str = e.get("tamanho_luva") or "-"
        uni_str = e.get("tamanho_uniforme") or "-"
        self.lbl_luva_uni.configure(text=f"Luva: {luva_str} | Uniforme: {uni_str}")
        self.lbl_masc.configure(text=e.get("tamanho_mascara") or "-")

        self.current_items = EmployeeService.get_employee_sheet(emp_id)
        self.table.clear()

        for item in self.current_items:
            dt = item["data_hora"]
            try:
                dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass

            t_raw = item["tipo"]
            mov_est = str(item.get("mov_estado") or "").upper()
            is_nao_dev = t_raw in ("NÃO DEVOLVIDO", "EXTRAVIO_DEMISSAO") or "NÃO DEVOLV" in mov_est or "NAO DEVOLV" in mov_est or "RETIDO" in mov_est

            tag = "even"
            if is_nao_dev:
                tipo_display = "🚨 NÃO DEV."
                tag = "danger"
            elif t_raw == "SAIDA":
                tipo_display = "SAIDA"
                tag = "odd"
            elif t_raw == "DEVOLUCAO":
                tipo_display = "DEVOLUCAO"
                tag = "success"
            else:
                tipo_display = t_raw

            val_u = float(item.get("custo_unitario") or item.get("valor_unitario") or item.get("epi_preco") or 0.0)
            val_u_str = f"R$ {val_u:.2f}" if val_u > 0 else "-"

            tam_disp = (item.get("tamanho") or item.get("mov_tamanho") or item.get("epi_tamanho") or "-").strip()
            if "," in tam_disp and self.current_employee:
                c_uni = str(self.current_employee.get("tamanho_uniforme") or "").strip()
                c_calc = str(self.current_employee.get("tamanho_calcado") or "").strip()
                c_luva = str(self.current_employee.get("tamanho_luva") or "").strip()
                cands = [c.strip() for c in tam_disp.split(",") if c.strip()]
                matched = None
                for c in cands:
                    if c_uni and c_uni not in ("-", "") and c.upper() == c_uni.upper():
                        matched = c
                        break
                    if c_calc and c_calc not in ("-", "") and c.upper() == c_calc.upper():
                        matched = c
                        break
                    if c_luva and c_luva not in ("-", "") and c.upper() == c_luva.upper():
                        matched = c
                        break
                tam_disp = matched if matched else "Único"
            elif "," in tam_disp:
                tam_disp = "Único"
            fab_name = item.get("epi_fabricante") or "-"
            fab_tam = f"{fab_name} / {tam_disp}"
            sig_status = "✔️ Assinado" if item.get("assinatura_path") else "Pendente"

            vida_util = int(item.get("dias_vida_util") or 0)
            if vida_util > 0:
                raw_dt_val = str(item.get("data_hora") or "")
                try:
                    dt_base = datetime.strptime(raw_dt_val[:10], "%Y-%m-%d").date()
                except Exception:
                    try:
                        dt_base = datetime.strptime(raw_dt_val[:10], "%d/%m/%Y").date()
                    except Exception:
                        dt_base = datetime.now().date()
                dt_exp = dt_base + timedelta(days=vida_util)
                mes_lbl = f"{vida_util // 30}m" if (vida_util % 30 == 0 and vida_util >= 30) else f"{vida_util}d"
                val_str = f"{dt_exp.strftime('%d/%m/%Y')} ({mes_lbl})"
            else:
                val_str = "Indeterminada"

            est_raw = str(item.get("mov_estado") or item.get("estado_conservacao") or "NOVO").upper()
            if any(k in est_raw for k in ["USADO", "REUTIL", "BOM", "HIGIEN"]):
                cond_tag = "USADO"
            elif any(k in est_raw for k in ["RUIM", "MANUT"]):
                cond_tag = "MANUTENÇÃO"
            elif any(k in est_raw for k in ["DESC", "SUCATA"]):
                cond_tag = "DESCARTE"
            elif is_nao_dev:
                cond_tag = "RETIDO"
            else:
                cond_tag = "NOVO"

            epi_nome_display = f"{item['epi_nome']}  [{cond_tag}]"

            self.table.insert_row(
                item["id"],
                [
                    dt,
                    tipo_display,
                    item["epi_codigo"],
                    epi_nome_display,
                    item["epi_ca"],
                    val_str,
                    fab_tam,
                    f"{item['quantidade']} {item['epi_unidade']}",
                    val_u_str,
                    sig_status,
                    item["motivo"],
                    item["responsavel_entrega"],
                    item.get("observacao") or ""
                ],
                tag=tag
            )

        self.items_count_lbl.configure(text=f"{len(self.current_items)} entregas registradas")

    def refresh(self):
        """Atualiza a lista de colaboradores e a ficha atual."""
        if self.current_employee:
            self._load_sheet_for_employee(self.current_employee["id"])
        else:
            self.load_employees()

    def _open_direct_delivery(self, is_retroativo=False):
        """Abre modal de saída de EPI diretamente na Ficha do Colaborador, sem mudar de aba."""
        if not self.current_employee:
            messagebox.showwarning("Aviso", "Selecione um colaborador primeiro.")
            return
        from ui.views.movements_view import MovementsView
        emp_id = self.current_employee["id"]
        MovementsView.open_exit_modal(
            self,
            preselected_employee_id=emp_id,
            is_retroativo=is_retroativo,
            on_success=lambda: self._load_sheet_for_employee(emp_id)
        )

    def _quick_exit(self):
        self._open_direct_delivery(is_retroativo=False)

    def _quick_retro_exit(self):
        self._open_direct_delivery(is_retroativo=True)

    def _generate_pdf(self):
        if not self.current_employee:
            messagebox.showwarning("Aviso", "Selecione um colaborador primeiro.")
            return

        try:
            pdf_path = PDFService.generate_employee_sheet_pdf(self.current_employee, self.current_items)
            ans = messagebox.askyesno(
                "Ficha de EPI Gerada",
                f"A Ficha de EPI NR-6 do colaborador {self.current_employee['nome']} foi gerada com sucesso!\n\nArquivo:\n{pdf_path}\n\nDeseja abrir agora para visualizar e imprimir?"
            )
            if ans:
                os.startfile(pdf_path)
        except Exception as e:
            messagebox.showerror("Erro ao Gerar Ficha", str(e))

    def _generate_blank_pdf(self):
        if not self.current_employee:
            messagebox.showwarning("Aviso", "Selecione um colaborador primeiro.")
            return

        try:
            pdf_path = PDFService.generate_employee_sheet_pdf(
                self.current_employee,
                items=[],
                only_blank=True,
                sheet_title="Continuação / Em Branco"
            )
            ans = messagebox.askyesno(
                "Folha de Continuação Gerada",
                f"A Folha em Branco (Continuação) do colaborador {self.current_employee['nome']} foi gerada com sucesso!\n\nArquivo:\n{pdf_path}\n\nDeseja abrir agora para visualizar e imprimir?"
            )
            if ans:
                os.startfile(pdf_path)
        except Exception as e:
            messagebox.showerror("Erro ao Gerar Folha em Branco", str(e))

    def _open_devolucao_modal(self):
        """Abre modal interativo para devolução e quitação de EPIs com assinatura."""
        if not self.current_employee:
            messagebox.showwarning("Aviso", "Selecione um colaborador primeiro para registrar a devolução.")
            return

        from services.devolucao_service import DevolucaoService
        from ui.components.signature_pad import SignatureDialog

        emp_id = self.current_employee["id"]
        emp_nome = self.current_employee["nome"]
        active_epis = DevolucaoService.get_employee_active_epis(emp_id)

        if not active_epis:
            messagebox.showinfo("Sem Pendências", f"O colaborador {emp_nome} não possui nenhum EPI pendente de devolução em sua custódia.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Devolução & Quitação de EPI - {emp_nome}")
        dialog.geometry("960x700")
        dialog.minsize(920, 620)
        dialog.resizable(True, True)
        dialog.grab_set()

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 960) // 2
        y = (dialog.winfo_screenheight() - 700) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text=f"🔄 Devolução & Baixa de EPIs: {emp_nome}", font=FONT_SUBTITLE, text_color=TEXT_MAIN).pack(pady=(12, 2))

        # Seletor de Modo: Devolução Regular vs Não Devolução na Demissão
        tipo_registro_var = tk.StringVar(value="DEVOLUCAO")

        mode_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        mode_frame.pack(fill="x", padx=20, pady=(4, 10))

        btn_modo_dev = ctk.CTkButton(
            mode_frame,
            text="🟢 Devolução Regular (EPIs Devolvidos)",
            font=FONT_BODY_BOLD,
            height=32,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8"
        )
        btn_modo_dev.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_modo_falta = ctk.CTkButton(
            mode_frame,
            text="🚨 NÃO DEVOLUÇÃO NA DEMISSÃO / EXTRAVIO (Colaborador Ausente)",
            font=FONT_BODY_BOLD,
            height=32,
            fg_color="#334155",
            hover_color="#475569"
        )
        btn_modo_falta.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Banner de Prejuízo Financeiro (quando em modo falta)
        banner_prejuizo = ctk.CTkFrame(dialog, fg_color="#FEE2E2", corner_radius=6, border_width=1, border_color="#EF4444")
        lbl_prejuizo_txt = ctk.CTkLabel(
            banner_prejuizo,
            text="💰 Prejuízo Financeiro Apurado: R$ 0,00 | Valor sujeito a desconto em rescisão (CLT Art. 462 § 1º)",
            font=FONT_BODY_BOLD,
            text_color="#991B1B"
        )
        lbl_prejuizo_txt.pack(padx=10, pady=6)

        # Quadro de parâmetros gerais da devolução
        top_f = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        top_f.pack(fill="x", padx=20, pady=(0, 8))
        top_f.grid_columnconfigure((0, 1), weight=1)

        # Motivo
        m_box = ctk.CTkFrame(top_f, fg_color="transparent")
        m_box.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(m_box, text="Motivo do Registro:", font=FONT_BODY_BOLD).pack(anchor="w")
        motivos_dev = [
            "Demissão / Desligamento da Empresa",
            "Substituição por Desgaste Natural",
            "Troca por Danificação / Quebra",
            "Mudança de Função / Setor",
            "Devolução de Excedente"
        ]
        motivos_falta = [
            "Demissão sem Devolução de EPI (Ausência / Recusa)",
            "Abandono de Emprego com Retenção de EPI",
            "Extravio / Perda de EPI pelo Colaborador"
        ]
        motivo_var = tk.StringVar(value=motivos_dev[0])
        motivo_combo = ctk.CTkComboBox(m_box, values=motivos_dev, variable=motivo_var, height=32)
        motivo_combo.pack(fill="x", pady=(2, 0))

        # Responsável
        r_box = ctk.CTkFrame(top_f, fg_color="transparent")
        r_box.grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(r_box, text="Quem está Registrando (Almoxarifado):", font=FONT_BODY_BOLD).pack(anchor="w")
        from services.auth_service import AuthService
        cur_u = AuthService.get_current_user().get("nome", "Almoxarifado")
        resp_entry = ctk.CTkEntry(r_box, height=32)
        resp_entry.insert(0, cur_u)
        resp_entry.pack(fill="x", pady=(2, 0))

        # Lista com Scroll de Itens sob custódia
        list_card = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        list_card.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        ctk.CTkLabel(list_card, text="Equipamentos sob custódia do colaborador:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", padx=12, pady=(6, 2))

        scroll_items = ctk.CTkScrollableFrame(list_card, fg_color="transparent", height=200)
        scroll_items.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        row_widgets = []
        estados_opts = [
            "✅ Bom / Reutilizável (Volta ao Estoque)",
            "⚠️ Ruim (Necessita Manutenção / Higienização)",
            "❌ Inservível / Descarte (Sucata / Descartado)",
            "🚨 Não Devolvido / Retido"
        ]

        for item in active_epis:
            card = ctk.CTkFrame(scroll_items, fg_color="#1E293B", corner_radius=6, border_width=1, border_color="#334155")
            card.pack(fill="x", pady=4, padx=4)

            # Controles à Direita (Fixo, nunca espreme nem quebra)
            right_box = ctk.CTkFrame(card, fg_color="transparent")
            right_box.pack(side="right", padx=(8, 10), pady=8)

            # Estado de conservação
            est_var = tk.StringVar(value=estados_opts[0])
            est_combo = ctk.CTkComboBox(right_box, values=estados_opts, variable=est_var, width=220, height=30, font=FONT_SMALL)
            est_combo.pack(side="right", padx=(6, 0))

            # Quantidade com label
            q_var = tk.StringVar(value=str(item["saldo_com_funcionario"]))
            q_ent = ctk.CTkEntry(right_box, textvariable=q_var, width=45, height=30, font=FONT_BODY_BOLD, justify="center")
            q_ent.pack(side="right", padx=(4, 0))
            ctk.CTkLabel(right_box, text="Qtd:", font=FONT_SMALL_BOLD).pack(side="right", padx=(6, 0))

            # Valor Unitário com label
            preco_init = float(item.get("epi_preco", 0.0) or 0.0)
            v_var = tk.StringVar(value=f"{preco_init:.2f}")
            v_ent = ctk.CTkEntry(right_box, textvariable=v_var, width=65, height=30, font=FONT_BODY, justify="center")
            v_ent.pack(side="right", padx=(4, 0))
            ctk.CTkLabel(right_box, text="Valor R$:", font=FONT_SMALL_BOLD).pack(side="right", padx=(6, 0))

            # Informações do EPI à Esquerda (Expansível)
            left_box = ctk.CTkFrame(card, fg_color="transparent")
            left_box.pack(side="left", fill="both", expand=True, padx=(10, 6), pady=6)

            chk_var = tk.BooleanVar(value=True)
            preco_unit = preco_init
            tam_str = (item.get("tamanho") or item.get("epi_tamanho") or "").strip()
            if "," in tam_str:
                tam_str = tam_str.split(",")[0].strip()
            tam_badge = f" (Tam: {tam_str})" if tam_str and tam_str.upper() not in ("ÚNICO", "UNICO", "-") else ""
            chk_txt = f"{item['epi_codigo']} - {item['epi_nome']}{tam_badge}"
            chk = ctk.CTkCheckBox(left_box, text=chk_txt, variable=chk_var, font=FONT_BODY_BOLD)
            chk.pack(anchor="w", pady=(0, 2))

            sub_txt = f"🛡️ C.A. {item['epi_ca']}   |   📦 Em Custódia: {item['saldo_com_funcionario']} {item['epi_unidade']}   |   💵 Cadastrado: R$ {preco_unit:.2f}"
            lbl_sub = ctk.CTkLabel(left_box, text=sub_txt, font=FONT_SMALL, text_color=TEXT_MUTED)
            lbl_sub.pack(anchor="w", padx=(28, 0))

            row_widgets.append({
                "item": item,
                "chk": chk_var,
                "qtd_var": q_var,
                "valor_var": v_var,
                "estado_var": est_var,
                "est_combo": est_combo,
                "preco_unit": preco_unit
            })

        # Rodapé do Modal (Assinatura e Botão de Finalizar)
        bot_f = ctk.CTkFrame(dialog, fg_color="transparent")
        bot_f.pack(fill="x", padx=20, pady=(0, 12))

        sig_path_holder = {"path": None}
        lbl_sig_status = ctk.CTkLabel(bot_f, text="⚠️ Assinatura pendente", font=FONT_SMALL_BOLD, text_color=WARNING)
        lbl_sig_status.pack(side="left", padx=5)

        def coletar_assinatura():
            def on_sig_done(p):
                sig_path_holder["path"] = p
                lbl_sig_status.configure(text="✅ Assinatura Capturada!", text_color=SUCCESS)
            from ui.components.signature_pad import SignatureDialog
            SignatureDialog(dialog, employee_name=emp_nome, on_signature_saved=on_sig_done)

        btn_sig = ctk.CTkButton(
            bot_f,
            text="✍️ Coletar Assinatura do Colaborador",
            fg_color="#0F766E",
            hover_color="#115E59",
            height=34,
            command=coletar_assinatura
        )
        btn_sig.pack(side="left", padx=10)

        def calcular_prejuizo_total():
            total = 0.0
            for rw in row_widgets:
                if rw["chk"].get():
                    try:
                        q_val = int(rw["qtd_var"].get().strip())
                        try:
                            v_val = float(rw["valor_var"].get().strip().replace(",", "."))
                        except ValueError:
                            v_val = rw["preco_unit"]
                        total += q_val * v_val
                    except ValueError:
                        pass
            return total

        def set_modo_regular():
            tipo_registro_var.set("DEVOLUCAO")
            btn_modo_dev.configure(fg_color="#1E3A8A", hover_color="#1D4ED8")
            btn_modo_falta.configure(fg_color="#334155", hover_color="#475569")
            motivo_combo.configure(values=motivos_dev)
            motivo_var.set(motivos_dev[0])
            banner_prejuizo.pack_forget()
            btn_sig.configure(state="normal")
            lbl_sig_status.configure(text="⚠️ Assinatura pendente", text_color=WARNING)
            btn_confirm.configure(text="✅ Confirmar Devolução e Gerar Termo", fg_color="#DC2626")
            for rw in row_widgets:
                rw["estado_var"].set(estados_opts[0])

        def set_modo_falta():
            tipo_registro_var.set("FALTA_DEMISSAO")
            btn_modo_dev.configure(fg_color="#334155", hover_color="#475569")
            btn_modo_falta.configure(fg_color="#DC2626", hover_color="#B91C1C")
            motivo_combo.configure(values=motivos_falta)
            motivo_var.set(motivos_falta[0])
            tot = calcular_prejuizo_total()
            lbl_prejuizo_txt.configure(text=f"💰 PREJUÍZO TOTAL APURADO: R$ {tot:.2f} | Valor sujeito a desconto no TRCT (CLT Art. 462 § 1º)")
            banner_prejuizo.pack(after=mode_frame, fill="x", padx=20, pady=(0, 8))
            btn_sig.configure(state="disabled")
            lbl_sig_status.configure(text="ℹ️ Colaborador ausente (dispensa de assinatura)", text_color=TEXT_MUTED)
            btn_confirm.configure(text="🚨 Confirmar Falta / Extravio e Gerar Termo TRCT", fg_color="#991B1B")
            for rw in row_widgets:
                rw["estado_var"].set(estados_opts[3])

        btn_modo_dev.configure(command=set_modo_regular)
        btn_modo_falta.configure(command=set_modo_falta)

        def finalizar_devolucao():
            itens_selecionados = []
            for rw in row_widgets:
                if rw["chk"].get():
                    try:
                        q_val = int(rw["qtd_var"].get().strip())
                        if q_val > 0:
                            try:
                                v_val = float(rw["valor_var"].get().strip().replace(",", "."))
                            except (ValueError, TypeError):
                                v_val = float(rw["preco_unit"] or 0.0)

                            itens_selecionados.append({
                                "epi_id": rw["item"]["epi_id"],
                                "epi_codigo": rw["item"]["epi_codigo"],
                                "epi_nome": rw["item"]["epi_nome"],
                                "epi_ca": rw["item"]["epi_ca"],
                                "epi_unidade": rw["item"]["epi_unidade"],
                                "epi_preco": v_val,
                                "valor_unitario": v_val,
                                "quantidade": min(q_val, rw["item"]["saldo_com_funcionario"]),
                                "estado_conservacao": rw["estado_var"].get(),
                                "tamanho": rw["item"].get("tamanho") or rw["item"].get("epi_tamanho") or "Único"
                            })
                    except ValueError:
                        pass

            if not itens_selecionados:
                messagebox.showwarning("Aviso", "Selecione ao menos um EPI!")
                return

            resp_nome = resp_entry.get().strip() or "Almoxarifado"
            mot_nome = motivo_var.get()
            is_falta = tipo_registro_var.get() == "FALTA_DEMISSAO"
            btn_confirm.configure(state="disabled", text="⏳ Registrando...")
            dialog.update_idletasks()

            try:
                if is_falta:
                    # 1. Registra como extravio / não devolução na demissão
                    res = DevolucaoService.register_unreturned_dismissal(
                        funcionario_id=emp_id,
                        items_unreturned=itens_selecionados,
                        responsavel=resp_nome,
                        motivo=mot_nome,
                        alterar_status_funcionario=True
                    )

                    # 2. Gera PDF Oficial do Termo de Não Devolução e Retenção para o TRCT / RH
                    pdf_termo = DevolucaoService.generate_termo_nao_devolucao_pdf(
                        funcionario_id=emp_id,
                        items_unreturned=itens_selecionados,
                        responsavel=resp_nome,
                        motivo=mot_nome,
                        total_prejuizo=res["total_prejuizo"]
                    )

                    dialog.destroy()
                    self._load_sheet_for_employee(emp_id)

                    ans = messagebox.askyesno(
                        "Falta de EPI Registrada!",
                        f"A NÃO devolução dos EPIs na demissão foi registrada com sucesso!\n\n"
                        f"• Prejuízo Financeiro Apurado: R$ {res['total_prejuizo']:.2f}\n"
                        f"• Status do Colaborador: Desligado (Com Pendência de EPI)\n"
                        f"• Termo Jurídico TRCT: {pdf_termo}\n\n"
                        f"Deseja abrir o Termo Oficial em PDF agora para imprimir ou anexar à rescisão?"
                    )
                    if ans:
                        os.startfile(pdf_termo)

                else:
                    # Devolução Regular
                    DevolucaoService.register_return(
                        funcionario_id=emp_id,
                        items_returned=itens_selecionados,
                        responsavel=resp_nome,
                        motivo=mot_nome,
                        assinatura_path=sig_path_holder["path"]
                    )

                    # Se o motivo for Demissão ou Desligamento, atualiza status do colaborador
                    if "demiss" in mot_nome.lower() or "deslig" in mot_nome.lower():
                        from services.employee_service import EmployeeService
                        remaining = DevolucaoService.get_employee_active_epis(emp_id)
                        if not remaining:
                            EmployeeService.update_status(emp_id, "Inativo / Desligado")
                        else:
                            EmployeeService.update_status(emp_id, "Desligado (Com Pendência de EPI)")

                    pdf_termo = DevolucaoService.generate_termo_devolucao_pdf(
                        funcionario_id=emp_id,
                        items_returned=itens_selecionados,
                        responsavel=resp_nome,
                        motivo=mot_nome,
                        assinatura_colaborador_path=sig_path_holder["path"]
                    )

                    dialog.destroy()
                    self._load_sheet_for_employee(emp_id)

                    ans = messagebox.askyesno(
                        "Devolução Concluída com Sucesso!",
                        f"A devolução dos EPIs foi registrada e o Termo Oficial de Quitação foi gerado em:\n{pdf_termo}\n\nDeseja abrir o Termo em PDF agora para visualização e arquivamento?"
                    )
                    if ans:
                        os.startfile(pdf_termo)

            except Exception as ex:
                btn_confirm.configure(state="normal", text="✅ Confirmar Devolução e Gerar Termo")
                messagebox.showerror("Erro ao Processar Registro", str(ex))

        btn_confirm = ctk.CTkButton(
            bot_f,
            text="✅ Confirmar Devolução e Gerar Termo",
            font=FONT_BODY_BOLD,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            height=34,
            command=finalizar_devolucao
        )
        btn_confirm.pack(side="right")


