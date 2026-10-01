package com.dorama.avatar

import java.io.InputStream
import kotlin.math.*

data class WavData(val samples: FloatArray, val sampleRate: Int)

object WavUtils {
    fun readPcm16(input: InputStream): WavData {
        val b = input.readBytes()
        require(b.size > 44 && String(b,0,4) == "RIFF" && String(b,8,4) == "WAVE") { "Нужен обычный WAV PCM" }
        var p=12; var sr=16000; var channels=1; var bits=16; var data=-1; var dataLen=0
        while (p+8 <= b.size) {
            val id=String(b,p,4); val n=le32(b,p+4); val q=p+8
            if (id=="fmt " && n>=16) { channels=le16(b,q+2); sr=le32(b,q+4); bits=le16(b,q+14) }
            if (id=="data") { data=q; dataLen=min(n,b.size-q); break }
            p=q+n+(n and 1)
        }
        require(data>=0 && bits==16) { "Поддерживается WAV PCM 16-bit" }
        val frames=dataLen/(2*channels); val out=FloatArray(frames)
        for(i in 0 until frames){ var sum=0f; for(c in 0 until channels){ val k=data+(i*channels+c)*2; val v=((b[k].toInt() and 255) or (b[k+1].toInt() shl 8)).toShort(); sum += v/32768f }; out[i]=sum/channels }
        return if(sr==16000) WavData(out,sr) else WavData(resample(out,sr,16000),16000)
    }
    private fun resample(x:FloatArray, from:Int,to:Int):FloatArray { val n=(x.size.toLong()*to/from).toInt(); return FloatArray(n){i-> val pos=i.toDouble()*from/to; val a=pos.toInt().coerceAtMost(x.lastIndex); val z=(a+1).coerceAtMost(x.lastIndex); val t=(pos-a).toFloat(); x[a]*(1-t)+x[z]*t } }
    fun melSpectrogram(x:FloatArray, sr:Int=16000):Array<FloatArray>{
        val nFft=800; val hop=200; val win=800; val bins=nFft/2+1; val frames=max(1,1+(x.size-win)/hop)
        val mel=Array(80){FloatArray(frames)}; val filters=melFilters(80,bins,sr,nFft)
        val cosT=Array(bins){k->FloatArray(nFft){n->cos(2.0*PI*k*n/nFft).toFloat()}}; val sinT=Array(bins){k->FloatArray(nFft){n->sin(2.0*PI*k*n/nFft).toFloat()}}
        val hann=FloatArray(win){n->(0.5-0.5*cos(2.0*PI*n/(win-1))).toFloat()}
        for(t in 0 until frames){ val off=t*hop; val power=FloatArray(bins); for(k in 0 until bins){var re=0f;var im=0f;for(n in 0 until win){val v=x.getOrElse(off+n){0f}*hann[n];re+=v*cosT[k][n];im-=v*sinT[k][n]};power[k]=re*re+im*im}; for(m in 0 until 80){var s=0f;for(k in 0 until bins)s+=power[k]*filters[m][k]; mel[m][t]=(ln(max(1e-10f,s).toDouble())/ln(10.0)).toFloat()} }
        var mx=-1e9f; for(r in mel) for(v in r) if(v>mx)mx=v; for(r in mel) for(i in r.indices) r[i]=max(mx-8f,r[i]); return mel
    }
    private fun melFilters(m: Int, bins: Int, sr: Int, nfft: Int): Array<FloatArray> {
        val lo = 2595.0 * log10(1.0 + 55.0 / 700.0)
        val hi = 2595.0 * log10(1.0 + 7600.0 / 700.0)
        val pts = DoubleArray(m + 2) {
            val mel = lo + (hi - lo) * it / (m + 1)
            700.0 * (10.0.pow(mel / 2595.0) - 1.0)
        }
        val idx = IntArray(m + 2) {
            floor((nfft + 1) * pts[it] / sr).toInt().coerceIn(0, bins - 1)
        }
        return Array(m) { j ->
            FloatArray(bins) { k ->
                when {
                    k < idx[j] || k > idx[j + 2] -> 0f
                    k <= idx[j + 1] ->
                        (k - idx[j]).toFloat() / max(1, idx[j + 1] - idx[j])
                    else ->
                        (idx[j + 2] - k).toFloat() / max(1, idx[j + 2] - idx[j + 1])
                }
            }
        }
    }
    private fun le16(b:ByteArray,p:Int)=(b[p].toInt() and 255) or ((b[p+1].toInt() and 255) shl 8)
    private fun le32(b:ByteArray,p:Int)=le16(b,p) or (le16(b,p+2) shl 16)
}
