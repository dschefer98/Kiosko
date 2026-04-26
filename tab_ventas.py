"""Modulo de Interfaz Grafica (CustomTkinter) para el Punto de Venta y Control de Caja."""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from datetime import datetime
from typing import List, Dict, Any

from services import InventarioService, VentasService, CajaService
from database import DatabaseManager

class TabVentas:
    """Vista principal que consolida el Carrito de Ventas, Turnos y Gastos (V2.0)."""

    def __init__(self, parent: ctk.CTkFrame, db_manager: DatabaseManager, root_window: ctk.CTk):
        self.parent = parent
        self.root = root_window
        
        self.inv_service = InventarioService(db_manager)
        self.ventas_service = VentasService(db_manager)
        self.caja_service = CajaService(db_manager)
        
        self.frame = self.parent
        
        self.carrito: List[Dict[str, Any]] = []
        self.producto_seleccionado = None
        self.total_carrito = 0.0
        self.var_redondear = ctk.BooleanVar(value=True)
        
        self.setup_ui()
        self.configurar_atajos_teclado()
        
        self.verificar_estado_turno()
        self.actualizar_fechas_disponibles()

    def configurar_atajos_teclado(self) -> None:
        self.root.bind('<F1>', lambda e: self.cobrar_carrito(1))
        self.root.bind('<F2>', lambda e: self.cobrar_carrito(2))
        self.root.bind('<F3>', lambda e: self.combo_productos.focus_set())
        self.root.bind('<Escape>', lambda e: self.limpiar_inputs())

    def setup_ui(self) -> None:
        # --- PANEL SUPERIOR: CONTROL DE TURNO ---
        self.frame_turno = ctk.CTkFrame(self.frame, fg_color="#1f538d", corner_radius=0)
        self.frame_turno.pack(fill="x")
        
        self.lbl_estado_turno = ctk.CTkLabel(self.frame_turno, text="", font=("Arial", 14, "bold"), text_color="white")
        self.lbl_estado_turno.pack(side="left", padx=20, pady=5)
        
        self.btn_accion_turno = ctk.CTkButton(self.frame_turno, text="", font=("Arial", 12, "bold"), command=self.gestionar_turno)
        self.btn_accion_turno.pack(side="right", padx=20, pady=5)

        # --- SECCION 1: CARRITO DE VENTAS ---
        f_busqueda = ctk.CTkFrame(self.frame, fg_color="transparent")
        f_busqueda.pack(fill="x", pady=10, padx=20)
        
        ctk.CTkLabel(f_busqueda, text="BUSCAR PRODUCTO (F3)", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 10))
        
        self.combo_productos = ttk.Combobox(f_busqueda, font=("Arial", 14), width=40)
        self.combo_productos.pack(side="left", padx=10)
        self.combo_productos.config(postcommand=self.cargar_productos_busqueda)
        self.combo_productos.bind("<KeyRelease>", self.buscar_producto_tipeado)
        self.combo_productos.bind("<<ComboboxSelected>>", self.on_producto_seleccionado)
        
        # Controles de Cantidad / Peso
        self.f_inputs = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.f_inputs.pack(fill="x", padx=20, pady=5)
        
        self.f_cantidad = ctk.CTkFrame(self.f_inputs, fg_color="transparent")
        ctk.CTkLabel(self.f_cantidad, text="Cantidad:", font=("Arial", 12)).pack(side="left")
        self.entry_cantidad = ctk.CTkEntry(self.f_cantidad, width=60, font=("Arial", 14), justify="center")
        self.entry_cantidad.insert(0, "1")
        self.entry_cantidad.pack(side="left", padx=10)
        
        self.f_peso = ctk.CTkFrame(self.f_inputs, fg_color="transparent")
        ctk.CTkLabel(self.f_peso, text="Gramos:", font=("Arial", 12)).pack(side="left")
        self.entry_peso = ctk.CTkEntry(self.f_peso, width=80, font=("Arial", 14))
        self.entry_peso.pack(side="left", padx=10)
        
        self.check_redondeo = ctk.CTkCheckBox(self.f_peso, text="Redondear Multiplo 50", variable=self.var_redondear, font=("Arial", 12))
        self.check_redondeo.pack(side="left", padx=15)
        
        ctk.CTkButton(self.f_inputs, text="AGREGAR AL CARRITO", fg_color="#34495e", hover_color="#2c3e50", 
                      font=("Arial", 12, "bold"), command=self.agregar_al_carrito).pack(side="right")
        
        self.f_peso.pack_forget()
        self.f_cantidad.pack(side="left")

        # Grilla del Carrito
        f_grilla = ctk.CTkFrame(self.frame, corner_radius=10)
        f_grilla.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.tree_carrito = ttk.Treeview(f_grilla, columns=("Producto", "Cant/Peso", "Subtotal"), show='headings', height=6)
        self.tree_carrito.heading("Producto", text="Producto")
        self.tree_carrito.heading("Cant/Peso", text="Cantidad/Peso")
        self.tree_carrito.heading("Subtotal", text="Subtotal")
        self.tree_carrito.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Total y Botones de Cobro
        f_cobro = ctk.CTkFrame(self.frame, fg_color="#2b2b2b", corner_radius=10)
        f_cobro.pack(fill="x", padx=20, pady=5)
        
        self.lbl_total = ctk.CTkLabel(f_cobro, text="TOTAL: $ 0.00", font=("Arial", 30, "bold"), text_color="#2ecc71")
        self.lbl_total.pack(side="left", padx=30, pady=15)

        # NUEVO: BOTON DESHACER (Ahora vive en la barra negra, junto al TOTAL)
        self.btn_deshacer = ctk.CTkButton(
            f_cobro, 
            text="↩️ DESHACER ULTIMA VENTA", 
            fg_color="#c0392b", 
            hover_color="#922b21", 
            font=("Arial", 12, "bold"),
            height=40,
            command=self.deshacer_ultima_venta_ui
        )
        self.btn_deshacer.pack(side="left", padx=20)
        
        ctk.CTkButton(f_cobro, text="💵 EFECTIVO (F1)", fg_color="#27ae60", hover_color="#219a52", font=("Arial", 12, "bold"), 
                      width=140, height=40, command=lambda: self.cobrar_carrito(1)).pack(side="right", padx=10)
        ctk.CTkButton(f_cobro, text="📱 TRANSF. (F2)", fg_color="#2980b9", hover_color="#2471a3", font=("Arial", 12, "bold"), 
                      width=140, height=40, command=lambda: self.cobrar_carrito(2)).pack(side="right", padx=10)
        ctk.CTkButton(f_cobro, text="🗑️ VACIAR", fg_color="#e74c3c", hover_color="#c0392b", font=("Arial", 12, "bold"), 
                      width=100, height=40, command=self.vaciar_carrito).pack(side="right", padx=20)

        # --- SECCION 2: GASTOS Y RESUMEN ---
        f_bottom = ctk.CTkFrame(self.frame, fg_color="transparent")
        f_bottom.pack(fill="x", padx=20, pady=10)
        
        f_gastos = ctk.CTkFrame(f_bottom, corner_radius=10)
        f_gastos.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(f_gastos, text="Registro de Egresos de Caja", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=7, pady=10)
        
        ctk.CTkLabel(f_gastos, text="Categoria:").grid(row=1, column=0, padx=5, pady=5)
        self.combo_gasto_cat = ctk.CTkComboBox(f_gastos, values=["Proveedores", "Servicios", "Sueldos", "Retiros", "Otros"], width=130, state="readonly")
        self.combo_gasto_cat.grid(row=1, column=1, padx=5)
        
        ctk.CTkLabel(f_gastos, text="Detalle:").grid(row=1, column=2, padx=5, pady=5)
        self.entry_gasto_desc = ctk.CTkEntry(f_gastos, width=150)
        self.entry_gasto_desc.grid(row=1, column=3, padx=5)
        
        ctk.CTkLabel(f_gastos, text="Monto ($):").grid(row=1, column=4, padx=5, pady=5)
        self.entry_gasto_monto = ctk.CTkEntry(f_gastos, width=100)
        self.entry_gasto_monto.grid(row=1, column=5, padx=5)
        
        ctk.CTkButton(f_gastos, text="CARGAR", fg_color="#e67e22", hover_color="#d35400", width=80, command=self.registrar_gasto).grid(row=1, column=6, padx=10)

        # FRAME DE RESUMEN DIARIO
        f_resumen = ctk.CTkFrame(f_bottom, corner_radius=10)
        f_resumen.pack(side="right", fill="both")
        
        ctk.CTkLabel(f_resumen, text="Resumen Diario", font=("Arial", 12, "bold")).pack(pady=5)
        
        self.combo_fechas = ctk.CTkComboBox(f_resumen, state="readonly", width=120, command=self.actualizar_resumen_caja)
        self.combo_fechas.pack(pady=5, padx=20)
        
        self.lbl_t_efec = ctk.CTkLabel(f_resumen, text="Efectivo: $ 0.00", text_color="#2ecc71", font=("Arial", 12, "bold"))
        self.lbl_t_efec.pack()
        self.lbl_t_transf = ctk.CTkLabel(f_resumen, text="Transf.: $ 0.00", text_color="#3498db", font=("Arial", 12, "bold"))
        self.lbl_t_transf.pack()
        self.lbl_t_gastos = ctk.CTkLabel(f_resumen, text="Gastos: $ 0.00", text_color="#e74c3c", font=("Arial", 12, "bold"))
        self.lbl_t_gastos.pack(pady=(0, 10))

        self.cargar_productos_busqueda()

    def verificar_estado_turno(self) -> None:
        turno = self.caja_service.obtener_turno_activo()
        if turno:
            self.lbl_estado_turno.configure(text=f"🟢 Turno Abierto | Fondo: $ {turno.fondo_inicial:,.2f}")
            self.btn_accion_turno.configure(text="CERRAR TURNO", fg_color="#c0392b", hover_color="#a93226")
        else:
            self.lbl_estado_turno.configure(text="🔴 Turno Cerrado")
            self.btn_accion_turno.configure(text="ABRIR TURNO", fg_color="#27ae60", hover_color="#219a52")

    def gestionar_turno(self) -> None:
        turno = self.caja_service.obtener_turno_activo()
        if not turno:
            fondo_str = simpledialog.askstring("Apertura", "Ingrese el Fondo Inicial ($):", parent=self.root)
            if fondo_str is not None:
                try:
                    fondo = float(fondo_str)
                    self.caja_service.abrir_turno(fondo)
                    self.verificar_estado_turno()
                    messagebox.showinfo("Exito", "Turno iniciado correctamente.")
                except ValueError as e:
                    messagebox.showerror("Error", str(e))
        else:
            self.realizar_arqueo()

    def realizar_arqueo(self) -> None:
        try:
            datos = self.caja_service.precalcular_arqueo()
            msg_arqueo = (
                f"Fondo Inicial: $ {datos['fondo_inicial']:,.2f}\n"
                f"Ingresos (Efectivo): $ {datos['ingresos_efectivo']:,.2f}\n"
                f"Egresos (Gastos): $ {datos['egresos']:,.2f}\n\n"
                f"TOTAL ESPERADO: $ {datos['total_teorico']:,.2f}\n\n"
                "Ingrese el dinero real contado:"
            )
            monto_real_str = simpledialog.askstring("Arqueo", msg_arqueo, parent=self.root)
            if monto_real_str is not None:
                monto_real = float(monto_real_str)
                _, diferencia = self.caja_service.cerrar_turno(monto_real)
                self.verificar_estado_turno()
                messagebox.showinfo("Resultado", f"Diferencia: $ {diferencia:,.2f}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def registrar_gasto(self) -> None:
        cat = self.combo_gasto_cat.get()
        desc = self.entry_gasto_desc.get().strip()
        monto_str = self.entry_gasto_monto.get().strip()
        if not cat or not monto_str: return
        try:
            self.caja_service.registrar_gasto(cat, desc, float(monto_str))
            self.entry_gasto_desc.delete(0, tk.END)
            self.entry_gasto_monto.delete(0, tk.END)
            self.actualizar_resumen_caja()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def actualizar_fechas_disponibles(self) -> None:
        hoy = datetime.now().strftime("%Y-%m-%d") 
        datos = self.caja_service.obtener_resumen_diario(hoy)
        self.combo_fechas.configure(values=datos['fechas_disponibles'])
        self.combo_fechas.set(hoy)
        self.actualizar_resumen_caja()

    def actualizar_resumen_caja(self, event=None) -> None:
        fecha_sel = self.combo_fechas.get()
        if not fecha_sel: return
        datos = self.caja_service.obtener_resumen_diario(fecha_sel)
        self.lbl_t_efec.configure(text=f"Efectivo: $ {datos['efectivo']:,.2f}")
        self.lbl_t_transf.configure(text=f"Transf.: $ {datos['transferencia']:,.2f}")
        self.lbl_t_gastos.configure(text=f"Gastos: $ {datos['gastos']:,.2f}")

    def cargar_productos_busqueda(self):
        productos = self.inv_service.obtener_catalogo()
        self.productos_en_memoria = {p.nombre_producto: p for p in productos}
        self.combo_productos['values'] = list(self.productos_en_memoria.keys())

    def buscar_producto_tipeado(self, event) -> None:
        if event.keysym in ('Up', 'Down', 'Return', 'Escape'): return
        texto = self.combo_productos.get().lower()
        if not hasattr(self, 'productos_en_memoria'): self.cargar_productos_busqueda()
        nombres = list(self.productos_en_memoria.keys())
        self.combo_productos['values'] = [n for n in nombres if texto in n.lower()]
        self.combo_productos.event_generate('<Down>')

    def on_producto_seleccionado(self, event):
        nombre = self.combo_productos.get().strip()
        self.producto_seleccionado = self.productos_en_memoria.get(nombre)
        if self.producto_seleccionado:
            if self.producto_seleccionado.categoria.lower() == 'fiambres':
                self.f_cantidad.pack_forget()
                self.f_peso.pack(side="left")
                self.entry_peso.focus()
            else:
                self.f_peso.pack_forget()
                self.f_cantidad.pack(side="left")
                self.entry_cantidad.focus()

    def agregar_al_carrito(self):
        if not self.producto_seleccionado: return
        es_peso = self.producto_seleccionado.categoria.lower() == 'fiambres'
        try:
            valor_input = float(self.entry_peso.get()) if es_peso else float(self.entry_cantidad.get())
            subtotal = self.ventas_service.calcular_subtotal(self.producto_seleccionado, valor_input, es_peso, self.var_redondear.get())
            self.carrito.append({'producto': self.producto_seleccionado, 'cantidad': valor_input, 'es_peso': es_peso, 'subtotal': subtotal})
            desc = f"{valor_input} gr" if es_peso else f"{int(valor_input)} un"
            self.tree_carrito.insert("", tk.END, values=(self.producto_seleccionado.nombre_producto, desc, f"$ {subtotal:,.2f}"))
            self.total_carrito += subtotal
            self.lbl_total.configure(text=f"TOTAL: $ {self.total_carrito:,.2f}")
            self.limpiar_inputs()
        except ValueError:
            messagebox.showerror("Error", "Cantidad invalida.")

    def cobrar_carrito(self, id_metodo_pago: int):
        if not self.caja_service.obtener_turno_activo(): return messagebox.showwarning("Atencion", "Abra turno primero.")
        if not self.carrito: return
        try:
            id_ticket = self.ventas_service.procesar_ticket_completo(self.carrito, id_metodo_pago)
            self.vaciar_carrito()
            self.actualizar_resumen_caja()
            messagebox.showinfo("Venta Exitosa", f"Ticket: {id_ticket}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def limpiar_inputs(self):
        self.combo_productos.set('')
        self.producto_seleccionado = None
        self.entry_cantidad.delete(0, tk.END)
        self.entry_cantidad.insert(0, "1")
        self.entry_peso.delete(0, tk.END)
        self.combo_productos.focus_set()

    def vaciar_carrito(self):
        self.carrito.clear()
        self.total_carrito = 0.0
        self.lbl_total.configure(text="TOTAL: $ 0.00")
        for i in self.tree_carrito.get_children(): self.tree_carrito.delete(i)
        self.limpiar_inputs()
    
    def deshacer_ultima_venta_ui(self) -> None:
        """Rollback de la ultima venta registrada."""
        confirmacion = messagebox.askyesno("Anular Venta", "¿Desea ANULAR el ultimo ticket?\nSe devolvera el stock y restara el monto de caja.")
        if confirmacion:
            try:
                ticket = self.caja_service.anular_ultimo_ticket() 
                messagebox.showinfo("Exito", f"Ticket {ticket} anulado.")
                self.actualizar_resumen_caja() 
            except Exception as e:
                messagebox.showerror("Error", str(e))