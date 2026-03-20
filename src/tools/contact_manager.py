"""
Tool 3: ContactManager
Lee información de personas de contacto.
"""
import json
import os
from langchain_core.tools import Tool

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")
CONTACTS_DIR = os.path.join(DATA_DIR, "contactos")


def contact_manager(query: str) -> str:
    """
    Consulta información de contactos (personas).
    Input: 'list_all' para listar todos, o un contact_id para ver detalle.
    """
    if query.strip() == "list_all":
        contacts = []
        for filename in sorted(os.listdir(CONTACTS_DIR)):
            if filename.endswith(".json"):
                filepath = os.path.join(CONTACTS_DIR, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    c = json.load(f)
                contacts.append(f"{c['id']}: {c['nombre']} — {c.get('rol', 'N/A')} — tel: {c.get('telefono', 'N/A')}")
        return "\n".join(contacts) if contacts else "No hay contactos registrados"

    # Buscar por ID
    contact_id = query.strip()
    filepath = os.path.join(CONTACTS_DIR, f"{contact_id}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f), ensure_ascii=False, indent=2)

    # Buscar en todos los archivos por ID interno
    for filename in os.listdir(CONTACTS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(CONTACTS_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                c = json.load(f)
            if c.get("id") == contact_id:
                return json.dumps(c, ensure_ascii=False, indent=2)

    return f"Contacto '{contact_id}' no encontrado"


contact_manager_tool = Tool(
    name="ContactManager",
    description="""Lee información de personas de contacto de NV Mexico.
    Input: 'list_all' para listar todos los contactos con teléfono y rol,
    o un contact_id para ver detalle completo.""",
    func=contact_manager,
)
