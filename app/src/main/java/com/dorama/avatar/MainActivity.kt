package com.dorama.avatar

import ai.onnxruntime.*
import android.content.ContentValues
import android.graphics.*
import android.media.*
import android.net.Uri
import android.os.Bundle
import android.os.Build
import android.os.Environment
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
    private lateinit var mouthOffsetLabel: TextView
    private var mouthOffsetPercent: Int = -4

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
        findViewById<Button>(R.id.imageButton).setOnClickListener { imagePicker.launch(arrayOf("image/*")) }
        findViewById<Button>(R.id.audioButton).setOnClickListener { audioPicker.launch(arrayOf("audio/*")) }
        findViewById<Button>(R.id.modelButton).setOnClickListener { downloadModel() }
        findViewById<Button>(R.id.generateButton).setOnClickListener { generate() }
    }

    private fun modelFile() = File(filesDir, "wav2lip_facefusion_gan96.onnx")

    private fun downloadModel() {
        if (modelFile().exists() && modelFile().length() > 100_000_000) {
            status.text = "✓ Модель уже есть: ${modelFile().length() / 1024 / 1024} МБ"
            return
        }
        thread {
            try {
                runOnUiThread { status.text = "Скачиваю FaceFusion Wav2Lip GAN 96…"; progress.progress = 0 }
                val c = URL("https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/wav2lip_gan_96.onnx").openConnection()
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
                runOnUiThread { status.text = "✓ FaceFusion Wav2Lip GAN 96 готова" }
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
     * V0.7: не берём огромный квадрат 1.5x вокруг лица.
     * Используем сам face box с небольшими полями, как ближе к пайплайну Wav2Lip.
     */
    private fun cropInfo(b: Bitmap, r: Rect): FaceCrop {
        // Ближе к оригинальному Wav2Lip: face box + только нижний pad 10 px.
        val left = r.left.coerceIn(0, b.width - 2)
        val right = r.right.coerceIn(left + 2, b.width)
        val top = r.top.coerceIn(0, b.height - 2)
        val bottom = (r.bottom + 10).coerceIn(top + 2, b.height)
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
    /*
     * Оригинальный Wav2Lip получает изображения через OpenCV (BGR),
     * затем NHWC -> NCHW. Поэтому в Android явно подаём B,G,R.
     */
    private fun imageTensor(b: Bitmap): FloatArray {
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
        return out
    }

    /*
     * V0.7: не предполагаем layout выхода ONNX заранее.
     * Поддерживаем [1,3,96,96] (NCHW) и [1,96,96,3] (NHWC).
     * Каналы модели BGR, Bitmap ожидает RGB.
     */
    private fun outputBitmap(v: Any): Bitmap {
        val batch = v as? Array<*> ?: throw RuntimeException("ONNX output: не Array")
        val first = batch.firstOrNull() as? Array<*> ?: throw RuntimeException("ONNX output: пустой batch")
        val out = Bitmap.createBitmap(96, 96, Bitmap.Config.ARGB_8888)
        val pix = IntArray(96 * 96)

        if (first.size == 3) {
            // NCHW: [1][3][96][96]
            for (y in 0 until 96) for (x in 0 until 96) {
                fun ch(k: Int): Int {
                    val row = (first[k] as Array<*>)[y] as FloatArray
                    return (row[x].coerceIn(0f, 1f) * 255f).roundToInt()
                }
                pix[y * 96 + x] = Color.rgb(ch(2), ch(1), ch(0))
            }
        } else if (first.size == 96) {
            // NHWC: [1][96][96][3]
            for (y in 0 until 96) {
                val row = first[y] as Array<*>
                for (x in 0 until 96) {
                    val bgr = row[x] as FloatArray
                    val b = (bgr[0].coerceIn(0f, 1f) * 255f).roundToInt()
                    val g = (bgr[1].coerceIn(0f, 1f) * 255f).roundToInt()
                    val r = (bgr[2].coerceIn(0f, 1f) * 255f).roundToInt()
                    pix[y * 96 + x] = Color.rgb(r, g, b)
                }
            }
        } else {
            throw RuntimeException("Неизвестный ONNX output layout: first=${first.size}")
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
     * V0.7: вставляем только нижнюю часть сгенерированного лица.
     * Глаза/волосы/фон остаются из оригинала. По краям мягкое feather-смешивание.
     */
    private fun compositeMouth(
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
                val melName = names.firstOrNull { it.contains("mel", true) || it.contains("audio", true) || it.contains("source", true) } ?: names[0]
                val imgName = names.firstOrNull { it.contains("video", true) || it.contains("frame", true) || it.contains("img", true) || it.contains("face", true) || it.contains("target", true) } ?: names.last()
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
                    val composed = compositeMouth(base, face, crop, mouthOffsetPercent)
                    if (f == 0) {
                        val stamp = System.currentTimeMillis()
                        savePng(crop.bitmap, "V08_01_input_crop_${stamp}.png")
                        savePng(face, "V08_02_wav2lip_face_${stamp}.png")
                        savePng(composed, "V08_03_composite_before_encoder_${stamp}.png")
                    }
                    rendered.add(composed)
                    face.recycle()
                    if (f % 3 == 0) runOnUiThread {
                        progress.progress = 1 + f * 75 / frames
                        status.text = "V0.8 lip-sync: ${f + 1}/$frames кадров"
                    }
                }
                session.close()
                val tmp = File(cacheDir, "v08_${System.currentTimeMillis()}.mp4")
                val encoderInfo = encodeMp4(rendered, samples, tmp)
                rendered.forEach { it.recycle() }
                saveMovie(tmp)
                val sec = (System.currentTimeMillis() - started) / 1000.0
                runOnUiThread {
                    progress.progress = 100
                    status.text = "✓ V0.8 ГОТОВА\n✓ PNG до кодирования сохранены в Pictures/DoramaAvatar\n✓ MP4: ${encoderInfo.width}x${encoderInfo.height}\n✓ AVC codec: ${encoderInfo.codec}\n✓ YUV format: ${encoderInfo.colorFormat}\n✓ $frames кадров / H.264 + AAC\n⏱ ${"%.1f".format(sec)} сек\n📁 Movies/DoramaAvatar\n\nСдвиг рта: ${mouthOffsetPercent}%\nПришли V08_03 + MP4, если нужна ещё подгонка."
                    Toast.makeText(this, "V0.8: MP4 + PNG сохранены", Toast.LENGTH_LONG).show()
                }
            } catch (e: Throwable) {
                runOnUiThread { status.text = "Ошибка V0.8: ${e.javaClass.simpleName}: ${e.message}" }
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
    private data class EncoderInfo(val codec: String, val colorFormat: Int, val width: Int, val height: Int)

    private fun align16(v: Int): Int = ((v + 15) / 16) * 16

    private fun padToSize(src: Bitmap, w: Int, h: Int): Bitmap {
        if (src.width == w && src.height == h) return src
        val out = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val c = Canvas(out)
        c.drawColor(Color.BLACK)
        c.drawBitmap(src, 0f, 0f, Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG))
        return out
    }

    private fun chooseAvcEncoder(): Pair<MediaCodecInfo, Int> {
        val infos = MediaCodecList(MediaCodecList.REGULAR_CODECS).codecInfos
        val codec = infos.firstOrNull { info ->
            info.isEncoder && info.supportedTypes.any { it.equals(MediaFormat.MIMETYPE_VIDEO_AVC, true) }
        } ?: throw RuntimeException("AVC encoder не найден")
        val colors = codec.getCapabilitiesForType(MediaFormat.MIMETYPE_VIDEO_AVC).colorFormats.toSet()
        val chosen = when {
            colors.contains(MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar) -> MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar
            colors.contains(MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Planar) -> MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Planar
            colors.contains(MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible) -> MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible
            else -> throw RuntimeException("Нет поддерживаемого ByteBuffer YUV420. Форматы: ${colors.joinToString()}")
        }
        return codec to chosen
    }

    private fun encodeMp4(frames: List<Bitmap>, audio: FloatArray, out: File): EncoderInfo {
        val width = align16(frames[0].width)
        val height = align16(frames[0].height)
        val (codecInfo, colorFormat) = chooseAvcEncoder()

        val vf = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, width, height)
        vf.setInteger(MediaFormat.KEY_COLOR_FORMAT, colorFormat)
        vf.setInteger(MediaFormat.KEY_BIT_RATE, 2_500_000)
        vf.setInteger(MediaFormat.KEY_FRAME_RATE, 25)
        vf.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
        val v = MediaCodec.createByCodecName(codecInfo.name)
        v.configure(vf, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        v.start()

        val af = MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, 16000, 1)
        af.setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
        af.setInteger(MediaFormat.KEY_BIT_RATE, 64000)
        val a = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
        a.configure(af, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        a.start()

        val mux = MediaMuxer(out.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        var vt = -1; var at = -1; var muxStarted = false
        val pendingV = ArrayList<Sample>(); val pendingA = ArrayList<Sample>()

        fun drain(codec: MediaCodec, isVideo: Boolean, eos: Boolean) {
            val info = MediaCodec.BufferInfo()
            var idle = 0
            while (true) {
                val ix = codec.dequeueOutputBuffer(info, if (eos) 10000 else 0)
                if (ix == MediaCodec.INFO_TRY_AGAIN_LATER) {
                    if (!eos) break
                    if (++idle > 300) throw RuntimeException("Encoder EOS timeout")
                    continue
                }
                idle = 0
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

        for ((i, src) in frames.withIndex()) {
            val frame = padToSize(src, width, height)
            val yuv = when (colorFormat) {
                MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar -> toNv12(frame)
                else -> toI420(frame)
            }
            if (frame !== src) frame.recycle()
            var ix = v.dequeueInputBuffer(10000)
            while (ix < 0) { drain(v, true, false); ix = v.dequeueInputBuffer(10000) }
            val buf = v.getInputBuffer(ix)!!
            if (buf.capacity() < yuv.size) throw RuntimeException("Video input buffer ${buf.capacity()} < ${yuv.size}")
            buf.clear(); buf.put(yuv)
            v.queueInputBuffer(ix, 0, yuv.size, i * 40000L, 0)
            drain(v, true, false)
        }
        var vix = v.dequeueInputBuffer(10000)
        while (vix < 0) { drain(v, true, false); vix = v.dequeueInputBuffer(10000) }
        v.queueInputBuffer(vix, 0, 0, frames.size * 40000L, MediaCodec.BUFFER_FLAG_END_OF_STREAM)

        var pos = 0; val chunk = 1024
        while (pos < audio.size) {
            var ai = a.dequeueInputBuffer(10000)
            while (ai < 0) { drain(a, false, false); ai = a.dequeueInputBuffer(10000) }
            val n = min(chunk, audio.size - pos); val bb = a.getInputBuffer(ai)!!; bb.clear()
            for (j in 0 until n) {
                val smp = (audio[pos + j].coerceIn(-1f, 1f) * 32767).toInt().toShort()
                bb.put((smp.toInt() and 255).toByte()); bb.put(((smp.toInt() shr 8) and 255).toByte())
            }
            a.queueInputBuffer(ai, 0, n * 2, pos * 1_000_000L / 16000, 0)
            pos += n; drain(a, false, false)
        }
        var aix = a.dequeueInputBuffer(10000)
        while (aix < 0) { drain(a, false, false); aix = a.dequeueInputBuffer(10000) }
        a.queueInputBuffer(aix, 0, 0, pos * 1_000_000L / 16000, MediaCodec.BUFFER_FLAG_END_OF_STREAM)

        drain(v, true, true); drain(a, false, true)
        v.stop(); a.stop(); v.release(); a.release()
        if (muxStarted) mux.stop()
        mux.release()
        return EncoderInfo(codecInfo.name, colorFormat, width, height)
    }

    private fun rgbToYuv(c: Int): IntArray {
        val r = Color.red(c); val g = Color.green(c); val b = Color.blue(c)
        val y = (((66 * r + 129 * g + 25 * b + 128) shr 8) + 16).coerceIn(0, 255)
        val u = (((-38 * r - 74 * g + 112 * b + 128) shr 8) + 128).coerceIn(0, 255)
        val v = (((112 * r - 94 * g - 18 * b + 128) shr 8) + 128).coerceIn(0, 255)
        return intArrayOf(y, u, v)
    }

    private fun toI420(b: Bitmap): ByteArray {
        val w = b.width; val h = b.height
        val p = IntArray(w * h); b.getPixels(p, 0, w, 0, 0, w, h)
        val out = ByteArray(w * h * 3 / 2)
        var yi = 0; var ui = w * h; var vi = ui + w * h / 4
        for (y in 0 until h) for (x in 0 until w) {
            val yy = rgbToYuv(p[y * w + x]); out[yi++] = yy[0].toByte()
            if (y % 2 == 0 && x % 2 == 0) { out[ui++] = yy[1].toByte(); out[vi++] = yy[2].toByte() }
        }
        return out
    }

    private fun toNv12(b: Bitmap): ByteArray {
        val w = b.width; val h = b.height
        val p = IntArray(w * h); b.getPixels(p, 0, w, 0, 0, w, h)
        val out = ByteArray(w * h * 3 / 2)
        var yi = 0; var uvi = w * h
        for (y in 0 until h) for (x in 0 until w) {
            val yy = rgbToYuv(p[y * w + x]); out[yi++] = yy[0].toByte()
            if (y % 2 == 0 && x % 2 == 0) { out[uvi++] = yy[1].toByte(); out[uvi++] = yy[2].toByte() }
        }
        return out
    }

    private fun savePng(bitmap: Bitmap, fileName: String): Uri? {
        return try {
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, fileName)
                put(MediaStore.Images.Media.MIME_TYPE, "image/png")
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/DoramaAvatar")
                }
            }
            val uri = contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values) ?: return null
            contentResolver.openOutputStream(uri)!!.use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
            uri
        } catch (_: Throwable) { null }
    }

    private fun saveMovie(f: File): Uri {
        val cv = ContentValues().apply {
            put(MediaStore.Video.Media.DISPLAY_NAME, "DoramaAvatar_V08_${System.currentTimeMillis()}.mp4")
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
