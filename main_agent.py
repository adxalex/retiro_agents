
"""CLI del agente del Parque del Retiro: demo y modo interactivo."""

import argparse
from uuid import uuid4

from src.agent import aprobar_plan, procesar_turno


def mostrar_traza(resultado: dict) -> None:
    """Muestra los eventos registrados durante la ejecución."""
    traza = resultado.get("traza") or []

    if not traza:
        print("\nNo hay eventos de traza disponibles.")
        return

    print("\nTraza de ejecución:")
    for evento in traza:
        origen = evento.get("origen", "desconocido")
        nombre = evento.get("nombre", "sin nombre")
        status = evento.get("status", "sin estado")
        preview = evento.get("preview", "")

        print(f"- [{origen}] {nombre} | {status}")
        if preview:
            print(f"  {preview}")


def mostrar_resultado(resultado: dict) -> None:
    """Muestra la respuesta, el plan, la traza y el estado."""
    if resultado.get("error"):
        print(f"\nError: {resultado['error']}")

    if resultado.get("respuesta"):
        print("\nRespuesta:")
        print(resultado["respuesta"])

    plan = resultado.get("plan") or []
    if plan:
        print("\nPlan propuesto:")
        for indice, paso in enumerate(plan, start=1):
            print(f"{indice}. {paso}")

    if resultado.get("pendiente_aprobacion"):
        print("\nEl plan está pendiente de aprobación.")

    if resultado.get("done"):
        print("\nEl plan ha sido aprobado y aplicado correctamente.")

    mostrar_traza(resultado)


def modo_demo() -> None:
    """Ejecuta un ejemplo preparado y muestra el flujo de aprobación."""
    thread_id = str(uuid4())

    print("=" * 55)
    print("DEMO DEL AGENTE DEL PARQUE DEL RETIRO")
    print("=" * 55)
    print("Modo demostración: la aprobación automática está permitida")
    print("exclusivamente en este modo para ilustrar el flujo HITL.")
    print(f"Identificador de conversación: {thread_id}")

    peticion = (
        "Organiza una visita por el Parque del Retiro teniendo en cuenta "
        "la hora, la meteorología y los lugares de interés."
    )

    print(f"\nPetición de demostración:\n{peticion}")

    resultado = procesar_turno(peticion, thread_id)
    mostrar_resultado(resultado)

    if resultado.get("error"):
        print("\nLa demo no ha podido completar la consulta.")
        print("Comprueba la configuración y la integración de las tools.")
        return

    if resultado.get("pendiente_aprobacion"):
        print("\n[DEMO] Se aprobará la propuesta para ilustrar el flujo HITL.")
        resultado = aprobar_plan(
            thread_id,
            True,
            "Aprobación automática exclusiva del modo demo.",
        )
        mostrar_resultado(resultado)

    elif not resultado.get("plan"):
        print(
            "\nLa consulta ha terminado sin una propuesta aprobable. "
            "Cuando las tools estén integradas y aporten información "
            "suficiente, se podrá demostrar también la aprobación."
        )

    if resultado.get("error"):
        print("\nLa aprobación de demostración ha devuelto un error.")


def modo_interactivo() -> None:
    """Mantiene una conversación con aprobación humana explícita."""
    thread_id = str(uuid4())

    print("Agente del Parque del Retiro")
    print("Escribe 'salir' para terminar.")
    print("Escribe '/nueva' para iniciar otra conversación.")
    print(f"Identificador de conversación: {thread_id}")

    while True:
        try:
            texto = input("\nTú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nConversación finalizada.")
            break

        if texto.lower() in {"salir", "exit", "quit"}:
            print("Conversación finalizada.")
            break

        if texto.lower() == "/nueva":
            thread_id = str(uuid4())
            print("\nNueva conversación iniciada.")
            print(f"Identificador de conversación: {thread_id}")
            continue

        if not texto:
            print("Escribe una consulta para continuar.")
            continue

        resultado = procesar_turno(texto, thread_id)
        mostrar_resultado(resultado)

        if resultado.get("error"):
            continue

        if not resultado.get("pendiente_aprobacion"):
            continue

        # En modo interactivo nunca se aprueba automáticamente.
        while True:
            try:
                decision = input(
                    "\n¿Apruebas el plan? (s/n): "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print(
                    "\nNo se ha registrado una decisión. "
                    "La propuesta sigue pendiente."
                )
                return

            if decision in {"salir", "exit", "quit"}:
                print("Conversación finalizada.")
                return

            if decision in {"s", "si", "sí"}:
                resultado = aprobar_plan(thread_id, True)
                mostrar_resultado(resultado)

                if resultado.get("error"):
                    print("No se ha podido completar la aprobación.")
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
                    print("No se ha podido registrar el rechazo.")
                else:
                    print(
                        "Puedes enviar una nueva petición en esta "
                        "misma conversación."
                    )
                break

            print("Introduce 's' para aprobar o 'n' para rechazar.")


def main() -> None:
    """Punto de entrada: permite elegir demo o modo interactivo."""
    parser = argparse.ArgumentParser(
        description="Agente del Parque del Retiro"
    )
    parser.add_argument(
        "--modo",
        choices=("demo", "interactivo"),
        default="interactivo",
        help="Modo de ejecución (por defecto: interactivo).",
    )
    args = parser.parse_args()

    if args.modo == "demo":
        modo_demo()
    else:
        modo_interactivo()


if __name__ == "__main__":
    main()
