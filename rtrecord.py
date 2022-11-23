'''
Author: rx-ted
Date: 2022-11-11 23:57:45
LastEditors: rx-ted
LastEditTime: 2022-11-23 22:39:33
'''

'''
支持PPASR/MASR,其余未测试
'''


import threading
import _thread
import pyaudio
import wave
import numpy as np
import pyAudioKits.audio as ak
import asyncio
import audioop
import  websockets
import time
uri = "ws://localhost:5001"


async def hello():

    async with websockets.connect(uri) as websocket:
        ls = b''
        p = pyaudio.PyAudio()
        stream = p.open(16000, 1, pyaudio.paInt16, True)
        if True:

            for i in range(int(16000/1024*5)):
                buf = stream.read(1024)

                if buf is None:
                    break
                ls += buf
            ls += b'end'

            # await websocket.send(ls)
            # g = await websocket.recv()
            # print(g)
            # if '拜拜' in g:break
            # else:
            #     time.sleep(2)

        stream.stop_stream()
        stream.close()
        p.terminate()  # 释放portaudio资源


async def main():
    try:
        async with websockets.connect(uri) as ws:
            r = Recording(ws=ws)
            await r.recording()
    except Exception as e:
        print(e)
        pass


class Recording:
    def __init__(self,
                 ws,
                 rate=16000,
                 channels=1,
                 format=pyaudio.paInt16,
                 max_recording=60,
                 chuck=1024,
                 sound_path='tmp.wav',
                 max_low_audio_flag=100,
                 max_rms_audio_flag=100,
                 record_pause_time=1
                 ) -> None:
        '''
        :param rate: 采样率
        :param channels: 声道数
        :param format: 声音格式
        :param max_recording: 最大录音时间
        :param chuck: 单次缓冲区大小
        :param sound_path: 默认保存音频路径,很费读写
        :param max_low_audio_flag: 采样经验值，积累到一定，就不录音
        :param max_rms_audio_flag: 采样音频能量，检测分贝


        '''
        self.ws = ws
        self.rate = rate
        self.channels = channels
        self.format = format
        self._recording = False
        self.max_recording = max_recording
        self.chuck = chuck
        self.sound_file = sound_path
        self.max_low_audio_flag = max_low_audio_flag
        self.max_rms_audio_flag = max_rms_audio_flag
        self.record_pause_time = record_pause_time
        self.audio_frames = []
        self.p = pyaudio.PyAudio()
        self.sample_width = pyaudio.get_sample_size(self.format)
        self._end_flag = False
        self.stream = self.p.open(
            rate=self.rate,
            channels=self.channels,
            format=self.format,
            input=True
        )

    async def recording(self):
        frames_data = b''
        self._recording = True
        low_audio_flag = 0
        audio_count = 0  # 每一次读取1024
        msg = None
        while self._recording and not self.ws.closed:
            if self.audio_frames:
                s = self.audio_frames.pop(0)
                await self.ws.send(s)
                tmp = await self.ws.recv()
                if tmp != msg:
                    msg = tmp
                    print(msg)

                # asyncio.create_task(self.send_recv_data)
            buf = self.stream.read(self.chuck)
            rms = self.rms(buf)
            low_audio_flag = 0 if rms > self.max_rms_audio_flag else low_audio_flag + 1

            frames_data += buf
            if low_audio_flag > self.record_pause_time:
                frames_data = self.bin2sound(frames_data) + b'end'
                self.audio_frames.append(frames_data)
                frames_data = b''

            if low_audio_flag > self.max_low_audio_flag:
                print('已经很长没录到声音了，暂时关闭~')
                self.audio_frames[-1] += b'ext'
                # self._recording = False
            # print('the {} time detecting:{} '.format(audio_count, rms))
            audio_count += 1
        self.stream.stop_stream()
        self.p.terminate()
        # self.p.close()
        self.stream.close()

    def bin2sound(self, buf: bytes) -> bytes:
        wf = wave.open('tmp', 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.sample_width)
        wf.setframerate(self.rate)
        wf.writeframes(buf)
        wf.close()
        wf = wave.open('tmp', 'rb')
        buf = wf.readframes(wf.getnframes())
        wf.close()
        return buf

    def rms(self, stream):
        if not stream:
            return 0
        elif len(stream) % 2 != 0:
            stream += b' '
        d = np.frombuffer(stream, np.int16).astype(np.float64)
        return round(np.sqrt((d*d).sum()/len(d)))


# 录音时候
'''
录音什么时候停止
1 没检测到声音则发送服务端，追加后面结束标志
2 录音超过最大录音时间则发送服务端

'''

if __name__ == "__main__":

    asyncio.run(main())
