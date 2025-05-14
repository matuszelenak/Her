const INITIAL_BUFFER_SIZE = 8192 * 4;
const TARGET_LATENCY_SAMPLES = 4096 * 2;
const MAX_BUFFER_SIZE = 65536 * 16;

const HIGH_WATERMARK_SAMPLES = Math.floor(MAX_BUFFER_SIZE * 0.75);
const LOW_WATERMARK_SAMPLES = Math.floor(MAX_BUFFER_SIZE * 0.25);

class AudioProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super(options);

        this.buffer = new Float32Array(INITIAL_BUFFER_SIZE);
        this.bufferSize = INITIAL_BUFFER_SIZE;
        this.writeIndex = 0;
        this.readIndex = 0;
        this.samplesAvailable = 0;

        this.isPlaying = false;
        this.startedPlayback = false;

        // --- Flow Control State ---
        this.isBackendSendingPaused = false; // Track if we told the backend to pause

        this.port.onmessage = (event) => {
            // Handle incoming audio data from main thread
            const receivedSamples = event.data;
            if (receivedSamples instanceof Float32Array) {
                this.addToBuffer(receivedSamples);
            } else {
                // Ignore non-audio data (could be control messages *to* the worklet if needed)
                console.warn('[AudioWorklet] Received non-Float32Array data:', event.data);
            }
        };
    }

    // --- Helper to send control messages to main thread ---
    sendControlMessage(command) {
        this.port.postMessage({
            type: 'control',
            command: command // e.g., 'pause_sending', 'resume_sending'
        });
    }

    addToBuffer(samples) {
        // --- Resize buffer logic (same as before) ---
        if (this.samplesAvailable + samples.length > this.bufferSize) {
            if (this.bufferSize >= MAX_BUFFER_SIZE) {
                console.warn('[AudioWorklet] Buffer full, dropping samples.');
                // Send pause signal just in case it wasn't sent
                if (!this.isBackendSendingPaused) {
                    this.sendControlMessage('pause_sending');
                    this.isBackendSendingPaused = true;
                }
                return; // Drop incoming samples if max size reached
            }
            const newSize = Math.min(MAX_BUFFER_SIZE, Math.max(this.bufferSize * 2, this.samplesAvailable + samples.length));
            // ... (rest of resize logic is the same as before) ...
            console.log(`[AudioWorklet] Resizing buffer from ${this.bufferSize} to ${newSize}`);
            const newBuffer = new Float32Array(newSize);
            if (this.readIndex < this.writeIndex) {
                newBuffer.set(this.buffer.subarray(this.readIndex, this.writeIndex), 0);
            } else {
                const firstPart = this.buffer.subarray(this.readIndex);
                newBuffer.set(firstPart, 0);
                const secondPart = this.buffer.subarray(0, this.writeIndex);
                newBuffer.set(secondPart, firstPart.length);
            }
            this.buffer = newBuffer;
            this.bufferSize = newSize;
            this.readIndex = 0;
            this.writeIndex = this.samplesAvailable;
        }

        // --- Add samples to buffer (same as before) ---
        const spaceToEnd = this.bufferSize - this.writeIndex;
        if (samples.length <= spaceToEnd) {
            this.buffer.set(samples, this.writeIndex);
            this.writeIndex += samples.length;
        } else {
            const part1 = samples.subarray(0, spaceToEnd);
            this.buffer.set(part1, this.writeIndex);
            const part2 = samples.subarray(spaceToEnd);
            this.buffer.set(part2, 0);
            this.writeIndex = part2.length;
        }
        if (this.writeIndex === this.bufferSize) {
            this.writeIndex = 0;
        }
        this.samplesAvailable += samples.length;

        // --- Start playback logic (same as before) ---
        if (!this.startedPlayback && this.samplesAvailable >= TARGET_LATENCY_SAMPLES) {
            console.log('[AudioWorklet] Reached target buffer size, starting playback.');
            this.isPlaying = true;
            this.startedPlayback = true;
        }

        // --- Flow Control: Check High Watermark ---
        if (!this.isBackendSendingPaused && this.samplesAvailable > HIGH_WATERMARK_SAMPLES) {
            //console.warn(`[AudioWorklet] Buffer high watermark reached (${this.samplesAvailable} > ${HIGH_WATERMARK_SAMPLES}). Pausing backend sending.`);
            this.sendControlMessage('pause_sending');
            this.isBackendSendingPaused = true;
        }
    }

    process(inputs, outputs, parameters) {
        const outputChannel = outputs[0][0];
        const blockSize = outputChannel.length;

        if (!this.isPlaying) {
            outputChannel.fill(0);
            return true;
        }

        let processedSamples = 0;
        if (this.samplesAvailable >= blockSize) {
            // --- Copy data from buffer (same as before) ---
            const spaceToEnd = this.bufferSize - this.readIndex;
            if (blockSize <= spaceToEnd) {
                outputChannel.set(this.buffer.subarray(this.readIndex, this.readIndex + blockSize));
                this.readIndex += blockSize;
            } else {
                const part1 = this.buffer.subarray(this.readIndex);
                outputChannel.set(part1, 0);
                const remaining = blockSize - part1.length;
                const part2 = this.buffer.subarray(0, remaining);
                outputChannel.set(part2, part1.length);
                this.readIndex = remaining;
            }
            if (this.readIndex === this.bufferSize) {
                this.readIndex = 0;
            }
            this.samplesAvailable -= blockSize;
            processedSamples = blockSize;

        } else {
            // console.warn('[AudioWorklet] Buffer underrun!');
            outputChannel.fill(0);
        }

        if (this.isBackendSendingPaused && this.samplesAvailable < LOW_WATERMARK_SAMPLES) {
            // console.log(`[AudioWorklet] Buffer low watermark reached (${this.samplesAvailable} < ${LOW_WATERMARK_SAMPLES}). Resuming backend sending.`);
            this.sendControlMessage('resume_sending');
            this.isBackendSendingPaused = false;
        }

        return true;
    }
}


registerProcessor('audio-player', AudioProcessor);
