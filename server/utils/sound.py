import numpy as np
from scipy import signal


def resample_chunk(audio_chunk_np, original_sr, target_sr):
    num_samples_original = len(audio_chunk_np)
    if num_samples_original == 0: return audio_chunk_np
    num_samples_target = round(num_samples_original * (target_sr / original_sr))
    if num_samples_target <= 0: return np.array([], dtype=np.float32)
    resampled_chunk = signal.resample(audio_chunk_np, num_samples_target)
    return resampled_chunk.astype(np.float32)
