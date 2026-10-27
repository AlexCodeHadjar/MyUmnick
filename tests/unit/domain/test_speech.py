from vtuber.domain import SAMPLE_WIDTH_BYTES, AudioChunk, AudioFormat


def test_bytes_per_second_is_rate_times_sample_width() -> None:
    assert AudioFormat(sample_rate=24000).bytes_per_second == 24000 * SAMPLE_WIDTH_BYTES


def test_chunk_duration_follows_its_format() -> None:
    one_second = bytes(AudioFormat(sample_rate=24000).bytes_per_second)

    assert AudioChunk(AudioFormat(24000), one_second).duration_s == 1.0
    assert AudioChunk(AudioFormat(48000), one_second).duration_s == 0.5


def test_formats_with_same_rate_are_equal() -> None:
    assert AudioFormat(22050) == AudioFormat(22050)
    assert AudioFormat(22050) != AudioFormat(24000)
