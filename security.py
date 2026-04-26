"""Módulo de seguridad para el control de licencias y bloqueo de hardware (HWID)."""

import os
import json
import uuid
import platform
import hashlib
from datetime import datetime, timedelta
from typing import Tuple, Optional

class SecurityService:
    """Controlador que gestiona la validación de hardware y licencias de uso."""

    def __init__(self, license_file: str = "license.key"):
        """Inicializa el servicio de seguridad.
        
        Args:
            license_file (str): Ruta del archivo donde se almacena el token local.
        """
        self.license_file = license_file
        self.hwid = self._generar_hwid()

    def _generar_hwid(self) -> str:
        """Genera un identificador único atado a la máquina física.
        
        Combina la dirección MAC de la tarjeta de red con el nombre del nodo 
        y la arquitectura del sistema operativo, creando un hash SHA-256.
        
        Returns:
            str: Hash hexadecimal único de 64 caracteres.
        """
        mac_address = str(uuid.getnode())
        sistema = platform.node() + platform.machine()
        
        raw_id = f"{mac_address}-{sistema}-KioskoSaaS"
        # Hasheamos para evitar exponer datos del sistema del cliente
        return hashlib.sha256(raw_id.encode('utf-8')).hexdigest()

    def obtener_codigo_cliente(self) -> str:
        """Devuelve una versión corta del HWID para que el cliente la dicte por teléfono.
        
        Returns:
            str: Código alfanumérico corto de 12 caracteres.
        """
        return self.hwid[:12].upper()

    def validar_licencia(self) -> Tuple[bool, str]:
        """Comprueba si el software está autorizado para ejecutarse en esta PC.
        
        Implementa el 'Token de Tolerancia Offline'.
        
        Returns:
            Tuple[bool, str]: (Es Válida, Mensaje de estado).
        """
        if not os.path.exists(self.license_file):
            return False, "No se encontró ninguna licencia instalada."

        try:
            with open(self.license_file, 'r') as f:
                datos_licencia = json.load(f)
                
            licencia_hwid = datos_licencia.get('hwid')
            fecha_expiracion_str = datos_licencia.get('expiracion')
            
            # 1. HWID Binding: ¿Es la misma computadora?
            if licencia_hwid != self.hwid:
                return False, "Violación de Seguridad: El software fue movido a otra computadora."
                
            # 2. Tolerancia Offline: ¿Sigue vigente el periodo pagado?
            fecha_expiracion = datetime.strptime(fecha_expiracion_str, "%Y-%m-%d")
            if datetime.now() > fecha_expiracion:
                return False, "Suscripción expirada. Por favor, renueve su plan."
                
            dias_restantes = (fecha_expiracion - datetime.now()).days
            return True, f"Licencia válida. Quedan {dias_restantes} días de uso offline."
            
        except Exception as e:
            return False, f"El archivo de licencia está corrupto: {e}"

    def activar_licencia_local(self, dias_vigencia: int = 30) -> None:
        """Genera un archivo de licencia válido atado a esta máquina física.
        En producción, este método solo debería ser llamado por un instalador 
        admin o tras una conexión exitosa a tu servidor de pagos.
        
        Args:
            dias_vigencia (int): Cantidad de días que el programa funcionará sin internet.
        """
        fecha_exp = (datetime.now() + timedelta(days=dias_vigencia)).strftime("%Y-%m-%d")
        datos = {
            "hwid": self.hwid,
            "expiracion": fecha_exp,
            "firma": "Kiosko_SaaS_Valid" # En el futuro, esto será un JWT firmado criptográficamente
        }
        
        with open(self.license_file, 'w') as f:
            json.dump(datos, f)