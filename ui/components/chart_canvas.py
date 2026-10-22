import tkinter as tk
import customtkinter as ctk
from ui.components.theme import *

class ModernBarChart(ctk.CTkFrame):
    """
    Componente de gráfico de barras horizontais nativo, leve, responsivo e adaptável a tema claro/escuro.
    Perfeito para 'Top EPIs Mais Consumidos' ou 'Gastos por Departamento'.
    """
    def __init__(self, parent, title="Gráfico", height=180, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.title_text = title
        self.height = height
        self._build_ui()

    def _build_ui(self):
        self.lbl_title = ctk.CTkLabel(self, text=self.title_text, font=FONT_SECTION, text_color=TEXT_MAIN)
        self.lbl_title.pack(anchor="w", padx=10, pady=(6, 4))

        self.canvas = tk.Canvas(self, height=self.height, bg="#1E293B", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.canvas.bind("<Configure>", lambda e: self._redraw())

        self.data = []

    def set_data(self, data: list):
        """
        data: list de tuplas ou dicts:
        [{'label': 'Capacete', 'value': 45, 'formatted': '45 un (R$ 1.700)'}, ...]
        """
        self.data = data
        self._redraw()

    def apply_theme(self, mode: str):
        bg = "#1E293B" if mode == "Dark" else "#F1F5F9"
        self.canvas.configure(bg=bg)
        self._redraw()

    def _redraw(self):
        self.canvas.delete("all")
        if not self.data:
            w = self.canvas.winfo_width() or 300
            h = self.canvas.winfo_height() or self.height
            mode = ctk.get_appearance_mode()
            text_color = "#94A3B8" if mode == "Dark" else "#64748B"
            self.canvas.create_text(w / 2, h / 2, text="Sem dados para exibição no período", fill=text_color, font=("Segoe UI", 10))
            return

        w = self.canvas.winfo_width()
        if w < 100:
            w = 340
        h = self.canvas.winfo_height() or self.height

        mode = ctk.get_appearance_mode()
        label_color = "#E2E8F0" if mode == "Dark" else "#1E293B"
        bar_bg = "#334155" if mode == "Dark" else "#E2E8F0"
        value_color = "#93C5FD" if mode == "Dark" else "#1D4ED8"

        palette = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]

        max_val = max(d["value"] for d in self.data) or 1
        num_items = len(self.data)
        item_h = max(24, int((h - 15) / max(num_items, 1)))
        pad_y = 4
        bar_h = max(10, item_h - (pad_y * 2) - 12)

        start_x = 10
        label_w = min(130, int(w * 0.35))
        bar_max_w = w - label_w - 95

        for i, item in enumerate(self.data):
            y_top = 10 + i * item_h
            y_center = y_top + 8

            # Rótulo
            label = item["label"]
            if len(label) > 18:
                label = label[:17] + "…"
            self.canvas.create_text(start_x, y_center, text=label, anchor="w", fill=label_color, font=("Segoe UI", 9, "bold"))

            # Fundo da barra
            bx1 = start_x + label_w
            bx2 = bx1 + bar_max_w
            by1 = y_center - bar_h / 2
            by2 = y_center + bar_h / 2
            self.canvas.create_rectangle(bx1, by1, bx2, by2, fill=bar_bg, width=0)

            # Barra preenchida
            ratio = item["value"] / max_val
            fill_w = max(4, int(bar_max_w * ratio))
            bar_color = palette[i % len(palette)]
            self.canvas.create_rectangle(bx1, by1, bx1 + fill_w, by2, fill=bar_color, width=0)

            # Valor formatado
            val_text = item.get("formatted", str(item["value"]))
            self.canvas.create_text(bx2 + 8, y_center, text=val_text, anchor="w", fill=value_color, font=("Segoe UI", 8, "bold"))
