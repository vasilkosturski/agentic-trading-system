import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { accountService, Account, Position, Transaction } from '../services';

// Query keys for caching
export const accountKeys = {
  all: ['accounts'] as const,
  lists: () => [...accountKeys.all, 'list'] as const,
  list: (filters: string) => [...accountKeys.lists(), { filters }] as const,
  details: () => [...accountKeys.all, 'detail'] as const,
  detail: (id: string) => [...accountKeys.details(), id] as const,
  positions: (id: string) => [...accountKeys.detail(id), 'positions'] as const,
  transactions: (id: string) => [...accountKeys.detail(id), 'transactions'] as const,
};

// Hook to get all accounts
export const useAccounts = () => {
  return useQuery({
    queryKey: accountKeys.lists(),
    queryFn: accountService.getAccounts,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
};

// Hook to get a specific account
export const useAccount = (accountId: string) => {
  return useQuery({
    queryKey: accountKeys.detail(accountId),
    queryFn: () => accountService.getAccount(accountId),
    enabled: !!accountId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

// Hook to get account positions
export const useAccountPositions = (accountId: string) => {
  return useQuery({
    queryKey: accountKeys.positions(accountId),
    queryFn: () => accountService.getAccountPositions(accountId),
    enabled: !!accountId,
    staleTime: 30 * 1000, // 30 seconds for positions
    refetchInterval: 30 * 1000, // Auto-refresh every 30 seconds
  });
};

// Hook to get account transactions
export const useAccountTransactions = (accountId: string) => {
  return useQuery({
    queryKey: accountKeys.transactions(accountId),
    queryFn: () => accountService.getAccountTransactions(accountId),
    enabled: !!accountId,
    staleTime: 60 * 1000, // 1 minute
  });
};

// Hook to create a new account
export const useCreateAccount = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: accountService.createAccount,
    onSuccess: () => {
      // Invalidate and refetch accounts list
      queryClient.invalidateQueries({ queryKey: accountKeys.lists() });
    },
  });
};

// Hook to update an account
export const useUpdateAccount = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ accountId, data }: { accountId: string; data: Partial<Account> }) =>
      accountService.updateAccount(accountId, data),
    onSuccess: (data, variables) => {
      // Update the specific account in cache
      queryClient.setQueryData(accountKeys.detail(variables.accountId), data);
      // Invalidate accounts list to ensure consistency
      queryClient.invalidateQueries({ queryKey: accountKeys.lists() });
    },
  });
};

// Hook to delete an account
export const useDeleteAccount = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: accountService.deleteAccount,
    onSuccess: (_, accountId) => {
      // Remove the account from cache
      queryClient.removeQueries({ queryKey: accountKeys.detail(accountId) });
      // Invalidate accounts list
      queryClient.invalidateQueries({ queryKey: accountKeys.lists() });
    },
  });
};