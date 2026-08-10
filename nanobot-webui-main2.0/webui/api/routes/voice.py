"""Voice service routes."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from webui.api.deps import get_current_user
from webui.api.models import (
    VoiceDevicesResponse,
    VoiceHealthResponse,
    VoiceInputDeviceInfo,
    VoiceTranscriptionResponse,
)
from webui.voice import get_voice_runtime_status, get_voice_service, list_input_devices

router = APIRouter()


@router.get("/health", response_model=VoiceHealthResponse)
async def get_voice_health(
    _user: Annotated[dict, Depends(get_current_user)],
) -> VoiceHealthResponse:
    payload = get_voice_runtime_status()
    if payload["ok"]:
        service = get_voice_service()
        service_payload = service.health_payload()
        payload["model_loaded"] = service_payload["model_loaded"]
        payload["device"] = service_payload["device"]

    return VoiceHealthResponse(
        ok=bool(payload["ok"]),
        reason=payload["reason"] if isinstance(payload["reason"], str) else None,
        sensevoiceDir=str(payload["sensevoice_dir"]),
        modelPy=str(payload["model_py"]),
        pythonExecutable=str(payload["python_executable"]),
        modelLoaded=bool(payload["model_loaded"]),
        device=payload["device"] if isinstance(payload["device"], str) else None,
        missingDependencies=[
            item for item in payload["missing_dependencies"] if isinstance(item, str)
        ],
        missingPaths=[item for item in payload["missing_paths"] if isinstance(item, str)],
    )


@router.get("/devices", response_model=VoiceDevicesResponse)
async def get_voice_devices(
    _user: Annotated[dict, Depends(get_current_user)],
) -> VoiceDevicesResponse:
    try:
        items = await asyncio.to_thread(list_input_devices)
    except RuntimeError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Failed to query microphone devices: {exc}",
        ) from exc

    return VoiceDevicesResponse(
        items=[
            VoiceInputDeviceInfo(
                index=item.index,
                name=item.name,
                hostapi=item.hostapi,
                maxInputChannels=item.max_input_channels,
                defaultSamplerate=item.default_samplerate,
                isDefault=item.is_default,
            )
            for item in items
        ]
    )


@router.post("/transcriptions", response_model=VoiceTranscriptionResponse)
async def create_voice_transcription(
    _user: Annotated[dict, Depends(get_current_user)],
    file: UploadFile = File(...),
    language: str = Form("zh"),
    device: str = Form("cuda:0"),
) -> VoiceTranscriptionResponse:
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Audio filename is required")

    payload = await file.read()
    if not payload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded audio file is empty")

    status_payload = get_voice_runtime_status()
    if not status_payload["ok"]:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            str(status_payload["reason"] or "Voice transcription is unavailable"),
        )

    try:
        service = get_voice_service()
        temp_path = await asyncio.to_thread(service.save_upload_to_temp, file.filename, payload)
        try:
            result = await asyncio.to_thread(
                service.transcribe_file,
                temp_path,
                language=language,
                device=device,
            )
        finally:
            temp_path.unlink(missing_ok=True)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Voice transcription failed: {exc}",
        ) from exc
    finally:
        await file.close()

    return VoiceTranscriptionResponse(
        success=True,
        text=result.text,
        language=result.language,
        device=result.device,
        inferenceMs=result.inference_ms,
        audioDurationMs=result.audio_duration_ms,
        filename=Path(file.filename).name,
    )
