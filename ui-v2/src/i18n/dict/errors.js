// Server error texts keyed by the API `code` (D-09). describeError(err) looks up `error.<CODE>` first and falls
// back to the server text. Both languages are listed because the English server text is not the key here.
export const en = {
  "error.AUTH_FAILED": "Incorrect username or password. Check your credentials and try again.",
  "error.INVITE_INVALID": "This invitation is not valid. Ask a project owner for a new invitation.",
  "error.PASSWORD_POLICY": "The password does not meet the password policy.",
  "error.REGISTRATION_INVALID": "Registration could not be completed. Choose a different username or password and try again.",
  "error.PROJECT_NAME_UNAVAILABLE": "That project name is unavailable. Choose a different project name.",
  "error.PROJECT_FORBIDDEN": "You do not have permission to change roles in this project.",
  "error.LAST_OWNER": "A project must keep at least one owner. Promote another member first.",
  "error.MEMBER_NOT_FOUND": "That user is not a member of this project. Reload the list and try again.",
  "error.ROLE_INVALID": "That role is not valid. Choose Viewer, Editor or Owner.",
  "error.ADMIN_REQUIRED": "Only a DG admin can change project settings.",
  "error.CONNECTOR_ACCESS_REQUIRED": "Connector access is required. Ask a project owner to grant it.",
  "error.ACCESS_EXISTS": "This member already has access.",
  "error.NOT_A_MEMBER": "That user is not a member of this project.",
  "error.DEGRAM_POLICY_INVALID": "Choose a setting to change.",
  "error.CONNECTOR_TOKENS_RETIRED": "Connector tokens are retired. Sign in with your DG account.",
  // Phase 1303 mapping routes (1303-API-CONTRACT §2)
  "error.MAPPING_SESSION_NOT_FOUND": "This mapping session was not found. Refresh the list and try again.",
  "error.MAPPING_QUESTION_NOT_FOUND": "This question is no longer open. Refresh the session and answer the current questions.",
  "error.MAPPING_OPTION_INVALID": "That answer is not valid for this question. Refresh the session and choose again.",
  "error.MAPPING_INPUT_INVALID": "The mapping request is not valid. Check the descriptor file and try again.",
  "error.MAPPING_TOO_MANY_ELEMENTS": "Too many elements for one session. Send at most 5000 elements."
};

export const ru = {
  "error.AUTH_FAILED": "Неверное имя пользователя или пароль. Проверьте данные и повторите попытку.",
  "error.INVITE_INVALID": "Приглашение недействительно. Попросите владельца проекта выдать новое.",
  "error.PASSWORD_POLICY": "Пароль не соответствует требованиям к паролю.",
  "error.REGISTRATION_INVALID": "Не удалось завершить регистрацию. Выберите другое имя пользователя или пароль и повторите попытку.",
  "error.PROJECT_NAME_UNAVAILABLE": "Это имя проекта недоступно. Выберите другое имя проекта.",
  "error.PROJECT_FORBIDDEN": "Нет прав на изменение ролей в этом проекте.",
  "error.LAST_OWNER": "В проекте должен остаться хотя бы один владелец. Сначала назначьте другого владельца.",
  "error.MEMBER_NOT_FOUND": "Этот пользователь не участвует в проекте. Обновите список и повторите.",
  "error.ROLE_INVALID": "Недопустимая роль. Выберите «Наблюдатель», «Редактор» или «Владелец».",
  "error.ADMIN_REQUIRED": "Менять настройки проекта может только администратор DG.",
  "error.CONNECTOR_ACCESS_REQUIRED": "Нужен доступ к коннектору. Попросите владельца проекта выдать его.",
  "error.ACCESS_EXISTS": "У этого участника уже есть доступ.",
  "error.NOT_A_MEMBER": "Этот пользователь не участвует в проекте.",
  "error.DEGRAM_POLICY_INVALID": "Выберите настройку для изменения.",
  "error.CONNECTOR_TOKENS_RETIRED": "Токены коннекторов больше не используются. Войдите под своей учётной записью DG.",
  "error.MAPPING_SESSION_NOT_FOUND": "Сессия меппинга не найдена. Обновите список и повторите попытку.",
  "error.MAPPING_QUESTION_NOT_FOUND": "Этот вопрос уже закрыт. Обновите сессию и ответьте на текущие вопросы.",
  "error.MAPPING_OPTION_INVALID": "Этот ответ недопустим для данного вопроса. Обновите сессию и выберите снова.",
  "error.MAPPING_INPUT_INVALID": "Запрос меппинга недопустим. Проверьте файл дескрипторов и повторите попытку.",
  "error.MAPPING_TOO_MANY_ELEMENTS": "Слишком много элементов для одной сессии. Отправьте не более 5000 элементов."
};
