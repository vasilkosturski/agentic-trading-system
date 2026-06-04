package com.trading.testsupport;

import org.springframework.test.context.DynamicPropertyRegistry;
import org.testcontainers.containers.PostgreSQLContainer;

/**
 * JVM-wide singleton PostgreSQL container shared across all integration tests.
 *
 * Each integration test class registering its own static {@link PostgreSQLContainer}
 * leaves multiple containers + Hikari pools alive in the same test JVM. At shutdown
 * each pool fires a 20s connection-validation timeout against postgres containers
 * Ryuk has already killed, which can starve Gradle's XML test reporter and produce
 * spurious build failures. One container, one shutdown.
 */
public final class SharedPostgresContainer {

    private static final PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>("postgres:15-alpine")
            .withDatabaseName("test_trading")
            .withUsername("test")
            .withPassword("test")
            .withReuse(true);

    static {
        POSTGRES.start();
    }

    private SharedPostgresContainer() {}

    public static void register(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
        registry.add("spring.jpa.hibernate.ddl-auto", () -> "create-drop");
        registry.add("spring.jpa.properties.hibernate.hbm2ddl.create_namespaces", () -> "true");
    }
}
