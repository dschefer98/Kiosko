"""Widget Flotante para Notas Rapidas (CustomTkinter)."""

import customtkinter as ctk
from tkinter import messagebox

from services import NotasService
from database import DatabaseManager

class WidgetNotas(ctk.CTkToplevel):
    """Ventana flotante persistente para tomar apuntes rapidos en caja."""

    def __init__(self, parent, db_manager: DatabaseManager):
        super().__init__(parent)
        
        self.servicio = NotasService(db_manager)
        
        # Configuracion de la ventana flotante
        self.title("📝 Notas de Caja")
        self.geometry("400x500")
        self.resizable(False, False)
        self.attributes("-topmost", True) # Mantiene la ventana siempre visible arriba
        
        self.setup_ui()
        self.cargar_notas()

    def setup_ui(self):
        # 1. Area para escribir nueva nota
        frame_input = ctk.CTkFrame(self, fg_color="transparent")
        frame_input.pack(fill="x", padx=15, pady=15)
        
        self.txt_nueva_nota = ctk.CTkTextbox(frame_input, height=80, fg_color="#34495e")
        self.txt_nueva_nota.pack(fill="x", pady=(0, 10))
        
        btn_guardar = ctk.CTkButton(frame_input, text="GUARDAR NOTA", fg_color="#2980b9", 
                                    hover_color="#2471a3", font=("Arial", 12, "bold"), 
                                    command=self.guardar_nota)
        btn_guardar.pack(fill="x")

        # Separador
        ctk.CTkFrame(self, height=2, fg_color="#7f8c8d").pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(self, text="Notas Activas:", font=("Arial", 14, "bold")).pack(anchor="w", padx=15)

        # 2. Area para mostrar las notas (Scrollable)
        self.frame_notas = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.frame_notas.pack(fill="both", expand=True, padx=15, pady=10)

    def cargar_notas(self):
        # Limpiar frame
        for widget in self.frame_notas.winfo_children():
            widget.destroy()
            
        notas = self.servicio.obtener_notas_activas()
        
        if not notas:
            ctk.CTkLabel(self.frame_notas, text="No hay notas pendientes.", text_color="gray").pack(pady=20)
            return

        for nota in notas:
            id_nota = nota['id_nota']
            contenido = nota['contenido']
            fecha = nota['fecha_creacion']
            
            f_item = ctk.CTkFrame(self.frame_notas, corner_radius=8, fg_color="#2c3e50")
            f_item.pack(fill="x", pady=5)
            
            ctk.CTkLabel(f_item, text=f"🕒 {fecha}", font=("Arial", 10), text_color="#bdc3c7").pack(anchor="w", padx=10, pady=(5, 0))
            ctk.CTkLabel(f_item, text=contenido, font=("Arial", 12), justify="left", wraplength=300).pack(anchor="w", padx=10, pady=5)
            
            ctk.CTkButton(f_item, text="Resolver ✓", width=80, height=24, fg_color="#27ae60", 
                          hover_color="#219a52", command=lambda n_id=id_nota: self.resolver_nota(n_id)).pack(side="right", padx=10, pady=(0, 10))

    def guardar_nota(self):
        texto = self.txt_nueva_nota.get("1.0", "end-1c").strip()
        if not texto: return
        
        try:
            self.servicio.agregar_nota(texto)
            self.txt_nueva_nota.delete("1.0", "end")
            self.cargar_notas()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la nota: {e}")

    def resolver_nota(self, id_nota: int):
        try:
            self.servicio.archivar_nota(id_nota)
            self.cargar_notas()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo archivar la nota: {e}")