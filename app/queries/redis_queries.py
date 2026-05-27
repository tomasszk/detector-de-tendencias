import json
from app.connections import get_redis_connection
from app.models.redis_keys import (
    TRENDING_GLOBAL,
    TRENDING_CAT,
    CACHE_TOP10_GLOBAL,
    CONTADOR_EVENTOS_TOTAL,
    SESION_USUARIO,
)


def get_redis_dashboard_data() -> dict:
    """
    Retorna los datos del dashboard Redis.
    Formato requerido por el contrato del proyecto.
    """
    r = get_redis_connection()

    try:
        # Contador total de eventos
        contador_raw = r.get(CONTADOR_EVENTOS_TOTAL)
        contador_eventos = int(contador_raw) if contador_raw else 0

        # Ranking global (top 10 desde Sorted Set)
        top_global_raw = r.zrevrange(TRENDING_GLOBAL, 0, 9, withscores=True)
        top_global = [{"producto_id": p, "score": s} for p, s in top_global_raw]

        # Ranking por categoría
        top_por_categoria = {}
        claves_cat = r.keys("trending:cat:*")
        for clave in claves_cat:
            categoria_id = clave.split(":")[-1]
            items = r.zrevrange(clave, 0, 9, withscores=True)
            top_por_categoria[categoria_id] = [
                {"producto_id": p, "score": s} for p, s in items
            ]

        # Cache top 10 global
        cache_raw = r.get(CACHE_TOP10_GLOBAL)
        cache_top10_global = json.loads(cache_raw) if cache_raw else []

        # Muestra de sesiones activas (máx. 5)
        claves_sesion = r.keys("sesion:*")
        sesiones_sample = []
        for clave in claves_sesion[:5]:
            datos = r.hgetall(clave)
            if datos:
                datos["usuario_id"] = clave.split(":")[-1]
                sesiones_sample.append(datos)

        return {
            "status": "ok",
            "contador_eventos": contador_eventos,
            "top_global": top_global,
            "top_por_categoria": top_por_categoria,
            "cache_top10_global": cache_top10_global,
            "sesiones_sample": sesiones_sample,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "contador_eventos": 0,
            "top_global": [],
            "top_por_categoria": {},
            "cache_top10_global": [],
            "sesiones_sample": [],
        }


def run_redis_queries() -> None:
    """
    Ejecuta y muestra las consultas demostrativas de Redis.
    Llamada desde app/queries/run_queries.py con run_redis_queries()
    """
    r = get_redis_connection()

    print("\n" + "="*50)
    print("REDIS - Consultas demostrativas")
    print("="*50)

    # 1. Ranking global top 10
    print("\n[1] Ranking global (top 10):")
    top10 = r.zrevrange(TRENDING_GLOBAL, 0, 9, withscores=True)
    for i, (producto, score) in enumerate(top10, 1):
        print(f"  {i}. {producto} — score: {score}")

    # 2. Ranking por categoría (primera encontrada)
    print("\n[2] Ranking por categoría (muestra):")
    claves_cat = r.keys("trending:cat:*")
    if claves_cat:
        clave = claves_cat[0]
        categoria_id = clave.split(":")[-1]
        items = r.zrevrange(clave, 0, 4, withscores=True)
        print(f"  Categoría: {categoria_id}")
        for producto, score in items:
            print(f"    {producto} — score: {score}")

    # 3. Cache top 10 con TTL
    print("\n[3] Cache top10_global:")
    cache_raw = r.get(CACHE_TOP10_GLOBAL)
    ttl = r.ttl(CACHE_TOP10_GLOBAL)
    if cache_raw:
        cache = json.loads(cache_raw)
        print(f"  TTL restante: {ttl}s | Productos en cache: {len(cache)}")
        for item in cache[:3]:
            print(f"    {item['producto_id']} — score: {item['score']}")
    else:
        print("  Cache expirada o no disponible.")

    # 4. Contador total de eventos
    print("\n[4] Contador total de eventos:")
    contador = r.get(CONTADOR_EVENTOS_TOTAL)
    print(f"  Total eventos procesados: {contador}")

    # 5. Sesiones con hashes y expiración
    print("\n[5] Sesiones de usuarios (muestra):")
    claves_sesion = r.keys("sesion:*")
    print(f"  Sesiones activas en Redis: {len(claves_sesion)}")
    for clave in claves_sesion[:3]:
        datos = r.hgetall(clave)
        ttl_sesion = r.ttl(clave)
        usuario_id = clave.split(":")[-1]
        print(f"  {usuario_id} | email: {datos.get('email')} | "
              f"eventos: {datos.get('eventos_generados')} | TTL: {ttl_sesion}s")

    print("\n[Dashboard completo]")
    dashboard = get_redis_dashboard_data()
    print(f"  status: {dashboard['status']}")
    print(f"  contador_eventos: {dashboard['contador_eventos']}")
    print(f"  top_global: {len(dashboard['top_global'])} productos")
    print(f"  top_por_categoria: {len(dashboard['top_por_categoria'])} categorias")
    print(f"  cache_top10_global: {len(dashboard['cache_top10_global'])} productos")
    print(f"  sesiones_sample: {len(dashboard['sesiones_sample'])} sesiones")
