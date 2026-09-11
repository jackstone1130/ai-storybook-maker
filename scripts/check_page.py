#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无头浏览器诊断绘本页面：确认「真的渲染出来了」+ 有没有 JS 运行时错误。

交付前必跑。只看源码 / 只查语法是不够的 —— 大段代码替换后很容易悄悄删掉
渲染逻辑，页面会变成白板（什么都不显示，点什么都没反应）。

用法：
    python3 check_page.py 绘本.html [故事数] [每故事格数]

例：python3 check_page.py 语言发育故事绘本.html 6 5
"""
import sys, re, pathlib, subprocess, tempfile, os

CHROME_CANDIDATES = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
]


def log(*a): print(*a, flush=True)


def find_chrome():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    for name in ('google-chrome', 'chromium', 'chrome'):
        r = subprocess.run(['which', name], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip()
    return None


def main():
    if len(sys.argv) < 2:
        log(__doc__); return 1
    html = pathlib.Path(sys.argv[1]).resolve()
    expect_stories = int(sys.argv[2]) if len(sys.argv) > 2 else None
    expect_pages = int(sys.argv[3]) if len(sys.argv) > 3 else None

    chrome = find_chrome()
    if not chrome:
        log('✗ 没找到 Chrome / Edge / Chromium，无法做无头诊断'); return 1

    tmp = pathlib.Path(tempfile.mkdtemp(prefix='_pgchk_'))
    dom, err = tmp / 'dom.html', tmp / 'err.log'

    log(f'诊断：{html.name}')
    with open(dom, 'w') as o, open(err, 'w') as e:
        subprocess.run([chrome, '--headless=new', '--disable-gpu', '--no-sandbox',
                        '--enable-logging=stderr', '--virtual-time-budget=9000',
                        '--dump-dom', html.as_uri()],
                       stdout=o, stderr=e, timeout=180)

    domtxt = dom.read_text(encoding='utf-8', errors='ignore')
    errtxt = err.read_text(encoding='utf-8', errors='ignore')

    src = html.read_text(encoding='utf-8')
    n_pages = len(re.findall(r'class="page', domtxt))
    n_btns = len(re.findall(r'<button[^>]*>[0-9]\.', domtxt))
    n_say = len(re.findall(r'class="say"', domtxt))
    n_chars = len(re.findall(r'class="c', domtxt))
    n_imgs = len(re.findall(r'src="data:image', src))
    n_audios = len(re.findall(r'":\"data:audio', src))

    log('\n— 渲染结果 —')
    log(f'  .page 元素      {n_pages}' + (f'  (期望 {expect_pages})' if expect_pages else ''))
    log(f'  故事按钮        {n_btns}' + (f'  (期望 {expect_stories})' if expect_stories else ''))
    log(f'  跟说句块        {n_say}')
    log(f'  逐字元素        {n_chars}')
    log(f'  内嵌图片        {n_imgs}')
    log(f'  内嵌音频        {n_audios}')

    errs = [l for l in errtxt.splitlines()
            if re.search(r'uncaught|TypeError|ReferenceError|SyntaxError', l, re.I)]
    log('\n— 控制台错误 —')
    if errs:
        for l in errs[:8]:
            log('  ' + l.strip()[:220])
    else:
        log('  无 ✅')

    ok = True
    if errs:
        ok = False
    if expect_pages and n_pages != expect_pages:
        ok = False
    if n_pages == 0:
        ok = False

    log('\n' + ('✅ 通过' if ok else '❌ 有问题：页面可能没渲染出来，检查渲染代码是否完整'))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
