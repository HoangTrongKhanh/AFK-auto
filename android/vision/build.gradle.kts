// Nhận diện màn hình game bằng OpenCV, viết thuần Kotlin/JVM để kiểm thử được trên máy tính.
// Trong app, các lớp org.opencv.* và org.json.* lấy từ OpenCV cho Android và từ Android; ở đây chỉ dùng bản máy tính
// (org.openpnp:opencv cùng API, org.json) để biên dịch và chạy kiểm thử.
plugins {
    id("org.jetbrains.kotlin.jvm")
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    compileOnly("org.openpnp:opencv:4.9.0-0")
    compileOnly("org.json:json:20240303")
    testImplementation("org.openpnp:opencv:4.9.0-0")
    testImplementation("org.json:json:20240303")
    testImplementation(kotlin("test"))
}

tasks.test {
    useJUnitPlatform()
    systemProperty("afkauto.root", rootDir.parentFile.absolutePath)    // thư mục chứa templates/ và samples/
    testLogging {
        events("passed", "failed")
        showStandardStreams = true
    }
}
