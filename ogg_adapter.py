from spleeter.audio.adapter import AudioAdapter
from spleeter.audio import Codec
from typing import Dict, Optional, Union
from pathlib import Path
import numpy as np
from spleeter.types import Signal
import pyogg
import scipy.signal

def resample(waveform, sourceRate, desiredRate):
    desiredSamples = round(waveform.shape[0]*desiredRate/sourceRate)
    return np.array([scipy.signal.resample(waveform[:,ch].flatten(), desiredSamples) for ch in range(waveform.shape[1])]).transpose()

class PyOggAudioAdapter(AudioAdapter):
    """
    An AudioAdapter implementation that uses the PyOgg library.
    
    Functionality depends on libraries available--for example, libogg and
    libvorbis. See PyOgg documentation for details.
    """
    
    def load(
        _,
        path: Union[Path, str],
        offset: Optional[float] = None,
        duration: Optional[float] = None,
        sample_rate: Optional[float] = None,
        dtype: np.dtype = np.float32,
    ) -> Signal:
        f = pyogg.VorbisFile(path)
        waveform = np.frombuffer(f.buffer, dtype="<i2").reshape(-1, f.channels).astype(np.float32)/32768.0
        if sample_rate is not None and sample_rate != f.frequency:
            waveform = resample(waveform, f.frequency, sample_rate)
        else:
            sample_rate = f.frequency
        if offset is not None:
            waveform = waveform[int(offset*sample_rate):]
        if duration is not None:
            waveform = waveform[:int(duration*sample_rate)]
        if not waveform.dtype == np.dtype(dtype):
            waveform = waveform.astype(dtype)
        return (waveform, sample_rate)
    
    def save(
        _,
        path: Union[Path, str],
        data: np.ndarray,
        sample_rate: float,
        codec: Codec = None,
        bitrate: str = None,
    ) -> None:
        if codec is not None and codec != "wav":
            raise NotImplementedError()
        import wave
        n_samples, n_channels = data.shape
        with wave.open(path, 'wb') as f:
            f.setnchannels(n_channels)
            f.setframerate(sample_rate)
            f.setnframes(n_samples)
            f.setsampwidth(2)
            f.writeframesraw((data*32768.0).clip(-32768, 32767).astype("<i2").tobytes())

