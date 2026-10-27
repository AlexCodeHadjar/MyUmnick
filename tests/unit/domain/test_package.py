import dataclasses
import inspect
import pkgutil
from importlib import import_module

import pytest

from vtuber import domain


def _exported() -> list[object]:
    return [getattr(domain, name) for name in domain.__all__]


def _domain_dataclasses() -> list[type]:
    return [obj for obj in _exported() if inspect.isclass(obj) and dataclasses.is_dataclass(obj)]


def _public_definitions() -> set[str]:
    names: set[str] = set()
    for module_info in pkgutil.iter_modules(domain.__path__):
        module = import_module(f"{domain.__name__}.{module_info.name}")
        for name, obj in vars(module).items():
            is_own = getattr(obj, "__module__", None) == module.__name__
            if is_own and not name.startswith("_"):
                names.add(name)
    return names


@pytest.mark.parametrize("cls", _domain_dataclasses(), ids=lambda cls: cls.__name__)
def test_domain_dataclass_is_frozen_with_slots(cls: type) -> None:
    assert cls.__dataclass_params__.frozen  # type: ignore[attr-defined]  # нет в typeshed
    assert "__slots__" in vars(cls)


def test_every_public_class_and_function_is_exported() -> None:
    assert _public_definitions() <= set(domain.__all__)
