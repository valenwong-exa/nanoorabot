"""Standalone CLI entry for the reusable SenseVoice service."""

from __future__ import annotations

import argparse

from webui.voice import (
    SenseVoiceMicOptions,
    SenseVoiceService,
    get_voice_runtime_status,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m webui.voice_cli",
        description="Run the external SenseVoice microphone tool from the WebUI Python environment.",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available microphone devices and exit.",
    )
    parser.add_argument(
        "--sensevoice-dir",
        default=None,
        help="Path to the external SenseVoice-main workspace. Defaults to ../SenseVoice-main.",
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
        help="Recording sample rate passed to mic_test.py.",
    )
    parser.add_argument(
        "--language",
        default="zh",
        help="Recognition language passed to mic_test.py.",
    )
    parser.add_argument(
        "--device",
        default="cuda:0",
        help="Inference device passed to mic_test.py, such as cuda:0 or cpu.",
    )
    parser.add_argument(
        "--input-device",
        type=int,
        default=None,
        help="Optional microphone device index.",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep the recorded wav file for troubleshooting.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    status_payload = get_voice_runtime_status(sensevoice_dir=args.sensevoice_dir)
    if not status_payload["ok"]:
        print(f"[voice] {status_payload['reason']}", flush=True)
        print(
            "[voice] 请先按需安装 voice 依赖，例如: pip install \"nanobot-webui[voice]\"",
            flush=True,
        )
        return 1

    service = SenseVoiceService(sensevoice_dir=args.sensevoice_dir)
    print(f"[voice] SenseVoice 目录: {service.paths.root_dir}", flush=True)
    print(f"[voice] Python 环境: {service.python_executable}", flush=True)

    if args.list_devices:
        print(service.list_devices_text(), end="", flush=True)
        return 0

    return service.run_microphone_capture(
        SenseVoiceMicOptions(
            duration=args.duration,
            samplerate=args.samplerate,
            language=args.language,
            device=args.device,
            input_device=args.input_device,
            keep_audio=args.keep_audio,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
