// projects area dictionary. `ru` maps English text (the key) to Russian; `en` holds only tp() plural tables
// (English is otherwise the key). Wording follows 1308-UI-SPEC and the 1301-D38 glossary; project names and
// usernames are data and never pass through here (D-13).
export const ru = {
  // Members panel (D-16)
  "Members · {project}": "Участники · {project}",
  "Role of {username}": "Роль пользователя {username}",
  "Remove member": "Исключить участника",
  "No members listed": "Участники не указаны",
  "A project must keep at least one owner. Promote another member first.":
    "В проекте должен остаться хотя бы один владелец. Сначала назначьте другого владельца.",
  "Role updated for {username}": "Роль пользователя {username} изменена",
  "You will no longer be able to manage members of this project.":
    "Вы больше не сможете управлять участниками этого проекта.",
  "Change role": "Изменить роль",
  "Keep my role": "Оставить мою роль",
  "Could not change the role. Try again.": "Не удалось изменить роль. Повторите попытку.",

  // Project settings panel, DG admin only (D-17). The confirm button reads differently from the toggle label in
  // Russian, so it carries the "confirm" context (tc).
  "Project settings · {project}": "Настройки проекта · {project}",
  "Visible to DG admins only.": "Видно только администраторам DG.",
  "Allow provider export": "Разрешить экспорт провайдеру",
  "DeGram may send this project's data to the LLM provider. On by default.":
    "DeGram может передавать данные этого проекта провайдеру LLM. По умолчанию включено.",
  "Allow whole-definition export": "Разрешить экспорт определения целиком",
  "Lets DeGram request the complete Grasshopper definition. Each request still needs its own consent. Off by default.":
    "Позволяет DeGram запрашивать определение Grasshopper целиком. Каждый запрос по-прежнему требует отдельного согласия. По умолчанию выключено.",
  "Allow whole-definition export for {project}? DeGram will be able to request the entire definition, each time with your consent.":
    "Разрешить экспорт определения целиком для проекта {project}? DeGram сможет запрашивать определение целиком, каждый раз с согласия пользователя.",
  "confirm\u0004Allow whole-definition export": "Разрешить экспорт целиком",
  "Keep export off": "Оставить выключенным",
  "Loading settings…": "Загрузка настроек…",
  "Could not load project settings.": "Не удалось загрузить настройки проекта.",
  "Retry loading settings": "Повторить загрузку настроек",
  "Project settings saved": "Настройки проекта сохранены",
  "Could not save the setting. Try again.": "Не удалось сохранить настройку. Повторите попытку."
};

export const en = {};
