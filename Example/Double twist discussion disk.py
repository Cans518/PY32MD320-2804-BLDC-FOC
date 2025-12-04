import serial
import time

def send_serial_data(port, baudrate):
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        data_sequence = [
            b'\xAA\x01\xC2\x00\x00\x00',
            b'\xAA\x02\xC2\x00\x00\x00',
            b'\xAA\x01\xC2\x00\x55\x15',
            b'\xAA\x02\xC2\x00\x55\x15',
            b'\xAA\x01\xC2\x00\xAB\x2A',
            b'\xAA\x02\xC2\x00\xAB\x2A'
        ]

        while True:
            for data in data_sequence:
                ser.write(data)
                print(f"Sent: {data.hex().upper()}")
                time.sleep(0.12)

    except serial.SerialException as e:
        print(f"Error: {e}")
    finally:
        ser.close()

if __name__ == "__main__":
    serial_port = 'COM16' 
    baud_rate = 115200

    send_serial_data(serial_port, baud_rate)
