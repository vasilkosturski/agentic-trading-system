# Java backend Dockerfile - Development friendly
FROM gradle:8.5-jdk17

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

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

# Expose port
EXPOSE 8080

# Build and run the application
CMD ["./gradlew", "bootRun", "--no-daemon"]