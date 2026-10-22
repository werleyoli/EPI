import tkinter as tk
from tkinter import ttk
import customtkinter as ctk

class StyledTable(ctk.CTkFrame):
    """
    Componente de Tabela Reutilizável estilizada baseada em ttk.Treeview,
    com suporte completo a Dark Mode / Light Mode, scrollbars,
    seleção de linha, ordenação e tags coloridas.
    """
    def __init__(self, parent, columns, show_headers=True, on_select=None, on_double_click=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.columns = columns
        self.on_select = on_select
        self.on_double_click = on_double_click
        self.sort_desc = {}

        self._build_table(show_headers)
        self.apply_theme(ctk.get_appearance_mode())

    def apply_theme(self, mode):
        """Aplica cores para Modo Escuro (Dark) ou Claro (Light)."""
        is_dark = mode.lower() == "dark"
        style = ttk.Style()
        style.theme_use("clam")

        bg_main = "#1E293B" if is_dark else "#FFFFFF"
        fg_main = "#F8FAFC" if is_dark else "#1E293B"
        bg_header = "#0F172A" if is_dark else "#1E3A8A"
        fg_header = "#FFFFFF"
        bg_select = "#3B82F6" if is_dark else "#DBEAFE"
        fg_select = "#FFFFFF" if is_dark else "#1E3A8A"

        style.configure(
            "Custom.Treeview",
            background=bg_main,
            foreground=fg_main,
            fieldbackground=bg_main,
            font=("Segoe UI", 10),
            rowheight=32,
            borderwidth=0
        )
        style.configure(
            "Custom.Treeview.Heading",
            background=bg_header,
            foreground=fg_header,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(6, 6)
        )
        style.map(
            "Custom.Treeview.Heading",
            background=[("active", "#2563EB")]
        )
        style.map(
            "Custom.Treeview",
            background=[("selected", bg_select)],
            foreground=[("selected", fg_select)]
        )

        # Tags para coloração de linhas (linhas zebradas e alertas)
        if is_dark:
            self.tree.tag_configure("even", background="#1E293B", foreground="#F8FAFC")
            self.tree.tag_configure("odd", background="#162238", foreground="#F8FAFC")
            self.tree.tag_configure("warning", background="#78350F", foreground="#FEF3C7")
            self.tree.tag_configure("danger", background="#7F1D1D", foreground="#FEE2E2")
            self.tree.tag_configure("success", background="#064E3B", foreground="#D1FAE5")
        else:
            self.tree.tag_configure("even", background="#FFFFFF", foreground="#1E293B")
            self.tree.tag_configure("odd", background="#F8FAFC", foreground="#1E293B")
            self.tree.tag_configure("warning", background="#FEF3C7", foreground="#92400E")
            self.tree.tag_configure("danger", background="#FEE2E2", foreground="#991B1B")
            self.tree.tag_configure("success", background="#D1FAE5", foreground="#065F46")

    def _build_table(self, show_headers):
        col_ids = [c["id"] for c in self.columns]
        show_mode = "headings" if show_headers else "tree"

        self.tree = ttk.Treeview(
            self,
            columns=col_ids,
            show=show_mode,
            selectmode="browse",
            style="Custom.Treeview"
        )

        # Configura colunas
        for col in self.columns:
            cid = col["id"]
            title = col.get("text", cid)
            width = col.get("width", 100)
            align = col.get("anchor", "w")
            stretch = col.get("stretch", True)

            self.tree.heading(cid, text=title, anchor=align, command=lambda c=cid: self._sort_column(c))
            self.tree.column(cid, width=width, anchor=align, stretch=stretch)

        # Scrollbars
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Eventos
        self.tree.bind("<<TreeviewSelect>>", self._handle_select)
        if self.on_double_click:
            self.tree.bind("<Double-1>", self._handle_double_click)

    def _handle_select(self, event):
        if self.on_select:
            selected_item = self.get_selected()
            self.on_select(selected_item)

    def _handle_double_click(self, event):
        if self.on_double_click:
            selected_item = self.get_selected()
            if selected_item:
                self.on_double_click(selected_item)

    def _sort_column(self, col):
        """Ordena a tabela clicando no cabeçalho da coluna."""
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        desc = self.sort_desc.get(col, False)

        try:
            items.sort(key=lambda t: float(t[0].replace(",", ".").replace("UN", "").replace("PAR", "").strip()), reverse=desc)
        except ValueError:
            items.sort(reverse=desc)

        for index, (val, k) in enumerate(items):
            self.tree.move(k, "", index)

        self.sort_desc[col] = not desc

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def insert_row(self, row_id, values, tag=None):
        tags = [tag] if tag else ["even" if len(self.tree.get_children()) % 2 == 0 else "odd"]
        self.tree.insert("", "end", iid=str(row_id), values=values, tags=tags)

    def get_selected(self):
        selected = self.tree.selection()
        if selected:
            return selected[0]
        return None

    def get_selected_values(self):
        selected = self.tree.selection()
        if selected:
            return self.tree.item(selected[0], "values")
        return None
