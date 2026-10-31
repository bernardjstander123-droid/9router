plugins { id("com.android.application") }
android {
    namespace = "com.sceneforge.studio"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.sceneforge.studio"
        minSdk = 26
        targetSdk = 35
        versionCode = 14
        versionName = "0.14-debug"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildTypes {
        getByName("release") { isMinifyEnabled = false }
    }
}
