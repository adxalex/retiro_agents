
"""CLI interactivo del agente del Parque del Retiro."""

from uuid import uuid4

from src.agent import aprobar_plan, procesar_turno


def mostrar_resultado(resultado: dict) -> None:
    """Muestra la respuesta y el estado de la operación."""
    if resultado.get("error"):
        print(f"\nError: {resultado['error']}")

    if resultado.get("respuesta"):
        print("\nRespuesta:")
        print(resultado["respuesta"])

    if resultado.get("plan"):
        print("\nPlan propuesto:")
        for indice, paso in enumerate(resultado["plan"], start=1):
            print(f"{indice}. {paso}")

    if resultado.get("pendiente_aprobacion"):
        print("\nEl plan está pendiente de aprobación.")

    if resultado.get("done"):
        print("\nEl plan ha sido aprobado y el flujo ha terminado.")


def modo_interactivo() -> None:
    """Mantiene una conversación hasta que el usuario decida salir."""
    thread_id = str(uuid4())

    print("Agente del Parque del Retiro")
    print("Escribe 'salir' para terminar la conversación.")
    print(f"Identificador de conversación: {thread_id}")

    while True:
        texto = input("\nTú: ").strip()

        if texto.lower() in {"salir", "exit", "quit"}:
            print("Conversación finalizada.")
            break

        if not texto:
            print("Escribe una consulta para continuar.")
            continue

        resultado = procesar_turno(texto, thread_id)
        mostrar_resultado(resultado)

        if resultado.get("pendiente_aprobacion"):
            while True:
                decision = input(
                    "\n¿Apruebas el plan? (s/n): "
                ).strip().lower()
                
                if decision in {"salir", "exit", "quit"}:
                    print("Conversación finalizada.")
                    return

                if decision in {"s", "si", "sí"}:
                    resultado = aprobar_plan(thread_id, True)
                    mostrar_resultado(resultado)

                    if resultado.get("error"):
                        continue

                    break

                if decision == "n":
                    comentario = input(
                        "¿Qué cambiarías del plan? (opcional): "
                    ).strip()

                    resultado = aprobar_plan(
                        thread_id,
                        False,
                        comentario,
                    )
                    mostrar_resultado(resultado)

                    if resultado.get("error"):
                        continue

                    break

                print("Introduce 's' para aprobar o 'n' para rechazar.")


def main() -> None:
    """Punto de entrada del programa."""
    modo_interactivo()


if __name__ == "__main__":
    main()
