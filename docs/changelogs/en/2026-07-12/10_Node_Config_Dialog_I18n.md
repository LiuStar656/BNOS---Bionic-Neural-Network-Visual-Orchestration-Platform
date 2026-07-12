# 10 Node Config Dialog Internationalization

## Overview

Resolved 20 hardcoded mixed CN/EN strings in `node_config_dialog.py`, completing the i18n migration for the Resource Limits section and tooltip messages.

---

## I. Changes

| File | Change |
|------|------|
| `strings_cn.json` | +19 CN keys |
| `strings_en.json` | +19 EN keys |
| `translation_keys.py` | +19 class attributes |
| `node_config_dialog.py` | 20 `"..."` → `t(TK.KEY)` |

---

## II. Key Replacements (CN mode)

| Before | After |
|------|------|
| `"Resource Limits"` | `"资源限制"` |
| `"Priority:" / "Low" / "Normal"` | `"优先级:" / "低" / "正常"` |
| `"CPU Limit (%):"` | `"CPU 限制(%):"` |
| `"Memory Limit:"` | `"内存限制:"` |
| `"Unlimited"` | `"无限制"` |
| `"Apply Resource Limits"` | `"应用资源限制"` |
| tooltip `"100 = 1 core..."` | `"100 = 1 核, 200 = 2 核..."` |
| `"Applied: priority=low, cpu=200%"` | `"已应用: 优先级=低, cpu=200%"` |
| `"Resource limits cleared..."` | `"资源限制已清除（全部默认值）"` |

---

## III. Test Status

193/193 tests passed, ruff check all clear.
