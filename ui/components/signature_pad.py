import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import os
import uuid
from PIL import Image, ImageDraw, ImageTk
from database import SIGNATURES_DIR
from ui.components.theme import *
from services.mobile_signature_service import MobileSignatureService

class SignatureDialog(ctk.CTkToplevel):
    """
    Diálogo para Captura de Assinatura Digital do Colaborador (NR-6)
    Suporta:
    1. Assinatura na Tela (Mouse, Touch Screen, Mesa Digitalizadora)
    2. Assinatura Sem Toque pelo Celular do Funcionário (QR Code dinâmico via Wi-Fi)
    """
    def __init__(self, parent, employee_name, on_signature_saved):
        super().__init__(parent)
        self.employee_name = employee_name
        self.on_signature_saved = on_signature_saved
        self.saved_image_path = None
        self.mobile_active = False

        self.title("Assinatura Digital do Colaborador (NR-6)")
        self.geometry("560x420")
        self.resizable(False, False)
        self.grab_set()

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 560) // 2
        y = (self.winfo_screenheight() - 420) // 2
        self.geometry(f"+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()

    def _on_close(self):
        MobileSignatureService.stop_session()
        self.destroy()

    def _build_ui(self):
        # Cabeçalho
        ctk.CTkLabel(
            self,
            text=f"✍️ Coleta de Assinatura: {self.employee_name}",
            font=FONT_SUBTITLE,
            text_color=TEXT_MAIN
        ).pack(pady=(14, 2))

        self.lbl_instruction = ctk.CTkLabel(
            self,
            text="Assine no quadro abaixo ou clique em '📱 Assinar pelo Celular' para escanear QR Code",
            font=FONT_SMALL,
            text_color=TEXT_MUTED
        )
        self.lbl_instruction.pack(pady=(0, 10))

        # Container Central que alterna entre Canvas e QR Code
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=25, pady=(0, 10))

        # ---------------- MODO 1: CANVAS NA TELA ----------------
        self.canvas_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.canvas_frame.pack(fill="both", expand=True)

        self.canvas_w = 500
        self.canvas_h = 210

        canvas_border = ctk.CTkFrame(self.canvas_frame, fg_color="#CBD5E1", corner_radius=6, border_width=1, border_color="#94A3B8")
        canvas_border.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            canvas_border,
            width=self.canvas_w,
            height=self.canvas_h,
            bg="#FFFFFF",
            highlightthickness=0,
            cursor="crosshair"
        )
        self.canvas.pack(padx=2, pady=2, fill="both", expand=True)

        # Linha pontilhada de guia da assinatura
        self.canvas.create_line(30, 160, 470, 160, fill="#E2E8F0", width=1, dash=(4, 4))
        self.canvas.create_text(250, 180, text="X ________________________________________ (Espaço para Assinatura)", fill="#94A3B8", font=("Segoe UI", 8))

        # Estrutura PIL paralela para renderizar com precisão
        self.image = Image.new("RGBA", (self.canvas_w, self.canvas_h), (255, 255, 255, 0))
        self.draw = ImageDraw.Draw(self.image)
        self.points_drawn = 0

        # Eventos do mouse / touch
        self.last_x, self.last_y = None, None
        self.canvas.bind("<Button-1>", self._start_draw)
        self.canvas.bind("<B1-Motion>", self._draw)
        self.canvas.bind("<ButtonRelease-1>", self._stop_draw)

        # ---------------- MODO 2: QR CODE CELULAR ----------------
        self.qr_frame = ctk.CTkFrame(self.content_container, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER_COLOR)

        self.lbl_qr_img = ctk.CTkLabel(self.qr_frame, text="")
        self.lbl_qr_img.pack(pady=(10, 4))

        self.lbl_qr_url = ctk.CTkLabel(self.qr_frame, text="", font=FONT_SMALL_BOLD, text_color="#1E3A8A")
        self.lbl_qr_url.pack(pady=(0, 2))

        self.lbl_qr_status = ctk.CTkLabel(
            self.qr_frame,
            text="⏳ Aguardando colaborador assinar na tela do celular...",
            font=FONT_SMALL,
            text_color="#D97706"
        )
        self.lbl_qr_status.pack(pady=(0, 10))

        # ---------------- BARRA INFERIOR DE BOTÕES ----------------
        self.btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_bar.pack(fill="x", padx=25, pady=(0, 15))

        self.btn_clear = ctk.CTkButton(
            self.btn_bar,
            text="🗑️ Limpar",
            font=FONT_BODY,
            fg_color="#64748B",
            hover_color="#475569",
            width=90,
            command=self.clear_canvas
        )
        self.btn_clear.pack(side="left")

        self.btn_mobile = ctk.CTkButton(
            self.btn_bar,
            text="📱 Assinar pelo Celular (QR Code)",
            font=FONT_BODY_BOLD,
            fg_color="#0D9488",
            hover_color="#0F766E",
            command=self.toggle_mobile_mode
        )
        self.btn_mobile.pack(side="left", padx=8)

        self.btn_confirm = ctk.CTkButton(
            self.btn_bar,
            text="✔️ Confirmar",
            font=FONT_BODY_BOLD,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            width=130,
            command=self.save_signature
        )
        self.btn_confirm.pack(side="right")

    def toggle_mobile_mode(self):
        """Alterna entre desenhar no monitor e escanear QR Code para assinar no smartphone."""
        if not self.mobile_active:
            # Ativa QR Code
            self.mobile_active = True
            self.canvas_frame.pack_forget()
            self.btn_clear.pack_forget()
            self.btn_confirm.pack_forget()
            self.btn_mobile.configure(text="💻 Voltar para Assinatura na Tela", fg_color="#4F46E5", hover_color="#4338CA")

            def on_sig_received(path):
                self.saved_image_path = path
                self.after(0, self._on_mobile_signature_success)

            url, qr_img_path = MobileSignatureService.start_session(self.employee_name, on_sig_received)

            pil_img = Image.open(qr_img_path).resize((170, 170))
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(170, 170))
            self.lbl_qr_img.configure(image=ctk_img)
            self.lbl_qr_url.configure(text=f"Acesse: {url}")
            self.qr_frame.pack(fill="both", expand=True)
            self.lbl_instruction.configure(text="Aponte a câmera do celular para o QR Code abaixo para assinar na tela do aparelho:")
        else:
            # Volta para tela
            self.mobile_active = False
            MobileSignatureService.stop_session()
            self.qr_frame.pack_forget()
            self.canvas_frame.pack(fill="both", expand=True)
            self.btn_clear.pack(side="left")
            self.btn_confirm.pack(side="right")
            self.btn_mobile.configure(text="📱 Assinar pelo Celular (QR Code)", fg_color="#0D9488", hover_color="#0F766E")
            self.lbl_instruction.configure(text="Assine no quadro abaixo usando o mouse ou tela sensível ao toque:")

    def _on_mobile_signature_success(self):
        self.lbl_qr_status.configure(
            text="✅ Assinatura Recebida do Celular com Sucesso!",
            text_color=SUCCESS,
            font=FONT_BODY_BOLD
        )
        if self.on_signature_saved and self.saved_image_path:
            self.on_signature_saved(self.saved_image_path)

        self.after(1200, self._on_close)

    def _start_draw(self, event):
        self.last_x, self.last_y = event.x, event.y

    def _draw(self, event):
        if self.last_x is not None and self.last_y is not None:
            self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill="#0F172A", width=2.5, capstyle=tk.ROUND, smooth=True
            )
            self.draw.line(
                [self.last_x, self.last_y, event.x, event.y],
                fill=(15, 23, 42, 255), width=3
            )
            self.points_drawn += 1
        self.last_x, self.last_y = event.x, event.y

    def _stop_draw(self, event):
        self.last_x, self.last_y = None, None

    def clear_canvas(self):
        self.canvas.delete("all")
        self.canvas.create_line(30, 160, 470, 160, fill="#E2E8F0", width=1, dash=(4, 4))
        self.canvas.create_text(250, 180, text="X ________________________________________ (Espaço para Assinatura)", fill="#94A3B8", font=("Segoe UI", 8))
        self.image = Image.new("RGBA", (self.canvas_w, self.canvas_h), (255, 255, 255, 0))
        self.draw = ImageDraw.Draw(self.image)
        self.points_drawn = 0

    def save_signature(self):
        if self.points_drawn < 5:
            messagebox.showwarning("Assinatura Inválida", "Por favor, desenhe a assinatura antes de confirmar!")
            return

        os.makedirs(SIGNATURES_DIR, exist_ok=True)
        filename = f"sig_{uuid.uuid4().hex[:10]}.png"
        filepath = os.path.join(SIGNATURES_DIR, filename)

        self.image.save(filepath, "PNG")
        self.saved_image_path = filepath

        if self.on_signature_saved:
            self.on_signature_saved(filepath)

        self._on_close()

# Alias para compatibilidade
SignaturePadDialog = SignatureDialog
