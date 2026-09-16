# bridge/cases/bukit_bintang/ — 武吉免登案例

> 单案例工作区：吉隆坡武吉免登（Bukit Bintang）一日游素材 + AI 剪辑成片记录。

## 目录结构

```
bukit_bintang/
├── README.md                       ← 本文件
├── cover_out.png                   ← 案例封面（871 KB PNG，原根目录 `--out`）
├── scripts/                        ← 9 个一次性脚本（原 kuaishou/scripts/）
│   ├── build_fx_bukit.py
│   ├── build_voice_sticker_buk_item.py
│   ├── check_buk_item.py
│   ├── check_refs.py
│   ├── check_stickers.py
│   ├── extract_vip_fx.py
│   ├── extract_vip_fx2.py
│   ├── gen_tts_buk_item.py
│   ├── inspect_bukit.py
│   └── tmp_recon_bukit.py          ← 原根目录的 tmp_recon_bukit.py（并入此案例）
├── tmp/                            ← 案例本地模板 + 解析
│   ├── parse_draft_bukit_bintang.py
│   ├── cover_wrapper_template.json
│   ├── text_material_template.json
│   ├── text_segment_template.json
│   └── text_track_shell.json
└── scratchpad/                     ← 案例中间产物（3.05 MB）
    ├── backup_武吉免登_..._20260717_232531/
    ├── 还原_武吉免登_原视频_curve_backup/
    ├── tmp_subs_20260717_232510/
    ├── tmp_subs_20260717_232531/
    ├── translate_bukit_bintang_20260721/
    ├── apply_curve_clone.py
    ├── f1.jpg ~ f8.jpg
    ├── restore_backup.py
    ├── subs.txt
    └── verify_curves.py
```

## 操作流程（一次性脚本）

每个 `scripts/*.py` 完成一个原子操作，按需调用：

| 脚本 | 作用 |
|---|---|
| `inspect_bukit.py` | 检查 OS session 产物结构 |
| `gen_tts_buk_item.py` | 生成武吉免登项目的 TTS 配音 |
| `extract_vip_fx.py` / `extract_vip_fx2.py` | 从剪映客户端提取 VIP 特效 ID |
| `build_voice_sticker_buk_item.py` | 装配语音 + 贴纸 |
| `build_fx_bukit.py` | 注入 VIP 特效 |
| `check_buk_item.py` / `check_refs.py` / `check_stickers.py` | 校验成片各轨 |
| `tmp_recon_bukit.py` | 武吉免登本地侦查 |

## scratchpad/ 内容说明

- `backup_*/`：剪辑过程中的 clip_curve 备份（防回退）。
- `tmp_subs_*/`：字幕试错版本。
- `translate_bukit_bintang_20260721/`：小红书 / 抖音风格字幕文案（含英文版）。
- `f1.jpg ~ f8.jpg`：分镜抽帧，用于画面分析。
- `restore_backup.py` / `apply_curve_clone.py` / `verify_curves.py`：曲线回退 / 克隆 / 校验。

## 模板副本（tmp/）

`bridge/cases/bukit_bintang/tmp/` 与 `bridge/tmp/`（顶层公共模板）内容相同；两份都保留：本目录作为案例本地副本（方便对照），`bridge/tmp/` 作为公共模板（跨案例复用）。如需去重，运行 `kuaishou-clean-cache` skill 评估。
