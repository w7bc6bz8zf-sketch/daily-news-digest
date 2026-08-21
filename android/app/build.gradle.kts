plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
}

android {
    namespace = "com.prizma.news"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.prizma.news"
        minSdk = 26
        targetSdk = 34
        versionCode = 2
        versionName = "1.2"
    }

    // Ключ лежит в репозитории специально: приложение распространяется APK-файлом,
    // стабильная подпись нужна, чтобы обновления ставились поверх без удаления.
    signingConfigs {
        create("release") {
            storeFile = file("../keystore/prizma.p12")
            storeType = "pkcs12"
            storePassword = "prizma-news"
            keyAlias = "prizma"
            keyPassword = "prizma-news"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("release")
        }
    }

    buildFeatures { compose = true }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.06.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    // M2 — только ради стабильного pullRefresh (в M3 1.2 он экспериментальный и глючный)
    implementation("androidx.compose.material:material")
    implementation("androidx.activity:activity-compose:1.9.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.3")
    implementation("io.coil-kt:coil-compose:2.6.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")
    implementation("org.jsoup:jsoup:1.17.2")
}
