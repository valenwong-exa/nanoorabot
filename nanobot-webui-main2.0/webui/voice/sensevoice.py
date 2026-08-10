"""SenseVoice service helpers for nanobot WebUI."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave
from importlib.util import find_spec
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SENSEVOICE_ENV_VAR = "NANOBOT_SENSEVOICE_DIR"
VOICE_TRANSCRIPTION_DEPENDENCIES = (
    "numpy",
    "scipy",
    "torch",
    "torchaudio",
    "modelscope",
    "funasr",
)
VOICE_DEVICE_QUERY_DEPENDENCIES = ("sounddevice",)


@dataclass(frozen=True)
class SenseVoicePaths:
    """Resolved file-system paths for the external SenseVoice workspace."""

    root_dir: Path
    mic_test_py: Path
    model_py: Path


@dataclass(frozen=True)
class SenseVoiceMicOptions:
    """CLI options for the external microphone tool."""

    duration: float = 30.0
    samplerate: int = 16000
    language: str = "zh"
    device: str = "cuda:0"
    input_device: int | None = None
    keep_audio: bool = False

    def to_cli_args(self) -> list[str]:
        args = [
            "--duration",
            str(self.duration),
            "--samplerate",
            str(self.samplerate),
            "--language",
            self.language,
            "--device",
            self.device,
        ]
        if self.input_device is not None:
            args.extend(["--input-device", str(self.input_device)])
        if self.keep_audio:
            args.append("--keep-audio")
        return args


@dataclass(frozen=True)
class VoiceInputDevice:
    """Structured microphone device information."""

    index: int
    name: str
    hostapi: str | None
    max_input_channels: int
    default_samplerate: float | None
    is_default: bool


@dataclass(frozen=True)
class VoiceTranscriptionResult:
    """Structured speech-to-text result."""

    text: str
    language: str
    device: str
    inference_ms: int
    audio_duration_ms: int | None


def _missing_modules(module_names: tuple[str, ...]) -> list[str]:
    return [module_name for module_name in module_names if find_spec(module_name) is None]


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_sensevoice_dir() -> Path:
    configured = os.environ.get(DEFAULT_SENSEVOICE_ENV_VAR)
    if configured:
        return Path(configured).expanduser().resolve(strict=False)
    return (_default_repo_root().parent / "SenseVoice-main").resolve(strict=False)


def resolve_sensevoice_paths(sensevoice_dir: str | Path | None = None) -> SenseVoicePaths:
    """Resolve and validate the external SenseVoice workspace."""

    root_dir = (
        Path(sensevoice_dir).expanduser().resolve(strict=False)
        if sensevoice_dir is not None
        else _default_sensevoice_dir()
    )
    mic_test_py = root_dir / "mic_test.py"
    model_py = root_dir / "model.py"
    if not root_dir.exists():
        raise FileNotFoundError(f"SenseVoice 目录不存在: {root_dir}")
    if not mic_test_py.exists():
        raise FileNotFoundError(f"未找到 SenseVoice 脚本: {mic_test_py}")
    if not model_py.exists():
        raise FileNotFoundError(f"未找到 SenseVoice 模型代码文件: {model_py}")
    return SenseVoicePaths(
        root_dir=root_dir,
        mic_test_py=mic_test_py,
        model_py=model_py,
    )


def get_voice_runtime_status(
    sensevoice_dir: str | Path | None = None,
) -> dict[str, object]:
    """Inspect whether browser-upload transcription can run in the current environment."""

    root_dir = (
        Path(sensevoice_dir).expanduser().resolve(strict=False)
        if sensevoice_dir is not None
        else _default_sensevoice_dir()
    )
    mic_test_py = root_dir / "mic_test.py"
    model_py = root_dir / "model.py"
    missing_paths: list[str] = []
    if not root_dir.exists():
        missing_paths.append(str(root_dir))
    if not mic_test_py.exists():
        missing_paths.append(str(mic_test_py))
    if not model_py.exists():
        missing_paths.append(str(model_py))

    missing_dependencies = _missing_modules(VOICE_TRANSCRIPTION_DEPENDENCIES)
    ok = len(missing_paths) == 0 and len(missing_dependencies) == 0

    reason: str | None = None
    if missing_paths:
        reason = "未检测到 SenseVoice 目录或关键文件，请先准备 SenseVoice-main。"
    elif missing_dependencies:
        reason = (
            "未安装语音识别依赖，请按需安装 voice 依赖后再启用语音功能。"
        )

    return {
        "ok": ok,
        "reason": reason,
        "sensevoice_dir": str(root_dir),
        "model_py": str(model_py),
        "python_executable": str(Path(sys.executable).resolve(strict=False)),
        "model_loaded": False,
        "device": None,
        "missing_dependencies": missing_dependencies,
        "missing_paths": missing_paths,
    }


def list_input_devices() -> list[VoiceInputDevice]:
    try:
        import sounddevice as sd
    except ModuleNotFoundError as exc:
        raise RuntimeError("缺少 sounddevice 依赖，无法查询录音设备") from exc

    raw_devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    default_input = None
    try:
        default_input = int(sd.default.device[0])
    except Exception:
        default_input = None

    devices: list[VoiceInputDevice] = []
    for index, raw in enumerate(raw_devices):
        max_input_channels = int(raw.get("max_input_channels", 0) or 0)
        if max_input_channels <= 0:
            continue
        hostapi_index = raw.get("hostapi")
        hostapi_name = None
        if isinstance(hostapi_index, int) and 0 <= hostapi_index < len(hostapis):
            hostapi_name = str(hostapis[hostapi_index].get("name") or "")
        devices.append(
            VoiceInputDevice(
                index=index,
                name=str(raw.get("name") or f"device-{index}"),
                hostapi=hostapi_name or None,
                max_input_channels=max_input_channels,
                default_samplerate=(
                    float(raw.get("default_samplerate"))
                    if raw.get("default_samplerate") is not None
                    else None
                ),
                is_default=index == default_input,
            )
        )
    return devices


def normalize_device(requested_device: str | None) -> str:
    """Resolve the runtime device with automatic CPU fallback."""

    import torch

    normalized = (requested_device or "cpu").strip()
    if normalized.startswith("cuda") and not torch.cuda.is_available():
        return "cpu"
    return normalized


class SenseVoiceService:
    """Reusable SenseVoice service for CLI, API, and future frontend calls."""

    def __init__(
        self,
        sensevoice_dir: str | Path | None = None,
        python_executable: str | Path | None = None,
    ) -> None:
        self.paths = resolve_sensevoice_paths(sensevoice_dir)
        self.python_executable = str(
            Path(python_executable).expanduser().resolve(strict=False)
            if python_executable is not None
            else Path(sys.executable).resolve(strict=False)
        )
        self._model_lock = threading.Lock()
        self._model: object | None = None
        self._postprocess: object | None = None
        self._loaded_device: str | None = None

    def build_mic_command(
        self,
        options: SenseVoiceMicOptions | None = None,
        *,
        list_devices: bool = False,
    ) -> list[str]:
        command = [self.python_executable, str(self.paths.mic_test_py)]
        if list_devices:
            command.append("--list-devices")
        elif options is not None:
            command.extend(options.to_cli_args())
        return command

    def run_mic_tool(
        self,
        options: SenseVoiceMicOptions | None = None,
        *,
        list_devices: bool = False,
        capture_output: bool = False,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        command = self.build_mic_command(options, list_devices=list_devices)
        return subprocess.run(
            command,
            cwd=str(self.paths.root_dir),
            text=True,
            capture_output=capture_output,
            check=check,
        )

    def run_microphone_capture(self, options: SenseVoiceMicOptions | None = None) -> int:
        result = self.run_mic_tool(options=options, capture_output=False, check=False)
        return result.returncode

    def list_devices_text(self) -> str:
        result = self.run_mic_tool(list_devices=True, capture_output=True, check=True)
        return result.stdout

    def list_input_devices(self) -> list[VoiceInputDevice]:
        return list_input_devices()

    def is_model_loaded(self) -> bool:
        return self._model is not None and self._postprocess is not None

    def health_payload(self) -> dict[str, object]:
        return {
            "ok": True,
            "sensevoice_dir": str(self.paths.root_dir),
            "model_py": str(self.paths.model_py),
            "python_executable": self.python_executable,
            "model_loaded": self.is_model_loaded(),
            "device": self._loaded_device,
        }

    def transcribe_file(
        self,
        audio_path: str | Path,
        *,
        language: str = "zh",
        device: str = "cuda:0",
    ) -> VoiceTranscriptionResult:
        runtime_device = normalize_device(device)
        model, postprocess = self._ensure_runtime(runtime_device)
        infer_start = time.perf_counter()
        response = model.generate(
            input=str(Path(audio_path).resolve(strict=False)),
            cache={},
            language=language,
            use_itn=True,
            batch_size=1,
        )
        inference_ms = int((time.perf_counter() - infer_start) * 1000)
        text = postprocess(response[0]["text"]) if response else ""
        return VoiceTranscriptionResult(
            text=text,
            language=language,
            device=runtime_device,
            inference_ms=inference_ms,
            audio_duration_ms=_read_audio_duration_ms(Path(audio_path)),
        )

    def save_upload_to_temp(self, filename: str | None, payload: bytes) -> Path:
        suffix = Path(filename or "voice.wav").suffix or ".wav"
        fd, temp_path = tempfile.mkstemp(prefix="nanobot_voice_", suffix=suffix)
        temp_file = Path(temp_path)
        os.close(fd)
        temp_file.write_bytes(payload)
        return temp_file

    def _ensure_runtime(self, device: str) -> tuple[object, object]:
        with self._model_lock:
            if (
                self._model is not None
                and self._postprocess is not None
                and self._loaded_device == device
            ):
                return self._model, self._postprocess

            from funasr import AutoModel
            from funasr.utils.postprocess_utils import rich_transcription_postprocess

            self._model = AutoModel(
                model="iic/SenseVoiceSmall",
                trust_remote_code=True,
                remote_code=str(self.paths.model_py),
                device=device,
                disable_update=True,
            )
            self._postprocess = rich_transcription_postprocess
            self._loaded_device = device
            return self._model, self._postprocess


def _read_audio_duration_ms(audio_path: Path) -> int | None:
    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            if sample_rate <= 0:
                return None
            return int(frames / sample_rate * 1000)
    except (wave.Error, FileNotFoundError, OSError):
        return None


_service_instance: SenseVoiceService | None = None
_service_instance_lock = threading.Lock()


def get_voice_service(sensevoice_dir: str | Path | None = None) -> SenseVoiceService:
    """Return a process-level singleton voice service."""

    global _service_instance
    with _service_instance_lock:
        if _service_instance is None:
            _service_instance = SenseVoiceService(sensevoice_dir=sensevoice_dir)
        return _service_instance
