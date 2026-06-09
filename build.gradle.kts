/**
 * NOTE: This is entirely optional and basics can be done in `settings.gradle.kts`
 */

repositories {
    // Any external repositories besides: MavenLocal, MavenCentral, HytaleMaven, and CurseMaven
}

dependencies {
    implementation("org.graalvm.polyglot:polyglot:24.2.1")
    implementation("org.graalvm.polyglot:python-community:24.2.1")
}

tasks.register("extractPythonPluginClass") {
    dependsOn("jar")
    doLast {
        val pytaleJar = file("build/libs/pytale.jar")
        val resourceDir = file("pytale-tools/pytale_tools/resources")
        val outputFile = file("pytale-tools/pytale_tools/resources/PythonPlugin.class")

        if (!pytaleJar.exists()) {
            throw GradleException("pytale.jar not found at ${pytaleJar.absolutePath}")
        }

        resourceDir.mkdirs()

        project.zipTree(pytaleJar).matching {
            include("dev/taledale/pytale/PythonPlugin.class")
        }.forEach { file ->
            if (file.isFile) {
                file.copyTo(outputFile, overwrite = true)
                println("✓ Extracted PythonPlugin.class to ${outputFile.relativeTo(rootDir)}")
            }
        }

        if (!outputFile.exists()) {
            throw GradleException("Failed to extract PythonPlugin.class from pytale.jar")
        }
    }
}

tasks.named("jar") {
    finalizedBy("extractPythonPluginClass")
}
