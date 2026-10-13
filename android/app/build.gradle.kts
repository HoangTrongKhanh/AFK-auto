import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "vn.afkauto.leoai"
    compileSdk = 36

    defaultConfig {
        applicationId = "vn.afkauto.leoai"
        minSdk = 30             // AccessibilityService.takeScreenshot() cần Android 11
        targetSdk = 36
        versionCode = 13
        versionName = "1.3"
    }

    // Khóa ký bản phát hành nằm ngoài repo (android/keystore.properties trỏ tới file .jks). Không có thì bản release
    // ký tạm bằng khóa debug - chỉ để thử, không phát cho người dùng vì sau này không cài đè được.
    val keystoreFile = rootProject.file("keystore.properties")
    signingConfigs {
        if (keystoreFile.exists()) {
            create("phatHanh") {
                val p = Properties().apply { keystoreFile.inputStream().use { load(it) } }
                storeFile = file(p.getProperty("storeFile"))
                storePassword = p.getProperty("storePassword")
                keyAlias = p.getProperty("keyAlias")
                keyPassword = p.getProperty("keyPassword")
            }
        }
    }

    // Ảnh mẫu dùng chung với bản Python: đóng gói thẳng thư mục templates/ ở gốc dự án.
    sourceSets["main"].assets.srcDir("../../templates")

    buildTypes {
        debug {
            ndk { abiFilters += listOf("arm64-v8a", "x86_64") }     // máy thật + máy ảo
        }
        release {
            ndk { abiFilters += listOf("arm64-v8a") }               // điện thoại/máy tính bảng thật
            isMinifyEnabled = false
            signingConfig = signingConfigs.findByName("phatHanh") ?: signingConfigs.getByName("debug")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    packaging {
        jniLibs.useLegacyPackaging = false
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

// ./gradlew phatHanh: build bản release rồi chép ra thư mục gốc dự án thành AfkAuto-<phiên bản>.apk để gửi đi.
tasks.register("phatHanh") {
    dependsOn("assembleRelease")
    doLast {
        check(rootProject.file("keystore.properties").exists()) { "Thiếu android/keystore.properties (khóa ký bản phát hành)" }
        val apk = layout.buildDirectory.file("outputs/apk/release/app-release.apk").get().asFile
        val out = rootProject.projectDir.parentFile.resolve("AfkAuto-${android.defaultConfig.versionName}.apk")
        apk.copyTo(out, overwrite = true)
        println("Đã xuất ${out.path}")
    }
}

dependencies {
    implementation(project(":vision"))
    implementation("org.opencv:opencv:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
}
