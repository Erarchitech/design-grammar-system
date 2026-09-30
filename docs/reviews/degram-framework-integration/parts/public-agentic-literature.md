# Публичная агентная литература: что она обосновывает для desktop BIM-assistant и постоянного графа проектного знания

**Дата доступа:** 30 сентября 2026 года. **Объём:** только пять заданных публичных работ. **Тип проверки:** аудит первоисточников и измеряемых результатов, а не репликация экспериментов. Полностью прочитаны четыре PDF; для Iversen & Huang получены библиографические метаданные и индексированная аннотация, но не полный текст. Приватные рукописи, `Publications/`, `DG_OBSIDIAN/dissemination`, секреты и код проекта не использовались. Нумерация ссылок локальна для этого отчёта, из `evidence/public-agentic/citation-ledger.json`.

## 1. Вывод для архитектурного решения

**Эти работы поддерживают отделение языкового интерфейса от исполняемых BIM-операций, проверяемое извлечение из графа и явную валидацию результатов. Они не доказывают, что интерпретация LLM перестала быть узким местом, что несколько агентов необходимы или что контейнеризация гарантирует безопасность.** Наиболее наглядный результат: у Heimig-Elschner et al. 100% tool-success и 100% проверок IFC schema/industry practice сосуществуют с Model Success 40% и 48,9% для двух задач и ручными оценками 2,7/5 и 3,9/5 (§6, табл. 4–5, PDF с. 7–8).[8]

**Рекомендуемая отправная точка — один оркестратор, специализированные инструменты, типизированные промежуточные представления и независимые исполнимые проверки.** Это рекомендация данного аудита, а не экспериментальный вывод об оптимальном количестве агентов. Усложнение до multi-agent должно пройти сравнение с одноагентной системой при одинаковых инструментах, контексте, бюджете и внешнем критерии правильности; опубликованное сравнение Gusarov et al. меняет одновременно роли, feedback и verification, поэтому эффект именно числа агентов не идентифицирован.[9]

Для постоянного графа необходимо различать три сущности:

1. **Снимок фактов BIM**: какой элемент и какое значение существовали в какой версии модели.
2. **Нормативные/проектные утверждения**: источник, редакция, условия применимости, интерпретация, статус подтверждения.
3. **История проектного решения**: альтернативы, обоснование, принявший решение человек, изменения и причины пересмотра.

Это предлагаемая модель ответственности. Ни просмотренный IFC→LPG QA у Gusarov, ни IFC→RDF compliance у Chen, ни versioned IFC artifacts у Heimig-Elschner не являются испытанием всех трёх слоёв или продольного накопления проектного знания.[8][9][7]

## 2. Матрица доступа и границы доказательств

Все пути в таблице заданы от корня репозитория. Номера страниц — физические страницы PDF, совпадающие здесь с печатной нумерацией. Тексты содержат маркеры `=== PDF PAGE N ===`; двухколоночная верстка Gusarov местами извлечена с перемежением строк, поэтому короткие цитаты и таблицы сверялись по локальным участкам, а не пересказывались по аннотации.

| Работа / идентификатор | Реально полученный источник | Что прочитано | Локальные доказательства | Ограничение доступа |
|---|---|---|---|---|
| Heimig-Elschner, Du, Scheuvens, Borrmann, Beetz. *A Modular Reference Architecture for MCP-Servers Enabling Agentic BIM Interaction*, arXiv:2601.00809 | [Версия v2, PDF](https://arxiv.org/pdf/2601.00809v2), датирована 28.03.2026 | Полный текст, 17 с., включая все шесть JSON test cases и manual rubric | `evidence/public-agentic/heimig_v2.pdf`, `heimig.txt` | Исследуется именно v2, не автоматически v1 января; latest-PDF и versioned-PDF имеют одинаковый SHA-256 |
| Gusarov, Volkova, Khrulkov, Kuznetsov, Maslov, Oseledets. *Multi-Agent GraphRAG: A Text-to-Cypher Framework for Labeled Property Graphs*, arXiv:2511.08274 | [Версия v1, PDF](https://arxiv.org/pdf/2511.08274v1), 11.11.2025 | Полный текст, 13 с., включая trace и десять IFC QA в приложении C | `evidence/public-agentic/gusarov_v1.pdf`, `gusarov.txt` | В статье ссылка на код буквально `https://github.com/your-repo`; воспроизводимый репозиторий из этой ссылки не установлен |
| Iversen & Huang. *Leveraging large language models for BIM-based automated compliance checking*, DOI `10.1016/j.autcon.2025.106707` | [Publisher landing page](https://www.sciencedirect.com/science/article/pii/S0926580525007472); [Crossref](https://api.crossref.org/works/10.1016/j.autcon.2025.106707); [OpenAlex record](https://api.openalex.org/works/https://doi.org/10.1016/j.autcon.2025.106707) | Метаданные DOI; аннотация, восстановленная из OpenAlex `abstract_inverted_index`, сопоставлена с выдачей издательской страницы | `evidence/public-agentic/iversen_crossref.html` и `iversen_openalex.html` — фактически JSON; `iversen_abstract_openalex.txt`; `iversen_search.json`; `iversen_api.html` — XML только coredata | **Полный текст недоступен**: publisher/PDF 403, API FULL 401; API без FULL вернул только метаданные; archive API 429; изолированный browser не стартовал из-за отсутствия Chromium. Издательский выпуск: том 182, февраль 2026; `2025` в DOI не следует выдавать за дату выпуска |
| Madireddy et al. *Large Language Model-Driven Code Compliance Checking in Building Information Modeling*, DOI `10.3390/electronics14112146` | [PDF на CDN издателя](https://mdpi-res.com/d_attachment/electronics/electronics-14-02146/article_deploy/electronics-14-02146.pdf) | Полный текст, 21 с., включая табл. 1–4 | `evidence/public-agentic/madireddy_cdn.pdf`, `madireddy_cdn.txt` | MDPI landing/PDF и UH repository дали 403; официальный CDN доступен с валидным TLS |
| Chen, Lin, Jiang, An. *Automated Building Information Modeling Compliance Check through a Large Language Model Combined with Deep Learning and Ontology*, DOI `10.3390/buildings14071983` | [PDF на CDN издателя](https://mdpi-res.com/d_attachment/buildings/buildings-14-01983/article_deploy/buildings-14-01983.pdf) | Полный текст, 28 с., включая классификационные метрики и ограничения | `evidence/public-agentic/chen_cdn.pdf`, `chen_cdn.txt` | MDPI и UCL landing дали 403; официальный CDN доступен с валидным TLS |

**Статус evidence:** четыре full-text и одна abstract-only работа; последнее — ограничение этого аудита, а не доказательство отсутствия эксперимента в статье. Журнальные тексты и препринты не смешиваются по статусу публикации. Загрузка PDF и сверка цитат не означают воспроизведения кода или независимого подтверждения авторских результатов.

**Что намеренно не подменялось:** поиск NVA по названию Iversen вернул магистерскую работу 2024 года, а поиск по заданному DOI — ноль записей. Эта диссертация не принималась за журнальную статью и не использовалась для восстановления её выборки. Найденные в поиске обзоры/цитирующие статьи также не использовались как первичные доказательства размеров выборки или ограничений заданного DOI.

## 3. Heimig-Elschner et al.: сильная архитектурная декомпозиция, ограниченная эмпирическая валидация

### 3.1. Что предлагается и что реализовано

Работа выделяет семь capabilities: хранение моделей; BIM execution; knowledge/context; взаимодействие пользователя с моделью; information retrieval/exploration; validation/QA; мультимодальные входы/выходы. В прототипе реализованы **четыре из семи**, а не весь reference architecture: выполнение, хранение, knowledge/context и UI (§4–5, PDF с. 3–7).[8]

MCP-интерфейс отделён от конкретного BIM API через `BaseAdapter`. Сервис выполнения имеет `/query`, `/create`, `/modify`, JSON-схемы запросов; загрузку и сохранение через versioned S3-compatible storage; выходы `Artifact`, `Manifest`, `logicalResult`, `DiffRaw`/`DiffSummary`; компактный `ChatArtifact` возвращается агенту. Реальный backend — `IFCOSAdapter`/IfcOpenShell, MinIO хранит модели, Weaviate/Ollama обеспечивают vector retrieval (§4.2–5, PDF с. 5–7).[8]

**Допустимый перенос:** контракт операции, версия входной модели, явный артефакт результата и diff — полезный образец для воспроизводимого desktop-assistant. **Недопустимый перенос:** считать уже экспериментально доказанными Revit/Archicad interoperability, enterprise scalability, семантический KG reasoning или persistent design-rationale memory. В заключении validation/QA, multimodality и retrieval/exploration прямо оставлены на будущую работу (§8, PDF с. 9).[8]

### 3.2. Как проведена оценка

Авторы прямо ограничивают эксперимент: “**a feasibility and non-regression study**” (§6, PDF с. 7). Использован **один ReAct-agent на gpt-5-mini**, упрощённый относительно четырёхагентного Text2BIM; исходный model-checking loop исключён. Шесть предзаданных задач, каждая повторена пять раз из чистого состояния: всего 30 запусков. Проверки requirements заданы правилами IfcOpenShell selector; дополнительно выполнено manual review по шкале 1–5 (§6.1, PDF с. 7; appendix, с. 12).[8]

| Test case | Содержание задания, кратко | Средние tool calls | Tool-success | Model Success | Manual review | Tokens Total per Run, K |
|---|---|---:|---:|---:|---:|---:|
| `tc_du-et-al_4` | Одноэтажный дом 120 м², три спальни, две ванные, кухня, гостиная | 25,8 | 100% | 95,0% | 3,5 | 685,661 |
| `tc_du_et_al_3` | Четырёхэтажный дом, пятно 5×3 м | 16,6 | 100% | 40,0% | 2,7 | 352,427 |
| `tc_du_et_al_5` | Трёхэтажный L-shaped дом, заданные длины и ширины | 18,2 | 100% | 48,9% | 3,9 | 421,361 |
| `tc_du_et_al_6` | Шестиугольное пятно, стороны 5 м, дверь и окна | 16,8 | 100% | 100,0% | 4,8 | 345,733 |
| `tc_new_1` | Стена 7×3 м, два окна и дверь | 12,6 | 100% | 100,0% | 4,2 | 203,476 |
| `tc_new_2` | Именованный проект/site/building, габариты 20×30 м и элементы | 15,6 | 100% | 100,0% | 5,0 | 280,453 |

Источник всех чисел — табл. 4–5, PDF с. 8; содержания задач — appendix, с. 12–17. IFC Schema и Industry Practice в табл. 5 равны 100% для всех шести случаев. Колонка tokens сохранена в авторской единице **K**, а не интерпретирована как несколько сотен токенов.[8]

**Важная осторожность со знаменателем:** Model Success — авторская модельная метрика conformity по заданным правилам, усреднённая по пяти runs; нельзя без raw logs переименовать 48,9% в «вероятность полностью правильного здания». В статье нет достаточно подробной формулы агрегации всех правил, доверительных интервалов, распределения результатов по runs или межэкспертного согласия для manual review (§6 и appendix).[8]

### 3.3. Какие выводы не следуют из 100%

- Успешный tool call означает успех операции на уровне инструментального протокола/исполнения, но таблица не устанавливает корректность проектного намерения. Авторы сами отмечают недостатки пространственного и геометрического reasoning: координаты и относительное размещение (§7, PDF с. 9).[8]
- IFC-валидность не равна нормативной, функциональной или архитектурной корректности. Это видно уже внутри опубликованной таблицы: полная schema/industry-practice валидность и существенно меньшая conformity/ручная оценка.[8]
- Заявленный “non-regression” следует понимать в авторском узком смысле feasibility: **контролируемого сравнения с монолитным MCP server нет**, а checker исходного Text2BIM удалён. Формальная неухудшающая оценка относительно идентичного baseline не выполнена (§6–7, PDF с. 7, 9).[8]
- Microservice separation — архитектурное свойство; сравнительные scalability/service-exchangeability benchmarks не проводились. В прототипе один backend, последовательная stateless модель ограничивает параллельные вызовы и concurrent edits (§7, PDF с. 9).[8]

**Проверять нужно и сам oracle.** В `tc_new_2` prompt просит “one storey”, а success criteria требуют `IfcBuildingStorey min: 2`; у четырёхэтажного дома — ровно пять storeys. Это может отражать соглашение о дополнительном roof-storey, а не ошибку модели, но оно должно быть явно задано. Проверка свойств `Qto_*` также не является самостоятельным доказательством реальных размеров геометрии. Эти наблюдения основаны на appendix, PDF с. 13–14; это замечания к валидности критериев, не утверждение о дефекте авторского кода.[8]

### 3.4. Isolation не равно security

Ключевая цитата: выполнение “**isolated from the MCP server’s memory and filesystem**” (§4.2, PDF с. 5). Это конкретная граница процесса/контейнера, а не доказанная защита от всех угроз. Статья описывает sandbox, presigned URLs и adapter contract, но не представляет penetration testing, модели угроз, проверки prompt injection, разграничения доступа нескольких проектов, утечек через сеть, политики секретов, разрешений на произвольный код или восстановления после враждебных запросов (§4–7).[8]

**Проектный вывод аудита:** отделять четыре независимых вопроса: crash isolation; права на файл/модель; конфиденциальность информации; корректность разрешённого изменения. Контейнер может успешно выполнить разрешённую, но неверно интерпретированную команду. Нужны явные capabilities/allowlists, read-only режим, approval для изменений, ограниченные права и отдельные security tests; их эффективность предстоит измерить, она не унаследована от MCP.

## 4. Gusarov et al.: полезен database-grounded feedback, необходимость семи агентов не доказана

### 4.1. Реальная задача и механизм

Это **Text-to-Cypher question answering над labeled property graphs**, не автоматическое проектирование и не система сохранения проектных решений. Python 3.12/LangGraph оркестрирует Memgraph-запросы; роли: Query Generator, Query Evaluator, Named Entity Extractor, Verification Module, Instructions Generator, Feedback Aggregator, Interpreter; отдельно Graph Database Executor (Implementation, PDF с. 3–5).[9]

Verification сочетает программные запросы существования label/property/value/relations, normalized Levenshtein similarity и LLM-ranking кандидатов. Query Evaluator — LLM-critic; он различает Accept, Incorrect, Error or Empty. В итоге реальные данные/ошибки БД входят в feedback, но семантическое решение о приемлемости всё равно частично делегировано модели (PDF с. 4).[9]

**Полезное отличие:** проверять существование сущностей и значения на реальной схеме/БД — сильнее, чем просто просить LLM «проверить себя». Однако существующий identifier может быть не тем объектом, а исполнимый Cypher может выражать не тот смысл. Авторская категория Incorrect прямо охватывает исполнимые, но семантически ошибочные запросы (PDF с. 4).[9]

### 4.2. Что измерено

Взяты пять domains CypherBench: art, flight accident, company, geography, fictional character; по 150 случайно выбранных QA, то есть **750 вопросов на конфигурацию модели**. Четыре backbone: Gemini 2.5 Pro, GPT-4o (2024-11-20), Qwen3 Coder, GigaChat 2 MAX. “Single” — Generator→Executor→Interpreter без iterative feedback, но текст также разрешает до четырёх attempts; “Agentic” — тот же backbone во всех ролях с feedback/refinement. Pipeline запущен **один раз на dataset graph** (Experiments, PDF с. 5–6).[9]

Итоговая accuracy — не exact match Cypher, не execution success и не deterministic equality result sets. Это **доля естественно-языковых ответов, признанных семантически эквивалентными JSON ground truth отдельной GigaChat 2 MAX** по LLM-as-a-judge protocol (Evaluation Metrics, PDF с. 6).[9]

| Backbone | Single, среднее по пяти domains | Agentic | Разница, процентные пункты |
|---|---:|---:|---:|
| Gemini 2.5 Pro | 67,00% | 77,23% | +10,23 |
| GPT-4o | 56,07% | 62,86% | +6,79 |
| Qwen3 Coder | 45,73% | 53,40% | +7,67 |
| GigaChat 2 MAX | 41,23% | 51,24% | +10,01 |

Первые две колонки — табл. 1, PDF с. 6; разницы пересчитаны в `derived_metrics.json`. Авторское обозначение прироста через “%” здесь уточнено как **п.п.**, поскольку вычитаются две accuracy.[9]

### 4.3. Ограничения причинного вывода

1. **Нет абляции числа агентов.** Сравнение добавляет одновременно verification, refinement, critic и aggregation. Оно показывает преимущество пакета изменений на данном benchmark, но не необходимость отдельных LLM-ролей по сравнению с одним ReAct-agent с теми же checks. Не показаны варианты «один агент + database checks», «без critic», «без entity extractor», «детерминированный aggregator».[9]
2. **Не уравнен фактический compute.** Упоминание четырёх attempts не уравнивает токены, LLM calls, latency или стоимость нескольких ролей; эти показатели в результатах не представлены. Формулировка maximum four iterations и Algorithm 1 с первоначальным Generate до цикла `t ≤ 4` также требуют уточнения: начальная генерация плюс четыре revisions или четыре total attempts (PDF с. 4–6).[9]
3. **Судья не внешний gold oracle.** GigaChat 2 MAX оценивает в том числе ответы GigaChat 2 MAX. Это не доказательство предвзятости, но отсутствие независимой экспертной калибровки и измерения judge error ограничивает достоверность оценки. Нет повторных прогонов и доверительных интервалов.[9]
4. **Сырые числители не восстановить.** Некоторые проценты табл. 1, например 55,70% при заявленных 150 QA, не соответствуют простому отношению целого числа правильных ответов к 150. Возможны фильтрация/иной знаменатель или особенности агрегации, но статья не раскрывает это достаточно; нельзя самовольно достраивать counts.[9]
5. **Воспроизводимость обещана, но ссылка-заглушка.** На PDF с. 4 и в ссылке на prompt templates буквально стоит `https://github.com/your-repo`. Это снижает проверяемость logs/prompts в доступной версии, но не доказывает, что код нигде не существует.[9]
6. **Семантические затруднения остаются.** Авторы описывают ошибки disjunction, symmetric relations, multi-intent и композиции подцелей (Discussion and limitations, PDF с. 7). Значит, вывод «интерпретация уже решена» противоречит даже собственному анализу ошибок работы.[9]

### 4.4. BIM-демонстрация: десять вопросов и ошибка масштаба

Отдельный IFC-case — Sample House, **одна модель, десять вручную подготовленных вопросов**, agentic Gemini 2.5 Pro. Это feasibility engineering-data QA, не промышленный BIM benchmark и не подтверждение большей точности compliance/design (PDF с. 5–6; Appendix C, с. 13).[9]

Показательный Q2: ожидается **76,47 м³** объёма roof space; ответ системы — “**76465.52 m³. This value appears unusually large.**” (Appendix C, PDF с. 13). Авторы положительно отмечают способность express uncertainty. Но предупреждение не исправляет неверное численное значение и единицу: это **не корректный ответ** в заявленной физической величине. Наоборот, пример обосновывает отдельный deterministic unit/quantity layer; источник расхождения без исходных данных/кода точно не локализован.[9]

Q7 ожидает perimeter “12,810” без ясной единицы, система отвечает 12,81 m; Q9 использует ожидаемое 1000 mm / 1 m. Не следует объявлять Appendix C «100% correctness», а неоднозначности units надо разрешать по IFC metadata, а не стилем LLM-ответа.[9]

**Вывод для постоянного графа:** статья поддерживает query grounding на схеме и фактах. Она не оценивает создание и согласование новых знаний, память между сессиями, temporal/versioned graph, изменение схемы, provenance проектных решений, conflict resolution, синхронизацию с живым Revit или write access. Multi-turn dialogue прямо обозначен как future work (Conclusion, PDF с. 7).[9]

## 5. Iversen & Huang: перспективная аннотация, но предел проверки — abstract-only

### 5.1. Что подтверждено доступной аннотацией

Артефакт DSR объединяет прямую интерпретацию regulations, извлечение BIM data, выполнение проверок и отчёты. Доступная аннотация даёт четыре различных результата, которые нельзя сливать в одно «97–100% правильности»:[10]

| Этап | Указанный показатель | Что можно сказать | Чего нельзя проверить без full text |
|---|---|---|---|
| Rule interpretation: classification | F1 97% | Авторский результат для классификации правил | Классы, macro/micro averaging, support, sampling, leakage |
| Dependency identification | F1 100% | Авторский результат для выявления зависимостей | Число положительных/отрицательных связей, сложность dependencies, независимость annotation |
| Building model preparation | 97% correct selection of extraction tools | Выбор инструмента — отдельная task metric | Correct arguments, геометрическая точность extraction, полнота атрибутов |
| Rule execution | Accuracy 97,7% | Отдельная accuracy, сравнение с naive baseline заявлено | Denominator, confusion matrix, false-compliance rate, состав baseline, статистическая процедура |

Источник таблицы — **аннотация**, полученная через OpenAlex; в издательском search result highlights фигурирует также execution F1 98%. **Accuracy 97,7% и F1 98% — разные метрики**, не повод «исправлять» одну другой. Полный текст нужен для их согласования; screenshot/search snippet не заменяет Methods/Results.[10]

Короткая цитата из индексированной аннотации: “**overcomes the manual rule digitization bottleneck in traditional ACC systems**”. Её объект — ручная оцифровка правил в традиционных ACC; не утверждение, что семантическая интерпретация вообще больше не ограничивает надёжность. Перенос этой фразы на свободное проектирование, любые нормативы и любые модели был бы необоснованным расширением.[10]

### 5.2. Что остаётся неизвестным

Не установлены по первичному full text: число правил/моделей, выбранный норматив и версия, число повторов, LLM/version, обработка отсутствующих данных, generalization на другую юрисдикцию, содержимое инструментов, журнал ошибок, latency/cost, человеко-часы подготовки. **Эти поля не помечены «отсутствуют в статье» — они «не проверены в этом аудите».** Приводить найденные в чужом обзоре «130 clauses TEK17» как проверенную здесь авторскую выборку было бы нарушением первичного grounding; такой перенос не сделан.

**Ограниченный архитектурный урок:** декомпозировать interpretation, dependency resolution, tool selection и execution в отдельные объекты тестирования. Даже высокая локальная метрика этапа не даёт автоматически end-to-end correctness, а естественно-языковой reasoning report сам по себе не устанавливает fidelity объяснения или правомерность нормативной трактовки. Это логический вывод аудита из различия измеряемых задач, а не новый эмпирический результат Iversen & Huang.

## 6. Madireddy et al.: полуавтоматическая генерация скриптов, не доказанная точность compliance

### 6.1. Эксперимент и человеческий вклад

Два case studies: single-family residential project и office building; всего **12 sample rules** из IRC, IMC и иных источников. Примеры включают двери, лестницы, ограждения, высоты, window-to-wall ratio, площади, fixtures, материалы, footings и ventilation. В офисном case выбраны восемь правил. Используется Revit 2024/PythonShell, LLM генерирует Python, пользователь выполняет его и возвращает ошибки (§4, PDF с. 8–16).[6]

Prompt engineering включает trial-and-error, общие compatibility instructions и **rule-specific mapping** на API categories/properties. Примеры: `OST_StairsRailing`, elevation levels, `OST_Windows`/`OST_Walls`, `OST_Floors`, `OST_PlumbingFixtures`; это существенная доменная работа человека, а не полностью исчезнувшая формализация (§4.2, табл. 2–3, PDF с. 9–11).[6]

Авторы прямо признают в ограничениях: “**the current workflow requires manual intervention**” для исполнения и исправлений (§5, PDF с. 18; перенос слова в PDF). Полноценный агент, взаимодействующий с Revit API, предлагается как future work, не уже испытанная реализация.[6]

### 6.2. Какая именно success rate

Табл. 4 сравнивает восемь LLM/products **на правилах 1–5**, не на всех 12 правилах всех кейсов. Метрики: время генерации, количество correction attempts, бинарный статус получения работающего скрипта на какой-либо попытке и success rate. Определение Eq. 1: correctly executed scripts / number of attempts; значения таблицы соответствуют одному успешному скрипту на `(1 + correction attempts)` для успешно завершённого правила (§4.6, PDF с. 16–17).[6]

| Название в статье | Успешные правила из пяти по Status | Средние correction attempts, авторская таблица | Средняя Success Rate |
|---|---:|---:|---:|
| ChatGPT 4.0 | 5 | 6,8 | 13,2% |
| Claude Sonnet 3.5 | 5 | 3,4 | 23,7% |
| Meta LLaMA 3.1-405B | 0 | — | 0% |
| Microsoft Copilot | 0 | — | 0% |
| Gemini | 3 | 6 | 9,7% |
| Perplexity.AI | 4 | 5,0 | 14,4% |
| Grok | 5 | 0,6 | 76,7% |
| Deepseek | 5 | 2,2 | 33,3% |

Все значения переписаны из табл. 4, PDF с. 17; версии не уточнены сверх опубликованных названий. Для незавершённых правил attempts не раскрыты, а средние correction attempts у Gemini/Perplexity считаются по доступным успешным случаям, поэтому это не одинаковая end-to-end стоимость для всех моделей.[6]

**76,7% у Grok — не 76,7% правильно проверенных зданий или обнаруженных нарушений.** Для correction counts `[0, 0, 2, 0, 1]` среднее отношений `100/(1+c)` даёт 76,6667%; pooled отношение пяти успешных скриптов к восьми попыткам даёт **62,5%**. Обе арифметики сохранены в `derived_metrics.json`; опубликованная величина соответствует macro average по правилам. Это демонстрирует, почему нужно сохранять знаменатель.[6]

### 6.3. Почему маркетинговые формулировки слишком сильны

- “Processing Time” — продолжительность генерации, “**as reported by the models themselves**” (§4.6, PDF с. 16), а не инструментальная end-to-end latency. В неё нельзя молча включить manual transfer, Revit execution и debugging; экономия времени относительно человеческого baseline не установлена этой таблицей.[6]
- Статус «script functional/error-free» не измеряет precision/recall нарушений или соблюдение всех условий правила. Нет опубликованной полноценной confusion matrix на экспертном gold set compliance outcomes.[6]
- В §4.2 фраза “**guaranteed to generate an error-free Python script**” после trial-and-error не является статистической гарантией: табл. 4 содержит неудачи и retries. Научно осторожная формулировка — «подобранный prompt позволил получить работающие скрипты в части тестируемых условий».[6]
- В Results Grok назван best overall по табл. 4, но Conclusion выделяет ChatGPT/Claude как most effective (PDF с. 17–18). Это внутренняя несогласованность акцентов; нельзя строить надёжный рейтинг моделей по заключению, игнорируя таблицу.[6]
- Revit/software versions и качество room tags/names/boundaries критичны. Авторы ограничивают выводы двумя моделями, 12 правилами и платформой Revit, признают ручные операции и проблемы неполных/устаревших metadata (§5, PDF с. 18–19).[6]

### 6.4. Проверка семантической верности — не факультативная

Внутри самой статьи есть места, требующие проверки rule-to-code, даже без обращения к внешним нормативам:

- **Rule 6, табл. 1:** одна жилая комната не менее 120 ft²; остальные жилые комнаты, кроме кухонь, не менее 70 ft². **Текст §4.3:** скрипт проходит по habitable rooms и отмечает площади менее 120 ft². Описание исполнения упрощает условную логику исходного правила (PDF с. 9, 13).[6]
- **Rule 12, табл. 1:** ventilation = `(5 × occupants) + (0.06 × floor area)`. **Текст §4.4:** проверка описана по area-based 0.06 CFM/ft²; people-based term не упомянут (PDF с. 9, 15).[6]
- **Rule 1, табл. 1:** наряду с width фигурирует net clear width; описание примера проверяет width/height (PDF с. 9, 12). Не показано, что все различающиеся величины были отдельно извлечены и проверены.[6]

Это **документальные несоответствия описаний**, а не доказанная reverse-engineering ошибка невыложенного скрипта. Без полного кода нельзя установить, были ли условия фактически опущены. Но именно поэтому работающий скрипт и убедительный report не должны считаться ground truth compliance.

## 7. Chen et al.: измерена главным образом классификация текста, а не end-to-end нормативная правильность

### 7.1. Pipeline и scope

Framework: lightweight domain ontology → классификация сложности текста → GPT-4 extraction → rule-based mapping в SPARQL → проверка RDF/ontology instances. Нормативный контекст — GB-50096-2011; ontology создаётся полуавтоматически через term extraction/clustering с **manual adjustment**. IFC concepts связываются с ontology по **predefined mapping table**, Python извлекает сведения о room/floor/area/apartment type (§3.1–3.5, с. 7–11; §4.1, с. 11–12).[7]

BIM-case — специально построенная авторами **девятиэтажная жилая модель**, по четыре residential units и public area на этаж, поскольку реальные модели конфиденциальны. Несмотря на вводное описание real-world BIM, §4.1 прямо сообщает custom model. Основной scope — residential area requirements, не все разделы проектирования (§4.1, с. 11–12; §5.3, с. 25).[7]

### 7.2. Что выражает 0,97

Классифицируются **три уровня вложенности/сложности информации**: single-layer, double-layer, triple-layer, а не классы «нарушение/соответствие» и не юридическая правильность. Таблицы 3–6 показывают по **100 samples на класс**, то есть 300 evaluation samples в каждой сравнительной таблице; полный размер training corpus и схема отделения augmentations от test examples не раскрыты достаточно для воспроизведения (§3.3, с. 8; §4.2, с. 13–19).[7]

| Модель | F1 class 0 | F1 class 1 | F1 class 2 | Что сравнивается |
|---|---:|---:|---:|---|
| TextCNN, табл. 3 | 0,995 | 0,788 | 0,777 | Text classification |
| LSTM, табл. 4 | 0,958 | 0,850 | 0,886 | Text classification |
| BERT, табл. 5 | 0,954 | 0,882 | 0,925 | Text classification |
| Fusion, табл. 6 | 0,995 | 0,951 | 0,954 | Text classification |

Для fusion авторы сообщают train accuracy 0,99/loss 0,06 и validation accuracy **0,97**/loss 0,14 (§4.2.4, PDF с. 18). По tab. 6 recalls 0,990/0,970/0,940 и support 100/100/100 суммарная доля получается 290/300 ≈ **0,9667**, что согласуется с округлением до 0,97. Это не «97% compliance accuracy».[7]

Есть небольшая внутренняя ошибка изложения: текст LSTM при восьми ошибках на class 0 называет F1 0,995, тогда как табл. 4 даёт 0,958. В отчёте принята таблица, а не противоречащая ей фраза (§4.2.2, PDF с. 15).[7]

### 7.3. Где заканчивается доказательство

**GPT-4 extraction демонстрируется примерами, а не сопоставимой численной ablation.** В §4.3 показаны ICL prompts и JSON extraction, в §4.4 — SPARQL examples. Не приведена отдельная количественная оценка exact extraction Object–Property–Condition–Value, ошибок SPARQL mapping, false compliant/false non-compliant outcomes и end-to-end accuracy на независимой BIM/нормативной выборке. Поэтому улучшение classifier не доказывает величину улучшения LLM extraction или compliance.[7]

Причинный вывод о пользе fusion также ограничен: standalone BERT использует BERT-base-Chinese, а fusion инициализирует Hfl/Chinese-MacBERT-base (§4.2.3–4.2.4, с. 16, 18). Меняется не только объединение CNN/LSTM/BERT, но и pretrained backbone; нужен matched-backbone baseline для изоляции эффекта fusion.[7]

Статья смешивает термины “one-shot learning”/“fine-tune” в §3.4.2 и явно описывает **in-context learning** в §4.3; instructional fine-tuning снова вынесен в future work (§5.3). На основании доступного описания безопаснее говорить о prompt/ICL conditioning GPT-4, не заявлять доказанную процедуру изменения его весов.[7]

Фраза о temperature=0, которая “ensures ... precise and reliable” (§4.3, с. 20), сильнее показанного: детерминированность выбора не равна истинности извлечённого условия. Это методологическое возражение аудита, а не установленный результат повторных вызовов модели.[7]

### 7.4. Урок для графа знаний

Ontology/RDF полезны как **явная семантическая схема и исполнимый слой запросов**, связывающий source clause, объект, свойство, условие и значение. Но mapping table и ontology содержат авторские решения и требуют проверки. Присутствие RDF/OWL/SPARQL не делает результаты автоматически правильными.[7]

Короткая ограничивающая цитата: “**primarily focused on compliance checking of residential area requirements**” (§5.3, PDF с. 25). Qualitative spatial functionality/aesthetics, electrical/mechanical/structural domains и более широкая generalization обозначены как future work. Следовательно, эту работу нельзя использовать как проверку полноценного архитектурного design reasoning или памяти принятия решений.[7]

## 8. Проверка двух сильных тезисов

### 8.1. «LLM-интерпретация больше не является bottleneck»

**Вердикт: как универсальный вывод — не поддерживается.**

- Если bottleneck означает **ручную оцифровку простых/отобранных правил**, Iversen & Huang заявляют её преодоление в аннотации, а Madireddy/Chen демонстрируют автоматизацию части преобразования. Но у последних остаются rule-specific prompts, manual mapping/ontology adjustment, а у Iversen full-text границы не проверены.[10][6][7]
- Если bottleneck означает **ограничение надёжности end-to-end**, Heimig-Elschner демонстрируют семантико-геометрический разрыв при успешном выполнении; Gusarov описывают композиционные ошибки и показывают неверное значение объёма; Madireddy не измеряют semantic compliance accuracy.[8][9][6]
- Если bottleneck означает **доминирующую задержку или стоимость**, ни token totals Heimig, ни self-reported generation time Madireddy, ни accuracy Gusarov не дают общей декомпозиции wall-clock/human effort/cost для сравниваемого desktop workflow.[8][9][6]

**Поддерживаемая формулировка:** «LLM снижает потребность в ручном написании части запросов и проверок в ограниченных постановках; ведущие источники ошибок и затрат смещаются между интерпретацией, grounding, извлечением, исполнением и валидацией. Какой этап доминирует, требуется измерять на целевых задачах».

Для проверки исходного тезиса нужны paired runs с заменой только одного этапа на oracle: gold interpretation; gold BIM mapping; gold extracted quantities; gold checking logic. Измерять, насколько каждый oracle снижает ошибку и время. Это **предложенный эксперимент**, не проведённый в рассмотренных работах.

### 8.2. «Для BIM + knowledge graph необходим multi-agent»

**Вердикт: доказан полезный комплекс feedback/verification, не необходимость multi-agent.** У Gusarov единый backbone выполняет разные роли; преимущества перед его упрощённой baseline не отделены от дополнительных инструментов, feedback и compute. Heimig-Elschner сознательно переходят от четырёхагентного прототипа-предшественника к одному агенту и показывают feasibility, но без matched multi-agent comparison — это также не доказательство превосходства single-agent.[9][8]

**Рациональное условие добавления роли:** у неё есть отличающаяся информация, permission boundary, измеримая функция или независимо проверяемая обязанность. Семь именованных prompts без таких оснований могут увеличить стоимость и коррелированные ошибки. Для доказательства выигрыша нужны абляции ролей, matched tools/context/budgets, latency/cost и gold correctness. Разделение ролей не следует называть статистической независимостью суждений.

## 9. Ограниченные архитектурные уроки

Следующие пункты — **рекомендации данного аудита**, выведенные из наблюдённых ограничений; не утверждение, что такая система уже реализована в этом репозитории.

| Решение | Поддерживающее наблюдение | Граница переноса / обязательная проверка |
|---|---|---|
| Отделить host/UI/LLM от BIM adapter | `BaseAdapter`, artifacts, diff, versioned storage у Heimig, §4–5.[8] | Проверить контракт хотя бы на live Revit и IFC backend; не объявлять backend-agnostic только по интерфейсу |
| Начинать read-only, изменения оформлять proposal→preview→approve→commit | Разрыв tool-success/model correctness у Heimig, табл. 4–5.[8] | Approval не заменяет checking; diff должен показывать неожиданные удаления/изменения и действительную финальную модель |
| Сохранять operation envelope | Versioned artifacts и manifest у Heimig, §4.2.[8] | Добавить model revision/hash, element IDs, units, tool/version, validated arguments, pre/postconditions, status, author/approver; это предлагаемые расширения |
| Проверять схему и факты программно | Database-grounded verification у Gusarov.[9] | Разделить schema-valid, executable, semantically-correct и supported-answer; пустой результат не всегда ошибка |
| Нормализовать единицы вне LLM | Ошибка roof-volume в Appendix C Gusarov.[9] | Проверять dimension/unit provenance, conversion, tolerance; raw number без unit — incomplete evidence |
| Использовать typed interpretation вместо непросматриваемого текста | Object–Property–Condition–Value у Chen.[7] | Дополнить applicability, exceptions, quantifiers, references, jurisdiction/version; четыре поля сами по себе не покрывают всю нормативную семантику |
| Считать ontology/mappings контролируемыми артефактами | Manual adjustment и predefined mapping у Chen; rule-specific instructions у Madireddy.[7][6] | Versioning, review, regression tests; LLM proposal не становится автоматически канонической записью |
| Разделить canonical knowledge и retrieved/generated suggestions | Graph QA и ontology compliance не оценивают longitudinal knowledge governance.[9][7] | Provenance, confidence/status, change history, invalidation, duplicate/conflict handling нужно проектировать и тестировать отдельно |
| Не подменять security контейнером | Изоляция execution от host у Heimig без adversarial evaluation.[8] | Threat model, least privilege, запрет произвольного write/code по умолчанию, network egress policy, project scope, security test suite |
| Добавлять агентов только после ablation | Gusarov сравнивают полный пакет ролей/feedback с baseline.[9] | Учитывать дополнительные LLM calls и coordinator failures; deterministic validator иногда лучше дополнительного «critic» |

**Особенность desktop/live BIM:** чистый stateless IFC snapshot отличается от открытого авторского документа с несохранёнными правками. Предлагаемый контракт должен перед commit сверять revision/preconditions, не применять команды к молча переключившемуся документу, обеспечивать rollback и формально определять, что означает «сохранено». Heimig-Elschner сами отмечают необходимость remote bridges для commercial tools и пока не проверенную concurrent modification (§7–8, PDF с. 9).[8]

**Особенность долговременного знания:** хранить не только «LLM сказал X», но цепочку `source fragment → interpretation version → BIM snapshot → executed query/check → observed result → accepted decision`. При смене нормы, модели или mapping пересчитывать зависимые выводы либо помечать их stale. Это необходимое расширение исследуемых подходов, а не уже опубликованная longitudinal валидация.

## 10. Предлагаемая программа оценки для desktop-assistant

Ниже — проект протокола будущих испытаний. Целевые пороги, число задач и допустимый риск должен утвердить ответственный владелец продукта; данный аудит не придумывает «универсально безопасные» значения.

### 10.1. Раздельные уровни результата

| Уровень | Unit of analysis | Проверяемый результат | Нельзя подменять |
|---|---|---|---|
| Interpretation | Исходный запрос/пункт нормы | Объект, scope, exception, quantifier, comparator, units; возможность запросить уточнение | Красивым reasoning или корректной JSON-схемой |
| Grounding/retrieval | Объект/свойство/источник | Правильные element IDs, поддерживающие fragments, полнота retrieval, корректная версия нормы/модели | Наличием identifier в графе |
| Tool execution | Вызов инструмента | Correct arguments, успешное исполнение, отсутствие unintended side effects | HTTP 200 и отсутствием исключения |
| Model validity | Артефакт BIM | Parse/schema/topology/geometry/unit integrity | Соответствием проектному brief |
| Compliance | Применимый clause × element/model | TP/FP/FN/TN; отдельно false-compliance; unknown/not-applicable | Долей исполнившихся скриптов |
| Design correctness | Полный brief × итоговая модель | Все обязательные требования, пространственная логика, сохранность нецелевых элементов, экспертная приемлемость | Одиноким rule-check score или partial credit |
| Knowledge persistence | Изменение знаний × сессия/версия | Traceability, stale invalidation, conflict/duplicate handling, replay, корректное повторное использование | Просто наличием graph database |
| Security | Adversarial action × policy boundary | Запрет чтения/изменения вне scope, утечки, injection, denial of service, unauthorized commit | Контейнеризацией и тем, что workflow не упал |

### 10.2. Наборы задач и gold evidence

- Отделить lookup, multi-hop/compositional QA, interpreting conditional regulations, proposal/edit, generation, сохранение и пересмотр решения. Сложность должна включать units, coordinate systems, linked models, ambiguous names, incomplete metadata и несовпадение schema/version.
- Для compliance иметь независимую экспертную разметку исходного положения, условий применимости и конкретного BIM outcome; disagreements и adjudication сохранять, а не решать автоматически тем же LLM.
- Для generation/edit проверять геометрию независимо от свойств, которые записал генератор, и явно фиксировать соглашения вроде roof-storey. Для всех задач публиковать точный oracle, raw counts и exclusions.
- Использовать не только удачные/чистые модели: missing/contradictory values, null/empty versus zero, неподдерживаемые правила, смену единиц и нормативных редакций. «Не могу определить» должно быть разрешённым состоянием, отдельно оцениваться coverage и selective risk.
- Для постоянного графа проверять задачи через несколько сессий и ревизий: новое правило отменяет старое; модель изменилась после проверки; решение принято на ошибочном извлечении; два пользователя предлагают противоречащие факты; человек отозвал согласование.

### 10.3. Baselines и абляции

Сравнивать при одинаковых моделях/инструментах и заранее ограниченном бюджете:

1. Детерминированные curated queries/checkers для поддерживаемых задач.
2. Один LLM direct tool-use без retrieval/refinement.
3. Один ReAct-agent + schema-aware retrieval + deterministic verification + ограниченный feedback loop.
4. Тот же pipeline с дополнительными LLM-ролями.
5. Поочерёдное удаление critic/entity verification/aggregator и замена их детерминированными компонентами, где возможно.

Отдельно сравнить graph retrieval с подходящими SQL/key-value/vector baselines: цель — проверить пользу представления для конкретной задачи, а не подтвердить название GraphRAG. Для любой добавленной сложности фиксировать не только accuracy, но и реальный wall-clock, tokens/API calls, стоимость, человеческие минуты, число отказов и непредусмотренных изменений.

### 10.4. Повторяемость и отчётность

- Публиковать точный model ID/version, prompts, tools/schema versions, dataset split, sampling, seeds где поддерживаются, лимиты retries/timeouts и distinction initial attempt versus correction.
- Делать повторные запуски; оценивать uncertainty с учётом кластеризации по задаче/модели/правилу. Коррелированные calls одного workflow — не независимые samples.
- Сохранять все попытки, включая неуспешные/незавершённые; показывать task-level success отдельно от partial-rule score, macro отдельно от micro, количество выбранных и исключённых задач.
- Калибровать LLM-judge на human-adjudicated подвыборке; публиковать judge disagreement, false accept и sensitivity к формулировке. Критические свойства проверять исполнимым oracle/экспертом, не большинством однотипных LLM.
- После mutation читать фактическое конечное состояние из BIM backend; после graph update проверять canonical record и его dependencies; проверять undo/rollback и отказ при устаревшей ревизии.
- Для bottleneck claim выполнять oracle-substitution experiments отдельно от архитектурных benchmarks; для security — отдельную adversarial программу с заранее объявленными policy boundaries.

## 11. Реестр коротких проверяемых цитат

Короткие цитаты ниже ограничены нужными фрагментами; переносы строк нормализованы. Для Iversen источник цитаты — индексированная аннотация, не самостоятельно прочитанный full text.

| ID | Прямая цитата | Якорь | Роль в аргументе |
|---|---|---|---|
| H1 | “a feasibility and non-regression study” | Heimig-Elschner §6, PDF с. 7.[8] | Авторы ограничивают scope |
| H2 | “isolated from the MCP server’s memory and filesystem” | §4.2, PDF с. 5.[8] | Конкретная isolation boundary, не security proof |
| H3 | “Missing spatial and geometric reasoning capabilities” | §7, PDF с. 9.[8] | Reasoning ограничения не исчезли |
| G1 | “seven cooperating agents and one graph database” | Gusarov Implementation, PDF с. 4.[9] | Состав workflow |
| G2 | “76465.52 m³. This value appears unusually large.” | Appendix C, Q2, PDF с. 13.[9] | Caution не исправляет unit/value error |
| I1 | “overcomes the manual rule digitization bottleneck in traditional ACC systems” | Iversen & Huang, Abstract, OpenAlex copy.[10] | Claim касается ручной оцифровки |
| M1 | “as reported by the models themselves” | Madireddy §4.6, PDF с. 16.[6] | Время не инструментально измерено |
| M2 | “guaranteed to generate an error-free Python script” | §4.2, PDF с. 9.[6] | Слишком сильная гарантия после prompt tuning |
| C1 | “an accuracy of 0.97 and a loss value of 0.14 on the validation set” | Chen §4.2.4, PDF с. 18.[7] | Это text classifier, не compliance |
| C2 | “primarily focused on compliance checking of residential area requirements” | Chen §5.3, PDF с. 25.[7] | Ограниченная область применения |

## 12. Проверяемость файлов и что ещё не сделано

- Исходные PDF, извлечённые тексты и результаты попыток доступа: `evidence/public-agentic/`.
- Фиксация versioned arXiv PDF и SHA-256: `pdf_manifest.json`; latest и versioned копии сверены программно.
- Загрузка с проверкой TLS, фактическими status/URLs/size/hash: `fetch_public.py`, `access_initial.json`, `access_alternatives.json`, `access_iversen_recovery.json`, `access_final.json`, `access_metadata.json`, `access_last_attempt.json`.
- Аннотация Iversen не названа full text: `iversen_abstract_openalex.txt`, `iversen_search.json`; метаданные API сохранены отдельно. Маленькие XML/HTML ответы 200 проверены и не выданы за PDF.
- Цитаты и арифметика: `citation-ledger.json`, `verify_evidence.py`, `derived_metrics.json`.
- Не сделано: репликация авторского кода, независимая экспертиза нормативной трактовки, security audit реализации или аудит кода данного репозитория. Полный Methods/Results Iversen & Huang остаётся обязательным источником перед использованием точных характеристик их benchmark в научном/архитектурном обосновании.

**Итог:** использовать публикации как источники ограниченных архитектурных приёмов и наблюдаемых failure modes; не объединять разные stage metrics в обещание надёжного автономного проектирования. Наиболее защищаемая позиция — evidence-first assistant с управляемыми правами, явными версиями и проверяемыми результатами, а не отказ от проверки интерпретации или усложнение числа агентов ради самого multi-agent label.

## Sources

[6] https://mdpi-res.com/d_attachment/electronics/electronics-14-02146/article_deploy/electronics-14-02146.pdf
[7] https://mdpi-res.com/d_attachment/buildings/buildings-14-01983/article_deploy/buildings-14-01983.pdf
[8] https://arxiv.org/pdf/2601.00809v2
[9] https://arxiv.org/pdf/2511.08274v1
[10] https://api.openalex.org/works/https://doi.org/10.1016/j.autcon.2025.106707 — Iversen & Huang: abstract indexed by OpenAlex (not full text)
