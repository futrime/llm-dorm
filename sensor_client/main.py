import json

from comm import ZmqComm
from schemas import SensorReport

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
    while True:
        complete_message, temp_storage = wait_and_receive(
            bt_serial, temp_storage)
        if complete_message.strip():  # Check if the message is not empty
            print(parse_message(
                timestamp=time.asctime(), message=complete_message))
            sensor_report = SensorReport(
                endpoint="sensor_client",
                messageId="1",
                sensorType="Environment",
                sensorDescription="Environment data of temperature, humidity, light, human presence, illumination, and pressure.",
                data=parse_message(
                    timestamp=time.asctime(), message=complete_message),
            )
            comm.send("sensor", str(sensor_report))

if __name__ == "__main__":
    main()
