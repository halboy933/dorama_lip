#!/usr/bin/env python3
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

print("Dorama Avatar LipSync — применение V1.0 FULL CALIBRATION")
print(f"Проект: {root}")

g = gradle_path.read_text(encoding="utf-8")
if 'versionName = "1.0"' not in g:
    g = replace_one(
        g,
        'versionCode = 9; versionName = "0.9"',
        'versionCode = 10; versionName = "1.0"',
        "versionCode/versionName V0.9",
    )
gradle_path.write_text(g, encoding="utf-8")

layout = '''<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent">
<LinearLayout
    android:orientation="vertical"
    android:padding="20dp"
    android:layout_width="match_parent"
    android:layout_height="wrap_content">

<TextView android:text="Dorama Avatar • V1.0 CALIBRATION"
    android:textSize="24sp" android:textStyle="bold"
    android:layout_width="wrap_content" android:layout_height="wrap_content"/>

<TextView android:id="@+id/status"
    android:text="Подгонка рта: X / Y / угол / размер"
    android:paddingTop="12dp" android:paddingBottom="12dp"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>

<ProgressBar android:id="@+id/progress"
    style="?android:attr/progressBarStyleHorizontal"
    android:max="100" android:progress="0"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>

<ImageView android:id="@+id/preview"
    android:layout_width="match_parent" android:layout_height="330dp"
    android:scaleType="centerCrop" android:background="#222222"/>

<Button android:id="@+id/imageButton" android:text="1. Выбрать PNG/JPG"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<Button android:id="@+id/audioButton" android:text="2. Выбрать WAV"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<Button android:id="@+id/modelButton" android:text="3. Проверить / скачать Wav2Lip GAN 96"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>

<TextView android:id="@+id/mouthOffsetXLabel" android:text="X: +10% (вправо)"
    android:textSize="16sp" android:textStyle="bold" android:paddingTop="12dp"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<SeekBar android:id="@+id/mouthOffsetXSeek" android:max="40" android:progress="30"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:text="X: −20% влево • 0% центр • +20% вправо"
    android:textSize="12sp" android:layout_width="match_parent" android:layout_height="wrap_content"/>

<TextView android:id="@+id/mouthOffsetYLabel" android:text="Y: -6% (вверх)"
    android:textSize="16sp" android:textStyle="bold" android:paddingTop="8dp"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<SeekBar android:id="@+id/mouthOffsetYSeek" android:max="30" android:progress="9"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:text="Y: −15% вверх • 0% центр • +15% вниз"
    android:textSize="12sp" android:layout_width="match_parent" android:layout_height="wrap_content"/>

<TextView android:id="@+id/mouthAngleLabel" android:text="Угол: 0°"
    android:textSize="16sp" android:textStyle="bold" android:paddingTop="8dp"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<SeekBar android:id="@+id/mouthAngleSeek" android:max="24" android:progress="12"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:text="Угол: −12° ... 0° ... +12°"
    android:textSize="12sp" android:layout_width="match_parent" android:layout_height="wrap_content"/>

<TextView android:id="@+id/mouthScaleLabel" android:text="Размер: 100%"
    android:textSize="16sp" android:textStyle="bold" android:paddingTop="8dp"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<SeekBar android:id="@+id/mouthScaleSeek" android:max="30" android:progress="15"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:text="Размер: 85% ... 100% ... 115%"
    android:textSize="12sp" android:layout_width="match_parent" android:layout_height="wrap_content"/>

<Button android:id="@+id/generateButton" android:text="4. Создать MP4 с этими настройками"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>

<TextView android:text="Стартовый пресет: X=+10%, Y=-6%, угол=0°, размер=100%. Настройки запоминаются."
    android:paddingTop="14dp" android:layout_width="match_parent" android:layout_height="wrap_content"/>

</LinearLayout>
</ScrollView>
'''
layout_path.write_text(layout, encoding="utf-8")

m = main_path.read_text(encoding="utf-8")

old_fields = '''    private lateinit var mouthOffsetXLabel: TextView
    private lateinit var mouthOffsetYLabel: TextView
    private var mouthOffsetXPercent: Int = 0
    private var mouthOffsetYPercent: Int = -4
'''
new_fields = '''    private lateinit var mouthOffsetXLabel: TextView
    private lateinit var mouthOffsetYLabel: TextView
    private lateinit var mouthAngleLabel: TextView
    private lateinit var mouthScaleLabel: TextView
    private var mouthOffsetXPercent: Int = 10
    private var mouthOffsetYPercent: Int = -6
    private var mouthAngleDeg: Int = 0
    private var mouthScalePercent: Int = 100
'''
if "mouthAngleDeg" not in m:
    m = replace_one(m, old_fields, new_fields, "поля калибровки V0.9")

start = m.find("        mouthOffsetXLabel = findViewById(R.id.mouthOffsetXLabel)")
end = m.find('        findViewById<Button>(R.id.imageButton)', start)
if start < 0 or end < 0:
    print("ОШИБКА PATCH: не найден блок калибровки onCreate V0.9")
    sys.exit(5)

new_ui = '''        mouthOffsetXLabel = findViewById(R.id.mouthOffsetXLabel)
        mouthOffsetYLabel = findViewById(R.id.mouthOffsetYLabel)
        mouthAngleLabel = findViewById(R.id.mouthAngleLabel)
        mouthScaleLabel = findViewById(R.id.mouthScaleLabel)

        val prefs = getSharedPreferences("dorama_avatar_calibration", MODE_PRIVATE)
        mouthOffsetXPercent = prefs.getInt("mouth_x", 10)
        mouthOffsetYPercent = prefs.getInt("mouth_y", -6)
        mouthAngleDeg = prefs.getInt("mouth_angle", 0)
        mouthScalePercent = prefs.getInt("mouth_scale", 100)

        val mouthOffsetXSeek = findViewById<SeekBar>(R.id.mouthOffsetXSeek)
        val mouthOffsetYSeek = findViewById<SeekBar>(R.id.mouthOffsetYSeek)
        val mouthAngleSeek = findViewById<SeekBar>(R.id.mouthAngleSeek)
        val mouthScaleSeek = findViewById<SeekBar>(R.id.mouthScaleSeek)

        mouthOffsetXSeek.progress = (mouthOffsetXPercent + 20).coerceIn(0, 40)
        mouthOffsetYSeek.progress = (mouthOffsetYPercent + 15).coerceIn(0, 30)
        mouthAngleSeek.progress = (mouthAngleDeg + 12).coerceIn(0, 24)
        mouthScaleSeek.progress = (mouthScalePercent - 85).coerceIn(0, 30)

        fun refreshCalibrationLabels() {
            fun signed(v: Int): String = if (v > 0) "+$v" else "$v"
            val xDir = when {
                mouthOffsetXPercent < 0 -> "влево"
                mouthOffsetXPercent > 0 -> "вправо"
                else -> "центр"
            }
            val yDir = when {
                mouthOffsetYPercent < 0 -> "вверх"
                mouthOffsetYPercent > 0 -> "вниз"
                else -> "центр"
            }
            mouthOffsetXLabel.text = "X: ${signed(mouthOffsetXPercent)}% ($xDir)"
            mouthOffsetYLabel.text = "Y: ${signed(mouthOffsetYPercent)}% ($yDir)"
            mouthAngleLabel.text = "Угол: ${signed(mouthAngleDeg)}°"
            mouthScaleLabel.text = "Размер: ${mouthScalePercent}%"
        }

        fun saveCalibration() {
            prefs.edit()
                .putInt("mouth_x", mouthOffsetXPercent)
                .putInt("mouth_y", mouthOffsetYPercent)
                .putInt("mouth_angle", mouthAngleDeg)
                .putInt("mouth_scale", mouthScalePercent)
                .apply()
        }

        refreshCalibrationLabels()

        mouthOffsetXSeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, value: Int, fromUser: Boolean) {
                mouthOffsetXPercent = value - 20
                refreshCalibrationLabels()
                if (fromUser) saveCalibration()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        mouthOffsetYSeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, value: Int, fromUser: Boolean) {
                mouthOffsetYPercent = value - 15
                refreshCalibrationLabels()
                if (fromUser) saveCalibration()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        mouthAngleSeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, value: Int, fromUser: Boolean) {
                mouthAngleDeg = value - 12
                refreshCalibrationLabels()
                if (fromUser) saveCalibration()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        mouthScaleSeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, value: Int, fromUser: Boolean) {
                mouthScalePercent = 85 + value
                refreshCalibrationLabels()
                if (fromUser) saveCalibration()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })
'''
m = m[:start] + new_ui + m[end:]

func_start = m.find("    private fun compositeMouth(")
func_end = m.find("    private fun generate()", func_start)
if func_start < 0 or func_end < 0:
    print("ОШИБКА PATCH: не найдена compositeMouth")
    sys.exit(6)

new_composite = r'''    private fun compositeMouth(
        base: Bitmap,
        generated96: Bitmap,
        c: FaceCrop,
        offsetXPercent: Int,
        offsetYPercent: Int,
        angleDeg: Int,
        scalePercent: Int
    ): Bitmap {
        val out = base.copy(Bitmap.Config.ARGB_8888, true)
        val generated = Bitmap.createScaledBitmap(generated96, c.width, c.height, true)

        val transformed = Bitmap.createBitmap(c.width, c.height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(transformed)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
        val mouthCx = c.width * 0.50f
        val mouthCy = c.height * 0.72f
        val scale = scalePercent / 100f

        val matrix = Matrix()
        matrix.postScale(scale, scale, mouthCx, mouthCy)
        matrix.postRotate(angleDeg.toFloat(), mouthCx, mouthCy)
        canvas.drawBitmap(generated, matrix, paint)

        val original = IntArray(c.width * c.height)
        val gen = IntArray(c.width * c.height)
        out.getPixels(original, 0, c.width, c.left, c.top, c.width, c.height)
        transformed.getPixels(gen, 0, c.width, 0, 0, c.width, c.height)

        val shiftX = (c.width * offsetXPercent / 100f).roundToInt()
        val shiftY = (c.height * offsetYPercent / 100f).roundToInt()

        for (y in 0 until c.height) {
            val fy = y.toFloat() / max(1, c.height - 1)
            for (x in 0 until c.width) {
                val fx = x.toFloat() / max(1, c.width - 1)

                val dx = (fx - 0.50f) / 0.34f
                val dy = (fy - 0.72f) / 0.19f
                val d2 = dx * dx + dy * dy
                val alpha = (1f - smoothStep(0.38f, 1.00f, d2)).coerceIn(0f, 1f)
                if (alpha <= 0f) continue

                val srcX = (x - shiftX).coerceIn(0, c.width - 1)
                val srcY = (y - shiftY).coerceIn(0, c.height - 1)
                val dstIndex = y * c.width + x
                val srcIndex = srcY * c.width + srcX

                val g = gen[srcIndex]
                if (Color.alpha(g) == 0) continue

                val a = original[dstIndex]
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
        transformed.recycle()
        generated.recycle()
        return out
    }

'''
m = m[:func_start] + new_composite + m[func_end:]

m = replace_one(
    m,
    "val composed = compositeMouth(base, face, crop, mouthOffsetXPercent, mouthOffsetYPercent)",
    "val composed = compositeMouth(base, face, crop, mouthOffsetXPercent, mouthOffsetYPercent, mouthAngleDeg, mouthScalePercent)",
    "вызов compositeMouth V0.9",
)

m = m.replace("V09_01_input_crop_", "V10_01_input_crop_")
m = m.replace("V09_02_wav2lip_face_", "V10_02_wav2lip_face_")
m = m.replace("V09_03_composite_before_encoder_", "V10_03_composite_before_encoder_")
m = m.replace('File(cacheDir, "v09_', 'File(cacheDir, "v10_')
m = m.replace("V0.9 lip-sync:", "V1.0 lip-sync:")
m = m.replace("✓ V0.9 ГОТОВА", "✓ V1.0 ГОТОВА")
m = m.replace(
    'X: ${mouthOffsetXPercent}% • Y: ${mouthOffsetYPercent}%\\nПришли V09_03 + MP4, если нужна ещё подгонка.',
    'X: ${mouthOffsetXPercent}% • Y: ${mouthOffsetYPercent}% • Angle: ${mouthAngleDeg}° • Scale: ${mouthScalePercent}%\\nПришли V10_03 + MP4, если нужна ещё подгонка.'
)
m = m.replace(
    'Toast.makeText(this, "V0.9: MP4 + PNG сохранены", Toast.LENGTH_LONG).show()',
    'Toast.makeText(this, "V1.0: MP4 + PNG сохранены", Toast.LENGTH_LONG).show()'
)
m = m.replace("Ошибка V0.9:", "Ошибка V1.0:")
m = m.replace("DoramaAvatar_V09_", "DoramaAvatar_V10_")

main_path.write_text(m, encoding="utf-8")

w = workflow_path.read_text(encoding="utf-8")
w = replace_one(
    w,
    "DoramaAvatarLipSync-v0.9-debug",
    "DoramaAvatarLipSync-v1.0-debug",
    "workflow artifact V0.9",
)
workflow_path.write_text(w, encoding="utf-8")

readme_path.write_text(
'''Dorama Avatar LipSync V1.0 FULL CALIBRATION

Рабочая FaceFusion Wav2Lip GAN 96 модель, mel, BGR и MP4-пайплайн сохранены.

Добавлено:
1) X offset: -20% ... +20%;
2) Y offset: -15% ... +15%;
3) Angle: -12° ... +12°;
4) Scale: 85% ... 115%;
5) настройки запоминаются через SharedPreferences;
6) стартовый пресет текущего аватара: X=+10%, Y=-6%, Angle=0°, Scale=100%;
7) зона смешивания немного уже, чтобы меньше размывать щёки и подбородок;
8) диагностика: V10_01, V10_02, V10_03;
9) MP4: DoramaAvatar_V10_*.mp4.

Теперь разные картинки можно подгонять прямо на телефоне без пересборки приложения.
После геометрии следующий этап — уменьшение размытия / повышение качества зоны губ.

Wav2Lip weights используются только как технический некоммерческий тест.
''',
encoding="utf-8"
)

for old_name in ("dorama_lip_update_v0_8.py", "dorama_lip_update_v0_9.py"):
    old = root / old_name
    if old.exists():
        try:
            old.unlink()
            print(f"Удалён старый патчер: {old.name}")
        except OSError:
            pass

checks = [
    (gradle_path, 'versionName = "1.0"'),
    (layout_path, "Dorama Avatar • V1.0 CALIBRATION"),
    (layout_path, "mouthAngleSeek"),
    (layout_path, "mouthScaleSeek"),
    (main_path, "mouthAngleDeg"),
    (main_path, "mouthScalePercent"),
    (main_path, "matrix.postRotate"),
    (main_path, "matrix.postScale"),
    (main_path, "✓ V1.0 ГОТОВА"),
    (workflow_path, "DoramaAvatarLipSync-v1.0-debug"),
]
failed = []
for p, marker in checks:
    if marker not in p.read_text(encoding="utf-8"):
        failed.append(f"{p.relative_to(root)} -> {marker}")

if failed:
    print("\nОШИБКА ПРОВЕРКИ V1.0:")
    for item in failed:
        print(" -", item)
    sys.exit(7)

print("\n✓ V1.0 применена")
print("✓ X: -20..+20, старт +10")
print("✓ Y: -15..+15, старт -6")
print("✓ Angle: -12..+12°")
print("✓ Scale: 85..115%")
print("✓ настройки запоминаются")
print("✓ рабочая GAN-модель сохранена")
print("✓ GitHub Actions artifact = v1.0-debug")
print("\nТеперь:")
print("  git status")
print("  git add -A")
print('  git commit -m "Add Dorama Avatar LipSync v1.0 calibration"')
print("  git push")
