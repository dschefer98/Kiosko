"""Módulo de Servicios. Encapsula la lógica de negocio del Kiosko POS."""

from datetime import datetime
import uuid
import math
from typing import List, Dict, Any, Optional, Tuple

from database import DatabaseManager
from models import Producto, Cliente, Venta, Pago, Gasto, TurnoCaja
from exceptions import ProductoNoEncontradoError, TurnoCajaCerradoError

class InventarioService:
    """Controlador que maneja las operaciones y reglas de negocio del inventario."""

    def __init__(self, db_manager: DatabaseManager):
        """Inicializa el servicio de inventario.
        
        Args:
            db_manager (DatabaseManager): Instancia del motor de base de datos.
        """
        self.db = db_manager

    def obtener_catalogo(self) -> List[Producto]:
        """Recupera todos los productos del inventario ordenados alfabéticamente.
        
        Returns:
            List[Producto]: Lista de entidades Producto.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM productos ORDER BY nombre_producto ASC")
            # Convertimos cada fila de SQLite directamente a nuestra Dataclass
            return [Producto(**row) for row in cursor.fetchall()]

    def guardar_producto(self, data: Dict[str, Any]) -> Producto:
        """Aplica reglas de negocio, formatea y guarda un producto.
        
        Args:
            data (Dict[str, Any]): Diccionario con los datos crudos desde la UI.
            
        Returns:
            Producto: El producto procesado y guardado.
            
        Raises:
            ValueError: Si los tipos de datos son incorrectos o violan reglas de negocio.
        """
        costo_compra = float(data.get('costo_compra', 0))
        costo_venta = float(data.get('costo_venta', 0))
        
        # Regla de Negocio: Evitar pérdidas por error de tipeo
        if costo_venta < costo_compra:
            raise ValueError("El precio de venta no puede ser menor al costo de compra.")

        producto = Producto(
            id_producto=int(data['id_producto']) if data.get('id_producto') else None,
            nombre_producto=str(data['nombre_producto']).strip().title(),
            categoria=str(data['categoria']).strip().title(),
            costo_compra=costo_compra,
            costo_venta=costo_venta,
            stock=int(data.get('stock', 0)),
            barcode=str(data.get('barcode', '')).strip()
        )
        return self.db.guardar_producto(producto)

    def aplicar_aumento_masivo(self, categoria: str, porcentaje: float) -> int:
        """Aplica un aumento inflacionario a toda una categoría.
        
        Aplica el porcentaje y redondea el precio final al múltiplo de 50 
        más cercano hacia arriba (Regla de negocio).
        
        Args:
            categoria (str): Nombre de la categoría a afectar.
            porcentaje (float): Porcentaje de aumento (ej. 15.5).
            
        Returns:
            int: Cantidad de productos actualizados.
            
        Raises:
            ValueError: Si el porcentaje es inválido.
        """
        if porcentaje <= 0:
            raise ValueError("El porcentaje de aumento debe ser mayor a 0.")

        factor = 1 + (porcentaje / 100.0)
        productos_actualizados = 0

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Búsqueda case-insensitive
            cursor.execute("SELECT * FROM productos WHERE LOWER(categoria) = ?", (categoria.lower(),))
            filas = cursor.fetchall()

            for fila in filas:
                prod = Producto(**fila)
                nuevo_precio_bruto = prod.costo_venta * factor
                
                # Lógica matemática movida aquí (fuera de la UI y DB)
                prod.costo_venta = float(math.ceil(nuevo_precio_bruto / 50.0) * 50.0)
                
                self.db.guardar_producto(prod)
                productos_actualizados += 1

        return productos_actualizados
    def registrar_merma(self, id_producto: int, cantidad: float, motivo: str) -> None:
        """Registra una pérdida de inventario y deduce el stock de forma segura."""
        from datetime import datetime
        
        # Obtenemos el producto para saber cuánto nos costó y cuánto stock tiene
        producto = self.db.obtener_producto_por_id(id_producto)
        
        if producto.stock < cantidad:
            raise ValueError("No puedes registrar una pérdida mayor al stock que tienes.")

        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        hora_actual = datetime.now().strftime("%H:%M:%S")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Descontar el stock físicamente
            nuevo_stock = producto.stock - cantidad
            cursor.execute("UPDATE productos SET stock = ? WHERE id_producto = ?", (nuevo_stock, id_producto))

            # 2. Registrar el evento contable de la merma
            cursor.execute("""
                INSERT INTO mermas (id_producto, cantidad, motivo, costo_perdido, fecha, hora)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (id_producto, cantidad, motivo, producto.costo_compra, fecha_actual, hora_actual))
            
            conn.commit()


class VentasService:
    """Controlador que maneja las reglas de negocio de la caja y ventas."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def calcular_subtotal(self, producto: Producto, valor_ingresado: float, es_peso: bool, aplicar_redondeo: bool) -> float:
        """Calcula el precio de línea aplicando reglas de peso y redondeo.
        
        Args:
            producto (Producto): Entidad del producto.
            valor_ingresado (float): Unidades o Gramos.
            es_peso (bool): True si el producto se vende por peso.
            aplicar_redondeo (bool): True para redondear hacia arriba al múltiplo de 50.
            
        Returns:
            float: El subtotal calculado.
        """
        if es_peso:
            # Lógica original: (gramos / 100) * precio_cada_100g
            subtotal = (valor_ingresado / 100.0) * producto.costo_venta
        else:
            subtotal = valor_ingresado * producto.costo_venta

        if aplicar_redondeo:
            return float(math.ceil(subtotal / 50.0) * 50.0)
        
        return round(subtotal, 2)

    def procesar_ticket_completo(self, carrito: List[Dict[str, Any]], id_metodo_pago: int, id_cliente: int = 1) -> str:
        """Procesa una venta por lotes (Carrito) de forma transaccional.
        
        Genera un único ID de Ticket y registra cada línea del carrito.
        
        Args:
            carrito: Lista de diccionarios con {'producto': Producto, 'cantidad': float, 'subtotal': float}.
            id_metodo_pago (int): 1=Efectivo, 2=Transferencia.
            id_cliente (int): ID del cliente (por defecto 1 = Final).
            
        Returns:
            str: El ID del ticket generado.
        """
        if not carrito:
            raise ValueError("El carrito está vacío.")

        # Generar un ID de ticket único para todo el lote
        unique_part = uuid.uuid4().hex[:8].upper()
        timestamp = datetime.now().strftime("%y%m%d%H%M")
        id_ticket = f"TK{timestamp}-{unique_part}"
        
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        hora_actual = datetime.now().strftime("%H:%M:%S")

        # Procesar cada línea del carrito
        for item in carrito:
            producto: Producto = item['producto']
            
            # La cantidad en BBDD para fiambres se puede guardar como 1 (venta única) o los gramos exactos.
            # Según tu lógica anterior, guardabas 1 para fiambres. Mantendremos esa convención.
            cantidad_bd = 1 if item['es_peso'] else int(item['cantidad'])

            venta = Venta(
                id_ticket=id_ticket,
                fecha=fecha_actual,
                hora=hora_actual,
                id_producto=producto.id_producto,
                id_cliente=id_cliente,
                cantidad=cantidad_bd,
                precio_venta_historico=item['subtotal'],
                id_metodo_pago=id_metodo_pago
            )
            # El motor SQLite ya maneja el descuento de stock de forma atómica
            self.db.registrar_venta(venta)

        return id_ticket

import pandas as pd
from typing import Dict, List, Any

class DashboardService:
    """Controlador que maneja las métricas de Inteligencia de Negocios y Reportes."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def obtener_kpis_principales(self) -> Dict[str, float]:
        """Calcula el volumen transado y la ganancia bruta mediante SQL."""
        # Calculamos la ganancia neta restando el costo de compra (multiplicado por la cantidad) al precio de venta histórico
        query = """
            SELECT 
                SUM(v.precio_venta_historico) as total_ingresos,
                SUM(v.precio_venta_historico - (p.costo_compra * v.cantidad)) as ganancia_neta
            FROM ventas v
            JOIN productos p ON v.id_producto = p.id_producto
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            
            return {
                'total_ingresos': float(row['total_ingresos'] or 0.0),
                'ganancia_neta': float(row['ganancia_neta'] or 0.0)
            }

    def obtener_ranking_productos(self, limite: int = 5) -> List[Dict[str, Any]]:
        """Obtiene el Top N de productos más vendidos."""
        query = """
            SELECT p.nombre_producto, SUM(v.cantidad) as total_vendido
            FROM ventas v
            JOIN productos p ON v.id_producto = p.id_producto
            GROUP BY p.id_producto
            ORDER BY total_vendido DESC
            LIMIT ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limite,))
            return [dict(row) for row in cursor.fetchall()]

    def obtener_alertas_stock(self, umbral: int = 5) -> List[Dict[str, Any]]:
        """Obtiene el listado de productos que requieren reposición."""
        query = """
            SELECT nombre_producto, stock 
            FROM productos 
            WHERE stock < ? 
            ORDER BY stock ASC
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (umbral,))
            return [dict(row) for row in cursor.fetchall()]

    def exportar_data_warehouse_excel(self, filepath: str) -> None:
        """Exporta las tablas transaccionales a un archivo Excel multipestaña.
        
        Args:
            filepath (str): Ruta absoluta donde se guardará el archivo .xlsx.
            
        Raises:
            Exception: Si falla la escritura del archivo o no hay datos.
        """
        query_ventas_enriquecidas = """
            SELECT 
                v.id_ticket, v.fecha, v.hora, p.nombre_producto, p.categoria, 
                v.cantidad, p.costo_compra, v.precio_venta_historico as total_cobrado,
                (v.precio_venta_historico - (p.costo_compra * v.cantidad)) as margen_ganancia
            FROM ventas v
            LEFT JOIN productos p ON v.id_producto = p.id_producto
            ORDER BY v.id_venta DESC
        """
        query_inventario = "SELECT * FROM productos ORDER BY nombre_producto"
        
        with self.db.get_connection() as conn:
            # Pandas se encarga de traducir el SQL directamente a un DataFrame
            df_ventas = pd.read_sql_query(query_ventas_enriquecidas, conn)
            df_stock = pd.read_sql_query(query_inventario, conn)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df_ventas.to_excel(writer, sheet_name='Ventas_y_Rentabilidad', index=False)
                df_stock.to_excel(writer, sheet_name='Estado_Stock', index=False)
                # Nota: Las tablas de Gastos y Caja las integraremos cuando refactoricemos esos módulos
                
class CajaService:
    """Controlador que maneja las operaciones de turnos y flujo de caja."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def obtener_turno_activo(self) -> Optional['TurnoCaja']:
        """Recupera el turno de caja que se encuentra actualmente abierto."""
        return self.db.obtener_turno_activo()

    def abrir_turno(self, fondo_inicial: float) -> 'TurnoCaja':
        """Inicia un nuevo turno de caja con validaciones de negocio."""
        if self.obtener_turno_activo():
            raise ValueError("Ya existe un turno abierto. Ciérrelo antes de abrir uno nuevo.")
        
        if fondo_inicial < 0:
            raise ValueError("El fondo inicial no puede ser negativo.")

        id_str = f"TRN{datetime.now().strftime('%y%m%d%H%M')}"
        turno = TurnoCaja(
            id_turno_str=id_str,
            fecha_apertura=datetime.now().strftime("%Y-%m-%d"),
            hora_apertura=datetime.now().strftime("%H:%M:%S"),
            fondo_inicial=fondo_inicial
        )
        return self.db.abrir_turno(turno)

    def registrar_gasto(self, categoria: str, descripcion: str, monto: float) -> 'Gasto':
        """Aplica reglas de negocio y registra un egreso de caja."""
        if not self.obtener_turno_activo():
            from exceptions import TurnoCajaCerradoError
            raise TurnoCajaCerradoError("Debe abrir un turno para registrar gastos.")
        
        if monto <= 0:
            raise ValueError("El monto del gasto debe ser mayor a 0.")

        gasto = Gasto(
            fecha=datetime.now().strftime("%Y-%m-%d"),
            hora=datetime.now().strftime("%H:%M:%S"),
            categoria=categoria.strip(),
            descripcion=descripcion.strip(),
            monto=monto
        )
        return self.db.registrar_gasto(gasto)

    def precalcular_arqueo(self) -> dict:
        """Calcula los totales esperados en caja consultando directamente mediante SQL."""
        turno = self.obtener_turno_activo()
        if not turno:
            from exceptions import TurnoCajaCerradoError
            raise TurnoCajaCerradoError("No hay turno abierto para arquear.")

        fecha_hoy = turno.fecha_apertura
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Ingresos Ventas (Efectivo)
            cursor.execute("SELECT SUM(precio_venta_historico) as val FROM ventas WHERE fecha = ? AND id_metodo_pago = 1", (fecha_hoy,))
            ventas_efectivo = cursor.fetchone()['val'] or 0.0
            
            # Ingresos Pagos/Abonos (Efectivo)
            cursor.execute("SELECT SUM(monto_abonado) as val FROM pagos WHERE fecha = ? AND id_metodo_pago = 1", (fecha_hoy,))
            pagos_efectivo = cursor.fetchone()['val'] or 0.0
            
            # Egresos (Gastos)
            cursor.execute("SELECT SUM(monto) as val FROM gastos WHERE fecha = ?", (fecha_hoy,))
            gastos_totales = cursor.fetchone()['val'] or 0.0

        ingresos_totales = ventas_efectivo + pagos_efectivo
        total_teorico = turno.fondo_inicial + ingresos_totales - gastos_totales

        return {
            'fondo_inicial': turno.fondo_inicial,
            'ingresos_efectivo': ingresos_totales,
            'egresos': gastos_totales,
            'total_teorico': total_teorico
        }

    def cerrar_turno(self, monto_real: float) -> Tuple[float, float]:
        """Ejecuta el cierre de caja y calcula la diferencia final.
        
        Returns:
            Tuple[float, float]: (Total Teórico, Diferencia).
        """
        turno = self.obtener_turno_activo()
        if not turno:
            from exceptions import TurnoCajaCerradoError
            raise TurnoCajaCerradoError("No hay turno abierto para cerrar.")

        datos_arqueo = self.precalcular_arqueo()
        total_teorico = datos_arqueo['total_teorico']
        diferencia = monto_real - total_teorico

        data_cierre = {
            'fecha_cierre': datetime.now().strftime("%Y-%m-%d"),
            'hora_cierre': datetime.now().strftime("%H:%M:%S"),
            'total_calculado': total_teorico,
            'total_real': monto_real,
            'diferencia': diferencia
        }

        self.db.cerrar_turno(turno.id_turno, data_cierre)
        return total_teorico, diferencia

    def obtener_resumen_diario(self, fecha: str) -> dict:
        """Agrupa los movimientos financieros de un día específico mediante SQL."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Sumatorias por método de pago (1=Efectivo, 2=Transferencia)
            cursor.execute("SELECT SUM(precio_venta_historico) as val FROM ventas WHERE fecha = ? AND id_metodo_pago = 1", (fecha,))
            ve = cursor.fetchone()['val'] or 0.0
            cursor.execute("SELECT SUM(precio_venta_historico) as val FROM ventas WHERE fecha = ? AND id_metodo_pago = 2", (fecha,))
            vt = cursor.fetchone()['val'] or 0.0
            
            cursor.execute("SELECT SUM(monto_abonado) as val FROM pagos WHERE fecha = ? AND id_metodo_pago = 1", (fecha,))
            pe = cursor.fetchone()['val'] or 0.0
            cursor.execute("SELECT SUM(monto_abonado) as val FROM pagos WHERE fecha = ? AND id_metodo_pago = 2", (fecha,))
            pt = cursor.fetchone()['val'] or 0.0
            
            cursor.execute("SELECT SUM(monto) as val FROM gastos WHERE fecha = ?", (fecha,))
            ga = cursor.fetchone()['val'] or 0.0
            
            # Obtener todas las fechas históricas para el Combobox
            cursor.execute("""
                SELECT DISTINCT fecha FROM ventas 
                UNION SELECT DISTINCT fecha FROM pagos 
                UNION SELECT DISTINCT fecha FROM gastos
            """)
            fechas_db = [row['fecha'] for row in cursor.fetchall()]
            
            # Asegurar que el día de hoy siempre esté en la lista
            hoy = datetime.now().strftime("%Y-%m-%d")
            if hoy not in fechas_db:
                fechas_db.append(hoy)
                
            # Función interna inteligente para parsear fechas sin que el programa se caiga
        def parsear_fecha_segura(fecha_str):
            try:
                return datetime.strptime(fecha_str, "%Y-%m-%d") # Intenta formato V2.0
            except ValueError:
                try:
                    return datetime.strptime(fecha_str, "%d/%m/%Y") # Intenta formato V1.0
                except ValueError:
                    return datetime.now() # Fallback de emergencia

        fechas_disponibles = sorted(list(set(fechas_db)), key=parsear_fecha_segura, reverse=True)

        return {
            'efectivo': ve + pe,
            'transferencia': vt + pt,
            'gastos': ga,
            'fechas_disponibles': fechas_disponibles
        }
    def anular_ultimo_ticket(self) -> str:
        """Busca la ultima transaccion y la revierte completamente (Stock y Deuda)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Encontrar el id_ticket de la última venta registrada
            cursor.execute("SELECT id_ticket FROM ventas ORDER BY id_venta DESC LIMIT 1")
            row = cursor.fetchone()
            
            if not row:
                raise ValueError("No hay ninguna venta registrada para deshacer.")
                
            ultimo_ticket = row['id_ticket']
            
            # 2. Obtener todos los productos exactos que se vendieron en ese ticket
            cursor.execute("SELECT id_producto, cantidad FROM ventas WHERE id_ticket = ?", (ultimo_ticket,))
            items = cursor.fetchall()
            
            # 3. Devolver el stock físico al inventario
            for item in items:
                cursor.execute("UPDATE productos SET stock = stock + ? WHERE id_producto = ?", 
                               (item['cantidad'], item['id_producto']))
            
            # 4. Eliminar el registro de la base de datos (Borra el ticket y sus deudas)
            cursor.execute("DELETE FROM ventas WHERE id_ticket = ?", (ultimo_ticket,))
            
            conn.commit()
            
            return ultimo_ticket    
class FiadosService:
    """Controlador que maneja las reglas de negocio de las Cuentas Corrientes y Deudas."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def obtener_clientes(self) -> List[Cliente]:
        """Recupera la lista de clientes registrados (excluyendo al Consumidor Final)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clientes WHERE id_cliente != 1 ORDER BY nombre_alias ASC")
            return [Cliente(**row) for row in cursor.fetchall()]

    def obtener_o_crear_cliente(self, nombre_alias: str) -> Cliente:
        """Busca un cliente por alias. Si no existe, lo crea atómicamente."""
        nombre_alias = nombre_alias.strip().title()
        if not nombre_alias:
            raise ValueError("El nombre del cliente no puede estar vacío.")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clientes WHERE LOWER(nombre_alias) = ?", (nombre_alias.lower(),))
            row = cursor.fetchone()
            if row:
                return Cliente(**row)
            
            # Crear nuevo cliente con límite por defecto
            cursor.execute("INSERT INTO clientes (nombre_alias, limite_credito) VALUES (?, ?)", (nombre_alias, 30000.0))
            nuevo_id = cursor.lastrowid
            conn.commit()
            return Cliente(id_cliente=nuevo_id, nombre_alias=nombre_alias, limite_credito=30000.0)

    def registrar_cargo(self, id_cliente: int, id_producto: int) -> None:
        """Registra una deuda e inicializa el Saldo Pendiente (V2.0)."""
        from datetime import datetime
        from models import Venta
        
        producto = self.db.obtener_producto_por_id(id_producto)
        
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        hora_actual = datetime.now().strftime("%H:%M:%S")
        
        # 1. Registramos la venta (Fiado = Método 3)
        nueva_venta = Venta(
            id_ticket=f"F-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            fecha=fecha_actual,
            hora=hora_actual,
            id_producto=id_producto,
            id_cliente=id_cliente,
            cantidad=1.0,
            precio_venta_historico=producto.costo_venta,
            id_metodo_pago=3 
        )
        venta_registrada = self.db.registrar_venta(nueva_venta)
        
        # 2. Inicializamos el saldo_pendiente de esta venta específica
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            saldo_inicial = producto.costo_venta * 1.0
            cursor.execute("UPDATE ventas SET saldo_pendiente = ? WHERE id_venta = ?", 
                           (saldo_inicial, venta_registrada.id_venta))
            conn.commit()

    def registrar_pago(self, id_cliente: int, monto: float, id_metodo_pago: int, usar_precio_actualizado: bool = False) -> None:
        """Aplica un pago utilizando conciliación FIFO para Soldar Deudas (V2.0)."""
        from datetime import datetime
        from models import Pago
        
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        hora_actual = datetime.now().strftime("%H:%M:%S")
        
        # 1. Guardar el comprobante del pago
        nuevo_pago = Pago(
            fecha=fecha_actual, hora=hora_actual, id_cliente=id_cliente, 
            monto_abonado=monto, id_metodo_pago=id_metodo_pago
        )
        self.db.registrar_pago(nuevo_pago)
        
        # 2. Lógica de Conciliación (FIFO)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Traer ventas pendientes con el precio histórico y el precio actual
            cursor.execute("""
                SELECT v.id_venta, v.saldo_pendiente, v.precio_venta_historico, v.cantidad, p.costo_venta
                FROM ventas v
                JOIN productos p ON v.id_producto = p.id_producto
                WHERE v.id_cliente = ? AND v.id_metodo_pago = 3 AND v.saldo_pendiente > 0
                ORDER BY v.id_venta ASC
            """, (id_cliente,))
            
            ventas_pendientes = cursor.fetchall()
            monto_restante = float(monto)
            
            for v in ventas_pendientes:
                if monto_restante <= 0:
                    break
                    
                id_venta = v['id_venta']
                saldo_historico_actual = float(v['saldo_pendiente'])
                precio_hist = float(v['precio_venta_historico'])
                cant = float(v['cantidad'])
                
                # ¿Cuánto vale la deuda de esta venta HOY para el cliente según el Toggle?
                if usar_precio_actualizado:
                    total_original = precio_hist * cant
                    porcentaje_vivo = saldo_historico_actual / total_original
                    nuevo_total = float(v['costo_venta']) * cant
                    deuda_visible = nuevo_total * porcentaje_vivo
                else:
                    deuda_visible = saldo_historico_actual
                
                if monto_restante >= deuda_visible:
                    # El abono cubre toda la deuda visible. ¡Queda SOLDADA (Saldo 0)!
                    cursor.execute("UPDATE ventas SET saldo_pendiente = 0 WHERE id_venta = ?", (id_venta,))
                    monto_restante -= deuda_visible
                else:
                    # El abono es parcial. 
                    # 1. Calculamos qué porcentaje de la deuda visible estamos pagando
                    porcentaje_pagado = monto_restante / deuda_visible
                    
                    # 2. Reducimos el saldo histórico en ese mismo porcentaje
                    reduccion_historica = saldo_historico_actual * porcentaje_pagado
                    nuevo_saldo_historico = saldo_historico_actual - reduccion_historica
                    
                    cursor.execute("UPDATE ventas SET saldo_pendiente = ? WHERE id_venta = ?", (nuevo_saldo_historico, id_venta))
                    monto_restante = 0 # Se nos acabó el dinero del abono
            
            conn.commit()

    def obtener_estado_cuenta(self, id_cliente: int, usar_precio_actualizado: bool) -> dict:
        """Devuelve las deudas activas aplicando Inflación Proporcional (V2.0)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # V2.0: El sistema YA NO MIRA las ventas soldadas (saldo = 0)
            cursor.execute("""
                SELECT v.fecha, v.cantidad, v.precio_venta_historico, v.saldo_pendiente, 
                       p.nombre_producto, p.costo_venta
                FROM ventas v
                JOIN productos p ON v.id_producto = p.id_producto
                WHERE v.id_cliente = ? AND id_metodo_pago = 3 AND saldo_pendiente > 0
                ORDER BY v.id_venta ASC
            """, (id_cliente,))
            cargos = cursor.fetchall()

        detalle_pendientes = []
        deuda_total = 0.0

        for cargo in cargos:
            saldo_base = float(cargo['saldo_pendiente'])
            
            if usar_precio_actualizado:
                # Si se activa el Toggle, aplicamos la inflación matemática V2.0
                precio_hist = float(cargo['precio_venta_historico'])
                cant = float(cargo['cantidad'])
                total_original = precio_hist * cant
                
                # Porcentaje de la deuda original que sigue vivo (ej. 0.5 si debe la mitad)
                porcentaje_vivo = saldo_base / total_original
                
                # Calculamos el precio hoy, y le aplicamos ese porcentaje
                nuevo_total = float(cargo['costo_venta']) * cant
                deuda_item = nuevo_total * porcentaje_vivo
            else:
                deuda_item = saldo_base

            deuda_total += deuda_item
            
            detalle_pendientes.append({
                'producto': cargo['nombre_producto'],
                'fecha': cargo['fecha'],
                'deuda_item': deuda_item
            })

        return {
            'deuda_total': deuda_total,
            'detalle': detalle_pendientes
        }
class NotasService:
    """Gestiona el block de notas rapido del cajero (V2.0)."""
    
    def __init__(self, db_manager):
        self.db = db_manager

    def obtener_notas_activas(self) -> list:
        """Recupera todas las notas que no han sido archivadas."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id_nota, contenido, fecha_creacion 
                FROM notas 
                WHERE estado = 0 
                ORDER BY id_nota DESC
            """)
            return cursor.fetchall()

    def agregar_nota(self, contenido: str) -> None:
        """Crea una nueva nota rápida."""
        from datetime import datetime
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO notas (contenido, fecha_creacion) VALUES (?, ?)", 
                           (contenido.strip(), fecha_actual))
            conn.commit()

    def archivar_nota(self, id_nota: int) -> None:
        """Oculta una nota marcándola como resuelta (estado = 1)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE notas SET estado = 1 WHERE id_nota = ?", (id_nota,))
            conn.commit()
class BIService:
    """Motor de Inteligencia de Negocios y Prediccion (V2.0)."""
    
    def __init__(self, db_manager):
        self.db = db_manager

    def predecir_quiebres_stock(self, dias_analisis: int = 30, umbral_dias_alerta: int = 5) -> list:
        """
        Analiza la velocidad de ventas historica para predecir en cuantos dias
        se agotara el stock actual de cada producto.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Calculamos cuánto se vendió de cada producto en los últimos X días
            # Gracias a que migramos las fechas a YYYY-MM-DD, SQLite puede hacer este cálculo nativo
            query = f"""
                SELECT p.id_producto, p.nombre_producto, p.stock,
                       SUM(v.cantidad) as total_vendido
                FROM productos p
                JOIN ventas v ON p.id_producto = v.id_producto
                WHERE v.fecha >= date('now', '-{dias_analisis} days')
                GROUP BY p.id_producto
            """
            cursor.execute(query)
            estadisticas = cursor.fetchall()

        alertas_predictivas = []

        for row in estadisticas:
            stock_actual = float(row['stock'])
            total_vendido = float(row['total_vendido'])
            
            if stock_actual <= 0:
                alertas_predictivas.append({
                    'producto': row['nombre_producto'],
                    'estado': 'AGOTADO',
                    'dias_restantes': 0
                })
                continue

            # 2. Velocidad de Ventas (Promedio diario)
            venta_diaria_promedio = total_vendido / dias_analisis
            
            if venta_diaria_promedio > 0:
                # 3. Cálculo de Autonomía (Stock / Velocidad)
                dias_autonomia = stock_actual / venta_diaria_promedio
                
                # Si la autonomía es menor al umbral (ej. faltan menos de 5 días para quedarse sin stock)
                if dias_autonomia <= umbral_dias_alerta:
                    alertas_predictivas.append({
                        'producto': row['nombre_producto'],
                        'estado': 'CRITICO',
                        'dias_restantes': round(dias_autonomia, 1)
                    })

        # Ordenar para que los más urgentes (menos días) salgan primero
        alertas_predictivas.sort(key=lambda x: x['dias_restantes'])
        
        return alertas_predictivas