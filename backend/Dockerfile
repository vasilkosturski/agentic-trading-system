# Multi-stage build for Java backend
FROM gradle:8.5-jdk17 AS builder

# Optionally trust extra CA for corporate proxy (file injected by build script)
COPY extra-ca.pe[m] /tmp/
RUN if [ -f /tmp/extra-ca.pem ]; then \
      keytool -importcert -noprompt -cacerts -storepass changeit -alias extra-ca -file /tmp/extra-ca.pem && \
      rm /tmp/extra-ca.pem; \
    fi

# Set working directory
WORKDIR /app

# Copy gradle files
COPY build.gradle.kts settings.gradle.kts ./
COPY gradle gradle
COPY gradlew ./

# Make gradlew executable
RUN chmod +x gradlew

# Copy source code
COPY src src

# Build the application
RUN ./gradlew bootJar --no-daemon

# Runtime stage
FROM eclipse-temurin:17-jre

# Optionally trust extra CA for corporate proxy at runtime (Finnhub API calls)
COPY extra-ca.pe[m] /tmp/
RUN apt-get update && apt-get install -y curl ca-certificates && \
    if [ -f /tmp/extra-ca.pem ]; then \
      cp /tmp/extra-ca.pem /usr/local/share/ca-certificates/extra-ca.crt && \
      update-ca-certificates && \
      keytool -importcert -noprompt -cacerts -storepass changeit -alias extra-ca -file /tmp/extra-ca.pem && \
      rm /tmp/extra-ca.pem; \
    fi && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the built JAR from builder stage
COPY --from=builder /app/build/libs/*.jar app.jar

# Expose port
EXPOSE 8080

# Run the application
CMD ["java", "-jar", "app.jar"]