import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import shutil
import os
from datetime import datetime

from database import get_connection, DB_FILE
from ui.components.theme import *
from ui.components.table_view import StyledTable
from services.audit_service import AuditService
from services.notification_service import NotificationService
from services.excel_service import ExcelService
from services.backup_service import BackupService

class SettingsView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        # Cabeçalho
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=25, pady=(15, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(title_box, text="Configurações & Painel Administrativo", font=FONT_TITLE, text_color=TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Parâmetros da empresa, alertas por e-mail, operadores do almoxarifado, backup e trilha de auditoria", font=FONT_BODY, text_color=TEXT_MUTED).pack(anchor="w")

        # Tabview com as 4 abas organizadas
        self.tabview = ctk.CTkTabview(self, fg_color=BG_CARD)
        self.tabview.pack(fill="both", expand=True, padx=25, pady=(0, 20))

        self.tab_empresa = self.tabview.add("🏢 Empresa & Operadores")
        self.tab_email = self.tabview.add("📧 Alertas & E-mail (SMTP)")
        self.tab_backup = self.tabview.add("💾 Backup & Restauração")
        self.tab_auditoria = self.tabview.add("🛡️ Trilha de Auditoria")

        self._build_tab_empresa()
        self._build_tab_email()
        self._build_tab_backup()
        self._build_tab_auditoria()

    # ------------------ ABA 1: EMPRESA & OPERADORES ------------------
    def _build_tab_empresa(self):
        parent = self.tab_empresa
        content = ctk.CTkFrame(parent, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=10, pady=10)
        content.grid_columnconfigure((0, 1), weight=1)
        content.grid_rowconfigure(0, weight=1)

        # Coluna Esquerda: Dados da Empresa
        card_empresa = ctk.CTkFrame(content, fg_color="transparent")
        card_empresa.grid(row=0, column=0, sticky="nsew", padx=(0, 15))

        ctk.CTkLabel(card_empresa, text="Dados da Empresa (Cabeçalho da Ficha NR-6)", font=FONT_SECTION, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(card_empresa, text="Razão Social / Nome da Empresa *", font=FONT_BODY_BOLD).pack(anchor="w", pady=(2, 2))
        self.entry_nome = ctk.CTkEntry(card_empresa, height=32)
        self.entry_nome.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(card_empresa, text="CNPJ *", font=FONT_BODY_BOLD).pack(anchor="w", pady=(2, 2))
        self.entry_cnpj = ctk.CTkEntry(card_empresa, height=32)
        self.entry_cnpj.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(card_empresa, text="Endereço Completo", font=FONT_BODY_BOLD).pack(anchor="w", pady=(2, 2))
        self.entry_end = ctk.CTkEntry(card_empresa, height=32)
        self.entry_end.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(card_empresa, text="Responsável Técnico / Setor SST", font=FONT_BODY_BOLD).pack(anchor="w", pady=(2, 2))
        self.entry_resp = ctk.CTkEntry(card_empresa, height=32)
        self.entry_resp.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(card_empresa, text="Texto do Termo de Responsabilidade e Guarda NR-6:", font=FONT_BODY_BOLD).pack(anchor="w", pady=(2, 2))
        self.txt_termo = ctk.CTkTextbox(card_empresa, height=100)
        self.txt_termo.pack(fill="x", pady=(0, 10))

        btn_save_emp = ctk.CTkButton(
            card_empresa,
            text="💾 Salvar Dados da Empresa",
            font=FONT_BODY_BOLD,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=34,
            command=self.save_company_data
        )
        btn_save_emp.pack(anchor="e")

        # Coluna Direita: Operadores & Backup
        right_f = ctk.CTkFrame(content, fg_color="transparent")
        right_f.grid(row=0, column=1, sticky="nsew", padx=(15, 0))

        ctk.CTkLabel(right_f, text="👷 Operadores do Almoxarifado (Quem entrega)", font=FONT_SECTION, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(right_f, text="Nomes sugeridos automaticamente na tela de saída:", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 8))

        f_add_op = ctk.CTkFrame(right_f, fg_color="transparent")
        f_add_op.pack(fill="x", pady=(0, 8))
        self.entry_new_op = ctk.CTkEntry(f_add_op, placeholder_text="Novo operador...", height=32)
        self.entry_new_op.pack(side="left", fill="x", expand=True, padx=(0, 6))
        btn_add_op = ctk.CTkButton(f_add_op, text="Adicionar", width=80, height=32, command=self.add_operator)
        btn_add_op.pack(side="right")

        is_dark = ctk.get_appearance_mode().lower() == "dark"
        self.ops_listbox = tk.Listbox(
            right_f,
            height=6,
            font=("Segoe UI", 10),
            bg="#1E293B" if is_dark else "#FFFFFF",
            fg="#F8FAFC" if is_dark else "#1E293B",
            selectbackground="#3B82F6",
            selectforeground="#FFFFFF",
            relief="flat",
            highlightthickness=1,
            highlightcolor="#475569" if is_dark else "#CBD5E1"
        )
        self.ops_listbox.pack(fill="x", pady=(0, 8))

        btn_del_op = ctk.CTkButton(right_f, text="Remover Selecionado", fg_color="#EF4444", hover_color="#DC2626", height=28, command=self.delete_operator)
        btn_del_op.pack(anchor="e", pady=(0, 15))

        # Backup
        card_bkp = ctk.CTkFrame(right_f, fg_color="transparent")
        card_bkp.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(card_bkp, text="🛡️ Cópia de Segurança (Backup)", font=FONT_SECTION, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))
        ctk.CTkLabel(card_bkp, text="Gere um arquivo .db com todo o banco de dados:", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 8))

        btn_bkp = ctk.CTkButton(
            card_bkp,
            text="💾 Fazer Backup do Banco de Dados",
            font=FONT_BODY_BOLD,
            fg_color="#059669",
            hover_color="#047857",
            height=34,
            command=self.backup_database
        )
        btn_bkp.pack(anchor="w")

        # Card de Informações da Versão do Sistema
        card_ver = ctk.CTkFrame(right_f, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        card_ver.pack(fill="x", pady=(15, 0), ipady=4)

        from version import APP_NAME, VERSION, BUILD_DATE, RELEASE_TAG
        ctk.CTkLabel(card_ver, text=f"ℹ️ {APP_NAME} - Informações da Versão", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w", padx=10, pady=(6, 2))
        ctk.CTkLabel(
            card_ver,
            text=f"• Versão Atual: {VERSION} (Build {BUILD_DATE})\n• Distribuição: {RELEASE_TAG}\n• Conformidade: MTE / Norma Regulamentadora NR-6\n• Armazenamento: Banco Local SQLite Portátil",
            font=FONT_SMALL,
            text_color=TEXT_MUTED,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 6))

    # ------------------ ABA 2: ALERTAS & E-MAIL (SMTP) ------------------
    def _build_tab_email(self):
        parent = self.tab_email
        f_mail = ctk.CTkFrame(parent, fg_color="transparent")
        f_mail.pack(fill="both", expand=True, padx=20, pady=15)

        ctk.CTkLabel(f_mail, text="Configuração do Servidor de Envio de E-mails (SMTP)", font=FONT_SECTION, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f_mail, text="Permite o envio automático de relatórios de estoque crítico e alertas de C.A. a vencer", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 15))

        grid_f = ctk.CTkFrame(f_mail, fg_color="transparent")
        grid_f.pack(fill="x", pady=(0, 15))
        grid_f.grid_columnconfigure((0, 1), weight=1)

        # Servidor e Porta
        s_box = ctk.CTkFrame(grid_f, fg_color="transparent")
        s_box.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=6)
        ctk.CTkLabel(s_box, text="Servidor SMTP:", font=FONT_BODY_BOLD).pack(anchor="w")
        self.entry_smtp_srv = ctk.CTkEntry(s_box, placeholder_text="smtp.gmail.com ou smtp.office365.com", height=32)
        self.entry_smtp_srv.pack(fill="x", pady=(2, 0))

        p_box = ctk.CTkFrame(grid_f, fg_color="transparent")
        p_box.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=6)
        ctk.CTkLabel(p_box, text="Porta SMTP (587 TLS / 465 SSL):", font=FONT_BODY_BOLD).pack(anchor="w")
        self.entry_smtp_porta = ctk.CTkEntry(p_box, placeholder_text="587", height=32)
        self.entry_smtp_porta.pack(fill="x", pady=(2, 0))

        # Usuário e Senha
        u_box = ctk.CTkFrame(grid_f, fg_color="transparent")
        u_box.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=6)
        ctk.CTkLabel(u_box, text="Usuário / E-mail de Envio:", font=FONT_BODY_BOLD).pack(anchor="w")
        self.entry_smtp_user = ctk.CTkEntry(u_box, placeholder_text="almoxarifado@empresa.com", height=32)
        self.entry_smtp_user.pack(fill="x", pady=(2, 0))

        pw_box = ctk.CTkFrame(grid_f, fg_color="transparent")
        pw_box.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=6)
        ctk.CTkLabel(pw_box, text="Senha de Aplicativo SMTP:", font=FONT_BODY_BOLD).pack(anchor="w")
        self.entry_smtp_pass = ctk.CTkEntry(pw_box, placeholder_text="••••••••", show="*", height=32)
        self.entry_smtp_pass.pack(fill="x", pady=(2, 0))

        # Destinatários de Alerta
        ctk.CTkLabel(f_mail, text="Destinatários dos Alertas de Segurança & Compras (separados por vírgula):", font=FONT_BODY_BOLD).pack(anchor="w", pady=(8, 2))
        self.entry_smtp_dest = ctk.CTkEntry(f_mail, placeholder_text="compras@empresa.com, seguranca@empresa.com, gerencia@empresa.com", height=32)
        self.entry_smtp_dest.pack(fill="x", pady=(0, 15))

        btn_bar = ctk.CTkFrame(f_mail, fg_color="transparent")
        btn_bar.pack(fill="x")

        btn_test_mail = ctk.CTkButton(
            btn_bar,
            text="📨 Testar Envio / Enviar Alerta Agora",
            font=FONT_BODY,
            fg_color="#0D9488",
            hover_color="#0F766E",
            height=36,
            command=self.test_email
        )
        btn_test_mail.pack(side="left")

        btn_save_mail = ctk.CTkButton(
            btn_bar,
            text="💾 Salvar Configurações de E-mail",
            font=FONT_BODY_BOLD,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=36,
            command=self.save_smtp_data
        )
        btn_save_mail.pack(side="right")

    # ------------------ ABA 3: BACKUP & RESTAURAÇÃO ------------------
    def _build_tab_backup(self):
        parent = self.tab_backup
        f_main = ctk.CTkFrame(parent, fg_color="transparent")
        f_main.pack(fill="both", expand=True, padx=15, pady=12)

        ctk.CTkLabel(f_main, text="💾 Central de Segurança: Backup & Restauração Completa", font=FONT_SECTION, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f_main, text="Crie cópias compactadas (.zip) contendo o banco de dados SQLite, históricos de entrega, PDFs emitidos e assinaturas digitais.", font=FONT_SMALL, text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 15))

        # Barra de Ações Rápidas
        actions_bar = ctk.CTkFrame(f_main, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        actions_bar.pack(fill="x", pady=(0, 15))

        inner_act = ctk.CTkFrame(actions_bar, fg_color="transparent")
        inner_act.pack(fill="x", padx=15, pady=12)

        btn_new_bkp = ctk.CTkButton(
            inner_act,
            text="💾 Criar Backup Agora (.zip)",
            font=FONT_BODY_BOLD,
            fg_color="#059669",
            hover_color="#047857",
            height=36,
            command=self.execute_create_backup
        )
        btn_new_bkp.pack(side="left", padx=(0, 10))

        btn_export_bkp = ctk.CTkButton(
            inner_act,
            text="📂 Exportar p/ Pen-drive ou Nuvem",
            font=FONT_BODY,
            fg_color="#0D9488",
            hover_color="#0F766E",
            height=36,
            command=self.execute_export_backup
        )
        btn_export_bkp.pack(side="left", padx=(0, 10))

        btn_restore = ctk.CTkButton(
            inner_act,
            text="🔄 Restaurar Sistema de Arquivo (.zip)",
            font=FONT_BODY_BOLD,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            height=36,
            command=self.execute_restore_backup
        )
        btn_restore.pack(side="left", padx=(0, 10))

        btn_open_folder = ctk.CTkButton(
            inner_act,
            text="📁 Abrir Pasta de Backups",
            font=FONT_BODY,
            fg_color="#475569",
            hover_color="#334155",
            height=36,
            command=lambda: os.startfile(BackupService.get_backup_dir())
        )
        btn_open_folder.pack(side="right")

        # Tabela de Histórico de Backups Disponíveis
        lbl_list = ctk.CTkLabel(f_main, text="Backups locais disponíveis para restauração:", font=FONT_BODY_BOLD, text_color=TEXT_MAIN)
        lbl_list.pack(anchor="w", pady=(0, 6))

        tbl_box = ctk.CTkFrame(f_main, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        tbl_box.pack(fill="both", expand=True)

        cols = [
            {"id": "arquivo", "text": "Nome do Arquivo de Backup (.zip)", "width": 380, "anchor": "w"},
            {"id": "data", "text": "Data / Hora de Criação", "width": 180, "anchor": "center"},
            {"id": "tamanho", "text": "Tamanho Compactado", "width": 140, "anchor": "center"}
        ]
        self.tbl_backups = StyledTable(tbl_box, columns=cols)
        self.tbl_backups.pack(fill="both", expand=True, padx=10, pady=10)

    def execute_create_backup(self):
        try:
            zip_path = BackupService.create_backup()
            self.refresh_backups_list()
            ans = messagebox.askyesno(
                "Backup Realizado com Sucesso!",
                f"O backup completo do sistema foi gerado em:\n{zip_path}\n\nDeseja abrir a pasta do arquivo agora?"
            )
            if ans:
                os.startfile(os.path.dirname(zip_path))
        except Exception as ex:
            messagebox.showerror("Erro no Backup", str(ex))

    def execute_export_backup(self):
        folder = filedialog.askdirectory(title="Selecione a Pasta de Destino (Pen-drive, Google Drive, OneDrive)")
        if not folder:
            return
        try:
            zip_path = BackupService.create_backup(dest_folder=folder)
            self.refresh_backups_list()
            messagebox.showinfo("Exportação Concluída", f"Backup exportado com sucesso para:\n{zip_path}")
        except Exception as ex:
            messagebox.showerror("Erro ao Exportar Backup", str(ex))

    def execute_restore_backup(self):
        fpath = filedialog.askopenfilename(
            title="Selecione o arquivo .zip de backup para restaurar",
            filetypes=[("Backup EPI Master Pro", "*.zip")]
        )
        if not fpath:
            return

        ans = messagebox.askyesno(
            "⚠️ CONFIRMAÇÃO DE RESTAURAÇÃO",
            "A restauração substituirá os dados atuais pelo conteúdo do arquivo de backup selecionado.\n\n"
            "Uma cópia de segurança prévia será mantida automaticamente.\n\n"
            "Deseja realmente continuar com a restauração?"
        )
        if not ans:
            return

        try:
            BackupService.restore_backup(fpath)
            self.load_data()
            self.refresh_backups_list()
            messagebox.showinfo(
                "Restauração Concluída!",
                "O sistema e o banco de dados foram restaurados com sucesso a partir do backup!"
            )
        except Exception as ex:
            messagebox.showerror("Falha na Restauração", str(ex))

    def refresh_backups_list(self):
        if hasattr(self, "tbl_backups"):
            self.tbl_backups.apply_theme(ctk.get_appearance_mode())
            backups = BackupService.list_backups()
            self.tbl_backups.clear()
            for b in backups:
                self.tbl_backups.insert_row(
                    b["filename"],
                    [b["filename"], b["date"], f"{b['size_mb']} MB"]
                )

    # ------------------ ABA 4: TRILHA DE AUDITORIA ------------------
    def _build_tab_auditoria(self):
        parent = self.tab_auditoria
        f_audit = ctk.CTkFrame(parent, fg_color="transparent")
        f_audit.pack(fill="both", expand=True, padx=10, pady=10)

        # Filtros
        filt_f = ctk.CTkFrame(f_audit, fg_color="transparent")
        filt_f.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(filt_f, text="🔍 Buscar:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 5))
        self.audit_search_var = tk.StringVar()
        self.audit_search_entry = ctk.CTkEntry(filt_f, placeholder_text="Usuário, ação, detalhes...", textvariable=self.audit_search_var, width=280, height=32)
        self.audit_search_entry.pack(side="left", padx=(0, 15))
        self.audit_search_entry.bind("<KeyRelease>", lambda e: self.refresh_audit_logs())

        ctk.CTkLabel(filt_f, text="Módulo:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED).pack(side="left", padx=(0, 5))
        self.audit_mod_var = tk.StringVar(value="TODOS")
        self.audit_mod_combo = ctk.CTkComboBox(
            filt_f,
            values=["TODOS", "ESTOQUE", "FUNCIONARIOS", "MOVIMENTACOES", "MATRIZ", "CONFIGURACOES"],
            variable=self.audit_mod_var,
            width=150,
            height=32,
            command=lambda v: self.refresh_audit_logs()
        )
        self.audit_mod_combo.pack(side="left", padx=(0, 15))

        btn_refresh_audit = ctk.CTkButton(filt_f, text="🔄 Atualizar", width=80, height=32, command=self.refresh_audit_logs)
        btn_refresh_audit.pack(side="left", padx=5)

        # Tabela de Auditoria
        cols = [
            {"id": "data", "text": "Data/Hora", "width": 130, "anchor": "center"},
            {"id": "user", "text": "Usuário", "width": 140, "anchor": "w"},
            {"id": "modulo", "text": "Módulo", "width": 110, "anchor": "center"},
            {"id": "acao", "text": "Ação Realizada", "width": 150, "anchor": "w"},
            {"id": "detalhes", "text": "Detalhes / Informações Adicionais", "width": 380, "anchor": "w"},
        ]
        self.tbl_audit = StyledTable(f_audit, columns=cols, height=260)
        self.tbl_audit.pack(fill="both", expand=True)

    def refresh(self):
        self.load_data()

    def load_data(self):
        # Carrega empresa
        with get_connection() as conn:
            rows = conn.execute("SELECT chave, valor FROM configuracoes").fetchall()
            configs = {r["chave"]: r["valor"] for r in rows}

        self.entry_nome.delete(0, "end")
        self.entry_nome.insert(0, configs.get("empresa_nome", ""))

        self.entry_cnpj.delete(0, "end")
        self.entry_cnpj.insert(0, configs.get("empresa_cnpj", ""))

        self.entry_end.delete(0, "end")
        self.entry_end.insert(0, configs.get("empresa_endereco", ""))

        self.entry_resp.delete(0, "end")
        self.entry_resp.insert(0, configs.get("responsavel_seguranca", ""))

        self.txt_termo.delete("1.0", "end")
        self.txt_termo.insert("1.0", configs.get("termo_nr6", ""))

        # Carrega SMTP
        self.entry_smtp_srv.delete(0, "end")
        self.entry_smtp_srv.insert(0, configs.get("smtp_servidor", "smtp.gmail.com"))

        self.entry_smtp_porta.delete(0, "end")
        self.entry_smtp_porta.insert(0, configs.get("smtp_porta", "587"))

        self.entry_smtp_user.delete(0, "end")
        self.entry_smtp_user.insert(0, configs.get("smtp_usuario", ""))

        self.entry_smtp_pass.delete(0, "end")
        self.entry_smtp_pass.insert(0, configs.get("smtp_senha", ""))

        self.entry_smtp_dest.delete(0, "end")
        self.entry_smtp_dest.insert(0, configs.get("alerta_destinatarios", ""))

        self.refresh_operators()
        self.refresh_audit_logs()
        self.refresh_backups_list()

    def refresh_operators(self):
        self.ops_listbox.delete(0, "end")
        with get_connection() as conn:
            rows = conn.execute("SELECT nome FROM operadores WHERE ativo = 1 ORDER BY nome ASC").fetchall()
            for r in rows:
                self.ops_listbox.insert("end", r["nome"])

    def refresh_audit_logs(self):
        if hasattr(self, "tbl_audit"):
            self.tbl_audit.apply_theme(ctk.get_appearance_mode())
            s = self.audit_search_var.get().strip()
            mod = self.audit_mod_var.get().strip()
            logs = AuditService.list_logs(search=s, modulo=mod, limit=150)
            self.tbl_audit.clear()
            for l in logs:
                self.tbl_audit.insert_row(
                    l["id"],
                    [l["data_hora"], l["usuario_nome"], l["modulo"], l["acao"], l.get("detalhes") or ""]
                )

    def add_operator(self):
        nome = self.entry_new_op.get().strip()
        if not nome:
            return
        with get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO operadores (nome, cargo) VALUES (?, 'Almoxarife')", (nome,))
            conn.commit()
        AuditService.log("CRIAR_OPERADOR", "CONFIGURACOES", f"Novo operador adicionado: {nome}")
        self.entry_new_op.delete(0, "end")
        self.refresh_operators()
        self.refresh_audit_logs()

    def delete_operator(self):
        sel = self.ops_listbox.curselection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um operador na lista para remover.")
            return
        nome = self.ops_listbox.get(sel[0])
        with get_connection() as conn:
            conn.execute("UPDATE operadores SET ativo = 0 WHERE nome = ?", (nome,))
            conn.commit()
        AuditService.log("EXCLUIR_OPERADOR", "CONFIGURACOES", f"Operador desativado: {nome}")
        self.refresh_operators()
        self.refresh_audit_logs()

    def save_company_data(self):
        nome = self.entry_nome.get().strip()
        cnpj = self.entry_cnpj.get().strip()
        end = self.entry_end.get().strip()
        resp = self.entry_resp.get().strip()
        termo = self.txt_termo.get("1.0", "end").strip()

        if not nome:
            messagebox.showerror("Erro", "A Razão Social da Empresa é obrigatória!")
            return

        with get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('empresa_nome', ?)", (nome,))
            conn.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('empresa_cnpj', ?)", (cnpj,))
            conn.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('empresa_endereco', ?)", (end,))
            conn.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('responsavel_seguranca', ?)", (resp,))
            conn.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('termo_nr6', ?)", (termo,))
            conn.commit()

        AuditService.log("ATUALIZAR_EMPRESA", "CONFIGURACOES", f"Dados da empresa atualizados: {nome}")
        self.refresh_audit_logs()
        messagebox.showinfo("Sucesso", "Configurações da empresa salvas com sucesso!")

    def save_smtp_data(self):
        cfg = {
            "smtp_servidor": self.entry_smtp_srv.get().strip(),
            "smtp_porta": self.entry_smtp_porta.get().strip() or "587",
            "smtp_usuario": self.entry_smtp_user.get().strip(),
            "smtp_senha": self.entry_smtp_pass.get().strip(),
            "alerta_destinatarios": self.entry_smtp_dest.get().strip()
        }
        NotificationService.save_smtp_config(cfg)
        self.refresh_audit_logs()
        messagebox.showinfo("Configurações Salvas", "Parâmetros de SMTP e destinatários de alertas salvos com sucesso!")

    def test_email(self):
        dest = self.entry_smtp_dest.get().strip()
        if not dest:
            messagebox.showwarning("Aviso", "Informe ao menos um e-mail de destinatário!")
            return
        res = NotificationService.send_alert_email(destinatarios_custom=dest)
        self.refresh_audit_logs()
        if res.get("sucesso"):
            messagebox.showinfo("Resultado do Envio", res["mensagem"])
        else:
            messagebox.showerror("Falha no Envio", res["mensagem"])

    def backup_database(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = filedialog.asksaveasfilename(
                title="Salvar Cópia de Segurança do Banco de Dados",
                initialfile=f"backup_epi_{timestamp}.db",
                filetypes=[("Arquivo SQLite", "*.db"), ("Todos os arquivos", "*.*")]
            )
            if dest:
                shutil.copy2(DB_FILE, dest)
                AuditService.log("BACKUP_BANCO", "CONFIGURACOES", f"Backup gerado em: {os.path.basename(dest)}")
                self.refresh_audit_logs()
                messagebox.showinfo("Backup Concluído", f"Cópia de segurança criada com sucesso em:\n{dest}")
        except Exception as e:
            messagebox.showerror("Erro no Backup", str(e))
