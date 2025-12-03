import time
import serial
import struct
from typing import List, Tuple


class MotorController:
    def __init__(self, port: str, baudrate: int = 115200):
        """
        初始化电机控制器
        """
        self.ser = serial.Serial(port, baudrate, timeout=1)
        self.current_zero_position = 0  # 当前0电角度位置
        self.motor_id = 0x01  # 默认电机ID

    def set_motor_id(self, new_id: int):
        """
        设置电机ID并更新后续命令
        """
        if new_id < 0 or new_id > 255:
            raise ValueError("电机ID必须在0-255范围内")
        self.motor_id = new_id
        print(f"电机ID设置为: 0x{new_id:02X}")

    def send_command(self, command: bytes) -> bytes:
        """
        发送命令并接收响应
        命令格式: AA 01 命令位 00 参数低8位 参数高8位
        """
        self.ser.write(command)
        time.sleep(0.01)
        return self.ser.read_all()

    def set_coarse_zero_position(self):
        """
        使用0B命令拉高IA，得到粗0位
        命令: AA [ID] 0B 00 00 00
        """
        command = bytes([0xAA, self.motor_id, 0x0B, 0x00, 0x00, 0x00])
        response = self.send_command(command)
        time.sleep(1)
        _, _, position = self.read_position_data()
        self.set_zero_position(position)
        self.stop_motor()
        print("设置粗0位完成")
        return response

    def read_position_data(self) -> Tuple[int, int, int]:
        """
        读取位置、速度、电流数据
        命令: AA [ID] 00 07 00 00
        返回: (位置, 速度, 电流)
        """
        command = bytes([0xAA, self.motor_id, 0x08, 0x07, 0x00, 0x00])
        response = self.send_command(command)

        if len(response) >= 7:
            # 解析7字节数据: AB + uint16位置 + int16速度 + uint16电流
            # 响应格式: AB [位置低8位] [位置高8位] [速度低8位] [速度高8位] [电流低8位] [电流高8位]
            position = struct.unpack('<H', response[1:3])[0]  # uint16 小端
            position = 0x3fff - position
            speed = struct.unpack('<h', response[3:5])[0]  # int16 小端
            current = struct.unpack('<H', response[5:7])[0]  # uint16 小端
            return position, speed, current
        else:
            print(f"读取数据失败，响应长度: {len(response)}")
            return 0, 0, 0

    def set_zero_position(self, zero_pos: int):
        """
        使用F1命令设定0电角度位置
        命令: AA [ID] F1 00 [位置低8位] [位置高8位]
        """
        self.current_zero_position = zero_pos
        low_byte = zero_pos & 0xFF
        high_byte = (zero_pos >> 8) & 0xFF
        command = bytes([0xAA, self.motor_id, 0xF1, 0x00, low_byte, high_byte])
        response = self.send_command(command)
        print(f"设置0电角度位置: {zero_pos} (0x{zero_pos:04X})")
        return response

    def clear_motor_status(self):
        """
        C1命令清除电机状态
        命令: AA [ID] C1 00 00 00
        """
        command = bytes([0xAA, self.motor_id, 0xC0, 0x00, 0x00, 0x00])
        response = self.send_command(command)
        print("清除电机状态完成")
        return response

    def set_motor_speed(self, speed: int):
        """
        C0命令控制电机转速
        命令: AA [ID] C0 00 [速度低8位] [速度高8位]
        """
        # 处理负数速度（16位有符号转无符号）
        if speed < 0:
            speed = 0x10000 + speed  # 补码表示

        low_byte = speed & 0xFF
        high_byte = (speed >> 8) & 0xFF

        command = bytes([0xAA, self.motor_id, 0xC0, 0x00, low_byte, high_byte])
        response = self.send_command(command)

        # 显示实际设置的速度值（有符号）
        actual_speed = speed if speed < 0x8000 else speed - 0x10000
        print(f"设置电机转速: {actual_speed}")
        return response

    def stop_motor(self):
        """
        C0命令停止电机
        命令: AA [ID] C0 00 00 00
        """
        command = bytes([0xAA, self.motor_id, 0xC0, 0x00, 0x00, 0x00])
        response = self.send_command(command)
        print("停止电机")
        return response

    def save_conf(self):
        """
        B0命令保存配置
        命令: AA [ID] B0 00 00 00
        """
        command = bytes([0xAA, self.motor_id, 0xB0, 0x00, 0x00, 0x00])
        response = self.send_command(command)
        print("正在保存设置")
        return response

    def set_new_motor_id(self, new_id: int):
        """
        F0命令设置新电机ID
        命令: AA [当前ID] F0 00 [新ID] 00
        """
        if new_id < 0 or new_id > 255:
            raise ValueError("电机ID必须在0-255范围内")

        command = bytes([0xAA, self.motor_id, 0xF0, 0x00, new_id, 0x00])
        response = self.send_command(command)
        print(f"新电机ID 0x{new_id:02X} 已设置")
        return response

    def set_negative_limit(self, limit: int):
        """
        C8命令设置负限位
        命令: AA [ID] C8 00 [限位低8位] [限位高8位]
        """
        # 将int16转换为无符号字节
        if limit < 0:
            limit_bytes = limit + 0x10000
        else:
            limit_bytes = limit

        low_byte = limit_bytes & 0xFF
        high_byte = (limit_bytes >> 8) & 0xFF

        command = bytes([0xAA, self.motor_id, 0xC8, 0x00, low_byte, high_byte])
        response = self.send_command(command)
        print(f"设置负限位: {limit}")
        return response

    def set_positive_limit(self, limit: int):
        """
        C9命令设置正限位
        命令: AA [ID] C9 00 [限位低8位] [限位高8位]
        """
        # 将int16转换为无符号字节
        if limit < 0:
            limit_bytes = limit + 0x10000
        else:
            limit_bytes = limit

        low_byte = limit_bytes & 0xFF
        high_byte = (limit_bytes >> 8) & 0xFF

        command = bytes([0xAA, self.motor_id, 0xC9, 0x00, low_byte, high_byte])
        response = self.send_command(command)
        print(f"设置正限位: {limit}")
        return response

    def measure_average_speed(self, duration: float = 8.0, frequency: float = 50.0) -> float:
        """
        以指定频率读取电流数据并计算平均值
        """
        interval = 1.0 / frequency
        total_readings = int(duration * frequency)
        speeds = []

        print(f"开始采集电流数据，持续时间: {duration}秒，频率: {frequency}Hz")

        start_time = time.time()
        for i in range(total_readings):
            _, speed, current = self.read_position_data()
            speeds.append(speed)

            # 计算下一次读取的时间
            elapsed = time.time() - start_time
            next_read_time = (i + 1) * interval
            sleep_time = next_read_time - elapsed

            if sleep_time > 0:
                time.sleep(sleep_time)

        average_speed = sum(speeds) / len(speeds)
        print(f"平均速度: {average_speed:.2f}, 采样点数: {len(speeds)}")
        return average_speed

    def find_zero_electrical_angle(self, initial_zero_pos: int = 0, max_iterations: int = 100) -> int:
        """
        自动寻找0电角度位置
        """
        print("开始自动寻找0电角度位置...")


        for iteration in range(max_iterations):
            print(f"\n--- 第 {iteration + 1} 次迭代 ---")
            print(f"当前0电角度位置: {self.current_zero_position}")

            # 清除电机状态
            self.stop_motor()
            time.sleep(0.1)

            # 正转测试
            print("正转测试...")
            self.set_motor_speed(25000)
            time.sleep(1)  # 等待电机稳定
            forward_speed = self.measure_average_speed(1.0, 100.0)
            self.stop_motor()
            time.sleep(1)  # 等待电机停止

            # 反转测试
            print("反转测试...")
            self.set_motor_speed(-25000)
            time.sleep(1)  # 等待电机稳定
            reverse_speed = self.measure_average_speed(1.0, 100.0)
            self.stop_motor()
            time.sleep(1)  # 等待电机停止

            # 计算电流差值
            current_difference = abs(forward_speed) - abs(reverse_speed)
            print(f"正转速度: {forward_speed:.2f}, 反转速度: {reverse_speed:.2f}, 差值: {current_difference:.2f}")

            # 判断是否满足条件
            if abs(current_difference) <= 2:
                print(f"\n找到0电角度位置: {self.current_zero_position}")
                print(f"最终速度差值: {current_difference:.2f}")
                return self.current_zero_position

            delta = 2
            # 调整0电角度位置
            if abs(current_difference) > 50:
                delta = 20
            elif abs(current_difference) > 30:
                delta = 15
            elif abs(current_difference) > 25:
                delta = 10
            elif abs(current_difference) > 15:
                delta = 5
            if current_difference > 0:
                # 正转电流大，0电角度位置+10
                self.current_zero_position -= delta
                print("正转速度较大，0电角度位置+10")
            else:
                # 反转电流大，0电角度位置-10
                self.current_zero_position += delta
                print("反转速度较大，0电角度位置-10")

            # 设置新的0电角度位置
            self.set_zero_position(self.current_zero_position)
            time.sleep(0.1)

        print(f"达到最大迭代次数 {max_iterations}，未找到精确的0电角度位置")
        return self.current_zero_position

    def close(self):
        """
        关闭串口连接
        """
        self.ser.close()


def main():
    # 使用示例
    # 请根据实际情况修改串口号
    port = "COM10"  # Windows
    # port = "/dev/ttyUSB0"  # Linux
    # port = "/dev/tty.usbserial"  # macOS

    try:
        # 第一步：获取初始电机ID
        print("=== 电机标定程序 ===")
        initial_id_input = input("请输入当前电机ID (0-255, 十六进制可加0x前缀): ").strip()
        if initial_id_input.startswith('0x') or initial_id_input.startswith('0X'):
            initial_id = int(initial_id_input, 16)
        else:
            initial_id = int(initial_id_input)

        if initial_id < 0 or initial_id > 255:
            print("电机ID必须在0-255范围内")
            return

        # 初始化电机控制器
        motor = MotorController(port)
        motor.set_motor_id(initial_id)
        print(f"已连接电机，当前ID: 0x{initial_id:02X}")

        # 第二步：设置粗0位
        print("\n第二步：设置粗0位")
        motor.send_command(bytes([0xAA, motor.motor_id, 0xF2, 0x00, 0x00, 0x00]))
        motor.set_coarse_zero_position()
        motor.set_motor_speed(10000)
        time.sleep(1)
        speed = motor.measure_average_speed(2.0, 35.0);
        motor.stop_motor()
        # 读取当前位置
        position, speed, current = motor.read_position_data()
        print(f"当前位置: {position}, 速度: {speed}, 电流: {current}")
        time.sleep(2)
        # 第三步：自动寻找0电角度
        print("\n第三步：自动寻找0电角度")
        final_zero_pos = motor.find_zero_electrical_angle(initial_zero_pos=position)

        print(f"\n最终0电角度位置: {final_zero_pos}")

        # 验证最终结果
        print("\n验证最终结果...")
        motor.clear_motor_status()

        # 正转测试
        motor.set_motor_speed(25000)
        time.sleep(2)
        forward_current = motor.measure_average_speed(2.0, 30.0)
        motor.stop_motor()
        time.sleep(2)

        # 反转测试
        motor.set_motor_speed(-25000)
        time.sleep(2)
        reverse_current = motor.measure_average_speed(2.0, 30.0)
        motor.stop_motor()

        final_difference = abs(forward_current) - abs(reverse_current)
        print(
            f"最终验证 - 正转: {forward_current:.2f}, 反转: {reverse_current:.2f}, 差值: {final_difference:.2f}")

        if abs(final_difference) <= 10:
            print("✓ 0电角度设定成功！")
        else:
            print("⚠ 0电角度设定可能不够精确")

        # 第四步：标定后配置
        print("\n=== 标定后配置 ===")

        # 设置新ID
        new_id_input = input("请输入新的电机ID (0-255, 十六进制可加0x前缀): ").strip()
        if new_id_input.startswith('0x') or new_id_input.startswith('0X'):
            new_id = int(new_id_input, 16)
        else:
            new_id = int(new_id_input)

        if new_id < 0 or new_id > 255:
            print("电机ID必须在0-255范围内")
            return

        motor.set_new_motor_id(new_id)
        motor.set_motor_id(new_id)  # 更新后续命令使用的ID

        # 设置负限位
        negative_limit_input = input("请输入负限位值 (-32768 到 32767): ").strip()
        negative_limit = int(negative_limit_input)
        motor.set_negative_limit(negative_limit)

        # 设置正限位
        positive_limit_input = input("请输入正限位值 (-32768 到 32767): ").strip()
        positive_limit = int(positive_limit_input)
        motor.set_positive_limit(positive_limit)

        # 保存所有配置
        print("\n保存所有配置...")
        motor.save_conf()

        print("\n✓ 标定和配置完成！")
        print(f"电机ID: 0x{new_id:02X}")
        print(f"负限位: {negative_limit}")
        print(f"正限位: {positive_limit}")
        print(f"0电角度位置: {final_zero_pos}")

    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        if 'motor' in locals():
            motor.close()


if __name__ == "__main__":
    main()