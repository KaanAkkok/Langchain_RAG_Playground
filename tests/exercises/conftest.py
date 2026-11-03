"""Ortak pytest ayarları: ``async def`` testleri ek eklenti olmadan çalıştırır."""

from __future__ import annotations

import asyncio
import inspect

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    if not inspect.iscoroutinefunction(pyfuncitem.obj):
        return None
    names = pyfuncitem._fixtureinfo.argnames
    kwargs = {name: pyfuncitem.funcargs[name] for name in names}
    asyncio.run(pyfuncitem.obj(**kwargs))
    return True
