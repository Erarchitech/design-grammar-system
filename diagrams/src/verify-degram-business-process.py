from pathlib import Path
import json
from playwright.sync_api import sync_playwright
from PIL import Image
base=Path(__file__).resolve().parents[1]
out=base/'export'
stem='fig-02-degram-business-process'
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe',headless=True)
    page=browser.new_page(viewport={'width':1920,'height':1200},device_scale_factor=1)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((out/f'{stem}.html').resolve().as_uri())
    page.locator('#process svg').screenshot(path=str(out/f'{stem}-html-preview.png'))
    page.locator('#scope svg').screenshot(path=str(out/f'{stem}-scope-html-preview.png'))
    checks=page.evaluate('''() => ({title:document.title, pages:document.querySelectorAll('.sheet svg').length, steps:document.querySelectorAll('#process svg text[data-id^="step-title-"]').length, externalAssets:[...document.querySelectorAll('script[src],link[href],img[src]')].map(x=>x.src||x.href), overflows:[...document.querySelectorAll('svg text')].filter(e=>{let b=e.getBBox();return b.x<0||b.x+b.width>1920||b.y+b.height>1080}).map(e=>e.textContent), labelOverflows:[...document.querySelectorAll('svg text')].filter(e=>{let b=e.getBBox(), d=e.dataset; return b.width>Number(d.w)+2 || b.height>Number(d.h)+3}).map(e=>({id:e.dataset.id,text:e.textContent.trim(),actual:e.getBBox().width,allowed:e.dataset.w}))})''')
    assert checks['pages']==2 and checks['steps']==6 and not errors and not checks['overflows'], checks
    assert not checks['labelOverflows'], checks['labelOverflows']
    for graph in ['Ontograph','Metagraph','ComputGraph','ValidGraph','SpecGraph']:
        assert graph in page.locator('#process').inner_text(), graph
    page.locator('a[href="#boundaries"]').click()
    page.locator('#boundaries summary').click()
    assert page.locator('#boundaries').get_attribute('open') is not None
    page.set_viewport_size({'width':390,'height':844})
    mobile=page.evaluate('({body:document.body.scrollWidth,viewport:innerWidth,diagram:document.querySelector(".sheet").scrollWidth})')
    assert mobile['body']==mobile['viewport'], mobile
    browser.close()
im=Image.open(out/f'{stem}.png');im.convert('RGB').resize((1920,1080)).save(out/f'{stem}-preview.jpg',quality=92)
checks['browser_errors']=errors
checks['mobile']=mobile
checks['drawio_png']={'size':im.size,'bytes':(out/f'{stem}.png').stat().st_size}
(out/f'{stem}-qa.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(checks,ensure_ascii=False,indent=2))
