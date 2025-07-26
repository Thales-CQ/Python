import React, { useState, useEffect } from 'react';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [user, setUser] = useState(null);
  const [currentPage, setCurrentPage] = useState('login');
  const [token, setToken] = useState(localStorage.getItem('token'));

  // Login Component
  const LoginPage = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleLogin = async (e) => {
      e.preventDefault();
      setLoading(true);
      setError('');

      try {
        const response = await fetch(`${API_URL}/api/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ username, password }),
        });

        if (response.ok) {
          const data = await response.json();
          setToken(data.access_token);
          setUser(data.user);
          localStorage.setItem('token', data.access_token);
          setCurrentPage('dashboard');
        } else {
          const errorData = await response.json();
          setError(errorData.detail || 'Erro ao fazer login');
        }
      } catch (err) {
        setError('Erro de conexão');
      } finally {
        setLoading(false);
      }
    };

    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl p-8 w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">Sistema de Caixa</h1>
            <p className="text-gray-600">Faça login para continuar</p>
          </div>

          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Usuário
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Senha
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? 'Entrando...' : 'Entrar'}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-600">
            <p>Usuário padrão: <strong>admin</strong></p>
            <p>Senha padrão: <strong>admin123</strong></p>
          </div>
        </div>
      </div>
    );
  };

  // Dashboard Component
  const Dashboard = () => {
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
      fetchSummary();
    }, []);

    const fetchSummary = async () => {
      try {
        const response = await fetch(`${API_URL}/api/transactions/summary`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setSummary(data);
        }
      } catch (err) {
        console.error('Erro ao buscar resumo:', err);
      } finally {
        setLoading(false);
      }
    };

    const getRoleLabel = (role) => {
      switch (role) {
        case 'admin': return 'Administrador';
        case 'manager': return 'Gerente';
        case 'salesperson': return 'Vendedor';
        default: return role;
      }
    };

    return (
      <div className="min-h-screen bg-gray-100">
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="flex justify-between items-center px-6 py-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Sistema de Caixa</h1>
              <p className="text-sm text-gray-600">
                Bem-vindo, {user.username} ({getRoleLabel(user.role)})
              </p>
            </div>
            <button
              onClick={() => {
                setToken(null);
                setUser(null);
                localStorage.removeItem('token');
                setCurrentPage('login');
              }}
              className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700"
            >
              Sair
            </button>
          </div>
        </header>

        {/* Navigation */}
        <nav className="bg-white shadow-sm border-b">
          <div className="px-6 py-3">
            <div className="flex space-x-4">
              <button
                onClick={() => setCurrentPage('dashboard')}
                className={`px-4 py-2 rounded-md ${
                  currentPage === 'dashboard'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                Dashboard
              </button>
              <button
                onClick={() => setCurrentPage('cashier')}
                className={`px-4 py-2 rounded-md ${
                  currentPage === 'cashier'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                Caixa
              </button>
              <button
                onClick={() => setCurrentPage('history')}
                className={`px-4 py-2 rounded-md ${
                  currentPage === 'history'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                Histórico
              </button>
              {(user.role === 'admin' || user.role === 'manager') && (
                <>
                  <button
                    onClick={() => setCurrentPage('products')}
                    className={`px-4 py-2 rounded-md ${
                      currentPage === 'products'
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    Produtos
                  </button>
                  <button
                    onClick={() => setCurrentPage('billing')}
                    className={`px-4 py-2 rounded-md ${
                      currentPage === 'billing'
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    Cobrança
                  </button>
                </>
              )}
              {user.role === 'admin' && (
                <button
                  onClick={() => setCurrentPage('users')}
                  className={`px-4 py-2 rounded-md ${
                    currentPage === 'users'
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Usuários
                </button>
              )}
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="px-6 py-8">
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center">
                    <div className="p-2 bg-green-100 rounded-full">
                      <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Total Entradas</p>
                      <p className="text-2xl font-bold text-gray-900">
                        R$ {summary?.total_entrada?.toFixed(2) || '0.00'}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center">
                    <div className="p-2 bg-red-100 rounded-full">
                      <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                      </svg>
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Total Saídas</p>
                      <p className="text-2xl font-bold text-gray-900">
                        R$ {summary?.total_saida?.toFixed(2) || '0.00'}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center">
                    <div className="p-2 bg-blue-100 rounded-full">
                      <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Saldo</p>
                      <p className={`text-2xl font-bold ${
                        (summary?.saldo || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        R$ {summary?.saldo?.toFixed(2) || '0.00'}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center">
                    <div className="p-2 bg-yellow-100 rounded-full">
                      <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Transações</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {summary?.total_transactions || 0}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Ações Rápidas</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <button
                    onClick={() => setCurrentPage('cashier')}
                    className="bg-green-600 text-white px-4 py-3 rounded-md hover:bg-green-700 flex items-center justify-center space-x-2"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    <span>Nova Transação</span>
                  </button>
                  <button
                    onClick={() => setCurrentPage('history')}
                    className="bg-blue-600 text-white px-4 py-3 rounded-md hover:bg-blue-700 flex items-center justify-center space-x-2"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2-2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                    <span>Ver Histórico</span>
                  </button>
                  {(user.role === 'admin' || user.role === 'manager') && (
                    <button
                      onClick={() => setCurrentPage('billing')}
                      className="bg-purple-600 text-white px-4 py-3 rounded-md hover:bg-purple-700 flex items-center justify-center space-x-2"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span>Cobrança</span>
                    </button>
                  )}
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    );
  };

  // Cashier Component
  const CashierPage = () => {
    const [amount, setAmount] = useState('');
    const [description, setDescription] = useState('');
    const [type, setType] = useState('entrada');
    const [paymentMethod, setPaymentMethod] = useState('dinheiro');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');

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
          }),
        });

        if (response.ok) {
          setMessage('Transação registrada com sucesso!');
          setAmount('');
          setDescription('');
          setTimeout(() => setMessage(''), 3000);
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

    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Operação de Caixa</h2>

          {message && (
            <div className={`mb-4 p-3 rounded ${
              message.includes('Erro') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
            }`}>
              {message}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tipo de Transação
                </label>
                <select
                  value={type}
                  onChange={(e) => setType(e.target.value)}
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
                  <option value="dinheiro">Dinheiro</option>
                  <option value="cartao">Cartão</option>
                  <option value="pix">PIX</option>
                  <option value="boleto">Boleto</option>
                </select>
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
        </div>
      </div>
    );
  };

  // History Component
  const HistoryPage = () => {
    const [transactions, setTransactions] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
      fetchTransactions();
    }, []);

    const fetchTransactions = async () => {
      try {
        const response = await fetch(`${API_URL}/api/transactions`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setTransactions(data);
        }
      } catch (err) {
        console.error('Erro ao buscar transações:', err);
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

    return (
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h2 className="text-xl font-bold text-gray-900">Histórico de Transações</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Data
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tipo
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Valor
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Descrição
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Pagamento
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {transactions.map((transaction) => (
                <tr key={transaction.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(transaction.created_at).toLocaleDateString('pt-BR')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      transaction.type === 'entrada' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {transaction.type === 'entrada' ? 'Entrada' : 'Saída'}
                    </span>
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                    transaction.type === 'entrada' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    R$ {transaction.amount.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {transaction.description}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {transaction.payment_method}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // Check authentication on mount
  useEffect(() => {
    if (token) {
      fetch(`${API_URL}/api/me`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
        .then(response => {
          if (response.ok) {
            return response.json();
          } else {
            throw new Error('Token inválido');
          }
        })
        .then(userData => {
          setUser(userData);
          setCurrentPage('dashboard');
        })
        .catch(() => {
          setToken(null);
          setUser(null);
          localStorage.removeItem('token');
          setCurrentPage('login');
        });
    }
  }, [token]);

  // Render current page
  if (currentPage === 'login') {
    return <LoginPage />;
  }

  if (currentPage === 'dashboard') {
    return <Dashboard />;
  }

  if (currentPage === 'cashier') {
    return (
      <div className="min-h-screen bg-gray-100">
        <header className="bg-white shadow-sm border-b">
          <div className="flex justify-between items-center px-6 py-4">
            <h1 className="text-2xl font-bold text-gray-800">Caixa</h1>
            <button
              onClick={() => setCurrentPage('dashboard')}
              className="text-blue-600 hover:text-blue-800"
            >
              ← Voltar ao Dashboard
            </button>
          </div>
        </header>
        <main className="px-6 py-8">
          <CashierPage />
        </main>
      </div>
    );
  }

  if (currentPage === 'history') {
    return (
      <div className="min-h-screen bg-gray-100">
        <header className="bg-white shadow-sm border-b">
          <div className="flex justify-between items-center px-6 py-4">
            <h1 className="text-2xl font-bold text-gray-800">Histórico</h1>
            <button
              onClick={() => setCurrentPage('dashboard')}
              className="text-blue-600 hover:text-blue-800"
            >
              ← Voltar ao Dashboard
            </button>
          </div>
        </header>
        <main className="px-6 py-8">
          <HistoryPage />
        </main>
      </div>
    );
  }

  return <Dashboard />;
}

export default App;