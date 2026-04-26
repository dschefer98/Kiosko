import customtkinter as ctk
from tkinter import messagebox
import sys
from updater_service import UpdateService

from database import DatabaseManager
from backup_service import CloudBackupService
from security import SecurityService

from tab_ventas import TabVentas
from tab_fiados import TabFiados
from tab_dashboard import TabDashboard
from tab_inventario import TabInventario
from widget_notas import WidgetNotas  # Importamos el nuevo widget

# --- CONFIGURACIÓN GLOBAL DE UI ---
ctk.set_appearance_mode("Dark")  # Opciones: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Opciones: "blue", "green", "dark-blue"

class KioskoApp:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("Kiosko POS - SaaS Edition")
        self.root.geometry("1100x850") 
        self.db = DatabaseManager()
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        # --- Cabecera Global ---
        header_frame = ctk.CTkFrame(self.root, fg_color="transparent", height=40)
        header_frame.pack(fill="x", padx=20, pady=(15, 0))
        
        # NUEVO: Instanciamos el servicio y ejecutamos comprobación silenciosa al arrancar
        self.updater = UpdateService()
        self.updater.check_for_updates(silent=True)
        
        # NUEVO: Botón de Actualizar (arriba a la izquierda)
        self.btn_update = ctk.CTkButton(header_frame, text="☁️ Buscar Actualizaciones", 
                                       command=lambda: self.updater.check_for_updates(silent=False), 
                                       width=150, fg_color="#34495e", hover_color="#2c3e50",
                                       font=("Arial", 12, "bold"))
        self.btn_update.pack(side="left")

        # Botón global de Notas (arriba a la derecha)
        self.btn_notas = ctk.CTkButton(header_frame, text="📝 Notas Rápidas", 
                                       command=self.abrir_notas, width=130, 
                                       fg_color="#e67e22", hover_color="#d35400",
                                       font=("Arial", 12, "bold"))
        self.btn_notas.pack(side="right")

        # --- CONTENEDOR DE PESTAÑAS ---
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(expand=True, fill='both', padx=20, pady=(0, 10))
        
        # Creamos los contenedores para cada pestaña
        frame_ventas = self.tabview.add("Caja y Ventas")
        frame_fiados = self.tabview.add("Cuentas Corrientes")
        frame_inv = self.tabview.add("Inventario Maestro")
        frame_bi = self.tabview.add("Dashboard BI")
        
        # Inyectamos directamente los frames a nuestras clases
        self.tab_ventas = TabVentas(frame_ventas, self.db, self.root)
        self.tab_fiados = TabFiados(frame_fiados, self.db)
        self.tab_inventario = TabInventario(frame_inv, self.db)
        self.tab_dashboard = TabDashboard(frame_bi, self.db)

    def abrir_notas(self):
        """Abre la ventana flotante de notas o la trae al frente si ya está abierta."""
        if not hasattr(self, 'ventana_notas') or not self.ventana_notas.winfo_exists():
            self.ventana_notas = WidgetNotas(self.root, self.db)
        else:
            self.ventana_notas.focus()

    def on_closing(self):
        if messagebox.askyesno("Salir", "¿Cerrar el Kiosko y realizar respaldo en la nube?"):
            try:
                self.root.withdraw()
                self.root.update()
                backup_service = CloudBackupService()
                backup_service.iniciar_backup_segundo_plano()
            except Exception as e:
                print(f"Error: {e}")
            finally:
                self.root.quit()
                self.root.destroy()

def arrancar_kiosko():
    # Inicializamos la ventana nativa de CustomTkinter
    root = ctk.CTk()
    app = KioskoApp(root)
    root.mainloop()

if __name__ == "__main__":
    seguridad = SecurityService()
    es_valida, mensaje = seguridad.validar_licencia()
    
    if es_valida:
        print(f"Check de Seguridad Superado: {mensaje}")
        arrancar_kiosko()
    else:
        print(f"Check de Seguridad Fallido: {mensaje}")
        arrancar_kiosko() # Quita esto y restaura el bloqueo luego de probar