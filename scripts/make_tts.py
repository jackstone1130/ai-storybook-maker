#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量为绘本 HTML 生成朗读音频，并 base64 内嵌回文件（单文件自包含）。

读取 HTML 里 `const S = [...]` 的故事数据，逐格合成两段音频：
  s{i}p{j}   长句（家长读）
  s{i}p{j}s  短句（孩子跟说，仅当该格有 say 字段）

用法：
    python3 make_tts.py 绘本.html

换音色：先 `say -v '?'` 看本机有哪些，改 VOICE
调语速：改 RATE（儿童读物建议 125-135）
"""
import re, sys, base64, pathlib, tempfile, subprocess

VOICE = 'Lilian (Premium)'     # macOS 高级中文音色；建议找带 (Premium)/(Enhanced) 的
RATE  = '130'                  # 放慢但不发闷
BITRATE = '64k'                # 语音 64k 单声道足够；想更保真改 96k

# 标点后的停顿（毫秒）。故意不做音高变调——[[pbas]] 是整体升降调，会让人声发飘。
PUNCT_PAUSE = {'，': 320, '、': 200, '；': 320, '：': 290, '。': 230, '！': 260, '？': 260}
PUNCT = '，、；：。！？'


def log(*a): print(*a, flush=True)


def storytelling(text):
    """给句子加呼吸停顿。只加停顿，不改音高。"""
    text = text.replace('“', '[[slnc 150]]').replace('”', '[[slnc 150]]')
    chunks, buf = [], ''
    for ch in text:
        if ch in PUNCT:
            chunks.append((buf, ch)); buf = ''
        else:
            buf += ch
    if buf:
        chunks.append((buf, ''))
    out = []
    for txt, punct in chunks:
        if txt:
            out.append(txt)
        if punct:
            out.append(punct + f'[[slnc {PUNCT_PAUSE[punct]}]]')
    return ''.join(out)


def synth(text, out_m4a, tmp):
    aiff = tmp / (out_m4a.stem + '.aiff')
    r = subprocess.run(['say', '-v', VOICE, '-r', RATE, '-o', str(aiff), storytelling(text)],
                       capture_output=True)
    if r.returncode != 0 or not aiff.exists():
        log('  !! say 失败:', r.stderr.decode()[:160]); return False
    r2 = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(aiff),
                         '-c:a', 'aac', '-b:a', BITRATE, '-ac', '1', '-ar', '24000',
                         str(out_m4a)], capture_output=True)
    aiff.unlink(missing_ok=True)
    if r2.returncode != 0:
        log('  !! 转码失败:', r2.stderr.decode()[:160]); return False
    return True


def main():
    if len(sys.argv) < 2:
        log('用法: python3 make_tts.py <绘本.html>'); return 1
    html = pathlib.Path(sys.argv[1]).resolve()
    if not html.exists():
        log('找不到文件：', html); return 1
    out = html.parent / 'audio'

    # 沙箱下 mkdir 对已存在目录可能抛错，逐个容错
    for d in (out, pathlib.Path('/tmp/_tts')):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        if not d.is_dir():
            log('✗ 无法创建目录：', d); return 1
    tmp = pathlib.Path('/tmp/_tts')

    s = html.read_text(encoding='utf-8')
    i0 = s.index('const S = [')
    i1 = s.index('const stories=', i0)      # 数据区结束锚点
    block = s[i0:i1]

    titles = re.findall(r'title:"([^"]+)"', block)
    # 逐页解析：{ hint, art, txt, say? }
    pg = re.findall(
        r'\{\s*hint:"[^"]*",\s*art:`[^`]*`,\s*txt:`([^`]*)`(?:,\s*say:`([^`]*)`)?\s*\}',
        block, re.S)
    if not titles or not pg:
        log('✗ 解析不到故事数据，请确认 HTML 结构'); return 1
    per = len(pg) // len(titles)

    longs = [re.sub(r'<[^>]+>', '', t) for t, _ in pg]
    shorts = [re.sub(r'<[^>]+>', '', sy) if sy else '' for _, sy in pg]

    log(f'音色：{VOICE}　语速：{RATE}　共 {len(titles)} 个故事 / {len(longs)} 格\n')

    pairs, ok = [], 0
    for k in range(len(longs)):
        i, j = k // per + 1, k % per + 1
        if j == 1:
            log(f'[{i}] {titles[i-1]}')
        key = f's{i}p{j}'
        f = out / (key + '.m4a')
        if synth(longs[k], f, tmp):
            ok += 1; pairs.append((key, f))
            log(f'   {key:8s}{f.stat().st_size/1024:6.1f}KB  {longs[k][:24]}')
        if shorts[k]:
            k2 = key + 's'
            f2 = out / (k2 + '.m4a')
            if synth(shorts[k], f2, tmp):
                ok += 1; pairs.append((k2, f2))
                log(f'   {k2:8s}{f2.stat().st_size/1024:6.1f}KB  ↳ {shorts[k]}')

    total = sum(f.stat().st_size for _, f in pairs)
    log(f'\n完成 {ok} 段，{total/1024/1024:.2f} MB')

    # ---- 内嵌回 HTML ----
    s = html.read_text(encoding='utf-8')
    s = re.sub(r'\nconst AUDIO_B64=\{.*?\};', '', s, flags=re.S)   # 清掉上一次
    anchor = "const AUDIO_DIR='audio/';"
    if anchor not in s:
        log('✗ HTML 里找不到注入锚点 `const AUDIO_DIR=\'audio/\';`'); return 1
    items = [f'"{k}":"data:audio/mp4;base64,{base64.b64encode(f.read_bytes()).decode()}"'
             for k, f in pairs]
    s = s.replace(anchor, anchor + '\nconst AUDIO_B64={' + ','.join(items) + '};', 1)

    bak = pathlib.Path(str(html) + '.bak')
    if not bak.exists():
        bak.write_text(html.read_text(encoding='utf-8'), encoding='utf-8')
    html.write_text(s, encoding='utf-8')
    log(f'已内嵌 → {html.name}　{html.stat().st_size/1024/1024:.2f} MB')
    return 0


if __name__ == '__main__':
    sys.exit(main())
