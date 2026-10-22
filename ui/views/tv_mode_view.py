import tkinter as tk
import customtkinter as ctk
from datetime import datetime, timedelta
from database import get_connection
from services.epi_service import EPIService
from services.validade_uso_service import ValidadeUsoService
from services.compra_service import CompraService
from ui.components.table_view import StyledTable

class TVModeWindow(ctk.CTkToplevel):
    """
    Painel de TV do Almoxarifado para monitoramento contínuo em tempo real.
    Otimizado para exibição em TVs de grande porte e telas de parede.
    Suporta atualização instantânea reativa e exibição completa do estoque de produtos.
    """
    active_instances = []

    @classmethod
    def trigger_instant_refresh(cls):
        """Dispara atualização em tempo real (0ms) em todos os painéis de TV abertos."""
        for inst in list(cls.active_instances):
            try:
                inst.after(0, inst.refresh_data)
            except Exception:
                pass

    def __init__(self, parent=None):
        super().__init__(parent)
        TVModeWindow.active_instances.append(self)

        self.title("Painel de TV Almoxarifado SST - EPI Master Pro")
        self.geometry("1280x760")
        self.is_fullscreen = False

        # Centraliza na tela
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 1280) // 2
        y = (self.winfo_screenheight() - 760) // 2
        self.geometry(f"+{x}+{y}")

        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.bind("<Escape>", lambda e: self.exit_fullscreen())

        # Modo de visualização do estoque ("TODOS" ou "CRITICOS")
        self.estoque_view_mode = "TODOS"
        self.auto_rotate_active = True
        self.rotate_counter = 0

        self._build_ui()
        self.refresh_data()
        self._start_clock()
        self._start_auto_loop()

    def destroy(self):
        if self in TVModeWindow.active_instances:
            TVModeWindow.active_instances.remove(self)
        super().destroy()

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)

    def exit_fullscreen(self):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.attributes("-fullscreen", False)

    def _build_ui(self):
        self.configure(fg_color="#0F172A") # Fundo escuro profissional

        # Cabeçalho da TV
        header = ctk.CTkFrame(self, fg_color="#1E293B", height=84, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Logo / Título
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=25, pady=10)

        t_row = ctk.CTkFrame(title_box, fg_color="transparent")
        t_row.pack(anchor="w")

        ctk.CTkLabel(t_row, text="📺 PAINEL OPERACIONAL DE ALMOXARIFADO & SST", font=("Segoe UI", 20, "bold"), text_color="#38BDF8").pack(side="left")
        
        self.lbl_live_badge = ctk.CTkLabel(
            t_row,
            text="🟢 AO VIVO (TEMPO REAL)",
            font=("Segoe UI", 10, "bold"),
            fg_color="#064E3B",
            text_color="#34D399",
            corner_radius=12,
            padx=8,
            pady=2
        )
        self.lbl_live_badge.pack(side="left", padx=(12, 0))

        ctk.CTkLabel(title_box, text="Monitoramento de Estoque Físico, Reposição Crítica, Entregas do Dia e Trocas Preventivas", font=("Segoe UI", 12), text_color="#94A3B8").pack(anchor="w")

        # Botão de Atualizar Manual + Relógio Gigante
        right_header = ctk.CTkFrame(header, fg_color="transparent")
        right_header.pack(side="right", padx=25)

        btn_refresh_now = ctk.CTkButton(
            right_header,
            text="🔄 Atualizar Agora",
            font=("Segoe UI", 11, "bold"),
            fg_color="#0369A1",
            hover_color="#0284C7",
            width=125,
            height=30,
            command=self.refresh_data
        )
        btn_refresh_now.pack(side="left", padx=(0, 18))

        clock_box = ctk.CTkFrame(right_header, fg_color="transparent")
        clock_box.pack(side="right")

        self.lbl_clock = ctk.CTkLabel(clock_box, text="00:00:00", font=("Segoe UI", 26, "bold"), text_color="#F8FAFC")
        self.lbl_clock.pack(anchor="e")

        self.lbl_date = ctk.CTkLabel(clock_box, text="Segunda-feira, 01/01/2026", font=("Segoe UI", 12), text_color="#38BDF8")
        self.lbl_date.pack(anchor="e")

        # KPIs Gigantes
        kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=20, pady=(12, 8))
        kpi_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.kpi_total = self._make_tv_card(kpi_frame, 0, "ESTOQUE DE PRODUTOS", "0 itens", "#3B82F6")
        self.kpi_criticos = self._make_tv_card(kpi_frame, 1, "ESTOQUE CRÍTICO / ZERADOS", "0", "#EF4444")
        self.kpi_saidas_hoje = self._make_tv_card(kpi_frame, 2, "SAÍDAS REALIZADAS HOJE", "0 un", "#10B981")
        self.kpi_trocas_fila = self._make_tv_card(kpi_frame, 3, "TROCAS PENDENTES (SEMANA)", "0", "#F59E0B")

        # Conteúdo Central: Dividido em 2 Painéis
        split_frame = ctk.CTkFrame(self, fg_color="transparent")
        split_frame.pack(fill="both", expand=True, padx=20, pady=5)
        split_frame.grid_columnconfigure((0, 1), weight=1)
        split_frame.grid_rowconfigure(0, weight=1)

        # Painel Esquerdo: Estoque de Produtos & Alertas Críticos
        left_box = ctk.CTkFrame(split_frame, fg_color="#1E293B", corner_radius=10, border_width=1, border_color="#334155")
        left_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Barra Superior do Painel de Estoque (com abas de seleção)
        left_top = ctk.CTkFrame(left_box, fg_color="transparent")
        left_top.pack(fill="x", padx=12, pady=(10, 6))

        self.lbl_left_title = ctk.CTkLabel(
            left_top,
            text="📦 ESTOQUE GERAL DE PRODUTOS",
            font=("Segoe UI", 13, "bold"),
            text_color="#38BDF8"
        )
        self.lbl_left_title.pack(side="left")

        # Controles de Abas e Rotação
        tab_box = ctk.CTkFrame(left_top, fg_color="transparent")
        tab_box.pack(side="right")

        self.btn_tab_todos = ctk.CTkButton(
            tab_box,
            text="📦 Todos os Produtos",
            font=("Segoe UI", 11, "bold"),
            height=28,
            width=135,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            command=lambda: self._set_estoque_mode("TODOS")
        )
        self.btn_tab_todos.pack(side="left", padx=2)

        self.btn_tab_crit = ctk.CTkButton(
            tab_box,
            text="⚠️ Só Críticos",
            font=("Segoe UI", 11, "bold"),
            height=28,
            width=100,
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self._set_estoque_mode("CRITICOS")
        )
        self.btn_tab_crit.pack(side="left", padx=2)

        self.chk_auto_rotate_btn = ctk.CTkButton(
            tab_box,
            text="🔁 Auto (12s): ON",
            font=("Segoe UI", 10),
            height=28,
            width=105,
            fg_color="#0F766E",
            hover_color="#115E59",
            command=self._toggle_auto_rotate
        )
        self.chk_auto_rotate_btn.pack(side="left", padx=(6, 0))

        cols_estoque = [
            {"id": "cod", "text": "Cód.", "width": 60, "anchor": "center"},
            {"id": "nome", "text": "Descrição do Equipamento (EPI)", "width": 190, "anchor": "w"},
            {"id": "ca", "text": "C.A.", "width": 60, "anchor": "center"},
            {"id": "loc", "text": "Locais", "width": 115, "anchor": "w"},
            {"id": "saldo", "text": "Estoque", "width": 80, "anchor": "center"},
            {"id": "min", "text": "Mín.", "width": 60, "anchor": "center"},
            {"id": "status", "text": "Situação", "width": 80, "anchor": "center"}
        ]
        self.tbl_crit = StyledTable(left_box, columns=cols_estoque)
        self.tbl_crit.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Painel Direito: Fila de Trocas da Semana
        right_box = ctk.CTkFrame(split_frame, fg_color="#1E293B", corner_radius=10, border_width=1, border_color="#334155")
        right_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        ctk.CTkLabel(right_box, text="⏰ FILA DE CONVOCAÇÃO: TROCAS PREVENTIVAS DESTA SEMANA", font=("Segoe UI", 13, "bold"), text_color="#FBBF24").pack(anchor="w", padx=15, pady=(10, 6))

        cols_trocas = [
            {"id": "func", "text": "Colaborador", "width": 170, "anchor": "w"},
            {"id": "epi", "text": "EPI em Uso", "width": 190, "anchor": "w"},
            {"id": "prev", "text": "Previsão", "width": 80, "anchor": "center"},
            {"id": "status", "text": "Situação", "width": 100, "anchor": "center"}
        ]
        self.tbl_trocas = StyledTable(right_box, columns=cols_trocas)
        self.tbl_trocas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Rodapé com Slogan de Segurança
        footer = ctk.CTkFrame(self, fg_color="#1E293B", height=42, corner_radius=0)
        footer.pack(fill="x")
        footer.pack_propagate(False)

        ctk.CTkLabel(
            footer,
            text="🛡️ NR-6 SEGURANÇA DO TRABALHO: O EPI protege sua integridade física. Não execute tarefas sem os equipamentos recomendados!",
            font=("Segoe UI", 12, "bold"),
            text_color="#F8FAFC"
        ).pack(side="left", padx=25)

        btn_fs = ctk.CTkButton(footer, text="⛶ Tela Cheia (F11)", width=120, height=28, fg_color="#334155", command=self.toggle_fullscreen)
        btn_fs.pack(side="right", padx=20)

    def _set_estoque_mode(self, mode):
        self.estoque_view_mode = mode
        if mode == "TODOS":
            self.btn_tab_todos.configure(fg_color="#2563EB", hover_color="#1D4ED8")
            self.btn_tab_crit.configure(fg_color="#334155", hover_color="#475569")
            self.lbl_left_title.configure(text="📦 ESTOQUE GERAL DE PRODUTOS", text_color="#38BDF8")
        else:
            self.btn_tab_todos.configure(fg_color="#334155", hover_color="#475569")
            self.btn_tab_crit.configure(fg_color="#DC2626", hover_color="#B91C1C")
            self.lbl_left_title.configure(text="⚠️ ALERTA: ITENS COM ESTOQUE CRÍTICO / REPOSIÇÃO", text_color="#F87171")
        self.refresh_data()

    def _toggle_auto_rotate(self):
        self.auto_rotate_active = not self.auto_rotate_active
        if self.auto_rotate_active:
            self.chk_auto_rotate_btn.configure(text="🔁 Auto (12s): ON", fg_color="#0F766E")
        else:
            self.chk_auto_rotate_btn.configure(text="⏸️ Auto: OFF", fg_color="#475569")

    def _make_tv_card(self, parent, col, title, initial_val, color):
        f = ctk.CTkFrame(parent, fg_color="#1E293B", corner_radius=8, border_width=1, border_color="#334155")
        f.grid(row=0, column=col, sticky="nsew", padx=6)

        ctk.CTkLabel(f, text=title, font=("Segoe UI", 11, "bold"), text_color="#94A3B8").pack(anchor="w", padx=15, pady=(8, 0))
        lbl = ctk.CTkLabel(f, text=initial_val, font=("Segoe UI", 22, "bold"), text_color=color)
        lbl.pack(anchor="w", padx=15, pady=(2, 8))
        return lbl

    def _start_clock(self):
        try:
            now = datetime.now()
            self.lbl_clock.configure(text=now.strftime("%H:%M:%S"))
            self.lbl_date.configure(text=now.strftime("%d/%m/%Y • %A"))
        except Exception:
            pass
        self.after(1000, self._start_clock)

    def _start_auto_loop(self):
        """Loop de atualização de dados frequente (a cada 3s) e rotação de telas."""
        try:
            self.rotate_counter += 1
            # A cada 12 segundos (4 ciclos de 3s), alterna o modo se auto-rotate estiver ativo
            if self.auto_rotate_active and self.rotate_counter >= 4:
                self.rotate_counter = 0
                next_mode = "CRITICOS" if self.estoque_view_mode == "TODOS" else "TODOS"
                self._set_estoque_mode(next_mode)
            else:
                self.refresh_data()
        except Exception:
            pass

        self.after(3000, self._start_auto_loop)

    def refresh_data(self):
        try:
            self.tbl_crit.apply_theme("Dark")
            self.tbl_trocas.apply_theme("Dark")

            # 1. KPIs
            sum_epi = EPIService.get_summary()
            self.kpi_total.configure(text=f"{sum_epi['total_itens']} itens ({sum_epi['total_unidades']} un)")
            self.kpi_criticos.configure(text=str(sum_epi["criticos"]))

            # Saídas de Hoje
            today_str = datetime.now().strftime("%Y-%m-%d")
            with get_connection() as conn:
                r = conn.execute("SELECT SUM(quantidade) as q FROM movimentacoes WHERE tipo = 'SAIDA' AND data_hora LIKE ?", (f"{today_str}%",)).fetchone()
                qtd_hoje = r["q"] or 0
                self.kpi_saidas_hoje.configure(text=f"{qtd_hoje} un")

            # 2. Painel Esquerdo: Produtos em Estoque / Críticos
            self.tbl_crit.clear()
            if self.estoque_view_mode == "TODOS":
                epis = EPIService.list_epis(show_inactive=False)
                for e in epis:
                    cod = e.get("codigo", "")
                    nome = e.get("nome", "")
                    ca = e.get("ca") or "-"
                    
                    loc1 = (e.get("localizacao") or "").strip()
                    loc2 = (e.get("localizacao_secundaria") or "").strip()
                    if loc1 and loc2:
                        loc_str = f"{loc1} | {loc2}"
                    elif loc1:
                        loc_str = loc1
                    elif loc2:
                        loc_str = loc2
                    else:
                        loc_str = "-"

                    qtd = int(e.get("quantidade") or 0)
                    min_q = int(e.get("estoque_minimo") or 0)
                    un = e.get("unidade") or "UN"

                    if qtd == 0:
                        sit = "🔴 Zerado"
                        tag = "danger"
                    elif qtd <= min_q:
                        sit = "🟡 Crítico"
                        tag = "warning"
                    else:
                        sit = "🟢 Normal"
                        tag = "odd"

                    self.tbl_crit.insert_row(
                        e["id"],
                        [cod, nome, ca, loc_str, f"{qtd} {un}", f"{min_q} {un}", sit],
                        tag=tag
                    )
            else:
                crit_items = CompraService.get_critical_stock_for_purchase()
                for it in crit_items:
                    cod = it.get("codigo", "")
                    nome = it.get("nome", "")
                    ca = it.get("ca") or "-"
                    qtd = int(it.get("quantidade") or 0)
                    min_q = int(it.get("estoque_minimo") or 0)
                    un = it.get("unidade") or "UN"

                    sit = "🔴 Zerado" if qtd == 0 else "🟡 Crítico"
                    tag = "danger" if qtd == 0 else "warning"

                    self.tbl_crit.insert_row(
                        it["id"],
                        [cod, nome, ca, "Almoxarifado", f"{qtd} {un}", f"{min_q} {un}", sit],
                        tag=tag
                    )

            # 3. Fila de Trocas da Semana
            trocas = ValidadeUsoService.get_items_due_for_exchange()
            fila = [t for t in trocas if t["dias_restantes"] <= 7]
            self.kpi_trocas_fila.configure(text=str(len(fila)))

            self.tbl_trocas.clear()
            for t in fila[:30]:
                self.tbl_trocas.insert_row(
                    t["mov_id"],
                    [t["func_nome"], t["epi_nome"], t["data_previsao_troca"][:5], t["status_label"]],
                    tag="danger" if t["status"] == "VENCIDO" else "odd"
                )

        except Exception as ex:
            print("Erro ao atualizar Painel de TV:", ex)
