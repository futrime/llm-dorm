import json

from comm import ZmqComm
from schemas import ActuatorCommand

COMM_BROKER_HOST = "10.8.0.5"
COMM_BROKER_BACKEND_PORT = 5556
COMM_BROKER_FRONTEND_PORT = 5555

comm = ZmqComm(
    broker_host=COMM_BROKER_HOST,
    broker_backend_port=COMM_BROKER_BACKEND_PORT,
    broker_frontend_port=COMM_BROKER_FRONTEND_PORT,
)


def main() -> None:
    comm.connect()
    comm.register_receive_callback("actuator", actuator_comm_callback)


def actuator_comm_callback(msg_str: str) -> None:
    msg = json.loads(msg_str)
    if msg["messageId"] != "ActuatorCommand":
        return

    if msg["endpoint"] != "gate":
        return

    print(msg["data"]["command"])


if __name__ == "__main__":
    main()
