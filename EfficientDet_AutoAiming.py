# Created @202602
import math
import time
import threading
import cv2
import tensorflow as tf
import win32api
import win32con
from mss import mss
import numpy as np
from ctypes import windll
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import csv
import os

Val_DetectConf = 30
Val_ScreenRatio = 15
Val_LockRatio = 50
Val_MoveFactor = 300
Val_Suspension = 25

keypoints_1 = None
keypoints_2 = None
keypoints_3 = None
keypoints_4 = None
keypoints_5 = None

threshold_value = 0.3

frame_to_display = None
input_frame = None

# Make program aware of DPI scaling
user32 = windll.user32
user32.SetProcessDPIAware()

# Get Screen Resolution
x_screen = win32api.GetSystemMetrics(0)
y_screen = win32api.GetSystemMetrics(1)
xy_ration = x_screen/y_screen

x_target = 0
y_target = 0
aim_target = "Head"
MoveFactor_move = 300
Suspension_val = 25

x_ratio = 0.15
lock_ratio = 0.50
mon1 = None

# model_path = "thunder-uint8.tflite"
# model_path = "lightning-uint8.tflite"
# model_path = "lightning-float16.tflite"
# model_path = "lightning-float32.tflite"

# model_path = "ssd_mobilenet_v1.tflite"

model_path = "efficientdet_lite0.tflite"
# model_path = "efficientdet_lite1.tflite"

# model_path = "efficientnet-tflite-lite4-uint8-v1.tflite"
# Load MoveNet model
interpreter = tf.lite.Interpreter(model_path=model_path, num_threads=4)


# interpreter = Interpreter(model_path=model_path, num_threads=4)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

FPS_array_detect = []
FPS_array_img = []

is_program_closed = False
is_img_closed = True
is_key_changed = False

input_size = input_details[0]['shape'][1:3]

aim_key_code = 0x05
aim_key_name = "X2 mouse button"
KEY_NAMES = {
    # Mouse Buttons
    0x01: "Left Mouse Button",
    0x02: "Right Mouse Button",
    0x04: "Middle Mouse Button",
    0x05: "X1 mouse button",
    0x06: "X2 mouse button",

    # Control Keys
    0x08: "Backspace",
    0x09: "Tab",
    0x0C: "Clear",
    0x0D: "Enter",
    0x10: "Shift",
    0x11: "Ctrl",
    0x12: "Alt",
    0x14: "Caps Lock",
    0x1B: "Esc",
    0x20: "Space",
    0x21: "Page up",
    0x22: "Page dow",
    0x23: "End",
    0x24: "Home",
    0x2A: "Print",
    0x2B: "Execute",
    0x2C: "Print Screen",
    0x2D: "Insert key",
    0x2E: "Delete",
    0x2F: "Help",

    # Arrows and Navigation
    0x25: "Left Arrow",
    0x26: "Up Arrow",
    0x27: "Right Arrow",
    0x28: "Down Arrow",

    0x29: "Select key",

    # Function Keys
    0x70: "F1", 0x71: "F2", 0x72: "F3", 0x73: "F4", 0x74: "F5",
    0x75: "F6", 0x76: "F7", 0x77: "F8", 0x78: "F9", 0x79: "F10",
    0x7A: "F11", 0x7B: "F12",

    # Numbers (Top Row)
    0x30: "0", 0x31: "1", 0x32: "2", 0x33: "3", 0x34: "4", 0x35: "5",
    0x36: "6", 0x37: "7", 0x38: "8", 0x39: "9", 0xBD: "-_", 0xBB: "=+", 0xDB: "[{", 0xDD: "]}", 0xDC: "\|",
    0xC0: "`~", 0xBA: ";:", 0xDE: """ ' " """, 0xBC: ",<", 0xBE: ".>", 0xBF:"/?",

    # Letters
    0x41: "A", 0x42: "B", 0x43: "C", 0x44: "D", 0x45: "E", 0x46: "F",
    0x47: "G", 0x48: "H", 0x49: "I", 0x4A: "J", 0x4B: "K", 0x4C: "L",
    0x4D: "M", 0x4E: "N", 0x4F: "O", 0x50: "P", 0x51: "Q", 0x52: "R",
    0x53: "S", 0x54: "T", 0x55: "U", 0x56: "V", 0x57: "W", 0x58: "X",
    0x59: "Y", 0x5A: "Z",

    # Numpad Keys
    0x60: "Numpad 0", 0x61: "Numpad 1", 0x62: "Numpad 2", 0x63: "Numpad 3",
    0x64: "Numpad 4", 0x65: "Numpad 5", 0x66: "Numpad 6", 0x67: "Numpad 7",
    0x68: "Numpad 8", 0x69: "Numpad 9",
    0x6A: "Numpad *", 0x6B: "Numpad +", 0x6D: "Numpad -", 0x6E: "Numpad .",
    0x6F: "Numpad /",

    # Special Keys
    0x5B: "Left Windows Key",
    0x5C: "Right Windows Key",
    0x5D: "Applications Key",
}

is_COM_Found = False
ser = None
Name_COM = ""

ports = serial.tools.list_ports.comports()
port_list = []
is_serial_open = False
input_method = "Virtual"

if os.path.exists('ParaSetting.csv'):
    try:
        csvfile = open('ParaSetting.csv')
        val_data = csvfile.readlines()
        val_data = [line.strip().split(",") for line in val_data]
        Val_DetectConf = int(val_data[1][0])
        Val_ScreenRatio = int(val_data[1][1])
        Val_LockRatio = int(val_data[1][2])
        Val_MoveFactor = int(val_data[1][3])
        Val_Suspension = int(val_data[1][4])
        aim_key_code = int(val_data[1][5])
        is_key_changed = True
    except (FileNotFoundError, IndexError, ValueError) as e:
        print(f"Error reading parameters: {e}")

else:
    data = [
        ['DetectConf', 'ScreenRatio', 'LockRatio', 'MoveFactor'],
        [30, 15, 50, 300]
    ]
    csvfile = open('ParaSetting.csv', mode='w', newline='')
    writer = csv.writer(csvfile)
    writer.writerows(data)
    csvfile.close()

def find_the_com():
    global port_list, ports
    port_list = []
    ports = serial.tools.list_ports.comports()
    for port in ports:
        port_list.append(port.description)
    print(port_list)


def connect_to_port():
    global ser, is_serial_open
    if ser is not None:
        if ser.is_open:
            is_serial_open = True
            ser.close()
            time.sleep(1)
        else:
            is_serial_open = False
    for port in ports:
        if port.description == Name_COM:
            print(port.device)
            try:
                ser = serial.Serial(port=port.name, baudrate=115200, timeout=1)
                print("Connected to", ser.name)  # Prints the port name
                is_serial_open = True
            except serial.SerialException as e:
                is_serial_open = False
                find_the_com()
                print("Error:", e)
            break


def preprocess_frame(frame):
    # resized = cv2.resize(frame, tuple(input_size), interpolation=cv2.INTER_NEAREST)
    resized = cv2.resize(frame, tuple(input_size), interpolation=cv2.INTER_AREA)
    resized_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    if model_path == "lightning-float32.tflite":
        return np.expand_dims(resized_rgb.astype(np.float32), axis=0)
    elif model_path == "lightning-uint8.tflite":
        return np.expand_dims(resized_rgb.astype(np.uint8), axis=0)
    elif model_path == "lightning-float16.tflite":
        return np.expand_dims(resized_rgb.astype(np.uint8), axis=0)
    elif model_path == "thunder-uint8.tflite":
        return np.expand_dims(resized_rgb.astype(np.uint8), axis=0)
    elif model_path == "efficientdet_lite0.tflite":
        return np.expand_dims(resized_rgb.astype(np.uint8), axis=0)
    elif model_path == "efficientdet_lite1.tflite":
        return np.expand_dims(resized_rgb.astype(np.uint8), axis=0)
    # elif model_path == "ssd_mobilenet_v1.tflite":
    #     return np.expand_dims(resized_rgb.astype(np.uint8), axis=0)
    else:
        return np.expand_dims(resized_rgb.astype(np.uint8), axis=0)
    return None


def detect_image(frame):
    input_data = preprocess_frame(frame)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    # print("Detect invoke")
    detections = interpreter.get_tensor(output_details[0]['index'])
    boxes = interpreter.get_tensor(output_details[0]['index'])[0]  # Bounding boxes
    classes = interpreter.get_tensor(output_details[1]['index'])[0]  # Class IDs
    scores = interpreter.get_tensor(output_details[2]['index'])[0]  # Confidence
    return boxes, classes, scores



def func_image_input():
    global input_frame, FPS_array_img, x_ratio, mon1
    sct = mss()
    # Set Window Size
    x_ratio = 0.15
    x_window = int(x_screen * x_ratio)
    y_window = int(y_screen * (x_ratio * xy_ration))
    d_left = int(x_screen / 2 - x_window / 2)
    d_top = int(y_screen / 2 - y_window / 2)
    mon1 = {'left': d_left, 'top': d_top, 'width': x_window, 'height': y_window}

    tic = time.time()

    while not is_program_closed:
        screenShot = sct.grab(mon1)
        numpy_image = np.array(screenShot)
        input_frame = numpy_image[:, :, 0:3]

        toc = time.time()
        delta_t = toc - tic
        tic = toc
        if delta_t:
            FPS = 1 / delta_t
            FPS_array_img.append(FPS)
            if len(FPS_array_img) > 20:
                FPS_array_img.pop(0)

def func_detect():
    global frame_to_display, x_target, y_target, FPS_array_detect, ser
    tic = time.time()
    while not is_program_closed:
        if input_frame is not None:
            boxes, classes, scores = detect_image(input_frame)
            frame_to_display = input_frame.copy()
            h, w, _ = frame_to_display.shape
            x_center_nearest = 0
            y_center_nearest = 0
            distance_center = 0.5 * math.sqrt(2)

            for i in range(len(scores)):
                if scores[i] > threshold_value and int(classes[i]) == 0:
                    y_min, x_min, y_max, x_max = boxes[i]
                    x_center = (x_min + x_max) / 2 - 0.5
                    y_center = (y_min + y_max) / 2 - 0.5
                    distance_center_temp = math.sqrt(x_center**2 + y_center**2)
                    if distance_center_temp < distance_center:
                        distance_center = distance_center_temp
                        x_center_nearest = x_center
                        y_center_nearest = y_center

                    if not is_img_closed:
                        start = (int(x_min * w), int(y_min * h))
                        end = (int(x_max * w), int(y_max * h))
                        frame_to_display = cv2.rectangle(frame_to_display, start, end, (0, 255, 0), 2)

                        label = f"Person {scores[i]:.2f}"
                        frame_to_display = cv2.putText(frame_to_display, label, start,
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            x_target = x_center_nearest
            y_target = y_center_nearest

            if aim_key_code is not None:
                if win32api.GetKeyState(aim_key_code) < 0 and abs(x_target) < lock_ratio and abs(y_target) < lock_ratio:
                    if input_method == "Virtual":

                        delta_x = x_target * MoveFactor_move
                        delta_y = y_target * MoveFactor_move
                        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE,
                                             round(delta_x),
                                             round(delta_y),
                                             0, 0)
                        if abs(x_target)!=0 and abs(y_target)!=0:
                            if win32api.GetKeyState(0x01) < 0:
                                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE,
                                                     0, Suspension_val, 0, 0)

                    if input_method == "COM Port":
                        if ser is not None:
                            if ser.is_open:
                                if round(x_target * MoveFactor_move) >= 127:
                                    x_move_com = 127
                                elif round(x_target * MoveFactor_move) <= -127:
                                    x_move_com = -127
                                else:
                                    x_move_com = round(x_target * MoveFactor_move)

                                if round(y_target * MoveFactor_move) >= 127:
                                    y_move_com = 127
                                elif round(y_target * MoveFactor_move) <= -127:
                                    y_move_com = -127
                                else:
                                    y_move_com = round(y_target * MoveFactor_move)

                                if abs(x_target) != 0 and abs(y_target) != 0:
                                    if win32api.GetKeyState(0x01) < 0:
                                        y_move_com = y_move_com + int(Suspension_val/10)

                                string_to_send = "(" + str(x_move_com) + "," + str(y_move_com) + ")"
                                try:
                                    ser.write(string_to_send.encode('utf-8'))  # Encoding the string to bytes
                                except serial.serialutil.SerialTimeoutException:
                                    ser.close()
                                    find_the_com()
                                    print("Write operation timed out. Retrying...")


            toc = time.time()
            delta_t = toc - tic
            tic = toc
            if delta_t:
                FPS = 1 / delta_t
                FPS_array_detect.append(FPS)
                if len(FPS_array_detect) > 20:
                    FPS_array_detect.pop(0)
                # print("Detect FPS", round(FPS))
        else:
            time.sleep(0.001)


def func_gui():
    global threshold_value, x_ratio, lock_ratio, mon1, aim_target, MoveFactor_move, is_key_changed, aim_key_name, port_list, Suspension_val
    global input_method, Name_COM, is_serial_open
    global Val_DetectConf, Val_MoveFactor, Val_ScreenRatio, Val_LockRatio, Val_Suspension
    root = tk.Tk()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    gui_size_str = "800x600"
    root.geometry(gui_size_str)
    root.resizable(height=True, width=True)
    root.attributes('-topmost', True)
    root.title("AutoAiming_EfficientDet")

    x1 = 0
    y1 = 10

    x2 = x1 + 350
    y2 = y1 - 10

    x3 = 0
    y3 = y2 + 70

    x4 = x3 + 350
    y4 = y3 - 10

    x5 = 0
    y5 = y4 + 70

    x6 = x5 + 350
    y6 = y5 - 10

    x7 = 0
    y7 = y6 + 70

    x8 = x7 + 350
    y8 = y7 - 10

    x7_1 = 0
    y7_1 = y8 + 70

    x8_1 = x7_1 + 350
    y8_1 = y7_1 - 10

    x9 = 0
    y9 = y8_1 #+ 70

    x10 = x9 + 350
    y10 = y9

    x11 = 0
    y11 = y10 + 60

    x12 = x11 + 210
    y12 = y11

    x13 = x11 + 500
    y13 = y11

    x14 = 0
    y14 = y13 + 50

    x15 = x14 + 200
    y15 = y14

    x16 = 0
    y16 = y15 + 50

    x17 = x16 + 150
    y17 = y16

    x18 = x17 + 470
    y18 = y17

    x19 = x18 + 100
    y19 = y17 - 5

    x20 = 0
    y20 = y19 + 55

    x21 = 0
    y21 = y20 + 80

    label_detect_conf = tk.Label(root, text="Detection Confidence (%): ", font=("Arial", 15))
    label_detect_conf.place(x=x1, y=y1)

    slider_detect_conf = tk.Scale(root, from_=1, to=100, orient='horizontal', length=400, showvalue=True)
    slider_detect_conf.place(x=x2, y=y2)
    slider_detect_conf.set(Val_DetectConf)

    label_x_ratio = tk.Label(root, text="Image Capture Ratio (%): ", font=("Arial", 15))
    label_x_ratio.place(x=x3, y=y3)

    slider_x_ratio = tk.Scale(root, from_=1, to=100, orient='horizontal', length=400,showvalue=True)
    slider_x_ratio.set(Val_ScreenRatio)
    slider_x_ratio.place(x=x4, y=y4)

    label_ratio_lock = tk.Label(root, text="Auto Aim Ratio (%): ", font=("Arial", 15))
    label_ratio_lock.place(x=x5, y=y5)

    slider_ratio_lock = tk.Scale(root, from_=1, to=100, orient='horizontal', length=400, showvalue=True)
    slider_ratio_lock.set(Val_LockRatio)
    slider_ratio_lock.place(x=x6, y=y6)

    label_move_factor = tk.Label(root, text="Aiming Move Factor: ", font=("Arial", 15))
    label_move_factor.place(x=x7, y=y7)

    slider_move_factor = tk.Scale(root, from_=0, to=1000, orient='horizontal', length=400, showvalue=True, resolution=1)
    slider_move_factor.set(Val_MoveFactor)
    slider_move_factor.place(x=x8, y=y8)

    label_suspension_value = tk.Label(root, text="Suspension Value: ", font=("Arial", 15))
    label_suspension_value.place(x=x7_1, y=y7_1)

    slider_suspension_value = tk.Scale(root, from_=0, to=100, orient='horizontal', length=400, showvalue=True, resolution=1)
    slider_suspension_value.set(Val_Suspension)
    slider_suspension_value.place(x=x8_1, y=y8_1)

    # label_target_tag = tk.Label(root, text="Aiming Part: ", font=("Arial", 15))
    # label_target_tag.place(x=x9, y=y9)
    #
    # combo_target = ttk.Combobox(root, values=["Head", "Chest"], state="readonly",
    #                             font=("Arial", 15))
    # combo_target.place(x=x10, y=y10)
    # combo_target.set(value="Head")

    label_key = tk.Label(root, text="Activation Key: ", font=("Arial", 15))
    label_key.place(x=x11, y=y11)

    label_key_name = tk.Label(root, text=aim_key_name, font=("Arial", 15))
    label_key_name.place(x=x12, y=y12)

    button_set_key = tk.Button(root, text="Reset Activation Key", font=("Arial", 10), command=detect_pressed_key)
    button_set_key.place(x=x13, y=y13)

    label_input_method = tk.Label(root, text="Input Method: ", font=("Arial", 15))
    label_input_method.place(x=x14, y=y14)

    combo_input_method = ttk.Combobox(root, values=["Virtual", "COM Port"], state="readonly", font=("Arial", 15), width=8)
    combo_input_method.place(x=x15, y=y15)
    combo_input_method.set(value="Virtual")

    button_find_com = tk.Button(root, text="Search COMs", font=("Arial", 10), command=find_the_com)
    button_find_com.place(x=x16, y=y16)

    combo_port = ttk.Combobox(root, values=[], state="readonly", font=("Arial", 15), width=25)
    combo_port.place(x=x17, y=y17)

    button_connect = tk.Button(root, text="Connect", command=connect_to_port, font=("Arial", 10))
    button_connect.place(x=x18, y=y18)

    label_indicator = tk.Label(root, text="♦", font=("Arial", 20), fg="red")
    label_indicator.place(x=x19, y=y19)

    button_camera_view = tk.Button(root, text="Switch On/Off Capture View", command=switch_camera, font=("Arial", 15))
    button_camera_view.place(x=x20, y=y20)

    label_FPS = tk.Label(root, text="FPS_label: ", font=("Arial", 15))
    label_FPS.place(x=x21, y=y21)

    while not is_program_closed:
        root.update()

        value_conf_detect = slider_detect_conf.get()
        Val_DetectConf = value_conf_detect
        threshold_value = value_conf_detect/100

        value_capture_ratio = slider_x_ratio.get()
        Val_ScreenRatio = value_capture_ratio

        value_lock_ratio = slider_ratio_lock.get()
        Val_LockRatio = value_lock_ratio

        value_move_factor = slider_move_factor.get()
        Val_MoveFactor = value_move_factor
        MoveFactor_move = value_move_factor

        value_suspension = slider_suspension_value.get()
        Val_Suspension = value_suspension
        Suspension_val = Val_Suspension

        # aim_target = combo_target.get()
        input_method = combo_input_method.get()
        Name_COM = combo_port.get()

        if x_ratio != value_capture_ratio/100:
            x_ratio = value_capture_ratio/100
            x_window = int(x_screen * x_ratio)
            y_window = int(y_screen * (x_ratio * xy_ration))
            d_left = int(x_screen / 2 - x_window / 2)
            d_top = int(y_screen / 2 - y_window / 2)
            mon1 = {'left': d_left, 'top': d_top, 'width': x_window, 'height': y_window}

        if lock_ratio != value_lock_ratio/100:
            lock_ratio = value_lock_ratio/100

        if len(FPS_array_detect):
            FPS_ave_detect = sum(FPS_array_detect) / len(FPS_array_detect)
        else:
            FPS_ave_detect = 0
        if len(FPS_array_img):
            FPS_ave_img = sum(FPS_array_img) / len(FPS_array_img)
        else:
            FPS_ave_img = 0

        if is_key_changed:
            aim_key_name = KEY_NAMES.get(aim_key_code)
            label_key_name.config(text=aim_key_name)
            is_key_changed = False

        if combo_port["values"] != port_list:
            combo_port["values"] = port_list

        port_device_ui = combo_port.get()
        if not (port_device_ui in port_list):
            combo_port.set("")
            is_serial_open = False

        if is_serial_open:
            label_indicator.config(fg="green")
        else:
            label_indicator.config(fg="red")

        label_FPS.config(text="FPS_label->" + "Detect FPS: " + str(round(FPS_ave_detect)) + " | " + "Source FPS: " + str(round(FPS_ave_img)))
        time.sleep(0.001)


def on_closing():
    global is_program_closed
    new_data = [
        ['DetectConf', 'ScreenRatio', 'LockRation', 'MoveFactor', "SuspensionValue", "ActivationKey"],
        [Val_DetectConf, Val_ScreenRatio, Val_LockRatio, Val_MoveFactor, Val_Suspension, aim_key_code]
    ]
    try:
        local_csvfile = open('ParaSetting.csv', mode='w', newline='')
        local_writer = csv.writer(local_csvfile)
        local_writer.writerows(new_data)
        local_csvfile.close()
    except:
        pass
    is_program_closed = True


def switch_camera():
    global is_img_closed
    is_img_closed = not is_img_closed


def detect_pressed_key():
    global aim_key_code, is_key_changed, x_target, y_target
    aim_key_code = None
    while True:
        for key in range(2, 256):  # Iterate through key codes
            if win32api.GetAsyncKeyState(key) < 0:  # Check high-order bit
                aim_key_code = key
                break
        if aim_key_code is not None:
            is_key_changed = True
            x_target = 0
            y_target = 0
            break
        time.sleep(0.01)  # Add a slight delay to reduce CPU usage


def func_display():
    window_name = "EfficientDet Detection"

    while not is_program_closed:
        if (frame_to_display is not None) and (not is_img_closed):
            cv2.imshow(window_name, frame_to_display)
            cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                pass
        else:
            visibility = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE)
            if visibility >= 0:
                cv2.destroyAllWindows()
    cv2.destroyAllWindows()


t_gui = threading.Thread(target=func_gui, args=())
t_image = threading.Thread(target=func_image_input, args=())
t_detect = threading.Thread(target=func_detect, args=())
t_display = threading.Thread(target=func_display, args=())

t_gui.start()
t_image.start()
time.sleep(0.5)
t_detect.start()
t_display.start()

t_gui.join()
t_image.join()
t_detect.join()
t_display.join()