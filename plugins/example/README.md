# vtuber-example

Плагин-пример. Руководство — `docs/plugins.md`.

```bash
uv pip install -e plugins/example
```

В `config/user.toml`:

```toml
[plugins]
enabled = ["example"]

[plugins.settings.example]
label = "мой стрим"
```
