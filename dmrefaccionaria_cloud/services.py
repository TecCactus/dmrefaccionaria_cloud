from datetime import datetime
from upstash_redis import Redis


class RefaccionariaError(Exception):
    """Excepción controlada para reglas de negocio en DMRefaccionaria."""
    pass


class RefaccionariaService:
    def __init__(self, redis: Redis):
        self.redis = redis

    def _registrar_evento(self, mensaje: str) -> None:
        """Guarda un movimiento en una List de Redis y conserva solo los últimos 15."""
        hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.redis.lpush("historial:movimientos", f"[{hora}] {mensaje}")
        self.redis.ltrim("historial:movimientos", 0, 14)

    # =========================================================================
    # 1. CRUD DE REFACCIONES (Hashes + Set índice)
    # =========================================================================

    def crear_refaccion(self, codigo: str, nombre: str, marca: str, vehiculo: str, precio: float, stock: int) -> dict:
        codigo = codigo.strip().upper()
        if not codigo or not nombre.strip():
            raise RefaccionariaError("El código y el nombre de la refacción son obligatorios.")
        if precio <= 0 or stock < 0:
            raise RefaccionariaError("El precio debe ser mayor a 0 y el stock no puede ser negativo.")

        clave = f"refaccion:{codigo}"
        if self.redis.exists(clave):
            raise RefaccionariaError(f"Ya existe una refacción con el código '{codigo}'.")

        datos = {
            "codigo": codigo,
            "nombre": nombre.strip(),
            "marca": marca.strip(),
            "vehiculo": vehiculo.strip(),
            "precio": f"{precio:.2f}",
            "stock": str(stock)
        }

        self.redis.hset(clave, values=datos)
        self.redis.sadd("catalogo:codigos", codigo)
        self._registrar_evento(f"ALTA: {codigo} - {datos['nombre']} (${datos['precio']})")
        return datos

    def obtener_refaccion(self, codigo: str) -> dict:
        codigo = codigo.strip().upper()
        datos = self.redis.hgetall(f"refaccion:{codigo}")
        if not datos:
            raise RefaccionariaError(f"No se encontró la refacción '{codigo}'.")
        return datos

    def listar_refacciones(self) -> list[dict]:
        codigos = sorted(self.redis.smembers("catalogo:codigos") or [])
        resultado = []
        for cod in codigos:
            datos = self.redis.hgetall(f"refaccion:{cod}")
            if datos:
                resultado.append(datos)
        return resultado

    def actualizar_refaccion(self, codigo: str, nuevo_precio: float | None = None, nuevo_stock: int | None = None) -> dict:
        codigo = codigo.strip().upper()
        clave = f"refaccion:{codigo}"
        if not self.redis.exists(clave):
            raise RefaccionariaError(f"No existe la refacción '{codigo}'.")

        cambios = {}
        if nuevo_precio is not None:
            if nuevo_precio <= 0:
                raise RefaccionariaError("El precio debe ser mayor a 0.")
            cambios["precio"] = f"{nuevo_precio:.2f}"

        if nuevo_stock is not None:
            if nuevo_stock < 0:
                raise RefaccionariaError("El stock no puede ser negativo.")
            cambios["stock"] = str(nuevo_stock)

        if not cambios:
            raise RefaccionariaError("No se proporcionaron cambios para actualizar.")

        self.redis.hset(clave, values=cambios)
        self._registrar_evento(f"ACTUALIZACIÓN: {codigo} -> {cambios}")
        return self.redis.hgetall(clave)

    def eliminar_refaccion(self, codigo: str) -> None:
        codigo = codigo.strip().upper()
        clave = f"refaccion:{codigo}"
        if not self.redis.exists(clave):
            raise RefaccionariaError(f"No existe la refacción '{codigo}'.")

        self.redis.delete(clave)
        self.redis.srem("catalogo:codigos", codigo)
        self.redis.zrem("ranking:refacciones_top", codigo)
        self._registrar_evento(f"BAJA: Refacción {codigo} eliminada del catálogo")

    # =========================================================================
    # 2. COTIZACIONES TEMPORALES EN MOSTRADOR (Hash + TTL / EXPIRE)
    # =========================================================================

    def crear_cotizacion_temporal(self, cliente: str, codigo: str, cantidad: int, ttl_segundos: int = 60) -> dict:
        cliente_slug = cliente.strip().lower().replace(" ", "_")
        if not cliente_slug:
            raise RefaccionariaError("El nombre del cliente o taller es obligatorio.")
        if cantidad <= 0 or ttl_segundos <= 0:
            raise RefaccionariaError("La cantidad y el tiempo TTL deben ser mayores a 0.")

        refaccion = self.obtener_refaccion(codigo)
        stock_actual = int(refaccion["stock"])
        if cantidad > stock_actual:
            raise RefaccionariaError(f"Stock insuficiente. Disponible: {stock_actual} unidades.")

        total = float(refaccion["precio"]) * cantidad
        clave_cot = f"cotizacion:{cliente_slug}"

        cotizacion = {
            "cliente": cliente.strip(),
            "codigo_refaccion": refaccion["codigo"],
            "nombre_refaccion": refaccion["nombre"],
            "cantidad": str(cantidad),
            "total": f"{total:.2f}"
        }

        self.redis.hset(clave_cot, values=cotizacion)
        self.redis.expire(clave_cot, ttl_segundos)

        self.redis.zincrby("ranking:refacciones_top", cantidad, refaccion["codigo"])
        self._registrar_evento(
            f"COTIZACIÓN (TTL {ttl_segundos}s): {cliente.strip()} cotizó {cantidad}x {refaccion['codigo']} (${total:.2f})"
        )
        return cotizacion

    def consultar_cotizacion(self, cliente: str) -> tuple[dict, int]:
        cliente_slug = cliente.strip().lower().replace(" ", "_")
        clave_cot = f"cotizacion:{cliente_slug}"
        datos = self.redis.hgetall(clave_cot)
        if not datos:
            raise RefaccionariaError(
                f"No hay cotización activa para '{cliente}' (no existe o ya expiró su TTL)."
            )
        segundos_restantes = self.redis.ttl(clave_cot)
        return datos, segundos_restantes

    def confirmar_venta_cotizacion(self, cliente: str) -> dict:
        cliente_slug = cliente.strip().lower().replace(" ", "_")
        clave_cot = f"cotizacion:{cliente_slug}"
        cotizacion = self.redis.hgetall(clave_cot)
        if not cotizacion:
            raise RefaccionariaError("La cotización ya expiró o no existe.")

        codigo = cotizacion["codigo_refaccion"]
        cantidad = int(cotizacion["cantidad"])
        refaccion = self.obtener_refaccion(codigo)

        nuevo_stock = int(refaccion["stock"]) - cantidad
        if nuevo_stock < 0:
            raise RefaccionariaError("Stock insuficiente al intentar cerrar la venta.")

        self.redis.hset(f"refaccion:{codigo}", values={"stock": str(nuevo_stock)})
        self.redis.delete(clave_cot)
        self._registrar_evento(
            f"VENTA CONFIRMADA: {cotizacion['cliente']} compró {cantidad}x {codigo} (${cotizacion['total']})"
        )
        return cotizacion

    # =========================================================================
    # 3. CONSULTAS ESPECIALIZADAS: TOP RANKING (Sorted Set) E HISTORIAL (List)
    # =========================================================================

    def obtener_top_refacciones(self, limite: int = 5) -> list[tuple[str, float]]:
        return self.redis.zrevrange("ranking:refacciones_top", 0, limite - 1, withscores=True) or []

    def obtener_historial(self) -> list[str]:
        return self.redis.lrange("historial:movimientos", 0, 14) or []