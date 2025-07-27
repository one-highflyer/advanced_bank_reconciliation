import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { getBankAccounts, getCompanies, type BankAccount, type Company } from '../lib/services/bankReconciliationService';
import { RefreshCcw } from 'lucide-react';

interface BankReconciliationFiltersProps {
  onFiltersChange: (filters: {
    company: string;
    bankAccount: string;
    fromDate: string;
    toDate: string;
  }) => void;
}

export function BankReconciliationFilters({ onFiltersChange }: BankReconciliationFiltersProps) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<string>('');
  const [selectedBankAccount, setSelectedBankAccount] = useState<string>('');
  const [fromDate, setFromDate] = useState<string>('');
  const [toDate, setToDate] = useState<string>('');

  useEffect(() => {
    loadCompanies();
    setDefaultDates();
  }, []);

  useEffect(() => {
    if (selectedCompany) {
      loadBankAccounts();
      setSelectedBankAccount('');
    }
  }, [selectedCompany]);

  useEffect(() => {
    if (selectedCompany && selectedBankAccount && fromDate && toDate && onFiltersChange) {
      onFiltersChange({
        company: selectedCompany,
        bankAccount: selectedBankAccount,
        fromDate,
        toDate,
      });
    }
  }, [selectedCompany, selectedBankAccount, fromDate, toDate]);

  const loadCompanies = async () => {
    setLoading(true);
    try {
      const companiesData = await getCompanies();
      setCompanies(companiesData);
    } catch (err) {
      console.error('Error loading companies:', err);
      setCompanies([]);
    } finally {
      setLoading(false);
    }
  };

  const loadBankAccounts = async () => {
    setLoading(true);
    try {
      const bankAccountsData = await getBankAccounts(selectedCompany);
      setBankAccounts(bankAccountsData);
    } catch (err) {
      console.error('Error loading bank accounts:', err);
      setBankAccounts([]);
    } finally {
      setLoading(false);
    }
  };

  const setDefaultDates = () => {
    const today = new Date();
    const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate());

    setFromDate(lastMonth.toISOString().split('T')[0]);
    setToDate(today.toISOString().split('T')[0]);
  };

  const handleRefresh = () => {
    if (selectedBankAccount && fromDate && toDate) {
      onFiltersChange({
        company: selectedCompany,
        bankAccount: selectedBankAccount,
        fromDate,
        toDate,
      });
    }
  };

  return (
    <div className="bg-background rounded-lg shadow border p-6 mb-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <Label htmlFor="company">Company</Label>
          <Select
            value={selectedCompany}
            onValueChange={setSelectedCompany}
            disabled={loading}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select company" />
            </SelectTrigger>
            <SelectContent>
              {companies.map((company) => (
                <SelectItem key={company.name} value={company.name}>
                  {company.company_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label htmlFor="bank-account">Bank Account</Label>
          <Select
            value={selectedBankAccount}
            onValueChange={setSelectedBankAccount}
            disabled={loading}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select bank account" />
            </SelectTrigger>
            <SelectContent>
              {bankAccounts.map((account) => (
                <SelectItem key={account.name} value={account.name}>
                  {account.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label htmlFor="from-date">From Date</Label>
          <Input
            id="from-date"
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
          />
        </div>

        <div>
          <Label htmlFor="to-date">To Date</Label>
          <Input
            id="to-date"
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
          />
        </div>

        <div className="col-span-full flex items-end justify-end">
          <Button
            onClick={handleRefresh}
            disabled={!selectedCompany || !selectedBankAccount || !fromDate || !toDate}
          >
            Refresh
            <RefreshCcw className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
} 