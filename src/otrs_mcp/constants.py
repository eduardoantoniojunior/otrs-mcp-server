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

# Ordenacao de artigos retornados por get_ticket/get_ticket_articles.
VALID_ARTICLE_ORDERS = frozenset({"asc", "desc"})

# Campos que podem ser devolvidos por artigo. Corpo bruto do OTRS traz
# cabecalhos completos, anexos e metadados internos; aqui aplicamos um
# whitelist explicito para evitar vazar dados nao pedidos para o cliente MCP.
ARTICLE_WHITELIST_FIELDS = frozenset(
    {
        "ArticleID",
        "Subject",
        "Body",
        "SenderType",
        "ArticleType",
        "CommunicationChannel",  # OTRS >= 6 usa este em vez de ArticleType
        "IsVisibleForCustomer",
        "CreateTime",
        "ChangeTime",
        "From",
        "To",
        "Cc",
        "ContentType",
        "Charset",
        "MimeType",
    }
)
