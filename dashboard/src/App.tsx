import './App.css'
import { FrappeProvider } from 'frappe-react-sdk'
import { Navbar } from './components/Navbar'
import { BrowserRouter, Routes, Route, Link, Outlet, useLocation } from 'react-router-dom'
import ReconcileTransactions from './pages/ReconcileTransactions'
import MatchedTransactions from './pages/MatchedTransactions'
import BankReconciliationStatement from './pages/BankReconciliationStatement'

function BankReconciliationLayout() {
  const location = useLocation();

  return (
    <div className="container mx-auto py-4">
      {/* Navigation Tabs */}
      <div className="border-b border-border mb-4">
        <div className="flex px-6">
          <Link
            to="/reconcile"
            className={`px-4 py-4 font-medium transition-colors duration-200 ${
              location.pathname === '/' || location.pathname === '/reconcile'
                ? 'border-b-2 border-primary text-primary'
                : 'text-muted-foreground hover:text-foreground'
            }`}>
            Reconcile Transactions
          </Link>
          <Link
            to="/matched"
            className={`px-4 py-4 font-medium transition-colors duration-200 ${
              location.pathname === '/matched'
                ? 'border-b-2 border-primary text-primary'
                : 'text-muted-foreground hover:text-foreground'
            }`}>
            Matched Transactions
          </Link>
          <Link
            to="/statement"
            className={`px-4 py-4 font-medium transition-colors duration-200 ${
              location.pathname === '/statement'
                ? 'border-b-2 border-primary text-primary'
                : 'text-muted-foreground hover:text-foreground'
            }`}>
            Bank Reconciliation Statement
          </Link>
        </div>
      </div>

      <Outlet />
    </div>
  );
}

function App() {
  return (
    <FrappeProvider>
      <BrowserRouter>
        <div className="min-h-screen w-full bg-background">
          <Navbar />
          <Routes>
            <Route path="/" element={<BankReconciliationLayout />}>
              <Route index element={<ReconcileTransactions />} />
              <Route path="reconcile" element={<ReconcileTransactions />} />
              <Route path="matched" element={<MatchedTransactions />} />
              <Route path="statement" element={<BankReconciliationStatement />} />
            </Route>
          </Routes>
        </div>
      </BrowserRouter>
    </FrappeProvider>
  )
}

export default App
