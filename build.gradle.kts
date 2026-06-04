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
