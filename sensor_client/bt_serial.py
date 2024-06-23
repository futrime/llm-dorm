import json
import time
import serial
import serial.tools.list_ports

# Function to connect to Bluetooth serial device
def bt_serial_connect(device_number, baudrate=115200) -> serial.Serial:
    bt_serial = serial.Serial('/dev/rfcomm' + str(device_number), baudrate)
    if not bt_serial.is_open:
        bt_serial.open()
    bt_serial.flush()
    return bt_serial

# Function to wait and receive complete data from Bluetooth serial device
def wait_and_receive(bt_serial, temp_storage="") -> tuple:
    while True:
        cnt = bt_serial.in_waiting
        if cnt != 0:
            recv = bt_serial.read(cnt).decode()
            bt_serial.flush()
            temp_storage += recv

            # Check for complete messages
            if '\n' in temp_storage:
                messages = temp_storage.split('\n')
                # Get the first complete message
                complete_message = messages.pop(0)
                # Remainder (incomplete or next messages)
                temp_storage = '\n'.join(messages)
                return complete_message, temp_storage

        time.sleep(0.05)

# Function to send data to Bluetooth serial device
def bt_serial_send(bt_serial, data) -> None:
    bt_serial.write(data.encode())

# Function to parse the message and convert to JSON format
def parse_message(message, timestamp) -> str:
    # Extract the values from the message
    parts = message[1:-1].split(',')
    data = {}
    for part in parts:
        key, value = part.split(':')
        key = key.strip()
        value = value.strip()
        if key == "T":
            data["Temperature"] = value
        elif key == "H":
            data["Humidity"] = value
        elif key == "L":
            data["LightStrength"] = value
        elif key == "M":
            data["ManExists"] = value
        elif key == "I":
            data["Illumination"] = 'ON' if value == "1" else 'OFF'
        elif key == "P":
            data["Pressure"] = value

    # Add the timestamp
    data["Timestamp"] = timestamp

    # Convert to JSON
    return json.dumps(data)


if __name__ == "__main__":
    bt_serial = bt_serial_connect(1, 115200)
    temp_storage = ""  # Temporary storage for incomplete messages
    time.sleep(0.1)
    bt_serial_send(bt_serial, '075 010')
    complete_message, temp_storage = wait_and_receive(bt_serial, temp_storage)
    print(complete_message)
    while True:
        complete_message, temp_storage = wait_and_receive(
            bt_serial, temp_storage)
        if complete_message.strip():  # Check if the message is not empty
            print(parse_message(
                timestamp=time.asctime(), message=complete_message))
