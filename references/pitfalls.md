# 踩坑清单

按「症状 → 原因 → 手法」组织。每条都真金白银踩过。

---

## 一、交付与运行环境

### 症状：资源 404 / 图片音频加载不出来
**原因**：预览类服务通常只映射**单个 HTML 文件**，同目录的 `audio/`、`images/` 一律 404。
**手法**：**一律单文件自包含**，图片和音频全部 base64 内嵌。
代价是文件变大（30 张图 + 60 段音频 ≈ 7MB），浏览器解析 base64 需 1-3 秒，属正常。

### 症状：有画面但**没有声音**，用户以为"音色没换成"
**原因**：预览面板**禁用音频播放**。代码播放失败后静默降级到系统语音，用户听到的还是旧的机械音，却以为换音色失败了。
**手法**：
1. 交付时**用 `open` 在系统浏览器打开**，不要指望预览面板；
2. **播放失败必须显式提示**（弹页内提示条），绝不能静默降级——否则用户和你会一起被误导，排查会绕好几轮。

### 症状：界面好看但**用户说"点击不动"**
**原因**：JS 在初始化阶段抛错，页面一个元素都没渲染。
**手法**：见下方「验证手法」。

---

## 二、语音

### 症状：声音"发飘"、不像本人
**原因**：用了 `say` 的 `[[pbas ±N]]`。它是**整体升降调**（相当于给整段录音调高低），**不是自然的语调曲线**。幅度大或一句话里切换多次，人声就变形了。
**手法**：**不要用它做抑扬顿挫**。想要起伏只能换在线 TTS。可用的只剩两个旋钮：
- 语速：`say -r 128~138`
- 停顿：标点后插 `[[slnc 毫秒]]`（逗号 ~320、句末 ~230）

### 症状：念到哪个字、字亮不起来 / 高亮和声音不同步
**原因**：长句和跟说短句合成了**一整段音频**，页面上无法知道切换点在哪。
**手法**：**长句、短句拆成两段独立音频**（`sXpY` / `sXpYs`），页面顺序播放，切换点天然精确。逐字则按 `currentTime / duration × 字数` 计算。

### 症状：`say` 把控制符号念出来了
**原因**：命令拼写错误时，`say` 会把它当普通文本读。
**手法**：加完命令后**实测验证**：
```bash
say -v "音色" -r 130 -o t.aiff "[[slnc 600]]测试"   # 时长应比不加长 0.6s
```

### 可用的内嵌命令（macOS `say`，实测）
| 命令 | 作用 | 备注 |
|---|---|---|
| `[[slnc N]]` | 插入 N 毫秒静音 | ✅ 稳定 |
| `[[pbas ±N]]` | 音高基准 | ⚠️ 整体升降调，**负值常常无效**，慎用 |
| `-r N` | 语速（不是命令，是参数） | ✅ |
| `[[volm N]]` | 音量 | 少用 |

---

## 三、AI 插画

### 症状：模型往画面里塞英文标注（MILK、YUM! 之类）
**手法**：prompt 末尾加死一句：
```
IMPORTANT: the image must contain absolutely no text, no letters, no words,
no numbers, no captions, no logo and no watermark anywhere.
```

### 症状：平台水印去不掉
**原因**：这类工具常**强制**加水印，参数和 prompt 都关不掉。
**手法**：后期抹。正解是**取水印区左侧等宽区域横向镜像后原样粘贴** —— 镜像保证接缝天然连续。
- ⚠️ **不要做整块高斯模糊**，会留一块明显的灰斑
- ⚠️ **不要从上方取源做纵向镜像**，上下底色不同会出现明显色差接缝
- **操作前务必备份原图**——否则返工时原图已被覆盖

### 症状：同一个故事里角色长得不一样
**手法**：角色描述串**逐字相同**，只改 `Scene:` 之后。
```
[固定角色串] + [固定风格串] + Scene: [本格场景] + [禁文字指令]
```
跨故事复用同一角色时，把角色串原样搬过去。

---

## 四、代码

### 症状：替换数据后整个页面变白板
**原因**：用 `s[:a] + new + s[b:]` 做区间替换时，`a` 和 `b` 之间**夹着别的代码**，被一起删掉了。
**手法**：锚点必须**紧邻目标**。例如替换一个数组元素，结束锚点要用 `'\n  ]\n },'` 这种紧贴的，**不要**用远处的 `index('const somethingElse=')`。

### 症状：图片放大后压到下面的文字
**原因**：`transform: scale()` 的元素**父容器没有裁切**。
**手法**：父容器加 `overflow:hidden` + `border-radius`（圆角交给容器）。

### 症状：判断"CSS 动画有没有生效"时得出错误结论
**原因**：**无头浏览器的截图不渲染动画中间帧**，两个时间点截图差异接近 0，会误判成"没生效"。
**手法**：用 `getAnimations()` 查动画实例：
```js
const el = document.querySelector('.art img');
const an = el.getAnimations();
document.title = 'RESULT|name=' + getComputedStyle(el).animationName +
                 ' anims=' + an.length + ' state=' + (an[0] && an[0].playState);
```
再用 `--dump-dom | grep "RESULT|"` 抓出来。`state=running` 就是真的在跑。

---

## 五、验证手法（交付前必跑）

### 无头浏览器诊断
```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --no-sandbox \
  --enable-logging=stderr --virtual-time-budget=9000 \
  --dump-dom "file:///绝对路径/绘本.html" 2>err.log >dom.html

grep -iE "uncaught|TypeError|ReferenceError" err.log   # 运行时错误
grep -o 'class="page' dom.html | wc -l                 # 应等于 故事数 × 每故事格数
```
或直接用 `scripts/check_page.py 绘本.html 6 5`。

**为什么必须做**：语法检查通过 ≠ 能跑。大段替换后很容易悄悄删掉渲染逻辑，语法仍然合法，但页面是白板。

### 校验 JS 语法（先剥掉超长的 base64，否则解析慢）
```python
js = re.findall(r'<script>(.*?)</script>', html, re.S)[-1]
js = re.sub(r'(src="data:image/jpeg;base64,)[^"]+"', r'\1"', js)
js = re.sub(r'const AUDIO_B64=\{.*?\};', 'const AUDIO_B64={};', js, flags=re.S)
```

---

## 六、执行环境

### `Path.mkdir(exist_ok=True)` 仍抛错
某些受限沙箱下，**对已存在的目录**调用 `mkdir(exist_ok=True)` 仍会抛 `EEXIST`。
**手法**：临时目录一律用 `tempfile.mkdtemp(prefix=...)`；必须用固定目录时逐个 `try/except` 兜住。

### 长跑脚本中途"静默死掉"
**原因**：`cmd | head -N` 会让脚本在写后续输出时收到 SIGPIPE 提前退出，可能**写不完最终文件**。
**手法**：输出重定向到日志文件，跑完再读：
```bash
python3 build.py > /tmp/run.log 2>&1; echo "退出码 $?"; tail -5 /tmp/run.log
```

### 删除文件被 Finder 拒绝
`osascript` 驱动 Finder 删除可能报「权限违例 -10004」。
**手法**：用 `mv 目标 ~/.Trash/名字` 直接移入废纸篓（可恢复，比 `rm` 安全）。

---

## 七、给孩子用的交互保护

### 需求：别让孩子乱点按钮
**手法**：控制栏**默认整体隐藏**，三种唤出方式——
1. **长按画面 1.2 秒**（判定要加容差：`pointermove` 位移 >8px 即取消，否则孩子滑动会误触）
2. 点右下角**几乎看不见的小灰点**（透明热区 + 7px 浅灰圆点）
3. 键盘 **P** 键

状态存 `localStorage`；**首次访问自动显示 6 秒**再收起，让家长知道有这些功能。
