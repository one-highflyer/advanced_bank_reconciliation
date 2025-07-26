
interface BankTransaction {
    name: string;
    date: string;
    description: string;
    amount: number;
    currency: string;
    reference_number: string;
    deposit: number;
    withdrawal: number;
}


export { BankTransaction }
