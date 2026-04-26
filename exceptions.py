"""Módulo de excepciones personalizadas para el dominio del Kiosko POS."""

class KioskoBaseError(Exception):
    """Clase base para todas las excepciones personalizadas del sistema."""
    pass

class ProductoNoEncontradoError(KioskoBaseError):
    """Lanzada cuando se intenta operar con un ID o Código de Barras inexistente."""
    pass

class StockInsuficienteError(KioskoBaseError):
    """Lanzada cuando se intenta vender una cantidad mayor al stock disponible."""
    pass

class ClienteNoEncontradoError(KioskoBaseError):
    """Lanzada cuando se intenta operar con un cliente inexistente."""
    pass

class TurnoCajaCerradoError(KioskoBaseError):
    """Lanzada cuando se intenta registrar una transacción sin un turno abierto."""
    pass