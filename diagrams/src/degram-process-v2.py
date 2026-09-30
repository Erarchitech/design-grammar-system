"""Canonical two-slide DeGram process model; replaces the v1 generator."""
from pathlib import Path
from html import escape
import json
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'export'
SRC = BASE / 'src'
STEM = 'fig-02-degram-business-process'
W, H = 1920, 1080
INK, MUTED, PURPLE = '#000000', '#525252', '#A680B8'
BLUE, ORANGE, GREEN, ONTO = '#3399FF', '#FF9933', '#006600', '#9999FF'
mxfile = ET.Element('mxfile', host='app.diagrams.net', type='device')
pages = []
root = None
svg = []


def page(slug, name, subtitle):
    global root, svg
    diagram = ET.SubElement(mxfile, 'diagram', id=slug, name=name)
    model = ET.SubElement(diagram, 'mxGraphModel', grid='1', gridSize='10', page='1', pageScale='1', pageWidth=str(W), pageHeight=str(H), background='#FFFFFF', shadow='0')
    root = ET.SubElement(model, 'root')
    ET.SubElement(root, 'mxCell', id='0')
    ET.SubElement(root, 'mxCell', id='1', parent='0')
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="{slug}-title"><title id="{slug}-title">{escape(name)}</title>', f'<defs><marker id="{slug}-arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0 1 L8 5 L0 9 Z" fill="{PURPLE}"/></marker></defs>']
    pages.append({'slug': slug, 'name': name})
    rect('canvas', 0, 0, W, H, '#FFFFFF', 0)
    text('brand', 60, 26, 1200, 30, 'DESIGN GRAMMARS / DeGram Agent', 22, bold=True)
    text('status', 1470, 26, 390, 30, 'ЦЕЛЕВОЙ ПРОЦЕСС · '+str(len(pages))+'/2', 18, color=MUTED, align='right')
    text('title', 60, 70, 1800, 60, name, 40, bold=True)
    text('subtitle', 60, 132, 1800, 34, subtitle, 23, color=MUTED)


def rect(id, x, y, w, h, color=INK, radius=14, dashed=False):
    cell = ET.SubElement(root, 'mxCell', id=id, value='', style=f'rounded={int(radius>0)};arcSize=8;html=1;strokeWidth=2;fillColor=#FFFFFF;strokeColor={color};dashed={int(dashed)};', vertex='1', parent='1')
    ET.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), **{'as': 'geometry'})
    dash = ' stroke-dasharray="6 5"' if dashed else ''
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="#FFFFFF" stroke="{color}" stroke-width="2"{dash}/>')


def text(id, x, y, w, h, label, size=23, color=INK, bold=False, align='left'):
    style = f'text;html=1;whiteSpace=wrap;overflow=hidden;align={align};verticalAlign=middle;spacing=0;fontFamily=Helvetica;fontSize={size};fontColor={color};fontStyle={int(bold)};strokeColor=none;fillColor=none;'
    cell = ET.SubElement(root, 'mxCell', id=id, value='<br>'.join(escape(s) for s in label.split('\n')), style=style, vertex='1', parent='1')
    ET.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), **{'as': 'geometry'})
    lines = label.split('\n')
    ty = y+h/2-(len(lines)-1)*size*1.25/2+size*.34
    tx = x+w/2 if align=='center' else x+w if align=='right' else x
    anchor = 'middle' if align=='center' else 'end' if align=='right' else 'start'
    svg.append(f'<text data-id="{id}" data-x="{x}" data-y="{y}" data-w="{w}" data-h="{h}" x="{tx}" y="{ty}" font-family="Helvetica,Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}" text-anchor="{anchor}">')
    for i, line in enumerate(lines):
        svg.append(f'<tspan x="{tx}" dy="{0 if i==0 else size*1.25}">{escape(line)}</tspan>')
    svg.append('</text>')


def edge(id, points, dashed=False, arrow=True):
    style = f'edgeStyle=none;rounded=0;html=1;strokeColor={PURPLE};strokeWidth=2;endArrow={"block" if arrow else "none"};endFill=1;dashed={int(dashed)};'
    cell = ET.SubElement(root, 'mxCell', id=id, style=style, edge='1', parent='1')
    geo = ET.SubElement(cell, 'mxGeometry', relative='1', **{'as':'geometry'})
    ET.SubElement(geo, 'mxPoint', x=str(points[0][0]), y=str(points[0][1]), **{'as':'sourcePoint'})
    ET.SubElement(geo, 'mxPoint', x=str(points[-1][0]), y=str(points[-1][1]), **{'as':'targetPoint'})
    if len(points)>2:
        arr = ET.SubElement(geo, 'Array', **{'as':'points'})
        for x,y in points[1:-1]: ET.SubElement(arr, 'mxPoint', x=str(x), y=str(y))
    dash = ' stroke-dasharray="6 5"' if dashed else ''
    marker = f' marker-end="url(#{pages[-1]["slug"]}-arrow)"' if arrow else ''
    svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="none" stroke="{PURPLE}" stroke-width="2"{dash}{marker}/>')


def box(id, x, y, w, h, title, body, color=INK, title_size=25, body_size=22):
    rect(id, x, y, w, h, color)
    text(id+'-title', x+18, y+10, w-36, 37, title, title_size, bold=True)
    text(id+'-body', x+18, y+51, w-36, h-61, body, body_size, color=MUTED)


def finish():
    svg.append('</svg>')
    rendered='\n'.join(svg)
    ET.fromstring(rendered)
    ids=[c.get('id') for c in root]
    assert len(ids)==len(set(ids))
    pages[-1]['svg']=rendered


page('process', 'От требований к принятому решению', 'Шесть шагов процесса и элементы системы, которые их поддерживают')
box('cde',60,190,550,120,'CDE · среда общих данных','Вход: документы и их редакции\nВыход: принятые материалы проекта',BLUE)
box('onto',650,190,590,120,'Ontograph · классы компании','Общий язык объектов и свойств\nДля проектов в CDE этой компании',ONTO)
box('rights',1280,190,580,120,'Права доступа · на всех шагах','Просмотр / редактирование / управление\nDG и CDE проверяют права участника',INK,body_size=21)
edge('cde-input',[(190,310),(190,350)],dashed=True)
edge('vocabulary-link',[(790,310),(790,350)],dashed=True)
steps=[('01','Собрать\nтребования','Заказчик + архитектор'),('02','Согласовать\nправила','Ведущий архитектор'),('03','Связать\nс моделью','Проектировщик'),('04','Разработать\nвариант','Проектировщик'),('05','Проверить\nвариант','Система + проектировщик'),('06','Принять\nи передать','Ответственный за решение')]
for i,(number,title,role) in enumerate(steps):
    x=60+i*300
    rect('step-'+number,x,350,260,142,GREEN if i==5 else INK)
    text('num-'+number,x+18,358,224,26,number,18,color=MUTED)
    text('step-title-'+number,x+18,388,224,70,title,28,bold=True)
    text('role-'+number,x+12,462,236,24,role,17,color=MUTED,align='center')
    if i<5: edge('sequence-'+number,[(x+260,414),(x+296,414)])
# Short local ties avoid an unreadable all-to-all graph. Step numbers show reuse.
rect('project-graphs',60,550,1800,192,BLUE,dashed=True)
text('project-graphs-title',80,557,1755,30,'ГРАФЫ АКТИВНОГО ПРОЕКТА · номера показывают, на каких шагах они используются',21,bold=True)
for id,pts in [('source-memory',[(190,492),(190,550)]),('rule-link',[(490,492),(490,525),(720,525),(720,550)]),('calculation-link',[(1090,492),(1090,550)]),('validation-link',[(1390,492),(1390,525),(1610,525),(1610,550)])]:
    edge(id,pts,dashed=True,arrow=False)
for id,x,title,body in [
    ('spec',80,'SpecGraph · 01, 06','Источники, пояснения\nи основания решений'),
    ('meta',525,'Metagraph · 02, 03, 05','Правила проекта\nи область их применения'),
    ('comput',970,'ComputGraph · 03, 04','Связи параметров,\nскриптов и модели'),
    ('valid',1415,'ValidGraph · 05, 06','Результаты проверок\nи проверенное состояние')]:
    box(id,x,600,425,120,title,body,BLUE,title_size=24)
# Client and connected tools; labels define non-sequential support relations.
rect('degram',60,778,1800,92,ORANGE)
text('degram-title',80,787,1750,32,'DeGram · рабочее место участника: диалог + web-интерфейс DG + Model Viewer',26,bold=True)
text('degram-subtitle',80,827,1750,29,'Помогает на всех шести шагах; изменения подтверждает человек. Доступ к графам — через DG и права проекта.',22,color=MUTED)
edge('dg-access',[(960,778),(960,742)],dashed=True,arrow=False)
box('llm',60,919,550,103,'LLM · языковая модель','Предлагает и объясняет; не утверждает',ORANGE,body_size=21)
box('mcp-revit',650,919,590,103,'MCP-сервер Revit ↔ Revit','Локальная модель на ПК участника',PURPLE,body_size=21)
box('mcp-gh',1280,919,580,103,'MCP-сервер GH ↔ Grasshopper','Скрипты и связывание через DG addin',PURPLE,body_size=21)
for x,id in [(335,'llm-link'),(945,'revit-link'),(1570,'gh-link')]: edge(id,[(x,870),(x,919)],dashed=True,arrow=False)
text('legend',60,1035,1800,28,'→ порядок работы · пунктир: связь с системой · замечания на шаге 05 → доработка на 04 · итог 06 → публикация в CDE',20,color=MUTED)
finish()

page('scope','Классы общие — правила принадлежат проекту','Опыт переносится между проектами компании как проверяемая копия, а не как общее действующее правило')
rect('company',60,190,1800,810,ONTO,dashed=True)
text('company-title',85,202,1740,36,'КОМПАНИЯ И ЕЁ CDE · общая среда данных, классов и накопленного опыта',25,bold=True)
box('shared-cde',90,258,600,135,'CDE · документы и модели','Редакции и доступные материалы проектов\nСсылки на источники и публикации',BLUE,body_size=23)
box('shared-onto',740,258,680,135,'Ontograph · общие классы объектов','Классы, свойства и термины компании\nИзменение словаря — отдельное согласование',ONTO,body_size=23)
box('org-rights',1470,258,360,135,'Права участника','Компания + проект\n+ доступ в CDE',INK,body_size=23)
# Two project boundaries. Shared vocabulary references are explicit, never copied as private classes.
edge('shared-to-a',[(940,393),(940,422),(430,422),(430,462)],dashed=True)
edge('shared-to-b',[(1230,393),(1230,422),(1480,422),(1480,462)],dashed=True)
rect('project-a',90,462,720,280,BLUE)
rect('project-b',1110,462,720,280,BLUE)
for suffix,x,name,rulebody in [('a',90,'ПРОЕКТ A · исходный','Metagraph: правило A, редакция 3'),('b',1110,'ПРОЕКТ B · новый','Metagraph: копия → собственная редакция')]:
    text('project-'+suffix+'-name',x+20,473,680,35,name,26,bold=True)
    text('project-'+suffix+'-rule',x+20,526,680,36,rulebody,25,bold=True)
    text('project-'+suffix+'-scope',x+20,571,680,70,'Действует только в этом проекте:\nдля выбранных классов, объектов и условий',24,color=MUTED)
    text('project-'+suffix+'-evidence',x+20,655,680,64,'ComputGraph · модель и расчёты; ValidGraph · проверки\nSpecGraph · источники, решения и история',21,color=MUTED)
text('independence',825,520,270,155,'Общие классы\n\nРаздельные правила\nи результаты',22,color=MUTED,align='center')
# Lessons learned transfer goes below both projects; no implicit global activation.
box('lessons',510,805,900,125,'Lessons learned · отобранный опыт компании','Копия правила + источник + условия применения + основание\nВ новом проекте: адаптация → проверка → утверждение',GREEN,body_size=23)
edge('publish-experience',[(430,742),(430,870),(510,870)])
edge('adopt-experience',[(1410,870),(1480,870),(1480,742)])
text('select-label',105,795,300,106,'Отобрать и разрешить\nпередачу опыта\nиз проекта A',22,color=MUTED,align='center')
text('adopt-label',1510,795,300,106,'Скопировать\nс разрешённым доступом\nв проект B',22,color=MUTED,align='center')
text('no-global',100,950,1700,32,'Проект B сохраняет ссылку на источник копии и ведёт свою историю. Правило A и результаты его проверок остаются в проекте A.',21,color=MUTED)
text('scope-footer',60,1020,1800,36,'Права определяют, КТО может действовать. Область правила определяет, К ЧЕМУ и В КАКОМ ПРОЕКТЕ оно применяется.',23,bold=True)
finish()

ET.indent(mxfile)
(SRC/f'{STEM}.drawio').write_text(ET.tostring(mxfile,encoding='unicode'),encoding='utf8')
for i,p in enumerate(pages):
    (OUT/f'{STEM}{"" if i==0 else "-scope"}.svg').write_text(p['svg'],encoding='utf8')

explanation='''<section class="explain" id="explain"><h2>Связи без технических подробностей</h2>
<table><thead><tr><th>Элемент</th><th>Роль в процессе</th><th>Область</th></tr></thead><tbody>
<tr><th>Ontograph</th><td>Общий словарь классов объектов и свойств; используется при формализации правил, связывании и проверке модели.</td><td>Компания и её CDE; проект ссылается на согласованную редакцию словаря.</td></tr>
<tr><th>Metagraph</th><td>Правила, критерии и условия применимости. Создание, новая редакция и вывод из использования — с подтверждением.</td><td>Один проект. Класс может быть общим, но связанное с ним правило действует только внутри проекта.</td></tr>
<tr><th>ComputGraph</th><td>Связи параметров, частей скрипта и модели, по которым можно понять реализацию варианта. Вычисления выполняются профильными инструментами.</td><td>Проект и его модель/вариант.</td></tr>
<tr><th>ValidGraph</th><td>Что проверяли, на каком состоянии модели, по какой редакции правила; результаты, охват и недостающие данные.</td><td>Проект и конкретная проверка. Результаты проекта A не доказывают соответствие проекта B.</td></tr>
<tr><th>SpecGraph</th><td>Связи с документами и их фрагментами, пояснения, основания решений и происхождение скопированных правил.</td><td>Проект. Исходные документы и их редакции остаются в CDE.</td></tr>
<tr><th>CDE</th><td>Среда общих данных: исходные материалы поступают на шаг 01, согласованные результаты публикуются после шага 06. Новая редакция документа запускает анализ затронутых правил.</td><td>Компания с разграничением доступа к проектам. DeGram не заменяет CDE.</td></tr>
<tr><th>Права доступа</th><td>Просмотр (viewer), редактирование (editor), управление проектом (owner). Согласование словаря и проектных решений определяется ответственностью участника, а не только технической ролью.</td><td>Проверяются DG для данных проекта и CDE для документов. Права в одном проекте не дают доступа к другому.</td></tr>
<tr><th>LLM</th><td>Помогает интерпретировать требования, предложить правило или правку, объяснить результат. Контекст передаётся в пределах прав и политики компании.</td><td>Выбранная допустимая модель — корпоративная, локальная или внешняя по согласованной политике. LLM не утверждает правила и не заменяет проверки.</td></tr>
<tr><th>MCP-серверы</th><td>Локальные мосты от DeGram к Revit и Grasshopper. DG addin связывает объекты, параметры и части GH-скрипта с DG. Изменения подтверждает пользователь.</td><td>ПК участника. Успешный вызов инструмента не равен корректному проектному решению; мосты не обходят права DG.</td></tr>
</tbody></table>
<details id="boundaries"><summary>Как переносится опыт между проектами</summary><ol><li>В проекте A ответственный отбирает полезное правило, разрешает передачу и фиксирует его источник, редакцию и ограничения.</li><li>Участник с разрешённым доступом создаёт копию в проекте B. Библиотека lessons learned — отобранные материалы компании в CDE со ссылками на DG, а не шестой граф или общий набор автоматически действующих правил.</li><li>В проекте B проверяют соответствие общим классам, адаптируют параметры и область применения, выполняют проверку на его модели.</li><li>Ответственный проекта B утверждает новую редакцию. Дальнейшие изменения проектов независимы, а ссылка на происхождение сохраняется.</li></ol><p><strong>Пример:</strong> класс «Дверь» общий для компании. Требование к ширине двери проекта A копируется в B как предложение; его значение и применимость согласуются для условий B.</p></details>
<details><summary>Что означает целевая модель</summary><p>Схема описывает желаемый бизнес-процесс, а не готовность текущей реализации. Политика LLM, интеграции CDE, перенос опыта и область разрешённых операций Revit требуют проектирования и проверки. Корпоративная область классов не означает обязательного физического хранения Ontograph внутри продукта CDE.</p><p>Проверка с замечаниями возвращает вариант на доработку. Недостаточные данные дополняют и проверяют повторно. Новые требования проходят согласование; прежние редакции и решения сохраняются.</p></details></section>'''
css='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:white;color:#111;font-family:Helvetica,Arial,sans-serif}nav{display:flex;gap:22px;flex-wrap:wrap;align-items:center;padding:18px 3vw;border-bottom:1px solid #ddd}nav strong{margin-right:auto}a{color:inherit;text-underline-offset:4px}a:focus-visible,summary:focus-visible{outline:3px solid #3399ff;outline-offset:5px}.sheet{overflow-x:auto;padding:10px 1.5vw 20px;border-bottom:1px solid #ddd}.sheet svg{display:block;width:100%;height:auto;min-width:1050px}.hint{margin:20px 3vw;color:#525252}.explain{padding:20px 4vw 60px;max-width:1450px;overflow-x:auto}h2{font-size:28px}table{width:100%;border-collapse:collapse;font-size:17px;line-height:1.55}th,td{text-align:left;vertical-align:top;padding:14px;border-bottom:1px solid #ddd}thead{background:#f5f5f5}details{border-top:1px solid #ddd;padding-top:20px;margin-top:25px}summary{font-weight:bold;font-size:22px;cursor:pointer;min-height:44px}p,li{font-size:18px;line-height:1.6}li{margin-bottom:10px}footer{padding:20px 4vw;border-top:1px solid #ddd;color:#525252;line-height:1.5}@media(max-width:700px){th,td{padding:8px;font-size:15px}}@media print{@page{size:A3 landscape;margin:5mm}nav,.hint,.explain,footer{display:none}.sheet{padding:0;border:0;overflow:visible;break-after:page}.sheet:last-of-type{break-after:auto}.sheet svg{min-width:0;width:100%}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}'''
html='<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DG и DeGram — процесс и области применения</title><style>'+css+'</style></head><body><nav aria-label="Навигация"><strong>DG / DeGram</strong><a href="#process">1. Процесс и система</a><a href="#scope">2. Компания и проекты</a><a href="#explain">Пояснения</a><a href="#boundaries">Lessons learned</a></nav><main>'
html+=''.join('<section class="sheet" id="'+p['slug']+'" aria-label="'+escape(p['name'])+'">'+p['svg']+'</section>' for p in pages)
html+='<p class="hint">Два презентационных листа. На узком экране схемы прокручиваются; Ctrl+P печатает их отдельными страницами.</p>'+explanation+'</main><footer>Целевая модель для обсуждения. Основание: ptBIM R2, ITcon Submission, исследование интеграции DeGram и уточнённые границы компании/проекта. Пять графов DG; DeGram — клиент участника, не дополнительный граф.</footer></body></html>'
(OUT/f'{STEM}.html').write_text(html,encoding='utf8')
mermaid='''---
config:
  theme: base
  themeVariables:
    primaryColor: '#FFFFFF'
    primaryTextColor: '#000000'
    primaryBorderColor: '#000000'
    lineColor: '#A680B8'
---
flowchart TB
  subgraph COMPANY[Компания и её CDE]
    CDE[CDE: документы и модели]
    ONTO[Ontograph: общие классы]
    RIGHTS[Права: компания / проект / CDE]
    subgraph A[Проект A]
      S1[01 Требования] --> S2[02 Правила] --> S3[03 Связь с моделью] --> S4[04 Вариант] --> S5[05 Проверка] --> S6[06 Решение и передача]
      S5 -. Замечания .-> S4
      SPEC[SpecGraph: источники и решения]
      META[Metagraph: проектные правила]
      COMPUT[ComputGraph: параметры и скрипты]
      VALID[ValidGraph: проверки]
      S1 -.- SPEC
      S6 -.- SPEC
      S2 -.- META
      S3 -.- META
      S4 -.- COMPUT
      S5 -.- VALID
      S6 -.- VALID
    end
    subgraph B[Проект B]
      COPY[Собственная редакция правил]
      ADAPT[Адаптация → проверка → утверждение] --> COPY
    end
    ONTO -. Общие классы .-> A
    ONTO -. Общие классы .-> B
    CDE --> S1
    S6 --> CDE
    META --> LL[Lessons learned: отобрать и разрешить передачу]
    LL -->|Копия с источником| ADAPT
  end
  DG[DeGram: диалог / web DG / Model Viewer]
  DG -.- A
  RIGHTS -.- DG
  LLM[LLM: предложения и объяснения] -.- DG
  DG -.- MR[MCP Revit ↔ Revit]
  DG -.- MG[MCP GH ↔ Grasshopper / DG addin]
'''
(SRC/f'{STEM}.mmd').write_text(mermaid,encoding='utf8')
manifest={'pages':2,'steps':6,'graphs':['Ontograph','Metagraph','ComputGraph','ValidGraph','SpecGraph'],'status':'target-process proposal','scope':'company classes; project rules; copy/adapt/validate/approve lessons learned','generator':'diagrams/src/degram-process-v2.py','validation':'XML/SVG parse passed; export/browser QA pending'}
(OUT/f'{STEM}-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(manifest,ensure_ascii=False))
