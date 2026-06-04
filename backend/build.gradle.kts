plugins {
    id("org.springframework.boot") version "3.5.14"
    id("io.spring.dependency-management") version "1.1.7"
    id("com.diffplug.spotless") version "6.25.0"
    checkstyle
    java
}

group = "com.trading"
version = "0.0.1-SNAPSHOT"

java {
    sourceCompatibility = JavaVersion.VERSION_21
}

repositories {
    mavenCentral()
    maven { url = uri("https://jitpack.io") }
}

dependencies {
    // Lombok
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")
    
    // Spring Boot starters
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-security")

    // JWT support
    // Bumped 0.12.3 -> 0.13.0: drop-in API; fixes JPMS module-info quirk on JDK 17+ (we're on JDK 21)
    // and a decompression memory leak in concurrent envs. No 0.14.x release yet (next minor will baseline Java 8+).
    implementation("io.jsonwebtoken:jjwt-api:0.13.0")
    runtimeOnly("io.jsonwebtoken:jjwt-impl:0.13.0")
    runtimeOnly("io.jsonwebtoken:jjwt-jackson:0.13.0")
    
    // Database
    implementation("org.xerial:sqlite-jdbc:3.44.1.0")
    implementation("org.postgresql:postgresql:42.7.1")
    implementation("org.hibernate.orm:hibernate-community-dialects:6.3.1.Final")
    
    // JSONB support for Hibernate (for trading runs phase tables).
    // NOTE: The hypersistence-utils-hibernate-63 artifact supports Hibernate ORM 6.3-6.6
    // (no separate "-66" artifact exists; series jumps to -71/-72/-73 for Hibernate 7.x).
    // Bumped from 3.7.0 to 3.15.2 (latest 3.x) for Spring Boot 3.5 / Hibernate 6.6 compatibility.
    implementation("io.hypersistence:hypersistence-utils-hibernate-63:3.15.2")
    
    // JSON processing
    implementation("com.fasterxml.jackson.core:jackson-databind")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310")
    
    // OpenAI integration
    implementation("com.theokanning.openai-gpt3-java:service:0.18.2")
    
    // HTTP client
    implementation("org.springframework.boot:spring-boot-starter-webflux")

    // Retry with exponential backoff for external API calls
    implementation("org.springframework.retry:spring-retry")
    implementation("org.springframework:spring-aspects")
    
    // Logging
    implementation("ch.qos.logback:logback-classic")
    
    // Testing
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.security:spring-security-test")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
    
    // Testcontainers for real PostgreSQL testing
    testImplementation("org.testcontainers:testcontainers:1.19.3")
    testImplementation("org.testcontainers:postgresql:1.19.3")
    testImplementation("org.testcontainers:junit-jupiter:1.19.3")
}

tasks.withType<Test> {
    useJUnitPlatform()
}

spotless {
    java {
        target("src/**/*.java")
        palantirJavaFormat("2.50.0")
        removeUnusedImports()
        trimTrailingWhitespace()
        endWithNewline()
    }
}

checkstyle {
    toolVersion = "10.17.0"
    configFile = file("config/checkstyle/checkstyle.xml")
    isIgnoreFailures = false
    maxWarnings = 0
}

tasks.withType<Checkstyle>().configureEach {
    reports {
        xml.required.set(false)
        html.required.set(true)
    }
}

tasks.withType<JavaCompile>().configureEach {
    options.compilerArgs.add("-Xlint:all")
}
