"""Motor de persistencia utilizando SQLite3.
Implementa el patrón de repositorio para interactuar con la base de datos.
"""

import sqlite3
import logging
from typing import List, Optional, ContextManager
from contextlib import contextmanager

from models import Producto, Cliente, Venta, Pago, Gasto, TurnoCaja
from exceptions import ProductoNoEncontradoError, StockInsuficienteError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    """Gestiona la conexión y las operaciones CRUD de la base de datos SQLite."""

    def __init__(self, db_path: str = "kiosko_data.db"):
        """Inicializa el manager de la base de datos.
        
        Args:
            db_path (str): Ruta al archivo de la base de datos SQLite.
        """
        self.db_path = db_path
        self.inicializar_esquema()

    @contextmanager
    def get_connection(self):
        """Provee un manejador de contexto para la conexión a la base de datos.
        Habilita el soporte para llaves foráneas y devuelve filas como diccionarios.
        
        Yields:
            sqlite3.Connection: Conexión activa a la base de datos.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = 1") # Activar llaves foráneas
        try:
            yield conn
        finally:
            conn.close()

    def inicializar_esquema(self) -> None:
        """Crea las tablas relacionales si no existen en la base de datos (Esquema V2.0)."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS productos (
                id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_producto TEXT NOT NULL,
                categoria TEXT,
                costo_compra REAL NOT NULL,
                costo_venta REAL NOT NULL,
                stock INTEGER NOT NULL,
                barcode TEXT UNIQUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS clientes (
                id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_alias TEXT UNIQUE NOT NULL,
                limite_credito REAL NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ventas (
                id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
                id_ticket TEXT NOT NULL,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                id_producto INTEGER NOT NULL,
                id_cliente INTEGER NOT NULL,
                cantidad INTEGER NOT NULL,
                precio_venta_historico REAL NOT NULL,
                saldo_pendiente REAL DEFAULT 0.0, -- NUEVO CAMPO V2.0
                id_metodo_pago INTEGER NOT NULL,
                FOREIGN KEY (id_producto) REFERENCES productos (id_producto),
                FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS pagos (
                id_pago INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                id_cliente INTEGER NOT NULL,
                monto_abonado REAL NOT NULL,
                id_metodo_pago INTEGER NOT NULL,
                FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS gastos (
                id_gasto INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                categoria TEXT NOT NULL,
                descripcion TEXT,
                monto REAL NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS turnos_caja (
                id_turno INTEGER PRIMARY KEY AUTOINCREMENT,
                id_turno_str TEXT UNIQUE NOT NULL,
                fecha_apertura TEXT NOT NULL,
                hora_apertura TEXT NOT NULL,
                fondo_inicial REAL NOT NULL,
                fecha_cierre TEXT,
                hora_cierre TEXT,
                total_calculado REAL DEFAULT 0.0,
                total_real REAL DEFAULT 0.0,
                diferencia REAL DEFAULT 0.0,
                estado TEXT DEFAULT 'Abierto'
            )
            """,
            # ==========================================
            # NUEVAS TABLAS V2.0
            # ==========================================
            """
            CREATE TABLE IF NOT EXISTS mermas (
                id_merma INTEGER PRIMARY KEY AUTOINCREMENT,
                id_producto INTEGER NOT NULL,
                cantidad REAL NOT NULL,
                motivo TEXT NOT NULL,
                costo_perdido REAL NOT NULL,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                FOREIGN KEY(id_producto) REFERENCES productos(id_producto)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS notas (
                id_nota INTEGER PRIMARY KEY AUTOINCREMENT,
                contenido TEXT NOT NULL,
                estado INTEGER DEFAULT 0, -- 0: Activa, 1: Archivada
                fecha_creacion TEXT NOT NULL
            )
            """
        ]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for q in queries:
                cursor.execute(q)
            
            # Insertar cliente por defecto si la tabla está vacía
            cursor.execute("SELECT COUNT(*) FROM clientes")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO clientes (id_cliente, nombre_alias, limite_credito) VALUES (1, 'Cliente Final', 0.0)"
                )
            conn.commit()

    # --- MÉTODOS DE PRODUCTO ---

    def guardar_producto(self, producto: Producto) -> Producto:
        """Inserta o actualiza un producto en la base de datos aplicando limpieza estricta."""
        
        # 1. Sanitizar el ID (Si la interfaz envía un texto vacío "", lo forzamos a None real)
        try:
            prod_id = int(producto.id_producto) if producto.id_producto and str(producto.id_producto).strip() != "" else None
        except ValueError:
            prod_id = None

        # 2. Sanitizar Barcode (Destruye textos vacíos "" o el texto literal "None" generado por Python)
        b_code = producto.barcode
        if not b_code or str(b_code).strip() == "" or str(b_code).strip().lower() == "none":
            b_code = None  # Esto asegura que llegue un verdadero NULL a SQLite

        with self.get_connection() as conn:
            cursor = conn.cursor()
            if prod_id is None:
                # Nuevo producto (INSERT)
                cursor.execute("""
                    INSERT INTO productos (nombre_producto, categoria, costo_compra, costo_venta, stock, barcode)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (producto.nombre_producto, producto.categoria, producto.costo_compra, 
                      producto.costo_venta, producto.stock, b_code))
                producto.id_producto = cursor.lastrowid
            else:
                # Actualizar existente (UPDATE)
                cursor.execute("""
                    UPDATE productos 
                    SET nombre_producto = ?, categoria = ?, costo_compra = ?, 
                        costo_venta = ?, stock = ?, barcode = ?
                    WHERE id_producto = ?
                """, (producto.nombre_producto, producto.categoria, producto.costo_compra, 
                      producto.costo_venta, producto.stock, b_code, prod_id))
            conn.commit()
            return producto

    def obtener_producto_por_id(self, id_producto: int) -> Producto:
        """Recupera un producto específico por su ID.
        
        Args:
            id_producto (int): El identificador único del producto.
            
        Returns:
            Producto: La entidad del producto.
            
        Raises:
            ProductoNoEncontradoError: Si el ID no existe en la base de datos.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM productos WHERE id_producto = ?", (id_producto,))
            row = cursor.fetchone()
            
            if not row:
                raise ProductoNoEncontradoError(f"Producto con ID {id_producto} no encontrado.")
                
            return Producto(
                id_producto=row['id_producto'],
                nombre_producto=row['nombre_producto'],
                categoria=row['categoria'],
                costo_compra=row['costo_compra'],
                costo_venta=row['costo_venta'],
                stock=row['stock'],
                barcode=row['barcode']
            )

    # --- MÉTODOS DE VENTA (TRANSACCIONAL) ---

    def registrar_venta(self, venta: Venta) -> Venta:
        """Registra una venta y descuenta el stock de forma atómica.
        
        Args:
            venta (Venta): Entidad con los datos de la transacción.
            
        Returns:
            Venta: La venta registrada con su ID autoincremental.
            
        Raises:
            ProductoNoEncontradoError: Si el producto a vender no existe.
            StockInsuficienteError: Si se intenta vender más de lo que hay.
        """
        with self.get_connection() as conn:
            # El context manager 'conn' asegura que si hay un raise, se hace ROLLBACK automático
            cursor = conn.cursor()
            
            # 1. Verificar existencia y stock actual
            cursor.execute("SELECT stock FROM productos WHERE id_producto = ?", (venta.id_producto,))
            row = cursor.fetchone()
            
            if not row:
                raise ProductoNoEncontradoError(f"Producto ID {venta.id_producto} no encontrado.")
                
            stock_actual = row['stock']
            
            if stock_actual < venta.cantidad:
                raise StockInsuficienteError(
                    f"Stock insuficiente. Solicitado: {venta.cantidad}, Disponible: {stock_actual}"
                )
            
            # 2. Descontar stock
            nuevo_stock = stock_actual - venta.cantidad
            cursor.execute("UPDATE productos SET stock = ? WHERE id_producto = ?", 
                           (nuevo_stock, venta.id_producto))
            
            # 3. Registrar ticket de venta
            cursor.execute("""
                INSERT INTO ventas (id_ticket, fecha, hora, id_producto, id_cliente, 
                                  cantidad, precio_venta_historico, id_metodo_pago)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (venta.id_ticket, venta.fecha, venta.hora, venta.id_producto, 
                  venta.id_cliente, venta.cantidad, venta.precio_venta_historico, venta.id_metodo_pago))
            
            venta.id_venta = cursor.lastrowid
            conn.commit()
            return venta
            
            # --- MÉTODOS DE CAJA Y GASTOS ---

    def registrar_gasto(self, gasto: Gasto) -> Gasto:
        """Inserta un nuevo registro de gasto en la base de datos."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO gastos (fecha, hora, categoria, descripcion, monto)
                VALUES (?, ?, ?, ?, ?)
            """, (gasto.fecha, gasto.hora, gasto.categoria, gasto.descripcion, gasto.monto))
            gasto.id_gasto = cursor.lastrowid
            conn.commit()
            return gasto

    def registrar_pago(self, pago: Pago) -> Pago:
        """Registra el pago o abono de un cliente."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pagos (fecha, hora, id_cliente, monto_abonado, id_metodo_pago)
                VALUES (?, ?, ?, ?, ?)
            """, (pago.fecha, pago.hora, pago.id_cliente, pago.monto_abonado, pago.id_metodo_pago))
            pago.id_pago = cursor.lastrowid
            conn.commit()
            return pago

    # --- MÉTODOS DE CONTROL DE TURNOS ---

    def obtener_turno_activo(self) -> Optional[TurnoCaja]:
        """Recupera el turno de caja que se encuentra actualmente abierto, si existe."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM turnos_caja WHERE estado = 'Abierto' ORDER BY id_turno DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return TurnoCaja(**dict(row))
            return None

    def abrir_turno(self, turno: TurnoCaja) -> TurnoCaja:
        """Abre un nuevo turno de caja."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO turnos_caja (id_turno_str, fecha_apertura, hora_apertura, fondo_inicial, estado)
                VALUES (?, ?, ?, ?, ?)
            """, (turno.id_turno_str, turno.fecha_apertura, turno.hora_apertura, turno.fondo_inicial, turno.estado))
            turno.id_turno = cursor.lastrowid
            conn.commit()
            return turno

    def cerrar_turno(self, id_turno: int, data_cierre: dict) -> None:
        """Actualiza un turno de caja para marcarlo como cerrado con los resultados del arqueo."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE turnos_caja 
                SET fecha_cierre = ?, hora_cierre = ?, total_calculado = ?, total_real = ?, diferencia = ?, estado = 'Cerrado'
                WHERE id_turno = ?
            """, (
                data_cierre['fecha_cierre'], data_cierre['hora_cierre'], 
                data_cierre['total_calculado'], data_cierre['total_real'], 
                data_cierre['diferencia'], id_turno
            ))
            conn.commit()