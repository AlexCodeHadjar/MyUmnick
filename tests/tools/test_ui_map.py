from pathlib import Path

from tools.gen_map import render
from tools.ui_map import first_comment, render_ui


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_ui(root: Path) -> Path:
    src = root / "ui" / "src"
    _write(
        src / "core" / "index.ts", '// Публичный API core.\nexport { Client } from "./client";\n'
    )
    _write(
        src / "core" / "client.ts",
        "/**\n * Клиент ядра.\n */\nimport x from 'y';\n\n"
        "/** Связь с ядром.\n *  Подробности. */\nexport class Client {}\n\n"
        "export const LIMIT = 16;\n"
        "// Не экспорт.\nconst hidden = 1;\n"
        "export async function connect(): Promise<void> {}\n"
        "export type { Other } from './other';\n",
    )
    _write(src / "core" / "client.test.ts", "export const notApi = 1;\n")
    _write(src / "core" / "protocol.gen.ts", "// Автогенерация.\nexport interface A {}\n")
    _write(src / "vite-env.d.ts", "/// <reference types='svelte' />\n")
    _write(
        src / "app" / "App.svelte",
        '<script lang="ts">\n  // Окно приложения.\n  import Chat from "./Chat.svelte";\n'
        "</script>\n",
    )
    return src


def test_sections_per_directory_with_index_summary(tmp_path: Path) -> None:
    text = "\n".join(render_ui(_make_ui(tmp_path), tmp_path))

    assert "## ui/src/core\nПубличный API core.\n" in text
    assert "## ui/src/app\n—\n" in text
    assert "## ui/src\n" not in text


def test_exports_with_first_jsdoc_line_and_location(tmp_path: Path) -> None:
    text = "\n".join(render_ui(_make_ui(tmp_path), tmp_path))

    assert "- `Client` — `ui/src/core/client.ts:8` — Связь с ядром." in text
    assert "- `LIMIT` — `ui/src/core/client.ts:10` — —" in text
    assert "- `connect` — `ui/src/core/client.ts:13` — Не экспорт." not in text
    assert "- `connect` — `ui/src/core/client.ts:13` — —" in text
    assert "hidden" not in text
    assert "Other" not in text


def test_components_and_generated_files_are_single_entries(tmp_path: Path) -> None:
    text = "\n".join(render_ui(_make_ui(tmp_path), tmp_path))

    assert "- `App.svelte` — `ui/src/app/App.svelte:1` — Окно приложения." in text
    assert "- `protocol.gen.ts` — `ui/src/core/protocol.gen.ts:1` — Автогенерация." in text
    assert "`A`" not in text


def test_tests_and_ambient_declarations_are_skipped(tmp_path: Path) -> None:
    text = "\n".join(render_ui(_make_ui(tmp_path), tmp_path))

    assert "notApi" not in text
    assert "vite-env" not in text


def test_first_comment_stops_at_code() -> None:
    assert first_comment(["", "import x from 'y';", "// поздно"]) == "—"
    assert first_comment(["/**", " * ", " * Текст.", " */"]) == "Текст."
    assert first_comment([]) == "—"


def test_project_map_includes_ui_after_core(tmp_path: Path) -> None:
    core = tmp_path / "src" / "pkg"
    _write(core / "__init__.py", '"""Ядро."""\n')
    text = render(core, tmp_path, _make_ui(tmp_path))

    assert text.index("## src/pkg") < text.index("## ui/src/app")
    assert text.endswith("\n")
    assert render(core, tmp_path, tmp_path / "нет") == render(core, tmp_path)
