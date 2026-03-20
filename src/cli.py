"""
CLI para probar KalendBot localmente sin WhatsApp/Evolution API.
Simula conversaciones con cualquier contacto.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Asegurar que src esté en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent import handle_message
from src.tools.contact_manager import contact_manager
from src.tools.calendar_manager import calendar_manager


def main():
    print("=" * 60)
    print("  KalendBot CLI — Modo de prueba local")
    print("=" * 60)
    print()

    # Listar contactos disponibles
    print("Contactos disponibles:")
    print(contact_manager("list_all"))
    print()

    # Elegir contacto
    contact_id = input("¿Con qué contacto quieres simular? (ID): ").strip()
    if not contact_id:
        print("Usando contacto genérico 'test-user'")
        contact_id = "test-user"

    print(f"\nSimulando conversación como '{contact_id}'")
    print("Escribe 'salir' para terminar, 'status' para ver calendario\n")

    while True:
        user_input = input(f"\n[{contact_id}]: ").strip()

        if user_input.lower() == "salir":
            print("¡Hasta luego!")
            break

        if user_input.lower() == "status":
            print("\nEventos pendientes:")
            print(calendar_manager(action="list_pending"))
            continue

        if not user_input:
            continue

        response = handle_message("cli", user_input, contact_id=contact_id)
        print(f"\n[KalendBot]: {response}")


if __name__ == "__main__":
    main()
