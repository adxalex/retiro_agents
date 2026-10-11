"""CLI del sistema RAG: indexar el corpus (offline) y preguntar (online).

Ejemplos:

    python main.py --index                 # construye el indice
    python main.py --index --recreate-index
    python main.py --query "¿A que hora cierra el parque?"
    python main.py --ask   "¿A que hora cierra el parque?"
    python main.py --ask   "..." --top-k 5 --category seguridad
    python main.py --ask   "..." --json     # salida JSON, para scripts

--query solo recupera fragmentos (util para depurar el retrieval).
--ask ejecuta el flujo completo y puede abstenerse si no hay evidencia.
"""

from __future__ import annotations

import argparse
import json
import sys

from config import COLLECTION_NAME, LLM_MODEL, TOP_K

ANCHO = 78


def _titulo(texto: str) -> None:
    print(f"\n{texto}\n{'-' * min(len(texto), ANCHO)}")


def _fragmento(numero: int, chunk: dict, caracteres: int = 300) -> None:
    """Imprime un chunk recuperado con su procedencia y su score."""
    procedencia = chunk.get("source", "desconocida")
    if chunk.get("page"):
        procedencia += f", pagina {chunk['page']}"
    if chunk.get("category"):
        procedencia += f", {chunk['category']}"

    texto = " ".join(chunk.get("text", "").split())
    if len(texto) > caracteres:
        texto = texto[:caracteres].rstrip() + "..."

    print(f"\n[{numero}] score {chunk['score']:.3f} · {procedencia}")
    print(f"    {chunk.get('chunk_id', '')}")
    print(f"    {texto}")


def cmd_index(recreate: bool = False, dry_run: bool = False) -> int:
    """Carga, chunkea e indexa el corpus completo.

    Por defecto NO recrea la coleccion: hace upsert sobre la existente. Para
    reconstruirla desde cero hay que pedirlo con --recreate-index, porque
    regenerar los embeddings consume cuota de la API.
    """
    from src.pipeline import build_index

    informe = build_index(recreate=recreate, dry_run=dry_run)

    _titulo("Dry run completado" if dry_run else "Indexacion completada")
    print(f"Documentos cargados: {informe['documents']}")
    print(f"Fuentes diferentes:  {informe['sources']}")
    print(f"Chunks generados:    {informe['chunks']}")
    for grupo, cuantos in informe.get("chunks_by_group", {}).items():
        print(f"  {grupo}: {cuantos}")
    if informe.get("indexed"):
        print(f"\nRegistros en Chroma: {informe.get('collection_count')}")
        print("Coleccion recreada desde cero." if recreate
              else "Upsert sobre la coleccion existente.")
    else:
        print("\nNo se ha llamado a Gemini ni a Chroma.")
    return 0


def cmd_query(pregunta: str, top_k: int = TOP_K, category: str | None = None,
              como_json: bool = False) -> int:
    """Ejecuta solo retrieval y muestra los chunks recuperados."""
    from src.retrieve import retrieve

    where = {"category": category} if category else None
    chunks = retrieve(pregunta, top_k=top_k, where=where)

    if como_json:
        print(json.dumps(chunks, ensure_ascii=False, indent=2))
        return 0

    _titulo(f"Fragmentos recuperados para: {pregunta}")
    if not chunks:
        print("\nNo se ha recuperado ningun fragmento. ¿Esta creado el indice?")
        print(f"Prueba: python main.py --index   (coleccion: {COLLECTION_NAME})")
        return 1

    for numero, chunk in enumerate(chunks, start=1):
        _fragmento(numero, chunk)
    print(f"\n{len(chunks)} fragmentos · top_k={top_k}")
    return 0


def cmd_ask(pregunta: str, top_k: int = TOP_K, category: str | None = None,
            score_minimo: float | None = None, mostrar_contexto: bool = False,
            como_json: bool = False) -> int:
    """Ejecuta el flujo RAG completo y muestra la respuesta."""
    from src.generate import responder

    where = {"category": category} if category else None
    salida = responder(
        pregunta,
        top_k=top_k,
        score_minimo=score_minimo,
        where=where,
    )

    if como_json:
        print(json.dumps(salida, ensure_ascii=False, indent=2))
        return 0

    _titulo(f"Pregunta: {pregunta}")
    print(f"\n{salida['respuesta']}")

    if salida["abstuvo"]:
        print(f"\n(abstencion: {salida['motivo_abstencion']})")
    elif salida["fuentes"]:
        print("\nFuentes:")
        for numero, fuente in enumerate(salida["fuentes"], start=1):
            print(f"  [{numero}] {fuente}")

    if mostrar_contexto and salida["chunks"]:
        _titulo("Contexto recuperado")
        for numero, chunk in enumerate(salida["chunks"], start=1):
            _fragmento(numero, chunk)

    print(f"\nmodelo: {LLM_MODEL} · top_k={top_k} · "
          f"chunks={len(salida['chunks'])}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG - Parque de El Retiro")
    parser.add_argument("--index", action="store_true", help="Indexar el corpus")
    parser.add_argument("--recreate-index", action="store_true",
                        help="Borrar y reconstruir el indice desde cero")
    parser.add_argument("--query", type=str, help="Solo retrieval, sin generacion")
    parser.add_argument("--ask", type=str, help="Respuesta RAG completa")
    parser.add_argument("--top-k", type=int, default=TOP_K,
                        help=f"Numero de fragmentos a recuperar (por defecto {TOP_K})")
    parser.add_argument("--category", type=str,
                        help="Filtra por categoria (historia, seguridad...)")
    parser.add_argument("--score-minimo", type=float,
                        help="Umbral de abstencion; por defecto, el de .env")
    parser.add_argument("--contexto", action="store_true",
                        help="Con --ask, muestra tambien los fragmentos usados")
    parser.add_argument("--dry-run", action="store_true",
                        help="Con --index, valida load y chunk sin llamar a Gemini")
    parser.add_argument("--saludo", action="store_true",
                        help="Muestra el saludo con el tiempo actual del Retiro")
    parser.add_argument("--json", action="store_true",
                        help="Salida en JSON en lugar de texto")
    args = parser.parse_args()

    if args.top_k <= 0:
        parser.error("--top-k debe ser mayor que 0.")

    try:
        if args.saludo:
            from src.contexto_visita import saludo_contextual, texto_de_bienvenida

            print(texto_de_bienvenida(saludo_contextual()))
            return 0
        if args.index:
            return cmd_index(recreate=args.recreate_index, dry_run=args.dry_run)
        if args.query:
            return cmd_query(args.query, top_k=args.top_k, category=args.category,
                             como_json=args.json)
        if args.ask:
            return cmd_ask(args.ask, top_k=args.top_k, category=args.category,
                           score_minimo=args.score_minimo,
                           mostrar_contexto=args.contexto, como_json=args.json)
        parser.print_help()
        return 0
    except KeyboardInterrupt:
        print("\nCancelado.", file=sys.stderr)
        return 130
    except Exception as error:  # noqa: BLE001
        mensaje = str(error)
        print(f"\nError: {mensaje}", file=sys.stderr)
        if "does not exist" in mensaje or COLLECTION_NAME in mensaje:
            print(
                f"La coleccion '{COLLECTION_NAME}' todavia no existe: hay que "
                "construir el indice antes de consultar.\n"
                "  python main.py --index",
                file=sys.stderr,
            )
        elif "API key" in mensaje or "GEMINI_API_KEY" in mensaje:
            print("Revisa que GEMINI_API_KEY este definida en tu .env.",
                  file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
