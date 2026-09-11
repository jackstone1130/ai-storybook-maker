# 页面结构与交互机制

## 数据层

```js
const S = [
  {
    title: "故事名",
    tags: ["句型：先…然后…最后", "目标音：ch / sh"],
    pages: [
      {
        hint: "家长提示（怎么提问、做什么动作）",
        art:  `<img src="data:image/jpeg;base64,..." alt="...">`,   // 或用内联 SVG
        txt:  `长句，<em>句型词</em>高亮`,                            // 家长读
        say:  `孩子跟说的短句`                                        // 可选
      },
      // ... 每故事 N 格
    ]
  },
  // ... 更多故事
];
```

`say` 是**可选**字段——没有它就只有长句，页面不会渲染绿框。

## DOM 结构

```
.wrap
 ├ .howto                    使用说明
 ├ .picker#picker            故事选择按钮（由 S 渲染）
 └ .stage
    ├ #envNote               播放失败时的提示条
    ├ .storyhead             标题 + 句型标签
    ├ #pages                 所有故事的容器
    │  └ .story[data-i]      每个故事一个
    │     └ .page[data-j]    每格一个
    │        ├ .art          插画（img 或 svg）
    │        ├ .txt          长句（逐字拆成 <i class="c">）
    │        ├ .say          跟说句（可选）
    │        └ .hint         家长提示
    ├ .ctrl                  翻页 / 朗读 / 自动播放
    ├ .toolbar               动画开关 / 语音设置 / 停止
    └ .panel#voicePanel      语音设置面板
#allWrap                     打印用的全部画面
.allbar                      展开全部画面按钮
#peek                        右下角隐藏的家长入口
```

## 核心函数

| 函数 | 作用 |
|---|---|
| `wrapChars(html)` | 把一行文字拆成单字 `<i class="c">`；`<em>` 转成 `.c.em` 保留高亮色 |
| `render()` | 切换故事/页，更新标题、标签、进度点 |
| `playAudio(key, fallback, done, hlEl)` | 播一段音频；三级回落 base64 → 文件 → 系统语音；失败调 `noteEnv()` |
| `tickHL(a, el)` | `requestAnimationFrame` 里按 `currentTime/duration × 字数` 逐字点亮 |
| `playPage(done)` | 播当前格：长句（高亮大字）→ 短句（高亮绿框） |
| `playSeq()` | 「连着听一遍」：依次播各页长句，边播边翻页边高亮；`seqToken` 防串台 |
| `stopSpeak()` / `stopHL()` | 中断播放与高亮（`speakToken` 令牌） |

### 高亮更新的节奏

不要用 `timeupdate`（约 4Hz，太粗）。用 `requestAnimationFrame` 自己算：

```js
const step = () => {
  if (a !== curAudio || a.paused || a.ended) return;
  const d = a.duration || 0;
  const idx = d ? Math.min(n - 1, Math.floor(a.currentTime / d * n)) : 0;
  chars.forEach((c, i) => c.classList.toggle('on', i === idx));
  hlRAF = requestAnimationFrame(step);
};
hlRAF = requestAnimationFrame(step);
```

### 中断要用令牌

翻页、切故事、点停止都可能打断正在播放的音频。用自增令牌避免"旧任务继续跑"：

```js
let speakToken = 0;
function stopSpeak(){ speakToken++; speechSynthesis.cancel(); ... }
// 每段播放前记下 my = speakToken，回调里先比对 if (my !== speakToken) return;
```

## 样式要点

```css
/* 插画容器必须裁切，否则 Ken Burns 放大后会压到文字 */
.art{ width:100%; max-width:520px; overflow:hidden; border-radius:14px; }
.art img{ width:100%; display:block; transform-origin:center; }

/* 推拉镜头：奇偶页方向交替，避免呆板 */
.page:nth-child(odd)  .art img{ animation:kbA 16s ease-in-out infinite alternate; }
.page:nth-child(even) .art img{ animation:kbB 19s ease-in-out infinite alternate; }

/* 逐字高亮 */
.txt .c.on{ color:#fff; background:#E08A3C; border-radius:6px; }
.say .c.on{ color:#fff; background:#3E9C74; border-radius:6px; }

/* 打印视图里不要动画 */
.sheet .art img{ animation:none; }

/* 家长控制栏默认隐藏 */
body.hideui .ctrl,body.hideui .toolbar,body.hideui .picker{ opacity:0; pointer-events:none; }
body.hideui .panel{ display:none; }
```

## 打印

`.sheet` 里放全部画面，`@media print` 控制分页。点「展开全部画面」后浏览器直接打印即可装订成册。
注意打印视图里要**关掉动画**，否则截图/打印会拍到缩放中的画面。
