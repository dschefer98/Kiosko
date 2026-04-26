"""Módulo de entidades de dominio del Kiosko POS."""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Producto:
    """Representa un producto en el inventario.
    
    Attributes:
        nombre_producto (str): Nombre comercial del producto.
        categoria (str): Categoría a la que pertenece (ej. Bebidas).
        costo_compra (float): Costo de adquisición.
        costo_venta (float): Precio de venta al público.
        stock (int): Unidades disponibles.
        barcode (str): Código de barras único.
        id_producto (Optional[int]): ID único en base de datos. None si es nuevo.
    """
    nombre_producto: str
    categoria: str
    costo_compra: float
    costo_venta: float
    stock: int
    barcode: str
    id_producto: Optional[int] = None

@dataclass
class Cliente:
    """Representa un cliente con cuenta corriente (fiado).
    
    Attributes:
        nombre_alias (str): Nombre o alias del cliente.
        limite_credito (float): Límite máximo de deuda permitida.
        id_cliente (Optional[int]): ID único en base de datos.
    """
    nombre_alias: str
    limite_credito: float = 30000.0
    id_cliente: Optional[int] = None

@dataclass
class Venta:
    """Representa una línea de venta de un producto.
    
    Attributes:
        id_ticket (str): Identificador alfanumérico del ticket o recibo.
        fecha (str): Fecha de la transacción (DD/MM/YYYY).
        hora (str): Hora de la transacción (HH:MM:SS).
        id_producto (int): ID del producto vendido.
        id_cliente (int): ID del cliente (1 para Consumidor Final).
        cantidad (int): Unidades vendidas.
        precio_venta_historico (float): Precio al que se vendió en ese momento.
        id_metodo_pago (int): 1=Efectivo, 2=Transferencia, 3=Fiado.
        id_venta (Optional[int]): ID interno autoincremental.
    """
    id_ticket: str
    fecha: str
    hora: str
    id_producto: int
    id_cliente: int
    cantidad: int
    precio_venta_historico: float
    id_metodo_pago: int
    id_venta: Optional[int] = None
    
@dataclass
class Pago:
    """Representa un abono o pago realizado por un cliente a su cuenta corriente.
    
    Attributes:
        fecha (str): Fecha del pago (DD/MM/YYYY).
        hora (str): Hora del pago (HH:MM:SS).
        id_cliente (int): Identificador del cliente que realiza el pago.
        monto_abonado (float): Cantidad de dinero entregada.
        id_metodo_pago (int): 1=Efectivo, 2=Transferencia.
        id_pago (Optional[int]): ID interno autoincremental.
    """
    fecha: str
    hora: str
    id_cliente: int
    monto_abonado: float
    id_metodo_pago: int
    id_pago: Optional[int] = None

@dataclass
class Gasto:
    """Representa un egreso de dinero de la caja registradora.
    
    Attributes:
        fecha (str): Fecha del gasto.
        hora (str): Hora del gasto.
        categoria (str): Clasificación del gasto (ej. Proveedores, Servicios).
        descripcion (str): Detalle del egreso.
        monto (float): Cantidad de dinero retirada.
        id_gasto (Optional[int]): ID interno autoincremental.
    """
    fecha: str
    hora: str
    categoria: str
    descripcion: str
    monto: float
    id_gasto: Optional[int] = None

@dataclass
class TurnoCaja:
    """Representa una sesión de trabajo o turno de caja para control de efectivo.
    
    Attributes:
        id_turno_str (str): Identificador alfanumérico único del turno (ej. TRN2408...).
        fecha_apertura (str): Fecha en que se abrió la caja.
        hora_apertura (str): Hora en que se abrió la caja.
        fondo_inicial (float): Dinero con el que arranca la caja.
        fecha_cierre (Optional[str]): Fecha de cierre.
        hora_cierre (Optional[str]): Hora de cierre.
        total_calculado (float): Dinero que el sistema espera que haya (Teórico).
        total_real (float): Dinero físico contado por el cajero (Arqueo).
        diferencia (float): Faltante (-) o Sobrante (+).
        estado (str): 'Abierto' o 'Cerrado'.
        id_turno (Optional[int]): ID interno autoincremental.
    """
    id_turno_str: str
    fecha_apertura: str
    hora_apertura: str
    fondo_inicial: float
    fecha_cierre: Optional[str] = None
    hora_cierre: Optional[str] = None
    total_calculado: float = 0.0
    total_real: float = 0.0
    diferencia: float = 0.0
    estado: str = 'Abierto'
    id_turno: Optional[int] = None