# MCP Setup — ручные шаги

Безопасность запрещает запись в `AppData` из этой сессии. Выполни эти 2 шага вручную:

## Шаг 1: Установить MCP extra

```bash
uv tool install --upgrade "graphifyy[mcp]"
```

Проверить:
```bash
python -c "from graphify.serve import serve; print('MCP OK')"
```

## Шаг 2: Добавить graphify в MCP-конфигурацию Claude Desktop

Открой файл: `C:\Users\Admin\AppData\Roaming\Claude\claude_desktop_config.json`

Найди секцию `"Perplexity": { ... }` и добавь после неё (не забудь запятую!):

```json
    "graphify": {
      "command": "C:\\Users\\Admin\\AppData\\Roaming\\uv\\tools\\graphifyy\\Scripts\\python.exe",
      "args": [
        "-m",
        "graphify.serve",
        "C:\\Users\\Admin\\source\\repos\\design-grammar-system\\graphify-out\\graph.json"
      ],
      "env": {}
    }
```

## Шаг 3: Перезапустить Claude Desktop/Code

После рестарта graphify MCP server будет доступен. Проверить:
```
Попроси Claude: "show me god nodes from the project graph"
```

---

Создано: 2026-06-22
