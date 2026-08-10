#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import tempfile
import threading
import time
import traceback
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd


def parse_args():
    parser = argparse.ArgumentParser(
        description="Record a short audio clip from microphone and transcribe it with SenseVoice."
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="Maximum recording duration in seconds while holding Ctrl+Z.",
    )
    parser.add_argument(
        "--samplerate",
        type=int,
        default=16000,
        help="Recording sample rate. SenseVoice works well with 16000 Hz.",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="zh",
        choices=["auto", "zh", "en", "yue", "ja", "ko", "nospeech"],
        help="Recognition language. Use zh for Chinese voice commands.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0",
        help="Inference device, e.g. cuda:0 or cpu.",
    )
    parser.add_argument(
        "--input-device",
        type=int,
        default=None,
        help="Optional microphone device index. Leave empty to use the system default input device.",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Print available audio devices and exit.",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep the recorded wav file instead of deleting it after inference.",
    )
    return parser.parse_args()


def list_devices():
    print(sd.query_devices())


def print_step(message):
    print(f"\n[步骤] {message}", flush=True)


def print_info(message):
    print(f"[信息] {message}", flush=True)


def print_warn(message):
    print(f"[警告] {message}", flush=True)


def resolve_runtime_paths():
    script_dir = Path(__file__).resolve().parent
    return {
        "script_dir": script_dir,
        "model_py": script_dir / "model.py",
    }


def normalize_device(requested_device):
    import torch

    normalized = (requested_device or "cpu").strip()
    if normalized.startswith("cuda") and not torch.cuda.is_available():
        print_warn("当前环境未检测到可用 CUDA，自动切换为 CPU 模式")
        return "cpu"
    return normalized


def record_audio(duration, samplerate, input_device=None):
    from pynput import keyboard

    channels = 1
    pressed_event = threading.Event()
    released_event = threading.Event()
    audio_chunks = []
    state = {
        "ctrl_pressed": False,
        "record_hotkey_pressed": False,
    }

    def audio_callback(indata, frames, callback_time, status):
        del frames, callback_time
        if status:
            print_warn(f"录音状态提示: {status}")
        audio_chunks.append(indata.copy())

    def on_press(key):
        if key == keyboard.Key.ctrl_l:
            state["ctrl_pressed"] = True
            if state["record_hotkey_pressed"] and not pressed_event.is_set():
                pressed_event.set()
        elif getattr(key, "char", None) == "\x1a" and state["ctrl_pressed"]:
            state["record_hotkey_pressed"] = True
            if not pressed_event.is_set():
                pressed_event.set()
        return None

    def on_release(key):
        if key == keyboard.Key.ctrl_l:
            state["ctrl_pressed"] = False
            if pressed_event.is_set():
                released_event.set()
                return False
        elif getattr(key, "char", None) == "\x1a":
            state["record_hotkey_pressed"] = False
            if pressed_event.is_set():
                released_event.set()
                return False
        if key == keyboard.Key.ctrl_l and pressed_event.is_set():
            released_event.set()
            return False
        return None

    print_step("等待 Ctrl+Z 按下")
    print_info("按住 Ctrl+Z 开始说话，松开后停止录音")
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    while not pressed_event.wait(timeout=0.05):
        pass

    print_step("检测到 Ctrl+Z，开始录音")
    record_start = time.time()
    try:
        with sd.InputStream(
            samplerate=samplerate,
            channels=channels,
            dtype="int16",
            device=input_device,
            callback=audio_callback,
        ):
            while True:
                if released_event.wait(timeout=0.05):
                    break
                if time.time() - record_start >= duration:
                    print_warn(f"已达到最长录音时长 {duration:.1f} 秒，自动停止")
                    break
    finally:
        listener.stop()
        listener.join()

    if not audio_chunks:
        raise RuntimeError("没有采集到音频数据，请检查麦克风设备或权限")

    print_step("录音结束")
    return np.concatenate(audio_chunks, axis=0).squeeze(axis=-1)


def save_wav(audio, samplerate):
    fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="sensevoice_mic_")
    os.close(fd)
    with wave.open(wav_path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(samplerate)
        wav_file.writeframes(audio.tobytes())
    return wav_path


def transcribe_once(model, args, rich_transcription_postprocess):
    audio = record_audio(
        duration=args.duration,
        samplerate=args.samplerate,
        input_device=args.input_device,
    )
    wav_path = save_wav(audio, args.samplerate)
    print_info(f"录音已保存到: {wav_path}")

    try:
        print_step("开始语音识别")
        infer_start = time.time()
        res = model.generate(
            input=wav_path,
            cache={},
            language=args.language,
            use_itn=True,
            batch_size=1,
        )
        print_info(f"识别完成，耗时 {time.time() - infer_start:.2f} 秒")
        text = rich_transcription_postprocess(res[0]["text"])
        print_step("识别结果")
        print(f"识别文本: {text if text else '[空结果]'}", flush=True)
        print(text if text else "", flush=True)
    finally:
        if args.keep_audio:
            print_info("已保留录音文件，便于复查识别效果")
        else:
            if os.path.exists(wav_path):
                os.remove(wav_path)
                print_info("已删除临时录音文件")


def main():
    args = parse_args()
    runtime_paths = resolve_runtime_paths()
    device = args.device

    if args.list_devices:
        print_step("列出可用音频设备")
        list_devices()
        return

    try:
        device = normalize_device(args.device)
        print_step("准备运行参数")
        print_info(f"识别语言: {args.language}")
        print_info(f"推理设备: {device}")
        print_info(f"采样率: {args.samplerate}")
        print_info(f"最长录音时长: {args.duration:.1f} 秒")
        if args.input_device is not None:
            print_info(f"录音设备编号: {args.input_device}")
        else:
            print_info("录音设备编号: 使用系统默认输入设备")

        print_step("导入 FunASR")
        from funasr import AutoModel
        from funasr.utils.postprocess_utils import rich_transcription_postprocess

        if not runtime_paths["model_py"].exists():
            raise FileNotFoundError(f"未找到模型代码文件: {runtime_paths['model_py']}")

        print_step("加载 SenseVoice 模型")
        print_info("首次运行可能需要下载模型，请耐心等待")
        model_load_start = time.time()
        model = AutoModel(
            model="iic/SenseVoiceSmall",
            trust_remote_code=True,
            remote_code=str(runtime_paths["model_py"]),
            device=device,
            disable_update=True,
        )
        print_info(f"模型加载完成，耗时 {time.time() - model_load_start:.2f} 秒")
        print_step("进入持续监听模式")
        print_info("识别完成后会继续等待下一次输入")
        print_info("按 Ctrl+C 可退出程序")
        while True:
            try:
                transcribe_once(model, args, rich_transcription_postprocess)
            except RuntimeError as exc:
                print_warn(f"本次录音失败: {exc}")
                print_info("将继续等待下一次输入")
    except KeyboardInterrupt:
        print_warn("用户中断了执行")
    except Exception as exc:
        print_warn(f"运行失败: {exc}")
        print_warn("如果是首次运行，常见原因是模型下载慢、GPU 环境不匹配，或麦克风设备选择错误")
        print_info("可先执行: python mic_test.py --list-devices")
        print_info("也可临时改用 CPU 测试: python mic_test.py --device cpu")
        traceback.print_exc()


if __name__ == "__main__":
    main()
