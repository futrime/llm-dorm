from typing import Any, Dict, List, Optional, TypedDict


class InfoDbEntry(TypedDict):
    endpoint: str
    description: str
    data: Any


class InfoDb:
    def __init__(self):
        self._info: Dict[str, InfoDbEntry] = {}

    def insert(self, entry: InfoDbEntry):
        self._info[entry["endpoint"]] = entry

    def get(self) -> List[InfoDbEntry]:
        return list(self._info.values())

    def get_endpoint(self, endpoint: str) -> Optional[InfoDbEntry]:
        return self._info.get(endpoint)
