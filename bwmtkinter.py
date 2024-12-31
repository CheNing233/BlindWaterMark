#!/usr/bin/env python
# -*- coding: utf8 -*-

import sys
import random
import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES  # 拖放功能的库
from tkinter import messagebox

# 参数
cmd = None
debug = False
seed = 20160930
oldseed = False
alpha = 3.0
fn1 = fn2 = fn3 = None


# OpenCV是以(BGR)的顺序存储图像数据的
# 而Matplotlib是以(RGB)的顺序显示图像的
def bgr_to_rgb(img):
    b, g, r = cv2.split(img)
    return cv2.merge([r, g, b])


def process_image(image_path, watermark_path, mode):
    global cmd, fn1, fn2, fn3
    cmd = mode

    # 提取文件名和后缀
    base_name, ext = os.path.splitext(image_path)

    # 文件路径处理
    fn1 = image_path
    fn2 = watermark_path
    if cmd == "encode":
        fn3 = base_name + "_encode" + ext
    else:
        fn3 = base_name + "_decode" + ext

    if not os.path.exists(fn1) or not os.path.exists(fn2):
        messagebox.showerror("错误", "缺少图片或水印文件")
        return

    # 图像处理逻辑
    if cmd == "encode":
        print(f"image<{fn1}> + watermark<{fn2}> -> image(encoded)<{fn3}>")
        img = cv2.imread(fn1)
        wm = cv2.imread(fn2)

        # 水印嵌入
        h, w = img.shape[0], img.shape[1]
        hwm = np.zeros((int(h * 0.5), w, img.shape[2]))
        hwm2 = np.copy(hwm)
        for i in range(wm.shape[0]):
            for j in range(wm.shape[1]):
                hwm2[i][j] = wm[i][j]

        random.seed(seed)
        m, n = list(range(hwm.shape[0])), list(range(hwm.shape[1]))
        random.shuffle(m)
        random.shuffle(n)

        for i in range(hwm.shape[0]):
            for j in range(hwm.shape[1]):
                hwm[i][j] = hwm2[m[i]][n[j]]

        rwm = np.zeros(img.shape)
        for i in range(hwm.shape[0]):
            for j in range(hwm.shape[1]):
                rwm[i][j] = hwm[i][j]
                rwm[rwm.shape[0] - i - 1][rwm.shape[1] - j - 1] = hwm[i][j]

        f1 = np.fft.fft2(img)
        f2 = f1 + alpha * rwm
        _img = np.fft.ifft2(f2)

        img_wm = np.real(_img)
        cv2.imwrite(fn3, img_wm, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
        messagebox.showinfo("加密完成", f"加密图片已保存为: {fn3}")

    elif cmd == "decode":
        print(f"image<{fn1}> + image(encoded)<{fn2}> -> watermark<{fn3}>")
        img = cv2.imread(fn1)
        img_wm = cv2.imread(fn2)

        random.seed(seed)
        m, n = list(range(int(img.shape[0] * 0.5))), list(range(img.shape[1]))
        random.shuffle(m)
        random.shuffle(n)

        f1 = np.fft.fft2(img)
        f2 = np.fft.fft2(img_wm)

        rwm = (f2 - f1) / alpha
        rwm = np.real(rwm)

        wm = np.zeros(rwm.shape)
        for i in range(int(rwm.shape[0] * 0.5)):
            for j in range(rwm.shape[1]):
                wm[m[i]][n[j]] = np.uint8(rwm[i][j])

        for i in range(int(rwm.shape[0] * 0.5)):
            for j in range(rwm.shape[1]):
                wm[rwm.shape[0] - i - 1][rwm.shape[1] - j - 1] = wm[i][j]

        cv2.imwrite(fn3, wm)
        messagebox.showinfo("解密完成", f"解密水印已保存为: {fn3}")


# Tkinter界面部分
class WatermarkApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("暗水印加密/解密")
        self.geometry("400x250")
        self.configure(bg="lightgray")

        self.mode_var = tk.StringVar(value="encode")

        # 添加选择框
        encode_radio = tk.Radiobutton(
            self, text="加密", variable=self.mode_var, value="encode", bg="lightgray", command=self.update_mode
        )
        decode_radio = tk.Radiobutton(
            self, text="解密", variable=self.mode_var, value="decode", bg="lightgray", command=self.update_mode
        )
        encode_radio.pack(pady=10)
        decode_radio.pack(pady=10)

        # 拖放标签
        self.image_label = tk.Label(
            self,
            text="拖动原图到这里",
            bg="white",
            relief="sunken",
            width=40,
            height=5,
        )
        self.image_label.pack(pady=10)

        self.watermark_label = tk.Label(
            self,
            text="拖动水印图到这里",
            bg="white",
            relief="sunken",
            width=40,
            height=5,
        )
        self.watermark_label.pack(pady=10)

        self.result_label = tk.Label(
            self,
            text="拖动加密图到这里（解密模式下）",
            bg="white",
            relief="sunken",
            width=40,
            height=5,
        )
        self.result_label.pack(pady=10)

        # 确认按钮
        self.confirm_button = tk.Button(self, text="开始处理", command=self.start_processing)
        self.confirm_button.pack(pady=20)

        # 拖放事件绑定
        self.image_label.drop_target_register(DND_FILES)
        self.image_label.dnd_bind("<<Drop>>", self.drop_image)

        self.watermark_label.drop_target_register(DND_FILES)
        self.watermark_label.dnd_bind("<<Drop>>", self.drop_watermark)

        self.result_label.drop_target_register(DND_FILES)
        self.result_label.dnd_bind("<<Drop>>", self.drop_result)

        # 隐藏结果标签和确认按钮（默认情况下）
        self.result_label.pack_forget()
        # self.confirm_button.pack_forget()
        
        self.geometry("500x400")
        

    def update_mode(self):
        """根据选择的模式更新界面"""
        mode = self.mode_var.get()
        if mode == "encode":
            self.watermark_label.pack(pady=10)
            self.result_label.pack_forget()  # 隐藏加密图标签
        else:  # 解密模式
            self.watermark_label.pack_forget()  # 隐藏水印图标签
            self.result_label.pack(pady=10)

        self.check_ready()
        

    def drop_image(self, event):
        self.image_path = event.data
        self.image_label.config(text=f"原图: {os.path.basename(self.image_path)}")
        self.check_ready()

    def drop_watermark(self, event):
        self.watermark_path = event.data
        self.watermark_label.config(text=f"水印图: {os.path.basename(self.watermark_path)}")
        self.check_ready()

    def drop_result(self, event):
        self.result_path = event.data
        self.result_label.config(text=f"加密图: {os.path.basename(self.result_path)}")
        self.check_ready()

    def check_ready(self):
        """检查是否准备好进行加解密操作"""
        if hasattr(self, "image_path") and hasattr(self, "watermark_path"):
            if self.mode_var.get() == "decode" and hasattr(self, "result_path"):
                self.confirm_button.config(state="normal")
            elif self.mode_var.get() == "encode":
                self.confirm_button.config(state="normal")
            else:
                self.confirm_button.config(state="disabled")

    def start_processing(self):
        """开始处理图像"""
        mode = self.mode_var.get()
        if mode == "encode":
            process_image(self.image_path, self.watermark_path, mode)
        elif mode == "decode":
            process_image(self.image_path, self.result_path, mode)


# 运行界面
if __name__ == "__main__":
    app = WatermarkApp()
    app.mainloop()
