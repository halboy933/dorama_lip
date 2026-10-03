#!/usr/bin/env python3
# Dorama Avatar LipSync updater V0.8
# Запускать из корня репозитория dorama_lip:
#   python3 dorama_lip_update_v0_8.py

from pathlib import Path
import sys

VERSION = "0.8"
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

def replace_required(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        print(f"ОШИБКА PATCH: не найден фрагмент {label}")
        sys.exit(4)
    return text.replace(old, new, 1)

def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    a = text.find(start_marker)
    if a < 0:
        print(f"ОШИБКА PATCH: не найдено начало {label}")
        sys.exit(5)
    b = text.find(end_marker, a)
    if b < 0:
        print(f"ОШИБКА PATCH: не найден конец {label}")
        sys.exit(6)
    return text[:a] + replacement + "\n\n    " + text[b:]

print("Dorama Avatar LipSync — применение V0.8 CALIBRATION")
print(f"Проект: {root}")

g = gradle_path.read_text(encoding="utf-8")
if 'versionName = "0.8"' not in g:
    g = replace_required(
        g,
        'versionCode = 7; versionName = "0.7"',
        'versionCode = 8; versionName = "0.8"',
        "versionCode/versionName V0.7"
    )
gradle_path.write_text(g, encoding="utf-8")

layout = '''<ScrollView xmlns:android="http://schemas.android.com/apk/res/android" android:layout_width="match_parent" android:layout_height="match_parent">
<LinearLayout android:orientation="vertical" android:padding="20dp" android:layout_width="match_parent" android:layout_height="wrap_content">
<TextView android:text="Dorama Avatar • V0.8 CALIBRATION" android:textSize="24sp" android:textStyle="bold" android:layout_width="wrap_content" android:layout_height="wrap_content"/>
<TextView android:id="@+id/status" android:text="Точная подгонка положения рта" android:paddingTop="12dp" android:paddingBottom="12dp" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<ProgressBar android:id="@+id/progress" style="?android:attr/progressBarStyleHorizontal" android:max="100" android:progress="0" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<ImageView android:id="@+id/preview" android:layout_width="match_parent" android:layout_height="360dp" android:scaleType="centerCrop" android:background="#222222"/>
<Button android:id="@+id/imageButton" android:text="1. Выбрать PNG/JPG" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<Button android:id="@+id/audioButton" android:text="2. Выбрать WAV" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<Button android:id="@+id/modelButton" android:text="3. Проверить / скачать Wav2Lip GAN 96" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:id="@+id/mouthOffsetLabel" android:text="Сдвиг рта: -4% (вверх)" android:textSize="17sp" android:textStyle="bold" android:paddingTop="14dp" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<SeekBar android:id="@+id/mouthOffsetSeek" android:max="20" android:progress="6" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:text="Лево = выше • центр = 0% • право = ниже. Диапазон −10…+10%. Начальное значение −4%." android:textSize="13sp" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<Button android:id="@+id/generateButton" android:text="4. Создать MP4 с этим сдвигом" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:text="V0.8: модель V0.7 не меняем. Сужена зона смешивания до области рта и добавлена ручная вертикальная калибровка, чтобы больше не собирать новую версию ради нескольких пикселей." android:paddingTop="16dp" android:layout_width="match_parent" android:layout_height="wrap_content"/>
</LinearLayout></ScrollView>
'''
layout_path.write_text(layout, encoding="utf-8")

m = main_path.read_text(encoding="utf-8")

if "mouthOffsetPercent" not in m:
    m = replace_required(
        m,
        "    private lateinit var progress: ProgressBar\n",
        "    private lateinit var progress: ProgressBar\n"
        "    private lateinit var mouthOffsetLabel: TextView\n"
        "    private var mouthOffsetPercent: Int = -4\n",
        "поля progress"
    )

if "mouthOffsetSeek" not in m:
    m = replace_required(
        m,
        "        progress = findViewById(R.id.progress)\n",
        '''        progress = findViewById(R.id.progress)
        mouthOffsetLabel = findViewById(R.id.mouthOffsetLabel)
        val mouthOffsetSeek = findViewById<SeekBar>(R.id.mouthOffsetSeek)
        mouthOffsetSeek.progress = mouthOffsetPercent + 10
        fun refreshMouthOffsetLabel() {
            val direction = when {
                mouthOffsetPercent < 0 -> "вверх"
                mouthOffsetPercent > 0 -> "вниз"
                else -> "без сдвига"
            }
            val signed = if (mouthOffsetPercent > 0) "+$mouthOffsetPercent" else "$mouthOffsetPercent"
            mouthOffsetLabel.text = "Сдвиг рта: $signed% ($direction)"
        }
        refreshMouthOffsetLabel()
        mouthOffsetSeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progressValue: Int, fromUser: Boolean) {
                mouthOffsetPercent = progressValue - 10
                refreshMouthOffsetLabel()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })
''',
        "onCreate progress"
    )

new_composite = r'''private fun compositeMouth(
        base: Bitmap,
        generated96: Bitmap,
        c: FaceCrop,
        offsetPercent: Int
    ): Bitmap {
        val out = base.copy(Bitmap.Config.ARGB_8888, true)
        val generated = Bitmap.createScaledBitmap(generated96, c.width, c.height, true)
        val original = IntArray(c.width * c.height)
        val gen = IntArray(c.width * c.height)
        out.getPixels(original, 0, c.width, c.left, c.top, c.width, c.height)
        generated.getPixels(gen, 0, c.width, 0, 0, c.width, c.height)

        // V0.8: отрицательное значение поднимает сгенерированный рот.
        val shiftPx = (c.height * offsetPercent / 100f).roundToInt()

        for (y in 0 until c.height) {
            val fy = y.toFloat() / max(1, c.height - 1)
            for (x in 0 until c.width) {
                val fx = x.toFloat() / max(1, c.width - 1)

                // Компактная эллиптическая область вокруг рта.
                val dx = (fx - 0.50f) / 0.38f
                val dy = (fy - 0.72f) / 0.22f
                val d2 = dx * dx + dy * dy

                val alpha = (1f - smoothStep(0.42f, 1.00f, d2)).coerceIn(0f, 1f)
                if (alpha <= 0f) continue

                val srcY = (y - shiftPx).coerceIn(0, c.height - 1)
                val srcX = x
                val dstIndex = y * c.width + x
                val srcIndex = srcY * c.width + srcX

                val a = original[dstIndex]
                val g = gen[srcIndex]
                fun mix(ca: Int, cg: Int) =
                    (ca * (1f - alpha) + cg * alpha).roundToInt().coerceIn(0, 255)

                original[dstIndex] = Color.rgb(
                    mix(Color.red(a), Color.red(g)),
                    mix(Color.green(a), Color.green(g)),
                    mix(Color.blue(a), Color.blue(g))
                )
            }
        }

        out.setPixels(original, 0, c.width, c.left, c.top, c.width, c.height)
        generated.recycle()
        return out
    }'''

if "private fun compositeMouth(" not in m:
    m = replace_between(
        m,
        "private fun compositeLower(",
        "private fun generate()",
        new_composite,
        "compositeLower"
    )

m = m.replace(
    "val composed = compositeLower(base, face, crop)",
    "val composed = compositeMouth(base, face, crop, mouthOffsetPercent)"
)

m = m.replace("V07_01_input_crop_", "V08_01_input_crop_")
m = m.replace("V07_02_wav2lip_face_", "V08_02_wav2lip_face_")
m = m.replace("V07_03_composite_before_encoder_", "V08_03_composite_before_encoder_")
m = m.replace('File(cacheDir, "v06_', 'File(cacheDir, "v08_')
m = m.replace("V0.7 lip-sync:", "V0.8 lip-sync:")
m = m.replace("✓ V0.7 ГОТОВА", "✓ V0.8 ГОТОВА")
m = m.replace(
    "Пришли V07_02 и V07_03 PNG + MP4. Проверим сырой выход Wav2Lip с FaceFusion GAN 96 и auto-layout.",
    'Сдвиг рта: ${mouthOffsetPercent}%\\nПришли V08_03 + MP4, если нужна ещё подгонка.'
)
m = m.replace(
    'Toast.makeText(this, "V0.7: MP4 + диагностические PNG сохранены", Toast.LENGTH_LONG).show()',
    'Toast.makeText(this, "V0.8: MP4 + PNG сохранены", Toast.LENGTH_LONG).show()'
)
m = m.replace("Ошибка V0.7:", "Ошибка V0.8:")
m = m.replace("DoramaAvatar_V07_", "DoramaAvatar_V08_")

main_path.write_text(m, encoding="utf-8")

w = workflow_path.read_text(encoding="utf-8")
w = w.replace("DoramaAvatarLipSync-v0.7-debug", "DoramaAvatarLipSync-v0.8-debug")
workflow_path.write_text(w, encoding="utf-8")

readme = '''Dorama Avatar LipSync V0.8 CALIBRATION

Цель V0.8: убрать небольшое вертикальное смещение рта, не меняя уже рабочую модель V0.7.

Изменения:
1) FaceFusion Wav2Lip GAN 96, mel, BGR и MP4 из V0.7 оставлены без изменений;
2) зона paste-back сужена: теперь заменяется в основном рот и ближайшая кожа;
3) добавлен ползунок вертикального сдвига рта от -10% до +10%;
4) стартовое значение -4% (поднять рот);
5) отрицательное значение = выше, положительное = ниже;
6) сохраняются V08_01, V08_02, V08_03 PNG;
7) MP4: DoramaAvatar_V08_*.mp4.

Главная идея: теперь для подгонки на несколько пикселей НЕ нужно собирать V0.9.
Можно менять ползунок и заново запускать генерацию.

Wav2Lip weights используются только как технический некоммерческий тест.
'''
readme_path.write_text(readme, encoding="utf-8")

for old in root.glob("DoramaAvatarLipSync_v0_*.zip"):
    try:
        old.unlink()
        print(f"Удалён старый архив: {old.name}")
    except OSError:
        pass

for old_name in ("dorama_lip_update_v0_6.py", "dorama_lip_update_v0_7.py"):
    old = root / old_name
    if old.exists():
        try:
            old.unlink()
            print(f"Удалён старый патчер: {old.name}")
        except OSError:
            pass

checks = [
    (gradle_path, 'versionName = "0.8"'),
    (layout_path, "Dorama Avatar • V0.8 CALIBRATION"),
    (layout_path, "mouthOffsetSeek"),
    (main_path, "private fun compositeMouth("),
    (main_path, "mouthOffsetPercent"),
    (main_path, "✓ V0.8 ГОТОВА"),
    (workflow_path, "DoramaAvatarLipSync-v0.8-debug"),
]

failed = []
for p, marker in checks:
    text = p.read_text(encoding="utf-8")
    if marker not in text:
        failed.append(f"{p.relative_to(root)} -> {marker}")

if failed:
    print("\nОШИБКА ПРОВЕРКИ V0.8:")
    for item in failed:
        print(" -", item)
    sys.exit(7)

print("\n✓ V0.8 применена")
print("✓ рабочая GAN-модель V0.7 сохранена")
print("✓ paste-back сужен до зоны рта")
print("✓ ползунок сдвига: -10% ... +10%")
print("✓ старт: -4% (вверх)")
print("✓ GitHub Actions artifact = v0.8-debug")
print("\nТеперь:")
print("  git status")
print("  git add -A")
print('  git commit -m "Add Dorama Avatar LipSync v0.8 calibration"')
print("  git push")
