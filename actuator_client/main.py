import json

from comm import ZmqComm
from schemas import ActuatorRegistration

from bt_serial import *

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
    bt_serial = bt_serial_connect(1)
    actuator_regist(bt_serial)
    comm.register_receive_callback("actuator", actuator_comm_callback)

def actuator_regist(bt_serial) -> None:    
    time.sleep(0.1)
    temp_storage = ""
    bt_serial_send(bt_serial, 'format?')
    cmd_format, temp_storage = wait_and_receive(bt_serial, temp_storage)
    if cmd_format.strip():
        print(cmd_format)
        if 'gate' in cmd_format:
            actuator_registration = ActuatorRegistration(
                endpoint="gate",
                messageId="ActuatorRegistration",
                actuatorType="Gate",
                actuatorDescription="Gate actuator to open and close the gate.",
                commandFormatDescription=cmd_format,
            )
            comm.send("actuator", str(actuator_registration))
        if 'light' in cmd_format:
            actuator_registration = ActuatorRegistration(
                endpoint="light",
                messageId="ActuatorRegistration",
                actuatorType="Light",
                actuatorDescription="Light actuator to control the light.",
                commandFormatDescription=cmd_format,
            )
            comm.send("actuator", str(actuator_registration))
        if 'aircon' in cmd_format:
            actuator_registration = ActuatorRegistration(
                endpoint="aircon",
                messageId="ActuatorRegistration",
                actuatorType="Airconditioner",
                actuatorDescription="Airconditioner actuator to control the airconditioner.",
                commandFormatDescription=cmd_format,
            )
            comm.send("actuator", str(actuator_registration))

def actuator_comm_callback(msg_str: str) -> None:
    msg = json.loads(msg_str)
    if msg["messageId"] != "ActuatorCommand":
        return

    if msg["endpoint"] != "gate":
        return
    
    command = str(msg["data"]["command"])
    bt_serial_send(bt_serial, command)
    print(wait_and_receive(bt_serial, "")[0])


if __name__ == "__main__":
    main()
