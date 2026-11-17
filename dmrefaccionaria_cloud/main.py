from database import get_redis_client
from services import RefaccionariaService, RefaccionariaError


def mostrar_menu():
    print("\n" + "=" * 54)
    print("   DMREFACCIONARIA — SISTEMA CLOUD (UPSTASH REDIS)")
    print("=" * 54)
    print("1. Listar catálogo de refacciones (Read - Hashes)")
    print("2. Buscar refacción por código (Read - HGETALL)")
    print("3. Registrar nueva refacción (Create - HSET)")
    print("4. Actualizar precio o stock (Update - HSET)")
    print("5. Eliminar refacción (Delete - DEL)")
    print("6. Crear cotización temporal con TTL (EXPIRE)")
    print("7. Consultar cotización activa y segundos TTL")
    print("8. Confirmar compra de cotización activa")
    print("9. Ver Top Refacciones más cotizadas (Sorted Set)")
    print("10. Ver bitácora de últimos movimientos (List)")
    print("0. Salir")


def main():
    try:
        redis = get_redis_client()
        service = RefaccionariaService(redis)
        print("[OK] Conectado exitosamente a Upstash Redis en la nube.")
    except Exception as e:
        print(f"[ERROR DE CONEXIÓN] {e}")
        return

    while True:
        mostrar_menu()
        opcion = input("Seleccione una opción (0-10): ").strip()

        try:
            if opcion == "1":
                items = service.listar_refacciones()
                if not items:
                    print("El catálogo está vacío.")
                else:
                    print(f"\n{'CÓDIGO':<10} | {'NOMBRE':<30} | {'MARCA':<10} | {'PRECIO':<10} | {'STOCK'}")
                    print("-" * 78)
                    for r in items:
                        print(f"{r['codigo']:<10} | {r['nombre']:<30} | {r['marca']:<10} | ${r['precio']:<9} | {r['stock']}")

            elif opcion == "2":
                cod = input("Código de la refacción (ej. BAL-001): ")
                r = service.obtener_refaccion(cod)
                print(f"\n[ENCONTRADO] {r['codigo']} — {r['nombre']}")
                print(f"  Marca: {r['marca']} | Vehículo: {r['vehiculo']}")
                print(f"  Precio: ${r['precio']} | Stock disponible: {r['stock']} uds.")

            elif opcion == "3":
                cod = input("Código (ej. ACE-006): ")
                nombre = input("Nombre de la pieza: ")
                marca = input("Marca: ")
                vehiculo = input("Vehículo compatible: ")
                precio = float(input("Precio ($): "))
                stock = int(input("Stock inicial: "))
                creado = service.crear_refaccion(cod, nombre, marca, vehiculo, precio, stock)
                print(f"[ÉXITO] Refacción '{creado['codigo']}' guardada en Upstash Redis.")

            elif opcion == "4":
                cod = input("Código de la refacción a actualizar: ")
                p_txt = input("Nuevo precio (dejar vacío para no cambiar): ").strip()
                s_txt = input("Nuevo stock (dejar vacío para no cambiar): ").strip()
                nuevo_precio = float(p_txt) if p_txt else None
                nuevo_stock = int(s_txt) if s_txt else None
                act = service.actualizar_refaccion(cod, nuevo_precio, nuevo_stock)
                print(f"[ÉXITO] {act['codigo']} actualizado -> Precio: ${act['precio']} | Stock: {act['stock']}")

            elif opcion == "5":
                cod = input("Código de la refacción a eliminar: ")
                service.eliminar_refaccion(cod)
                print(f"[ÉXITO] Refacción '{cod.upper()}' eliminada.")

            elif opcion == "6":
                cliente = input("Nombre del cliente o taller (ej. Taller Maya): ")
                cod = input("Código de refacción a cotizar: ")
                cant = int(input("Cantidad de piezas: "))
                ttl = int(input("Tiempo de vigencia TTL en segundos (ej. 45): "))
                cot = service.crear_cotizacion_temporal(cliente, cod, cant, ttl)
                print(f"[ÉXITO] Cotización creada para '{cot['cliente']}' por ${cot['total']} (Expira en {ttl}s).")

            elif opcion == "7":
                cliente = input("Nombre del cliente o taller a consultar: ")
                cot, ttl_restante = service.consultar_cotizacion(cliente)
                print(f"\n[COTIZACIÓN ACTIVA] Cliente: {cot['cliente']}")
                print(f"  Pieza: {cot['cantidad']}x {cot['nombre_refaccion']} ({cot['codigo_refaccion']})")
                print(f"  Total: ${cot['total']} | Tiempo restante antes de expirar: {ttl_restante} segundos")

            elif opcion == "8":
                cliente = input("Nombre del cliente o taller que confirma compra: ")
                venta = service.confirmar_venta_cotizacion(cliente)
                print(f"[ÉXITO] Venta cerrada para '{venta['cliente']}' por ${venta['total']}. Stock descontado.")

            elif opcion == "9":
                top = service.obtener_top_refacciones(5)
                print("\n--- TOP REFACCIONES MÁS COTIZADAS (Sorted Set) ---")
                for pos, (cod, puntos) in enumerate(top, start=1):
                    print(f"  #{pos} {cod} — {int(puntos)} unidades cotizadas")

            elif opcion == "10":
                eventos = service.obtener_historial()
                print("\n--- BITÁCORA DE MOVIMIENTOS RECIENTES (List) ---")
                for ev in eventos:
                    print(f"  • {ev}")

            elif opcion == "0":
                print("Cerrando sesión de DMRefaccionaria. ¡Hasta luego!")
                break

            else:
                print("[AVISO] Opción no válida. Elija del 0 al 10.")

        except ValueError:
            print("[ERROR DE FORMATO] Ingrese valores numéricos válidos para precio, stock, cantidad o TTL.")
        except RefaccionariaError as e:
            print(f"[REGLA DE NEGOCIO] {e}")
        except Exception as e:
            print(f"[ERROR INESPERADO] {e}")


if __name__ == "__main__":
    main()