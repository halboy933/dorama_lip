#!/usr/bin/env python3
# Dorama Avatar LipSync V1.3 — EDTalk 256 QUALITY ENGINE
# Запускать из корня репозитория:
#   cd /workspaces/dorama_lip
#   python3 dorama_lip_update_v1_3.py
#
# Требует V1.2. Stable signing / GitHub Secrets не меняет.

from pathlib import Path
import sys

root = Path.cwd()

if root.name != "dorama_lip":
    print(f"ОШИБКА: сейчас открыта папка {root}")
    print("Перейди в /workspaces/dorama_lip и запусти файл ещё раз.")
    sys.exit(2)

main_path = root / "app/src/main/java/com/dorama/avatar/MainActivity.kt"
wav_path = root / "app/src/main/java/com/dorama/avatar/WavUtils.kt"
gradle_path = root / "app/build.gradle.kts"
layout_path = root / "app/src/main/res/layout/activity_main.xml"
workflow_path = root / ".github/workflows/build-apk.yml"
readme_path = root / "README_RU.txt"

for p in (main_path, wav_path, gradle_path, layout_path, workflow_path):
    if not p.exists():
        print(f"ОШИБКА: не найден файл {p}")
        sys.exit(3)

def replace_one(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        print(f"ОШИБКА PATCH: не найдено {label}")
        sys.exit(4)
    return text.replace(old, new, 1)

print("Dorama Avatar LipSync — V1.3 EDTalk 256")
print(f"Проект: {root}")

# ----------------------------------------------------------------------
# VERSION / SIGNING — applicationId и stable signing не меняем.
# ----------------------------------------------------------------------
g = gradle_path.read_text(encoding="utf-8")
g = replace_one(
    g,
    'versionCode = 12\n        versionName = "1.2"',
    'versionCode = 13\n        versionName = "1.3"',
    "versionCode/versionName V1.2",
)
if 'applicationId = "com.dorama.avatar"' not in g or 'signingConfigs.create("stable")' not in g:
    print("ОШИБКА: stable signing V1.1/V1.2 не найден. Останавливаюсь.")
    sys.exit(5)
gradle_path.write_text(g, encoding="utf-8")

# ----------------------------------------------------------------------
# UI — два движка: 96 быстрый + 256 качество.
# ----------------------------------------------------------------------
layout = '''<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

<LinearLayout
    android:orientation="vertical"
    android:padding="20dp"
    android:layout_width="match_parent"
    android:layout_height="wrap_content">

<TextView
    android:text="Dorama Avatar • V1.3 EDTalk 256"
    android:textSize="24sp"
    android:textStyle="bold"
    android:layout_width="wrap_content"
    android:layout_height="wrap_content"/>

<TextView
    android:id="@+id/status"
    android:text="Новый режим качества: EDTalk 256×256"
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
    android:layout_height="310dp"
    android:scaleType="centerCrop"
    android:background="#222222"/>

<Button android:id="@+id/imageButton" android:text="1. Выбрать PNG/JPG"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<Button android:id="@+id/audioButton" android:text="2. Выбрать WAV"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>

<TextView
    android:text="Движок lip-sync"
    android:textStyle="bold"
    android:textSize="16sp"
    android:paddingTop="12dp"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"/>

<RadioGroup
    android:id="@+id/engineGroup"
    android:orientation="vertical"
    android:layout_width="match_parent"
    android:layout_height="wrap_content">

    <RadioButton
        android:id="@+id/engine256"
        android:text="Качество — EDTalk 256×256 (~258 МБ)"
        android:checked="true"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"/>

    <RadioButton
        android:id="@+id/engine96"
        android:text="Быстрый резерв — Wav2Lip GAN 96×96"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"/>
</RadioGroup>

<Button android:id="@+id/modelButton" android:text="3. Проверить / скачать выбранную модель"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>

<TextView android:id="@+id/mouthOffsetXLabel" android:text="X: +15% (вправо)"
    android:textSize="16sp" android:textStyle="bold" android:paddingTop="12dp"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<SeekBar android:id="@+id/mouthOffsetXSeek" android:max="40" android:progress="35"
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

<TextView android:id="@+id/mouthAngleLabel" android:text="Угол: +3°"
    android:textSize="16sp" android:textStyle="bold" android:paddingTop="8dp"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<SeekBar android:id="@+id/mouthAngleSeek" android:max="24" android:progress="15"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:text="Угол: −12° ... 0° ... +12°"
    android:textSize="12sp" android:layout_width="match_parent" android:layout_height="wrap_content"/>

<TextView android:id="@+id/mouthScaleLabel" android:text="Размер: 89%"
    android:textSize="16sp" android:textStyle="bold" android:paddingTop="8dp"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<SeekBar android:id="@+id/mouthScaleSeek" android:max="30" android:progress="4"
    android:layout_width="match_parent" android:layout_height="wrap_content"/>
<TextView android:text="Размер: 85% ... 100% ... 115%"
    android:textSize="12sp" android:layout_width="match_parent" android:layout_height="wrap_content"/>

<Button android:id="@+id/generateButton"
    android:text="4. Создать MP4"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"/>

<TextView
    android:text="V1.3: EDTalk 256 — основной режим качества. Wav2Lip 96 оставлен как резерв. X/Y/Angle/Scale и moving-mask сохранены."
    android:paddingTop="14dp"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"/>

</LinearLayout>
</ScrollView>
'''
layout_path.write_text(layout, encoding="utf-8")

# ----------------------------------------------------------------------
# WavUtils — добавляем спектрограмму EDTalk/FaceFusion.
# ----------------------------------------------------------------------
w = wav_path.read_text(encoding="utf-8")

edtalk_code = r'''
    /*
     * V1.3 EDTalk / FaceFusion audio path.
     *
     * FaceFusion для EDTalk:
     *  - mono 16 kHz
     *  - peak normalize
     *  - pre-emphasis 0.97
     *  - STFT 800 / hop 200
     *  - HTK mel 80, 55..7600 Hz
     *  - затем для каждого 80x16 окна:
     *      max(1e-5, x) -> log10(x) * 1.6 + 3.2 -> clip(-4, 4)
     */
    fun edtalkSpectrogram(x: FloatArray, sr: Int = TARGET_SR): Array<FloatArray> {
        require(sr == TARGET_SR) { "Ожидается 16 kHz" }
        if (x.isEmpty()) return Array(N_MELS) { FloatArray(16) }

        var peak = 0f
        for (v in x) peak = max(peak, abs(v))
        val norm = if (peak > 1e-8f) FloatArray(x.size) { x[it] / peak } else x.copyOf()

        val emphasized = FloatArray(norm.size)
        emphasized[0] = norm[0]
        for (i in 1 until norm.size) emphasized[i] = norm[i] - PREEMPH * norm[i - 1]

        val half = N_FFT / 2
        var paddedSize = emphasized.size + N_FFT
        val rem = (paddedSize - N_FFT) % HOP
        if (rem != 0) paddedSize += HOP - rem
        val y = FloatArray(paddedSize)
        emphasized.copyInto(y, half)

        val frames = 1 + (y.size - N_FFT) / HOP
        val bins = N_FFT / 2 + 1

        val window = FloatArray(WIN) { n ->
            (0.5 - 0.5 * cos(2.0 * PI * n / WIN)).toFloat()
        }
        var windowSum = 0.0
        for (v in window) windowSum += v
        if (windowSum <= 0.0) windowSum = 1.0

        val cosT = Array(bins) { k ->
            FloatArray(N_FFT) { n -> cos(2.0 * PI * k * n / N_FFT).toFloat() }
        }
        val sinT = Array(bins) { k ->
            FloatArray(N_FFT) { n -> sin(2.0 * PI * k * n / N_FFT).toFloat() }
        }

        val filters = buildEdtalkMelFilters(sr, N_FFT, N_MELS, FMIN, FMAX)
        val result = Array(N_MELS) { FloatArray(frames) }

        for (t in 0 until frames) {
            val off = t * HOP
            val mag = FloatArray(bins)

            for (k in 0 until bins) {
                var re = 0.0
                var im = 0.0
                for (n in 0 until N_FFT) {
                    val v = y[off + n] * window[n]
                    re += v * cosT[k][n]
                    im -= v * sinT[k][n]
                }
                mag[k] = (sqrt(re * re + im * im) / windowSum).toFloat()
            }

            for (m in 0 until N_MELS) {
                var amp = 0.0
                for (k in 0 until bins) amp += filters[m][k] * mag[k]
                result[m][t] = amp.toFloat()
            }
        }

        return result
    }

    fun edtalkFrame(spec: Array<FloatArray>, frameIndex: Int, fps: Int = 25): FloatArray {
        val start = floor(frameIndex * 80.0 / fps).toInt()
        val out = FloatArray(N_MELS * 16)

        for (m in 0 until N_MELS) {
            for (x in 0 until 16) {
                val raw = spec[m][(start + x).coerceAtMost(spec[m].lastIndex)]
                val safe = max(1e-5f, raw)
                val prepared = (log10(safe.toDouble()) * 1.6 + 3.2)
                    .toFloat()
                    .coerceIn(-4f, 4f)
                out[m * 16 + x] = prepared
            }
        }

        return out
    }

    private fun buildEdtalkMelFilters(
        sr: Int,
        nFft: Int,
        nMels: Int,
        fMin: Double,
        fMax: Double
    ): Array<FloatArray> {
        val bins = nFft / 2 + 1

        fun hzToMel(hz: Double): Double = 2595.0 * log10(1.0 + hz / 700.0)
        fun melToHz(mel: Double): Double = 700.0 * (10.0.pow(mel / 2595.0) - 1.0)

        val melMin = hzToMel(fMin)
        val melMax = hzToMel(fMax)
        val points = DoubleArray(nMels + 2) { i ->
            melToHz(melMin + (melMax - melMin) * i / (nMels + 1))
        }
        val indices = IntArray(nMels + 2) { i ->
            floor((nFft + 1) * points[i] / sr)
                .toInt()
                .coerceIn(0, bins - 1)
        }

        val filters = Array(nMels) { FloatArray(bins) }

        for (m in 0 until nMels) {
            val start = indices[m]
            val end = indices[m + 1]
            val len = end - start
            if (len <= 0) continue

            for (j in 0 until len) {
                val value = if (len == 1) {
                    1.0
                } else if (len % 2 == 1) {
                    val n = (len + 1) / 2.0
                    if (j < (len + 1) / 2) (j + 1) / n
                    else (len - j) / n
                } else {
                    val n = (len + 1) / 2.0
                    if (j < len / 2) (j + 0.5) / n
                    else (len - j - 0.5) / n
                }
                filters[m][start + j] = value.toFloat()
            }
        }

        return filters
    }
'''

insert_marker = '''    private fun le16(b: ByteArray, p: Int)'''
if "fun edtalkSpectrogram(" not in w:
    if insert_marker not in w:
        print("ОШИБКА PATCH: не найдено место вставки EDTalk в WavUtils.kt")
        sys.exit(6)
    w = w.replace(insert_marker, edtalk_code + "\n" + insert_marker, 1)

wav_path.write_text(w, encoding="utf-8")

# ----------------------------------------------------------------------
# MainActivity.
# ----------------------------------------------------------------------
m = main_path.read_text(encoding="utf-8")

field_marker = '''    private var mouthScalePercent: Int = 89
'''
if 'private var engineMode:' not in m:
    m = replace_one(
        m,
        field_marker,
        field_marker + '    private var engineMode: String = "edtalk256"\n',
        "engineMode field",
    )

prefs_marker = '''        mouthScalePercent = prefs.getInt("mouth_scale", 89)
'''
engine_init = prefs_marker + '''
        engineMode = prefs.getString("lip_engine", "edtalk256") ?: "edtalk256"
        val engineGroup = findViewById<RadioGroup>(R.id.engineGroup)
        findViewById<RadioButton>(
            if (engineMode == "wav2lip96") R.id.engine96 else R.id.engine256
        ).isChecked = true

        engineGroup.setOnCheckedChangeListener { _, checkedId ->
            engineMode = if (checkedId == R.id.engine96) "wav2lip96" else "edtalk256"
            prefs.edit().putString("lip_engine", engineMode).apply()
            status.text = if (engineMode == "edtalk256") {
                "✓ Выбран EDTalk 256×256 — качество"
            } else {
                "✓ Выбран Wav2Lip GAN 96×96 — быстрый резерв"
            }
        }
'''
if 'R.id.engineGroup' not in m:
    m = replace_one(m, prefs_marker, engine_init, "engine init")

model_start = m.find("    private fun modelFile()")
model_end = m.find("    private data class FaceCrop(", model_start)
if model_start < 0 or model_end < 0:
    print("ОШИБКА PATCH: не найден блок модели в MainActivity")
    sys.exit(7)

model_block = r'''    private fun wav2lipModelFile() = File(filesDir, "wav2lip_facefusion_gan96.onnx")
    private fun edtalkModelFile() = File(filesDir, "edtalk_facefusion_256.onnx")

    private fun activeModelFile(): File =
        if (engineMode == "edtalk256") edtalkModelFile() else wav2lipModelFile()

    private fun activeModelLabel(): String =
        if (engineMode == "edtalk256") "EDTalk 256×256" else "Wav2Lip GAN 96×96"

    private fun activeModelUrl(): String =
        if (engineMode == "edtalk256") {
            "https://github.com/facefusion/facefusion-assets/releases/download/models-3.3.0/edtalk_256.onnx"
        } else {
            "https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/wav2lip_gan_96.onnx"
        }

    private fun activeModelMinBytes(): Long =
        if (engineMode == "edtalk256") 250_000_000L else 100_000_000L

    private fun downloadModel() {
        val file = activeModelFile()
        val label = activeModelLabel()

        if (file.exists() && file.length() > activeModelMinBytes()) {
            status.text = "✓ $label уже есть: ${file.length() / 1024 / 1024} МБ"
            return
        }

        thread {
            try {
                runOnUiThread {
                    status.text = "Скачиваю $label…"
                    progress.progress = 0
                }

                val c = URL(activeModelUrl()).openConnection()
                val total = c.contentLengthLong

                c.getInputStream().use { input ->
                    file.outputStream().use { output ->
                        val buf = ByteArray(262144)
                        var n: Int
                        var done = 0L

                        while (input.read(buf).also { n = it } > 0) {
                            output.write(buf, 0, n)
                            done += n
                            if (total > 0) {
                                runOnUiThread {
                                    progress.progress = (done * 100 / total).toInt()
                                }
                            }
                        }
                    }
                }

                if (file.length() <= activeModelMinBytes()) {
                    throw RuntimeException("Файл модели слишком маленький: ${file.length()} байт")
                }

                runOnUiThread {
                    progress.progress = 100
                    status.text = "✓ $label готова (${file.length() / 1024 / 1024} МБ)"
                }
            } catch (e: Throwable) {
                file.delete()
                runOnUiThread {
                    status.text = "Ошибка модели $label: ${e.message}"
                }
            }
        }
    }

'''
m = m[:model_start] + model_block + m[model_end:]

old_crop_return = '''        val raw = Bitmap.createBitmap(b, left, top, w, h)
        return FaceCrop(Bitmap.createScaledBitmap(raw, 96, 96, true), left, top, w, h)
'''
new_crop_return = '''        val raw = Bitmap.createBitmap(b, left, top, w, h)
        return FaceCrop(raw, left, top, w, h)
'''
m = replace_one(m, old_crop_return, new_crop_return, "raw FaceCrop")

img_start = m.find("    private fun imageTensor(")
img_end = m.find("    /*\n     * V0.7: не предполагаем layout", img_start)
if img_start < 0 or img_end < 0:
    print("ОШИБКА PATCH: не найден imageTensor")
    sys.exit(8)

image_functions = r'''    private fun imageTensor96(source: Bitmap): FloatArray {
        val b = Bitmap.createScaledBitmap(source, 96, 96, true)
        val pix = IntArray(96 * 96)
        b.getPixels(pix, 0, 96, 0, 0, 96, 96)
        val out = FloatArray(6 * 96 * 96)

        for (y in 0 until 96) {
            for (x in 0 until 96) {
                val p = pix[y * 96 + x]
                val bgr = floatArrayOf(
                    Color.blue(p) / 255f,
                    Color.green(p) / 255f,
                    Color.red(p) / 255f
                )
                for (c in 0..2) {
                    val value = bgr[c]
                    out[c * 96 * 96 + y * 96 + x] = if (y >= 48) 0f else value
                    out[(c + 3) * 96 * 96 + y * 96 + x] = value
                }
            }
        }

        b.recycle()
        return out
    }

    private fun imageTensor256(source: Bitmap): FloatArray {
        val b = Bitmap.createScaledBitmap(source, 256, 256, true)
        val pix = IntArray(256 * 256)
        b.getPixels(pix, 0, 256, 0, 0, 256, 256)
        val out = FloatArray(3 * 256 * 256)

        for (y in 0 until 256) {
            for (x in 0 until 256) {
                val p = pix[y * 256 + x]
                out[0 * 256 * 256 + y * 256 + x] = Color.red(p) / 255f
                out[1 * 256 * 256 + y * 256 + x] = Color.green(p) / 255f
                out[2 * 256 * 256 + y * 256 + x] = Color.blue(p) / 255f
            }
        }

        b.recycle()
        return out
    }

'''
m = m[:img_start] + image_functions + m[img_end:]

out_func_end_marker = '''        return out
    }

    private fun smoothStep'''
if "private fun outputBitmap256(" not in m:
    if out_func_end_marker not in m:
        print("ОШИБКА PATCH: не найден конец outputBitmap")
        sys.exit(9)

    output256 = r'''        return out
    }

    private fun outputBitmap256(v: Any): Bitmap {
        val batch = v as? Array<*> ?: throw RuntimeException("EDTalk output: не Array")
        val first = batch.firstOrNull() as? Array<*>
            ?: throw RuntimeException("EDTalk output: пустой batch")

        val out = Bitmap.createBitmap(256, 256, Bitmap.Config.ARGB_8888)
        val pix = IntArray(256 * 256)

        if (first.size == 3) {
            for (y in 0 until 256) for (x in 0 until 256) {
                fun ch(k: Int): Int {
                    val row = (first[k] as Array<*>)[y] as FloatArray
                    return (row[x].coerceIn(0f, 1f) * 255f).roundToInt()
                }
                pix[y * 256 + x] = Color.rgb(ch(0), ch(1), ch(2))
            }
        } else if (first.size == 256) {
            for (y in 0 until 256) {
                val row = first[y] as Array<*>
                for (x in 0 until 256) {
                    val rgb = row[x] as FloatArray
                    val r = (rgb[0].coerceIn(0f, 1f) * 255f).roundToInt()
                    val g = (rgb[1].coerceIn(0f, 1f) * 255f).roundToInt()
                    val b = (rgb[2].coerceIn(0f, 1f) * 255f).roundToInt()
                    pix[y * 256 + x] = Color.rgb(r, g, b)
                }
            }
        } else {
            throw RuntimeException("Неизвестный EDTalk output layout: first=${first.size}")
        }

        out.setPixels(pix, 0, 256, 0, 0, 256, 256)
        return out
    }

    private fun smoothStep'''
    m = m.replace(out_func_end_marker, output256, 1)

gen_start = m.find("    private fun generate()")
gen_end = m.find("    private fun scaleEven(", gen_start)
if gen_start < 0 or gen_end < 0:
    print("ОШИБКА PATCH: не найден generate()")
    sys.exit(10)

generate_fn = r'''    private fun generate() {
        if (imageUri == null || audioUri == null) {
            status.text = "Сначала выбери картинку и WAV."
            return
        }

        val model = activeModelFile()
        if (!model.exists() || model.length() <= activeModelMinBytes()) {
            status.text = "Сначала скачай выбранную модель: ${activeModelLabel()}."
            return
        }

        thread {
            try {
                val started = System.currentTimeMillis()
                val engineAtStart = engineMode
                val engineLabel = if (engineAtStart == "edtalk256") {
                    "EDTalk 256×256"
                } else {
                    "Wav2Lip GAN 96×96"
                }

                runOnUiThread {
                    status.text = "Ищу лицо… ($engineLabel)"
                    progress.progress = 1
                }

                val src = contentResolver.openInputStream(imageUri!!)!!.use {
                    BitmapFactory.decodeStream(it)
                }
                val base = scaleEven(src, 720)
                val rect = detectFace(base)
                val crop = cropInfo(base, rect)

                val wav = contentResolver.openInputStream(audioUri!!)!!.use {
                    WavUtils.readPcm16(it)
                }
                val samples = wav.samples.copyOf(min(wav.samples.size, 16000 * 5))
                val frames = min(125, max(1, (samples.size / 16000f * 25).toInt()))

                val env = OrtEnvironment.getEnvironment()
                val session = env.createSession(model.absolutePath, OrtSession.SessionOptions())
                val names = session.inputNames.toList()

                val rendered = ArrayList<Bitmap>(frames)

                if (engineAtStart == "edtalk256") {
                    val spec = WavUtils.edtalkSpectrogram(samples)
                    val targetInput = imageTensor256(crop.bitmap)

                    val sourceName = names.firstOrNull {
                        it.equals("source", true) || it.contains("audio", true)
                    } ?: names[0]

                    val targetName = names.firstOrNull {
                        it.equals("target", true) || it.contains("image", true) ||
                            it.contains("frame", true) || it.contains("face", true)
                    } ?: names.getOrElse(1) { names.last() }

                    val weightName = names.firstOrNull {
                        it.equals("weight", true) || it.contains("weight", true)
                    } ?: names.last()

                    for (f in 0 until frames) {
                        val sourceFrame = WavUtils.edtalkFrame(spec, f)

                        val face = OnnxTensor.createTensor(
                            env,
                            FloatBuffer.wrap(sourceFrame),
                            longArrayOf(1, 1, 80, 16)
                        ).use { sourceTensor ->
                            OnnxTensor.createTensor(
                                env,
                                FloatBuffer.wrap(targetInput),
                                longArrayOf(1, 3, 256, 256)
                            ).use { targetTensor ->
                                OnnxTensor.createTensor(
                                    env,
                                    FloatBuffer.wrap(floatArrayOf(0.5f)),
                                    longArrayOf(1)
                                ).use { weightTensor ->
                                    session.run(
                                        mapOf(
                                            sourceName to sourceTensor,
                                            targetName to targetTensor,
                                            weightName to weightTensor
                                        )
                                    ).use { result ->
                                        outputBitmap256(result[0].value)
                                    }
                                }
                            }
                        }

                        val composed = compositeMouth(
                            base, face, crop,
                            mouthOffsetXPercent,
                            mouthOffsetYPercent,
                            mouthAngleDeg,
                            mouthScalePercent
                        )

                        if (f == 0) {
                            val stamp = System.currentTimeMillis()
                            savePng(crop.bitmap, "V13_01_input_crop_${stamp}.png")
                            savePng(face, "V13_02_edtalk256_face_${stamp}.png")
                            savePng(composed, "V13_03_composite_before_encoder_${stamp}.png")
                        }

                        rendered.add(composed)
                        face.recycle()

                        if (f % 2 == 0) {
                            runOnUiThread {
                                progress.progress = 1 + f * 75 / frames
                                status.text = "EDTalk 256: ${f + 1}/$frames кадров"
                            }
                        }
                    }
                } else {
                    val mel = WavUtils.melSpectrogram(samples)
                    val imageInput = imageTensor96(crop.bitmap)

                    val melName = names.firstOrNull {
                        it.contains("mel", true) || it.contains("audio", true) ||
                            it.contains("source", true)
                    } ?: names[0]

                    val imgName = names.firstOrNull {
                        it.contains("video", true) || it.contains("frame", true) ||
                            it.contains("img", true) || it.contains("face", true) ||
                            it.contains("target", true)
                    } ?: names.last()

                    for (f in 0 until frames) {
                        val mi = (f * 80.0 / 25.0).toInt()
                            .coerceAtMost(max(0, mel[0].size - 16))
                        val mf = FloatArray(80 * 16)

                        for (y in 0 until 80) for (x in 0 until 16) {
                            mf[y * 16 + x] =
                                mel[y][(mi + x).coerceAtMost(mel[y].lastIndex)]
                        }

                        val face = OnnxTensor.createTensor(
                            env,
                            FloatBuffer.wrap(mf),
                            longArrayOf(1, 1, 80, 16)
                        ).use { mt ->
                            OnnxTensor.createTensor(
                                env,
                                FloatBuffer.wrap(imageInput),
                                longArrayOf(1, 6, 96, 96)
                            ).use { img ->
                                session.run(mapOf(melName to mt, imgName to img)).use { r ->
                                    outputBitmap(r[0].value)
                                }
                            }
                        }

                        val composed = compositeMouth(
                            base, face, crop,
                            mouthOffsetXPercent,
                            mouthOffsetYPercent,
                            mouthAngleDeg,
                            mouthScalePercent
                        )

                        if (f == 0) {
                            val stamp = System.currentTimeMillis()
                            savePng(crop.bitmap, "V13_01_input_crop_${stamp}.png")
                            savePng(face, "V13_02_wav2lip96_face_${stamp}.png")
                            savePng(composed, "V13_03_composite_before_encoder_${stamp}.png")
                        }

                        rendered.add(composed)
                        face.recycle()

                        if (f % 3 == 0) {
                            runOnUiThread {
                                progress.progress = 1 + f * 75 / frames
                                status.text = "Wav2Lip 96: ${f + 1}/$frames кадров"
                            }
                        }
                    }
                }

                session.close()

                val tmp = File(cacheDir, "v13_${System.currentTimeMillis()}.mp4")
                val encoderInfo = encodeMp4(rendered, samples, tmp)
                rendered.forEach { it.recycle() }
                saveMovie(tmp)

                val sec = (System.currentTimeMillis() - started) / 1000.0

                runOnUiThread {
                    progress.progress = 100
                    status.text =
                        "✓ V1.3 ГОТОВА\n" +
                        "✓ Движок: $engineLabel\n" +
                        "✓ PNG: Pictures/DoramaAvatar\n" +
                        "✓ MP4: ${encoderInfo.width}x${encoderInfo.height}\n" +
                        "✓ $frames кадров / H.264 + AAC\n" +
                        "⏱ ${"%.1f".format(sec)} сек\n" +
                        "📁 Movies/DoramaAvatar\n\n" +
                        "X: ${mouthOffsetXPercent}% • Y: ${mouthOffsetYPercent}% • " +
                        "Angle: ${mouthAngleDeg}° • Scale: ${mouthScalePercent}%"

                    Toast.makeText(
                        this,
                        "V1.3: $engineLabel — MP4 готов",
                        Toast.LENGTH_LONG
                    ).show()
                }

                crop.bitmap.recycle()
            } catch (e: Throwable) {
                runOnUiThread {
                    status.text =
                        "Ошибка V1.3 ${activeModelLabel()}: " +
                        "${e.javaClass.simpleName}: ${e.message}"
                }
            }
        }
    }

'''
m = m[:gen_start] + generate_fn + m[gen_end:]

old_generated = '''        val generatedScaled = Bitmap.createScaledBitmap(generated96, c.width, c.height, true)
        val generated = sharpenGenerated(generatedScaled)
        generatedScaled.recycle()
'''
new_generated = '''        val generatedScaled = Bitmap.createScaledBitmap(generated96, c.width, c.height, true)
        val generated = if (generated96.width <= 96) {
            val sharp = sharpenGenerated(generatedScaled)
            generatedScaled.recycle()
            sharp
        } else {
            generatedScaled
        }
'''
m = replace_one(m, old_generated, new_generated, "quality branch in compositeMouth")

m = m.replace(
    '''                val dx = (fx - 0.50f) / 0.30f
                val dy = (fy - 0.72f) / 0.165f''',
    '''                val dx = (fx - 0.50f) / 0.32f
                val dy = (fy - 0.72f) / 0.18f'''
)
m = m.replace(
    "smoothStep(0.46f, 1.00f, d2)",
    "smoothStep(0.44f, 1.00f, d2)"
)

m = m.replace("DoramaAvatar_V12_", "DoramaAvatar_V13_")
m = m.replace("Ошибка V1.2:", "Ошибка V1.3:")

main_path.write_text(m, encoding="utf-8")

# ----------------------------------------------------------------------
# Workflow — тот же stable signing, только artifact V1.3.
# ----------------------------------------------------------------------
workflow = workflow_path.read_text(encoding="utf-8")
if "DORAMA_KEYSTORE_B64" not in workflow:
    print("ОШИБКА: workflow без stable signing. Останавливаюсь.")
    sys.exit(11)

workflow = replace_one(
    workflow,
    "DoramaAvatarLipSync-v1.2-stable",
    "DoramaAvatarLipSync-v1.3-stable",
    "workflow artifact V1.2",
)
workflow_path.write_text(workflow, encoding="utf-8")

readme_path.write_text(
'''Dorama Avatar LipSync V1.3 — EDTalk 256 QUALITY ENGINE

Главное:
- добавлен EDTalk 256×256 из FaceFusion assets;
- Wav2Lip GAN 96×96 оставлен как быстрый резерв;
- основной режим по умолчанию: EDTalk 256.

EDTalk 256:
- модель ~258 МБ;
- файл: edtalk_facefusion_256.onnx;
- скачивается один раз и хранится в filesDir;
- при обычных обновлениях приложения не удаляется;
- вход target: RGB CHW 256×256;
- source: 80×16 audio frame;
- weight: 0.5;
- output: RGB 256×256.

Audio path EDTalk повторяет FaceFusion:
- 16 kHz mono;
- peak normalize;
- pre-emphasis 0.97;
- STFT 800 / hop 200;
- HTK mel 80, 55..7600 Hz;
- log10 * 1.6 + 3.2, clip [-4, 4].

Сохранено:
- X / Y / Angle / Scale;
- SharedPreferences;
- moving mask;
- MP4 H.264 + AAC;
- stable signing key;
- обновление поверх V1.2;
- старая 96px модель остаётся на телефоне как fallback.

Стартовый ориентир текущего аватара:
X=+15%, Y=-6%, Angle=+3°, Scale=89%.

Диагностика:
- V13_01_input_crop
- V13_02_edtalk256_face (или wav2lip96_face)
- V13_03_composite_before_encoder
- DoramaAvatar_V13_*.mp4

EDTalk metadata in FaceFusion: vendor tanshuai0219, Apache-2.0.
Wav2Lip weights оставлены только как технический некоммерческий fallback.
''',
encoding="utf-8",
)

for old_name in (
    "dorama_lip_update_v1_0.py",
    "dorama_lip_update_v1_1.py",
    "dorama_lip_update_v1_2.py",
):
    old = root / old_name
    if old.exists():
        try:
            old.unlink()
            print(f"Удалён старый патчер: {old.name}")
        except OSError:
            pass

checks = [
    (gradle_path, 'versionName = "1.3"'),
    (gradle_path, 'versionCode = 13'),
    (gradle_path, 'signingConfigs.create("stable")'),
    (layout_path, "Dorama Avatar • V1.3 EDTalk 256"),
    (layout_path, "engine256"),
    (layout_path, "engine96"),
    (main_path, "edtalk_facefusion_256.onnx"),
    (main_path, "edtalk_256.onnx"),
    (main_path, "imageTensor256"),
    (main_path, "outputBitmap256"),
    (main_path, "WavUtils.edtalkSpectrogram"),
    (main_path, "WavUtils.edtalkFrame"),
    (main_path, 'longArrayOf(1, 3, 256, 256)'),
    (main_path, 'floatArrayOf(0.5f)'),
    (wav_path, "fun edtalkSpectrogram"),
    (wav_path, "fun edtalkFrame"),
    (workflow_path, "DORAMA_KEYSTORE_B64"),
    (workflow_path, "DoramaAvatarLipSync-v1.3-stable"),
]

failed = []
for p, marker in checks:
    if marker not in p.read_text(encoding="utf-8"):
        failed.append(f"{p.relative_to(root)} -> {marker}")

if failed:
    print("\nОШИБКА ПРОВЕРКИ V1.3:")
    for item in failed:
        print(" -", item)
    sys.exit(20)

print("\n✓ V1.3 EDTalk 256 применена")
print("✓ основной режим: EDTalk 256×256")
print("✓ Wav2Lip GAN 96 оставлен как резерв")
print("✓ X/Y/Angle/Scale + moving mask сохранены")
print("✓ stable signing НЕ менялся")
print("✓ V1.3 рассчитана на установку поверх V1.2")
print("✓ 256-модель скачивается один раз (~258 МБ)")

print("\nТеперь:")
print("  git status")
print("  git add -A")
print('  git commit -m "Add Dorama Avatar LipSync v1.3 EDTalk 256"')
print("  git push")
