import React, { useState, useEffect } from 'react';
import './App.css';

// Utility function for uppercase input
const toUpperCase = (e) => {
  const start = e.target.selectionStart;
  const end = e.target.selectionEnd;
  e.target.value = e.target.value.toUpperCase();
  
  // Only set selection range for input types that support it
  if (e.target.type !== 'email' && e.target.type !== 'password' && e.target.type !== 'number') {
    e.target.setSelectionRange(start, end);
  }
};

// Splash Screen Component
const SplashScreen = ({ onSplashComplete }) => {
  const [showLogin, setShowLogin] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowLogin(true); // Mostrar login sobre a imagem
    }, 6000); // 6 segundos

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="splash-screen-with-image">
      <div className="splash-image-background"></div>
      <div className="splash-overlay-dark"></div>
      
      {showLogin && (
        // Login aparece por cima da imagem
        <div className="login-over-image">
          <LoginPage 
            setIsAuthenticated={(isAuth) => {
              if (isAuth) {
                onSplashComplete();
              }
            }}
            toUpperCase={toUpperCase}
          />
        </div>
      )}
    </div>
  );
};

const API_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  
  // Define initial page based on user role
  const getInitialPage = () => {
    if (user?.role === 'vendas') {
      return 'clients'; // Vendas starts at client registration
    }
    return 'home'; // Other users start at home
  };

  const [currentPage, setCurrentPage] = useState(getInitialPage());
  const [loading, setLoading] = useState(true);
  const [showSplash, setShowSplash] = useState(true);

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
        setShowSplash(false); // Não mostrar splash se já autenticado
      } else {
        logout();
      }
    } catch (err) {
      logout();
    } finally {
      setLoading(false);
    }
  };

  const handleSplashComplete = () => {
    setShowSplash(false);
    // Force recheck authentication after splash complete
    const token = localStorage.getItem('token');
    if (token) {
      validateToken(token);
    }
  };

  const validateToken = async (token) => {
    try {
      const response = await fetch(`${API_URL}/api/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setIsAuthenticated(true);
      } else {
        localStorage.removeItem('token');
        setIsAuthenticated(false);
      }
    } catch (err) {
      localStorage.removeItem('token');
      setIsAuthenticated(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setUser(null);
    setCurrentPage('home');
    setShowSplash(true); // Mostrar splash novamente no logout
  };

  const logout = () => {
    handleLogout();
  };

  // Check if user has permission for a specific action
  const hasPermission = (requiredRoles, specificPermission = null) => {
    if (!user) return false;
    
    // Check role-based permissions
    if (requiredRoles.includes(user.role)) {
      return true;
    }
    
    // Check specific permissions for reception users
    if (user.role === 'reception' && specificPermission && user.permissions) {
      return user.permissions[specificPermission] === true;
    }
    
    return false;
  };

  // Show splash screen
  if (showSplash) {
    return <SplashScreen onSplashComplete={handleSplashComplete} />;
  }

  // Show loading
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Show login or main app
  if (!isAuthenticated) {
    return <LoginPage setIsAuthenticated={setIsAuthenticated} toUpperCase={toUpperCase} />;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Header 
        user={user} 
        currentPage={currentPage} 
        setCurrentPage={setCurrentPage} 
        logout={handleLogout}
        hasPermission={hasPermission}
      />
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 content-with-sidebar page-transition">
        {currentPage === 'home' && <HomePage user={user} token={token} />}
        {currentPage === 'cash-operation' && <CashOperationPage user={user} token={token} toUpperCase={toUpperCase} />}
        {currentPage === 'history' && <HistoryPage user={user} token={token} toUpperCase={toUpperCase} />}
        {currentPage === 'users' && hasPermission(['admin', 'manager']) && <UsersPage user={user} token={token} toUpperCase={toUpperCase} />}
        {currentPage === 'products' && (hasPermission(['admin', 'manager']) || hasPermission(['reception'], 'products')) && <ProductsPage user={user} token={token} toUpperCase={toUpperCase} />}
        {currentPage === 'clients' && <ClientsPage user={user} token={token} toUpperCase={toUpperCase} />}
        {currentPage === 'billing' && (hasPermission(['admin', 'manager']) || hasPermission(['reception'], 'bills')) && <BillingPage user={user} token={token} toUpperCase={toUpperCase} />}
        {currentPage === 'pending-charges' && (hasPermission(['admin', 'manager']) || hasPermission(['reception'], 'bills')) && <PendingChargesPage user={user} token={token} />}
        {currentPage === 'activity-logs' && (hasPermission(['admin']) || hasPermission(['reception'], 'reports')) && <ActivityLogsPage user={user} token={token} toUpperCase={toUpperCase} />}
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
    <div className="min-h-screen bg-gradient-to-br from-orange-400 via-red-500 to-red-600 flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="bg-white rounded-xl shadow-2xl p-8 border-2 border-yellow-300">
          <div className="text-center mb-8">
            <p className="text-xl text-gray-800 font-semibold">Faça login para continuar</p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-100 border-2 border-red-300 text-red-800 rounded-lg text-center font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="text-center">
              <label htmlFor="username" className="block text-sm font-semibold text-gray-800 mb-2">
                Usuário
              </label>
              <input
                id="username"
                type="text"
                value={credentials.username}
                onChange={(e) => setCredentials({...credentials, username: e.target.value})}
                onInput={toUpperCase}
                className="w-full px-4 py-3 border-2 border-yellow-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent text-center text-lg font-medium bg-yellow-50"
                placeholder="NOME DE USUÁRIO"
                required
              />
            </div>

            <div className="text-center">
              <label htmlFor="password" className="block text-sm font-semibold text-gray-800 mb-2">
                Senha
              </label>
              <input
                id="password"
                type="password"
                value={credentials.password}
                onChange={(e) => setCredentials({...credentials, password: e.target.value})}
                className="w-full px-4 py-3 border-2 border-yellow-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent text-center text-lg font-medium bg-yellow-50"
                placeholder="••••••••"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white font-bold rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 disabled:opacity-50 transition-all duration-200 text-lg shadow-lg border-2 border-yellow-400"
            >
              {loading ? 'Entrando...' : 'Entrar'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

// Enhanced Header with sidebar menu
const Header = ({ user, currentPage, setCurrentPage, logout, hasPermission }) => {
  return (
    <>
      {/* Sidebar Menu */}
      <div className="sidebar-trigger">
        <div className="sidebar-content">
          {/* Logo area */}
          <div className="p-4 border-b-2 border-yellow-300">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center shadow-lg border-2 border-yellow-300">
                <div className="w-6 h-6 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-md flex items-center justify-center">
                  <span className="text-white text-xs font-bold">LOGO</span>
                </div>
              </div>
              <div className="text-white">
                <div className="text-sm font-bold">Sua Empresa</div>
                <div className="text-xs text-yellow-100">Gestão Financeira</div>
              </div>
            </div>
          </div>

          {/* Navigation Menu */}
          <nav className="py-4 px-2 space-y-1 overflow-y-auto h-full pb-32">
            <div className="text-xs font-bold text-yellow-100 px-3 mb-3">PRINCIPAL</div>
            
            <button
              onClick={() => setCurrentPage('home')}
              className={`w-full flex items-center px-3 py-3 text-sm font-bold rounded-lg transition-all duration-200 menu-item-enter ${
                currentPage === 'home' 
                  ? 'bg-white text-red-600 shadow-lg transform scale-105' 
                  : 'text-white hover:bg-white hover:text-red-600 hover:shadow-md hover:transform hover:scale-105'
              }`}
            >
              <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              Home
            </button>
            
            <button
              onClick={() => setCurrentPage('cash-operation')}
              className={`w-full flex items-center px-3 py-3 text-sm font-bold rounded-lg transition-all duration-200 menu-item-enter ${
                currentPage === 'cash-operation' 
                  ? 'bg-white text-red-600 shadow-lg transform scale-105' 
                  : 'text-white hover:bg-white hover:text-red-600 hover:shadow-md hover:transform hover:scale-105'
              }`}
            >
              <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
              Caixa
            </button>
            
            <button
              onClick={() => setCurrentPage('history')}
              className={`w-full flex items-center px-3 py-3 text-sm font-bold rounded-lg transition-all duration-200 menu-item-enter ${
                currentPage === 'history' 
                  ? 'bg-white text-red-600 shadow-lg transform scale-105' 
                  : 'text-white hover:bg-white hover:text-red-600 hover:shadow-md hover:transform hover:scale-105'
              }`}
            >
              <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Histórico
            </button>

            {(hasPermission(['admin', 'manager']) || hasPermission(['reception'], 'products') || hasPermission(['reception'], 'bills')) && (
              <>
                <div className="border-t-2 border-yellow-300 my-3 pt-3">
                  <div className="text-xs font-bold text-yellow-100 px-3 mb-2">GERENCIAMENTO</div>
                </div>

                {(hasPermission(['admin', 'manager']) || hasPermission(['reception'], 'products')) && (
                  <button
                    onClick={() => setCurrentPage('products')}
                    className={`w-full flex items-center px-3 py-3 text-sm font-bold rounded-lg transition-all duration-200 menu-item-enter ${
                      currentPage === 'products' 
                        ? 'bg-white text-red-600 shadow-lg transform scale-105' 
                        : 'text-white hover:bg-white hover:text-red-600 hover:shadow-md hover:transform hover:scale-105'
                    }`}
                  >
                    <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                    </svg>
                    Produtos
                  </button>
                )}
                
                <button
                  onClick={() => setCurrentPage('clients')}
                  className={`w-full flex items-center px-3 py-3 text-sm font-bold rounded-lg transition-all duration-200 menu-item-enter ${
                    currentPage === 'clients' 
                      ? 'bg-white text-red-600 shadow-lg transform scale-105' 
                      : 'text-white hover:bg-white hover:text-red-600 hover:shadow-md hover:transform hover:scale-105'
                  }`}
                >
                  <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  Clientes
                </button>
                
                {(hasPermission(['admin', 'manager']) || hasPermission(['reception'], 'bills')) && (
                  <>
                    <button
                      onClick={() => setCurrentPage('billing')}
                      className={`w-full flex items-center px-3 py-3 text-sm font-bold rounded-lg transition-all duration-200 menu-item-enter ${
                        currentPage === 'billing' 
                          ? 'bg-white text-red-600 shadow-lg transform scale-105' 
                          : 'text-white hover:bg-white hover:text-red-600 hover:shadow-md hover:transform hover:scale-105'
                      }`}
                    >
                      <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                      Cobranças
                    </button>
                    
                    <button
                      onClick={() => setCurrentPage('pending-charges')}
                      className={`w-full flex items-center px-3 py-3 text-sm font-bold rounded-lg transition-all duration-200 menu-item-enter ${
                        currentPage === 'pending-charges' 
                          ? 'bg-black text-yellow-400 shadow-lg transform scale-105' 
                          : 'text-white hover:bg-black hover:text-yellow-400 hover:shadow-md hover:transform hover:scale-105'
                      }`}
                    >
                      <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Pendências
                    </button>
                  </>
                )}
                
                {hasPermission(['admin', 'manager']) && (
                  <button
                    onClick={() => setCurrentPage('users')}
                    className={`w-full flex items-center px-3 py-3 text-sm font-bold rounded-lg transition-all duration-200 menu-item-enter ${
                      currentPage === 'users' 
                        ? 'bg-white text-red-600 shadow-lg transform scale-105' 
                        : 'text-white hover:bg-white hover:text-red-600 hover:shadow-md hover:transform hover:scale-105'
                    }`}
                  >
                    <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                    </svg>
                    Usuários
                  </button>
                )}
              </>
            )}

            {(hasPermission(['admin']) || hasPermission(['reception'], 'reports')) && (
              <>
                <div className="border-t-2 border-yellow-300 my-3 pt-3">
                  <div className="text-xs font-bold text-yellow-100 px-3 mb-2">ADMINISTRAÇÃO</div>
                </div>

                <button
                  onClick={() => setCurrentPage('activity-logs')}
                  className={`w-full flex items-center px-3 py-3 text-sm font-bold rounded-lg transition-all duration-200 menu-item-enter ${
                    currentPage === 'activity-logs' 
                      ? 'bg-blue-600 text-white shadow-lg transform scale-105' 
                      : 'text-white hover:bg-blue-600 hover:text-white hover:shadow-md hover:transform hover:scale-105'
                  }`}
                >
                  <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Atividades
                </button>
              </>
            )}

            {/* User info and logout at bottom */}
            <div className="fixed bottom-0 left-0 right-0 w-64 p-4 bg-gradient-to-t from-red-500 to-transparent">
              <div className="bg-white bg-opacity-20 rounded-lg px-3 py-2 backdrop-blur-sm border-2 border-yellow-300 mb-3">
                <div className="text-white text-sm font-bold">
                  {user?.username}
                </div>
                <div className="text-yellow-200 text-xs font-medium">
                  {user?.role === 'admin' ? 'Administrador' : 
                   user?.role === 'manager' ? 'Gerente' : 
                   user?.role === 'vendas' ? 'Vendas' : 'Recepção'}
                </div>
              </div>
              <button
                onClick={logout}
                className="w-full bg-black hover:bg-gray-800 text-yellow-400 px-3 py-2 rounded-lg text-sm font-bold transition-all duration-200 flex items-center justify-center border-2 border-yellow-300 shadow-lg hover:transform hover:scale-105"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                Sair
              </button>
            </div>
          </nav>
        </div>
      </div>

      {/* Top Header - simplified */}
      <header className="bg-gradient-to-r from-yellow-500 via-orange-500 to-red-500 shadow-2xl border-b-4 border-yellow-300 content-with-sidebar">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Center - Page Title */}
            <div className="flex-1 text-center">
              <h1 className="text-xl font-bold text-white">
                {currentPage === 'home' && 'Dashboard Principal'}
                {currentPage === 'cash-operation' && 'Operações de Caixa'}
                {currentPage === 'history' && 'Histórico de Transações'}
                {currentPage === 'products' && 'Gerenciamento de Produtos'}
                {currentPage === 'clients' && 'Gerenciamento de Clientes'}
                {currentPage === 'billing' && 'Sistema de Cobranças'}
                {currentPage === 'pending-charges' && 'Cobranças Pendentes'}
                {currentPage === 'users' && 'Gerenciamento de Usuários'}
                {currentPage === 'activity-logs' && 'Logs de Atividade'}
              </h1>
            </div>

            {/* Right - Current date/time */}
            <div className="text-right bg-white bg-opacity-20 rounded-lg px-3 py-1 backdrop-blur-sm border-2 border-yellow-300">
              <div className="text-white text-sm font-bold">
                {new Date().toLocaleDateString('pt-BR')}
              </div>
              <div className="text-yellow-200 text-xs font-medium">
                {new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        </div>
      </header>
    </>
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
    <div className="space-y-4 md:space-y-6">
      {/* Welcome Section */}
      <div className="bg-gradient-to-r from-yellow-400 via-orange-500 to-red-500 rounded-xl shadow-lg p-4 md:p-6 border-2 border-yellow-300">
        <div className="text-center">
          <h1 className="text-xl md:text-3xl font-bold text-white mb-2 drop-shadow-lg">
            Bem-vindo, {user?.username}!
          </h1>
          <p className="text-sm md:text-lg text-yellow-100 capitalize font-medium">
            {currentDateTime}
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-6">
        <div className="bg-gradient-to-br from-yellow-100 to-yellow-200 border-2 border-yellow-400 rounded-xl p-4 md:p-6 shadow-lg">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 md:w-12 md:h-12 bg-gradient-to-br from-yellow-500 to-orange-500 rounded-xl flex items-center justify-center shadow-md">
                <svg className="w-5 h-5 md:w-6 md:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </div>
            </div>
            <div className="ml-3 md:ml-5 w-0 flex-1">
              <dl>
                <dt className="text-xs md:text-sm font-bold text-gray-700 truncate">
                  Total Entradas
                </dt>
                <dd className="text-lg md:text-2xl font-bold text-orange-600">
                  R$ {stats?.total_entrada?.toFixed(2) || '0.00'}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-red-100 to-red-200 border-2 border-red-400 rounded-xl p-4 md:p-6 shadow-lg">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 md:w-12 md:h-12 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center shadow-md">
                <svg className="w-5 h-5 md:w-6 md:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                </svg>
              </div>
            </div>
            <div className="ml-3 md:ml-5 w-0 flex-1">
              <dl>
                <dt className="text-xs md:text-sm font-bold text-gray-700 truncate">
                  Total Saídas  
                </dt>
                <dd className="text-lg md:text-2xl font-bold text-red-600">
                  R$ {stats?.total_saida?.toFixed(2) || '0.00'}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className={`${stats?.saldo >= 0 ? 'bg-gradient-to-br from-blue-100 to-blue-200 border-2 border-blue-400' : 'bg-gradient-to-br from-orange-100 to-orange-200 border-2 border-orange-400'} rounded-xl p-4 md:p-6 shadow-lg`}>
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className={`w-10 h-10 md:w-12 md:h-12 ${stats?.saldo >= 0 ? 'bg-gradient-to-br from-blue-500 to-blue-600' : 'bg-gradient-to-br from-orange-500 to-orange-600'} rounded-xl flex items-center justify-center shadow-md`}>
                <svg className="w-5 h-5 md:w-6 md:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                </svg>
              </div>
            </div>
            <div className="ml-3 md:ml-5 w-0 flex-1">
              <dl>
                <dt className="text-xs md:text-sm font-bold text-gray-700 truncate">
                  Saldo em Caixa
                </dt>
                <dd className={`text-lg md:text-2xl font-bold ${stats?.saldo >= 0 ? 'text-blue-600' : 'text-orange-600'}`}>
                  R$ {stats?.saldo?.toFixed(2) || '0.00'}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-gray-100 to-gray-200 border-2 border-black rounded-xl p-4 md:p-6 shadow-lg">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 md:w-12 md:h-12 bg-gradient-to-br from-black to-gray-800 rounded-xl flex items-center justify-center shadow-md">
                <svg className="w-5 h-5 md:w-6 md:h-6 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
            </div>
            <div className="ml-3 md:ml-5 w-0 flex-1">
              <dl>
                <dt className="text-xs md:text-sm font-bold text-gray-700 truncate">
                  Transações Hoje
                </dt>
                <dd className="text-lg md:text-2xl font-bold text-black">
                  {stats?.today_transactions || 0}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* History Preview Section */}
      <div className="bg-white rounded-xl shadow-lg border-2 border-yellow-300">
        <div className="px-4 md:px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-t-xl">
          <div className="flex justify-between items-center">
            <h3 className="text-base md:text-lg font-bold text-white">Histórico Recente</h3>
            <button
              onClick={() => setShowHistoryPreview(!showHistoryPreview)}
              className="px-3 md:px-4 py-2 bg-white text-red-600 rounded-lg hover:bg-gray-100 text-xs md:text-sm font-bold border-2 border-yellow-300 shadow-md transition-all duration-200"
            >
              {showHistoryPreview ? 'Ocultar' : 'Exibir'}
            </button>
          </div>
        </div>

        {showHistoryPreview && (
          <div className="p-4 md:p-6">
            {stats?.recent_transactions?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs md:text-sm">
                  <thead className="bg-gradient-to-r from-yellow-100 to-orange-100">
                    <tr>
                      <th className="px-2 md:px-4 py-2 md:py-3 text-left text-xs font-bold text-gray-800 uppercase border-b-2 border-yellow-300">Data</th>
                      <th className="px-2 md:px-4 py-2 md:py-3 text-left text-xs font-bold text-gray-800 uppercase border-b-2 border-yellow-300">Tipo</th>
                      <th className="px-2 md:px-4 py-2 md:py-3 text-left text-xs font-bold text-gray-800 uppercase border-b-2 border-yellow-300">Valor</th>
                      <th className="px-2 md:px-4 py-2 md:py-3 text-left text-xs font-bold text-gray-800 uppercase border-b-2 border-yellow-300 hidden sm:table-cell">Descrição</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {stats.recent_transactions.slice(0, 5).map((transaction) => (
                      <tr key={transaction.id} className="hover:bg-yellow-50 transition-colors duration-150">
                        <td className="px-2 md:px-4 py-2 md:py-3 whitespace-nowrap text-gray-900 font-medium text-xs md:text-sm">
                          {new Date(transaction.created_at).toLocaleDateString('pt-BR')}
                        </td>
                        <td className="px-2 md:px-4 py-2 md:py-3 whitespace-nowrap">
                          <span className={`px-2 md:px-3 py-1 text-xs font-bold rounded-full border-2 ${
                            transaction.type === 'entrada' ? 'bg-yellow-100 text-orange-800 border-yellow-400' :
                            transaction.type === 'pagamento_cliente' ? 'bg-blue-100 text-blue-800 border-blue-400' :
                            'bg-red-100 text-red-800 border-red-400'
                          }`}>
                            {transaction.type === 'entrada' ? 'ENTRADA' :
                             transaction.type === 'pagamento_cliente' ? 'PAG.CLIENTE' :
                             'SAÍDA'}
                          </span>
                        </td>
                        <td className={`px-2 md:px-4 py-2 md:py-3 whitespace-nowrap font-bold text-xs md:text-sm ${
                          transaction.type === 'entrada' || transaction.type === 'pagamento_cliente' ? 'text-orange-600' : 'text-red-600'
                        }`}>
                          R$ {transaction.amount.toFixed(2)}
                        </td>
                        <td className="px-2 md:px-4 py-2 md:py-3 text-gray-900 truncate max-w-xs font-medium text-xs md:text-sm hidden sm:table-cell">
                          {transaction.description}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4 font-medium text-sm md:text-base">Nenhuma transação recente</p>
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

// History Component with enhanced filtering
const HistoryPage = ({ user, token, toUpperCase }) => {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    search: '',
    month: '',
    year: new Date().getFullYear(),
    type: '',
    paymentMethod: ''
  });

  useEffect(() => {
    fetchTransactions();
  }, [filters]);

  const fetchTransactions = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.search) params.append('search', filters.search);
      if (filters.month) params.append('month', filters.month);
      if (filters.year) params.append('year', filters.year);
      if (filters.type) params.append('transaction_type', filters.type);
      if (filters.paymentMethod) params.append('payment_method', filters.paymentMethod);

      const response = await fetch(`${API_URL}/api/transactions?${params}`, {
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

  const handleCancelTransaction = async (transactionId) => {
    if (!window.confirm('Tem certeza que deseja cancelar esta transação?')) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/transactions/${transactionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        fetchTransactions();
      }
    } catch (err) {
      console.error('Erro ao cancelar transação:', err);
    }
  };

  const generatePDF = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.month) params.append('month', filters.month);
      if (filters.year) params.append('year', filters.year);

      const response = await fetch(`${API_URL}/api/reports/transactions/pdf?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `transacoes_${filters.month || 'todas'}_${filters.year}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error('Erro ao gerar PDF:', err);
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
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-bold text-gray-900">Histórico de Transações</h2>
          <button
            onClick={generatePDF}
            className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>Gerar PDF</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="px-6 py-4 border-b bg-gray-50">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Buscar
            </label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilters({...filters, search: e.target.value})}
              onInput={toUpperCase}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="NOME, DESCRIÇÃO..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Mês
            </label>
            <select
              value={filters.month}
              onChange={(e) => setFilters({...filters, month: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              <option value="1">Janeiro</option>
              <option value="2">Fevereiro</option>
              <option value="3">Março</option>
              <option value="4">Abril</option>
              <option value="5">Maio</option>
              <option value="6">Junho</option>
              <option value="7">Julho</option>
              <option value="8">Agosto</option>
              <option value="9">Setembro</option>
              <option value="10">Outubro</option>
              <option value="11">Novembro</option>
              <option value="12">Dezembro</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Ano
            </label>
            <input
              type="number"
              value={filters.year}
              onChange={(e) => setFilters({...filters, year: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tipo
            </label>
            <select
              value={filters.type}
              onChange={(e) => setFilters({...filters, type: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              <option value="entrada">Entrada</option>
              <option value="saida">Saída</option>
              <option value="pagamento_cliente">Pagamento Cliente</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Pagamento
            </label>
            <select
              value={filters.paymentMethod}
              onChange={(e) => setFilters({...filters, paymentMethod: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              <option value="dinheiro">Dinheiro</option>
              <option value="cartao">Cartão</option>
              <option value="pix">PIX</option>
              <option value="boleto">Boleto</option>
            </select>
          </div>
        </div>
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
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Produto
              </th>
              {(user.role === 'admin' || user.role === 'manager') && (
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Usuário
                </th>
              )}
              {(user.role === 'admin' || user.role === 'manager') && (
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ações
                </th>
              )}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {transactions.map((transaction) => (
              <tr key={transaction.id} className={transaction.cancelled ? 'bg-red-50' : ''}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {new Date(transaction.created_at).toLocaleDateString('pt-BR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    transaction.cancelled ? 'bg-red-100 text-red-800' :
                    transaction.type === 'entrada' ? 'bg-green-100 text-green-800' :
                    transaction.type === 'pagamento_cliente' ? 'bg-blue-100 text-blue-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {transaction.cancelled ? 'CANCELADA' : 
                     transaction.type === 'entrada' ? 'ENTRADA' :
                     transaction.type === 'pagamento_cliente' ? 'PAG.CLIENTE' :
                     'SAÍDA'}
                  </span>
                </td>
                <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                  transaction.cancelled ? 'text-gray-500 line-through' :
                  transaction.type === 'entrada' || transaction.type === 'pagamento_cliente' ? 'text-green-600' : 'text-red-600'
                }`}>
                  R$ {transaction.amount.toFixed(2)}
                </td>
                <td className="px-6 py-4 text-sm text-gray-900">
                  {transaction.description}
                  {transaction.client_name && (
                    <div className="text-xs text-gray-500">
                      Cliente: {transaction.client_name} - {transaction.client_cpf}
                    </div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {transaction.payment_method.toUpperCase()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {transaction.product_code ? `${transaction.product_code} - ${transaction.product_name}` : '-'}
                </td>
                {(user.role === 'admin' || user.role === 'manager') && (
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {transaction.user_name}
                  </td>
                )}
                {(user.role === 'admin' || user.role === 'manager') && (
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {!transaction.cancelled && (
                      <button
                        onClick={() => handleCancelTransaction(transaction.id)}
                        className="text-red-600 hover:text-red-900 text-xs"
                      >
                        Cancelar
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Products Page with CRUD operations
const ProductsPage = ({ user, token, toUpperCase }) => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [createData, setCreateData] = useState({
    code: '',
    name: '',
    price: '',
    description: '',
    quantity: ''
  });
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await fetch(`${API_URL}/api/products`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setProducts(data);
      }
    } catch (err) {
      console.error('Erro ao buscar produtos:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProduct = async (e) => {
    e.preventDefault();
    setMessage('');
    
    try {
      const response = await fetch(`${API_URL}/api/products`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...createData,
          price: parseFloat(createData.price),
          quantity: createData.quantity ? parseInt(createData.quantity) : null
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setShowCreateForm(false);
        setCreateData({ code: '', name: '', price: '', description: '', quantity: '' });
        fetchProducts();
        setMessage('Produto criado com sucesso!');
        setTimeout(() => setMessage(''), 5000);
      } else {
        // Enhanced error handling
        if (data.detail?.includes('já existe')) {
          setMessage(`Erro: ${data.detail}`);
        } else if (data.detail?.includes('maior que zero')) {
          setMessage('Erro: O preço deve ser maior que zero');
        } else {
          setMessage(`Erro: ${data.detail}`);
        }
      }
    } catch (err) {
      setMessage('Erro de conexão');
    }
  };

  const handleUpdateProduct = async (e) => {
    e.preventDefault();
    setMessage('');
    
    try {
      const response = await fetch(`${API_URL}/api/products/${editingProduct.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: editingProduct.name,
          price: parseFloat(editingProduct.price),
          description: editingProduct.description,
          quantity: editingProduct.quantity ? parseInt(editingProduct.quantity) : null,
          active: editingProduct.active
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setEditingProduct(null);
        fetchProducts();
        setMessage('Produto atualizado com sucesso!');
        setTimeout(() => setMessage(''), 5000);
      } else {
        if (data.detail?.includes('já existe')) {
          setMessage(`Erro: ${data.detail}`);
        } else if (data.detail?.includes('maior que zero')) {
          setMessage('Erro: O preço deve ser maior que zero');
        } else {
          setMessage(`Erro: ${data.detail}`);
        }
      }
    } catch (err) {
      setMessage('Erro de conexão');
    }
  };

  const handleDeleteProduct = async (productId) => {
    if (!window.confirm('Tem certeza que deseja excluir este produto?')) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/products/${productId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        fetchProducts();
        setMessage('Produto excluído com sucesso!');
        setTimeout(() => setMessage(''), 5000);
      }
    } catch (err) {
      setMessage('Erro ao excluir produto');
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
      <div className="px-6 py-4 border-b flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900">Gerenciamento de Produtos</h2>
        <button
          onClick={() => setShowCreateForm(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
        >
          Novo Produto
        </button>
      </div>

      {message && (
        <div className={`mx-6 mt-4 p-3 rounded ${
          message.includes('Erro') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
        }`}>
          {message}
        </div>
      )}

      {showCreateForm && (
        <div className="px-6 py-4 border-b bg-gray-50">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Criar Novo Produto</h3>
          <form onSubmit={handleCreateProduct} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Código
              </label>
              <input
                type="text"
                value={createData.code}
                onChange={(e) => setCreateData({...createData, code: e.target.value})}
                onInput={toUpperCase}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nome
              </label>
              <input
                type="text"
                value={createData.name}
                onChange={(e) => setCreateData({...createData, name: e.target.value})}
                onInput={toUpperCase}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Preço (R$)
              </label>
              <input
                type="number"
                step="0.01"
                value={createData.price}
                onChange={(e) => setCreateData({...createData, price: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Descrição
              </label>
              <input
                type="text"
                value={createData.description}
                onChange={(e) => setCreateData({...createData, description: e.target.value})}
                onInput={toUpperCase}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Quantidade
              </label>
              <input
                type="number"
                value={createData.quantity}
                onChange={(e) => setCreateData({...createData, quantity: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Deixe vazio para quantidade infinita"
              />
              <p className="text-xs text-gray-500 mt-1">Deixe vazio para quantidade infinita</p>
            </div>
            <div className="md:col-span-2 flex space-x-2">
              <button
                type="submit"
                className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700"
              >
                Criar Produto
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Código
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Nome
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Preço
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Descrição
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Quantidade
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Ações
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {products.map((product) => (
              <tr key={product.id}>
                {editingProduct?.id === product.id ? (
                  <>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {product.code}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <input
                        type="text"
                        value={editingProduct.name}
                        onChange={(e) => setEditingProduct({...editingProduct, name: e.target.value})}
                        onInput={toUpperCase}
                        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                      />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <input
                        type="number"
                        step="0.01"
                        value={editingProduct.price}
                        onChange={(e) => setEditingProduct({...editingProduct, price: e.target.value})}
                        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <input
                        type="text"
                        value={editingProduct.description || ''}
                        onChange={(e) => setEditingProduct({...editingProduct, description: e.target.value})}
                        onInput={toUpperCase}
                        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                      />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <input
                        type="number"
                        value={editingProduct.quantity || ''}
                        onChange={(e) => setEditingProduct({...editingProduct, quantity: e.target.value})}
                        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                        placeholder="Infinita"
                      />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <select
                        value={editingProduct.active}
                        onChange={(e) => setEditingProduct({...editingProduct, active: e.target.value === 'true'})}
                        className="px-2 py-1 border border-gray-300 rounded text-sm"
                      >
                        <option value="true">Ativo</option>
                        <option value="false">Inativo</option>
                      </select>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                      <button
                        onClick={handleUpdateProduct}
                        className="text-green-600 hover:text-green-900"
                      >
                        Salvar
                      </button>
                      <button
                        onClick={() => setEditingProduct(null)}
                        className="text-gray-600 hover:text-gray-900"
                      >
                        Cancelar
                      </button>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {product.code}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {product.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      R$ {product.price.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {product.description || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {product.quantity ? product.quantity : 'Infinita'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        product.active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {product.active ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                      <button
                        onClick={() => setEditingProduct(product)}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleDeleteProduct(product.id)}
                        className="text-red-600 hover:text-red-900"
                      >
                        Excluir
                      </button>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Clients Page with dedicated menu
const ClientsPage = ({ user, token, toUpperCase }) => {
  const [activeTab, setActiveTab] = useState('register');
  const [clients, setClients] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [createData, setCreateData] = useState({
    name: '',
    email: '',
    phone: '',
    address: '',
    cpf: ''
  });
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (activeTab === 'search') {
      fetchClients();
    }
  }, [activeTab]);

  const fetchClients = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/clients`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setClients(data);
        setSearchResults(data);
      }
    } catch (err) {
      console.error('Erro ao buscar clientes:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (query) => {
    setSearchQuery(query);
    if (!query.trim()) {
      setSearchResults(clients);
      return;
    }

    const filtered = clients.filter(client =>
      client.name.toLowerCase().includes(query.toLowerCase()) ||
      client.cpf.includes(query.replace(/\D/g, ''))
    );
    setSearchResults(filtered);
  };

  const handleCreateClient = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const response = await fetch(`${API_URL}/api/clients`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(createData),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage('Cliente criado com sucesso!');
        setCreateData({ name: '', email: '', phone: '', address: '', cpf: '' });
        setTimeout(() => setMessage(''), 5000);
      } else {
        if (data.detail?.includes('já cadastrado')) {
          setMessage(`Erro: ${data.detail}`);
        } else if (data.detail?.includes('CPF inválido')) {
          setMessage('Erro: CPF inválido');
        } else if (data.detail?.includes('Email inválido')) {
          setMessage('Erro: Email inválido');
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

  const fetchClientDetails = async (clientId) => {
    try {
      const [clientResponse, billsResponse] = await Promise.all([
        fetch(`${API_URL}/api/clients/${clientId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/api/clients/${clientId}/pending-bills`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ]);

      if (clientResponse.ok && billsResponse.ok) {
        const clientData = await clientResponse.json();
        const billsData = await billsResponse.json();
        
        setSelectedClient({
          ...clientData,
          bills: billsData.products_with_bills || []
        });
      }
    } catch (err) {
      console.error('Erro ao buscar detalhes do cliente:', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            <button
              onClick={() => setActiveTab('register')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'register'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Cadastrar Cliente
            </button>
            <button
              onClick={() => setActiveTab('search')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'search'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Buscar Cliente
            </button>
          </nav>
        </div>

        <div className="p-6">
          {message && (
            <div className={`mb-4 p-3 rounded ${
              message.includes('Erro') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
            }`}>
              {message}
            </div>
          )}

          {activeTab === 'register' && (
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-6">Cadastrar Novo Cliente</h2>
              <form onSubmit={handleCreateClient} className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Nome Completo *
                  </label>
                  <input
                    type="text"
                    value={createData.name}
                    onChange={(e) => setCreateData({...createData, name: e.target.value})}
                    onInput={toUpperCase}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    CPF *
                  </label>
                  <input
                    type="text"
                    value={createData.cpf}
                    onChange={(e) => setCreateData({...createData, cpf: e.target.value})}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="000.000.000-00"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Email *
                  </label>
                  <input
                    type="email"
                    value={createData.email}
                    onChange={(e) => setCreateData({...createData, email: e.target.value})}
                    onInput={toUpperCase}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Telefone
                  </label>
                  <input
                    type="tel"
                    value={createData.phone}
                    onChange={(e) => setCreateData({...createData, phone: e.target.value})}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="(11) 99999-9999"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Endereço
                  </label>
                  <input
                    type="text"
                    value={createData.address}
                    onChange={(e) => setCreateData({...createData, address: e.target.value})}
                    onInput={toUpperCase}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div className="md:col-span-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 font-medium"
                  >
                    {loading ? 'Cadastrando...' : 'Cadastrar Cliente'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {activeTab === 'search' && (
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-6">Buscar Cliente</h2>
              
              <div className="mb-6">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  onInput={toUpperCase}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="BUSCAR POR NOME OU CPF..."
                />
              </div>

              {loading ? (
                <div className="flex justify-center items-center h-32">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {searchResults.map((client) => (
                    <div
                      key={client.id}
                      className="bg-gray-50 border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                      onClick={() => fetchClientDetails(client.id)}
                    >
                      <h3 className="font-medium text-gray-900">{client.name}</h3>
                      <p className="text-sm text-gray-600">CPF: {client.cpf}</p>
                      <p className="text-sm text-gray-600">Email: {client.email}</p>
                      <button className="mt-2 text-blue-600 hover:text-blue-800 text-sm font-medium">
                        Ver Detalhes →
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {searchResults.length === 0 && !loading && (
                <div className="text-center py-8 text-gray-500">
                  {searchQuery ? 'Nenhum cliente encontrado' : 'Nenhum cliente cadastrado'}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Client Details Modal */}
      {selectedClient && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-gray-900">Detalhes do Cliente</h3>
              <button
                onClick={() => setSelectedClient(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Nome</label>
                  <p className="text-sm text-gray-900">{selectedClient.name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">CPF</label>
                  <p className="text-sm text-gray-900">{selectedClient.cpf}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Email</label>
                  <p className="text-sm text-gray-900">{selectedClient.email}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Telefone</label>
                  <p className="text-sm text-gray-900">{selectedClient.phone || 'Não informado'}</p>
                </div>
              </div>

              {selectedClient.address && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Endereço</label>
                  <p className="text-sm text-gray-900">{selectedClient.address}</p>
                </div>
              )}

              {selectedClient.bills && selectedClient.bills.length > 0 && (
                <div>
                  <h4 className="text-md font-medium text-gray-900 mb-2">Produtos e Pagamentos</h4>
                  <div className="space-y-2">
                    {selectedClient.bills.map((bill, index) => (
                      <div key={index} className="bg-gray-50 p-3 rounded-lg">
                        <div className="flex justify-between items-center">
                          <div>
                            <p className="font-medium text-gray-900">
                              {bill.product_code} - {bill.product_name}
                            </p>
                            <p className="text-sm text-gray-600">
                              {bill.pending_installments.length} parcelas pendentes
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-medium text-gray-900">
                              R$ {bill.product_price?.toFixed(2)}
                            </p>
                            {bill.oldest_overdue && (
                              <span className="text-xs text-red-600 font-medium">VENCIDA</span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Billing Page
const BillingPage = ({ user, token, toUpperCase }) => {
  const [clients, setClients] = useState([]);
  const [products, setProducts] = useState([]);
  const [bills, setBills] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [createData, setCreateData] = useState({
    client_id: '',
    product_id: '',
    total_amount: '',
    description: '',
    installments: '1'
  });

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [clientsRes, productsRes, billsRes] = await Promise.all([
        fetch(`${API_URL}/api/clients`, { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch(`${API_URL}/api/products`, { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch(`${API_URL}/api/bills`, { headers: { 'Authorization': `Bearer ${token}` } })
      ]);

      if (clientsRes.ok) {
        const clientsData = await clientsRes.json();
        setClients(clientsData);
      }
      if (productsRes.ok) {
        const productsData = await productsRes.json();
        setProducts(productsData);
      }
      if (billsRes.ok) {
        const billsData = await billsRes.json();
        setBills(billsData);
      }
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBill = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const response = await fetch(`${API_URL}/api/bills`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...createData,
          total_amount: parseFloat(createData.total_amount),
          installments: parseInt(createData.installments)
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage('Cobrança criada com sucesso!');
        setCreateData({
          client_id: '',
          product_id: '',
          total_amount: '',
          description: '',
          installments: '1'
        });
        fetchInitialData();
        setTimeout(() => setMessage(''), 5000);
      } else {
        setMessage(`Erro: ${data.detail}`);
      }
    } catch (err) {
      setMessage('Erro de conexão');
    } finally {
      setLoading(false);
    }
  };

  const selectedProduct = products.find(p => p.id === createData.product_id);

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Criar Nova Cobrança</h2>

        {message && (
          <div className={`mb-4 p-3 rounded ${
            message.includes('Erro') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
          }`}>
            {message}
          </div>
        )}

        <form onSubmit={handleCreateBill} className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Cliente *
            </label>
            <select
              value={createData.client_id}
              onChange={(e) => setCreateData({...createData, client_id: e.target.value})}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Selecione um cliente</option>
              {clients.map(client => (
                <option key={client.id} value={client.id}>
                  {client.name} - {client.cpf}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Produto (Opcional)
            </label>
            <select
              value={createData.product_id}
              onChange={(e) => {
                const productId = e.target.value;
                const product = products.find(p => p.id === productId);
                setCreateData({
                  ...createData, 
                  product_id: productId,
                  total_amount: product ? product.price.toString() : createData.total_amount
                });
              }}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Selecione um produto</option>
              {products.map(product => (
                <option key={product.id} value={product.id}>
                  {product.code} - {product.name} - R$ {product.price.toFixed(2)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Valor Total (R$) *
            </label>
            <input
              type="number"
              step="0.01"
              value={createData.total_amount}
              onChange={(e) => setCreateData({...createData, total_amount: e.target.value})}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            {selectedProduct && (
              <p className="text-sm text-gray-500 mt-1">
                Preço do produto: R$ {selectedProduct.price.toFixed(2)}
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Número de Parcelas *
            </label>
            <select
              value={createData.installments}
              onChange={(e) => setCreateData({...createData, installments: e.target.value})}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              {[1,2,3,4,5,6,7,8,9,10,11,12].map(num => (
                <option key={num} value={num}>{num}x</option>
              ))}
            </select>
            {createData.total_amount && createData.installments && (
              <p className="text-sm text-gray-500 mt-1">
                Valor por parcela: R$ {(parseFloat(createData.total_amount) / parseInt(createData.installments)).toFixed(2)}
              </p>
            )}
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Descrição *
            </label>
            <textarea
              value={createData.description}
              onChange={(e) => setCreateData({...createData, description: e.target.value})}
              onInput={toUpperCase}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows="3"
              required
            />
          </div>

          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 font-medium"
            >
              {loading ? 'Criando...' : 'Criar Cobrança'}
            </button>
          </div>
        </form>
      </div>

      {/* Recent Bills */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-medium text-gray-900">Cobranças Recentes</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cliente
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Produto
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Valor Total
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Parcelas
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Data
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {bills.slice(0, 10).map((bill) => (
                <tr key={bill.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {bill.client_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {bill.product_name || 'Sem produto'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    R$ {bill.total_amount.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {bill.installments}x
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(bill.created_at).toLocaleDateString('pt-BR')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// Pending Charges Page
const PendingChargesPage = ({ user, token }) => {
  const [pendingBills, setPendingBills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    month: new Date().getMonth() + 1,
    year: new Date().getFullYear(),
    clientName: ''
  });
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchPendingBills();
  }, [filters]);

  const fetchPendingBills = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.month) params.append('month', filters.month);
      if (filters.year) params.append('year', filters.year);
      if (filters.clientName) params.append('client_name', filters.clientName);

      const response = await fetch(`${API_URL}/api/bills/pending?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setPendingBills(data);
      }
    } catch (err) {
      console.error('Erro ao buscar cobranças pendentes:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePayInstallment = async (installmentId) => {
    if (!window.confirm('Confirma o pagamento desta parcela?')) {
      return;
    }

    setMessage('');
    try {
      const response = await fetch(`${API_URL}/api/bills/installments/${installmentId}/pay`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ payment_method: 'dinheiro' }),
      });

      if (response.ok) {
        const data = await response.json();
        setMessage(`Pagamento registrado! Parcela ${data.installment_paid} paga - R$ ${data.amount.toFixed(2)}`);
        fetchPendingBills();
        setTimeout(() => setMessage(''), 5000);
      } else {
        const errorData = await response.json();
        setMessage(`Erro: ${errorData.detail}`);
      }
    } catch (err) {
      setMessage('Erro de conexão');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h2 className="text-xl font-bold text-gray-900">Cobranças Pendentes</h2>
        </div>

        {/* Filters */}
        <div className="px-6 py-4 border-b bg-yellow-50">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Mês
              </label>
              <select
                value={filters.month}
                onChange={(e) => setFilters({...filters, month: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-yellow-500"
              >
                <option value="1">Janeiro</option>
                <option value="2">Fevereiro</option>
                <option value="3">Março</option>
                <option value="4">Abril</option>
                <option value="5">Maio</option>
                <option value="6">Junho</option>
                <option value="7">Julho</option>
                <option value="8">Agosto</option>
                <option value="9">Setembro</option>
                <option value="10">Outubro</option>
                <option value="11">Novembro</option>
                <option value="12">Dezembro</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Ano
              </label>
              <input
                type="number"
                value={filters.year}
                onChange={(e) => setFilters({...filters, year: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-yellow-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nome do Cliente
              </label>
              <input
                type="text"
                value={filters.clientName}
                onChange={(e) => setFilters({...filters, clientName: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-yellow-500"
                placeholder="DIGITE O NOME..."
              />
            </div>
          </div>
        </div>

        {message && (
          <div className={`mx-6 mt-4 p-3 rounded ${
            message.includes('Erro') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
          }`}>
            {message}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cliente
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Produto
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Parcela
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Valor
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Vencimento
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {pendingBills.map((bill) => (
                <tr key={bill.id} className={bill.status === 'overdue' ? 'bg-red-50' : ''}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div>
                      <p className="font-medium">{bill.client_name}</p>
                      <p className="text-xs text-gray-500">{bill.client_cpf}</p>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {bill.product_code ? `${bill.product_code} - ${bill.product_name}` : 'Sem produto'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {bill.installment_number}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    R$ {bill.amount.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(bill.due_date).toLocaleDateString('pt-BR')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      bill.status === 'overdue' 
                        ? 'bg-red-100 text-red-800' 
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {bill.status === 'overdue' ? 'VENCIDA' : 'PENDENTE'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                    <button
                      onClick={() => handlePayInstallment(bill.id)}
                      className="bg-green-600 text-white px-3 py-1 rounded-md hover:bg-green-700 text-xs font-medium"
                    >
                      Quitar Dívida
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {pendingBills.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <p>Nenhuma cobrança pendente encontrada para o período selecionado</p>
          </div>
        )}
      </div>
    </div>
  );
};

// Users Management Component
const UsersPage = ({ user, token, toUpperCase }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [editFormData, setEditFormData] = useState({
    username: '',
    email: '',
    role: '',
    newPassword: '',
    confirmPassword: '',
    active: true,
    permissions: {}
  });
  const [createData, setCreateData] = useState({
    username: '',
    email: '',
    password: '',
    role: 'vendas'
  });
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await fetch(`${API_URL}/api/users`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setUsers(data);
      }
    } catch (err) {
      console.error('Erro ao buscar usuários:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setMessage('');
    
    try {
      const response = await fetch(`${API_URL}/api/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(createData),
      });

      const data = await response.json();

      if (response.ok) {
        setShowCreateForm(false);
        setCreateData({ username: '', email: '', password: '', role: 'vendas' });
        fetchUsers();
        setMessage('Usuário criado com sucesso!');
        setTimeout(() => setMessage(''), 5000);
      } else {
        if (data.detail?.includes('já existe')) {
          setMessage(`Erro: ${data.detail}`);
        } else if (data.detail?.includes('já cadastrado')) {
          setMessage(`Erro: ${data.detail}`);
        } else if (data.detail?.includes('Email inválido')) {
          setMessage('Erro: Email inválido');
        } else if (data.detail?.includes('6 caracteres')) {
          setMessage('Erro: Senha deve ter pelo menos 6 caracteres');
        } else {
          setMessage(`Erro: ${data.detail}`);
        }
      }
    } catch (err) {
      setMessage('Erro de conexão');
    }
  };

  const handleToggleUser = async (userId, currentStatus) => {
    try {
      const response = await fetch(`${API_URL}/api/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ active: !currentStatus }),
      });

      if (response.ok) {
        fetchUsers();
        setMessage(`Usuário ${!currentStatus ? 'ativado' : 'desativado'} com sucesso!`);
        setTimeout(() => setMessage(''), 3000);
      }
    } catch (err) {
      console.error('Erro ao atualizar usuário:', err);
    }
  };

  const handleDeleteUser = async (userId, username) => {
    if (!window.confirm(`Tem certeza que deseja excluir o usuário ${username}?`)) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        fetchUsers();
        setMessage('Usuário excluído com sucesso!');
        setTimeout(() => setMessage(''), 3000);
      }
    } catch (err) {
      setMessage('Erro ao excluir usuário');
    }
  };

  const handleResetPassword = async (userId, username) => {
    const newPassword = prompt(`Digite a nova senha para ${username}:`);
    if (!newPassword) return;
    
    if (newPassword.length < 6) {
      setMessage('Erro: Senha deve ter pelo menos 6 caracteres');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/users/${userId}/password`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          new_password: newPassword
        }),
      });

      if (response.ok) {
        setMessage(`Senha alterada com sucesso para ${username}!`);
        setTimeout(() => setMessage(''), 3000);
      } else {
        const data = await response.json();
        setMessage(`Erro: ${data.detail}`);
        setTimeout(() => setMessage(''), 3000);
      }
    } catch (err) {
      setMessage('Erro ao alterar senha');
      setTimeout(() => setMessage(''), 3000);
    }
  };

  const handleForcePasswordChange = async (userId, username) => {
    if (!window.confirm(`Forçar ${username} a alterar senha no próximo login?`)) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          require_password_change: true
        }),
      });

      if (response.ok) {
        fetchUsers();
        setMessage(`${username} será obrigado a alterar senha no próximo login!`);
        setTimeout(() => setMessage(''), 3000);
      } else {
        const data = await response.json();
        setMessage(`Erro: ${data.detail}`);
        setTimeout(() => setMessage(''), 3000);
      }
    } catch (err) {
      setMessage('Erro ao configurar mudança de senha obrigatória');
      setTimeout(() => setMessage(''), 3000);
    }
  };

  const handleManagePermissions = (userItem) => {
    const currentPermissions = userItem.permissions || {};
    const availablePermissions = [
      { key: 'bills', label: 'Cobranças' },
      { key: 'reports', label: 'Relatórios' },
      { key: 'products', label: 'Produtos' }
    ];

    const permissionsText = availablePermissions.map(perm => {
      const hasPermission = currentPermissions[perm.key] === true;
      return `${perm.label}: ${hasPermission ? 'SIM' : 'NÃO'}`;
    }).join('\n');

    const newPermissionsText = prompt(
      `Permissões atuais para ${userItem.username}:\n${permissionsText}\n\n` +
      `Digite as permissões separadas por vírgula (bills, reports, products):\n` +
      `Deixe vazio para remover todas as permissões.`
    );

    if (newPermissionsText === null) return; // User cancelled

    const newPermissions = {};
    if (newPermissionsText.trim()) {
      const permissionsList = newPermissionsText.split(',').map(p => p.trim().toLowerCase());
      availablePermissions.forEach(perm => {
        newPermissions[perm.key] = permissionsList.includes(perm.key);
      });
    }

    updateUserPermissions(userItem.id, userItem.username, newPermissions);
  };

  const updateUserPermissions = async (userId, username, permissions) => {
    try {
      const response = await fetch(`${API_URL}/api/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          permissions: permissions
        }),
      });

      if (response.ok) {
        fetchUsers();
        setMessage(`Permissões atualizadas para ${username}!`);
        setTimeout(() => setMessage(''), 3000);
      } else {
        const data = await response.json();
        setMessage(`Erro: ${data.detail}`);
        setTimeout(() => setMessage(''), 3000);
      }
    } catch (err) {
      setMessage('Erro ao atualizar permissões');
      setTimeout(() => setMessage(''), 3000);
    }
  };

  const openEditModal = (userItem) => {
    setEditingUser(userItem);
    setEditFormData({
      username: userItem.username,
      email: userItem.email,
      role: userItem.role,
      newPassword: '',
      confirmPassword: '',
      active: userItem.active,
      permissions: userItem.permissions || {}
    });
    setShowEditModal(true);
  };

  const closeEditModal = () => {
    setShowEditModal(false);
    setEditingUser(null);
    setEditFormData({
      username: '',
      email: '',
      role: '',
      newPassword: '',
      confirmPassword: '',
      active: true,
      permissions: {}
    });
  };

  const handleSaveUser = async (e) => {
    e.preventDefault();
    setMessage('');

    // Validar senhas se foram preenchidas
    if (editFormData.newPassword && editFormData.newPassword !== editFormData.confirmPassword) {
      setMessage('Erro: As senhas não coincidem');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    if (editFormData.newPassword && editFormData.newPassword.length < 6) {
      setMessage('Erro: Senha deve ter pelo menos 6 caracteres');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    try {
      // 1. Atualizar dados básicos
      const basicResponse = await fetch(`${API_URL}/api/users/${editingUser.id}/basic`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          username: editFormData.username,
          email: editFormData.email,
          role: editFormData.role
        }),
      });

      if (!basicResponse.ok) {
        const data = await basicResponse.json();
        setMessage(`Erro: ${data.detail}`);
        return;
      }

      // 2. Atualizar status e permissões
      const statusResponse = await fetch(`${API_URL}/api/users/${editingUser.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          active: editFormData.active,
          permissions: editFormData.permissions
        }),
      });

      if (!statusResponse.ok) {
        const data = await statusResponse.json();
        setMessage(`Erro ao atualizar status: ${data.detail}`);
        return;
      }

      // 3. Atualizar senha se fornecida
      if (editFormData.newPassword) {
        const passwordResponse = await fetch(`${API_URL}/api/users/${editingUser.id}/password`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            new_password: editFormData.newPassword
          }),
        });

        if (!passwordResponse.ok) {
          const data = await passwordResponse.json();
          setMessage(`Erro ao alterar senha: ${data.detail}`);
          return;
        }
      }

      // Sucesso
      closeEditModal();
      fetchUsers();
      setMessage('Usuário atualizado com sucesso!');
      setTimeout(() => setMessage(''), 5000);

    } catch (err) {
      setMessage('Erro de conexão');
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
      <div className="px-6 py-4 border-b flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900">Gerenciamento de Usuários</h2>
        <button
          onClick={() => setShowCreateForm(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium"
        >
          Novo Usuário
        </button>
      </div>

      {message && (
        <div className={`mx-6 mt-4 p-3 rounded ${
          message.includes('Erro') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
        }`}>
          {message}
        </div>
      )}

      {showCreateForm && (
        <div className="px-6 py-4 border-b bg-blue-50">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Criar Novo Usuário</h3>
          <form onSubmit={handleCreateUser} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nome de Usuário *
              </label>
              <input
                type="text"
                value={createData.username}
                onChange={(e) => setCreateData({...createData, username: e.target.value})}
                onInput={toUpperCase}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email *
              </label>
              <input
                type="email"
                value={createData.email}
                onChange={(e) => setCreateData({...createData, email: e.target.value})}
                onInput={toUpperCase}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Senha *
              </label>
              <input
                type="password"
                value={createData.password}
                onChange={(e) => setCreateData({...createData, password: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
                minLength="6"
                placeholder="Mínimo 6 caracteres"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Função *
              </label>
              <select
                value={createData.role}
                onChange={(e) => setCreateData({...createData, role: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="reception">Recepção</option>
                <option value="vendas">Vendas</option>
                {user.role === 'admin' && <option value="manager">Gerente</option>}
                {user.role === 'admin' && <option value="admin">Administrador</option>}
              </select>
            </div>
            <div className="md:col-span-2 flex space-x-2">
              <button
                type="submit"
                className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700"
              >
                Criar Usuário
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Usuário
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Email
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Função
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Criado em
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Ações
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {users.map((userItem) => (
              <tr key={userItem.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {userItem.username}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {userItem.email}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    userItem.role === 'admin' ? 'bg-red-100 text-red-800' :
                    userItem.role === 'manager' ? 'bg-blue-100 text-blue-800' :
                    userItem.role === 'vendas' ? 'bg-purple-100 text-purple-800' :
                    'bg-green-100 text-green-800'
                  }`}>
                    {userItem.role === 'admin' ? 'Administrador' :
                     userItem.role === 'manager' ? 'Gerente' :
                     userItem.role === 'vendas' ? 'Vendas' : 'Recepção'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    userItem.active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {userItem.active ? 'Ativo' : 'Inativo'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {new Date(userItem.created_at).toLocaleDateString('pt-BR')}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                  {userItem.username !== 'ADMIN' && (
                    <>
                      <button
                        onClick={() => openEditModal(userItem)}
                        className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700"
                        title="Editar usuário"
                      >
                        Editar
                      </button>
                      {user.role === 'admin' && (
                        <button
                          onClick={() => handleDeleteUser(userItem.id, userItem.username)}
                          className="bg-red-600 text-white px-3 py-1 rounded-md text-xs font-medium hover:bg-red-700"
                        >
                          Excluir
                        </button>
                      )}
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal de Edição Completo */}
      {showEditModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-2xl shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-bold text-gray-900">
                  Editar Usuário: {editingUser?.username}
                </h3>
                <button
                  onClick={closeEditModal}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <form onSubmit={handleSaveUser} className="space-y-4">
                {/* Dados Básicos */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Nome de Usuário *
                    </label>
                    <input
                      type="text"
                      value={editFormData.username}
                      onChange={(e) => setEditFormData({...editFormData, username: e.target.value})}
                      onInput={toUpperCase}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Email *
                    </label>
                    <input
                      type="email"
                      value={editFormData.email}
                      onChange={(e) => setEditFormData({...editFormData, email: e.target.value})}
                      onInput={toUpperCase}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Função *
                    </label>
                    <select
                      value={editFormData.role}
                      onChange={(e) => setEditFormData({...editFormData, role: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="reception">Recepção</option>
                      <option value="vendas">Vendas</option>
                      {user.role === 'admin' && <option value="manager">Gerente</option>}
                      {user.role === 'admin' && <option value="admin">Administrador</option>}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Status
                    </label>
                    <select
                      value={editFormData.active}
                      onChange={(e) => setEditFormData({...editFormData, active: e.target.value === 'true'})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="true">Ativo</option>
                      <option value="false">Inativo</option>
                    </select>
                  </div>
                </div>

                {/* Alterar Senha */}
                <div className="border-t pt-4">
                  <h4 className="text-md font-medium text-gray-900 mb-3">Alterar Senha (Opcional)</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Nova Senha
                      </label>
                      <input
                        type="password"
                        value={editFormData.newPassword}
                        onChange={(e) => setEditFormData({...editFormData, newPassword: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Mínimo 6 caracteres"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Confirmar Nova Senha
                      </label>
                      <input
                        type="password"
                        value={editFormData.confirmPassword}
                        onChange={(e) => setEditFormData({...editFormData, confirmPassword: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Confirme a nova senha"
                      />
                    </div>
                  </div>
                </div>

                {/* Permissões Especiais */}
                {user.role === 'admin' && editFormData.role === 'reception' && (
                  <div className="border-t pt-4">
                    <h4 className="text-md font-medium text-gray-900 mb-3">Permissões Especiais</h4>
                    <div className="grid grid-cols-3 gap-4">
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={editFormData.permissions.bills || false}
                          onChange={(e) => setEditFormData({
                            ...editFormData, 
                            permissions: {...editFormData.permissions, bills: e.target.checked}
                          })}
                          className="mr-2"
                        />
                        Cobranças
                      </label>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={editFormData.permissions.reports || false}
                          onChange={(e) => setEditFormData({
                            ...editFormData, 
                            permissions: {...editFormData.permissions, reports: e.target.checked}
                          })}
                          className="mr-2"
                        />
                        Relatórios
                      </label>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={editFormData.permissions.products || false}
                          onChange={(e) => setEditFormData({
                            ...editFormData, 
                            permissions: {...editFormData.permissions, products: e.target.checked}
                          })}
                          className="mr-2"
                        />
                        Produtos
                      </label>
                    </div>
                  </div>
                )}

                {/* Botões */}
                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={closeEditModal}
                    className="bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                  >
                    Salvar Alterações
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Activity Logs Component (Admin only)
const ActivityLogsPage = ({ user, token, toUpperCase }) => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    userName: '',
    activityType: ''
  });

  useEffect(() => {
    fetchLogs();
  }, [filters]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);
      if (filters.userName) params.append('user_name', filters.userName);
      if (filters.activityType) params.append('activity_type', filters.activityType);

      const response = await fetch(`${API_URL}/api/activity-logs?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setLogs(data);
      }
    } catch (err) {
      console.error('Erro ao buscar logs:', err);
    } finally {
      setLoading(false);
    }
  };

  if (user.role !== 'admin') {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Acesso Negado</h2>
          <p className="text-gray-600">Apenas administradores podem visualizar logs de atividade.</p>
        </div>
      </div>
    );
  }

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
        <h2 className="text-xl font-bold text-gray-900">Histórico de Atividades</h2>
      </div>

      {/* Filters */}
      <div className="px-6 py-4 border-b bg-gray-50">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Data Início
            </label>
            <input
              type="date"
              value={filters.startDate}
              onChange={(e) => setFilters({...filters, startDate: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Data Fim
            </label>
            <input
              type="date"
              value={filters.endDate}
              onChange={(e) => setFilters({...filters, endDate: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome do Usuário
            </label>
            <input
              type="text"
              value={filters.userName}
              onChange={(e) => setFilters({...filters, userName: e.target.value})}
              onInput={toUpperCase}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="NOME DO USUÁRIO"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tipo de Atividade
            </label>
            <select
              value={filters.activityType}
              onChange={(e) => setFilters({...filters, activityType: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              <option value="login">Login</option>
              <option value="login_failed">Login Falhado</option>
              <option value="user_created">Usuário Criado</option>
              <option value="user_deactivated">Usuário Desativado</option>
              <option value="user_activated">Usuário Ativado</option>
              <option value="user_deleted">Usuário Excluído</option>
              <option value="transaction_created">Transação Criada</option>
              <option value="transaction_cancelled">Transação Cancelada</option>
              <option value="product_created">Produto Criado</option>
              <option value="product_modified">Produto Modificado</option>
              <option value="product_deleted">Produto Excluído</option>
              <option value="bill_created">Cobrança Criada</option>
              <option value="bill_paid">Cobrança Paga</option>
              <option value="client_created">Cliente Criado</option>
            </select>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Data/Hora
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Usuário
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Atividade
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Descrição
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {logs.map((log) => (
              <tr key={log.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {new Date(log.timestamp).toLocaleString('pt-BR')}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {log.user_name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    log.activity_type.includes('failed') ? 'bg-red-100 text-red-800' :
                    log.activity_type.includes('deleted') || log.activity_type.includes('cancelled') ? 'bg-red-100 text-red-800' :
                    log.activity_type.includes('created') || log.activity_type.includes('paid') ? 'bg-green-100 text-green-800' :
                    log.activity_type.includes('login') ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {log.activity_type.replace('_', ' ').toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-900">
                  {log.description}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {logs.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>Nenhum log de atividade encontrado</p>
        </div>
      )}
    </div>
  );
};

export default App;