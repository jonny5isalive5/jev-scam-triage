plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.sentovara.scamcheck"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.sentovara.scamcheck"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    // The shared rules file (Jev questions, domain lists, regexes, golden cases) lives at the
    // repo root in spec/ and is written by `python -m scam_triage.spec`. It is bundled as an asset.
    sourceSets["main"].assets.srcDirs("../../spec")
    // The golden-case checker runs both on the JVM (test/) and on a device (androidTest/).
    sourceSets["test"].java.srcDirs("src/sharedTest/java")
    sourceSets["androidTest"].java.srcDirs("src/sharedTest/java")

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    testOptions {
        unitTests.isReturnDefaultValues = true
    }
}

dependencies {
    // Local JVM unit tests don't get Android's org.json implementation; use the real one.
    testImplementation("org.json:json:20240303")
    testImplementation("junit:junit:4.13.2")

    // On-emulator tests (androidTest/), run in CI by ci/emulator-smoke.sh.
    androidTestImplementation("androidx.test:core:1.6.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
