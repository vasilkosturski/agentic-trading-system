package com.trading.dto.request;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CompleteRunRequest {

    @Valid
    private ResearchPhaseDto research;

    @NotNull(message = "Decision phase data is required")
    @Valid
    private DecisionPhaseDto decision;

    @Valid
    private ExecutionPhaseDto execution;

    public void validate() {
        if (decision != null) {
            decision.validate();
        }
    }
}
