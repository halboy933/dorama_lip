from pathlib import Path
import re
p=Path('app/src/main/java/com/dorama/avatar/MainActivity.kt')
s=p.read_text(encoding='utf-8')
if 'V139_EDTALK_ALIGNMENT' in s: raise SystemExit('V1.3.9 already applied')
anchor='    private fun cropInfo(b: Bitmap, r: Rect): FaceCrop {'
assert s.count(anchor)==1
block='''    // V139_EDTALK_ALIGNMENT: affine alignment using eyes and mouth landmarks.
    // Forward matrix maps full-image coordinates to 256x256 model coordinates.
    private data class EdtalkAligned(val bitmap: Bitmap, val forward: Matrix)

    private fun alignEdtalkFace(base: Bitmap): EdtalkAligned {
        val detector = FaceDetection.getClient(
            FaceDetectorOptions.Builder()
                .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_ACCURATE)
                .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_ALL)
                .build()
        )
        try {
            val task = detector.process(InputImage.fromBitmap(base, 0))
            while (!task.isComplete) Thread.sleep(20)
            if (!task.isSuccessful) throw task.exception ?: RuntimeException("EDTalk landmark detection failed")
            val face = (task.result ?: emptyList()).maxByOrNull {
                it.boundingBox.width() * it.boundingBox.height()
            } ?: throw RuntimeException("EDTalk: face not found")
            fun landmark(type: Int): PointF = face.getLandmark(type)?.position
                ?: throw RuntimeException("EDTalk: missing landmark $type")
            val left = landmark(com.google.mlkit.vision.face.FaceLandmark.LEFT_EYE)
            val right = landmark(com.google.mlkit.vision.face.FaceLandmark.RIGHT_EYE)
            val ml = landmark(com.google.mlkit.vision.face.FaceLandmark.MOUTH_LEFT)
            val mr = landmark(com.google.mlkit.vision.face.FaceLandmark.MOUTH_RIGHT)
            val mouthX = (ml.x + mr.x) / 2f
            val mouthY = (ml.y + mr.y) / 2f
            val source = floatArrayOf(left.x, left.y, right.x, right.y, mouthX, mouthY)
            val destination = floatArrayOf(82f, 96f, 174f, 96f, 128f, 174f)
            val forward = Matrix()
            check(forward.setPolyToPoly(source, 0, destination, 0, 3)) {
                "EDTalk: unable to align landmarks"
            }
            val aligned = Bitmap.createBitmap(256, 256, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(aligned)
            canvas.drawColor(Color.BLACK)
            canvas.drawBitmap(base, forward, Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG))
            return EdtalkAligned(aligned, forward)
        } finally {
            detector.close()
        }
    }

    // Map the generated aligned face back into the ORIGINAL face crop.
    // This preserves the existing manual ellipse and X/Y/rotation/scale compositor.
    private fun unalignEdtalkFace(generated: Bitmap, alignment: EdtalkAligned, crop: FaceCrop): Bitmap {
        val inverse = Matrix()
        check(alignment.forward.invert(inverse)) { "EDTalk: alignment matrix not invertible" }
        inverse.postTranslate(-crop.left.toFloat(), -crop.top.toFloat())
        val out = Bitmap.createBitmap(crop.width, crop.height, Bitmap.Config.ARGB_8888)
        Canvas(out).drawBitmap(generated, inverse, Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG))
        return out
    }

'''
s=s.replace(anchor,block+anchor)
needle='''                    val spec = WavUtils.edtalkSpectrogram(samples)
                    val targetInput = imageTensor256(crop.bitmap)'''
assert s.count(needle)==1
s=s.replace(needle,'''                    val spec = WavUtils.edtalkSpectrogram(samples)
                    val aligned = alignEdtalkFace(base)
                    savePng(aligned.bitmap, "V139_01_aligned_input.png")
                    val targetInput = imageTensor256(aligned.bitmap)''')
needle='''                        val composed = compositeMouth(
                            base, face, crop,
                            mouthOffsetXPercent,
                            mouthOffsetYPercent,
                            mouthAngleDeg,
                            mouthScalePercent
                        )'''
assert s.count(needle)==2
s=s.replace(needle,'''                        val mappedFace = unalignEdtalkFace(face, aligned, crop)
                        val composed = compositeMouth(
                            base, mappedFace, crop,
                            mouthOffsetXPercent,
                            mouthOffsetYPercent,
                            mouthAngleDeg,
                            mouthScalePercent
                        )''',1)
needle='''                            savePng(crop.bitmap, "V132_01_input_crop_${stamp}.png")
                            savePng(face, "V132_02_edtalk256_face_${stamp}.png")
                            savePng(composed, "V132_03_composite_before_encoder_${stamp}.png")'''
assert s.count(needle)==1
s=s.replace(needle,'''                            savePng(crop.bitmap, "V132_01_input_crop_${stamp}.png")
                            savePng(face, "V132_02_edtalk256_face_${stamp}.png")
                            savePng(mappedFace, "V139_02_inverse_mapped_${stamp}.png")
                            savePng(composed, "V132_03_composite_before_encoder_${stamp}.png")''')
needle='''                        rendered.add(composed)
                        face.recycle()'''
assert s.count(needle)==2
s=s.replace(needle,'''                        rendered.add(composed)
                        mappedFace.recycle()
                        face.recycle()''',1)
# No longer need alignment bitmap after EDTalk frames.
needle='''                } else {
                    val spec = WavUtils.melSpectrogram'''
if needle in s:
    s=s.replace(needle,'''                    aligned.bitmap.recycle()
                } else {
                    val spec = WavUtils.melSpectrogram''',1)
else:
    # keep aligned bitmap alive until function exits; harmless single 256x256 allocation
    pass
p.write_text(s,encoding='utf-8')
g=Path('app/build.gradle.kts')
t=g.read_text(encoding='utf-8')
t,n1=re.subn(r'versionCode\s*=\s*\d+','versionCode = 23',t,count=1)
t,n2=re.subn(r'versionName\s*=\s*"[^"]+"','versionName = "1.3.9"',t,count=1)
assert n1==n2==1
g.write_text(t,encoding='utf-8')
print('V1.3.9 patch applied; review git diff, build and test APK.')
