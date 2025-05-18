const CTL_READ_IDX = 1;
const CTL_SAMPLES_AVAIL_IDX = 2;


class SharedAudioProcessor extends AudioWorkletProcessor {
    HIGH_WATERMARK_SAMPLES = 0
    LOW_WATERMARK_SAMPLES = 0

    valid: boolean = false;
    isSignalingPause = false

    audioSAB = new SharedArrayBuffer(16)
    controlSAB = new SharedArrayBuffer(16)
    controlBuffer = new Int32Array(new SharedArrayBuffer(16));
    audioBuffer = new Float32Array(new SharedArrayBuffer(16));
    maxAudioBufferSamples = 0


    constructor(options: AudioWorkletNodeOptions) {
        super();

        if (!options.processorOptions || !options.processorOptions.audioSAB || !options.processorOptions.controlSAB) {
            console.error("[AudioWorklet] SABs not provided to processor options!");
            this.port.postMessage({ type: 'error', message: 'SABs not provided to processor' });
            this.valid = false;
            return; // Cannot operate
        }

        this.audioSAB = options.processorOptions.audioSAB;
        this.controlSAB = options.processorOptions.controlSAB;

        this.audioBuffer = new Float32Array(this.audioSAB);
        this.controlBuffer = new Int32Array(this.controlSAB);

        this.maxAudioBufferSamples = this.audioBuffer.length;
        this.HIGH_WATERMARK_SAMPLES = Math.floor(this.maxAudioBufferSamples * 0.75);
        this.LOW_WATERMARK_SAMPLES = Math.floor(this.maxAudioBufferSamples * 0.25);

        this.isSignalingPause = false;

        console.log(`[AudioWorklet] Initialized. Audio buffer: ${this.maxAudioBufferSamples} samples. HW: ${this.HIGH_WATERMARK_SAMPLES}, LW: ${this.LOW_WATERMARK_SAMPLES}`);
        this.valid = true;
        this.port.postMessage({ type: 'worklet_ready' });
    }

    sendControlMessage(command: 'pause_sending' | 'resume_sending') {
        this.port.postMessage({
            type: 'control',
            command: command
        });
    }

    process(inputs: Float32Array[][], outputs: Float32Array[][], parameters: Record<string, Float32Array>) {
        if (!this.valid) return true;

        const channels = outputs[0]
        const blockSize = outputs[0][0].length;

        let samplesAvailable = Atomics.load(this.controlBuffer, CTL_SAMPLES_AVAIL_IDX);
        if (samplesAvailable < blockSize) {
            return true
        }

        if (samplesAvailable >= blockSize) {
            let readPointer = Atomics.load(this.controlBuffer, CTL_READ_IDX);
            const spaceToEnd = this.maxAudioBufferSamples - readPointer;

            if (blockSize <= spaceToEnd) {
                for (let i = 0; i < blockSize; i++) {
                    for (let channel_idx = 0; channel_idx < channels.length; channel_idx++) {
                        channels[channel_idx][i] = this.audioBuffer[readPointer + i]
                    }
                }
                readPointer += blockSize;
            } else {
                for (let i = 0; i < spaceToEnd; i++) {
                    for (let channel_idx = 0; channel_idx < channels.length; channel_idx++) {
                        channels[channel_idx][i] = this.audioBuffer[readPointer + i]
                    }
                }
                const remaining = blockSize - spaceToEnd
                for (let i = spaceToEnd; i < blockSize; i++) {
                    for (let channel_idx = 0; channel_idx < channels.length; channel_idx++) {
                        channels[channel_idx][i] = this.audioBuffer[readPointer + i]
                    }
                }
                readPointer = remaining;
            }

            if (readPointer === this.maxAudioBufferSamples) {
                readPointer = 0;
            }

            Atomics.store(this.controlBuffer, CTL_READ_IDX, readPointer);
            Atomics.sub(this.controlBuffer, CTL_SAMPLES_AVAIL_IDX, blockSize);
            samplesAvailable -= blockSize;
        }

        if (!this.isSignalingPause && samplesAvailable > this.HIGH_WATERMARK_SAMPLES) {
            console.warn(`[AudioWorklet] High watermark reached (${samplesAvailable} > ${this.HIGH_WATERMARK_SAMPLES}). Requesting PAUSE.`);
            this.sendControlMessage('pause_sending');
            this.isSignalingPause = true;
        }
        else if (this.isSignalingPause && samplesAvailable < this.LOW_WATERMARK_SAMPLES) {
            console.log(`[AudioWorklet] Low watermark reached (${samplesAvailable} < ${this.LOW_WATERMARK_SAMPLES}). Requesting RESUME.`);
            this.sendControlMessage('resume_sending');
            this.isSignalingPause = false;
        }

        return true;
    }
}

registerProcessor('audio-processor', SharedAudioProcessor);