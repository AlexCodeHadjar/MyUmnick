"""Сравнение клонирования голоса по образцам (scripts/remote/README.md, раздел о голосе).

Не часть приложения: движки стоят в отдельных окружениях на арендованном сервере, в зависимости
проекта не входят. ADR и адаптер появятся, когда голос будет выбран на слух (ADR-0014).

Шаги: prepare (выровнять громкость, распознать текст образцов), synth (один движок на запуск,
у движков несовместимые версии torch), index (страница для прослушивания).
"""

# Разовый скрипт сервера: движки импортируются внутри функций, каждый есть только в своём окружении.
# ruff: noqa: INP001, D103, PLC0415, T201, E501

from __future__ import annotations

import argparse
import json
import shutil
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


PAGE = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Голоса по образцу</title><style>
:root{color-scheme:light dark;--bg:#f6f6f4;--card:#fff;--text:#1d1d1b;--dim:#6b6b66;--line:#ddddd8;--on:#2f6f5e}
@media (prefers-color-scheme:dark){:root{--bg:#181817;--card:#232322;--text:#ececea;--dim:#a0a09a;
--line:#3a3a37;--on:#6fc3aa}}
body{margin:0;padding:20px 16px 60px;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,sans-serif}
main{max-width:1280px;margin:auto}h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:26px 0 8px}
.dim{color:var(--dim);font-size:13px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%}
th,td{border:1px solid var(--line);padding:8px;text-align:left;vertical-align:top;background:var(--card)}
th{font-weight:600}td.n{font-variant-numeric:tabular-nums}audio{width:210px;height:34px;display:block}
.tabs{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 6px}
button{font:inherit;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:6px;
padding:6px 10px;cursor:pointer}button[aria-pressed=true]{border-color:var(--on);color:var(--on);font-weight:600}
.say{font-size:16px;margin:8px 0 12px}.row{display:flex;align-items:center;gap:8px;margin-top:4px}
#picks li{margin:6px 0}</style></head><body><main>
<h1>Голоса по образцу</h1><p class="dim">Сравните один столбец и одну строку: столбец — движок, строка — образец.
Скорость ориентировочная: движки работали одновременно.</p><h2>Движки</h2><div class="scroll"><table id="sum"></table></div>
<h2>Прослушивание</h2><div class="tabs" id="tabs"></div><p class="say" id="say"></p>
<div class="scroll"><table id="grid"></table></div><h2>Отмеченные ★</h2><ul id="picks"></ul><p class="dim" id="none">
Пока ничего. Отметьте понравившиеся записи: метки хранятся только в этом браузере.</p></main><script>
const ROWS=__ROWS__,TEXT=__TEXT__,REFS=__REFS__;const KEY="clone-picks";
const uniq=f=>[...new Set(ROWS.map(f))].sort(),med=a=>{a=[...a].sort((x,y)=>x-y);return a[a.length>>1]};
const engines=uniq(r=>r.engine),refs=uniq(r=>r.ref),phrases=uniq(r=>r.phrase);let cur=phrases[0],picks=[];
try{picks=JSON.parse(localStorage.getItem(KEY))||[]}catch(e){}
const el=(t,p={},...c)=>{const n=Object.assign(document.createElement(t),p);n.append(...c);return n};
const audio=src=>{const a=el("audio",{controls:true,preload:"none",src});a.onplay=()=>document.querySelectorAll("audio")
.forEach(o=>{if(o!==a)o.pause()});return a};
function save(){try{localStorage.setItem(KEY,JSON.stringify(picks))}catch(e){}}
function star(f){const b=el("button",{textContent:"★"});b.setAttribute("aria-pressed",picks.includes(f));b.title="Отметить";
b.onclick=()=>{picks=picks.includes(f)?picks.filter(x=>x!==f):[...picks,f];save();draw()};return b}
function draw(){tabs.replaceChildren(...phrases.map(p=>{const b=el("button",{textContent:p.replace(/^\\d_/,"")});
b.setAttribute("aria-pressed",p===cur);b.onclick=()=>{cur=p;draw()};return b}));say.textContent="«"+TEXT[cur]+"»";
grid.replaceChildren(el("tr",{},el("th",{textContent:"Образец"}),...engines.map(e=>el("th",{textContent:e}))),...refs.map(r=>
el("tr",{},el("td",{},el("div",{textContent:r.replace(".wav","")}),REFS?audio("refs/"+r):""),...engines.map(e=>{
const x=ROWS.find(o=>o.engine===e&&o.ref===r&&o.phrase===cur);return x?el("td",{},audio(x.file),el("div",{className:"row"},
star(x.file),el("span",{className:"dim",textContent:"синтез "+x.synth_s+" с"}))):el("td",{textContent:"нет"})}))));
pl.replaceChildren(...picks.map(f=>el("li",{},f.replace(".wav","")+" ",audio(f))));none.hidden=picks.length>0}
sum.append(el("tr",{},...["Движок","RTF, медиана","Короткая фраза, с","VRAM, ГБ","Записей"].map(t=>el("th",{textContent:t}))),
...engines.map(e=>{const v=ROWS.filter(r=>r.engine===e),s=v.filter(r=>r.phrase===phrases[0]);return el("tr",{},el("td",{textContent:e}),
...[med(v.map(r=>r.rtf)),med(s.map(r=>r.synth_s)),Math.max(...v.map(r=>r.vram_gb)),v.length].map(t=>el("td",{className:"n",textContent:t})))}));
const tabs=document.getElementById("tabs"),say=document.getElementById("say"),grid=document.getElementById("grid"),
pl=document.getElementById("picks"),none=document.getElementById("none");draw();
</script></body></html>
"""


def index(out: Path, prepared: Path | None = None) -> None:
    rows = [
        json.loads(line)
        for line in (out / RESULTS_FILE).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if prepared:  # копия рядом со страницей: так образец и запись сравниваются на одном экране
        (out / "refs").mkdir(exist_ok=True)
        for path in prepared.glob("*.wav"):
            shutil.copyfile(path, out / "refs" / path.name)
    data = {
        "__ROWS__": rows,
        "__TEXT__": PHRASES,
        "__REFS__": bool(prepared),
    }
    page = PAGE
    for key, value in data.items():
        # `</` в данных закрыл бы тег script, а имена файлов приходят с сервера.
        page = page.replace(key, json.dumps(value, ensure_ascii=False).replace("</", "<\\/"))
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
    step.add_argument("--prepared", type=Path)
    args = parser.parse_args()
    if args.step == "prepare":
        prepare(args.src, args.whisper)
    elif args.step == "synth":
        synth(args.engine, args.prepared, args.out)
    else:
        index(args.out, args.prepared)


if __name__ == "__main__":
    main()
