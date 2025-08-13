# Java backend Dockerfile - Development friendly
FROM gradle:8.5-jdk17

# Set working directory
WORKDIR /app

# Copy gradle files
COPY build.gradle.kts settings.gradle.kts ./
COPY gradle gradle

# Copy source code
COPY src src

# Expose port
EXPOSE 8080

# Build and run the application
CMD ["gradle", "bootRun", "--no-daemon"]