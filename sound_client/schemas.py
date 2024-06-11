from typing import Any, TypedDict


class ActuatorCommand(TypedDict):
    endpoint: str
    messageId: str
    data: Any


class ActuatorRegistration(TypedDict):
    endpoint: str
    messageId: str
    actuatorType: str
    actuatorDescription: str
    commandFormatDescription: str


class SensorReport(TypedDict):
    endpoint: str
    messageId: str
    sensorType: str
    sensorDescription: str
    data: Any
