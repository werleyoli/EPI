"""
Paleta de Cores e Estilos Adaptativos (Claro / Escuro) para o Sistema de Gestão de EPI
Suporta alternância dinâmica entre Tema Claro (Light) e Tema Escuro (Dark).
No CustomTkinter, cores podem ser tuplas (cor_light, cor_dark).
"""

# Cores Principais da Marca
PRIMARY = "#1E40AF"        # Azul royal corporativo
PRIMARY_HOVER = "#1D4ED8"  # Azul hover
PRIMARY_LIGHT = ("#DBEAFE", "#1E3A8A")

SECONDARY = ("#0F172A", "#0F172A")
SECONDARY_HOVER = ("#1E293B", "#334155")

SUCCESS = "#10B981"        # Verde para status normal / entradas
SUCCESS_HOVER = "#059669"

WARNING = "#F59E0B"        # Laranja / Amarelo para estoque baixo
WARNING_HOVER = "#D97706"

DANGER = "#EF4444"         # Vermelho para estoque crítico / zerado / saídas
DANGER_HOVER = "#DC2626"

INFO = "#0EA5E9"

# Fundos e Superfícies Adaptativos (Light, Dark)
BG_SIDEBAR = ("#1E293B", "#0F172A")    # Sidebar escura elegante em ambos
BG_MAIN = ("#F1F5F9", "#0B1120")       # Fundo principal da área de trabalho
BG_CARD = ("#FFFFFF", "#1E293B")       # Cartões e containers
BG_CARD_HOVER = ("#F8FAFC", "#334155")
BORDER_COLOR = ("#E2E8F0", "#334155")  # Bordas sutis

# Textos Adaptativos (Light, Dark)
TEXT_MAIN = ("#0F172A", "#F8FAFC")     # Texto principal escuro no claro, branco no escuro
TEXT_MUTED = ("#64748B", "#94A3B8")    # Texto secundário
TEXT_WHITE = "#FFFFFF"

# Fontes padrão
FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_SUBTITLE = ("Segoe UI", 14, "bold")
FONT_SECTION = ("Segoe UI", 12, "bold")
FONT_BODY = ("Segoe UI", 11)
FONT_BODY_BOLD = ("Segoe UI", 11, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_SMALL_BOLD = ("Segoe UI", 9, "bold")
