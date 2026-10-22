import tkinter as tk
import customtkinter as ctk
import os

from database import get_connection
from ui.components.theme import *
from ui.views.dashboard_view import DashboardView
from ui.views.inventory_view import InventoryView
from ui.views.movements_view import MovementsView
from ui.views.employees_view import EmployeesView
from ui.views.employee_sheet_view import EmployeeSheetView
from ui.views.reports_view import ReportsView
from ui.views.settings_view import SettingsView
from ui.views.matriz_view import MatrizView
from ui.views.login_view import LoginDialog
from version import VERSION, get_version_string

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configurações gerais da janela
        self.title(f"EPI Master Pro v{VERSION} - Sistema de Controle de Estoque & Fichas de EPI (NR-6)")
        self.geometry("1300x780")
        self.minsize(1050, 680)

        # Carrega preferência de tema do banco de dados (padrão Dark ou Light)
        self.current_theme = self._load_saved_theme()
        ctk.set_appearance_mode(self.current_theme)
        ctk.set_default_color_theme("blue")

        self.current_view_name = None
        self.views = {}

        self._build_layout()
        self.navigate_to("dashboard")

    def _load_saved_theme(self):
        try:
            with get_connection() as conn:
                row = conn.execute("SELECT valor FROM configuracoes WHERE chave = 'tema_app'").fetchone()
                if row and row["valor"]:
                    return row["valor"]
        except Exception:
            pass
        return "Dark"  # Padrão moderno Dark Mode

    def _save_theme(self, theme_name):
        try:
            with get_connection() as conn:
                conn.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('tema_app', ?)", (theme_name,))
                conn.commit()
        except Exception:
            pass

    def _build_layout(self):
        # Grid principal: Coluna 0 = Sidebar, Coluna 1 = Área de Conteúdo
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=240)
        self.grid_columnconfigure(1, weight=1)

        # ------------------ SIDEBAR ------------------
        self.sidebar = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, corner_radius=0, width=240)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Logo / Marca
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=18, pady=(22, 18))

        lbl_logo = ctk.CTkLabel(brand_frame, text="🛡️ EPI MASTER PRO", font=("Segoe UI", 16, "bold"), text_color=TEXT_WHITE)
        lbl_logo.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(brand_frame, text="Gestão de EPI & NR-6", font=FONT_SMALL, text_color="#94A3B8")
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Botão Rápido de Saída na Sidebar
        btn_quick_exit = ctk.CTkButton(
            self.sidebar,
            text="⚡ NOVA SAÍDA DE EPI",
            font=FONT_BODY_BOLD,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            height=40,
            corner_radius=8,
            command=lambda: self.navigate_to("movements", action="new_exit")
        )
        btn_quick_exit.pack(fill="x", padx=16, pady=(0, 16))

        # Itens de Menu
        self.menu_buttons = {}
        menu_items = [
            ("dashboard", "📊  Painel Geral"),
            ("inventory", "📦  Estoque de EPI"),
            ("movements", "📤  Saídas & Entregas"),
            ("matriz", "⚡  Kits & Matriz de EPI"),
            ("employee_sheet", "📄  Fichas de EPI (NR-6)"),
            ("employees", "👷  Funcionários"),
            ("reports", "📈  Relatórios & Filtros"),
            ("settings", "⚙️  Configurações"),
        ]

        for view_key, label_text in menu_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label_text,
                font=FONT_BODY_BOLD,
                anchor="w",
                height=38,
                corner_radius=8,
                fg_color="transparent",
                text_color="#E2E8F0",
                hover_color=SECONDARY_HOVER,
                command=lambda k=view_key: self.navigate_to(k)
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.menu_buttons[view_key] = btn

        # Rodapé da Sidebar (Usuário, Alternador de Tema e Versão)
        footer_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x", padx=16, pady=14)

        # Usuário Ativo & Botão de Trocar Usuário
        from services.auth_service import AuthService
        cur_user = AuthService.get_current_user()
        self.lbl_user_info = ctk.CTkLabel(
            footer_frame,
            text=f"👤 {cur_user['nome'][:18]} ({cur_user['perfil']})",
            font=FONT_SMALL_BOLD,
            text_color="#E2E8F0"
        )
        self.lbl_user_info.pack(anchor="w", pady=(0, 4))

        btn_trocar_user = ctk.CTkButton(
            footer_frame,
            text="🔄 Trocar Usuário / Login",
            font=FONT_SMALL,
            fg_color="transparent",
            text_color="#93C5FD",
            hover_color="#334155",
            height=24,
            command=self.open_login_dialog
        )
        btn_trocar_user.pack(anchor="w", pady=(0, 10))

        # BOTÃO MODO TV ALMOXARIFADO
        btn_tv = ctk.CTkButton(
            footer_frame,
            text="📺 Modo TV Almoxarifado",
            font=FONT_BODY_BOLD,
            fg_color="#0F766E",
            hover_color="#0D9488",
            text_color="#FFFFFF",
            height=34,
            corner_radius=6,
            command=self.open_tv_mode
        )
        btn_tv.pack(fill="x", pady=(0, 6))

        # BOTÃO ALTERNADOR DE TEMA DARK / LIGHT
        theme_icon = "☀️ Modo Claro" if self.current_theme == "Dark" else "🌙 Modo Escuro"
        self.btn_theme_toggle = ctk.CTkButton(
            footer_frame,
            text=theme_icon,
            font=FONT_BODY_BOLD,
            fg_color="#334155",
            hover_color="#475569",
            text_color="#FFFFFF",
            height=34,
            corner_radius=6,
            command=self.toggle_theme
        )
        self.btn_theme_toggle.pack(fill="x", pady=(0, 8))

        lbl_ver = ctk.CTkLabel(footer_frame, text=get_version_string(), font=FONT_SMALL, text_color="#64748B")
        lbl_ver.pack(anchor="w")

        lbl_db = ctk.CTkLabel(footer_frame, text="🟢 Banco Local SQLite", font=FONT_SMALL, text_color="#10B981")
        lbl_db.pack(anchor="w", pady=(2, 0))

        # ------------------ CONTAINER CENTRAL ------------------
        self.main_container = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

    def toggle_theme(self):
        """Alterna entre Tema Escuro e Tema Claro em tempo real."""
        if self.current_theme == "Dark":
            new_theme = "Light"
            btn_text = "🌙 Modo Escuro"
        else:
            new_theme = "Dark"
            btn_text = "☀️ Modo Claro"

        self.current_theme = new_theme
        ctk.set_appearance_mode(new_theme)
        self.btn_theme_toggle.configure(text=btn_text)
        self._save_theme(new_theme)

        # Propaga a atualização do estilo das tabelas em todas as telas
        for view in self.views.values():
            if hasattr(view, "table") and hasattr(view.table, "apply_theme"):
                view.table.apply_theme(new_theme)
            if hasattr(view, "tbl_saidas") and hasattr(view.tbl_saidas, "apply_theme"):
                view.tbl_saidas.apply_theme(new_theme)
            if hasattr(view, "tbl_alertas") and hasattr(view.tbl_alertas, "apply_theme"):
                view.tbl_alertas.apply_theme(new_theme)
            if hasattr(view, "refresh"):
                view.refresh()

    def open_login_dialog(self):
        def on_success(user):
            self.lbl_user_info.configure(text=f"👤 {user['nome'][:18]} ({user['perfil']})")
        LoginDialog(self, on_login_success=on_success)

    def open_tv_mode(self):
        from ui.views.tv_mode_view import TVModeWindow
        TVModeWindow(self)

    def navigate_to(self, view_name, **kwargs):
        """Alterna a tela visível de forma reativa e atualiza os botões da barra lateral."""
        for k, btn in self.menu_buttons.items():
            if k == view_name:
                btn.configure(fg_color="#1E3A8A", text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color="#E2E8F0")

        # Cria a tela sob demanda se ainda não existir
        if view_name not in self.views:
            if view_name == "dashboard":
                self.views[view_name] = DashboardView(self.main_container, on_navigate=self.navigate_to)
            elif view_name == "inventory":
                self.views[view_name] = InventoryView(self.main_container, on_refresh_dashboard=self._refresh_dashboard_if_exists)
            elif view_name == "movements":
                self.views[view_name] = MovementsView(self.main_container, on_refresh_dashboard=self._refresh_dashboard_if_exists)
            elif view_name == "matriz":
                self.views[view_name] = MatrizView(self.main_container, on_refresh_dashboard=self._refresh_dashboard_if_exists)
            elif view_name == "employee_sheet":
                self.views[view_name] = EmployeeSheetView(self.main_container, on_new_exit_for_employee=self._quick_exit_for_employee)
            elif view_name == "employees":
                self.views[view_name] = EmployeesView(
                    self.main_container,
                    on_view_sheet=self._view_employee_sheet_direct,
                    on_refresh_dashboard=self._refresh_dashboard_if_exists
                )
            elif view_name == "reports":
                self.views[view_name] = ReportsView(self.main_container)
            elif view_name == "settings":
                self.views[view_name] = SettingsView(self.main_container)

        # Oculta tela atual
        if self.current_view_name and self.current_view_name in self.views:
            self.views[self.current_view_name].grid_forget()

        # Exibe nova tela
        view = self.views[view_name]
        view.grid(row=0, column=0, sticky="nsew")
        self.current_view_name = view_name

        # Sincroniza tema da tela
        if hasattr(view, "table") and hasattr(view.table, "apply_theme"):
            view.table.apply_theme(self.current_theme)

        if hasattr(view, "refresh"):
            view.refresh()

        # Ações contextuais disparadas por atalhos
        action = kwargs.get("action")
        if action == "new_exit" and view_name == "movements":
            emp_id = kwargs.get("employee_id")
            is_retro = kwargs.get("is_retroativo", False)
            self.after(100, lambda: view.open_exit_modal(preselected_employee_id=emp_id, is_retroativo=is_retro))
        elif action == "new_entry" and view_name == "inventory":
            if "movements" in self.views:
                self.after(100, self.views["movements"].open_entry_modal)
            else:
                self.navigate_to("movements")
                self.after(100, self.views["movements"].open_entry_modal)
        elif action == "new_epi" and view_name == "inventory":
            self.after(100, view.open_new_modal)

    def _refresh_dashboard_if_exists(self):
        if "dashboard" in self.views:
            self.views["dashboard"].refresh()

    def _view_employee_sheet_direct(self, emp_id):
        self.navigate_to("employee_sheet")
        sheet_view = self.views["employee_sheet"]
        sheet_view.load_employees()
        sheet_view.select_employee_by_id(emp_id)

    def _quick_exit_for_employee(self, emp_id, is_retroativo=False):
        if self.current_view_name == "employee_sheet":
            sheet_view = self.views.get("employee_sheet")
            if sheet_view:
                sheet_view.select_employee_by_id(emp_id)
                sheet_view._open_direct_delivery(is_retroativo=is_retroativo)
                return
        self.navigate_to("movements", action="new_exit", employee_id=emp_id, is_retroativo=is_retroativo)
