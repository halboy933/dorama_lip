#!/usr/bin/env python3
# Dorama Avatar LipSync V1.3.1 — EDTalk 256 LOCAL MOUTH BLEND
# Run from /workspaces/dorama_lip AFTER V1.3.

from pathlib import Path
import sys

root = Path.cwd()
if root.name != "dorama_lip":
    print(f"ОШИБКА: сейчас открыта папка {root}")
    print("Перейди в /workspaces/dorama_lip и запусти файл ещё раз.")
    sys.exit(2)

main_path = root / "app/src/main/java/com/dorama/avatar/MainActivity.kt"
gradle_path = root / "app/build.gradle.kts"
layout_path = root / "app/src/main/res/layout/activity_main.xml"
workflow_path = root / ".github/workflows/build-apk.yml"
readme_path = root / "README_RU.txt"

for p in (main_path, gradle_path, layout_path, workflow_path):
    if not p.exists():
        print(f"ОШИБКА: не найден файл {p}")
        sys.exit(3)

def replace_one(text, old, new, label):
    if old not in text:
        print(f"ОШИБКА PATCH: не найдено {label}")
        sys.exit(4)
    return text.replace(old, new, 1)

print("Dorama Avatar LipSync — V1.3.1 LOCAL MOUTH BLEND")

# Require the exact V1.3 baseline.
g = gradle_path.read_text(encoding="utf-8")
g = replace_one(g,
    'versionCode = 13\n        versionName = "1.3"',
    'versionCode = 14\n        versionName = "1.3.1"',
    "version V1.3")
if 'signingConfigs.create("stable")' not in g:
    print("ОШИБКА: stable signing не найден. Останавливаюсь.")
    sys.exit(5)
gradle_path.write_text(g, encoding="utf-8")

m = main_path.read_text(encoding="utf-8")
if "edtalk_facefusion_256.onnx" not in m:
    print("ОШИБКА: EDTalk 256 из V1.3 не найден.")
    sys.exit(6)

# V1.3 used a relatively broad ellipse. V1.3.1 keeps original eyes/nose/cheeks
# and lets EDTalk replace mainly lips + immediate chin area.
m = replace_one(m,
    '''                val dx = (fx - 0.50f) / 0.32f\n                val dy = (fy - 0.72f) / 0.18f''',
    '''                // V1.3.1: narrow mouth-local mask. Preserve original face detail.\n                val dx = (fx - 0.50f) / 0.255f\n                val dy = (fy - 0.735f) / 0.125f''',
    "V1.3 mouth mask ellipse")

m = replace_one(m,
    "smoothStep(0.44f, 1.00f, d2)",
    "smoothStep(0.36f, 1.00f, d2)",
    "V1.3 mask feather")

# For 256 output add only a very mild detail recovery. Existing sharpenGenerated
# is useful for 96 but too strong for EDTalk, so blend 18% sharpened + 82% native.
old_quality = '''        val generated = if (generated96.width <= 96) {\n            val sharp = sharpenGenerated(generatedScaled)\n            generatedScaled.recycle()\n            sharp\n        } else {\n            generatedScaled\n        }'''
new_quality = '''        val generated = if (generated96.width <= 96) {\n            val sharp = sharpenGenerated(generatedScaled)\n            generatedScaled.recycle()\n            sharp\n        } else {\n            // V1.3.1: EDTalk 256 gets only a light detail recovery.\n            // Do not sharpen the original face; this bitmap is used only under mouth mask.\n            val sharp = sharpenGenerated(generatedScaled)\n            val detail = Bitmap.createBitmap(generatedScaled.width, generatedScaled.height, Bitmap.Config.ARGB_8888)\n            val canvas = Canvas(detail)\n            val pBase = Paint(Paint.ANTI_ALIAS_FLAG).apply { alpha = 209 } // 82%\n            val pSharp = Paint(Paint.ANTI_ALIAS_FLAG).apply { alpha = 46 } // 18%\n            canvas.drawBitmap(generatedScaled, 0f, 0f, pBase)\n            canvas.drawBitmap(sharp, 0f, 0f, pSharp)\n            sharp.recycle()\n            generatedScaled.recycle()\n            detail\n        }'''
m = replace_one(m, old_quality, new_quality, "V1.3 quality branch")

m = m.replace("V13_01_input_crop_", "V131_01_input_crop_")
m = m.replace("V13_02_edtalk256_face_", "V131_02_edtalk256_face_")
m = m.replace("V13_02_wav2lip96_face_", "V131_02_wav2lip96_face_")
m = m.replace("V13_03_composite_before_encoder_", "V131_03_composite_before_encoder_")
m = m.replace('"✓ V1.3 ГОТОВА\\n"', '"✓ V1.3.1 ГОТОВА\\n"')
m = m.replace('"V1.3: $engineLabel — MP4 готов"', '"V1.3.1: $engineLabel — MP4 готов"')
m = m.replace('"Ошибка V1.3 ${activeModelLabel()}: "', '"Ошибка V1.3.1 ${activeModelLabel()}: "')
m = m.replace('File(cacheDir, "v13_${System.currentTimeMillis()}.mp4")', 'File(cacheDir, "v131_${System.currentTimeMillis()}.mp4")')
m = m.replace("DoramaAvatar_V13_", "DoramaAvatar_V131_")
main_path.write_text(m, encoding="utf-8")

layout = layout_path.read_text(encoding="utf-8")
layout = layout.replace("Dorama Avatar • V1.3 EDTalk 256", "Dorama Avatar • V1.3.1 EDTalk 256")
layout = layout.replace("V1.3: EDTalk 256 — основной режим качества.", "V1.3.1: EDTalk 256 + LOCAL MOUTH BLEND. Исходная резкость лица сохраняется.")
layout_path.write_text(layout, encoding="utf-8")

workflow = workflow_path.read_text(encoding="utf-8")
workflow = replace_one(workflow,
    "DoramaAvatarLipSync-v1.3-stable",
    "DoramaAvatarLipSync-v1.3.1-stable",
    "workflow V1.3 artifact")
workflow_path.write_text(workflow, encoding="utf-8")

readme_path.write_text('''Dorama Avatar LipSync V1.3.1 — LOCAL MOUTH BLEND\n\nОснова: V1.3 EDTalk 256x256.\n\nИзменения V1.3.1:\n- лицо больше не заменяется широкой областью EDTalk;\n- маска сужена к губам и ближайшей зоне подбородка;\n- глаза, нос, лоб и большая часть щек остаются из исходной фотографии;\n- для EDTalk 256 добавлено очень мягкое восстановление деталей (18% sharpen);\n- края маски остаются плавными;\n- X/Y/Angle/Scale сохранены;\n- Wav2Lip 96 сохранен как fallback;\n- stable signing не меняется;\n- EDTalk 256 повторно скачивать не нужно.\n\nСтартовые параметры аватара:\nX=+15%, Y=-6%, Angle=+3°, Scale=89%.\n\nДиагностика:\nV131_01_input_crop\nV131_02_edtalk256_face\nV131_03_composite_before_encoder\nDoramaAvatar_V131_*.mp4\n''', encoding="utf-8")

checks = [
    (gradle_path, 'versionName = "1.3.1"'),
    (gradle_path, 'versionCode = 14'),
    (gradle_path, 'signingConfigs.create("stable")'),
    (main_path, '0.255f'),
    (main_path, '0.125f'),
    (main_path, 'alpha = 46'),
    (main_path, 'edtalk_facefusion_256.onnx'),
    (workflow_path, 'DoramaAvatarLipSync-v1.3.1-stable'),
]
failed = [f"{p.relative_to(root)} -> {marker}" for p, marker in checks if marker not in p.read_text(encoding="utf-8")]
if failed:
    print("\\nОШИБКА ПРОВЕРКИ V1.3.1:")
    for item in failed: print(" -", item)
    sys.exit(20)

print("\\n✓ V1.3.1 LOCAL MOUTH BLEND применена")
print("✓ EDTalk 256 сохранён")
print("✓ маска сужена до рта/подбородка")
print("✓ исходные глаза/нос/щёки сохраняются")
print("✓ мягкое восстановление деталей EDTalk: 18%")
print("✓ X/Y/Angle/Scale сохранены")
print("✓ stable signing НЕ менялся")
print("✓ модель повторно скачивать НЕ нужно")
print("\\nСначала выполни только: git status")
