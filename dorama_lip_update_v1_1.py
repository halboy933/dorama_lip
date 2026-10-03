#!/usr/bin/env python3
# Dorama Avatar LipSync V1.1 — MOVING MASK + STABLE SIGNING
# Запускать из корня репозитория:
#   cd /workspaces/dorama_lip
#   python3 dorama_lip_update_v1_1.py
#
# Поддерживает обновление исходников с V0.9 или V1.0.

from pathlib import Path
import base64
import secrets
import shutil
import subprocess
import sys
import tempfile

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

def run(cmd, check=False):
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
    )

def ensure_signing_secrets():
    needed = {
        "DORAMA_KEYSTORE_B64",
        "DORAMA_KEYSTORE_PASSWORD",
        "DORAMA_KEY_PASSWORD",
    }

    gh = shutil.which("gh")
    keytool = shutil.which("keytool")

    if not gh:
        print("ОШИБКА: gh CLI не найден. Не могу безопасно закрепить подпись APK.")
        sys.exit(10)

    auth = run([gh, "auth", "status"])
    if auth.returncode != 0:
        print("ОШИБКА: GitHub CLI не авторизован.")
        print(auth.stdout)
        sys.exit(11)

    listed = run([gh, "secret", "list"])
    if listed.returncode != 0:
        print("ОШИБКА: не удалось получить список GitHub Secrets.")
        print(listed.stdout)
        sys.exit(12)

    present = set()
    for line in listed.stdout.splitlines():
        parts = line.strip().split()
        if parts:
            present.add(parts[0])

    if needed.issubset(present):
        print("✓ Постоянный ключ подписи уже настроен в GitHub Secrets")
        return

    partial = needed.intersection(present)
    if partial:
        print("ОШИБКА: найден неполный набор signing-secrets.")
        for name in sorted(needed):
            print(("  ✓ " if name in present else "  ✗ ") + name)
        print("Автоматически перезаписывать существующую подпись не буду.")
        sys.exit(13)

    if not keytool:
        print("ОШИБКА: keytool не найден. Нужен JDK 17.")
        sys.exit(14)

    print("Создаю ОДИН постоянный ключ подписи для V1.1 и следующих версий…")
    password = secrets.token_urlsafe(28)

    with tempfile.TemporaryDirectory() as td:
        key_path = Path(td) / "dorama-release.jks"
        created = run([
            keytool,
            "-genkeypair",
            "-v",
            "-keystore", str(key_path),
            "-storetype", "JKS",
            "-storepass", password,
            "-keypass", password,
            "-alias", "dorama",
            "-keyalg", "RSA",
            "-keysize", "2048",
            "-validity", "36500",
            "-dname", "CN=Dorama Avatar,O=Dorama Studio,C=US",
        ])

        if created.returncode != 0 or not key_path.exists():
            print("ОШИБКА создания keystore:")
            print(created.stdout)
            sys.exit(15)

        values = {
            "DORAMA_KEYSTORE_B64": base64.b64encode(key_path.read_bytes()).decode("ascii"),
            "DORAMA_KEYSTORE_PASSWORD": password,
            "DORAMA_KEY_PASSWORD": password,
        }

        for name, value in values.items():
            res = run([gh, "secret", "set", name, "--body", value])
            if res.returncode != 0:
                print(f"ОШИБКА записи GitHub Secret {name}:")
                print(res.stdout)
                sys.exit(16)

    print("✓ Постоянный signing key сохранён в GitHub Secrets")
    print("✓ Сам JKS-файл в репозиторий НЕ добавляется")


print("Dorama Avatar LipSync — V1.1 MOVING MASK")
print(f"Проект: {root}")

# Сначала закрепляем подпись. Если это не получится, исходники не трогаем.
ensure_signing_secrets()

# ----------------------------------------------------------------------
# Gradle: V1.1 + постоянная подпись в CI.
# Без env-переменных локальная сборка всё ещё сможет использовать debug-key.
# ----------------------------------------------------------------------
gradle_path.write_text(r'''plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val doramaKeystorePath = System.getenv("DORAMA_KEYSTORE_PATH")
val doramaKeystorePassword = System.getenv("DORAMA_KEYSTORE_PASSWORD")
val doramaKeyPassword = System.getenv("DORAMA_KEY_PASSWORD")

android {
    namespace = "com.dorama.avatar"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.dorama.avatar"
        minSdk = 26
        targetSdk = 35
        versionCode = 11
        versionName = "1.1"
    }

    val stableSigning = if (
        !doramaKeystorePath.isNullOrBlank() &&
        !doramaKeystorePassword.isNullOrBlank() &&
        !doramaKeyPassword.isNullOrBlank()
    ) {
        signingConfigs.create("stable") {
            storeFile = file(doramaKeystorePath)
            storePassword = doramaKeystorePassword
            keyAlias = "dorama"
            keyPassword = doramaKeyPassword
        }
    } else {
        null
    }

    buildTypes {
        getByName("debug") {
            if (stableSigning != null) {
                signingConfig = stableSigning
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.activity:activity-ktx:1.10.0")
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.20.0")
    implementation("com.google.mlkit:face-detection:16.1.7")
}
''', encoding="utf-8")

# ----------------------------------------------------------------------
# UI: X / Y / Angle / Scale.
# ----------------------------------------------------------------------
layout_path.write_text('''<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

<LinearLayout
    android:orientation="vertical"
    android:padding="20dp"
    android:layout_width="match_parent"
    android:layout_height="wrap_content">

<TextView
    android:text="Dorama Avatar • V1.1 MOVING MASK"
    android:textSize="24sp"
    android:textStyle="bold"
    android:layout_width="wrap_content"
    android:layout_height="wrap_content"/>

<TextView
    android:id="@+id/status"
    android:text="Рот и мягкая маска теперь двигаются вместе"
    android:paddingTop="12dp"
    android:paddingBottom="12dp"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"/>

<ProgressBar
    android:id="@+id/progress"
    style="?android:attr/progressBarStyleHorizontal"
    android:max="100"
    android:progress="0"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"/>

<ImageView
    android:id="@+id/preview"
    android:layout_width="match_parent"
    android:layout_height="330dp"
    android:scaleType="centerCrop"
    android:background="#222222"/>

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

<Button android:id="@+id/generateButton"
    android:text="4. Создать MP4 с этими настройками"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"/>

<TextView
    android:text="Старт: X=+10%, Y=-6%, угол=0°, размер=100%. Настройки сохраняются."
    android:paddingTop="14dp"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"/>

</LinearLayout>
</ScrollView>
''', encoding="utf-8")

# ----------------------------------------------------------------------
# MainActivity: работает с текущим V0.9 или уже применённым V1.0.
# ----------------------------------------------------------------------
m = main_path.read_text(encoding="utf-8")

# Поля калибровки.
fields_start = m.find("    private lateinit var mouthOffsetXLabel: TextView")
fields_end = m.find("\n\n    private val imagePicker", fields_start)
if fields_start < 0 or fields_end < 0:
    print("ОШИБКА PATCH: не найден блок полей калибровки")
    sys.exit(20)

new_fields = '''    private lateinit var mouthOffsetXLabel: TextView
    private lateinit var mouthOffsetYLabel: TextView
    private lateinit var mouthAngleLabel: TextView
    private lateinit var mouthScaleLabel: TextView
    private var mouthOffsetXPercent: Int = 10
    private var mouthOffsetYPercent: Int = -6
    private var mouthAngleDeg: Int = 0
    private var mouthScalePercent: Int = 100'''

m = m[:fields_start] + new_fields + m[fields_end:]

# Блок UI-калибровки в onCreate.
ui_start = m.find("        mouthOffsetXLabel = findViewById(R.id.mouthOffsetXLabel)")
ui_end = m.find('        findViewById<Button>(R.id.imageButton)', ui_start)
if ui_start < 0 or ui_end < 0:
    print("ОШИБКА PATCH: не найден блок калибровки onCreate")
    sys.exit(21)

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

        fun signed(v: Int): String = if (v > 0) "+$v" else "$v"

        fun refreshCalibrationLabels() {
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

m = m[:ui_start] + new_ui + m[ui_end:]

# Главная правка: рот и feather-mask получают ОДИНАКОВУЮ Matrix.
func_start = m.find("    private fun compositeMouth(")
func_end = m.find("    private fun generate()", func_start)
if func_start < 0 or func_end < 0:
    print("ОШИБКА PATCH: не найдена compositeMouth")
    sys.exit(22)

new_composite = '''    private fun compositeMouth(
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

        val mouthCx = c.width * 0.50f
        val mouthCy = c.height * 0.72f
        val shiftX = c.width * offsetXPercent / 100f
        val shiftY = c.height * offsetYPercent / 100f
        val scale = scalePercent / 100f

        // ВАЖНО: одна Matrix и для изображения, и для маски.
        val transform = Matrix().apply {
            postScale(scale, scale, mouthCx, mouthCy)
            postRotate(angleDeg.toFloat(), mouthCx, mouthCy)
            postTranslate(shiftX, shiftY)
        }

        val transformedFace = Bitmap.createBitmap(
            c.width, c.height, Bitmap.Config.ARGB_8888
        )
        Canvas(transformedFace).drawBitmap(
            generated,
            transform,
            Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
        )

        // Исходная мягкая маска рта.
        val baseMask = Bitmap.createBitmap(
            c.width, c.height, Bitmap.Config.ARGB_8888
        )
        val maskPixels = IntArray(c.width * c.height)

        for (y in 0 until c.height) {
            val fy = y.toFloat() / max(1, c.height - 1)
            for (x in 0 until c.width) {
                val fx = x.toFloat() / max(1, c.width - 1)
                val dx = (fx - 0.50f) / 0.34f
                val dy = (fy - 0.72f) / 0.19f
                val d2 = dx * dx + dy * dy

                val alpha = (
                    (1f - smoothStep(0.38f, 1.00f, d2)) * 255f
                ).roundToInt().coerceIn(0, 255)

                maskPixels[y * c.width + x] =
                    Color.argb(alpha, 255, 255, 255)
            }
        }

        baseMask.setPixels(
            maskPixels, 0, c.width, 0, 0, c.width, c.height
        )

        // Та же Matrix двигает сам "кружок".
        val transformedMask = Bitmap.createBitmap(
            c.width, c.height, Bitmap.Config.ARGB_8888
        )
        Canvas(transformedMask).drawBitmap(
            baseMask,
            transform,
            Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
        )

        val original = IntArray(c.width * c.height)
        val facePixels = IntArray(c.width * c.height)
        val mask = IntArray(c.width * c.height)

        out.getPixels(
            original, 0, c.width,
            c.left, c.top, c.width, c.height
        )
        transformedFace.getPixels(
            facePixels, 0, c.width,
            0, 0, c.width, c.height
        )
        transformedMask.getPixels(
            mask, 0, c.width,
            0, 0, c.width, c.height
        )

        for (i in original.indices) {
            val alpha = Color.alpha(mask[i]) / 255f
            if (alpha <= 0f) continue

            val g = facePixels[i]
            if (Color.alpha(g) == 0) continue

            val a = original[i]

            fun mix(ca: Int, cg: Int): Int =
                (ca * (1f - alpha) + cg * alpha)
                    .roundToInt()
                    .coerceIn(0, 255)

            original[i] = Color.rgb(
                mix(Color.red(a), Color.red(g)),
                mix(Color.green(a), Color.green(g)),
                mix(Color.blue(a), Color.blue(g))
            )
        }

        out.setPixels(
            original, 0, c.width,
            c.left, c.top, c.width, c.height
        )

        transformedMask.recycle()
        baseMask.recycle()
        transformedFace.recycle()
        generated.recycle()

        return out
    }

'''

m = m[:func_start] + new_composite + m[func_end:]

old_call = "val composed = compositeMouth(base, face, crop, mouthOffsetXPercent, mouthOffsetYPercent)"
new_call = "val composed = compositeMouth(base, face, crop, mouthOffsetXPercent, mouthOffsetYPercent, mouthAngleDeg, mouthScalePercent)"
if old_call in m:
    m = m.replace(old_call, new_call, 1)
elif new_call not in m:
    print("ОШИБКА PATCH: неизвестный вызов compositeMouth")
    sys.exit(23)

# Диагностика / версии.
for old_prefix in ("V09_", "V10_"):
    m = m.replace(old_prefix, "V11_")
for old_tmp in ('File(cacheDir, "v09_', 'File(cacheDir, "v10_'):
    m = m.replace(old_tmp, 'File(cacheDir, "v11_')

for old in ("V0.9 lip-sync:", "V1.0 lip-sync:"):
    m = m.replace(old, "V1.1 lip-sync:")
for old in ("✓ V0.9 ГОТОВА", "✓ V1.0 ГОТОВА"):
    m = m.replace(old, "✓ V1.1 ГОТОВА")
for old in ("Ошибка V0.9:", "Ошибка V1.0:"):
    m = m.replace(old, "Ошибка V1.1:")

m = m.replace("DoramaAvatar_V09_", "DoramaAvatar_V11_")
m = m.replace("DoramaAvatar_V10_", "DoramaAvatar_V11_")

m = m.replace(
    'Toast.makeText(this, "V0.9: MP4 + PNG сохранены", Toast.LENGTH_LONG).show()',
    'Toast.makeText(this, "V1.1: MP4 + PNG сохранены", Toast.LENGTH_LONG).show()'
)
m = m.replace(
    'Toast.makeText(this, "V1.0: MP4 + PNG сохранены", Toast.LENGTH_LONG).show()',
    'Toast.makeText(this, "V1.1: MP4 + PNG сохранены", Toast.LENGTH_LONG).show()'
)

old_statuses = [
    'X: ${mouthOffsetXPercent}% • Y: ${mouthOffsetYPercent}%\\nПришли V11_03 + MP4, если нужна ещё подгонка.',
    'X: ${mouthOffsetXPercent}% • Y: ${mouthOffsetYPercent}% • Angle: ${mouthAngleDeg}° • Scale: ${mouthScalePercent}%\\nПришли V11_03 + MP4, если нужна ещё подгонка.',
]
new_status = 'X: ${mouthOffsetXPercent}% • Y: ${mouthOffsetYPercent}% • Angle: ${mouthAngleDeg}° • Scale: ${mouthScalePercent}%\\nV1.1: рот и feather-mask двигаются вместе.'
for old in old_statuses:
    m = m.replace(old, new_status)

main_path.write_text(m, encoding="utf-8")

# ----------------------------------------------------------------------
# GitHub Actions: всегда тот же signing key из GitHub Secrets.
# Если secrets исчезнут — сборка специально падает, а не создаёт новый ключ.
# ----------------------------------------------------------------------
workflow_path.write_text(r'''name: Build APK

on:
  workflow_dispatch:
  push:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'

      - uses: gradle/actions/setup-gradle@v4
        with:
          gradle-version: '8.9'

      - name: Verify stable signing secrets
        env:
          KEYSTORE_B64: ${{ secrets.DORAMA_KEYSTORE_B64 }}
          STORE_PASS: ${{ secrets.DORAMA_KEYSTORE_PASSWORD }}
          KEY_PASS: ${{ secrets.DORAMA_KEY_PASSWORD }}
        run: |
          test -n "$KEYSTORE_B64" || (echo "Missing DORAMA_KEYSTORE_B64" && exit 1)
          test -n "$STORE_PASS" || (echo "Missing DORAMA_KEYSTORE_PASSWORD" && exit 1)
          test -n "$KEY_PASS" || (echo "Missing DORAMA_KEY_PASSWORD" && exit 1)

      - name: Restore stable signing key
        env:
          KEYSTORE_B64: ${{ secrets.DORAMA_KEYSTORE_B64 }}
        run: |
          echo "$KEYSTORE_B64" | base64 -d > "$RUNNER_TEMP/dorama-release.jks"

      - name: Build signed APK
        env:
          DORAMA_KEYSTORE_PATH: ${{ runner.temp }}/dorama-release.jks
          DORAMA_KEYSTORE_PASSWORD: ${{ secrets.DORAMA_KEYSTORE_PASSWORD }}
          DORAMA_KEY_PASSWORD: ${{ secrets.DORAMA_KEY_PASSWORD }}
        run: gradle assembleDebug

      - uses: actions/upload-artifact@v4
        with:
          name: DoramaAvatarLipSync-v1.1-stable
          path: app/build/outputs/apk/debug/app-debug.apk
''', encoding="utf-8")

readme_path.write_text('''Dorama Avatar LipSync V1.1 — MOVING MASK + STABLE UPDATES

Исправление V1.1:
- раньше X/Y/Angle/Scale двигали содержимое lip-sync, а feather-mask могла оставаться на старом месте;
- теперь generated face и feather-mask получают одну и ту же Matrix;
- рот и мягкая граница двигаются, вращаются и масштабируются как единый объект.

Калибровка:
- X: -20% ... +20%, старт +10%;
- Y: -15% ... +15%, старт -6%;
- Angle: -12° ... +12°;
- Scale: 85% ... 115%;
- настройки сохраняются в SharedPreferences.

Обновления APK:
- V1.1 создаёт один постоянный signing key;
- signing key хранится в GitHub Secrets;
- каждый следующий Actions build использует тот же ключ;
- начиная с V1.1 приложение можно обновлять поверх V1.1/V1.2/...;
- модель в filesDir при обычном обновлении сохраняется.

ВАЖНО:
Старые сборки были подписаны временными debug-ключами GitHub runner.
Старый ключ восстановить нельзя.
Поэтому переход на V1.1 может потребовать ОДНУ последнюю чистую установку.
После V1.1 удалять приложение для обновлений больше не потребуется,
пока GitHub Secrets с signing key сохраняются.

Диагностика: V11_01 / V11_02 / V11_03
MP4: DoramaAvatar_V11_*.mp4

Wav2Lip weights используются только как технический некоммерческий тест.
''', encoding="utf-8")

# Убираем старые updater-файлы, если они уже лежат в repo.
for old_name in (
    "dorama_lip_update_v0_8.py",
    "dorama_lip_update_v0_9.py",
    "dorama_lip_update_v1_0.py",
):
    old = root / old_name
    if old.exists():
        try:
            old.unlink()
            print(f"Удалён старый патчер: {old.name}")
        except OSError:
            pass

# Самопроверка.
checks = [
    (gradle_path, 'versionName = "1.1"'),
    (gradle_path, 'signingConfigs.create("stable")'),
    (layout_path, "Dorama Avatar • V1.1 MOVING MASK"),
    (main_path, "val transform = Matrix().apply"),
    (main_path, "Canvas(transformedMask).drawBitmap"),
    (main_path, "mouthAngleDeg"),
    (main_path, "mouthScalePercent"),
    (main_path, "V11_03"),
    (workflow_path, "DORAMA_KEYSTORE_B64"),
    (workflow_path, "DoramaAvatarLipSync-v1.1-stable"),
]

failed = []
for p, marker in checks:
    if marker not in p.read_text(encoding="utf-8"):
        failed.append(f"{p.relative_to(root)} -> {marker}")

if failed:
    print("\nОШИБКА ПРОВЕРКИ V1.1:")
    for item in failed:
        print(" -", item)
    sys.exit(30)

print("\n✓ V1.1 применена")
print("✓ рот и feather-mask двигаются ОДНОЙ Matrix")
print("✓ X/Y/Angle/Scale сохранены")
print("✓ постоянный signing key закреплён в GitHub Secrets")
print("✓ следующие версии смогут обновляться поверх приложения")

print("\nВАЖНО:")
print("Текущая старая APK подписана старым временным debug-key.")
print("Переход на V1.1 может потребовать ОДНУ последнюю чистую установку.")
print("После V1.1 модель при обычных обновлениях больше не удаляется.")

print("\nТеперь:")
print("  git status")
print("  git add -A")
print('  git commit -m "Add Dorama Avatar LipSync v1.1 moving mask and stable signing"')
print("  git push")
