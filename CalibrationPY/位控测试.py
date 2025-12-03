import tkinter as tk
from tkinter import ttk
import serial
import threading
import time


class MotorControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("电机位置控制器")
        self.root.geometry("400x250")

        # 串口连接
        self.ser = None
        self.port = "COM5"  # 根据实际情况修改
        self.baudrate = 115200
        self.motor_id = 0x01

        self.setup_serial()
        self.create_widgets()

    def setup_serial(self):
        """初始化串口连接"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"串口 {self.port} 连接成功")
        except Exception as e:
            print(f"串口连接失败: {e}")

    def send_command(self, command: bytes):
        """发送命令"""
        if self.ser and self.ser.is_open:
            self.ser.write(command)

    def create_widgets(self):
        """创建界面控件"""
        # 设备ID选择
        id_frame = ttk.Frame(self.root)
        id_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(id_frame, text="设备ID:").pack(side="left", padx=5)

        self.id_var = tk.StringVar(value="1")
        self.id_entry = ttk.Entry(id_frame, textvariable=self.id_var, width=10)
        self.id_entry.pack(side="left", padx=5)

        self.id_button = ttk.Button(id_frame, text="设置ID", command=self.set_motor_id)
        self.id_button.pack(side="left", padx=5)

        # 位置显示
        self.position_var = tk.StringVar(value="位置: 0")
        ttk.Label(self.root, textvariable=self.position_var, font=("Arial", 12)).pack(pady=10)

        # 滑块
        self.slider_var = tk.IntVar(value=0)
        self.slider = ttk.Scale(
            self.root,
            from_=-8191,
            to=8191,
            orient="horizontal",
            variable=self.slider_var,
            command=self.on_slider_change
        )
        self.slider.pack(fill="x", padx=20, pady=10)

        # 按钮框架
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=10)

        # 重新设零按钮
        self.zero_button = ttk.Button(
            button_frame,
            text="重新设零 (C7)",
            command=self.set_zero_position
        )
        self.zero_button.pack(side="left", padx=5)

        # 状态显示
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self.root, textvariable=self.status_var).pack(pady=5)

    def set_motor_id(self):
        """设置电机ID"""
        try:
            new_id = int(self.id_var.get())
            if 0 <= new_id <= 255:
                self.motor_id = new_id
                self.status_var.set(f"ID设置为: {new_id}")
            else:
                self.status_var.set("错误: ID范围0-255")
        except ValueError:
            self.status_var.set("错误: 无效ID")

    def on_slider_change(self, value):
        """滑块改变时发送C2命令"""
        position = int(float(value))
        self.position_var.set(f"位置: {position}")
        self.send_c2_command(position)

    def send_c2_command(self, position):
        """发送C2位置命令"""
        # 处理位置值
        position = max(-8191, min(8191, position))

        # 16位有符号转无符号
        if position < 0:
            position_bytes = position + 0x10000
        else:
            position_bytes = position

        low_byte = position_bytes & 0xFF
        high_byte = (position_bytes >> 8) & 0xFF

        # C2命令: AA [ID] C2 00 [位置低8位] [位置高8位]
        command = bytes([0xAA, self.motor_id, 0xC2, 0x00, low_byte, high_byte])

        # 在新线程中发送命令
        threading.Thread(target=self._send_command, args=(command,), daemon=True).start()

        self.status_var.set(f"位置: {position}")

    def set_zero_position(self):
        """发送C7重新设零命令"""
        # C7命令: AA [ID] C7 00 00 00
        command = bytes([0xAA, self.motor_id, 0xC7, 0x00, 0x00, 0x00])

        threading.Thread(target=self._send_command, args=(command,), daemon=True).start()

        # 重置滑块到0
        self.slider_var.set(0)
        self.position_var.set("位置: 0")

        self.status_var.set("重新设零")

    def _send_command(self, command):
        """在新线程中发送命令"""
        try:
            self.send_command(command)
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"发送失败: {e}"))

    def on_closing(self):
        """关闭窗口时的清理工作"""
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MotorControlGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()