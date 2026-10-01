package com.dorama.avatar

import ai.onnxruntime.*
import android.graphics.*
import android.net.Uri
import android.os.Bundle
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

class MainActivity:AppCompatActivity(){
 private var imageUri:Uri?=null; private var audioUri:Uri?=null; private lateinit var status:TextView; private lateinit var preview:ImageView; private lateinit var progress:ProgressBar
 private val imagePicker=registerForActivityResult(ActivityResultContracts.OpenDocument()){u->u?.let{imageUri=it;preview.setImageURI(it);status.text="✓ Картинка: ${name(it)}"}}
 private val audioPicker=registerForActivityResult(ActivityResultContracts.OpenDocument()){u->u?.let{audioUri=it;status.text="✓ WAV: ${name(it)}"}}
 override fun onCreate(b:Bundle?){super.onCreate(b);setContentView(R.layout.activity_main);status=findViewById(R.id.status);preview=findViewById(R.id.preview);progress=findViewById(R.id.progress)
  findViewById<Button>(R.id.imageButton).setOnClickListener{imagePicker.launch(arrayOf("image/*"))}; findViewById<Button>(R.id.audioButton).setOnClickListener{audioPicker.launch(arrayOf("audio/*"))}; findViewById<Button>(R.id.modelButton).setOnClickListener{downloadModel()}; findViewById<Button>(R.id.generateButton).setOnClickListener{runInferenceTest()}
 }
 private fun modelFile()=File(filesDir,"wav2lip.onnx")
 private fun downloadModel(){thread{try{runOnUiThread{status.text="Скачиваю Wav2Lip ONNX (~145 МБ)…";progress.progress=0}; val con=URL("https://huggingface.co/bluefoxcreation/Wav2lip-Onnx/resolve/main/wav2lip.onnx?download=true").openConnection(); val total=con.contentLengthLong; con.getInputStream().use{i->modelFile().outputStream().use{o->val buf=ByteArray(1024*256);var n:Int;var done=0L;while(i.read(buf).also{n=it}>0){o.write(buf,0,n);done+=n;if(total>0)runOnUiThread{progress.progress=(done*100/total).toInt()}}}};runOnUiThread{status.text="✓ Модель скачана: ${modelFile().length()/1024/1024} МБ"}}catch(e:Exception){runOnUiThread{status.text="Ошибка загрузки модели: ${e.message}"}}}}
 private fun runInferenceTest(){if(imageUri==null||audioUri==null){status.text="Сначала выбери картинку и WAV.";return};if(!modelFile().exists()){status.text="Сначала скачай модель кнопкой 3.";return};thread{try{val start=System.currentTimeMillis();runOnUiThread{status.text="Ищу лицо…";progress.progress=2};val bmp=contentResolver.openInputStream(imageUri!!)!!.use{BitmapFactory.decodeStream(it)};val rect=detectFace(bmp);runOnUiThread{status.text="✓ Лицо найдено. Готовлю WAV/mel…";progress.progress=5};val wav=contentResolver.openInputStream(audioUri!!)!!.use{WavUtils.readPcm16(it)};val mel=WavUtils.melSpectrogram(wav.samples);val env=OrtEnvironment.getEnvironment();val opts=OrtSession.SessionOptions();val session=env.createSession(modelFile().absolutePath,opts);val names=session.inputNames.toList();val melName=names.firstOrNull{it.contains("mel",true)}?:names[0];val imgName=names.firstOrNull{it.contains("video",true)||it.contains("frame",true)||it.contains("img",true)}?:names.last();val crop=squareCrop(bmp,rect);val imgTensor=makeImageTensor(crop);val maxFrames=min(125,max(1,((wav.samples.size/16000f)*25).toInt()));var done=0;for(f in 0 until maxFrames){val mi=(f*80.0/25.0).toInt().coerceAtMost(max(0,mel[0].size-16));val mf=FloatArray(80*16);for(y in 0 until 80)for(x in 0 until 16)mf[y*16+x]=mel[y][(mi+x).coerceAtMost(mel[y].lastIndex)];OnnxTensor.createTensor(env,FloatBuffer.wrap(mf),longArrayOf(1,1,80,16)).use{mt->OnnxTensor.createTensor(env,FloatBuffer.wrap(imgTensor),longArrayOf(1,6,96,96)).use{itn->session.run(mapOf(melName to mt,imgName to itn)).use{r->r[0].value}}};done++;if(f%3==0)runOnUiThread{progress.progress=5+(done*95/maxFrames);status.text="Wav2Lip inference: $done/$maxFrames кадров…"}}
 };val sec=(System.currentTimeMillis()-start)/1000.0;runOnUiThread{progress.progress=100;status.text="✓ V0.2 ПРОЙДЕНА\n✓ Реальная Wav2Lip ONNX-модель запущена\n✓ Лицо найдено\n✓ WAV → mel готов\n✓ Обработано $done кадров (~${"%.1f".format(done/25.0)} сек видео)\n⏱ Время на телефоне: ${"%.1f".format(sec)} сек\n\nПришли этот экран. Следующий шаг — V0.3: вставка сгенерированного рта в кадры + запись MP4."}}catch(e:Throwable){runOnUiThread{status.text="Ошибка V0.2: ${e.javaClass.simpleName}: ${e.message}"}}}}
 private fun detectFace(b:Bitmap):android.graphics.Rect{val opt=FaceDetectorOptions.Builder().setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_ACCURATE).build();val det=FaceDetection.getClient(opt);val task=det.process(InputImage.fromBitmap(b,0));while(!task.isComplete)Thread.sleep(20);if(!task.isSuccessful)throw task.exception?:RuntimeException("Face detector");val faces=task.result?:emptyList();if(faces.isEmpty())throw RuntimeException("Лицо не найдено");return faces.maxBy{it.boundingBox.width()*it.boundingBox.height()}.boundingBox}
 private fun squareCrop(b:Bitmap,r:android.graphics.Rect):Bitmap{val cx=(r.left+r.right)/2;val cy=(r.top+r.bottom)/2;val s=(max(r.width(),r.height())*1.5).toInt().coerceAtMost(min(b.width,b.height));val l=(cx-s/2).coerceIn(0,b.width-s);val t=(cy-s/2).coerceIn(0,b.height-s);return Bitmap.createScaledBitmap(Bitmap.createBitmap(b,l,t,s,s),96,96,true)}
 private fun makeImageTensor(b:Bitmap):FloatArray{val pix=IntArray(96*96);b.getPixels(pix,0,96,0,0,96,96);val out=FloatArray(6*96*96);for(y in 0 until 96)for(x in 0 until 96){val p=pix[y*96+x];val rgb=floatArrayOf(Color.red(p)/255f,Color.green(p)/255f,Color.blue(p)/255f);for(c in 0..2){val v=rgb[c];out[c*96*96+y*96+x]=if(y<48)0f else v;out[(c+3)*96*96+y*96+x]=v}};return out}
 private fun name(u:Uri):String{contentResolver.query(u,null,null,null,null)?.use{c->val i=c.getColumnIndex(OpenableColumns.DISPLAY_NAME);if(c.moveToFirst()&&i>=0)return c.getString(i)};return u.lastPathSegment?:"file"}
}
