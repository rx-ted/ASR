# -*- encoding:utf-8 -*-
# author:rx-ted


import wave
import time
import os
import _thread
import pyaudio
import tkinter
from masr.predict import Predictor
import torch
device = torch.device("cpu")
tk = tkinter.Tk()  # 界面控件


class Recording:
    def __init__(self, window: tk) -> None:
        self.window = window
        self.window.title('语音识别')
        self.window.geometry('300x300')
        self.window.resizable(False, False)  # 不能最大化
        self.recordButton = tkinter.Button(
            self.window, text='录音识别', width=10, command=self.record_audio_thread,)
        self.recordButton.place(x=100, y=50) # 放置位置
        self.showLabel = tkinter.Label(self.window, text="输出日志:")
        self.showLabel.place(x=10, y=80)# 放置位置
        self.result_text = tkinter.Text(
            self.window, width=39, height=10, yscrollcommand=True)
        self.result_text.place(x=10, y=100)# 放置位置

        # 录音功能
        self.recordFlag = False  # 控制说话标志
        self.max_record = 600  # 600s 最大录音时长
        self.output_path = 'dataset/record'
        self.p = pyaudio.PyAudio()

        # 识别功能
        self.predictor = Predictor(decoder='ctc_greedy',use_gpu=False)  # 其余的参数都是默认的，不需要改动太大。

    def record_audio_thread(self):
        if not self.recordFlag:
            # 开始录音
            self.result_text.insert(tkinter.END, '开始录音\n')
            _thread.start_new_thread(self.recordAudio, ()) # 新线程
        else:
            self.result_text.insert(tkinter.END, '停止录音\n')
            self.recordButton.configure(text='录音识别')
            self.recordFlag = False  # 停止录音

    def speechRecognition(self, wav_path):
        try:
            start = time.time()
            score, text = self.predictor.predict(audio_path=wav_path)
            self.result_text.insert(tkinter.END, "消耗时间：%dms, 识别结果: %s, 得分: %d\n" % (
                round((time.time() - start) * 1000), text, score))
        except Exception as e:
            print(e)
        

    def recordAudio(self):
        self.recordButton.configure(text='停止录音')
        self.recordFlag = True
        # 识别间隔时间
        interval_time = 2
        CHUNK = 16000 * interval_time
        format = pyaudio.paInt16
        channels = 1
        rate = 16000

        # 打开录音
        self.stream = self.p.open(format=format,
                                  channels=channels,
                                  rate=rate,
                                  input=True,
                                  frames_per_buffer=CHUNK)
        start = time.time()
        frames = []
        while True:
            if not self.recordFlag:
                break
            data = self.stream.read(CHUNK)
            frames.append(data)

            # 超出最大录制时间
            if len(frames) * 2 > self.max_record:
                self.result_text.insert(tkinter.END, "录音已超过最大限制时长,强制停止录音!")
                break

        # 保存录音
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
        self.wav_path = os.path.join(
            self.output_path, '%s.wav' % str(int(time.time())))
        wf = wave.open(self.wav_path, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(self.p.get_sample_size(format))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        self.recording = False
        self.result_text.insert(
            tkinter.END, "录音已结束,录音文件保存在:%s\n" % self.wav_path)
        self.speechRecognition(self.wav_path)


if __name__ == '__main__':
    Recording(tk)
    tk.mainloop()



    