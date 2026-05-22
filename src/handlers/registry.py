"""
Command registry — single source of truth for all bot commands.
Both Telegram and WhatsApp channel adapters consume this registry.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Awaitable

logger = logging.getLogger("kalendbot.handlers.registry")


@dataclass
class CommandContext:
    """Channel-agnostic context passed to every command handler."""
    contact_id: str | None
    phone: str
    text: str                     # arguments after command name
    language: str                 # user's language preference ("es", "en", "nl")
    channel: str                  # "telegram" | "whatsapp"


@dataclass
class CommandResult:
    """Channel-agnostic result returned by every command handler."""
    text: str | None = None       # response text
    file_path: str | None = None  # file to send (export)
    image_path: str | None = None # image to send
    error: str | None = None      # error message


@dataclass
class CommandDef:
    """Definition of a command in the registry."""
    name: str
    aliases: list[str]
    handler: Callable[[CommandContext], Awaitable[CommandResult]]
    permission: str = "readonly"  # minimum role: "readonly", "contacto", "tester", "admin"
    description: dict[str, str] = field(default_factory=dict)


# Global command list — populated by register_command() calls from handler modules
_COMMANDS: list[CommandDef] = []


def register_command(cmd: CommandDef) -> None:
    """Register a command definition."""
    _COMMANDS.append(cmd)


def find_command(name: str) -> CommandDef | None:
    """Find a command by name or alias (case-insensitive)."""
    name_lower = name.lower()
    for cmd in _COMMANDS:
        if cmd.name == name_lower or name_lower in cmd.aliases:
            return cmd
    return None


def get_all_commands() -> list[CommandDef]:
    """Return all registered commands."""
    return list(_COMMANDS)


def get_commands_for_menu(language: str) -> list[tuple[str, str]]:
    """Return (command_name, description) pairs for a given language."""
    result = []
    for cmd in _COMMANDS:
        desc = cmd.description.get(language, cmd.description.get("es", cmd.name))
        result.append((cmd.name, desc))
    return result


def check_permission(contact_role: str, required: str) -> bool:
    """Check if a role meets the minimum permission level."""
    hierarchy = {"readonly": 0, "contacto": 1, "tester": 2, "admin": 3}
    return hierarchy.get(contact_role, 0) >= hierarchy.get(required, 0)
