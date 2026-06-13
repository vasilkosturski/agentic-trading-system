package com.trading.entity;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Properties;
import org.hibernate.boot.Metadata;
import org.hibernate.boot.MetadataSources;
import org.hibernate.boot.registry.StandardServiceRegistry;
import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.hibernate.cfg.AvailableSettings;
import org.hibernate.mapping.CheckConstraint;
import org.hibernate.mapping.Column;
import org.hibernate.mapping.PersistentClass;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class TradingRunPhaseCheckConstraintTest {

    private StandardServiceRegistry registry;
    private Metadata metadata;

    @BeforeAll
    void buildMetadata() {
        Properties props = new Properties();
        props.put(AvailableSettings.DIALECT, "org.hibernate.dialect.PostgreSQLDialect");

        registry = new StandardServiceRegistryBuilder().applySettings(props).build();

        metadata = new MetadataSources(registry)
                .addPackage("com.trading.entity")
                .addAnnotatedClass(ResearchPhase.class)
                .addAnnotatedClass(DecisionPhase.class)
                .addAnnotatedClass(ExecutionPhase.class)
                .addAnnotatedClass(TradingRun.class)
                .addAnnotatedClass(TradingAgent.class)
                .addAnnotatedClass(TradingAccount.class)
                .addAnnotatedClass(AccountHolding.class)
                .addAnnotatedClass(AccountTransaction.class)
                .addAnnotatedClass(AccountPortfolioSnapshot.class)
                .addAnnotatedClass(LogEntry.class)
                .addAnnotatedClass(PriceCache.class)
                .addAnnotatedClass(UsageMetrics.class)
                .buildMetadata();
    }

    @AfterAll
    void closeRegistry() {
        if (registry != null) {
            StandardServiceRegistryBuilder.destroy(registry);
        }
    }

    @Test
    void tradingRunPhaseColumnCarriesCheckConstraintListingFailed() {
        Column phase = findColumn(TradingRun.class, "phase");

        List<CheckConstraint> checks = phase.getCheckConstraints();
        assertThat(checks)
                .as("phase column should carry a Hibernate @Check constraint listing all RunPhase values")
                .isNotEmpty();

        String combined = checks.stream().map(CheckConstraint::getConstraint).reduce("", (a, b) -> a + " " + b);

        assertThat(combined).contains("FAILED");
        assertThat(combined).contains("INITIALIZING");
        assertThat(combined).contains("RESEARCHING");
        assertThat(combined).contains("DECIDING");
        assertThat(combined).contains("TRADING");
        assertThat(combined).contains("COMPLETED");
        assertThat(combined).contains("ERROR");
    }

    private Column findColumn(Class<?> entityClass, String columnName) {
        PersistentClass binding = metadata.getEntityBinding(entityClass.getName());
        return binding.getTable().getColumns().stream()
                .filter(c -> c.getName().equalsIgnoreCase(columnName))
                .findFirst()
                .orElseThrow(() ->
                        new AssertionError("Column " + columnName + " not found on " + entityClass.getSimpleName()));
    }
}
