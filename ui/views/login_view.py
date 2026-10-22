import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from services.auth_service import AuthService
from ui.components.theme import *

class LoginDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_login_success):
        super().__init__(parent)
        self.on_login_success = on_login_success

        self.title("Acesso ao Sistema - EPI Master Pro")
        self.geometry("420x460")
        self.resizable(False, False)
        self.grab_set()

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 420) // 2
        y = (self.winfo_screenheight() - 460) // 2
        self.geometry(f"+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        # Logo e Boas-Vindas
        ctk.CTkLabel(self, text="🛡️ EPI MASTER PRO", font=("Segoe UI", 18, "bold"), text_color="#1E3A8A").pack(pady=(25, 4))
        ctk.CTkLabel(self, text="Entre com seu usuário e senha para acessar", font=FONT_SMALL, text_color=TEXT_MUTED).pack(pady=(0, 20))

        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        card.pack(fill="both", expand=True, padx=25, pady=(0, 25))

        f = ctk.CTkFrame(card, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(f, text="Usuário / Login *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w")
        self.user_entry = ctk.CTkEntry(f, placeholder_text="Ex: admin ou almoxarife", height=36)
        self.user_entry.pack(fill="x", pady=(3, 15))
        self.user_entry.insert(0, "admin")

        ctk.CTkLabel(f, text="Senha de Acesso *", font=FONT_BODY_BOLD, text_color=TEXT_MAIN).pack(anchor="w")
        self.pass_entry = ctk.CTkEntry(f, placeholder_text="••••••••", show="•", height=36)
        self.pass_entry.pack(fill="x", pady=(3, 20))
        self.pass_entry.insert(0, "admin123")
        self.pass_entry.bind("<Return>", lambda e: self.do_login())

        btn_entrar = ctk.CTkButton(
            f,
            text="🔓 ENTRAR NO SISTEMA",
            font=FONT_BODY_BOLD,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=40,
            command=self.do_login
        )
        btn_entrar.pack(fill="x", pady=(0, 10))

        # Dica rápida de logins padrão
        ctk.CTkLabel(
            f,
            text="Padrão: admin / admin123  ou  almoxarife / 1234",
            font=FONT_SMALL,
            text_color=TEXT_MUTED
        ).pack(anchor="center")

    def do_login(self):
        user = self.user_entry.get().strip()
        pwd = self.pass_entry.get().strip()

        if not user or not pwd:
            messagebox.showwarning("Aviso", "Preencha usuário e senha!")
            return

        authenticated = AuthService.authenticate(user, pwd)
        if authenticated:
            messagebox.showinfo("Bem-vindo!", f"Olá, {authenticated['nome']}!\nPerfil de acesso: {authenticated['perfil']}")
            if self.on_login_success:
                self.on_login_success(authenticated)
            self.destroy()
        else:
            messagebox.showerror("Acesso Negado", "Usuário ou senha incorretos! Tente novamente.")
