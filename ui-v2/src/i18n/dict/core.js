// Core dictionary: owner-fixed strings (D-03) and the shared chrome every screen uses.
// `ru` maps English text (the key) to Russian; a plural entry is an object of Intl.PluralRules forms.
// `en` carries only entries whose English is not the key (error.* codes and tp() plural tables).
// Wording follows the 1301-D38 glossary; proper nouns stay Latin (D-13).
export const ru = {
  "Design Grammars.": "Грамматика.",
  "Encode your design intent.": "Граф правил проекта.",
  "System initiated": "Система инициализирована",
  Viewer: "Наблюдатель",
  Editor: "Редактор",
  Owner: "Владелец",
  On: "Вкл",
  Off: "Выкл",
  "Never connected": "Не подключался",

  // Landing region labels and hint (D-21: «AI Engine» is now «LLM model»)
  "Graph Viewer": "Просмотр графа",
  "Model Viewer": "Просмотр модели",
  "Projects.": "Проекты.",
  "LLM model": "Модель LLM",
  Connectors: "Коннекторы",
  Reasoner: "Ризонер",
  "DG API Docs": "Документация API",
  "Select a region": "Выберите раздел",

  // Landing boot line, sign-in card and host controls
  "Select the project": "Выберите проект",
  "Log in": "Войти",
  "Sign out": "Выйти",
  Access: "Доступ",
  "Welcome back": "С возвращением",
  "Enter your credentials to access Design Grammars.": "Введите данные для входа в Грамматику.",
  Register: "Регистрация",
  "Create your account": "Создать аккаунт",
  "Choose a username and a password of at least 12 characters. You can create your own projects afterwards.":
    "Выберите имя пользователя и пароль не короче 12 символов. Позже вы сможете создавать собственные проекты.",
  Invitation: "Приглашение",
  "Accept your invite": "Принять приглашение",
  "Enter the code from your project owner and choose a password.":
    "Введите код от владельца проекта и выберите пароль.",
  "Accept invite": "Принять приглашение",
  Username: "Имя пользователя",
  Password: "Пароль",
  "New password (12+ characters)": "Новый пароль (от 12 символов)",
  "Confirm password": "Подтвердите пароль",
  "Invite code": "Код приглашения",
  "Have an account? Log in": "Уже есть аккаунт? Войти",
  "Have an invite code? Accept invite": "Есть код приглашения? Принять приглашение",
  "New here? Register": "Впервые здесь? Зарегистрируйтесь",
  Cancel: "Отмена",
  "Enter your invite code.": "Введите код приглашения.",
  "Password must be at least 12 characters.": "Пароль должен содержать не менее 12 символов.",
  "Choose a username.": "Выберите имя пользователя.",
  "The passwords do not match.": "Пароли не совпадают.",
  "Enter your username.": "Введите имя пользователя.",
  "Enter your password.": "Введите пароль.",
  "Authentication failed.": "Не удалось войти.",
  "Start new session": "Начать новую сессию",
  "Connecting to DG": "Подключение к DG"
};

export const en = {};
