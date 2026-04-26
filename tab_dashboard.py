"""Modulo de Interfaz Grafica para Business Intelligence y Analitica."""

import customtkinter as ctk
import tkinter as tk  # <-- ¡Esta es la línea que faltaba!
from tkinter import ttk

from database import DatabaseManager
from services import BIService

class TabDashboard:
    """Panel de control gerencial con analisis predictivo."""

    def __init__(self, parent: ctk.CTkFrame, db_manager: DatabaseManager):
        self.parent = parent
        self.bi_service = BIService(db_manager)
        
        self.frame = self.parent
        self.setup_ui()

    def setup_ui(self) -> None:
        # Cabecera
        header = ctk.CTkFrame(self.frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(header, text="📊 Panel de Business Intelligence", font=("Arial", 24, "bold")).pack(side="left")
        ctk.CTkButton(header, text="🔄 ACTUALIZAR PREDICCIONES", fg_color="#2980b9", hover_color="#2471a3", 
                      command=self.cargar_datos_predictivos).pack(side="right")

        # Contenedor principal dividido en dos columnas
        main_container = ctk.CTkFrame(self.frame, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=5)
        
        # --- COLUMNA IZQUIERDA: PREDICCIONES DE STOCK ---
        col_izq = ctk.CTkFrame(main_container, corner_radius=10)
        col_izq.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        lbl_titulo = ctk.CTkLabel(col_izq, text="🔮 Predicción de Quiebre de Stock (Próx. 5 días)", font=("Arial", 14, "bold"), text_color="#f39c12")
        lbl_titulo.pack(pady=15)
        
        ctk.CTkLabel(col_izq, text="El sistema analiza el ritmo de venta del último mes para avisarte\nqué productos se agotarán pronto basándose en la demanda real.", 
                     font=("Arial", 11), text_color="gray").pack(pady=(0, 10))

        # Grilla de alertas
        f_tabla = ctk.CTkFrame(col_izq, fg_color="transparent")
        f_tabla.pack(fill="both", expand=True, padx=15, pady=10)
        
        cols = ("Producto", "Estado", "Autonomia Estimada")
        self.tree_alertas = ttk.Treeview(f_tabla, columns=cols, show='headings', height=15)
        
        self.tree_alertas.heading("Producto", text="Producto en Riesgo")
        self.tree_alertas.heading("Estado", text="Gravedad")
        self.tree_alertas.column("Estado", width=100, anchor="center")
        self.tree_alertas.heading("Autonomia Estimada", text="Tiempo Restante")
        self.tree_alertas.column("Autonomia Estimada", width=150, anchor="center")
        
        self.tree_alertas.tag_configure('agotado', background='#4a2322', foreground='#e74c3c')
        self.tree_alertas.tag_configure('critico', background='#5c3a21', foreground='#f39c12')
        
        self.tree_alertas.pack(fill="both", expand=True)

        # --- COLUMNA DERECHA: FUTUROS KPIs ---
        col_der = ctk.CTkFrame(main_container, width=300, corner_radius=10)
        col_der.pack(side="right", fill="y")
        
        ctk.CTkLabel(col_der, text="Métricas de Rentabilidad", font=("Arial", 14, "bold")).pack(pady=15, padx=20)
        ctk.CTkLabel(col_der, text="En desarrollo para V2.1:\n\n• Ganancia Bruta Mensual\n• Top 5 Productos más rentables\n• Horarios pico de ventas", 
                     font=("Arial", 12), text_color="#7f8c8d", justify="left").pack(pady=20, padx=20, anchor="w")

        # Carga inicial
        self.cargar_datos_predictivos()

    def cargar_datos_predictivos(self) -> None:
        # Limpiar tabla
        for i in self.tree_alertas.get_children():
            self.tree_alertas.delete(i)
            
        try:
            alertas = self.bi_service.predecir_quiebres_stock()
            
            if not alertas:
                self.tree_alertas.insert("", tk.END, values=("Inventario Sano", "OK", "Sin riesgo inminente"))
                return
                
            for alerta in alertas:
                estado = alerta['estado']
                if estado == 'AGOTADO':
                    texto_tiempo = "0 días (Urgente)"
                    tag = ('agotado',)
                else:
                    texto_tiempo = f"Aprox. {alerta['dias_restantes']} días"
                    tag = ('critico',)
                    
                self.tree_alertas.insert("", tk.END, values=(alerta['producto'], estado, texto_tiempo), tags=tag)
                
        except Exception as e:
            # Si hay un error (ej. tabla vacía), lo mostramos suavemente
            self.tree_alertas.insert("", tk.END, values=("Esperando datos...", "-", "-"))