const CTL_READ_IDX = 1;
const CTL_SAMPLES_AVAIL_IDX = 2;
const CTL_WORKLET_WAITING_IDX = 3;

let HIGH_WATERMARK_SAMPLES;
let LOW_WATERMARK_SAMPLES;

class SharedAudioProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super(options);

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
        // Initialize watermarks based on the actual buffer size passed
        HIGH_WATERMARK_SAMPLES = Math.floor(this.maxAudioBufferSamples * 0.75);
        LOW_WATERMARK_SAMPLES = Math.floor(this.maxAudioBufferSamples * 0.25);

        this.isSignalingPause = false;

        console.log(`[AudioWorklet] Initialized. Audio buffer: ${this.maxAudioBufferSamples} samples. HW: ${HIGH_WATERMARK_SAMPLES}, LW: ${LOW_WATERMARK_SAMPLES}`);
        this.valid = true;
        this.port.postMessage({ type: 'worklet_ready' });
    }

    sendControlMessage(command) {
        this.port.postMessage({
            type: 'control',
            command: command
        });
    }

    process(inputs, outputs, parameters) {
        if (!this.valid) return true; // Keep alive but do nothing if SABs were not provided

        const outputChannel = outputs[0][0]; // Assume mono output
        const blockSize = outputChannel.length; // Typically 128

        // Load current samples available from shared memory
        let samplesAvailable = Atomics.load(this.controlBuffer, CTL_SAMPLES_AVAIL_IDX);

        // If not enough samples, wait for main thread to produce more
        if (samplesAvailable < blockSize) {
            // console.warn(`[AudioWorklet] Not enough samples available to processor!`);
            return true
        }

        // If enough samples are available (either initially or after waiting)
        if (samplesAvailable >= blockSize) {
            let readPointer = Atomics.load(this.controlBuffer, CTL_READ_IDX);
            const spaceToEnd = this.maxAudioBufferSamples - readPointer;

            // Copy data from shared audio buffer to output channel
            if (blockSize <= spaceToEnd) {
                // No wrap-around needed for reading this block
                outputChannel.set(this.audioBuffer.subarray(readPointer, readPointer + blockSize));
                readPointer += blockSize;
            } else {
                // Reading this block requires wrap-around
                const part1 = this.audioBuffer.subarray(readPointer); // from readPointer to end
                outputChannel.set(part1, 0);
                const remaining = blockSize - part1.length;
                const part2 = this.audioBuffer.subarray(0, remaining); // from start
                outputChannel.set(part2, part1.length);
                readPointer = remaining;
            }

            // Handle wrap-around for readPointer if it exactly hit the end
            if (readPointer === this.maxAudioBufferSamples) {
                readPointer = 0;
            }

            Atomics.store(this.controlBuffer, CTL_READ_IDX, readPointer);
            Atomics.sub(this.controlBuffer, CTL_SAMPLES_AVAIL_IDX, blockSize); // Atomically subtract processed samples
            samplesAvailable -= blockSize; // Update local copy for watermark checks this cycle
        }


        // --- Flow Control Logic (using local 'samplesAvailable' after potential read) ---
        // Check high watermark: if buffer is getting too full, request main thread to pause backend
        if (!this.isSignalingPause && samplesAvailable > HIGH_WATERMARK_SAMPLES) {
            console.warn(`[AudioWorklet] High watermark reached (${samplesAvailable} > ${HIGH_WATERMARK_SAMPLES}). Requesting PAUSE.`);
            this.sendControlMessage('pause_sending');
            // The main thread will poll this flag.
            this.isSignalingPause = true;
        }
        // Check low watermark: if buffer was paused and now has enough room, request main thread to resume
        else if (this.isSignalingPause && samplesAvailable < LOW_WATERMARK_SAMPLES) {
            console.log(`[AudioWorklet] Low watermark reached (${samplesAvailable} < ${LOW_WATERMARK_SAMPLES}). Requesting RESUME.`);
            this.sendControlMessage('resume_sending');
            this.isSignalingPause = false;
        }

        return true;
    }
}

registerProcessor('audio-processor', SharedAudioProcessor);