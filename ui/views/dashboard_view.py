import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import datetime
from services.epi_service import EPIService
from services.employee_service import EmployeeService
from services.movement_service import MovementService
from services.notification_service import NotificationService
from ui.components.theme import *
from ui.components.table_view import StyledTable
from ui.components.chart_canvas import ModernBarChart

class DashboardView(ctk.CTkScrollableFrame):
    def __init__(self, parent, on_navigate):
        super().__init__(parent, fg_color="transparent")
        self.on_navigate = on_navigate
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Título da tela
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(15, 12))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="Painel Principal & Controle de EPI",
            font=FONT_TITLE,
            text_color=TEXT_MAIN
        )
        title_lbl.pack(side="left")

        today_str = datetime.now().strftime("%d de %B de %Y")
        date_lbl = ctk.CTkLabel(
            header_frame,
            text=f"📅 {today_str}",
            font=FONT_BODY,
            text_color=TEXT_MUTED
        )
        date_lbl.pack(side="right")

        # Container dos Cards de Indicadores (5 Cards)
        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.pack(fill="x", padx=25, pady=(0, 15))
        self.cards_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="card")

        self.card_total_epis = self._create_kpi_card(
            self.cards_frame, 0, "TOTAL DE ITENS", "0", "0 unidades", "#3B82F6", "📦"
        )
        self.card_criticos = self._create_kpi_card(
            self.cards_frame, 1, "ESTOQUE CRÍTICO", "0", "Precisam compra", "#EF4444", "⚠️"
        )
        self.card_funcionarios = self._create_kpi_card(
            self.cards_frame, 2, "COLABORADORES", "0", "Ativos", "#10B981", "👷"
        )
        self.card_saidas_mes = self._create_kpi_card(
            self.cards_frame, 3, "SAÍDAS NO MÊS", "0", "EPIs entregues", "#8B5CF6", "📤"
        )
        self.card_custo_mes = self._create_kpi_card(
            self.cards_frame, 4, "CUSTO SAÍDAS MÊS", "R$ 0,00", "Total investido", "#0EA5E9", "💰"
        )

        # Barra de Ações Rápidas
        actions_bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        actions_bar.pack(fill="x", padx=25, pady=(0, 15))

        bar_title = ctk.CTkLabel(actions_bar, text="AÇÕES RÁPIDAS:", font=FONT_BODY_BOLD, text_color=TEXT_MUTED)
        bar_title.pack(side="left", padx=15, pady=12)

        btn_nova_saida = ctk.CTkButton(
            actions_bar,
            text="➕ Nova Saída Individual",
            font=FONT_BODY_BOLD,
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=34,
            corner_radius=6,
            command=lambda: self.on_navigate("movements", action="new_exit")
        )
        btn_nova_saida.pack(side="left", padx=5)

        btn_kit = ctk.CTkButton(
            actions_bar,
            text="⚡ Entregar Kit por Cargo",
            font=FONT_BODY_BOLD,
            fg_color="#4F46E5",
            hover_color="#4338CA",
            height=34,
            corner_radius=6,
            command=lambda: self.on_navigate("matriz")
        )
        btn_kit.pack(side="left", padx=5)

        btn_ficha = ctk.CTkButton(
            actions_bar,
            text="📄 Fichas de EPI (NR-6)",
            font=FONT_BODY,
            fg_color="#475569",
            hover_color="#334155",
            height=34,
            corner_radius=6,
            command=lambda: self.on_navigate("employee_sheet")
        )
        btn_ficha.pack(side="left", padx=5)

        btn_email_alert = ctk.CTkButton(
            actions_bar,
            text="🚨 Disparar Alerta por E-mail",
            font=FONT_BODY,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            height=34,
            corner_radius=6,
            command=self._disparar_alerta_email
        )
        btn_email_alert.pack(side="right", padx=15)

        # ------------------ GRÁFICOS VISUAIS INTERATIVOS ------------------
        charts_frame = ctk.CTkFrame(self, fg_color="transparent")
        charts_frame.pack(fill="x", padx=25, pady=(0, 15))
        charts_frame.grid_columnconfigure((0, 1), weight=1, uniform="chart")

        chart_card1 = ctk.CTkFrame(charts_frame, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        chart_card1.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.chart_epis = ModernBarChart(chart_card1, title="📊 Top 5 EPIs Mais Consumidos (Saídas)", height=155)
        self.chart_epis.pack(fill="both", expand=True, padx=6, pady=6)

        chart_card2 = ctk.CTkFrame(charts_frame, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        chart_card2.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.chart_deptos = ModernBarChart(chart_card2, title="💰 Gastos Acumulados com EPI por Departamento", height=155)
        self.chart_deptos.pack(fill="both", expand=True, padx=6, pady=6)

        # Seções Divididas em Grid (Esquerda: Últimas Saídas | Direita: Alertas de Reposição e Troca)
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=25, pady=(0, 20))
        content_frame.grid_columnconfigure(0, weight=6, uniform="split")
        content_frame.grid_columnconfigure(1, weight=4, uniform="split")

        # Lado Esquerdo: Últimas Saídas
        left_box = ctk.CTkFrame(content_frame, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        left_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        left_header = ctk.CTkFrame(left_box, fg_color="transparent")
        left_header.pack(fill="x", padx=15, pady=(12, 8))

        ctk.CTkLabel(left_header, text="Últimas Saídas / Entregas Realizadas", font=FONT_SECTION, text_color=TEXT_MAIN).pack(side="left")
        btn_ver_todas = ctk.CTkButton(
            left_header,
            text="Ver Histórico Completo →",
            font=FONT_SMALL_BOLD,
            fg_color="transparent",
            text_color="#3B82F6",
            hover_color=PRIMARY_LIGHT,
            width=80,
            command=lambda: self.on_navigate("movements")
        )
        btn_ver_todas.pack(side="right")

        cols_saidas = [
            {"id": "data", "text": "Data/Hora", "width": 105, "anchor": "center"},
            {"id": "epi", "text": "Equipamento (EPI)", "width": 160, "anchor": "w"},
            {"id": "qtd", "text": "Qtd", "width": 45, "anchor": "center"},
            {"id": "custo", "text": "Custo", "width": 75, "anchor": "center"},
            {"id": "func", "text": "Funcionário", "width": 135, "anchor": "w"},
            {"id": "resp", "text": "Quem Entregou", "width": 115, "anchor": "w"},
        ]
        self.tbl_saidas = StyledTable(left_box, columns=cols_saidas, height=180)
        self.tbl_saidas.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Lado Direito: Alertas (Trocas Pendentes e Reposição)
        right_box = ctk.CTkFrame(content_frame, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        right_header = ctk.CTkFrame(right_box, fg_color="transparent")
        right_header.pack(fill="x", padx=15, pady=(12, 8))

        ctk.CTkLabel(right_header, text="⏰ Trocas Preventivas Pendentes", font=FONT_SECTION, text_color=WARNING).pack(side="left")

        cols_alertas = [
            {"id": "func", "text": "Colaborador", "width": 115, "anchor": "w"},
            {"id": "epi", "text": "EPI Vencido", "width": 125, "anchor": "w"},
            {"id": "dias", "text": "Dias em Uso", "width": 75, "anchor": "center"},
            {"id": "prev", "text": "Troca Prev.", "width": 75, "anchor": "center"},
        ]
        self.tbl_alertas = StyledTable(right_box, columns=cols_alertas, height=180)
        self.tbl_alertas.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def _create_kpi_card(self, parent, col, title, value, subtext, color, icon):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10, border_width=1, border_color=BORDER_COLOR)
        card.grid(row=0, column=col, sticky="nsew", padx=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=12)

        top_f = ctk.CTkFrame(inner, fg_color="transparent")
        top_f.pack(fill="x")

        title_lbl = ctk.CTkLabel(top_f, text=title, font=FONT_SMALL_BOLD, text_color=TEXT_MUTED)
        title_lbl.pack(side="left")

        icon_lbl = ctk.CTkLabel(top_f, text=icon, font=("Segoe UI", 15))
        icon_lbl.pack(side="right")

        val_lbl = ctk.CTkLabel(inner, text=value, font=("Segoe UI", 22, "bold"), text_color=color)
        val_lbl.pack(anchor="w", pady=(2, 0))

        sub_lbl = ctk.CTkLabel(inner, text=subtext, font=FONT_SMALL, text_color=TEXT_MUTED)
        sub_lbl.pack(anchor="w")

        return {"val_lbl": val_lbl, "sub_lbl": sub_lbl}

    def _disparar_alerta_email(self):
        """Dispara e-mail de alerta de estoque crítico e CAs a vencer."""
        res = NotificationService.send_alert_email()
        if res.get("sucesso"):
            messagebox.showinfo("Alerta Enviado", res["mensagem"])
        else:
            messagebox.showwarning("Aviso de E-mail", res["mensagem"])

    def refresh(self):
        mode = ctk.get_appearance_mode()
        if hasattr(self, "tbl_saidas"):
            self.tbl_saidas.apply_theme(mode)
        if hasattr(self, "tbl_alertas"):
            self.tbl_alertas.apply_theme(mode)
        if hasattr(self, "chart_epis"):
            self.chart_epis.apply_theme(mode)
        if hasattr(self, "chart_deptos"):
            self.chart_deptos.apply_theme(mode)

        try:
            epi_summary = EPIService.get_summary()
            func_summary = EmployeeService.get_summary()
            stats = MovementService.get_recent_stats()

            self.card_total_epis["val_lbl"].configure(text=f"{epi_summary['total_itens']}")
            self.card_total_epis["sub_lbl"].configure(text=f"{epi_summary['total_unidades']} un | R$ {epi_summary['valor_total_estoque']:.2f}")

            self.card_criticos["val_lbl"].configure(text=f"{epi_summary['criticos']}")
            sub_crit = f"{epi_summary['zerados']} zerados"
            if epi_summary.get('ca_vencendo', 0) > 0:
                sub_crit += f" | {epi_summary['ca_vencendo']} CA a vencer"
            self.card_criticos["sub_lbl"].configure(text=sub_crit)

            self.card_funcionarios["val_lbl"].configure(text=f"{func_summary['ativos']}")
            self.card_saidas_mes["val_lbl"].configure(text=f"{stats['saidas_mes']}")
            self.card_custo_mes["val_lbl"].configure(text=f"R$ {stats['custo_saidas_mes']:.2f}")

            # Atualiza Gráficos Visuais
            top_epis = MovementService.get_top_epis_consumed(5)
            self.chart_epis.set_data(top_epis)

            deptos_costs = MovementService.get_department_costs(5)
            self.chart_deptos.set_data(deptos_costs)

            # Atualiza tabela de últimas saídas
            self.tbl_saidas.clear()
            for s in stats["ultimas_saidas"]:
                dt = s["data_hora"]
                try:
                    dt = datetime.strptime(dt[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
                except Exception:
                    pass
                custo_fmt = f"R$ {s.get('custo_total', 0.0):.2f}"
                self.tbl_saidas.insert_row(
                    s["id"],
                    [dt, s["epi_nome"], s["quantidade"], custo_fmt, s.get("func_nome") or "-", s["responsavel_entrega"]]
                )

            # Atualiza alertas de trocas preventivas pendentes (Vida Útil)
            self.tbl_alertas.clear()
            pendentes = MovementService.list_pending_replacements()
            for p in pendentes[:15]:
                self.tbl_alertas.insert_row(
                    p["mov_id"],
                    [p["func_nome"], p["epi_nome"], f"{p['dias_em_uso']} dias", p["data_prevista_troca"]],
                    tag="warning"
                )
        except Exception as e:
            print("Erro ao atualizar dashboard:", e)
