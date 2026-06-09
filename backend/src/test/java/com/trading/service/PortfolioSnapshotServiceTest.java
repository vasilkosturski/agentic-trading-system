package com.trading.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.trading.config.AgentProperties;
import com.trading.entity.AccountHolding;
import com.trading.entity.AccountPortfolioSnapshot;
import com.trading.entity.TradingAccount;
import com.trading.entity.TradingAgent;
import com.trading.exception.ResourceNotFoundException;
import com.trading.repository.AccountHoldingRepository;
import com.trading.repository.AccountPortfolioSnapshotRepository;
import com.trading.repository.TradingAccountRepository;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
@DisplayName("PortfolioSnapshotService Tests")
class PortfolioSnapshotServiceTest {

    @Mock
    private TradingAccountRepository tradingAccountRepository;

    @Mock
    private AccountHoldingRepository holdingRepository;

    @Mock
    private AccountPortfolioSnapshotRepository snapshotRepository;

    @Mock
    private HoldingsValuationService holdingsValuationService;

    @Mock
    private AgentProperties agentProperties;

    @InjectMocks
    private PortfolioSnapshotService portfolioSnapshotService;

    @Test
    @DisplayName(
            "createSnapshot — empty holdings + no previous snapshot → totalValue=balance, holdingsValue=0, metrics null")
    void createSnapshot_EmptyHoldingsNoPrevious_PersistsBaseSnapshotWithoutMetrics() {
        TradingAccount account = newAccount("warren", 100_000.0);
        when(tradingAccountRepository.findByAgentName("warren")).thenReturn(Optional.of(account));
        when(holdingRepository.findByAccount(account)).thenReturn(List.of());
        when(holdingsValuationService.calculateHoldingsValue(List.of())).thenReturn(0.0);
        when(snapshotRepository.findTopByAccountOrderByTimestampDesc(account)).thenReturn(null);

        portfolioSnapshotService.createSnapshot("warren");

        ArgumentCaptor<AccountPortfolioSnapshot> captor = ArgumentCaptor.forClass(AccountPortfolioSnapshot.class);
        verify(snapshotRepository).save(captor.capture());

        AccountPortfolioSnapshot saved = captor.getValue();
        assertThat(saved.getAccount()).isSameAs(account);
        assertThat(saved.getCashBalance()).isEqualTo(100_000.0);
        assertThat(saved.getHoldingsValue()).isEqualTo(0.0);
        assertThat(saved.getTotalValue()).isEqualTo(100_000.0);
        assertThat(saved.getTimestamp()).isNotNull();
        // calculateMetrics never called (no previous snapshot) → PnL fields stay null
        assertThat(saved.getTotalPnl()).isNull();
        assertThat(saved.getTotalReturnPercent()).isNull();
        assertThat(saved.getDailyPnl()).isNull();

        // No previous snapshot → no initial-capital lookup
        verifyNoInteractions(agentProperties);
    }

    @Test
    @DisplayName("createSnapshot — populated holdings + previous snapshot → metrics computed against initialCapital")
    void createSnapshot_PopulatedHoldingsWithPrevious_ComputesMetrics() {
        TradingAccount account = newAccount("warren", 50_000.0);
        AccountHolding holding = new AccountHolding(account, "AAPL", 10, 150.0);
        List<AccountHolding> holdings = List.of(holding);

        AccountPortfolioSnapshot previous = new AccountPortfolioSnapshot();
        previous.setTotalValue(120_000.0);

        when(tradingAccountRepository.findByAgentName("warren")).thenReturn(Optional.of(account));
        when(holdingRepository.findByAccount(account)).thenReturn(holdings);
        when(holdingsValuationService.calculateHoldingsValue(anyList())).thenReturn(60_000.0);
        when(snapshotRepository.findTopByAccountOrderByTimestampDesc(account)).thenReturn(previous);
        when(agentProperties.getInitialCapital("warren")).thenReturn(100_000.0);

        portfolioSnapshotService.createSnapshot("warren");

        ArgumentCaptor<AccountPortfolioSnapshot> captor = ArgumentCaptor.forClass(AccountPortfolioSnapshot.class);
        verify(snapshotRepository).save(captor.capture());

        AccountPortfolioSnapshot saved = captor.getValue();
        // totalValue = balance(50_000) + holdingsValue(60_000) = 110_000
        assertThat(saved.getTotalValue()).isEqualTo(110_000.0);
        assertThat(saved.getCashBalance()).isEqualTo(50_000.0);
        assertThat(saved.getHoldingsValue()).isEqualTo(60_000.0);

        // calculateMetrics(100_000, 120_000) → totalPnl = 110_000 - 100_000 = 10_000;
        // totalReturnPercent = (10_000/100_000)*100 = 10.0; dailyPnl = 110_000 - 120_000 = -10_000.
        assertThat(saved.getTotalPnl()).isEqualTo(10_000.0);
        assertThat(saved.getTotalReturnPercent()).isEqualTo(10.0);
        assertThat(saved.getDailyPnl()).isEqualTo(-10_000.0);

        verify(agentProperties).getInitialCapital("warren");
    }

    @Test
    @DisplayName("createSnapshot — unknown agent → ResourceNotFoundException, no save, no downstream interaction")
    void createSnapshot_UnknownAgent_ThrowsAndDoesNotSave() {
        when(tradingAccountRepository.findByAgentName("unknown")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> portfolioSnapshotService.createSnapshot("unknown"))
                .isInstanceOf(ResourceNotFoundException.class)
                .hasMessageContaining("Trading account not found for agent: unknown");

        verifyNoInteractions(holdingRepository, snapshotRepository, holdingsValuationService, agentProperties);
    }

    // Helpers
    private TradingAccount newAccount(String agentName, double balance) {
        TradingAgent agent = new TradingAgent();
        agent.setName(agentName);
        TradingAccount account = new TradingAccount();
        account.setAgent(agent);
        account.setBalance(balance);
        return account;
    }
}
