from typing import Protocol


class CachePort(Protocol):
    async def delete_keys(self, *keys: str) -> None: ...

    async def delete_prefix(self, prefix: str) -> None: ...
