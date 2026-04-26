"""Modulo de Interfaz Grafica (CustomTkinter) para el Inventario Maestro."""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import math

from services import InventarioService
from database import DatabaseManager

class TabInventario:
    """Clase que representa la pestana de gestion de inventario premium (V2.0)."""

    def __init__(self, parent: ctk.CTkFrame, db_manager: DatabaseManager):
        self.parent = parent
        self.servicio = InventarioService(db_manager)
        self.frame = self.parent
        
        self.margenes_sugeridos = {
            "Bebidas": 1.40, "Lacteos": 1.30, "Fiambres": 1.50,
            "Snack Dulces": 1.50, "Galletitas": 1.40, "Higiene": 1.60, "Default": 1.40
        }
        self.setup_ui()

    def setup_ui(self) -> None:
        container = ctk.CTkFrame(self.frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === COLUMNA IZQUIERDA ===
        panel_izquierdo = ctk.CTkFrame(container, width=350, fg_color="transparent")
        panel_izquierdo.pack(side="left", fill="y", padx=(0, 10))
        
        # 1. Formulario ABM
        f_abm = ctk.CTkFrame(panel_izquierdo, corner_radius=10)
        f_abm.pack(fill="x", pady=5)
        
        ctk.CTkLabel(f_abm, text="Gestion de Producto", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        ctk.CTkLabel(f_abm, text="ID (Vacio=Nuevo):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.ent_id = ctk.CTkEntry(f_abm, width=180, state="readonly", fg_color="#34495e")
        self.ent_id.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(f_abm, text="Nombre:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.ent_nombre = ctk.CTkEntry(f_abm, width=180)
        self.ent_nombre.grid(row=2, column=1, padx=10, pady=5)

        ctk.CTkLabel(f_abm, text="Categoria:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.combo_categoria = ctk.CTkComboBox(f_abm, width=180, command=self.sugerir_precio)
        self.combo_categoria.grid(row=3, column=1, padx=10, pady=5)
        self.combo_categoria.set("")
        self.combo_categoria.bind("<KeyRelease>", self.sugerir_precio)

        ctk.CTkLabel(f_abm, text="Costo Compra ($):").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.ent_costo = ctk.CTkEntry(f_abm, width=180)
        self.ent_costo.grid(row=4, column=1, padx=10, pady=5)
        self.ent_costo.bind("<KeyRelease>", self.sugerir_precio)

        ctk.CTkLabel(f_abm, text="Precio Venta ($):").grid(row=5, column=0, sticky="w", padx=10, pady=5)
        self.ent_precio = ctk.CTkEntry(f_abm, width=180, text_color="#2ecc71")
        self.ent_precio.grid(row=5, column=1, padx=10, pady=5)

        ctk.CTkLabel(f_abm, text="Stock Actual:").grid(row=6, column=0, sticky="w", padx=10, pady=5)
        self.ent_stock = ctk.CTkEntry(f_abm, width=180)
        self.ent_stock.grid(row=6, column=1, padx=10, pady=5)

        ctk.CTkLabel(f_abm, text="Codigo Barras:").grid(row=7, column=0, sticky="w", padx=10, pady=5)
        self.ent_codigo = ctk.CTkEntry(f_abm, width=180)
        self.ent_codigo.grid(row=7, column=1, padx=10, pady=5)

        btn_frame = ctk.CTkFrame(f_abm, fg_color="transparent")
        btn_frame.grid(row=8, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frame, text="GUARDAR", fg_color="#27ae60", hover_color="#219a52", 
                      font=("Arial", 12, "bold"), width=100, command=self.guardar_producto_ui).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="LIMPIAR", fg_color="#7f8c8d", hover_color="#626567", 
                      width=100, command=self.limpiar_formulario).pack(side="left", padx=5)

        # 2. Boton de Mermas (V2.0)
        self.btn_merma = ctk.CTkButton(panel_izquierdo, text="🚨 REGISTRAR MERMA/PERDIDA", fg_color="#c0392b", 
                                       hover_color="#922b21", font=("Arial", 12, "bold"), command=self.abrir_modal_merma)
        self.btn_merma.pack(fill="x", pady=5)
        self.btn_merma.configure(state="disabled") # Se activa solo al seleccionar un producto

        # 3. Herramienta Lote
        f_lote = ctk.CTkFrame(panel_izquierdo, corner_radius=10)
        f_lote.pack(fill="x", pady=10)
        ctk.CTkLabel(f_lote, text="Aumento Masivo", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(10, 5))

        ctk.CTkLabel(f_lote, text="Categoria:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.combo_cat_lote = ctk.CTkComboBox(f_lote, width=160, state="readonly")
        self.combo_cat_lote.grid(row=1, column=1, padx=10, pady=5)
        self.combo_cat_lote.set("")

        ctk.CTkLabel(f_lote, text="Aumento (%):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.ent_porcentaje = ctk.CTkEntry(f_lote, width=160)
        self.ent_porcentaje.grid(row=2, column=1, padx=10, pady=5)

        ctk.CTkButton(f_lote, text="APLICAR", fg_color="#e67e22", hover_color="#d35400", 
                      font=("Arial", 12, "bold"), command=self.aplicar_aumento_lote).grid(row=3, column=0, columnspan=2, pady=10)

        # === COLUMNA DERECHA: TABLA MAESTRA ===
        panel_derecho = ctk.CTkFrame(container, fg_color="transparent")
        panel_derecho.pack(side="right", fill="both", expand=True)

        header_frame = ctk.CTkFrame(panel_derecho, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(header_frame, text="Catalogo de Productos", font=("Arial", 18, "bold")).pack(side="left")
        ctk.CTkButton(header_frame, text="REFRESCAR", width=120, fg_color="#34495e", hover_color="#2c3e50", 
                      command=self.refresh_inventory_view).pack(side="right")

        f_tabla = ctk.CTkFrame(panel_derecho, corner_radius=10)
        f_tabla.pack(fill="both", expand=True)

        cols = ("ID", "Producto", "Categoria", "Precio", "Stock")
        self.tree_inv = ttk.Treeview(f_tabla, columns=cols, show='headings', height=20)
        
        self.tree_inv.heading("ID", text="ID")
        self.tree_inv.column("ID", width=40, anchor="center")
        self.tree_inv.heading("Producto", text="Nombre del Producto")
        self.tree_inv.heading("Categoria", text="Categoria")
        self.tree_inv.heading("Precio", text="Precio Venta")
        self.tree_inv.column("Precio", width=100, anchor="center")
        self.tree_inv.heading("Stock", text="En Inventario")
        self.tree_inv.column("Stock", width=100, anchor="center")
        
        self.tree_inv.tag_configure('bajo_stock', background='#4a2322', foreground='#e74c3c')
        self.tree_inv.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tree_inv.bind('<ButtonRelease-1>', self.on_tree_select)
        self.refresh_inventory_view()

    def sugerir_precio(self, event=None):
        costo_str = self.ent_costo.get().strip()
        cat = self.combo_categoria.get().strip().title()
        if not costo_str: return
        try:
            costo = float(costo_str)
            margen = self.margenes_sugeridos.get(cat, self.margenes_sugeridos["Default"])
            precio_sugerido = float(math.ceil((costo * margen) / 50.0) * 50.0)
            self.ent_precio.delete(0, tk.END)
            self.ent_precio.insert(0, str(precio_sugerido))
        except ValueError:
            pass 

    def refresh_inventory_view(self) -> None:
        for i in self.tree_inv.get_children(): 
            self.tree_inv.delete(i)
        productos = self.servicio.obtener_catalogo()
        categorias_existentes = set(self.margenes_sugeridos.keys())

        for prod in productos:
            if prod.categoria: categorias_existentes.add(prod.categoria.title())
            precio_str = f"$ {prod.costo_venta:,.2f}"
            tags = ('bajo_stock',) if prod.stock < 5 else ()
            self.tree_inv.insert("", tk.END, values=(prod.id_producto, prod.nombre_producto, prod.categoria, precio_str, prod.stock), tags=tags)

        cats_ordenadas = sorted(list(categorias_existentes))
        self.combo_categoria.configure(values=cats_ordenadas)
        self.combo_cat_lote.configure(values=cats_ordenadas)
        self.btn_merma.configure(state="disabled")

    def on_tree_select(self, event) -> None:
        selected = self.tree_inv.focus()
        if not selected: return
        valores = self.tree_inv.item(selected, 'values')
        if not valores: return
        
        id_prod = int(valores[0])
        productos = self.servicio.obtener_catalogo()
        prod_seleccionado = next((p for p in productos if p.id_producto == id_prod), None)
        
        if prod_seleccionado:
            self.limpiar_formulario()
            self.ent_id.configure(state="normal")
            self.ent_id.insert(0, str(prod_seleccionado.id_producto))
            self.ent_id.configure(state="readonly")
            self.ent_nombre.insert(0, prod_seleccionado.nombre_producto)
            self.combo_categoria.set(prod_seleccionado.categoria)
            self.ent_costo.insert(0, str(prod_seleccionado.costo_compra))
            self.ent_precio.insert(0, str(prod_seleccionado.costo_venta))
            self.ent_stock.insert(0, str(prod_seleccionado.stock))
            self.ent_codigo.insert(0, prod_seleccionado.barcode if prod_seleccionado.barcode else "")
            
            self.btn_merma.configure(state="normal") # Activamos el boton rojo

    def limpiar_formulario(self) -> None:
        self.ent_id.configure(state="normal")
        self.ent_id.delete(0, tk.END)
        self.ent_id.configure(state="readonly")
        self.ent_nombre.delete(0, tk.END)
        self.combo_categoria.set('')
        self.ent_costo.delete(0, tk.END)
        self.ent_precio.delete(0, tk.END)
        self.ent_stock.delete(0, tk.END)
        self.ent_codigo.delete(0, tk.END)
        self.btn_merma.configure(state="disabled")

    def guardar_producto_ui(self) -> None:
        if not self.ent_nombre.get().strip():
            messagebox.showwarning("Faltan datos", "El nombre es obligatorio.")
            return

        codigo_barras = self.ent_codigo.get().strip()
        if codigo_barras == "": codigo_barras = None

        data_dict = {
            'id_producto': self.ent_id.get(), 'nombre_producto': self.ent_nombre.get(),
            'categoria': self.combo_categoria.get(), 'costo_compra': self.ent_costo.get(),
            'costo_venta': self.ent_precio.get(), 'stock': self.ent_stock.get(), 'barcode': codigo_barras
        }

        try:
            self.servicio.guardar_producto(data_dict)
            messagebox.showinfo("Exito", "Producto guardado correctamente.")
            self.limpiar_formulario()
            self.refresh_inventory_view()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def aplicar_aumento_lote(self) -> None:
        cat = self.combo_cat_lote.get().strip()
        pct_str = self.ent_porcentaje.get().strip()
        if not cat or not pct_str: return messagebox.showwarning("Faltan datos", "Ingrese categoria y porcentaje.")
            
        try:
            pct = float(pct_str)
            if messagebox.askyesno("Confirmar", f"¿Aumentar {pct}% a la categoria '{cat}'?"):
                afectados = self.servicio.aplicar_aumento_masivo(cat, pct)
                messagebox.showinfo("Exito", f"Se actualizaron {afectados} productos.")
                self.ent_porcentaje.delete(0, tk.END)
                self.combo_cat_lote.set('')
                self.refresh_inventory_view()
        except ValueError as e:
             messagebox.showerror("Error", f"Verifique los datos: {e}")

    # --- NUEVA FUNCION: Modal de Mermas ---
    def abrir_modal_merma(self) -> None:
        id_str = self.ent_id.get()
        if not id_str: return
        
        id_prod = int(id_str)
        nombre_prod = self.ent_nombre.get()
        stock_actual = float(self.ent_stock.get())
        
        # Pedimos cantidad
        cant_str = simpledialog.askstring("Merma", f"Producto: {nombre_prod}\nStock actual: {stock_actual}\n\n¿Cuantas unidades se perdieron/rompieron?")
        if not cant_str: return
        
        try:
            cantidad = float(cant_str)
            if cantidad <= 0: raise ValueError("La cantidad debe ser mayor a 0")
        except ValueError:
            return messagebox.showerror("Error", "Ingrese una cantidad numerica valida.")

        # Pedimos motivo usando un dialogo simple por ahora
        motivo = simpledialog.askstring("Motivo", "¿Cual fue el motivo? (Ej: Vencido, Roto, Robado, Falla de Fabrica)")
        if not motivo: motivo = "No especificado"

        try:
            self.servicio.registrar_merma(id_prod, cantidad, motivo)
            messagebox.showinfo("Exito", "Merma registrada correctamente. El stock ha sido actualizado.")
            self.limpiar_formulario()
            self.refresh_inventory_view()
        except Exception as e:
            messagebox.showerror("Error", str(e))   