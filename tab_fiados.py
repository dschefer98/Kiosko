"""Modulo de Interfaz Grafica (CustomTkinter) para Cuentas Corrientes."""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk

from services import FiadosService, InventarioService
from database import DatabaseManager

class TabFiados:
    """Vista para el control de deudores y conciliacion de saldos."""

    def __init__(self, parent: ctk.CTkFrame, db_manager: DatabaseManager):
        self.parent = parent
        self.fiados_service = FiadosService(db_manager)
        self.inv_service = InventarioService(db_manager)
        
        self.after_id = None
        self.cliente_seleccionado_id = None
        
        self.frame = self.parent
        self.var_precios_actualizados = ctk.BooleanVar(value=False)
        
        self.setup_ui()

    def setup_ui(self) -> None:
        cont = ctk.CTkFrame(self.frame, fg_color="transparent")
        cont.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- COLUMNA IZQUIERDA: CONTROLES ---
        izq = ctk.CTkFrame(cont, width=400, fg_color="transparent")
        izq.pack(side="left", fill="y", padx=10)
        
        ctk.CTkLabel(izq, text="GESTION DE DEUDORES", font=("Arial", 16, "bold")).pack(pady=10)
        
        f_cliente = ctk.CTkFrame(izq, corner_radius=10)
        f_cliente.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(f_cliente, text="Seleccionar o Crear Cliente:").pack(pady=(10, 0))
        
        # Mantenemos ttk.Combobox porque soporta postcommand y escritura libre
        self.combo_clientes = ttk.Combobox(f_cliente, font=("Arial", 12), width=30)
        self.combo_clientes.pack(pady=10, padx=10)
        self.combo_clientes.config(postcommand=self.cargar_comboboxes)
        self.combo_clientes.bind("<KeyRelease>", self.debounced_ver_deuda)
        self.combo_clientes.bind("<<ComboboxSelected>>", self._ejecutar_busqueda_deuda)
        
        self.check_precios = ctk.CTkCheckBox(
            izq, 
            text="Toggle de Valorizacion (Precios de Hoy)", 
            variable=self.var_precios_actualizados, 
            command=self._ejecutar_busqueda_deuda
        )
        self.check_precios.pack(pady=10)
        
        self.lbl_deuda = ctk.CTkLabel(izq, text="Deuda Total: $ 0.00", font=("Arial", 22, "bold"))
        self.lbl_deuda.pack(pady=15)

        # 1. Registrar Cargo
        f_cargo = ctk.CTkFrame(izq, corner_radius=10)
        f_cargo.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(f_cargo, text="1. Anadir Cargo a Cuenta", font=("Arial", 12, "bold")).pack(pady=(10, 5))
        
        self.combo_prod_fiado = ttk.Combobox(f_cargo, font=("Arial", 12), width=30)
        self.combo_prod_fiado.pack(pady=5, padx=10)
        self.combo_prod_fiado.config(postcommand=self.cargar_comboboxes)
        
        ctk.CTkButton(f_cargo, text="CARGAR A CUENTA", fg_color="#e74c3c", hover_color="#c0392b", 
                      font=("Arial", 12, "bold"), command=self.registrar_cargo_fiado).pack(pady=10)

        # 2. Registrar Pago
        f_abono = ctk.CTkFrame(izq, corner_radius=10)
        f_abono.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(f_abono, text="2. Registrar Abono / Pago", font=("Arial", 12, "bold")).pack(pady=(10, 5))
        
        self.entry_abono = ctk.CTkEntry(f_abono, font=("Arial", 16), width=150, justify="center")
        self.entry_abono.pack(pady=5)
        
        btns = ctk.CTkFrame(f_abono, fg_color="transparent")
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="PAGO EFECTIVO", fg_color="#27ae60", hover_color="#219a52", 
                      width=120, command=lambda: self.registrar_pago_fiado(1)).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="PAGO TRANSF.", fg_color="#2980b9", hover_color="#2471a3", 
                      width=120, command=lambda: self.registrar_pago_fiado(2)).pack(side="left", padx=5)

        # --- COLUMNA DERECHA: GRILLA DE ESTADO DE CUENTA ---
        der = ctk.CTkFrame(cont, corner_radius=10)
        der.pack(side="right", fill="both", expand=True, padx=10)
        
        self.tree = ttk.Treeview(der, columns=('Deuda',), show='tree headings')
        self.tree.heading('#0', text='Detalle de Cargos Pendientes')
        self.tree.column('#0', width=350)
        self.tree.heading('Deuda', text='Monto Adeudado')
        self.tree.column('Deuda', width=120, anchor='e')
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.cargar_comboboxes()

    def cargar_comboboxes(self) -> None:
        clientes = self.fiados_service.obtener_clientes()
        self.combo_clientes['values'] = [c.nombre_alias for c in clientes]
        
        productos = self.inv_service.obtener_catalogo()
        self.productos_map = {p.nombre_producto: p.id_producto for p in productos}
        self.combo_prod_fiado['values'] = sorted(list(self.productos_map.keys()))

    def debounced_ver_deuda(self, event) -> None:
        if self.after_id: self.combo_clientes.after_cancel(self.after_id)
        self.after_id = self.combo_clientes.after(500, self._ejecutar_busqueda_deuda)

    def _ejecutar_busqueda_deuda(self, event=None) -> None:
        alias = self.combo_clientes.get().strip()
        if not alias: return

        try:
            cliente = self.fiados_service.obtener_o_crear_cliente(alias)
            self.cliente_seleccionado_id = cliente.id_cliente
            
            estado = self.fiados_service.obtener_estado_cuenta(
                id_cliente=cliente.id_cliente, 
                usar_precio_actualizado=self.var_precios_actualizados.get()
            )
            
            deuda = estado['deuda_total']
            color_deuda = "#e74c3c" if deuda > 0 else "#2ecc71"
            self.lbl_deuda.configure(text=f"Deuda Total: $ {deuda:,.2f}", text_color=color_deuda)
            
            self.renderizar_grilla(cliente.nombre_alias, estado['detalle'])
            
        except Exception as e:
            self.lbl_deuda.configure(text="Error de busqueda", text_color="red")

    def renderizar_grilla(self, nombre_cliente: str, detalle_pendientes: list) -> None:
        for i in self.tree.get_children(): self.tree.delete(i)
        
        if not detalle_pendientes:
            self.tree.insert("", tk.END, text="✅ Cuenta al dia. Sin deudas pendientes.")
            return

        padre = self.tree.insert("", tk.END, text=f"👤 {nombre_cliente}", open=True)
        
        for item in detalle_pendientes:
            texto = f"  ↳ {item['producto']} ({item['fecha']})"
            monto_str = f"$ {item['deuda_item']:,.2f}"
            self.tree.insert(padre, tk.END, text=texto, values=(monto_str,))

    def registrar_cargo_fiado(self) -> None:
        if not self.cliente_seleccionado_id:
            messagebox.showwarning("Atencion", "Seleccione o escriba un cliente valido.")
            return
            
        prod_nombre = self.combo_prod_fiado.get().strip()
        id_prod = self.productos_map.get(prod_nombre)
        
        if not id_prod:
            messagebox.showwarning("Atencion", "Seleccione un producto del catalogo.")
            return

        try:
            self.fiados_service.registrar_cargo(self.cliente_seleccionado_id, id_prod)
            self.combo_prod_fiado.set('')
            self._ejecutar_busqueda_deuda()
            messagebox.showinfo("Exito", "Cargo anadido a la cuenta.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def registrar_pago_fiado(self, id_metodo_pago: int) -> None:
        if not self.cliente_seleccionado_id:
            messagebox.showwarning("Atencion", "Seleccione un cliente para registrar el pago.")
            return
            
        try:
            monto = float(self.entry_abono.get().strip())
            self.fiados_service.registrar_pago(self.cliente_seleccionado_id, monto, id_metodo_pago, self.var_precios_actualizados.get())
            self.entry_abono.delete(0, tk.END)
            self._ejecutar_busqueda_deuda()
        except ValueError:
            messagebox.showerror("Error", "Ingrese un monto numerico valido para el abono.")
        except Exception as e:
            messagebox.showerror("Error", str(e))