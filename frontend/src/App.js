import React, { useState, useEffect } from 'react';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [currentPage, setCurrentPage] = useState('home');
  const [loading, setLoading] = useState(true);

  const token = localStorage.getItem('token');

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchUserData();
    } else {
      setLoading(false);
    }
  }, [isAuthenticated, token]);

  const fetchUserData = async () => {
    try {
      const response = await fetch(`${API_URL}/api/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        logout();
      }
    } catch (err) {
      logout();
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setUser(null);
    setCurrentPage('home');
  };

  // Utility function for uppercase input
  const toUpperCase = (e) => {
    const start = e.target.selectionStart;
    const end = e.target.selectionEnd;
    e.target.value = e.target.value.toUpperCase();
    e.target.setSelectionRange(start, end);
  };

  // Check if user has permission for a specific action
  const hasPermission = (requiredRoles) => {
    if (!user) return false;
    return requiredRoles.includes(user.role);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage setIsAuthenticated={setIsAuthenticated} toUpperCase={toUpperCase} />;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Header 
        user={user} 
        currentPage={currentPage} 
        setCurrentPage={setCurrentPage} 
        logout={logout}
        hasPermission={hasPermission}
      />
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {currentPage === 'home' && <HomePage user={user} token={token} />}
        {currentPage === 'cash-operation' && <CashOperationPage user={user} token={token} toUpperCase={toUpperCase} />}
        {currentPage === 'history' && <HistoryPage user={user} token={token} toUpperCase={toUpperCase} />}
        {currentPage === 'users' && hasPermission(['admin', 'manager']) && <UsersPage user={user} token={token} toUpperCase={toUpperCase} />}
        {currentPage === 'products' && hasPermission(['admin', 'manager']) && <ProductsPage user={user} token={token} toUpperCase={toUpperCase} />}
        {currentPage === 'clients' && hasPermission(['admin', 'manager']) && <ClientsPage user={user} token={token} toUpperCase={toUpperCase} />}
        {currentPage === 'billing' && hasPermission(['admin', 'manager']) && <BillingPage user={user} token={token} toUpperCase={toUpperCase} />}
        {currentPage === 'pending-charges' && <PendingChargesPage user={user} token={token} />}
        {currentPage === 'activity-logs' && hasPermission(['admin']) && <ActivityLogsPage user={user} token={token} toUpperCase={toUpperCase} />}
      </main>
    </div>
  );
}

// Enhanced Login Page with centralized fields
const LoginPage = ({ setIsAuthenticated, toUpperCase }) => {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_URL}/api/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('token', data.access_token);
        setIsAuthenticated(true);
      } else {
        // Enhanced error messages
        if (data.detail === 'Usuário ou senha incorretos') {
          setError('Usuário ou senha incorretos');
        } else if (data.detail === 'Usuário desativado') {
          setError('Usuário desativado. Contate o administrador.');
        } else {
          setError(data.detail || 'Erro no login');
        }
      }
    } catch (err) {
      setError('Erro de conexão');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-blue-600 flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-gray-900">Sistema de Caixa</h2>
            <p className="mt-2 text-sm text-gray-600">Faça login para continuar</p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded text-center">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="text-center">
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                Usuário
              </label>
              <input
                id="username"
                type="text"
                value={credentials.username}
                onChange={(e) => setCredentials({...credentials, username: e.target.value})}
                onInput={toUpperCase}
                className="w-full px-4 py-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-center text-lg"
                placeholder="NOME DE USUÁRIO"
                required
              />
            </div>

            <div className="text-center">
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Senha
              </label>
              <input
                id="password"
                type="password"
                value={credentials.password}
                onChange={(e) => setCredentials({...credentials, password: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-center text-lg"
                placeholder="••••••••"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Entrando...' : 'Entrar'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

// Enhanced Header with new color scheme
const Header = ({ user, currentPage, setCurrentPage, logout, hasPermission }) => {
  return (
    <header className="bg-blue-800 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <h1 className="text-xl font-bold text-white">Sistema de Caixa</h1>
          </div>
          
          <nav className="flex items-center space-x-1">
            <button
              onClick={() => setCurrentPage('home')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'home' 
                  ? 'bg-blue-700 text-white' 
                  : 'text-blue-100 hover:bg-blue-700 hover:text-white'
              }`}
            >
              Home
            </button>
            
            <button
              onClick={() => setCurrentPage('cash-operation')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'cash-operation' 
                  ? 'bg-blue-700 text-white' 
                  : 'text-blue-100 hover:bg-blue-700 hover:text-white'
              }`}
            >
              Caixa
            </button>
            
            <button
              onClick={() => setCurrentPage('history')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                currentPage === 'history' 
                  ? 'bg-blue-700 text-white' 
                  : 'text-blue-100 hover:bg-blue-700 hover:text-white'
              }`}
            >
              Histórico
            </button>

            {hasPermission(['admin', 'manager']) && (
              <>
                <button
                  onClick={() => setCurrentPage('products')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    currentPage === 'products' 
                      ? 'bg-blue-700 text-white' 
                      : 'text-blue-100 hover:bg-blue-700 hover:text-white'
                  }`}
                >
                  Produtos
                </button>
                
                <button
                  onClick={() => setCurrentPage('clients')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    currentPage === 'clients' 
                      ? 'bg-blue-700 text-white' 
                      : 'text-blue-100 hover:bg-blue-700 hover:text-white'
                  }`}
                >
                  Clientes
                </button>
                
                <button
                  onClick={() => setCurrentPage('billing')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    currentPage === 'billing' 
                      ? 'bg-blue-700 text-white' 
                      : 'text-blue-100 hover:bg-blue-700 hover:text-white'
                  }`}
                >
                  Cobranças
                </button>
                
                <button
                  onClick={() => setCurrentPage('pending-charges')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    currentPage === 'pending-charges' 
                      ? 'bg-yellow-600 text-white' 
                      : 'text-blue-100 hover:bg-yellow-600 hover:text-white'
                  }`}
                >
                  Pendências
                </button>
                
                <button
                  onClick={() => setCurrentPage('users')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    currentPage === 'users' 
                      ? 'bg-blue-700 text-white' 
                      : 'text-blue-100 hover:bg-blue-700 hover:text-white'
                  }`}
                >
                  Usuários
                </button>
              </>
            )}

            {hasPermission(['admin']) && (
              <button
                onClick={() => setCurrentPage('activity-logs')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentPage === 'activity-logs' 
                    ? 'bg-blue-700 text-white' 
                    : 'text-blue-100 hover:bg-blue-700 hover:text-white'
                }`}
              >
                Atividades
              </button>
            )}
          </nav>

          <div className="flex items-center space-x-4">
            <span className="text-blue-100 text-sm">
              {user?.username} ({user?.role === 'admin' ? 'Admin' : user?.role === 'manager' ? 'Gerente' : 'Vendedor'})
            </span>
            <button
              onClick={logout}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Sair
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

// New Enhanced Homepage
const HomePage = ({ user, token }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showHistoryPreview, setShowHistoryPreview] = useState(false);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/dashboard/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Erro ao buscar estatísticas:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const currentDateTime = new Date(stats?.current_datetime || new Date()).toLocaleString('pt-BR', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Bem-vindo, {user?.username}!
          </h1>
          <p className="text-lg text-gray-600 capitalize">
            {currentDateTime}
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-green-600 rounded-md flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </div>
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Total Entradas
                </dt>
                <dd className="text-2xl font-bold text-green-600">
                  R$ {stats?.total_entrada?.toFixed(2) || '0.00'}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-red-600 rounded-md flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                </svg>
              </div>
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Total Saídas  
                </dt>
                <dd className="text-2xl font-bold text-red-600">
                  R$ {stats?.total_saida?.toFixed(2) || '0.00'}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className={`${stats?.saldo >= 0 ? 'bg-blue-50 border-blue-200' : 'bg-yellow-50 border-yellow-200'} border rounded-lg p-6`}>
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className={`w-8 h-8 ${stats?.saldo >= 0 ? 'bg-blue-600' : 'bg-yellow-600'} rounded-md flex items-center justify-center`}>
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                </svg>
              </div>
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Saldo em Caixa
                </dt>
                <dd className={`text-2xl font-bold ${stats?.saldo >= 0 ? 'text-blue-600' : 'text-yellow-600'}`}>
                  R$ {stats?.saldo?.toFixed(2) || '0.00'}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-gray-600 rounded-md flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Transações Hoje
                </dt>
                <dd className="text-2xl font-bold text-gray-600">
                  {stats?.today_transactions || 0}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* History Preview Section */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium text-gray-900">Histórico Recente</h3>
            <button
              onClick={() => setShowHistoryPreview(!showHistoryPreview)}
              className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
            >
              {showHistoryPreview ? 'Ocultar' : 'Exibir'}
            </button>
          </div>
        </div>

        {showHistoryPreview && (
          <div className="p-6">
            {stats?.recent_transactions?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Data</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Valor</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Descrição</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {stats.recent_transactions.slice(0, 5).map((transaction) => (
                      <tr key={transaction.id}>
                        <td className="px-4 py-2 whitespace-nowrap text-gray-900">
                          {new Date(transaction.created_at).toLocaleDateString('pt-BR')}
                        </td>
                        <td className="px-4 py-2 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                            transaction.type === 'entrada' ? 'bg-green-100 text-green-800' :
                            transaction.type === 'pagamento_cliente' ? 'bg-blue-100 text-blue-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {transaction.type === 'entrada' ? 'ENTRADA' :
                             transaction.type === 'pagamento_cliente' ? 'PAG.CLIENTE' :
                             'SAÍDA'}
                          </span>
                        </td>
                        <td className={`px-4 py-2 whitespace-nowrap font-medium ${
                          transaction.type === 'entrada' || transaction.type === 'pagamento_cliente' ? 'text-green-600' : 'text-red-600'
                        }`}>
                          R$ {transaction.amount.toFixed(2)}
                        </td>
                        <td className="px-4 py-2 text-gray-900 truncate max-w-xs">
                          {transaction.description}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">Nenhuma transação recente</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Cash Operation Component (enhanced with better error handling)
const CashOperationPage = ({ user, token, toUpperCase }) => {
  const [type, setType] = useState('entrada');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('dinheiro');
  const [productSearch, setProductSearch] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [showClientPayment, setShowClientPayment] = useState(false);
  const [clientsWithBills, setClientsWithBills] = useState([]);
  const [selectedClient, setSelectedClient] = useState('');
  const [clientProducts, setClientProducts] = useState([]);
  const [selectedClientProduct, setSelectedClientProduct] = useState('');
  const [clientPaymentMethod, setClientPaymentMethod] = useState('dinheiro');

  useEffect(() => {
    if (showClientPayment) {
      fetchClientsWithBills();
    }
  }, [showClientPayment]);

  const getPaymentMethods = () => {
    const methods = [
      { value: 'dinheiro', label: 'Dinheiro' },
      { value: 'pix', label: 'PIX' }
    ];
    
    if (type === 'entrada') {
      methods.push(
        { value: 'cartao', label: 'Cartão' },
        { value: 'boleto', label: 'Boleto' }
      );
    }
    
    return methods;
  };

  const handleProductSearch = async (e) => {
    const query = e.target.value;
    setProductSearch(query);
    
    if (query.length >= 2) {
      try {
        const response = await fetch(`${API_URL}/api/products/search?q=${encodeURIComponent(query)}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const products = await response.json();
          setSearchResults(products);
        }
      } catch (err) {
        console.error('Erro na busca:', err);
      }
    } else {
      setSearchResults([]);
    }
  };

  const selectProduct = (product) => {
    setSelectedProduct(product);
    setProductSearch(`${product.code} - ${product.name}`);
    setSearchResults([]);
    if (product.price && !amount) {
      setAmount(product.price.toString());
    }
  };

  const fetchClientsWithBills = async () => {
    try {
      const response = await fetch(`${API_URL}/api/clients/with-bills`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setClientsWithBills(data);
      }
    } catch (err) {
      console.error('Erro ao buscar clientes:', err);
    }
  };

  const fetchClientProducts = async (clientId) => {
    try {
      const response = await fetch(`${API_URL}/api/clients/${clientId}/pending-bills`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setClientProducts(data.products_with_bills || []);
      }
    } catch (err) {
      console.error('Erro ao buscar produtos do cliente:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const response = await fetch(`${API_URL}/api/transactions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          type,
          amount: parseFloat(amount),
          description,
          payment_method: paymentMethod,
          product_id: selectedProduct?.id || null,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage(`${type === 'entrada' ? 'Entrada' : 'Saída'} registrada com sucesso!`);
        setAmount('');
        setDescription('');
        setSelectedProduct(null);
        setProductSearch('');
        setTimeout(() => setMessage(''), 5000);
      } else {
        // Enhanced error message handling
        if (data.detail?.includes('maior que zero')) {
          setMessage('Erro: O valor deve ser maior que zero');
        } else {
          setMessage(`Erro: ${data.detail}`);
        }
      }
    } catch (err) {
      setMessage('Erro de conexão');
    } finally {
      setLoading(false);
    }
  };

  const handleClientPayment = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const response = await fetch(`${API_URL}/api/transactions/client-payment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          client_id: selectedClient,
          product_id: selectedClientProduct,
          payment_method: clientPaymentMethod,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setMessage(`Pagamento registrado! Parcela ${data.installment_paid} paga - R$ ${data.amount.toFixed(2)}`);
        setSelectedClient('');
        setSelectedClientProduct('');
        setClientProducts([]);
        setShowClientPayment(false);
        setTimeout(() => setMessage(''), 5000);
      } else {
        const errorData = await response.json();
        setMessage(`Erro: ${errorData.detail}`);
      }
    } catch (err) {
      setMessage('Erro de conexão');
    } finally {
      setLoading(false);
    }
  };

  const handleClientChange = (clientId) => {
    setSelectedClient(clientId);
    setSelectedClientProduct('');
    setClientProducts([]);
    if (clientId) {
      fetchClientProducts(clientId);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Operação de Caixa</h2>

        {/* Toggle buttons */}
        <div className="flex space-x-4 mb-6">
          <button
            onClick={() => setShowClientPayment(false)}
            className={`px-4 py-2 rounded-md ${
              !showClientPayment
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Transação Normal
          </button>
          <button
            onClick={() => setShowClientPayment(true)}
            className={`px-4 py-2 rounded-md ${
              showClientPayment
                ? 'bg-green-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Receber Pagamento de Cliente
          </button>
        </div>

        {message && (
          <div className={`mb-4 p-3 rounded ${
            message.includes('Erro') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
          }`}>
            {message}
          </div>
        )}

        {!showClientPayment ? (
          /* Normal Transaction Form */
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tipo de Transação
                </label>
                <select
                  value={type}
                  onChange={(e) => {
                    setType(e.target.value);
                    setPaymentMethod('dinheiro');
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="entrada">Entrada</option>
                  <option value="saida">Saída</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Forma de Pagamento
                </label>
                <select
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {getPaymentMethods().map(method => (
                    <option key={method.value} value={method.value}>
                      {method.label}
                    </option>
                  ))}
                </select>
                {type === 'saida' && (
                  <p className="text-xs text-gray-500 mt-1">
                    Saída permitida apenas com PIX ou dinheiro
                  </p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Buscar Produto (Opcional)
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={productSearch}
                  onChange={handleProductSearch}
                  onInput={toUpperCase}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Digite o código ou nome do produto"
                />
                {searchResults.length > 0 && (
                  <div className="absolute z-10 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-48 overflow-y-auto">
                    {searchResults.map((product) => (
                      <div
                        key={product.id}
                        onClick={() => selectProduct(product)}
                        className="px-3 py-2 hover:bg-gray-100 cursor-pointer"
                      >
                        <div className="font-medium">{product.code} - {product.name}</div>
                        <div className="text-sm text-gray-600">R$ {product.price.toFixed(2)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Valor (R$)
              </label>
              <input
                type="number"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Descrição
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                onInput={toUpperCase}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows="3"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className={`w-full py-2 px-4 rounded-md text-white font-medium ${
                type === 'entrada' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'
              } focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50`}
            >
              {loading ? 'Processando...' : `Registrar ${type === 'entrada' ? 'Entrada' : 'Saída'}`}
            </button>
          </form>
        ) : (
          /* Client Payment Form */
          <form onSubmit={handleClientPayment} className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <h3 className="text-lg font-medium text-blue-900 mb-2">Receber Pagamento de Cliente</h3>
              <p className="text-sm text-blue-700">
                Selecione o cliente e o produto para receber o pagamento da parcela mais antiga em atraso.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cliente
              </label>
              <select
                value={selectedClient}
                onChange={(e) => handleClientChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">Selecione um cliente</option>
                {clientsWithBills.map(client => (
                  <option key={client.client_id} value={client.client_id}>
                    {client.client_name} - {client.client_cpf} ({client.total_pending} pendentes)
                  </option>
                ))}
              </select>
            </div>

            {selectedClient && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Produto
                </label>
                <select
                  value={selectedClientProduct}
                  onChange={(e) => setSelectedClientProduct(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">Selecione um produto</option>
                  {clientProducts.map(product => (
                    <option key={product.product_id} value={product.product_id}>
                      {product.product_code} - {product.product_name} 
                      ({product.pending_installments.length} parcelas pendentes)
                      {product.oldest_overdue && (
                        <span className="text-red-600"> - VENCIDA</span>
                      )}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {selectedClientProduct && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <h4 className="font-medium text-yellow-900 mb-2">Próxima Parcela a Pagar:</h4>
                {(() => {
                  const product = clientProducts.find(p => p.product_id === selectedClientProduct);
                  const nextPayment = product?.oldest_overdue || product?.pending_installments[0];
                  if (nextPayment) {
                    return (
                      <div className="text-sm text-yellow-800">
                        <p>Parcela {nextPayment.installment_number} - R$ {nextPayment.amount.toFixed(2)}</p>
                        <p>Vencimento: {new Date(nextPayment.due_date).toLocaleDateString('pt-BR')}</p>
                        {nextPayment.is_overdue && (
                          <p className="text-red-600 font-medium">⚠️ VENCIDA</p>
                        )}
                      </div>
                    );
                  }
                  return null;
                })()}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Forma de Pagamento
              </label>
              <select
                value={clientPaymentMethod}
                onChange={(e) => setClientPaymentMethod(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="dinheiro">Dinheiro</option>
                <option value="cartao">Cartão</option>
                <option value="pix">PIX</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={loading || !selectedClient || !selectedClientProduct}
              className="w-full py-2 px-4 rounded-md text-white font-medium bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50"
            >
              {loading ? 'Processando...' : 'Receber Pagamento do Cliente'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default App;