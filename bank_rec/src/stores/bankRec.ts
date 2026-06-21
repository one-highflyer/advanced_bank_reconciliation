import { defineStore } from "pinia";
import type { LocationQuery } from "vue-router";
import {
  getBankAccounts,
  getBankRules,
  getBoot,
  getCreateDefaults,
  getMatchCandidates,
  getStatementSummary,
  getTransactionContext,
  getTransactions,
  createVoucherDraftFromTransaction,
  createVoucherFromTransaction,
  submitMatch,
  updateTransactionMetadata,
} from "@/services/api";
import type {
  BankAccount,
  BankRule,
  BankTransaction,
  BootData,
  CreateDefaultsResponse,
  CreateVoucherPayload,
  MatchCandidate,
  MatchVoucherSelection,
  StatementSummary,
  TransactionContext,
  TransactionStatusFilter,
} from "@/types/bankRec";
import { monthStartIso, todayIso } from "@/utils/format";

interface LoadingState {
  boot: boolean;
  bankAccounts: boolean;
  transactions: boolean;
  summary: boolean;
  context: boolean;
  rules: boolean;
  matchCandidates: boolean;
  submitMatch: boolean;
  updateMetadata: boolean;
  createDefaults: boolean;
  createVoucher: boolean;
  createDraft: boolean;
}

interface ErrorState {
  boot: string;
  bankAccounts: string;
  transactions: string;
  summary: string;
  context: string;
  rules: string;
  matchCandidates: string;
  submitMatch: string;
  updateMetadata: string;
  createDefaults: string;
  createVoucher: string;
  createDraft: string;
}

function stringQuery(value: LocationQuery[string], fallback = "") {
  if (Array.isArray(value)) {
    return value[0] || fallback;
  }
  return value || fallback;
}

function windowBoot(): BootData | null {
  if (!window.default_route || !window.session_user) {
    return null;
  }

  return {
    default_route: window.default_route,
    site_name: window.site_name || "",
    csrf_token: window.csrf_token || "",
    session_user: window.session_user,
    lang: window.lang || "en",
    dir: window.dir || "ltr",
    allowed_roles: window.allowed_roles || [],
    settings: window.settings || {},
    accounting_dimensions: window.accounting_dimensions || [],
  };
}

export const useBankRecStore = defineStore("bankRec", {
  state: () => ({
    boot: null as BootData | null,
    bankAccounts: [] as BankAccount[],
    selectedBankAccount: "",
    fromDate: monthStartIso(),
    toDate: todayIso(),
    transactionStatus: "unreconciled" as TransactionStatusFilter,
    transactions: [] as BankTransaction[],
    selectedTransactionName: "",
    selectedContext: null as TransactionContext | null,
    matchCandidates: [] as MatchCandidate[],
    createDefaults: null as CreateDefaultsResponse | null,
    summary: null as StatementSummary | null,
    rules: [] as BankRule[],
    loading: {
      boot: false,
      bankAccounts: false,
      transactions: false,
      summary: false,
      context: false,
      rules: false,
      matchCandidates: false,
      submitMatch: false,
      updateMetadata: false,
      createDefaults: false,
      createVoucher: false,
      createDraft: false,
    } as LoadingState,
    errors: {
      boot: "",
      bankAccounts: "",
      transactions: "",
      summary: "",
      context: "",
      rules: "",
      matchCandidates: "",
      submitMatch: "",
      updateMetadata: "",
      createDefaults: "",
      createVoucher: "",
      createDraft: "",
    } as ErrorState,
    requestIds: {
      transactions: 0,
      summary: 0,
      context: 0,
      rules: 0,
      matchCandidates: 0,
      createDefaults: 0,
    },
  }),

  getters: {
    selectedBankAccountDoc(state): BankAccount | undefined {
      return state.bankAccounts.find(
        (account) => account.name === state.selectedBankAccount
      );
    },
    selectedTransaction(state): BankTransaction | undefined {
      return state.transactions.find(
        (transaction) => transaction.name === state.selectedTransactionName
      );
    },
    activeCurrency(): string | undefined {
      return this.selectedBankAccountDoc?.currency;
    },
    selectedAmount(): number | null {
      return this.selectedTransaction?.amount ?? null;
    },
  },

  actions: {
    applyQuery(query: LocationQuery) {
      this.selectedBankAccount = stringQuery(
        query.bank_account,
        this.selectedBankAccount
      );
      this.fromDate = stringQuery(query.from_date, this.fromDate);
      this.toDate = stringQuery(query.to_date, this.toDate);
      this.selectedTransactionName = stringQuery(
        query.bank_transaction,
        this.selectedTransactionName
      );
      const status = stringQuery(query.status, this.transactionStatus);
      if (["unreconciled", "reconciled", "all"].includes(status)) {
        this.transactionStatus = status as TransactionStatusFilter;
      }
    },

    queryState() {
      return {
        bank_account: this.selectedBankAccount || undefined,
        from_date: this.fromDate || undefined,
        to_date: this.toDate || undefined,
        bank_transaction: this.selectedTransactionName || undefined,
        status:
          this.transactionStatus === "unreconciled"
            ? undefined
            : this.transactionStatus,
      };
    },

    async ensureBoot() {
      if (this.boot) {
        return;
      }

      this.loading.boot = true;
      this.errors.boot = "";

      try {
        this.boot = windowBoot() || (await getBoot());
        window.csrf_token = this.boot.csrf_token;
      } catch (error) {
        this.errors.boot =
          error instanceof Error ? error.message : "Unable to load Bank Rec.";
      } finally {
        this.loading.boot = false;
      }
    },

    async loadBankAccounts() {
      this.loading.bankAccounts = true;
      this.errors.bankAccounts = "";

      try {
        this.bankAccounts = await getBankAccounts();
        if (
          this.selectedBankAccount &&
          !this.bankAccounts.some(
            (account) => account.name === this.selectedBankAccount
          )
        ) {
          this.selectedBankAccount = "";
          this.selectedTransactionName = "";
        }
        if (!this.selectedBankAccount && this.bankAccounts.length) {
          this.selectedBankAccount = this.bankAccounts[0].name;
        }
      } catch (error) {
        this.errors.bankAccounts =
          error instanceof Error
            ? error.message
            : "Unable to load bank accounts.";
      } finally {
        this.loading.bankAccounts = false;
      }
    },

    async loadTransactions() {
      if (!this.selectedBankAccount) {
        this.transactions = [];
        this.selectedTransactionName = "";
        return;
      }

      const requestId = Date.now();
      this.requestIds.transactions = requestId;
      this.loading.transactions = true;
      this.errors.transactions = "";

      try {
        const rows = await getTransactions({
          bank_account: this.selectedBankAccount,
          from_date: this.fromDate,
          to_date: this.toDate,
          status: this.transactionStatus,
        });

        if (this.requestIds.transactions !== requestId) {
          return;
        }

        this.transactions = rows;
        if (
          this.selectedTransactionName &&
          !rows.some((row) => row.name === this.selectedTransactionName)
        ) {
          this.selectedTransactionName = "";
          this.selectedContext = null;
        }
        if (!this.selectedTransactionName && rows.length) {
          this.selectedTransactionName = rows[0].name;
        }
      } catch (error) {
        if (this.requestIds.transactions !== requestId) {
          return;
        }
        this.errors.transactions =
          error instanceof Error
            ? error.message
            : "Unable to load bank transactions.";
      } finally {
        if (this.requestIds.transactions === requestId) {
          this.loading.transactions = false;
        }
      }
    },

    async loadSummary() {
      if (!this.selectedBankAccount) {
        this.summary = null;
        return;
      }

      const requestId = Date.now();
      this.requestIds.summary = requestId;
      this.loading.summary = true;
      this.errors.summary = "";

      try {
        const summary = await getStatementSummary({
          bank_account: this.selectedBankAccount,
          from_date: this.fromDate,
          to_date: this.toDate,
        });
        if (this.requestIds.summary === requestId) {
          this.summary = summary;
        }
      } catch (error) {
        if (this.requestIds.summary === requestId) {
          this.errors.summary =
            error instanceof Error ? error.message : "Unable to load summary.";
        }
      } finally {
        if (this.requestIds.summary === requestId) {
          this.loading.summary = false;
        }
      }
    },

    async loadSelectedContext() {
      if (!this.selectedTransactionName) {
        this.selectedContext = null;
        return;
      }

      const requestId = Date.now();
      this.requestIds.context = requestId;
      this.loading.context = true;
      this.errors.context = "";

      try {
        const context = await getTransactionContext(this.selectedTransactionName);
        if (
          this.requestIds.context === requestId &&
          context.transaction.name === this.selectedTransactionName
        ) {
          this.selectedContext = context;
        }
      } catch (error) {
        if (this.requestIds.context === requestId) {
          this.errors.context =
            error instanceof Error
              ? error.message
              : "Unable to load transaction details.";
        }
      } finally {
        if (this.requestIds.context === requestId) {
          this.loading.context = false;
        }
      }
    },

    async loadMatchCandidates() {
      if (!this.selectedTransactionName) {
        this.matchCandidates = [];
        return;
      }

      const requestId = Date.now();
      this.requestIds.matchCandidates = requestId;
      this.loading.matchCandidates = true;
      this.errors.matchCandidates = "";

      try {
        const response = await getMatchCandidates({
          bank_transaction_name: this.selectedTransactionName,
          from_date: this.fromDate,
          to_date: this.toDate,
        });
        if (
          this.requestIds.matchCandidates === requestId &&
          response.transaction.name === this.selectedTransactionName
        ) {
          this.matchCandidates = response.candidates;
        }
      } catch (error) {
        if (this.requestIds.matchCandidates === requestId) {
          this.errors.matchCandidates =
            error instanceof Error
              ? error.message
              : "Unable to load match candidates.";
        }
      } finally {
        if (this.requestIds.matchCandidates === requestId) {
          this.loading.matchCandidates = false;
        }
      }
    },

    async loadCreateDefaults() {
      if (!this.selectedTransactionName) {
        this.createDefaults = null;
        return;
      }

      const requestId = Date.now();
      this.requestIds.createDefaults = requestId;
      this.loading.createDefaults = true;
      this.errors.createDefaults = "";

      try {
        const response = await getCreateDefaults(this.selectedTransactionName);
        if (
          this.requestIds.createDefaults === requestId &&
          response.transaction.name === this.selectedTransactionName
        ) {
          this.createDefaults = response;
        }
      } catch (error) {
        if (this.requestIds.createDefaults === requestId) {
          this.errors.createDefaults =
            error instanceof Error
              ? error.message
              : "Unable to load create defaults.";
        }
      } finally {
        if (this.requestIds.createDefaults === requestId) {
          this.loading.createDefaults = false;
        }
      }
    },

    async refreshReconcile() {
      await Promise.all([this.loadTransactions(), this.loadSummary()]);
      await this.loadSelectedContext();
    },

    async submitSelectedMatch(vouchers: MatchVoucherSelection[]) {
      if (!this.selectedTransactionName) {
        return null;
      }

      this.loading.submitMatch = true;
      this.errors.submitMatch = "";

      try {
        const response = await submitMatch({
          bank_transaction_name: this.selectedTransactionName,
          vouchers,
        });
        await this.refreshReconcile();
        await this.loadMatchCandidates();
        return response;
      } catch (error) {
        this.errors.submitMatch =
          error instanceof Error ? error.message : "Unable to reconcile match.";
        return null;
      } finally {
        this.loading.submitMatch = false;
      }
    },

    async createVoucher(payload: CreateVoucherPayload) {
      if (!this.selectedTransactionName) {
        return null;
      }

      this.loading.createVoucher = true;
      this.errors.createVoucher = "";

      try {
        const response = await createVoucherFromTransaction({
          bank_transaction_name: this.selectedTransactionName,
          payload,
        });
        await this.refreshReconcile();
        await Promise.all([this.loadMatchCandidates(), this.loadCreateDefaults()]);
        return response;
      } catch (error) {
        this.errors.createVoucher =
          error instanceof Error ? error.message : "Unable to create voucher.";
        return null;
      } finally {
        this.loading.createVoucher = false;
      }
    },

    async createDraftVoucher(payload: CreateVoucherPayload) {
      if (!this.selectedTransactionName) {
        return null;
      }

      this.loading.createDraft = true;
      this.errors.createDraft = "";

      try {
        return await createVoucherDraftFromTransaction({
          bank_transaction_name: this.selectedTransactionName,
          payload,
        });
      } catch (error) {
        this.errors.createDraft =
          error instanceof Error ? error.message : "Unable to create draft.";
        return null;
      } finally {
        this.loading.createDraft = false;
      }
    },

    async saveTransactionMetadata(payload: {
      reference_number?: string;
      party_type?: string;
      party?: string;
    }) {
      if (!this.selectedTransactionName) {
        return null;
      }

      this.loading.updateMetadata = true;
      this.errors.updateMetadata = "";

      try {
        const response = await updateTransactionMetadata({
          bank_transaction_name: this.selectedTransactionName,
          ...payload,
        });

        const index = this.transactions.findIndex(
          (row) => row.name === response.transaction.name
        );
        if (index >= 0) {
          this.transactions[index] = response.transaction;
        }
        if (this.selectedContext?.transaction.name === response.transaction.name) {
          this.selectedContext.transaction = response.transaction;
        }
        await this.loadMatchCandidates();
        return response;
      } catch (error) {
        this.errors.updateMetadata =
          error instanceof Error
            ? error.message
            : "Unable to update transaction.";
        return null;
      } finally {
        this.loading.updateMetadata = false;
      }
    },

    async loadRules(bankAccount?: string) {
      const requestId = Date.now();
      this.requestIds.rules = requestId;
      this.loading.rules = true;
      this.errors.rules = "";

      try {
        const rules = await getBankRules(bankAccount);
        if (this.requestIds.rules === requestId) {
          this.rules = rules;
        }
      } catch (error) {
        if (this.requestIds.rules === requestId) {
          this.errors.rules =
            error instanceof Error ? error.message : "Unable to load rules.";
        }
      } finally {
        if (this.requestIds.rules === requestId) {
          this.loading.rules = false;
        }
      }
    },

    async initialize(query: LocationQuery) {
      this.applyQuery(query);
      await this.ensureBoot();
      if (this.errors.boot) {
        return;
      }
      await this.loadBankAccounts();
    },
  },
});
