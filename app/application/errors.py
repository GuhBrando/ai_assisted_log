class NotAuthenticated(Exception):
    """Token ou API key ausente, inválida ou expirada → 401."""


class Forbidden(Exception):
    """Recurso existe mas o acesso é negado → 403."""


class NotFound(Exception):
    """Recurso não encontrado → 404."""


class Conflict(Exception):
    """Violação de unicidade (e-mail, nome de aplicação) → 409."""


class PayloadTooLarge(Exception):
    """information_data acima do limite de 64 KB → 413."""
