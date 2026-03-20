"""
Tool 3: ContactManager
Lee información de personas de contacto.
"""
import json
import os
from langchain_core.tools import Tool

DATA_DIR = os.getenv("KALENDBOT_DATA_DIR", "./kalendbot-data")
CONTACTS_DIR = os.path.join(DATA_DIR, "contactos")


def _load_all_contacts() -> list[dict]:
    """Carga todos los contactos del directorio."""
    contacts = []
    if not os.path.exists(CONTACTS_DIR):
        return contacts
    for filename in sorted(os.listdir(CONTACTS_DIR)):
        if filename.endswith(".json"):
            filepath = os.path.join(CONTACTS_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                contacts.append(json.load(f))
    return contacts


def _search_by_name(name: str) -> list[dict]:
    """Búsqueda parcial case-insensitive por nombre."""
    name_lower = name.lower().strip()
    results = []
    for c in _load_all_contacts():
        nombre = c.get("nombre", "").lower()
        contact_id = c.get("id", "").lower()
        if name_lower in nombre or name_lower in contact_id:
            results.append(c)
    return results


def contact_manager(query: str) -> str:
    """
    Consulta información de contactos (personas).
    Input: 'list_all' para listar todos, 'search:nombre' para buscar por nombre parcial,
    o un contact_id para ver detalle.
    """
    query = query.strip()

    if query == "list_all":
        contacts = _load_all_contacts()
        if not contacts:
            return "No hay contactos registrados"
        lines = [f"{c['id']}: {c['nombre']} — {c.get('rol', 'N/A')} — tel: {c.get('telefono', 'N/A')}" for c in contacts]
        return "\n".join(lines)

    # Búsqueda por nombre parcial
    if query.startswith("search:"):
        name = query[7:].strip()
        if not name:
            return "Error: Falta el nombre a buscar. Uso: search:nombre"
        results = _search_by_name(name)
        if not results:
            return f"No se encontraron contactos con nombre '{name}'"
        lines = [f"{c['id']}: {c['nombre']} — {c.get('rol', 'N/A')} — tel: {c.get('telefono', 'N/A')}" for c in results]
        return f"Encontrados {len(results)} contacto(s):\n" + "\n".join(lines)

    # Buscar por ID exacto (archivo)
    filepath = os.path.join(CONTACTS_DIR, f"{query}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f), ensure_ascii=False, indent=2)

    # Buscar en todos los archivos por ID interno
    for c in _load_all_contacts():
        if c.get("id") == query:
            return json.dumps(c, ensure_ascii=False, indent=2)

    # Fallback: intentar búsqueda por nombre como último recurso
    results = _search_by_name(query)
    if results:
        if len(results) == 1:
            return json.dumps(results[0], ensure_ascii=False, indent=2)
        lines = [f"{c['id']}: {c['nombre']} — {c.get('rol', 'N/A')}" for c in results]
        return f"No se encontró ID '{query}', pero se encontraron {len(results)} contacto(s) por nombre:\n" + "\n".join(lines)

    return f"Contacto '{query}' no encontrado"


contact_manager_tool = Tool(
    name="ContactManager",
    description="""Lee información de personas de contacto de NV Mexico.
    Input: 'list_all' para listar todos los contactos,
    'search:nombre' para buscar por nombre parcial (ej: 'search:Koen'),
    o un contact_id para ver detalle completo.
    IMPORTANTE: Para buscar una persona por nombre, usa 'search:nombre' primero.""",
    func=contact_manager,
)
