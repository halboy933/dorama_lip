plugins {
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
        versionCode = 17
        versionName = "1.3.4"
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
