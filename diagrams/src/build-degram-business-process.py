"""Compatibility entry point; the canonical model is now degram-process-v2.py."""
if __name__ == '__main__':
    import runpy
    from pathlib import Path
    runpy.run_path(str(Path(__file__).with_name('degram-process-v2.py')), run_name='__main__')
    raise SystemExit(0)
from pathlib import Path
from html import escape
import json
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
SRC = BASE / 'src'
OUT = BASE / 'export'
OUT.mkdir(parents=True, exist_ok=True)
STEM = 'fig-02-degram-business-process'
W, H = 1920, 1080
INK, MUTED, EDGE = '#000000', '#525252', '#A680B8'
steps = [
    ('01', 'Собрать\nтребования', 'Определить цели\nи ограничения', 'Заказчик + архитектор', 'Собирает требования\nи сохраняет\nих источник'),
    ('02', 'Согласовать\nправила', 'Уточнить смысл\nи критерии проверки', 'Ведущий архитектор', 'Предлагает правила.\nЧеловек уточняет\nи утверждает'),
    ('03', 'Связать\nс моделью', 'Указать объекты\nи нужные параметры', 'Проектировщик', 'Помогает найти объекты\nв Revit и Grasshopper'),
    ('04', 'Разработать\nвариант', 'Изменить модель\nи сохранить вариант', 'Проектировщик', 'Предлагает правки.\nПрименяет только\nс разрешения'),
    ('05', 'Проверить\nвариант', 'Показать результаты\nи пробелы в данных', 'Система +\nпроектировщик', 'Запускает проверки\nи объясняет\nих результаты'),
    ('06', 'Принять\nрешение', 'Выбрать вариант\nи передать команде', 'Ответственный\nархитектор', 'Показывает модель,\nрезультаты проверки\nи основание выбора'),
]

mxfile = ET.Element('mxfile', host='app.diagrams.net', type='device')
diagram = ET.SubElement(mxfile, 'diagram', id='dg-simple-process', name='Процесс с DeGram')
model = ET.SubElement(diagram, 'mxGraphModel', dx='1920', dy='1080', grid='1', gridSize='10', page='1', pageScale='1', pageWidth=str(W), pageHeight=str(H), background='#FFFFFF', math='0', shadow='0')
root = ET.SubElement(model, 'root')
ET.SubElement(root, 'mxCell', id='0')
ET.SubElement(root, 'mxCell', id='1', parent='0')
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">', '<title id="title">Design Grammars: бизнес-процесс с DeGram</title>', '<desc id="desc">Шесть шагов: собрать требования, согласовать правила, связать с моделью, разработать вариант, проверить, принять решение. DeGram помогает на каждом шаге; человек утверждает изменения. Замечания возвращают вариант на доработку; новые требования запускают новый цикл.</desc>', '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0 1 L8 5 L0 9 Z" fill="#A680B8"/></marker></defs>']


def rect(id, x, y, w, h, stroke=INK, fill='#FFFFFF', radius=14, width=2, dash=False):
    style = f'rounded={int(radius>0)};arcSize=8;whiteSpace=wrap;html=1;strokeWidth={width};fillColor={fill};strokeColor={stroke};'
    if dash: style += 'dashed=1;dashPattern=4 4;'
    cell = ET.SubElement(root, 'mxCell', id=id, value='', style=style, vertex='1', parent='1')
    ET.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), **{'as':'geometry'})
    d = ' stroke-dasharray="4 4"' if dash else ''
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{d}/>')


def text(id, x, y, w, h, content, size=24, color=INK, bold=False, align='left'):
    label = '<br>'.join(escape(line) for line in content.split('\n'))
    style = f'text;html=1;whiteSpace=wrap;overflow=hidden;align={align};verticalAlign=middle;spacing=0;fontFamily=Helvetica;fontSize={size};fontColor={color};fontStyle={int(bold)};strokeColor=none;fillColor=none;'
    cell = ET.SubElement(root, 'mxCell', id=id, value=label, style=style, vertex='1', parent='1')
    ET.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), **{'as':'geometry'})
    lines=content.split('\n'); lineheight=size*1.28
    ty=y+h/2-(len(lines)-1)*lineheight/2+size*.34
    tx=x+w/2 if align=='center' else x
    anchor='middle' if align=='center' else 'start'
    svg.append(f'<text x="{tx}" y="{ty}" font-family="Helvetica,Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}" text-anchor="{anchor}">')
    for i,line in enumerate(lines): svg.append(f'<tspan x="{tx}" dy="{0 if i==0 else lineheight}">{escape(line)}</tspan>')
    svg.append('</text>')


def edge(id, points, dashed=False):
    style=f'edgeStyle=none;rounded=0;html=1;strokeColor={EDGE};strokeWidth=2;endArrow=block;endFill=1;'
    if dashed:style+='dashed=1;dashPattern=6 4;'
    cell=ET.SubElement(root,'mxCell',id=id,style=style,edge='1',parent='1')
    geo=ET.SubElement(cell,'mxGeometry',relative='1',**{'as':'geometry'})
    ET.SubElement(geo,'mxPoint',x=str(points[0][0]),y=str(points[0][1]),**{'as':'sourcePoint'})
    ET.SubElement(geo,'mxPoint',x=str(points[-1][0]),y=str(points[-1][1]),**{'as':'targetPoint'})
    if len(points)>2:
        arr=ET.SubElement(geo,'Array',**{'as':'points'})
        for x,y in points[1:-1]:ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))
    dash=' stroke-dasharray="6 4"' if dashed else ''
    svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="none" stroke="{EDGE}" stroke-width="2" marker-end="url(#arrow)"{dash}/>')

rect('canvas',0,0,W,H,stroke='#FFFFFF',radius=0,width=0)
text('brand',60,40,1600,40,'DESIGN GRAMMARS  /  DeGram Agent',24,bold=True)
text('heading',60,105,1780,78,'От требований к обоснованному решению',48,bold=True)
text('intro',60,194,1770,55,'Одна среда для работы с требованиями, моделью и результатами проверки',27,color=MUTED)
text('target',1490,40,370,40,'ЦЕЛЕВАЯ МОДЕЛЬ ПРОЦЕССА',17,color=MUTED,align='center')
for i,(number,title,body,role,helptext) in enumerate(steps):
    x=60+i*300
    text(f'role-{i}',x,280,260,65,role,22,color=MUTED,align='center')
    rect(f'step-{i}',x,365,260,210,stroke='#006600' if i==5 else INK)
    text(f'number-{i}',x+20,378,220,30,number,19,color=MUTED)
    text(f'title-{i}',x+20,411,220,84,title,29,bold=True)
    text(f'body-{i}',x+20,502,220,62,body,22,color=MUTED)
    if i<5:edge(f'flow-{i}',[(x+260,470),(x+294,470)])

edge('rework',[(1390,576),(1390,640),(1090,640),(1090,582)],dashed=True)
text('rework-label',1110,597,260,36,'Замечания → доработка',20,color='#775686',align='center')
rect('support',60,687,1760,165,stroke='#FF9933',radius=14)
text('support-name',80,698,1715,42,'DeGram помогает на каждом шаге — решения и изменения утверждает человек',25,bold=True)
for i,item in enumerate(steps):
    x=80+i*290
    text(f'help-{i}',x,751,270,80,item[4],21,color=MUTED)

rect('history',60,889,1760,100,stroke='#3399FF',radius=14)
text('history-title',85,900,1710,38,'Общая история проекта сохраняется для всей команды',26,bold=True)
text('history-content',85,942,1700,32,'Источник требования  →  версия правила  →  вариант модели  →  результат проверки  →  основание выбора',23,color=MUTED)
text('iteration',60,1011,1320,39,'Новые требования или данные → новый цикл; прежние решения остаются в истории.',22,color=MUTED)
text('scope',1410,1009,410,44,'Проверено ≠ принято человеком',20,color='#006600',align='center')
svg.append('</svg>')
svg_text='\n'.join(svg)
ET.indent(mxfile)
(SRC/f'{STEM}.drawio').write_text(ET.tostring(mxfile,encoding='unicode'),encoding='utf8')
(OUT/f'{STEM}.svg').write_text(svg_text,encoding='utf8')

mermaid=['---','config:','  theme: base','  fontFamily: "Helvetica, Arial, sans-serif"','  themeVariables:','    primaryColor: "#FFFFFF"','    primaryTextColor: "#000000"','    primaryBorderColor: "#000000"','    lineColor: "#A680B8"','---','flowchart LR']
for i,s in enumerate(steps):mermaid.append(f'  S{i}["{s[0]}. {s[1].replace(chr(10)," ")}<br/>{s[3]}"]')
mermaid+=['  S0 --> S1 --> S2 --> S3 --> S4 --> S5','  S4 -. "Замечания: доработка" .-> S3','  D["DeGram помогает; человек утверждает"]','  H["История: источник — правило — модель — проверка — решение"]','  classDef node fill:#FFFFFF,stroke:#000000,stroke-width:2px,color:#000000','  class S0,S1,S2,S3,S4,S5,D,H node']
(SRC/f'{STEM}.mmd').write_text('\n'.join(mermaid),encoding='utf8')
rows=''.join(f'<tr><th>{s[0]} · {escape(s[1].replace(chr(10)," "))}</th><td>{escape(s[3])}</td><td>{escape(s[4].replace(chr(10)," "))}</td></tr>' for s in steps)
html='''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Design Grammars — процесс с DeGram</title>
<style>
:root{color-scheme:light;--ink:#000;--muted:#525252;--line:#dedede;--paper:#fff}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:Helvetica,Arial,sans-serif}nav{padding:16px 3vw;border-bottom:1px solid var(--line);display:flex;gap:24px;align-items:center;flex-wrap:wrap;font-size:15px}nav strong{margin-right:auto}a{color:inherit;text-underline-offset:4px}a:focus-visible,summary:focus-visible{outline:3px solid #3399ff;outline-offset:5px}.diagram{padding:12px 1.5vw 0;overflow-x:auto}.diagram svg{display:block;width:100%;height:auto;min-width:1000px}.note{margin:0 3vw 25px;font-size:15px;color:var(--muted);line-height:1.6}section.explain{padding:30px 4vw 60px;max-width:1400px}h1{font-size:29px;margin:0 0 16px}p{font-size:18px;line-height:1.6;max-width:1000px}table{width:100%;border-collapse:collapse;font-size:17px;line-height:1.5}th,td{text-align:left;padding:16px 14px;border-bottom:1px solid var(--line);vertical-align:top}thead{background:#f5f5f5}th{font-weight:600}details{margin-top:25px;border-top:1px solid var(--line);padding-top:20px}summary{cursor:pointer;font-size:20px;font-weight:600;min-height:44px}li{line-height:1.6;margin:8px 0;font-size:17px}footer{border-top:1px solid var(--line);padding:24px 4vw;color:var(--muted);font-size:14px;line-height:1.6}.mobile-hint{display:none}@media(max-width:800px){.mobile-hint{display:block}table{font-size:15px}th,td{padding:12px 8px}nav{gap:16px}.explain{overflow-x:auto}}@media print{@page{size:A3 landscape;margin:6mm}nav,.note,.explain,footer{display:none!important}.diagram{padding:0;overflow:visible}.diagram svg{width:100%;min-width:0;height:auto}body{background:white}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
</style></head><body>
<nav aria-label="Навигация"><strong>DG / Бизнес-процесс</strong><a href="#process">Схема</a><a href="#explain">Как читать</a><a href="#boundaries">Границы применения</a></nav>
<main><div id="process" class="diagram">'''+svg_text+'''</div>
<p class="note mobile-hint">Схему можно прокрутить по горизонтали. Для выступления откройте страницу на широком экране; для печати используйте Ctrl+P.</p>
<section id="explain" class="explain"><h1>Как работает процесс</h1><p>DeGram объединяет работу с требованиями, привычными инструментами проектирования и результатами проверки. Заказчик задаёт потребность, проектировщик разрабатывает вариант, ответственный архитектор принимает решение.</p>
<table><thead><tr><th>Шаг</th><th>Кто отвечает</th><th>Чем помогает DeGram</th></tr></thead><tbody>'''+rows+'''</tbody></table>
<details open><summary>Если нужны изменения</summary><ul><li><strong>Замечания к варианту:</strong> вернуться к разработке, изменить модель и повторить проверку.</li><li><strong>Недостаточно данных:</strong> дополнить модель или исходные сведения; отсутствие результата не означает, что всё соответствует требованиям.</li><li><strong>Изменились требования:</strong> согласовать новую редакцию правил и заново проверить затронутые варианты. Предыдущие результаты сохраняются.</li><li><strong>Правка не подтверждена:</strong> она остаётся предложением; модель и утверждённые правила не изменяются.</li></ul></details>
<details id="boundaries"><summary>Границы применения</summary><ul><li>Это <strong>предлагаемая целевая модель</strong>, а не перечень уже реализованных функций.</li><li>Модель и расчёты остаются в Revit, Grasshopper и профильных инструментах. DeGram помогает взаимодействовать с ними.</li><li>Редактирование Grasshopper выполняется с разрешения проектировщика. Объём автоматических изменений модели Revit ещё требует отдельного согласования.</li><li>Общие термины и правила организации утверждает ответственный за методологию; права обычного участника проекта их не заменяют.</li><li>Результат проверки относится к указанным правилам и данным. Выбор проектного решения остаётся за человеком.</li><li>Участники получают общую историю проекта, а не обязательный доступ к чужим личным диалогам. Просмотр возможен и через существующий web-интерфейс.</li></ul></details>
</section></main><footer>Основание: оригинальная статья ptBIM R2, ITcon Submission и исследование интеграции DeGram. Упрощённая модель для инженеров и архитекторов. Сплошные стрелки — основной ход; пунктир — возврат на доработку. DeGram — помощник, Design Grammars — общая среда проектного знания.</footer>
</body></html>'''
(OUT/f'{STEM}.html').write_text(html,encoding='utf8')
ids=[c.get('id') for c in root]
assert len(ids)==len(set(ids))
ET.parse(SRC/f'{STEM}.drawio')
ET.fromstring(svg_text)
manifest={'steps':len(steps),'drawio_pages':1,'style':'DG TO-BE, simplified presentation; white/black, semantic border colors','status':'proposed target process, not implemented-state claim','files':[str(SRC/f'{STEM}.drawio'),str(OUT/f'{STEM}.html'),str(OUT/f'{STEM}.svg'),str(SRC/f'{STEM}.mmd')],'source':'docs/reviews/degram-framework-integration/DEGRAM-FRAMEWORK-INTEGRATION-REVIEW.md','validation':'XML and SVG parsed; unique IDs; rendering/browser QA pending'}
(OUT/f'{STEM}-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
