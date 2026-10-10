package com.dorama.avatar

import java.io.InputStream
import kotlin.math.*

data class WavData(val samples: FloatArray, val sampleRate: Int)

object WavUtils {
    private const val TARGET_SR = 16000
    private const val N_FFT = 800
    private const val HOP = 200
    private const val WIN = 800
    private const val N_MELS = 80
    private const val FMIN = 55.0
    private const val FMAX = 7600.0
    private const val PREEMPH = 0.97f
    private const val MIN_LEVEL_DB = -100.0
    private const val REF_LEVEL_DB = 20.0
    private const val MAX_ABS_VALUE = 4.0f

    fun readPcm16(input: InputStream): WavData {
        val b = input.readBytes()
        require(b.size > 44 && String(b, 0, 4) == "RIFF" && String(b, 8, 4) == "WAVE") {
            "Нужен обычный WAV PCM"
        }
        var p = 12
        var sr = TARGET_SR
        var channels = 1
        var bits = 16
        var data = -1
        var dataLen = 0
        while (p + 8 <= b.size) {
            val id = String(b, p, 4)
            val n = le32(b, p + 4)
            val q = p + 8
            if (id == "fmt " && n >= 16) {
                channels = le16(b, q + 2)
                sr = le32(b, q + 4)
                bits = le16(b, q + 14)
            }
            if (id == "data") {
                data = q
                dataLen = min(n, b.size - q)
                break
            }
            p = q + n + (n and 1)
        }
        require(data >= 0 && bits == 16) { "Поддерживается WAV PCM 16-bit" }

        val frames = dataLen / (2 * channels)
        val mono = FloatArray(frames)
        for (i in 0 until frames) {
            var sum = 0f
            for (c in 0 until channels) {
                val k = data + (i * channels + c) * 2
                val v = ((b[k].toInt() and 255) or (b[k + 1].toInt() shl 8)).toShort()
                sum += v / 32768f
            }
            mono[i] = sum / channels
        }
        return if (sr == TARGET_SR) WavData(mono, sr)
        else WavData(resample(mono, sr, TARGET_SR), TARGET_SR)
    }

    private fun resample(x: FloatArray, from: Int, to: Int): FloatArray {
        val n = (x.size.toLong() * to / from).toInt().coerceAtLeast(1)
        return FloatArray(n) { i ->
            val pos = i.toDouble() * from / to
            val a = floor(pos).toInt().coerceIn(0, x.lastIndex)
            val z = (a + 1).coerceAtMost(x.lastIndex)
            val t = (pos - a).toFloat()
            x[a] * (1f - t) + x[z] * t
        }
    }

    /*
     * Wav2Lip uses librosa.stft(center=true, pad_mode=reflect),
     * scipy lfilter pre-emphasis [1, -0.97], Slaney mel filters,
     * amplitude-to-dB and normalization to [-4, +4].
     */
    fun melSpectrogram(x: FloatArray, sr: Int = TARGET_SR): Array<FloatArray> {
        require(sr == TARGET_SR) { "Ожидается 16 kHz" }
        if (x.isEmpty()) return Array(N_MELS) { FloatArray(1) }

        val emphasized = FloatArray(x.size)
        emphasized[0] = x[0]
        for (i in 1 until x.size) emphasized[i] = x[i] - PREEMPH * x[i - 1]

        val pad = N_FFT / 2
        val y = reflectPad(emphasized, pad)
        val frames = 1 + (y.size - N_FFT) / HOP
        val bins = N_FFT / 2 + 1

        // librosa/scipy Hann with fftbins=true => periodic Hann (denominator WIN)
        val window = FloatArray(WIN) { n ->
            (0.5 - 0.5 * cos(2.0 * PI * n / WIN)).toFloat()
        }
        val cosT = Array(bins) { k ->
            FloatArray(N_FFT) { n -> cos(2.0 * PI * k * n / N_FFT).toFloat() }
        }
        val sinT = Array(bins) { k ->
            FloatArray(N_FFT) { n -> sin(2.0 * PI * k * n / N_FFT).toFloat() }
        }
        val melBasis = buildSlaneyMelBasis(sr, N_FFT, N_MELS, FMIN, FMAX)
        val result = Array(N_MELS) { FloatArray(frames) }
        val minLevel = exp(MIN_LEVEL_DB / 20.0 * ln(10.0))

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
                mag[k] = sqrt(re * re + im * im).toFloat()
            }

            for (m in 0 until N_MELS) {
                var amp = 0.0
                for (k in 0 until bins) amp += melBasis[m][k] * mag[k]
                val db = 20.0 * log10(max(minLevel, amp)) - REF_LEVEL_DB
                val norm = (2.0 * MAX_ABS_VALUE) * ((db - MIN_LEVEL_DB) / (-MIN_LEVEL_DB)) - MAX_ABS_VALUE
                result[m][t] = norm.toFloat().coerceIn(-MAX_ABS_VALUE, MAX_ABS_VALUE)
            }
        }
        return result
    }

    private fun reflectPad(x: FloatArray, pad: Int): FloatArray {
        if (x.size <= 1) return FloatArray(x.size + pad * 2) { x.getOrElse(0) { 0f } }
        val out = FloatArray(x.size + 2 * pad)
        for (i in out.indices) {
            var j = i - pad
            while (j < 0 || j >= x.size) {
                j = if (j < 0) -j else 2 * x.size - 2 - j
            }
            out[i] = x[j]
        }
        return out
    }

    private fun buildSlaneyMelBasis(
        sr: Int,
        nFft: Int,
        nMels: Int,
        fMin: Double,
        fMax: Double
    ): Array<FloatArray> {
        val bins = nFft / 2 + 1
        val fftFreqs = DoubleArray(bins) { it.toDouble() * sr / nFft }
        val melMin = hzToMelSlaney(fMin)
        val melMax = hzToMelSlaney(fMax)
        val melFreqs = DoubleArray(nMels + 2) { i ->
            melToHzSlaney(melMin + (melMax - melMin) * i / (nMels + 1))
        }
        val basis = Array(nMels) { FloatArray(bins) }
        for (m in 0 until nMels) {
            val left = melFreqs[m]
            val center = melFreqs[m + 1]
            val right = melFreqs[m + 2]
            val lowerDen = max(1e-12, center - left)
            val upperDen = max(1e-12, right - center)
            val areaNorm = 2.0 / max(1e-12, right - left)
            for (k in 0 until bins) {
                val f = fftFreqs[k]
                val lower = (f - left) / lowerDen
                val upper = (right - f) / upperDen
                basis[m][k] = (max(0.0, min(lower, upper)) * areaNorm).toFloat()
            }
        }
        return basis
    }

    private fun hzToMelSlaney(hz: Double): Double {
        val fSp = 200.0 / 3.0
        val minLogHz = 1000.0
        val minLogMel = minLogHz / fSp
        val logStep = ln(6.4) / 27.0
        return if (hz >= minLogHz) minLogMel + ln(hz / minLogHz) / logStep else hz / fSp
    }

    private fun melToHzSlaney(mel: Double): Double {
        val fSp = 200.0 / 3.0
        val minLogHz = 1000.0
        val minLogMel = minLogHz / fSp
        val logStep = ln(6.4) / 27.0
        return if (mel >= minLogMel) minLogHz * exp(logStep * (mel - minLogMel)) else fSp * mel
    }


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

    // V144_MEL_DIAGNOSTICS: report-only, no inference changes.
    fun edtalkMelReport(spec: Array<FloatArray>, totalFrames: Int): String {
        val picks = listOf(0, totalFrames / 4, totalFrames / 2, 3 * totalFrames / 4, totalFrames - 1)
            .filter { it >= 0 }.distinct()
        val gain = WIN * 0.5f // Hann sum = 400 for 800 samples
        val sb = StringBuilder("EDTalk V1.4.4 mel comparison\n")
        sb.append("Current: log10(max(raw,1e-5))*1.6+3.2, clamp [-4,4]\n")
        sb.append("Alternative: multiply raw by 400 before log; diagnostic only\n")
        for (f in picks) {
            val current = edtalkFrame(spec, f)
            val start = floor(f * 80.0 / 25).toInt()
            val alternative = FloatArray(N_MELS * 16)
            for (mel in 0 until N_MELS) for (i in 0 until 16) {
                val raw = spec[mel][(start + i).coerceAtMost(spec[mel].lastIndex)]
                alternative[mel * 16 + i] =
                    (log10(max(1e-5f, raw * gain).toDouble()) * 1.6 + 3.2).toFloat().coerceIn(-4f, 4f)
            }
            fun stats(label: String, a: FloatArray): String =
                "$label min=${a.minOrNull()} max=${a.maxOrNull()} mean=${a.average()} floor=${a.count { it <= -3.999f }}/${a.size}\n"
            sb.append("frame=$f\n")
            sb.append(stats("current", current))
            sb.append(stats("windowGain400", alternative))
        }
        return sb.toString()
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

    private fun le16(b: ByteArray, p: Int) =
        (b[p].toInt() and 255) or ((b[p + 1].toInt() and 255) shl 8)

    private fun le32(b: ByteArray, p: Int) = le16(b, p) or (le16(b, p + 2) shl 16)
}
