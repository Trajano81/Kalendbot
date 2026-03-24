from src.tools.calendar_manager import calendar_manager_tool
from src.tools.provider_manager import provider_manager_tool
from src.tools.contact_manager import contact_manager_tool
from src.tools.date_locker import date_locker_tool
from src.tools.conflict_detector import conflict_detector_tool
from src.tools.group_notifier import group_notifier_tool
from src.tools.flyer_manager import flyer_manager_tool
from src.tools.rules_engine import rules_engine_tool

READ_TOOLS = [
    calendar_manager_tool,
    provider_manager_tool,
    contact_manager_tool,
    conflict_detector_tool,
    rules_engine_tool,
]

WRITE_TOOLS = [
    date_locker_tool,
    group_notifier_tool,
    flyer_manager_tool,
]

ALL_TOOLS = READ_TOOLS + WRITE_TOOLS
