"""Сравнение клонирования голоса по образцам (scripts/remote/README.md, раздел о голосе).

Не часть приложения: движки стоят в отдельных окружениях на арендованном сервере, в зависимости
проекта не входят. ADR и адаптер появятся, когда голос будет выбран на слух (ADR-0014).

Шаги: prepare (выровнять громкость, распознать текст образцов), synth (один движок на запуск,
у движков несовместимые версии torch), index (страница для прослушивания).
"""

# Разовый скрипт сервера: движки импортируются внутри функций, каждый есть только в своём окружении.
# ruff: noqa: INP001, D103, PLC0415, T201

from __future__ import annotations

import argparse
import html
import json
import time
import wave
from collections.abc import Callable
from pathlib import Path

PEAK = 0.89  # −1 дБFS: образцы тихие и разной громкости, перегруз при этом не появляется
REFS_FILE = "refs.json"
RESULTS_FILE = "results.jsonl"

PHRASES = {
    "1_korotko": "Хм, интересно.",  # без потокового режима это и есть задержка первой фразы
    "2_privet": "Привет! Я рада, что ты заглянул. Как прошёл твой день?",
    "3_emocii": "Нет, правда? Вот это да! Ни за что бы не подумала, что так получится!",
    "4_dlinno": "Знаешь, вчера я весь вечер читала про лекарственные травы, "
    "и теперь могу рассказать, чем ромашка отличается от пижмы.",
}


def normalized(path: Path, out: Path) -> None:
    import numpy as np

    with wave.open(str(path)) as src:
        params = src.getparams()
        samples = np.frombuffer(src.readframes(params.nframes), dtype=np.int16)
    gain = PEAK * 32767 / max(1, int(np.abs(samples.astype(np.int32)).max()))
    with wave.open(str(out), "wb") as dst:
        dst.setparams(params)
        dst.writeframes((samples * gain).astype(np.int16).tobytes())


def whisper_input(path: Path) -> object:
    """16 кГц float32: Whisper получает готовый массив, без декодера PyAV."""
    import numpy as np

    with wave.open(str(path)) as src:
        rate, frames = src.getframerate(), src.readframes(src.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768
    positions = np.arange(0, len(samples), rate / 16000)
    return np.interp(positions, np.arange(len(samples)), samples).astype(np.float32)


def prepare(src: Path, whisper: str) -> None:
    from faster_whisper import WhisperModel

    out = src / "prepared"
    out.mkdir(exist_ok=True)
    model = WhisperModel(whisper, device="cpu", compute_type="int8")
    refs: dict[str, str] = {}
    for path in sorted(src.glob("*.wav")):
        normalized(path, out / path.name)
        segments, _ = model.transcribe(whisper_input(out / path.name), language="ru")
        refs[path.name] = " ".join(s.text.strip() for s in segments)
        print(path.name, refs[path.name], flush=True)
    text = json.dumps(refs, ensure_ascii=False, indent=2)
    (out / REFS_FILE).write_text(text + "\n", encoding="utf-8")


Synth = Callable[[str, Path, str], tuple[object, int]]


def qwen(size: str) -> Synth:
    import torch
    from qwen_tts import Qwen3TTSModel

    model = Qwen3TTSModel.from_pretrained(
        f"Qwen/Qwen3-TTS-12Hz-{size}-Base", device_map="cuda:0", dtype=torch.bfloat16
    )

    def run(text: str, ref: Path, ref_text: str) -> tuple[object, int]:
        wavs, rate = model.generate_voice_clone(
            text=text, language="Russian", ref_audio=str(ref), ref_text=ref_text
        )
        return wavs[0], rate

    return run


def omni() -> Synth:
    import torch
    from omnivoice import OmniVoice

    model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cuda:0", dtype=torch.float16)

    def run(text: str, ref: Path, ref_text: str) -> tuple[object, int]:
        wavs = model.generate(text=text, language="Russian", ref_audio=str(ref), ref_text=ref_text)
        return wavs[0], 24000

    return run


def chatterbox() -> Synth:
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")

    def run(text: str, ref: Path, _ref_text: str) -> tuple[object, int]:
        wav = model.generate(text, language_id="ru", audio_prompt_path=str(ref))
        return wav.squeeze().cpu().numpy(), model.sr

    return run


ENGINES: dict[str, Callable[[], Synth]] = {
    "qwen0.6": lambda: qwen("0.6B"),
    "qwen1.7": lambda: qwen("1.7B"),
    "omni": omni,
    "chatterbox": chatterbox,
}


def synth(engine: str, prepared: Path, out: Path) -> None:
    import soundfile as sf
    import torch

    out.mkdir(parents=True, exist_ok=True)
    refs: dict[str, str] = json.loads((prepared / REFS_FILE).read_text(encoding="utf-8"))
    started = time.perf_counter()
    run = ENGINES[engine]()
    load_s = round(time.perf_counter() - started, 1)
    for ref, ref_text in refs.items():
        for key, text in PHRASES.items():
            name = f"{engine}__{Path(ref).stem}__{key}.wav"
            if (out / name).exists():  # сервер может пропасть: повторный запуск докачивает
                continue
            begin = time.perf_counter()
            audio, rate = run(text, prepared / ref, ref_text)
            spent = time.perf_counter() - begin
            sf.write(out / name, audio, rate)
            seconds = sf.info(out / name).duration
            row = {
                "file": name,
                "engine": engine,
                "ref": ref,
                "phrase": key,
                "load_s": load_s,
                "synth_s": round(spent, 2),
                "audio_s": round(seconds, 2),
                "rtf": round(spent / seconds, 3),
                "vram_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
            }
            with (out / RESULTS_FILE).open("a", encoding="utf-8") as results:
                results.write(json.dumps(row) + "\n")
            print(row, flush=True)


def index(out: Path) -> None:
    rows = [
        json.loads(line)
        for line in (out / RESULTS_FILE).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cells = []
    for row in sorted(rows, key=lambda r: (r["phrase"], r["ref"], r["engine"])):
        name = html.escape(row["file"], quote=True)
        cells.append(
            f"<tr><td>{html.escape(row['phrase'])}</td><td>{html.escape(row['ref'])}</td>"
            f"<td>{html.escape(row['engine'])}</td><td>{row['synth_s']}</td><td>{row['rtf']}</td>"
            f"<td>{row['vram_gb']}</td>"
            f'<td><audio controls preload="none" src="{name}"></audio></td></tr>'
        )
    page = (
        '<!doctype html><meta charset="utf-8"><title>Клонирование голоса</title>'
        "<table border=1 cellpadding=4><tr><th>Фраза<th>Образец<th>Движок<th>Синтез, с<th>RTF"
        "<th>VRAM, ГБ<th>Звук</tr>" + "".join(cells) + "</table>"
    )
    (out / "index.html").write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    steps = parser.add_subparsers(dest="step", required=True)
    step = steps.add_parser("prepare")
    step.add_argument("src", type=Path)
    step.add_argument("--whisper", default="large-v3-turbo")
    step = steps.add_parser("synth")
    step.add_argument("engine", choices=sorted(ENGINES))
    step.add_argument("prepared", type=Path)
    step.add_argument("out", type=Path)
    step = steps.add_parser("index")
    step.add_argument("out", type=Path)
    args = parser.parse_args()
    if args.step == "prepare":
        prepare(args.src, args.whisper)
    elif args.step == "synth":
        synth(args.engine, args.prepared, args.out)
    else:
        index(args.out)


if __name__ == "__main__":
    main()
