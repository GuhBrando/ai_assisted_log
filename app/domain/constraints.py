"""Limites do domínio usados pela validação da API (Pydantic) e pelo schema do banco.

Os dois leem daqui para não divergirem. Os valores seguem o contrato (docs/api/openapi.yaml).
"""

# Tags (RN-15)
TAG_PATTERN = r"^[a-z0-9_-]+:\S+$"
TAG_MAX_LENGTH = 100
MAX_TAGS = 20  # por log enviado e por aplicação
MAX_LOG_TAGS = 2 * MAX_TAGS  # lista final do log: as da aplicação somadas às do log, sem repetição

# Retenção (RN-08). O máximo também evita estourar o datetime do Python ao somar os dias.
RETENTION_DAYS_MIN = 1
RETENTION_DAYS_MAX = 3650
