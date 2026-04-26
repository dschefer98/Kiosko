"""Servicio de comprobación de actualizaciones vía GitHub."""

import requests
import threading
import webbrowser
from tkinter import messagebox

class UpdateService:
    def __init__(self):
        # Esta es la versión física de este código. 
        # Cámbiala a "2.1.0" etc., cuando programes nuevas cosas.
        self.current_version = "2.0.0" 
        
        # ATENCIÓN: Reemplaza TU_USUARIO y TU_REPO con los datos reales de tu GitHub
        self.version_url = "https://github.com/dschefer98/Kiosko/blob/main/version.txt"
        self.release_url = "https://github.com/dschefer98/Kiosko/releases/latest"

    def check_for_updates(self, silent=True):
        """Comprueba si hay una nueva versión en un hilo en segundo plano."""
        def _check():
            try:
                # Consultamos el archivo de texto crudo (raw) en GitHub
                response = requests.get(self.version_url, timeout=5)
                if response.status_code == 200:
                    latest_version = response.text.strip()
                    
                    if latest_version != self.current_version:
                        self._mostrar_alerta_actualizacion(latest_version)
                    elif not silent:
                        messagebox.showinfo("Actualización", "El sistema ya está en la versión más reciente.")
            except Exception as e:
                if not silent:
                    messagebox.showerror("Error de Red", f"No se pudo contactar con el servidor de actualizaciones.\n{e}")

        # Ejecutamos la función sin bloquear la interfaz gráfica
        threading.Thread(target=_check, daemon=True).start()

    def _mostrar_alerta_actualizacion(self, latest_version: str):
        """Muestra el diálogo y abre el navegador si el usuario acepta."""
        msg = (
            f"¡Hay una nueva actualización disponible!\n\n"
            f"Versión actual: {self.current_version}\n"
            f"Nueva versión: {latest_version}\n\n"
            f"¿Deseas descargar la nueva versión ahora?"
        )
        if messagebox.askyesno("Actualización Detectada", msg):
            webbrowser.open(self.release_url)