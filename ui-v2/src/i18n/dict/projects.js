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
  "Could not save the setting. Try again.": "Не удалось сохранить настройку. Повторите попытку.",

  // Project tiles, create-project form and the screen chrome. "Cancel" lives in the core dictionary.
  Back: "Назад",
  "Project name": "Название проекта",
  Create: "Создать",
  "New Project": "Новый проект",
  "That project name is unavailable.": "Это имя проекта недоступно.",
  "Could not create the project.": "Не удалось создать проект.",
  "Projects unavailable · {reason}": "Проекты недоступны · {reason}",
  "Projects unreachable": "Сервер проектов недоступен",
  Retry: "Повторить",
  member: "участник",
  active: "активный",
  "No projects yet · create one with New Project, or ask an owner for an invitation":
    "Проектов пока нет · создайте проект кнопкой «Новый проект» или попросите владельца о приглашении",
  "{n} node in graph": {
    one: "{n} узел в графе",
    few: "{n} узла в графе",
    many: "{n} узлов в графе",
    other: "{n} узла в графе"
  },
  "{n} project": {
    one: "{n} проект",
    few: "{n} проекта",
    many: "{n} проектов",
    other: "{n} проекта"
  },

  // Members panel: loading, invitation and removal
  "Members unavailable.": "Список участников недоступен.",
  "Could not remove the member.": "Не удалось исключить участника.",
  "Username to invite": "Имя пользователя для приглашения",
  "Send invitation": "Отправить приглашение",
  "Enter a username.": "Введите имя пользователя.",
  "Could not send the invitation.": "Не удалось отправить приглашение.",
  "{username} was added to {project} as {role}.": "{username} добавлен в проект {project} с ролью «{role}».",
  "Copy invite code": "Скопировать код приглашения",
  "Hide invite code": "Скрыть код приглашения",
  "Share this code with the invitee; it is shown once and expires in 72 hours.":
    "Передайте этот код приглашённому: он показывается один раз и действует 72 часа."
};

export const en = {
  "{n} node in graph": { one: "{n} node in graph", other: "{n} nodes in graph" },
  "{n} project": { one: "{n} project", other: "{n} projects" }
};
