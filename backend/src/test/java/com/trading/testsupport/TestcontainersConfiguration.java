package com.trading.testsupport;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.context.annotation.Bean;
import org.testcontainers.containers.PostgreSQLContainer;

/**
 * Spring-managed PostgreSQL container for integration tests.
 *
 * <p>The container is a Spring bean annotated with {@link ServiceConnection}, so Spring
 * owns its lifecycle: it starts the container before the context and — because the
 * {@code DataSource} depends on the container's connection details — destroys the
 * {@code DataSource} (closing the Hikari pool) <em>before</em> stopping the container.
 * That ordering is what eliminates the shutdown race the old static-singleton +
 * {@code @DynamicPropertySource} setup suffered: there, the container was reaped by Ryuk
 * independently of Spring's context close, so pools fired 20s connection-timeouts against
 * an already-dead database at JVM shutdown.
 *
 * <p>{@code @ServiceConnection} auto-configures {@code spring.datasource.url/username/password}
 * from the running container. Schema creation (three schemas + tables) is handled by the
 * active {@code postgresql} profile's {@code ddl-auto: update} +
 * {@code hbm2ddl.create_namespaces: true} against the fresh container.
 *
 * <p>Test classes activate this by adding {@code @Import(TestcontainersConfiguration.class)}.
 * Spring's context cache shares one container across test classes with identical context
 * configuration.
 */
@TestConfiguration(proxyBeanMethods = false)
public class TestcontainersConfiguration {

    @Bean
    @ServiceConnection
    @SuppressWarnings("resource") // lifecycle owned by Spring — closed on context shutdown
    PostgreSQLContainer<?> postgresContainer() {
        return new PostgreSQLContainer<>("postgres:15-alpine")
                .withDatabaseName("test_trading")
                .withUsername("test")
                .withPassword("test");
    }
}
