"""Constantes do OTRS MCP Server."""

VALID_PRIORITIES = frozenset(
    {"1 very low", "2 low", "3 normal", "4 high", "5 very high"}
)

VALID_STATES = frozenset(
    {
        "new",
        "open",
        "closed successful",
        "closed unsuccessful",
        "pending reminder",
        "pending auto close",
    }
)
