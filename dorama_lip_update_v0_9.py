#!/usr/bin/env python3
# Dorama Avatar LipSync updater V0.9 XY CALIBRATION
# Запускать из корня репозитория dorama_lip:
#   python3 dorama_lip_update_v0_9.py

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

def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        print(f"ОШИБКА PATCH: не найдено {label}: {marker}")
        sys.exit(4)

def replace_required(text: str, old: str, new: str, label: str) -> str:
    require(text, old, label)
    return text.replace(old, new, 1)

print("Dorama Avatar LipSync — применение V0.9 XY CALIBRATION")
print(f"Проект: {root}")

# version
g = gradle_path.read_text(encoding="utf-8")
if 'versionName = "0.9"' not in g:
    g = replace_required(
        g,
        'versionCode = 8; versionName = "0.8"',
        'versionCode = 9; versionName = "0.9"',
        "versionCode/versionName V0.8",
    )
gradle_path.write_text(g, encoding="utf-8")

# UI
layout = '''<ScrollView xmlns:android="http://schemas.android.com/apk/res/android" android:layout_width="match_parent" android:layout_height="match_parent">
<LinearLayout android:orientation="vertical" android:padding="20dp" android:layout_width="match_parent" android:layout_height="wrap_content">
<TextView android:text="Dorama Avatar • V0.9 XY CALIBRATION" android:textSize="24sp" android:textStyle="bold" android:layout_width="wrap_content" android:layout_height="wrap_content"/>
<TextView android:id="@+id/status" android:text="Точная подгонка рта по X и Y" android:paddingTop="12dp" android:paddingBottom="12dp" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<ProgressBar android:id="@+id/progress" style="?android:attr/progressBarStyleHorizontal" android:max="100" android:progress="0" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<ImageView android:id="@+id/preview" android:layout_width="match_parent" android:layout_height="360dp" android:scaleType="centerCrop" android:background="#222222"/>
<Button android:id="@+id/imageButton" android:text="1. Выбрать PNG/JPG" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<Button android:id="@+id/audioButton" android:text="2. Выбрать WAV" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<Button android:id="@+id/modelButton" android:text="3. Проверить / скачать Wav2Lip GAN 96" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:id="@+id/mouthOffsetXLabel" android:text="X: 0% (по центру)" android:textSize="17sp" android:textStyle="bold" android:paddingTop="14dp" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<SeekBar android:id="@+id/mouthOffsetXSeek" android:max="20" android:progress="10" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:text="X: лево = −10% • центр = 0% • право = +10%" android:textSize="13sp" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:id="@+id/mouthOffsetYLabel" android:text="Y: -4% (вверх)" android:textSize="17sp" android:textStyle="bold" android:paddingTop="10dp" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<SeekBar android:id="@+id/mouthOffsetYSeek" android:max="20" android:progress="6" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:text="Y: вверх = −10% • центр = 0% • вниз = +10%" android:textSize="13sp" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<Button android:id="@+id/generateButton" android:text="4. Создать MP4 с этими X/Y" android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:text="V0.9: рабочую модель V0.7 и mel не меняем. Теперь рот можно двигать по двум осям без новой сборки. Старт: X=0%, Y=-4%." android:paddingTop="16dp" android:layout_width="match_parent" android:layout_height="wrap_content"/>
</LinearLayout>
</ScrollView>
'''
layout_path.write_text(layout, encoding="utf-8")

# MainActivity
m = main_path.read_text(encoding="utf-8")

old_fields = '''    private lateinit var mouthOffsetLabel: TextView
    private var mouthOffsetPercent: Int = -4
'''
new_fields = '''    private lateinit var mouthOffsetXLabel: TextView
    private lateinit var mouthOffsetYLabel: TextView
    private var mouthOffsetXPercent: Int = 0
    private var mouthOffsetYPercent: Int = -4
'''
if "mouthOffsetXPercent" not in m:
    m = replace_required(m, old_fields, new_fields, "V0.8 offset fields")

start = m.find("        mouthOffsetLabel = findViewById(R.id.mouthOffsetLabel)")
end = m.find('        findViewById<Button>(R.id.imageButton)', start)
if start < 0 or end < 0:
    print("ОШИБКА PATCH: не найден блок калибровки V0.8 в onCreate")
    sys.exit(5)

new_ui_block = '''        mouthOffsetXLabel = findViewById(R.id.mouthOffsetXLabel)
        mouthOffsetYLabel = findViewById(R.id.mouthOffsetYLabel)
        val mouthOffsetXSeek = findViewById<SeekBar>(R.id.mouthOffsetXSeek)
        val mouthOffsetYSeek = findViewById<SeekBar>(R.id.mouthOffsetYSeek)
        mouthOffsetXSeek.progress = mouthOffsetXPercent + 10
        mouthOffsetYSeek.progress = mouthOffsetYPercent + 10

        fun refreshXLabel() {
            val direction = when {
                mouthOffsetXPercent < 0 -> "влево"
                mouthOffsetXPercent > 0 -> "вправо"
                else -> "по центру"
            }
            val signed = if (mouthOffsetXPercent > 0) "+$mouthOffsetXPercent" else "$mouthOffsetXPercent"
            mouthOffsetXLabel.text = "X: $signed% ($direction)"
        }

        fun refreshYLabel() {
            val direction = when {
                mouthOffsetYPercent < 0 -> "вверх"
                mouthOffsetYPercent > 0 -> "вниз"
                else -> "по центру"
            }
            val signed = if (mouthOffsetYPercent > 0) "+$mouthOffsetYPercent" else "$mouthOffsetYPercent"
            mouthOffsetYLabel.text = "Y: $signed% ($direction)"
        }

        refreshXLabel()
        refreshYLabel()

        mouthOffsetXSeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progressValue: Int, fromUser: Boolean) {
                mouthOffsetXPercent = progressValue - 10
                refreshXLabel()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        mouthOffsetYSeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progressValue: Int, fromUser: Boolean) {
                mouthOffsetYPercent = progressValue - 10
                refreshYLabel()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })
'''
m = m[:start] + new_ui_block + m[end:]

m = replace_required(
    m,
    '''    private fun compositeMouth(
        base: Bitmap,
        generated96: Bitmap,
        c: FaceCrop,
        offsetPercent: Int
    ): Bitmap {''',
    '''    private fun compositeMouth(
        base: Bitmap,
        generated96: Bitmap,
        c: FaceCrop,
        offsetXPercent: Int,
        offsetYPercent: Int
    ): Bitmap {''',
    "compositeMouth signature",
)

m = replace_required(
    m,
    '''        // V0.8: отрицательное значение поднимает сгенерированный рот.
        val shiftPx = (c.height * offsetPercent / 100f).roundToInt()
''',
    '''        // V0.9: независимый сдвиг по X и Y.
        // Отрицательный X = влево, положительный X = вправо.
        // Отрицательный Y = вверх, положительный Y = вниз.
        val shiftX = (c.width * offsetXPercent / 100f).roundToInt()
        val shiftY = (c.height * offsetYPercent / 100f).roundToInt()
''',
    "V0.8 shift",
)

m = replace_required(
    m,
    '''                val srcY = (y - shiftPx).coerceIn(0, c.height - 1)
                val srcX = x
''',
    '''                val srcY = (y - shiftY).coerceIn(0, c.height - 1)
                val srcX = (x - shiftX).coerceIn(0, c.width - 1)
''',
    "source XY mapping",
)

m = replace_required(
    m,
    "val composed = compositeMouth(base, face, crop, mouthOffsetPercent)",
    "val composed = compositeMouth(base, face, crop, mouthOffsetXPercent, mouthOffsetYPercent)",
    "compositeMouth call",
)

m = m.replace("V08_01_input_crop_", "V09_01_input_crop_")
m = m.replace("V08_02_wav2lip_face_", "V09_02_wav2lip_face_")
m = m.replace("V08_03_composite_before_encoder_", "V09_03_composite_before_encoder_")
m = m.replace('File(cacheDir, "v08_', 'File(cacheDir, "v09_')
m = m.replace("V0.8 lip-sync:", "V0.9 lip-sync:")
m = m.replace("✓ V0.8 ГОТОВА", "✓ V0.9 ГОТОВА")
m = m.replace(
    'Сдвиг рта: ${mouthOffsetPercent}%\\nПришли V08_03 + MP4, если нужна ещё подгонка.',
    'X: ${mouthOffsetXPercent}% • Y: ${mouthOffsetYPercent}%\\nПришли V09_03 + MP4, если нужна ещё подгонка.'
)
m = m.replace(
    'Toast.makeText(this, "V0.8: MP4 + PNG сохранены", Toast.LENGTH_LONG).show()',
    'Toast.makeText(this, "V0.9: MP4 + PNG сохранены", Toast.LENGTH_LONG).show()'
)
m = m.replace("Ошибка V0.8:", "Ошибка V0.9:")
m = m.replace("DoramaAvatar_V08_", "DoramaAvatar_V09_")

main_path.write_text(m, encoding="utf-8")

# workflow
w = workflow_path.read_text(encoding="utf-8")
w = replace_required(
    w,
    "DoramaAvatarLipSync-v0.8-debug",
    "DoramaAvatarLipSync-v0.9-debug",
    "workflow artifact v0.8",
)
workflow_path.write_text(w, encoding="utf-8")

# README
readme_path.write_text(
'''Dorama Avatar LipSync V0.9 XY CALIBRATION

Цель: точная ручная подгонка рта под разные картинки без новых сборок.

Что изменено:
1) рабочая FaceFusion Wav2Lip GAN 96 из V0.7 сохранена;
2) mel/BGR/ONNX/MP4 не менялись;
3) к вертикальному Y-сдвигу добавлен горизонтальный X-сдвиг;
4) X: -10% влево ... 0% ... +10% вправо;
5) Y: -10% вверх ... 0% ... +10% вниз;
6) стартовые значения: X=0%, Y=-4%;
7) маска остаётся компактной вокруг рта;
8) диагностика: V09_01, V09_02, V09_03;
9) MP4: DoramaAvatar_V09_*.mp4.

Теперь для новой картинки можно подогнать X/Y прямо на телефоне.
Если наклон рта всё ещё будет заметен после точного X/Y, следующим шагом будет небольшой Angle-ползунок.

Wav2Lip weights используются только как технический некоммерческий тест.
''',
encoding="utf-8"
)

old = root / "dorama_lip_update_v0_8.py"
if old.exists():
    try:
        old.unlink()
        print("Удалён старый патчер: dorama_lip_update_v0_8.py")
    except OSError:
        pass

checks = [
    (gradle_path, 'versionName = "0.9"'),
    (layout_path, "Dorama Avatar • V0.9 XY CALIBRATION"),
    (layout_path, "mouthOffsetXSeek"),
    (layout_path, "mouthOffsetYSeek"),
    (main_path, "mouthOffsetXPercent"),
    (main_path, "mouthOffsetYPercent"),
    (main_path, "val shiftX ="),
    (main_path, "val shiftY ="),
    (main_path, "✓ V0.9 ГОТОВА"),
    (workflow_path, "DoramaAvatarLipSync-v0.9-debug"),
]

failed = []
for p, marker in checks:
    txt = p.read_text(encoding="utf-8")
    if marker not in txt:
        failed.append(f"{p.relative_to(root)} -> {marker}")

if failed:
    print("\nОШИБКА ПРОВЕРКИ V0.9:")
    for item in failed:
        print(" -", item)
    sys.exit(7)

print("\n✓ V0.9 применена")
print("✓ X offset: -10% ... +10%")
print("✓ Y offset: -10% ... +10%")
print("✓ старт X=0%, Y=-4%")
print("✓ рабочая модель V0.7 сохранена")
print("✓ GitHub Actions artifact = v0.9-debug")
print("\nТеперь:")
print("  git status")
print("  git add -A")
print('  git commit -m "Add Dorama Avatar LipSync v0.9 XY calibration"')
print("  git push")
