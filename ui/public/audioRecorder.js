class RecordProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this._bufferSize = 4096;
        this._buffer = new Float32Array(this._bufferSize);
        this._initBuffer();
    }

    _initBuffer() {
        this._bytesWritten = 0;
    }

    _isBufferFull() {
        return this._bytesWritten === this._bufferSize;
    }

    _appendToBuffer(value) {
        if (this._isBufferFull()) {
            this._flush();
        }

        // Here _buffer is of type Float32Array
        this._buffer.set(value, this._bytesWritten);
        this._bytesWritten += value.length;
    }

    _flush() {
        let buffer = this._buffer;
        if (this._bytesWritten < this._bufferSize) {
            buffer = buffer.slice(0, this._bytesWritten);
        }

        this.port.postMessage({
            eventType: 'data',
            audioBuffer: buffer.buffer
        });

        this._initBuffer();
    }

    process(inputs, outputs, parameters) {
        const input0 = inputs[0];
        const inputChannel = input0[0];
        this._appendToBuffer(inputChannel);

        return true;
    }

}

registerProcessor('record-processor', RecordProcessor);