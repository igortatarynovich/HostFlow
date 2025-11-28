
from __future__ import annotations

from typing import Final, cast

# Временные (мутабельные) значения по умолчанию. Их будем переопределять,
# а финальные экспортируемые имена присвоим один раз в конце.
_DEFAULT_STAGE_CODE_TMP: str = "new"
_STAGES_TMP: list[str] = []
_STAGES_ORDER_TMP: list[str] = []
_PIPELINE_SEQUENCE_TMP: list[str] = []

# 1) Пытаемся импортировать модуль и брать атрибуты через getattr —
#    так мы избегаем ошибок статического анализатора (Pylance),
#    который ругается на неизвестные символы при `from x import NAME`.
try:
    from . import stages as _stages_mod  # type: ignore

    _DEFAULT_STAGE_CODE_TMP = cast(str, getattr(_stages_mod, "DEFAULT_STAGE_CODE", _DEFAULT_STAGE_CODE_TMP))
    _STAGES_TMP = cast(list[str], getattr(_stages_mod, "STAGES", _STAGES_TMP))
    _STAGES_ORDER_TMP = cast(list[str], getattr(_stages_mod, "STAGES_ORDER", _STAGES_ORDER_TMP))
    _PIPELINE_SEQUENCE_TMP = cast(list[str], getattr(_stages_mod, "PIPELINE_SEQUENCE", _PIPELINE_SEQUENCE_TMP))
except ImportError:
    # 2) Бэкап-импорт из старого расположения
    try:
        from backend.app.constants import stages as _stages_mod2  # type: ignore

        _DEFAULT_STAGE_CODE_TMP = cast(str, getattr(_stages_mod2, "DEFAULT_STAGE_CODE", _DEFAULT_STAGE_CODE_TMP))
        _STAGES_TMP = cast(list[str], getattr(_stages_mod2, "STAGES", _STAGES_TMP))
        _STAGES_ORDER_TMP = cast(list[str], getattr(_stages_mod2, "STAGES_ORDER", _STAGES_ORDER_TMP))
        _PIPELINE_SEQUENCE_TMP = cast(list[str], getattr(_stages_mod2, "PIPELINE_SEQUENCE", _PIPELINE_SEQUENCE_TMP))
    except ImportError:
        # остаёмся на дефолтах
        pass

# --- Экспортируемые имена ---
# Присваиваем их ОДИН РАЗ, чтобы не нарушать контракт Final и избавиться от предупреждений Pylance.
DEFAULT_STAGE_CODE: Final[str] = _DEFAULT_STAGE_CODE_TMP
STAGES: list[str] = _STAGES_TMP
STAGES_ORDER: list[str] = _STAGES_ORDER_TMP
PIPELINE_SEQUENCE: list[str] = _PIPELINE_SEQUENCE_TMP

# Совместимость со старым кодом, где ожидались имена с подчёрками
_DEFAULT_STAGE_CODE = DEFAULT_STAGE_CODE
_STAGES = STAGES
_STAGES_ORDER = STAGES_ORDER
_PIPELINE_SEQUENCE = PIPELINE_SEQUENCE

__all__ = [
    "DEFAULT_STAGE_CODE",
    "STAGES",
    "STAGES_ORDER",
    "PIPELINE_SEQUENCE",
    "_DEFAULT_STAGE_CODE",
    "_STAGES",
    "_STAGES_ORDER",
    "_PIPELINE_SEQUENCE",
]
