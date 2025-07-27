import './App.css'
import { FrappeProvider } from 'frappe-react-sdk'
import { Navbar } from './components/Navbar'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import BankReconciliation from './pages/BankReconciliation'

function App() {

	return (
		<FrappeProvider>
			<BrowserRouter>
				<div className="min-h-screen w-full bg-background">
					<Navbar />
					<Routes>
						<Route path="/" element={<BankReconciliation />} />
						<Route path="/home" element={<BankReconciliation />} />
					</Routes>
				</div>
			</BrowserRouter>
		</FrappeProvider>
	)
}

export default App
