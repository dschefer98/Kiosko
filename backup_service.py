"""Módulo de infraestructura para la gestión de copias de seguridad (BaaS)."""

import os
import zipfile
import threading
import time
import logging
from datetime import datetime

# Configuración del registro de eventos (Logs) para auditar los backups invisibles
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CloudBackupService:
    """Servicio en segundo plano para empaquetar y subir la base de datos a la nube."""

    def __init__(self, db_path: str = "kiosko_data.db", backup_dir: str = "backups"):
        """Inicializa el servicio de copias de seguridad.
        
        Args:
            db_path (str): Ruta de la base de datos activa.
            backup_dir (str): Carpeta local temporal para guardar los .zip.
        """
        self.db_path = db_path
        self.backup_dir = backup_dir
        self._asegurar_directorio()

    def _asegurar_directorio(self) -> None:
        """Crea el directorio local temporal de backups si no existe."""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def _comprimir_base_datos(self) -> str:
        """Comprime el archivo SQLite en un .zip con marca de tiempo.
        
        Returns:
            str: La ruta absoluta o relativa del archivo .zip generado.
            
        Raises:
            FileNotFoundError: Si la base de datos no existe en la ruta indicada.
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"No se encontró la base de datos: {self.db_path}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = os.path.join(self.backup_dir, f"backup_kiosko_{timestamp}.zip")

        # ZIP_DEFLATED asegura máxima compresión
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(self.db_path, arcname=os.path.basename(self.db_path))

        logging.info(f"Backup local creado exitosamente: {zip_filename}")
        return zip_filename

    def _subir_a_la_nube(self, zip_filepath: str) -> None:
        """Simula la conexión y subida a una API (AWS S3 / Google Drive API).
        
        Args:
            zip_filepath (str): Ruta del archivo .zip a subir.
        """
        logging.info(f"Conectando a la nube... Iniciando subida de {zip_filepath}")
        
        # TODO: Reemplazar con código real de boto3 (AWS) o google-api-python-client
        time.sleep(3) # Simulamos latencia de red (3 segundos de subida)
        
        logging.info("Subida a la nube completada con éxito. Datos asegurados.")

    def _ejecutar_flujo_backup(self) -> None:
        """Orquesta el flujo completo: compresión y subida segura."""
        try:
            zip_path = self._comprimir_base_datos()
            self._subir_a_la_nube(zip_path)
            # Opcional en el futuro: borrar el archivo zip local para no llenar el disco del cliente
        except Exception as e:
            logging.error(f"Fallo crítico en el servicio de Backup: {e}")

    def iniciar_backup_segundo_plano(self) -> None:
        """Lanza el proceso de backup en un hilo (thread) independiente.
        
        El argumento daemon=False asegura que el sistema operativo no mate
        el proceso de Python hasta que el backup haya terminado de subir, 
        incluso si la interfaz gráfica ya se cerró.
        """
        hilo_backup = threading.Thread(target=self._ejecutar_flujo_backup, daemon=False)
        hilo_backup.start()
        logging.info("Hilo de backup en segundo plano iniciado.")