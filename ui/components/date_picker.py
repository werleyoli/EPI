import customtkinter as ctk
import tkinter as tk
import calendar
from datetime import datetime
from ui.components.theme import BG_CARD, TEXT_MAIN, TEXT_MUTED, BORDER_COLOR, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, FONT_SMALL_BOLD

MESES_PT = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

class DatePickerDialog(ctk.CTkToplevel):
    def __init__(self, parent, initial_date=None, on_select=None):
        super().__init__(parent)
        self.on_select = on_select

        now = datetime.now()
        self.sel_year = now.year
        self.sel_month = now.month
        self.sel_day = now.day

        # Tenta interpretar initial_date
        if initial_date:
            try:
                dt_str = str(initial_date).strip()[:10]
                if "/" in dt_str:
                    parts = dt_str.split("/")
                    self.sel_day = int(parts[0])
                    self.sel_month = int(parts[1])
                    self.sel_year = int(parts[2])
                elif "-" in dt_str:
                    parts = dt_str.split("-")
                    self.sel_year = int(parts[0])
                    self.sel_month = int(parts[1])
                    self.sel_day = int(parts[2])
            except Exception:
                pass

        self.view_year = self.sel_year
        self.view_month = self.sel_month

        self.title("📅 Selecionar Data")
        self.geometry("340x360")
        self.resizable(False, False)
        self.grab_set()

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(10, (sw - 340) // 2)
        y = max(10, (sh - 360) // 2)
        self.geometry(f"+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        # Cabeçalho com Navegação de Mês/Ano
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(14, 6))

        btn_prev = ctk.CTkButton(
            hdr, text="◀", width=34, height=30,
            fg_color="#334155", hover_color="#475569",
            command=self._prev_month
        )
        btn_prev.pack(side="left")

        self.lbl_month_year = ctk.CTkLabel(
            hdr,
            text=f"{MESES_PT[self.view_month]} {self.view_year}",
            font=FONT_BODY_BOLD,
            text_color=TEXT_MAIN
        )
        self.lbl_month_year.pack(side="left", expand=True)

        btn_next = ctk.CTkButton(
            hdr, text="▶", width=34, height=30,
            fg_color="#334155", hover_color="#475569",
            command=self._next_month
        )
        btn_next.pack(side="right")

        # Dias da semana
        week_bar = ctk.CTkFrame(self, fg_color="transparent")
        week_bar.pack(fill="x", padx=16, pady=(4, 4))
        for d in DIAS_SEMANA:
            ctk.CTkLabel(
                week_bar, text=d, font=FONT_SMALL_BOLD,
                text_color=("#1E3A8A", "#60A5FA"), width=40
            ).pack(side="left", expand=True)

        # Container dos dias
        self.days_container = ctk.CTkFrame(self, fg_color="transparent")
        self.days_container.pack(fill="both", expand=True, padx=16, pady=2)

        self._render_calendar()

        # Barra inferior: Hoje / Limpar / Fechar
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.pack(fill="x", padx=16, pady=(8, 12))

        ctk.CTkButton(
            bot, text="Hoje", width=70, height=28,
            font=FONT_SMALL_BOLD, fg_color="#059669", hover_color="#047857",
            command=self._select_today
        ).pack(side="left")

        ctk.CTkButton(
            bot, text="Limpar", width=70, height=28,
            font=FONT_SMALL, fg_color="#64748B", hover_color="#475569",
            command=self._clear_date
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            bot, text="Fechar", width=70, height=28,
            font=FONT_SMALL, fg_color="#334155", hover_color="#475569",
            command=self.destroy
        ).pack(side="right")

    def _render_calendar(self):
        for widget in self.days_container.winfo_children():
            widget.destroy()

        self.lbl_month_year.configure(text=f"{MESES_PT[self.view_month]} {self.view_year}")

        cal = calendar.monthcalendar(self.view_year, self.view_month)
        today = datetime.now()

        for week in cal:
            row_f = ctk.CTkFrame(self.days_container, fg_color="transparent")
            row_f.pack(fill="x", pady=1)

            for day in week:
                if day == 0:
                    lbl_empty = ctk.CTkLabel(row_f, text="", width=40, height=28)
                    lbl_empty.pack(side="left", expand=True)
                else:
                    is_today = (day == today.day and self.view_month == today.month and self.view_year == today.year)
                    is_selected = (day == self.sel_day and self.view_month == self.sel_month and self.view_year == self.sel_year)

                    if is_selected:
                        fg = "#1E3A8A"
                        hov = "#1D4ED8"
                        txt_col = "#FFFFFF"
                    elif is_today:
                        fg = "#0D9488"
                        hov = "#0F766E"
                        txt_col = "#FFFFFF"
                    else:
                        fg = "#1E293B"
                        hov = "#334155"
                        txt_col = TEXT_MAIN

                    btn_d = ctk.CTkButton(
                        row_f,
                        text=str(day),
                        width=38,
                        height=28,
                        font=FONT_SMALL,
                        fg_color=fg,
                        hover_color=hov,
                        text_color=txt_col,
                        command=lambda d=day: self._pick_day(d)
                    )
                    btn_d.pack(side="left", expand=True, padx=1)

    def _pick_day(self, day):
        chosen_str = f"{day:02d}/{self.view_month:02d}/{self.view_year}"
        if self.on_select:
            self.on_select(chosen_str)
        self.destroy()

    def _select_today(self):
        now = datetime.now()
        chosen_str = now.strftime("%d/%m/%Y")
        if self.on_select:
            self.on_select(chosen_str)
        self.destroy()

    def _clear_date(self):
        if self.on_select:
            self.on_select("")
        self.destroy()

    def _prev_month(self):
        if self.view_month == 1:
            self.view_month = 12
            self.view_year -= 1
        else:
            self.view_month -= 1
        self._render_calendar()

    def _next_month(self):
        if self.view_month == 12:
            self.view_month = 1
            self.view_year += 1
        else:
            self.view_month += 1
        self._render_calendar()


def open_date_picker(parent, target_var=None, target_entry=None, on_change=None):
    """Abre o seletor de data e preenche a variável ou entry fornecida."""
    current_val = ""
    if target_var:
        current_val = target_var.get()
    elif target_entry:
        current_val = target_entry.get()

    def _on_pick(selected_date):
        if target_var:
            target_var.set(selected_date)
        if target_entry:
            target_entry.delete(0, "end")
            target_entry.insert(0, selected_date)
        if on_change:
            on_change()

    DatePickerDialog(parent, initial_date=current_val, on_select=_on_pick)
