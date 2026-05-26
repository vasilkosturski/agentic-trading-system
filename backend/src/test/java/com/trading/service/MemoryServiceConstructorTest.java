package com.trading.service;

import com.trading.repository.AccountTransactionRepository;
import com.trading.repository.TradingAccountRepository;
import com.trading.repository.TradingAgentRepository;
import com.trading.repository.TradingRunRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

@DisplayName("MemoryService constructor injection tests")
class MemoryServiceConstructorTest {

    @Test
    @DisplayName("MemoryService instantiates without a Spring context")
    void canInstantiateWithoutSpring() {
        MemoryService memoryService = new MemoryService(
            7,
            mock(AccountTransactionRepository.class),
            mock(TradingRunRepository.class),
            mock(TradingAgentRepository.class),
            mock(TradingAccountRepository.class),
            mock(AccountService.class)
        );
        assertThat(memoryService).isNotNull();
    }
}
