package com.dorama.avatar

import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import ai.onnxruntime.OrtEnvironment

class MainActivity : AppCompatActivity() {
    private var imageUri: Uri? = null
    private var audioUri: Uri? = null
    private lateinit var status: TextView
    private lateinit var preview: ImageView

    private val imagePicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let { imageUri = it; preview.setImageURI(it); status.text = "✓ Изображение: ${name(it)}" }
    }
    private val audioPicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let { audioUri = it; status.text = "✓ WAV: ${name(it)}\nТеперь нажми «Проверить телефон и файлы»." }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState); setContentView(R.layout.activity_main)
        status = findViewById(R.id.status); preview = findViewById(R.id.preview)
        findViewById<Button>(R.id.imageButton).setOnClickListener { imagePicker.launch(arrayOf("image/png","image/jpeg")) }
        findViewById<Button>(R.id.audioButton).setOnClickListener { audioPicker.launch(arrayOf("audio/wav","audio/x-wav","audio/*")) }
        findViewById<Button>(R.id.testButton).setOnClickListener { runTest() }
    }

    private fun runTest() {
        if (imageUri == null || audioUri == null) { status.text = "Сначала выбери картинку и WAV."; return }
        try {
            val env = OrtEnvironment.getEnvironment()
            val imgBytes = contentResolver.openInputStream(imageUri!!)?.use { it.available() } ?: 0
            val wavBytes = contentResolver.openInputStream(audioUri!!)?.use { it.available() } ?: 0
            status.text = "✓ Android: ${android.os.Build.VERSION.RELEASE}\n✓ Устройство: ${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}\n✓ ONNX Runtime запущен: ${env.version}\n✓ Изображение читается (~${imgBytes/1024} KB)\n✓ WAV читается (~${wavBytes/1024} KB)\n\nЭтап V0.1 пройден. Пришли этот экран — подключим Wav2Lip-модель и рендер MP4."
        } catch (e: Exception) { status.text = "Ошибка теста: ${e.message}" }
    }

    private fun name(uri: Uri): String {
        contentResolver.query(uri, null, null, null, null)?.use { c -> val i=c.getColumnIndex(OpenableColumns.DISPLAY_NAME); if(c.moveToFirst() && i>=0) return c.getString(i) }
        return uri.lastPathSegment ?: "file"
    }
}
