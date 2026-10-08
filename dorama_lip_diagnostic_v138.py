from pathlib import Path
import sys
p=Path('app/src/main/java/com/dorama/avatar/MainActivity.kt')
if not p.exists():
    sys.exit('ERROR: run from repository root')
s=p.read_text(encoding='utf-8')
if 'V138_FACE_LANDMARK_DIAGNOSTIC' in s:
    sys.exit('Already installed')
needle='    private fun cropInfo(b: Bitmap, r: Rect): FaceCrop {'
assert s.count(needle)==1, 'Unexpected source layout'
insert='''    // V138_FACE_LANDMARK_DIAGNOSTIC: diagnostics only; does not modify inference.
    private fun saveFaceLandmarkDiagnostic(base: Bitmap) {
        val detector = FaceDetection.getClient(
            FaceDetectorOptions.Builder()
                .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_ACCURATE)
                .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_ALL)
                .build()
        )
        try {
            val task = detector.process(InputImage.fromBitmap(base, 0))
            while (!task.isComplete) Thread.sleep(20)
            if (!task.isSuccessful) throw task.exception ?: RuntimeException("Landmark detection failed")
            val face = (task.result ?: emptyList()).maxByOrNull {
                it.boundingBox.width() * it.boundingBox.height()
            } ?: return
            val out = base.copy(Bitmap.Config.ARGB_8888, true)
            val canvas = Canvas(out)
            val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = Color.GREEN
                style = Paint.Style.STROKE
                strokeWidth = 3f
            }
            val label = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = Color.YELLOW
                textSize = 22f
                strokeWidth = 2f
            }
            val points = listOf(
                com.google.mlkit.vision.face.FaceLandmark.LEFT_EYE to "L eye",
                com.google.mlkit.vision.face.FaceLandmark.RIGHT_EYE to "R eye",
                com.google.mlkit.vision.face.FaceLandmark.NOSE_BASE to "Nose",
                com.google.mlkit.vision.face.FaceLandmark.MOUTH_LEFT to "L mouth",
                com.google.mlkit.vision.face.FaceLandmark.MOUTH_RIGHT to "R mouth"
            )
            for ((type, name) in points) {
                val pt = face.getLandmark(type)?.position ?: continue
                canvas.drawCircle(pt.x, pt.y, 7f, paint)
                canvas.drawText(name, pt.x + 9f, pt.y - 8f, label)
            }
            val rect = face.boundingBox
            canvas.drawRect(rect, paint)
            savePng(out, "V138_04_landmarks_original.png")
            out.recycle()
        } finally {
            detector.close()
        }
    }

'''
s=s.replace(needle,insert+needle)
needle2='                val crop = cropInfo(base, rect)'
assert s.count(needle2)==1
s=s.replace(needle2,needle2+'''
                if (engineAtStart == "edtalk256") {
                    try { saveFaceLandmarkDiagnostic(base) }
                    catch (e: Exception) { android.util.Log.w("DoramaAvatar", "Landmark diagnostic failed", e) }
                }
''')
p.write_text(s,encoding='utf-8')
print('V1.3.8 diagnostic patch applied')
