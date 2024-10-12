

class PlaybackProcessor extends AudioWorkletProcessor {

    constructor() {
        super();
        this._cursor = 0;
        this._bufferSize = 262144 * 4;
        this._sharedBufferOne = new SharedArrayBuffer(this._bufferSize);
        this._sharedViewOne = new Float32Array(this._sharedBufferOne);
        this._producerCursor = 0
        this.port.postMessage({
            eventType: 'buffer',
            buffer: this._sharedBufferOne
        });
        this.port.onmessage = (e) => {
            this._producerCursor = e.data
        }
    }

    process(inputs, outputs) {
        if (this._cursor === this._producerCursor) {
            for (let i = 0; i < outputs[0][0].length; i++) {
                outputs[0][0][i] = 0
            }
            return true
        }
        for (let i = 0; i < outputs[0][0].length; i++) {
            outputs[0][0][i] = this._sharedViewOne[this._cursor + i]
        }
        this._cursor = (this._cursor + outputs[0][0].length) % this._sharedViewOne.length
        if (this._cursor % (4096) === 0) {
            this.port.postMessage(this._cursor)
        }
        return true
    }
}

registerProcessor('playback-processor', PlaybackProcessor);
