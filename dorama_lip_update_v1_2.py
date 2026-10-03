#!/usr/bin/env python3
# Dorama Avatar LipSync V1.2 QUALITY
# Запуск:
#   cd /workspaces/dorama_lip
#   python3 dorama_lip_update_v1_2.py
#
# Требует V1.1. Постоянную подпись и GitHub Secrets НЕ меняет.

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

def replace_one(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        print(f"ОШИБКА PATCH: не найдено {label}")
        sys.exit(4)
    return text.replace(old, new, 1)

print("Dorama Avatar LipSync — V1.2 QUALITY")
print(f"Проект: {root}")

# ----------------------------------------------------------------------
# VERSION. applicationId/signing не меняем.
# ----------------------------------------------------------------------
g = gradle_path.read_text(encoding="utf-8")
g = replace_one(
    g,
    'versionCode = 11\n        versionName = "1.1"',
    'versionCode = 12\n        versionName = "1.2"',
    "versionCode/versionName V1.1",
)
gradle_path.write_text(g, encoding="utf-8")

# Убеждаемся, что стабильная подпись осталась на месте.
g_check = gradle_path.read_text(encoding="utf-8")
if 'applicationId = "com.dorama.avatar"' not in g_check or 'signingConfigs.create("stable")' not in g_check:
    print("ОШИБКА: постоянная подпись V1.1 не найдена. Останавливаюсь.")
    sys.exit(5)

# ----------------------------------------------------------------------
# UI. Все X/Y/Angle/Scale остаются.
# ----------------------------------------------------------------------
layout = layout_path.read_text(encoding="utf-8")
layout = layout.replace(
    "Dorama Avatar • V1.1 MOVING MASK",
    "Dorama Avatar • V1.2 QUALITY"
)
layout = layout.replace(
    "Рот и мягкая маска теперь двигаются вместе",
    "Улучшение резкости губ + более узкая мягкая маска"
)
layout = layout.replace(
    "Старт: X=+10%, Y=-6%, угол=0°, размер=100%. Настройки сохраняются.",
    "Геометрия сохраняется. Для текущего аватара ориентир: X=+15%, Y=-6%, угол=+3°, размер=89%."
)
layout_path.write_text(layout, encoding="utf-8")

# ----------------------------------------------------------------------
# MainActivity.
# ----------------------------------------------------------------------
m = main_path.read_text(encoding="utf-8")

# Новые стартовые значения только для чистой установки.
# На уже установленной V1.1 SharedPreferences сохранят реальные значения пользователя.
m = m.replace(
    "private var mouthOffsetXPercent: Int = 10",
    "private var mouthOffsetXPercent: Int = 15"
)
m = m.replace(
    "private var mouthAngleDeg: Int = 0",
    "private var mouthAngleDeg: Int = 3"
)
m = m.replace(
    "private var mouthScalePercent: Int = 100",
    "private var mouthScalePercent: Int = 89"
)
m = m.replace(
    'prefs.getInt("mouth_x", 10)',
    'prefs.getInt("mouth_x", 15)'
)
m = m.replace(
    'prefs.getInt("mouth_angle", 0)',
    'prefs.getInt("mouth_angle", 3)'
)
m = m.replace(
    'prefs.getInt("mouth_scale", 100)',
    'prefs.getInt("mouth_scale", 89)'
)

# Добавляем лёгкий unsharp-mask. Он применяется только к сгенерированной области,
# до геометрического преобразования и смешивания.
smooth_marker = '''    private fun smoothStep(edge0: Float, edge1: Float, x: Float): Float {
        if (edge1 <= edge0) return if (x >= edge1) 1f else 0f
        val t = ((x - edge0) / (edge1 - edge0)).coerceIn(0f, 1f)
        return t * t * (3f - 2f * t)
    }
'''

sharpen_helper = smooth_marker + r'''
    /*
     * V1.2 QUALITY:
     * лёгкая unsharp-маска после растягивания 96x96 на размер face crop.
     * Усиливаем края губ, но не применяем резкость ко всему исходному кадру.
     */
    private fun sharpenGenerated(src: Bitmap, amount: Float = 0.48f): Bitmap {
        val w = src.width
        val h = src.height
        if (w < 3 || h < 3) return src.copy(Bitmap.Config.ARGB_8888, true)

        val input = IntArray(w * h)
        val output = IntArray(w * h)
        src.getPixels(input, 0, w, 0, 0, w, h)

        // Края оставляем как есть.
        input.copyInto(output)

        fun sharpenChannel(center: Int, blur: Int): Int {
            return (center + amount * (center - blur))
                .roundToInt()
                .coerceIn(0, 255)
        }

        for (y in 1 until h - 1) {
            for (x in 1 until w - 1) {
                val i = y * w + x
                val c = input[i]
                val l = input[i - 1]
                val r = input[i + 1]
                val u = input[i - w]
                val d = input[i + w]

                // Быстрый мягкий blur: центр имеет больший вес.
                val br = (
                    Color.red(c) * 4 +
                    Color.red(l) + Color.red(r) +
                    Color.red(u) + Color.red(d)
                ) / 8
                val bg = (
                    Color.green(c) * 4 +
                    Color.green(l) + Color.green(r) +
                    Color.green(u) + Color.green(d)
                ) / 8
                val bb = (
                    Color.blue(c) * 4 +
                    Color.blue(l) + Color.blue(r) +
                    Color.blue(u) + Color.blue(d)
                ) / 8

                output[i] = Color.argb(
                    Color.alpha(c),
                    sharpenChannel(Color.red(c), br),
                    sharpenChannel(Color.green(c), bg),
                    sharpenChannel(Color.blue(c), bb)
                )
            }
        }

        return Bitmap.createBitmap(output, w, h, Bitmap.Config.ARGB_8888)
    }
'''

if "private fun sharpenGenerated(" not in m:
    m = replace_one(
        m,
        smooth_marker,
        sharpen_helper,
        "smoothStep для вставки sharpenGenerated",
    )

# В compositeMouth заменяем растянутый generated на sharpenedGenerated.
m = replace_one(
    m,
    '''        val generated = Bitmap.createScaledBitmap(generated96, c.width, c.height, true)

        val mouthCx = c.width * 0.50f''',
    '''        val generatedScaled = Bitmap.createScaledBitmap(generated96, c.width, c.height, true)
        val generated = sharpenGenerated(generatedScaled)
        generatedScaled.recycle()

        val mouthCx = c.width * 0.50f''',
    "масштабирование generated в compositeMouth",
)

# Сужаем только маску. Центр и Matrix НЕ меняем — геометрия V1.1 сохраняется.
m = replace_one(
    m,
    '''                val dx = (fx - 0.50f) / 0.34f
                val dy = (fy - 0.72f) / 0.19f
                val d2 = dx * dx + dy * dy

                val alpha = (
                    (1f - smoothStep(0.38f, 1.00f, d2)) * 255f
                ).roundToInt().coerceIn(0, 255)''',
    '''                // V1.2: маска уже, чтобы не размягчать щёки/нос/подбородок.
                // Центр тот же, поэтому выставленные X/Y/Angle/Scale не "съезжают".
                val dx = (fx - 0.50f) / 0.30f
                val dy = (fy - 0.72f) / 0.165f
                val d2 = dx * dx + dy * dy

                // В центре рот остаётся полностью сгенерированным,
                // feather короче и заканчивается раньше.
                val alpha = (
                    (1f - smoothStep(0.46f, 1.00f, d2)) * 255f
                ).roundToInt().coerceIn(0, 255)''',
    "маска V1.1",
)

# Имена диагностик/версий.
m = m.replace("V11_01_", "V12_01_")
m = m.replace("V11_02_", "V12_02_")
m = m.replace("V11_03_", "V12_03_")
m = m.replace('File(cacheDir, "v11_', 'File(cacheDir, "v12_')
m = m.replace("V1.1 lip-sync:", "V1.2 lip-sync:")
m = m.replace("✓ V1.1 ГОТОВА", "✓ V1.2 ГОТОВА")
m = m.replace("Ошибка V1.1:", "Ошибка V1.2:")
m = m.replace("DoramaAvatar_V11_", "DoramaAvatar_V12_")
m = m.replace(
    'Toast.makeText(this, "V1.1: MP4 + PNG сохранены", Toast.LENGTH_LONG).show()',
    'Toast.makeText(this, "V1.2: MP4 + PNG сохранены", Toast.LENGTH_LONG).show()'
)
m = m.replace(
    "V1.1: рот и feather-mask двигаются вместе.",
    "V1.2: moving-mask сохранена; зона губ уже + лёгкая резкость."
)

main_path.write_text(m, encoding="utf-8")

# ----------------------------------------------------------------------
# Workflow: ключ/Secrets НЕ меняем. Только имя artifact.
# ----------------------------------------------------------------------
w = workflow_path.read_text(encoding="utf-8")
if "DORAMA_KEYSTORE_B64" not in w:
    print("ОШИБКА: workflow без постоянного signing key. Останавливаюсь.")
    sys.exit(6)

w = replace_one(
    w,
    "DoramaAvatarLipSync-v1.1-stable",
    "DoramaAvatarLipSync-v1.2-stable",
    "artifact V1.1",
)
workflow_path.write_text(w, encoding="utf-8")

# ----------------------------------------------------------------------
# README.
# ----------------------------------------------------------------------
readme_path.write_text(
'''Dorama Avatar LipSync V1.2 — QUALITY

V1.2 НЕ меняет рабочую модель, mel, BGR, moving-mask, MP4 и постоянную подпись.

Что изменено:
1) X/Y/Angle/Scale полностью сохранены;
2) настройки продолжают храниться в SharedPreferences;
3) для чистой установки новый ориентир:
   X=+15%, Y=-6%, Angle=+3°, Scale=89%;
4) feather-mask стала уже вокруг губ:
   меньше затрагиваются щёки, нос и подбородок;
5) добавлена лёгкая unsharp-резкость только к сгенерированной зоне;
6) исходное изображение вне зоны губ вообще не шарпится;
7) диагностика: V12_01 / V12_02 / V12_03;
8) MP4: DoramaAvatar_V12_*.mp4.

Обновление:
- applicationId прежний: com.dorama.avatar;
- используется тот же stable signing key из V1.1;
- V1.2 должна устанавливаться поверх V1.1;
- модель в filesDir и настройки сохраняются, повторно скачивать модель не нужно.

Если качество после V1.2 достаточно для Shorts — это версия для первого выпуска рубрики.
Если остаётся заметная мягкость именно внутри губ, следующий уровень — более высокое
разрешение lip-sync-модели, а не дальнейшее усиление резкости 96x96.

Wav2Lip weights используются только как технический некоммерческий тест.
''',
encoding="utf-8",
)

# Чистим только старые updater-файлы. Secrets/keystore не трогаем.
for old_name in (
    "dorama_lip_update_v0_9.py",
    "dorama_lip_update_v1_0.py",
    "dorama_lip_update_v1_1.py",
):
    old = root / old_name
    if old.exists():
        try:
            old.unlink()
            print(f"Удалён старый патчер: {old.name}")
        except OSError:
            pass

# ----------------------------------------------------------------------
# CHECKS
# ----------------------------------------------------------------------
checks = [
    (gradle_path, 'versionName = "1.2"'),
    (gradle_path, 'versionCode = 12'),
    (gradle_path, 'applicationId = "com.dorama.avatar"'),
    (gradle_path, 'signingConfigs.create("stable")'),
    (layout_path, "Dorama Avatar • V1.2 QUALITY"),
    (main_path, "private fun sharpenGenerated("),
    (main_path, "val generated = sharpenGenerated(generatedScaled)"),
    (main_path, "/ 0.30f"),
    (main_path, "/ 0.165f"),
    (main_path, "smoothStep(0.46f, 1.00f, d2)"),
    (main_path, "V12_03"),
    (workflow_path, "DORAMA_KEYSTORE_B64"),
    (workflow_path, "DoramaAvatarLipSync-v1.2-stable"),
]

failed = []
for p, marker in checks:
    txt = p.read_text(encoding="utf-8")
    if marker not in txt:
        failed.append(f"{p.relative_to(root)} -> {marker}")

if failed:
    print("\nОШИБКА ПРОВЕРКИ V1.2:")
    for item in failed:
        print(" -", item)
    sys.exit(20)

print("\n✓ V1.2 QUALITY применена")
print("✓ X/Y/Angle/Scale оставлены")
print("✓ moving-mask V1.1 оставлена")
print("✓ маска вокруг губ стала уже")
print("✓ добавлена лёгкая резкость generated-зоны")
print("✓ stable signing key / GitHub Secrets НЕ изменялись")
print("✓ V1.2 рассчитана на установку ПОВЕРХ V1.1")
print("✓ модель и настройки при обновлении должны сохраниться")

print("\nТеперь:")
print("  git status")
print("  git add -A")
print('  git commit -m "Add Dorama Avatar LipSync v1.2 quality"')
print("  git push")
