# Multi-stage build for Java backend
FROM gradle:8.14-jdk21 AS builder

# Cache-bust the cert-injection layers based on cert content. The build script
# computes SHA256 of ~/zscaler-ca.pem and passes it as --build-arg
# EXTRA_CA_FINGERPRINT=<sha> (or "none" when no cert is present). Declaring the
# ARG IMMEDIATELY before the COPY/keytool steps means any change to the cert
# content invalidates the cache for those steps and they re-run.
ARG EXTRA_CA_FINGERPRINT=none

# Optionally trust extra CA for corporate proxy (file injected by build script)
COPY extra-ca.pe[m] /tmp/
RUN if [ -s /tmp/extra-ca.pem ]; then \
      keytool -importcert -noprompt -cacerts -storepass changeit -alias extra-ca -file /tmp/extra-ca.pem && \
      keytool -list -cacerts -storepass changeit -alias extra-ca > /dev/null && \
      echo "extra-ca successfully imported into builder JDK cacerts (fingerprint=${EXTRA_CA_FINGERPRINT})" && \
      rm /tmp/extra-ca.pem; \
    elif [ "${EXTRA_CA_FINGERPRINT}" != "none" ]; then \
      echo "FATAL: EXTRA_CA_FINGERPRINT=${EXTRA_CA_FINGERPRINT} but /tmp/extra-ca.pem is non-empty/missing in build context" >&2; \
      exit 1; \
    else \
      rm -f /tmp/extra-ca.pem; \
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
FROM eclipse-temurin:21-jre-noble

# Same cache-busting ARG for the runtime stage cert injection (Finnhub API calls
# at runtime require trust of the corporate CA when behind Zscaler).
ARG EXTRA_CA_FINGERPRINT=none

# Optionally trust extra CA for corporate proxy at runtime (Finnhub API calls)
COPY extra-ca.pe[m] /tmp/
RUN apt-get update && apt-get install -y curl ca-certificates && \
    if [ -s /tmp/extra-ca.pem ]; then \
      cp /tmp/extra-ca.pem /usr/local/share/ca-certificates/extra-ca.crt && \
      update-ca-certificates && \
      test -L /etc/ssl/certs/extra-ca.pem && \
      keytool -importcert -noprompt -cacerts -storepass changeit -alias extra-ca -file /tmp/extra-ca.pem && \
      keytool -list -cacerts -storepass changeit -alias extra-ca > /dev/null && \
      echo "extra-ca successfully imported into runtime JRE cacerts + system trust (fingerprint=${EXTRA_CA_FINGERPRINT})" && \
      rm /tmp/extra-ca.pem; \
    elif [ "${EXTRA_CA_FINGERPRINT}" != "none" ]; then \
      echo "FATAL: EXTRA_CA_FINGERPRINT=${EXTRA_CA_FINGERPRINT} but /tmp/extra-ca.pem is non-empty/missing in build context" >&2; \
      exit 1; \
    else \
      rm -f /tmp/extra-ca.pem; \
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
