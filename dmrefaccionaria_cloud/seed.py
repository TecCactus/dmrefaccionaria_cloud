from datetime import datetime
from database import get_redis_client

def poblar_base_datos():
    redis = get_redis_client()
    print("Conectado a Upstash Redis (Nube). Poblando inventario inicial de DMRefaccionaria...\n")

    catalogo_inicial = [
        {
            "codigo": "BAL-001",
            "nombre": "Balatas Delanteras Cerámicas",
            "marca": "Brembo",
            "vehiculo": "Chevrolet Aveo 2018-2023",
            "precio": "680.00",
            "stock": "14"
        },
        {
            "codigo": "FIL-002",
            "nombre": "Filtro de Aceite Sintético",
            "marca": "Gonher",
            "vehiculo": "Nissan Versa / March",
            "precio": "145.00",
            "stock": "30"
        },
        {
            "codigo": "AMO-003",
            "nombre": "Amortiguador Delantero Gas",
            "marca": "KYB",
            "vehiculo": "VW Vento / Polo",
            "precio": "1350.00",
            "stock": "8"
        },
        {
            "codigo": "BUJ-004",
            "nombre": "Juego de 4 Bujías Iridium",
            "marca": "NGK",
            "vehiculo": "Chevrolet Aveo / Spark",
            "precio": "520.00",
            "stock": "20"
        },
        {
            "codigo": "BAT-005",
            "nombre": "Acumulador 12V 550 CCA",
            "marca": "LTH",
            "vehiculo": "Universal Compacto",
            "precio": "2190.00",
            "stock": "6"
        }
    ]

    for item in catalogo_inicial:
        clave = f"refaccion:{item['codigo']}"
        redis.hset(clave, values=item)
        redis.sadd("catalogo:codigos", item["codigo"])

    redis.zadd("ranking:refacciones_top", {
        "BAL-001": 15,
        "FIL-002": 22,
        "AMO-003": 7,
        "BUJ-004": 12,
        "BAT-005": 4
    })

    clave_cot = "cotizacion:taller_peninsula"
    redis.hset(clave_cot, values={
        "cliente": "Taller Península",
        "codigo_refaccion": "BAL-001",
        "cantidad": "2",
        "total": "1360.00"
    })
    redis.expire(clave_cot, 120)

    hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    redis.delete("historial:movimientos")
    redis.lpush("historial:movimientos", f"[{hora}] SEED: Carga inicial de 5 refacciones en DMRefaccionaria")

    print("¡Listo! Se cargaron 5 refacciones, el ranking top y 1 cotización temporal con TTL de 120s.")

if __name__ == "__main__":
    poblar_base_datos()
    