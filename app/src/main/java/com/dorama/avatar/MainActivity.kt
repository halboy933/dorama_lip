package com.dorama.avatar

import ai.onnxruntime.*
import android.content.ContentValues
import android.graphics.*
import android.media.*
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.provider.OpenableColumns
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.face.FaceDetection
import com.google.mlkit.vision.face.FaceDetectorOptions
import java.io.File
import java.net.URL
import java.nio.FloatBuffer
import kotlin.concurrent.thread
import kotlin.math.*

class MainActivity : AppCompatActivity() {
    private var imageUri: Uri? = null
    private var audioUri: Uri? = null
    private lateinit var status: TextView
    private lateinit var preview: ImageView
    private lateinit var progress: ProgressBar

    private val imagePicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { u ->
        u?.let {
            imageUri = it
            preview.setImageURI(it)
            status.text = "✓ Картинка: ${name(it)}"
        }
    }
    private val audioPicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { u ->
        u?.let {
            audioUri = it
            status.text = "✓ WAV: ${name(it)}"
        }
    }

    override fun onCreate(b: Bundle?) {
        super.onCreate(b)
        setContentView(R.layout.activity_main)
        status = findViewById(R.id.status)
        preview = findViewById(R.id.preview)
        progress = findViewById(R.id.progress)
        findViewById<Button>(R.id.imageButton).setOnClickListener { imagePicker.launch(arrayOf("image/*")) }
        findViewById<Button>(R.id.audioButton).setOnClickListener { audioPicker.launch(arrayOf("audio/*")) }
        findViewById<Button>(R.id.modelButton).setOnClickListener { downloadModel() }
        findViewById<Button>(R.id.generateButton).setOnClickListener { generate() }
    }

    private fun modelFile() = File(filesDir, "wav2lip.onnx")

    private fun downloadModel() {
        if (modelFile().exists() && modelFile().length() > 100_000_000) {
            status.text = "✓ Модель уже есть: ${modelFile().length() / 1024 / 1024} МБ"
            return
        }
        thread {
            try {
                runOnUiThread { status.text = "Скачиваю модель…"; progress.progress = 0 }
                val c = URL("https://huggingface.co/bluefoxcreation/Wav2lip-Onnx/resolve/main/wav2lip.onnx?download=true").openConnection()
                val total = c.contentLengthLong
                c.getInputStream().use { input ->
                    modelFile().outputStream().use { out ->
                        val buf = ByteArray(262144)
                        var n: Int
                        var done = 0L
                        while (input.read(buf).also { n = it } > 0) {
                            out.write(buf, 0, n)
                            done += n
                            if (total > 0) runOnUiThread { progress.progress = (done * 100 / total).toInt() }
                        }
                    }
                }
                runOnUiThread { status.text = "✓ Модель готова" }
            } catch (e: Throwable) {
                runOnUiThread { status.text = "Ошибка модели: ${e.message}" }
            }
        }
    }

    private data class FaceCrop(
        val bitmap: Bitmap,
        val left: Int,
        val top: Int,
        val width: Int,
        val height: Int
    )

    private fun detectFace(b: Bitmap): Rect {
        val d = FaceDetection.getClient(
            FaceDetectorOptions.Builder()
                .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_ACCURATE)
                .build()
        )
        val task = d.process(InputImage.fromBitmap(b, 0))
        while (!task.isComplete) Thread.sleep(20)
        if (!task.isSuccessful) throw task.exception ?: RuntimeException("Face detector")
        val faces = task.result ?: emptyList()
        if (faces.isEmpty()) throw RuntimeException("Лицо не найдено")
        return faces.maxBy { it.boundingBox.width() * it.boundingBox.height() }.boundingBox
    }

    /*
     * V0.4: не берём огромный квадрат 1.5x вокруг лица.
     * Используем сам face box с небольшими полями, как ближе к пайплайну Wav2Lip.
     */
    private fun cropInfo(b: Bitmap, r: Rect): FaceCrop {
        val fw = r.width().coerceAtLeast(1)
        val fh = r.height().coerceAtLeast(1)
        val left = (r.left - fw * 0.12f).roundToInt().coerceAtLeast(0)
        val right = (r.right + fw * 0.12f).roundToInt().coerceAtMost(b.width)
        val top = (r.top - fh * 0.10f).roundToInt().coerceAtLeast(0)
        val bottom = (r.bottom + fh * 0.18f).roundToInt().coerceAtMost(b.height)
        val w = (right - left).coerceAtLeast(2)
        val h = (bottom - top).coerceAtLeast(2)
        val raw = Bitmap.createBitmap(b, left, top, w, h)
        return FaceCrop(Bitmap.createScaledBitmap(raw, 96, 96, true), left, top, w, h)
    }

    /*
     * Критическая ошибка V0.3 была здесь:
     * Wav2Lip ожидает, что у masked-копии занулена НИЖНЯЯ половина лица.
     * В V0.3 была занулена верхняя половина, поэтому верх кадра превращался в мусор.
     */
    private fun imageTensor(b: Bitmap): FloatArray {
        val pix = IntArray(96 * 96)
        b.getPixels(pix, 0, 96, 0, 0, 96, 96)
        val out = FloatArray(6 * 96 * 96)
        for (y in 0 until 96) {
            for (x in 0 until 96) {
                val p = pix[y * 96 + x]
                val rgb = floatArrayOf(Color.red(p) / 255f, Color.green(p) / 255f, Color.blue(p) / 255f)
                for (c in 0..2) {
                    val v = rgb[c]
                    out[c * 96 * 96 + y * 96 + x] = if (y >= 48) 0f else v
                    out[(c + 3) * 96 * 96 + y * 96 + x] = v
                }
            }
        }
        return out
    }

    private fun outputBitmap(v: Any): Bitmap {
        val a = v as Array<*>
        val c = a[0] as Array<*>
        val out = Bitmap.createBitmap(96, 96, Bitmap.Config.ARGB_8888)
        val pix = IntArray(96 * 96)
        for (y in 0 until 96) for (x in 0 until 96) {
            fun ch(k: Int): Int {
                val row = (c[k] as Array<*>)[y] as FloatArray
                return (row[x].coerceIn(0f, 1f) * 255f).roundToInt()
            }
            pix[y * 96 + x] = Color.rgb(ch(0), ch(1), ch(2))
        }
        out.setPixels(pix, 0, 96, 0, 0, 96, 96)
        return out
    }

    private fun smoothStep(edge0: Float, edge1: Float, x: Float): Float {
        if (edge1 <= edge0) return if (x >= edge1) 1f else 0f
        val t = ((x - edge0) / (edge1 - edge0)).coerceIn(0f, 1f)
        return t * t * (3f - 2f * t)
    }

    /*
     * V0.4: вставляем только нижнюю часть сгенерированного лица.
     * Глаза/волосы/фон остаются из оригинала. По краям мягкое feather-смешивание.
     */
    private fun compositeLower(base: Bitmap, generated96: Bitmap, c: FaceCrop): Bitmap {
        val out = base.copy(Bitmap.Config.ARGB_8888, true)
        val generated = Bitmap.createScaledBitmap(generated96, c.width, c.height, true)
        val original = IntArray(c.width * c.height)
        val gen = IntArray(c.width * c.height)
        out.getPixels(original, 0, c.width, c.left, c.top, c.width, c.height)
        generated.getPixels(gen, 0, c.width, 0, 0, c.width, c.height)

        for (y in 0 until c.height) {
            val fy = y.toFloat() / max(1, c.height - 1)
            // До ~42% высоты crop ничего не меняем; 42–58% — мягкий переход.
            val vertical = smoothStep(0.42f, 0.58f, fy)
            for (x in 0 until c.width) {
                if (vertical <= 0f) continue
                val fx = x.toFloat() / max(1, c.width - 1)
                val leftFeather = smoothStep(0.03f, 0.15f, fx)
                val rightFeather = 1f - smoothStep(0.85f, 0.97f, fx)
                val alpha = (vertical * min(leftFeather, rightFeather)).coerceIn(0f, 1f)
                if (alpha <= 0f) continue
                val i = y * c.width + x
                val a = original[i]
                val g = gen[i]
                fun mix(ca: Int, cg: Int) = (ca * (1f - alpha) + cg * alpha).roundToInt().coerceIn(0, 255)
                original[i] = Color.rgb(
                    mix(Color.red(a), Color.red(g)),
                    mix(Color.green(a), Color.green(g)),
                    mix(Color.blue(a), Color.blue(g))
                )
            }
        }
        out.setPixels(original, 0, c.width, c.left, c.top, c.width, c.height)
        generated.recycle()
        return out
    }

    private fun generate() {
        if (imageUri == null || audioUri == null) { status.text = "Сначала выбери картинку и WAV."; return }
        if (!modelFile().exists()) { status.text = "Сначала скачай модель."; return }
        thread {
            try {
                val started = System.currentTimeMillis()
                runOnUiThread { status.text = "Ищу лицо…"; progress.progress = 1 }
                val src = contentResolver.openInputStream(imageUri!!)!!.use { BitmapFactory.decodeStream(it) }
                val base = scaleEven(src, 720)
                val rect = detectFace(base)
                val crop = cropInfo(base, rect)
                val wav = contentResolver.openInputStream(audioUri!!)!!.use { WavUtils.readPcm16(it) }
                val samples = wav.samples.copyOf(min(wav.samples.size, 16000 * 5))
                val mel = WavUtils.melSpectrogram(samples)
                val frames = min(125, max(1, (samples.size / 16000f * 25).toInt()))
                val env = OrtEnvironment.getEnvironment()
                val session = env.createSession(modelFile().absolutePath, OrtSession.SessionOptions())
                val names = session.inputNames.toList()
                val melName = names.firstOrNull { it.contains("mel", true) } ?: names[0]
                val imgName = names.firstOrNull { it.contains("video", true) || it.contains("frame", true) || it.contains("img", true) } ?: names.last()
                val imageInput = imageTensor(crop.bitmap)
                val rendered = ArrayList<Bitmap>(frames)

                for (f in 0 until frames) {
                    val mi = (f * 80.0 / 25.0).toInt().coerceAtMost(max(0, mel[0].size - 16))
                    val mf = FloatArray(80 * 16)
                    for (y in 0 until 80) for (x in 0 until 16) {
                        mf[y * 16 + x] = mel[y][(mi + x).coerceAtMost(mel[y].lastIndex)]
                    }
                    val face = OnnxTensor.createTensor(env, FloatBuffer.wrap(mf), longArrayOf(1, 1, 80, 16)).use { mt ->
                        OnnxTensor.createTensor(env, FloatBuffer.wrap(imageInput), longArrayOf(1, 6, 96, 96)).use { img ->
                            session.run(mapOf(melName to mt, imgName to img)).use { r -> outputBitmap(r[0].value) }
                        }
                    }
                    rendered.add(compositeLower(base, face, crop))
                    face.recycle()
                    if (f % 3 == 0) runOnUiThread {
                        progress.progress = 1 + f * 75 / frames
                        status.text = "V0.4 lip-sync: ${f + 1}/$frames кадров"
                    }
                }
                session.close()
                val tmp = File(cacheDir, "v04_${System.currentTimeMillis()}.mp4")
                encodeMp4(rendered, samples, tmp)
                rendered.forEach { it.recycle() }
                saveMovie(tmp)
                val sec = (System.currentTimeMillis() - started) / 1000.0
                runOnUiThread {
                    progress.progress = 100
                    status.text = "✓ V0.4 ГОТОВА\n✓ Исправлена нижняя mask Wav2Lip\n✓ Новый face crop\n✓ Мягкий paste-back нижней части лица\n✓ $frames кадров / H.264 + AAC\n⏱ ${"%.1f".format(sec)} сек\n📁 Movies/DoramaAvatar\n\nПришли MP4 — проверим рот и границы."
                    Toast.makeText(this, "MP4 V0.4 сохранён", Toast.LENGTH_LONG).show()
                }
            } catch (e: Throwable) {
                runOnUiThread { status.text = "Ошибка V0.4: ${e.javaClass.simpleName}: ${e.message}" }
            }
        }
    }

    private fun scaleEven(b: Bitmap, maxSide: Int): Bitmap {
        val k = min(1f, maxSide.toFloat() / max(b.width, b.height))
        var w = (b.width * k).toInt().coerceAtLeast(2)
        var h = (b.height * k).toInt().coerceAtLeast(2)
        w -= w % 2; h -= h % 2
        return Bitmap.createScaledBitmap(b, w, h, true)
    }

    private data class Sample(val data: ByteArray, val info: MediaCodec.BufferInfo)

    private fun encodeMp4(frames: List<Bitmap>, audio: FloatArray, out: File) {
        val w = frames[0].width; val h = frames[0].height
        val vf = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, w, h)
        vf.setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible)
        vf.setInteger(MediaFormat.KEY_BIT_RATE, 2_500_000)
        vf.setInteger(MediaFormat.KEY_FRAME_RATE, 25)
        vf.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
        val v = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        v.configure(vf, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE); v.start()

        val af = MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, 16000, 1)
        af.setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
        af.setInteger(MediaFormat.KEY_BIT_RATE, 64000)
        val a = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
        a.configure(af, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE); a.start()

        val mux = MediaMuxer(out.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        var vt = -1; var at = -1; var muxStarted = false
        val pendingV = ArrayList<Sample>(); val pendingA = ArrayList<Sample>()

        fun drain(codec: MediaCodec, isVideo: Boolean, eos: Boolean) {
            val info = MediaCodec.BufferInfo()
            while (true) {
                val ix = codec.dequeueOutputBuffer(info, if (eos) 10000 else 0)
                if (ix == MediaCodec.INFO_TRY_AGAIN_LATER) { if (!eos) break else continue }
                if (ix == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    if (isVideo) vt = mux.addTrack(codec.outputFormat) else at = mux.addTrack(codec.outputFormat)
                    if (vt >= 0 && at >= 0 && !muxStarted) {
                        mux.start(); muxStarted = true
                        for (s in pendingV) mux.writeSampleData(vt, java.nio.ByteBuffer.wrap(s.data), s.info)
                        for (s in pendingA) mux.writeSampleData(at, java.nio.ByteBuffer.wrap(s.data), s.info)
                        pendingV.clear(); pendingA.clear()
                    }
                    continue
                }
                if (ix >= 0) {
                    val ob = codec.getOutputBuffer(ix)!!
                    if (info.size > 0 && (info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG) == 0) {
                        ob.position(info.offset); ob.limit(info.offset + info.size)
                        val bytes = ByteArray(info.size); ob.get(bytes)
                        val cp = MediaCodec.BufferInfo(); cp.set(0, bytes.size, info.presentationTimeUs, info.flags)
                        if (muxStarted) mux.writeSampleData(if (isVideo) vt else at, java.nio.ByteBuffer.wrap(bytes), cp)
                        else (if (isVideo) pendingV else pendingA).add(Sample(bytes, cp))
                    }
                    val end = (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0
                    codec.releaseOutputBuffer(ix, false)
                    if (end) break
                }
            }
        }

        for ((i, b) in frames.withIndex()) {
            var ix = v.dequeueInputBuffer(10000)
            while (ix < 0) { drain(v, true, false); ix = v.dequeueInputBuffer(10000) }
            val buf = v.getInputBuffer(ix)!!; val yuv = toI420(b)
            buf.clear(); buf.put(yuv)
            v.queueInputBuffer(ix, 0, yuv.size, i * 40000L, 0)
            drain(v, true, false)
        }
        var vix = v.dequeueInputBuffer(10000)
        if (vix >= 0) v.queueInputBuffer(vix, 0, 0, frames.size * 40000L, MediaCodec.BUFFER_FLAG_END_OF_STREAM)

        var pos = 0; val chunk = 1024
        while (pos < audio.size) {
            var ai = a.dequeueInputBuffer(10000)
            while (ai < 0) { drain(a, false, false); ai = a.dequeueInputBuffer(10000) }
            val n = min(chunk, audio.size - pos); val bb = a.getInputBuffer(ai)!!; bb.clear()
            for (j in 0 until n) {
                val s = (audio[pos + j].coerceIn(-1f, 1f) * 32767).toInt().toShort()
                bb.put((s.toInt() and 255).toByte()); bb.put(((s.toInt() shr 8) and 255).toByte())
            }
            a.queueInputBuffer(ai, 0, n * 2, pos * 1_000_000L / 16000, 0)
            pos += n; drain(a, false, false)
        }
        val aix = a.dequeueInputBuffer(10000)
        if (aix >= 0) a.queueInputBuffer(aix, 0, 0, pos * 1_000_000L / 16000, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
        drain(v, true, true); drain(a, false, true)
        v.stop(); a.stop(); v.release(); a.release(); if (muxStarted) mux.stop(); mux.release()
    }

    private fun toI420(b: Bitmap): ByteArray {
        val w = b.width; val h = b.height
        val p = IntArray(w * h); b.getPixels(p, 0, w, 0, 0, w, h)
        val out = ByteArray(w * h * 3 / 2); var yi = 0; var ui = w * h; var vi = ui + w * h / 4
        for (y in 0 until h) for (x in 0 until w) {
            val c = p[y * w + x]; val r = Color.red(c); val g = Color.green(c); val bl = Color.blue(c)
            out[yi++] = ((77 * r + 150 * g + 29 * bl) shr 8).coerceIn(0, 255).toByte()
            if (y % 2 == 0 && x % 2 == 0) {
                out[ui++] = (((-43 * r - 85 * g + 128 * bl) shr 8) + 128).coerceIn(0, 255).toByte()
                out[vi++] = (((128 * r - 107 * g - 21 * bl) shr 8) + 128).coerceIn(0, 255).toByte()
            }
        }
        return out
    }

    private fun saveMovie(f: File): Uri {
        val cv = ContentValues().apply {
            put(MediaStore.Video.Media.DISPLAY_NAME, "DoramaAvatar_V04_${System.currentTimeMillis()}.mp4")
            put(MediaStore.Video.Media.MIME_TYPE, "video/mp4")
            put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/DoramaAvatar")
        }
        val u = contentResolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, cv)
            ?: throw RuntimeException("Не удалось создать MP4")
        contentResolver.openOutputStream(u)!!.use { o -> f.inputStream().use { it.copyTo(o) } }
        f.delete(); return u
    }

    private fun name(u: Uri): String {
        contentResolver.query(u, null, null, null, null)?.use { c ->
            val i = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (c.moveToFirst() && i >= 0) return c.getString(i)
        }
        return u.lastPathSegment ?: "file"
    }
}
