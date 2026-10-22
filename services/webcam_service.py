import os
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
from database import APP_DIR, EXPORTS_DIR

PHOTOS_DIR = os.path.join(EXPORTS_DIR, "photos")

class WebcamService:
    @staticmethod
    def get_photos_dir():
        os.makedirs(PHOTOS_DIR, exist_ok=True)
        return PHOTOS_DIR

    @staticmethod
    def capture_quick_photo():
        """Captura um frame direto da webcam sem interface gráfica."""
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return None
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return None

            WebcamService.get_photos_dir()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recebedor_{ts}.jpg"
            filepath = os.path.join(PHOTOS_DIR, filename)

            cv2.imwrite(filepath, frame)
            return filepath
        except Exception:
            return None


class WebcamCaptureDialog(ctk.CTkToplevel):
    """Diálogo interativo com visualização ao vivo da webcam para bater foto do colaborador."""
    def __init__(self, parent, employee_name, on_photo_captured):
        super().__init__(parent)
        self.employee_name = employee_name
        self.on_photo_captured = on_photo_captured
        self.captured_path = None
        self.cap = None
        self.is_running = False

        self.title("Comprovação Fotográfica de Entrega (Webcam)")
        self.geometry("520x460")
        self.resizable(False, False)
        self.grab_set()

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 520) // 2
        y = (self.winfo_screenheight() - 460) // 2
        self.geometry(f"+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._start_camera()

    def _build_ui(self):
        ctk.CTkLabel(
            self,
            text=f"📸 Registro Fotográfico: {self.employee_name}",
            font=("Segoe UI", 16, "bold"),
            text_color="#1E3A8A"
        ).pack(pady=(14, 2))

        ctk.CTkLabel(
            self,
            text="Posicione o colaborador em frente à câmera e clique em 'Capturar Foto'",
            font=("Segoe UI", 12),
            text_color="#64748B"
        ).pack(pady=(0, 10))

        # Moldura do vídeo
        self.video_frame = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=8, width=440, height=310)
        self.video_frame.pack(padx=20, pady=(0, 15))
        self.video_frame.pack_propagate(False)

        self.lbl_video = ctk.CTkLabel(self.video_frame, text="Iniciando câmera...", text_color="#94A3B8")
        self.lbl_video.pack(fill="both", expand=True)

        # Botões
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=25, pady=(0, 15))

        btn_cancel = ctk.CTkButton(
            btn_bar,
            text="Cancelar",
            fg_color="#94A3B8",
            hover_color="#64748B",
            width=100,
            command=self._on_close
        )
        btn_cancel.pack(side="left")

        btn_capture = ctk.CTkButton(
            btn_bar,
            text="📸 Capturar Foto",
            font=("Segoe UI", 13, "bold"),
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=36,
            command=self._capture_frame
        )
        btn_capture.pack(side="right")

    def _start_camera(self):
        try:
            import cv2
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.lbl_video.configure(text="⚠️ Câmera não encontrada ou em uso por outro aplicativo.")
                return
            self.is_running = True
            self._update_feed()
        except Exception as ex:
            self.lbl_video.configure(text=f"Erro ao inicializar webcam: {ex}")

    def _update_feed(self):
        if self.is_running and self.cap and self.cap.isOpened():
            import cv2
            ret, frame = self.cap.read()
            if ret:
                # Inverte horizontalmente estilo espelho
                frame = cv2.flip(frame, 1)
                # Converte BGR para RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame).resize((440, 310))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(440, 310))
                self.lbl_video.configure(image=ctk_img, text="")
                self.last_frame = frame

            self.after(30, self._update_feed)

    def _capture_frame(self):
        if not hasattr(self, "last_frame") or self.last_frame is None:
            messagebox.showwarning("Aviso", "Nenhum sinal de vídeo disponível para captura.")
            return

        try:
            import cv2
            WebcamService.get_photos_dir()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recebedor_{ts}.jpg"
            filepath = os.path.join(PHOTOS_DIR, filename)

            cv2.imwrite(filepath, self.last_frame)
            self.captured_path = filepath

            if self.on_photo_captured:
                self.on_photo_captured(filepath)

            messagebox.showinfo("Foto Capturada!", "Comprovação fotográfica registrada com sucesso!")
            self._on_close()
        except Exception as ex:
            messagebox.showerror("Erro ao Salvar Foto", str(ex))

    def _on_close(self):
        self.is_running = False
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.destroy()
