# Сборка ядра в sidecar (S-13.1, ADR-0019). Запуск: uv run python packaging/build_sidecar.py
# Каталог, а не один файл: один файл распаковывал бы torch при каждом старте (NFR-07).
from PyInstaller.utils.hooks import collect_all, copy_metadata

# Подключаются динамически: движки — реестром в bootstrap, плагины — по entry points.
COLLECTED = ["ctranslate2", "faster_whisper", "onnxruntime", "sqlite_vec", "tokenizers"]
# Плагины ставятся отдельными пакетами; в собранном приложении pip нет, поэтому они идут в комплекте.
PLUGINS = {
    "vtuber-obs": "vtuber_obs",
    "vtuber-stream-chat": "vtuber_stream_chat",
    "vtuber-stream-director": "vtuber_stream_director",
    "vtuber-tools": "vtuber_tools",
}
# torch.package внутри модели Silero импортирует модули стандартной библиотеки по имени.
SILERO_RUNTIME = ["torch.package", "unicodedata", "wave", "difflib", "html", "uuid"]

datas, binaries, hiddenimports = [], [], [*PLUGINS.values(), *SILERO_RUNTIME]
for package in COLLECTED:
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden
for distribution in PLUGINS:
    datas += copy_metadata(distribution)

analysis = Analysis(
    ["sidecar_main.py"],
    pathex=["../src"],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    # piper — GPL-3.0 (ADR-0013), в поставку не идёт; остальное — инструменты, а не рантайм.
    excludes=["piper", "tkinter", "matplotlib", "pytest", "IPython", "mypy", "hypothesis", "sympy"],
    noarchive=False,
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="vtuber-core",
    console=True,
    upx=False,
)
COLLECT(executable, analysis.binaries, analysis.datas, name="vtuber-core", upx=False)
