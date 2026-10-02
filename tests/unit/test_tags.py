"""Testes unitários do tipo Tag (normalização e validação)."""

import pytest
from pydantic import BaseModel, ValidationError

from app.domain.tags import Tag


class _Model(BaseModel):
    tags: list[Tag]


def _parse(tags: list[str]) -> list[str]:
    return _Model(tags=tags).tags


def test_tag_valida_simples():
    assert _parse(["env:prod"]) == ["env:prod"]


def test_tag_normaliza_para_lowercase():
    assert _parse(["ENV:PROD"]) == ["env:prod"]


def test_tag_remove_espacos_nas_bordas():
    assert _parse(["  env:prod  "]) == ["env:prod"]


def test_tag_valor_com_caracteres_especiais():
    assert _parse(["version:1.2.3"]) == ["version:1.2.3"]


def test_tag_chave_com_hifen_e_underscore():
    assert _parse(["my_tag-key:valor"]) == ["my_tag-key:valor"]


def test_tag_invalida_sem_dois_pontos():
    with pytest.raises(ValidationError):
        _parse(["semDoisPontos"])


def test_tag_invalida_chave_vazia():
    with pytest.raises(ValidationError):
        _parse([":valor"])


def test_tag_invalida_valor_vazio():
    with pytest.raises(ValidationError):
        _parse(["chave:"])


def test_tag_invalida_espaco_no_valor():
    with pytest.raises(ValidationError):
        _parse(["chave:valor com espaco"])


def test_tag_invalida_muito_longa():
    longa = "a:b" + "x" * 200
    with pytest.raises(ValidationError):
        _parse([longa])


def test_multiplas_tags_validas():
    result = _parse(["env:prod", "version:2.0", "region:us-east-1"])
    assert result == ["env:prod", "version:2.0", "region:us-east-1"]
