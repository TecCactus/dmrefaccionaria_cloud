# DMRefaccionaria Cloud — Gestión de Inventario y Cotizaciones en Tiempo Real (NoSQL Clave-Valor)

Aplicación de consola desarrollada en Python conectada a una base de datos **NoSQL Clave-Valor alojada en la nube (Upstash Redis)** para la operación diaria de una refaccionaria automotriz. Permite gestionar el catálogo de piezas, generar cotizaciones temporales en mostrador con expiración automática (**TTL**), consultar rankings de demanda en tiempo real y mantener una bitácora de movimientos.

---

## Arquitectura y Stack Tecnológico

* **Lenguaje:** Python 3.10+
* **Base de Datos en la Nube:** Upstash Redis (Servicio Managed / Serverless DaaS sobre AWS `us-east-1`, paradigma Clave-Valor).
* **SDK Oficial:** `upstash-redis` (comunicación cifrada vía HTTPS REST API).
* **Gestión de Credenciales:** `python-dotenv` mediante variables de entorno (`.env`).

---

## Diseño del Modelo Clave-Valor (Estructuras Redis)

| Namespace / Clave | Tipo de Dato Redis | Propósito y Comandos Principales |
| :--- | :--- | :--- |
| `refaccion:<codigo>` | **Hash** | Almacena los atributos de cada pieza (`codigo`, `nombre`, `marca`, `vehiculo`, `precio`, `stock`). Comandos: `HSET`, `HGETALL`, `EXISTS`, `DEL`. |
| `catalogo:codigos` | **Set** | Índice de códigos activos para listar el catálogo sin bloquear el servidor con `KEYS *`. Comandos: `SADD`, `SMEMBERS`, `SREM`. |
| `cotizacion:<cliente>` | **Hash + TTL** | Guarda cotizaciones activas en mostrador con tiempo de vida limitado. Redis elimina la clave automáticamente al expirar. Comandos: `HSET`, `EXPIRE`, `TTL`, `DEL`. |
| `ranking:refacciones_top` | **Sorted Set** | Clasifica automáticamente las refacciones más cotizadas según demanda acumulada. Comandos: `ZADD`, `ZINCRBY`, `ZREVRANGE`. |
| `historial:movimientos` | **List** | Bitácora cronológica que conserva las últimas 15 operaciones del sistema. Comandos: `LPUSH`, `LTRIM`, `LRANGE`. |

---

## Estructura del Proyecto

```text
dmrefaccionaria_cloud/
├── .env.example        # Plantilla de variables de entorno (sin credenciales reales)
├── .gitignore          # Exclusión de .env y archivos temporales de Python
├── database.py         # Configuración de conexión remota y validación PING a Upstash
├── seed.py             # Script de carga inicial (seeding) de catálogo, ranking y cotización
├── services.py         # Lógica de negocio (CRUD, TTL, Sorted Sets y Lists)
├── main.py             # Interfaz interactiva de consola (CLI)
└── README.md           # Documentación técnica del repositorio