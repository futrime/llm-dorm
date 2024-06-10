from typing import Any, TypedDict


class InfoDbEntry(TypedDict):
    endpoint: str
    sensorDescription: str
    data: Any


class InfoDb:
    def __init__(self):
        self._info = []

    def insert(self, entry: InfoDbEntry):
        # Remove entry with the same endpoint
        self._info = [e for e in self._info if e["endpoint"] != entry["endpoint"]]

        self._info.append(entry)

    def get(self):
        return self._info
