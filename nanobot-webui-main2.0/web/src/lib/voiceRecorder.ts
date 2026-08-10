export interface VoiceRecordingResult {
  blob: Blob;
  durationMs: number;
  sampleRate: number;
}

interface BrowserVoiceRecorderOptions {
  targetSampleRate?: number;
}

type AudioContextWithWebkit = Window &
  typeof globalThis & {
    webkitAudioContext?: typeof AudioContext;
  };

export class BrowserVoiceRecorder {
  private readonly targetSampleRate: number;
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private processorNode: ScriptProcessorNode | null = null;
  private muteGainNode: GainNode | null = null;
  private buffers: Float32Array[] = [];

  constructor(options: BrowserVoiceRecorderOptions = {}) {
    this.targetSampleRate = options.targetSampleRate ?? 16000;
  }

  async start(): Promise<void> {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("browser_unsupported");
    }

    const AudioContextConstructor =
      window.AudioContext ?? (window as AudioContextWithWebkit).webkitAudioContext;
    if (!AudioContextConstructor) {
      throw new Error("browser_unsupported");
    }

    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    this.audioContext = new AudioContextConstructor();
    this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
    this.processorNode = this.audioContext.createScriptProcessor(4096, 1, 1);
    this.muteGainNode = this.audioContext.createGain();
    this.muteGainNode.gain.value = 0;

    this.processorNode.onaudioprocess = (event) => {
      const inputData = event.inputBuffer.getChannelData(0);
      this.buffers.push(new Float32Array(inputData));
    };

    this.sourceNode.connect(this.processorNode);
    this.processorNode.connect(this.muteGainNode);
    this.muteGainNode.connect(this.audioContext.destination);
  }

  async stop(): Promise<VoiceRecordingResult> {
    const sourceSampleRate = this.audioContext?.sampleRate ?? this.targetSampleRate;
    this.cleanupNodes();
    await this.cleanupStreamAndContext();

    const merged = mergeBuffers(this.buffers);
    this.buffers = [];
    const pcm = downsampleBuffer(merged, sourceSampleRate, this.targetSampleRate);
    const wavBuffer = encodeWav(pcm, this.targetSampleRate);

    return {
      blob: new Blob([wavBuffer], { type: "audio/wav" }),
      durationMs: Math.round((pcm.length / this.targetSampleRate) * 1000),
      sampleRate: this.targetSampleRate,
    };
  }

  async cancel(): Promise<void> {
    this.cleanupNodes();
    await this.cleanupStreamAndContext();
    this.buffers = [];
  }

  private cleanupNodes(): void {
    this.processorNode?.disconnect();
    this.sourceNode?.disconnect();
    this.muteGainNode?.disconnect();
    if (this.processorNode) {
      this.processorNode.onaudioprocess = null;
    }
    this.processorNode = null;
    this.sourceNode = null;
    this.muteGainNode = null;
  }

  private async cleanupStreamAndContext(): Promise<void> {
    this.mediaStream?.getTracks().forEach((track) => track.stop());
    this.mediaStream = null;
    if (this.audioContext && this.audioContext.state !== "closed") {
      await this.audioContext.close().catch(() => undefined);
    }
    this.audioContext = null;
  }
}

function mergeBuffers(buffers: Float32Array[]): Float32Array {
  const totalLength = buffers.reduce((sum, buffer) => sum + buffer.length, 0);
  const merged = new Float32Array(totalLength);
  let offset = 0;
  for (const buffer of buffers) {
    merged.set(buffer, offset);
    offset += buffer.length;
  }
  return merged;
}

function downsampleBuffer(
  buffer: Float32Array,
  sourceSampleRate: number,
  targetSampleRate: number,
): Float32Array {
  if (buffer.length === 0 || sourceSampleRate === targetSampleRate) {
    return buffer;
  }

  const sampleRateRatio = sourceSampleRate / targetSampleRate;
  const newLength = Math.round(buffer.length / sampleRateRatio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
    let accum = 0;
    let count = 0;

    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i += 1) {
      accum += buffer[i];
      count += 1;
    }

    result[offsetResult] = count > 0 ? accum / count : 0;
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
}

function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const bytesPerSample = 2;
  const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample);
  const view = new DataView(buffer);

  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * bytesPerSample, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * bytesPerSample, true);
  view.setUint16(32, bytesPerSample, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, "data");
  view.setUint32(40, samples.length * bytesPerSample, true);

  floatTo16BitPCM(view, 44, samples);
  return buffer;
}

function floatTo16BitPCM(view: DataView, offset: number, input: Float32Array): void {
  for (let i = 0; i < input.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, input[i]));
    view.setInt16(offset + i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
}

function writeString(view: DataView, offset: number, value: string): void {
  for (let i = 0; i < value.length; i += 1) {
    view.setUint8(offset + i, value.charCodeAt(i));
  }
}
