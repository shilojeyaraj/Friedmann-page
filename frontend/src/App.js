import FinancialApp from './components/financial/FinancialApp';
import { ClientProvider } from './contexts/ClientContext';

function App() {
  return (
    <ClientProvider>
      <FinancialApp />
    </ClientProvider>
  );
}

export default App;