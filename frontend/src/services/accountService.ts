import { apiClient } from './api';

// Types for account data
export interface Account {
  id: string;
  name: string;
  balance: number;
  currency: string;
  createdAt: string;
  updatedAt: string;
}

export interface Position {
  id: string;
  accountId: string;
  symbol: string;
  quantity: number;
  averagePrice: number;
  currentPrice: number;
  marketValue: number;
  unrealizedPnL: number;
  unrealizedPnLPercent: number;
}

export interface Transaction {
  id: string;
  accountId: string;
  type: 'BUY' | 'SELL';
  symbol: string;
  quantity: number;
  price: number;
  amount: number;
  timestamp: string;
  status: 'PENDING' | 'COMPLETED' | 'FAILED';
}

// Account API functions
export const accountService = {
  // Get all accounts
  getAccounts: async (): Promise<Account[]> => {
    const response = await apiClient.get('/accounts');
    return response.data;
  },

  // Get account by ID
  getAccount: async (accountId: string): Promise<Account> => {
    const response = await apiClient.get(`/accounts/${accountId}`);
    return response.data;
  },

  // Get account positions
  getAccountPositions: async (accountId: string): Promise<Position[]> => {
    const response = await apiClient.get(`/accounts/${accountId}/positions`);
    return response.data;
  },

  // Get account transactions
  getAccountTransactions: async (accountId: string): Promise<Transaction[]> => {
    const response = await apiClient.get(`/accounts/${accountId}/transactions`);
    return response.data;
  },

  // Create new account
  createAccount: async (accountData: Omit<Account, 'id' | 'createdAt' | 'updatedAt'>): Promise<Account> => {
    const response = await apiClient.post('/accounts', accountData);
    return response.data;
  },

  // Update account
  updateAccount: async (accountId: string, accountData: Partial<Account>): Promise<Account> => {
    const response = await apiClient.put(`/accounts/${accountId}`, accountData);
    return response.data;
  },

  // Delete account
  deleteAccount: async (accountId: string): Promise<void> => {
    await apiClient.delete(`/accounts/${accountId}`);
  },
};