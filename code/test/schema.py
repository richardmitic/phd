from typing import Any, Annotated
from pydantic import BaseModel, Discriminator, Tag

class StftConfig(BaseModel):
    frame_size: int = 1024
    hop_size: int = 512

class ChunkingConfig(BaseModel):
    chunk_length: float = 10.
    hop_length: float = 5.

class AudioChunk(BaseModel):
    start: float = 0.
    duration: float = 30.

class TimeFrequencyChunk(AudioChunk):
    stft_config: StftConfig = StftConfig()

class AudioChunks(AudioChunk):
    chunking_config: ChunkingConfig = ChunkingConfig()

class TimeFrequencyChunks(AudioChunk):
    chunking_config: ChunkingConfig = ChunkingConfig()
    stft_config: StftConfig = StftConfig()


def get_discriminator_value(v: Any) -> str:
    if isinstance(v, dict):
        if "chunking_config" in v and "stft_config" in v:
            return "tf_chunks"
        elif "chunking_config" in v and "stft_config" not in v:
            return "audio_chunks"
        elif "chunking_config" not in v and "stft_config" in v:
            return "tf_chunk"
        else:
            return "audio_chunk"
    else:
        if hasattr(v, "chunking_config") and hasattr(v, "stft_config"):
            return "tf_chunks"
        elif hasattr(v, "chunking_config") and not hasattr(v, "stft_config"):
            return "audio_chunks"
        elif not hasattr(v, "chunking_config") and hasattr(v, "stft_config"):
            return "tf_chunk"
        else:
            return "audio_chunk" 


class AudioConfig(BaseModel):
    config: Annotated[
        (
            Annotated[AudioChunk, Tag("audio_chunk")] |
            Annotated[AudioChunks, Tag("audio_chunks")] |
            Annotated[TimeFrequencyChunk, Tag("tf_chunk")] |
            Annotated[TimeFrequencyChunks, Tag("tf_chunks")] 
        ),
        Discriminator(get_discriminator_value)
    ]

chunk = AudioConfig.model_validate({"config": {
    'start': 0.0,
    'duration': 30.0
}})
tf = AudioConfig.model_validate({"config": {
    'start': 0.0,
    'duration': 30.0,
    "stft_config": {"frame_size": 1024, "hop_size": 512},
}})
chunks = AudioConfig.model_validate({"config": {
    'start': 0.0,
    'duration': 30.0,
    "chunking_config": {"chunk_length": 10., "hop_length": 5.}
}})
tfs = AudioConfig.model_validate({"config": {
    'start': 0.0,
    'duration': 30.0,
    "chunking_config": {"chunk_length": 10., "hop_length": 5.},
    "stft_config": {"frame_size": 1024, "hop_size": 512},
}})
print(chunk)
print(tf)
print(chunks)
print(tfs)

print(chunk.model_dump_json())
print(tf.model_dump_json())
print(chunks.model_dump_json())
print(tfs.model_dump_json())