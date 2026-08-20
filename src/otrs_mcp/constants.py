"""Constantes do OTRS MCP Server."""

VALID_QUEUES = frozenset({"Raw", "Junk", "Misc"})

VALID_PRIORITIES = frozenset({"1 low", "2 normal", "3 normal", "4 high"})

VALID_STATES = frozenset({"new", "open", "closed successful", "closed unsuccessful", "pending reminder", "pending auto close"})

VALID_TYPES = frozenset({"Unclassified", "Customer complaint", "Incident", "Problem", "Task"})

DEFAULT_PRIORITY = "3 normal"

PRIORITY_VARIATIONS = ["3 normal", "1 Low", "2 normal", "4 high"]
