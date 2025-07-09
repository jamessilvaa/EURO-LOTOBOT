import React, { useState, useEffect } from 'react';
import './App.css';

const App = () => {
  const [currentLanguage, setCurrentLanguage] = useState('pt');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('predict');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Auth states
  const [loginForm, setLoginForm] = useState({ token: '' });
  const [adminForm, setAdminForm] = useState({ token: '' });

  // Prediction states
  const [selectedLottery, setSelectedLottery] = useState('euromillones');
  const [prediction, setPrediction] = useState(null);
  const [predictions, setPredictions] = useState([]);

  // Admin states
  const [users, setUsers] = useState([]);
  const [newUser, setNewUser] = useState({ email: '', name: '' });

  // Translations
  const translations = {
    pt: {
      title: 'EURO LOTOBOT',
      subtitle: 'Sistema Futurista de Previsão com Inteligência Artificial',
      login: 'Entrar',
      loginTitle: 'Acesso ao Sistema',
      adminTitle: 'Acesso Administrativo',
      tokenPlaceholder: 'Digite seu token de acesso (usuário ou admin)',
      adminTokenPlaceholder: 'Digite o token de administrador',
      predict: 'Gerar Previsão',
      predictions: 'Minhas Previsões',
      admin: 'Administração',
      logout: 'Sair',
      selectLottery: 'Selecione a Loteria',
      generatePrediction: 'Gerar Previsão IA',
      confidence: 'Confiança',
      analysis: 'Análise IA',
      predictionDate: 'Data da Previsão',
      mainNumbers: 'Números Principais',
      luckyNumbers: 'Números da Sorte',
      complementary: 'Complementar',
      keyNumber: 'Número Chave',
      createUser: 'Criar Usuário',
      revokeAccess: 'Revogar Acesso',
      activateUser: 'Ativar Usuário',
      email: 'Email',
      name: 'Nome',
      status: 'Status',
      actions: 'Ações',
      active: 'Ativo',
      inactive: 'Inativo',
      userManagement: 'Gerenciamento de Usuários',
      addUser: 'Adicionar Usuário',
      emailPlaceholder: 'Digite o email do usuário',
      namePlaceholder: 'Digite o nome do usuário',
      create: 'Criar',
      revoke: 'Revogar',
      activate: 'Ativar',
      loading: 'Carregando...',
      error: 'Erro',
      success: 'Sucesso',
      close: 'Fechar',
      noPredictions: 'Nenhuma previsão encontrada',
      aiPowered: 'Alimentado por IA',
      lstmModel: 'Modelo LSTM + Gemini AI',
      futuristicDesign: 'Interface Futurista',
      realTimeAnalysis: 'Análise em Tempo Real'
    },
    es: {
      title: 'EURO LOTOBOT',
      subtitle: 'Sistema Futurista de Predicción con Inteligencia Artificial',
      login: 'Iniciar Sesión',
      loginTitle: 'Acceso al Sistema',
      adminTitle: 'Acceso Administrativo',
      tokenPlaceholder: 'Ingrese su token de acceso (usuario o admin)',
      adminTokenPlaceholder: 'Ingrese el token de administrador',
      predict: 'Generar Predicción',
      predictions: 'Mis Predicciones',
      admin: 'Administración',
      logout: 'Cerrar Sesión',
      selectLottery: 'Seleccione la Lotería',
      generatePrediction: 'Generar Predicción IA',
      confidence: 'Confianza',
      analysis: 'Análisis IA',
      predictionDate: 'Fecha de Predicción',
      mainNumbers: 'Números Principales',
      luckyNumbers: 'Números de la Suerte',
      complementary: 'Complementario',
      keyNumber: 'Número Clave',
      createUser: 'Crear Usuario',
      revokeAccess: 'Revocar Acceso',
      activateUser: 'Activar Usuario',
      email: 'Email',
      name: 'Nombre',
      status: 'Estado',
      actions: 'Acciones',
      active: 'Activo',
      inactive: 'Inactivo',
      userManagement: 'Gestión de Usuarios',
      addUser: 'Agregar Usuario',
      emailPlaceholder: 'Ingrese el email del usuario',
      namePlaceholder: 'Ingrese el nombre del usuario',
      create: 'Crear',
      revoke: 'Revocar',
      activate: 'Activar',
      loading: 'Cargando...',
      error: 'Error',
      success: 'Éxito',
      close: 'Cerrar',
      noPredictions: 'No se encontraron predicciones',
      aiPowered: 'Impulsado por IA',
      lstmModel: 'Modelo LSTM + Gemini AI',
      futuristicDesign: 'Interfaz Futurista',
      realTimeAnalysis: 'Análisis en Tiempo Real'
    }
  };

  const t = translations[currentLanguage];
  const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  useEffect(() => {
    const token = localStorage.getItem('userToken');
    const adminToken = localStorage.getItem('adminToken');
    
    if (token) {
      setIsAuthenticated(true);
      setIsAdmin(false);
      loadUserPredictions();
    } else if (adminToken) {
      setIsAuthenticated(true);
      setIsAdmin(true);
      loadUsers();
    }
  }, []);

  // Unified login handler
  const handleUnifiedLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const token = loginForm.token;
    
    // Check if it's admin token first
    if (token === 'EUROADMIN252024@') {
      try {
        const response = await fetch(`${backendUrl}/api/admin/users`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          localStorage.setItem('adminToken', token);
          setIsAuthenticated(true);
          setIsAdmin(true);
          setActiveTab('admin');
          loadUsers();
          setSuccess('Login administrativo realizado com sucesso!');
        } else {
          setError('Token administrativo inválido');
        }
      } catch (err) {
        setError('Erro ao fazer login administrativo');
      }
    } else {
      // Try as user token
      try {
        const response = await fetch(`${backendUrl}/api/predict`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            lottery_type: 'euromillones',
            language: currentLanguage
          })
        });

        if (response.ok) {
          localStorage.setItem('userToken', token);
          setIsAuthenticated(true);
          setIsAdmin(false);
          loadUserPredictions();
          setSuccess('Login realizado com sucesso!');
        } else {
          setError('Token inválido ou expirado');
        }
      } catch (err) {
        setError('Erro ao fazer login');
      }
    }
    
    setLoading(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('userToken');
    localStorage.removeItem('adminToken');
    setIsAuthenticated(false);
    setIsAdmin(false);
    setUser(null);
    setActiveTab('predict');
    setPrediction(null);
    setPredictions([]);
    setUsers([]);
  };

  const loadUserPredictions = async () => {
    try {
      const token = localStorage.getItem('userToken');
      const response = await fetch(`${backendUrl}/api/user/predictions`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setPredictions(data.predictions || []);
      }
    } catch (err) {
      console.error('Error loading predictions:', err);
    }
  };

  const loadUsers = async () => {
    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(`${backendUrl}/api/admin/users`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setUsers(data.users || []);
      }
    } catch (err) {
      console.error('Error loading users:', err);
    }
  };

  const generatePrediction = async () => {
    setLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('userToken');
      const response = await fetch(`${backendUrl}/api/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          lottery_type: selectedLottery,
          language: currentLanguage
        })
      });

      if (response.ok) {
        const data = await response.json();
        setPrediction(data);
        loadUserPredictions();
        setSuccess('Previsão gerada com sucesso!');
      } else {
        setError('Erro ao gerar previsão');
      }
    } catch (err) {
      setError('Erro ao conectar com o servidor');
    } finally {
      setLoading(false);
    }
  };

  const createUser = async () => {
    setLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(`${backendUrl}/api/admin/manage-users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          action: 'create_user',
          user_data: newUser
        })
      });

      if (response.ok) {
        const data = await response.json();
        setSuccess(`Usuário criado! Token: ${data.user.access_token}`);
        setNewUser({ email: '', name: '' });
        loadUsers();
      } else {
        setError('Erro ao criar usuário');
      }
    } catch (err) {
      setError('Erro ao conectar com o servidor');
    } finally {
      setLoading(false);
    }
  };

  const manageUser = async (email, action) => {
    setLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(`${backendUrl}/api/admin/manage-users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          action: action,
          user_data: { email }
        })
      });

      if (response.ok) {
        setSuccess(`Ação ${action} realizada com sucesso!`);
        loadUsers();
      } else {
        setError(`Erro ao executar ação ${action}`);
      }
    } catch (err) {
      setError('Erro ao conectar com o servidor');
    } finally {
      setLoading(false);
    }
  };

  const renderNumbers = (numbers, lottery) => {
    if (!numbers) return null;

    return (
      <div className="numbers-display">
        <div className="main-numbers">
          <h4>{t.mainNumbers}</h4>
          <div className="numbers-grid">
            {numbers.main_numbers?.map((num, index) => (
              <div key={index} className="number-ball main">{num}</div>
            ))}
          </div>
        </div>
        
        {numbers.lucky_numbers && (
          <div className="lucky-numbers">
            <h4>{t.luckyNumbers}</h4>
            <div className="numbers-grid">
              {numbers.lucky_numbers.map((num, index) => (
                <div key={index} className="number-ball lucky">{num}</div>
              ))}
            </div>
          </div>
        )}
        
        {numbers.complementary && (
          <div className="complementary-numbers">
            <h4>{t.complementary}</h4>
            <div className="numbers-grid">
              {numbers.complementary.map((num, index) => (
                <div key={index} className="number-ball complementary">{num}</div>
              ))}
            </div>
          </div>
        )}
        
        {numbers.key_number && (
          <div className="key-numbers">
            <h4>{t.keyNumber}</h4>
            <div className="numbers-grid">
              {numbers.key_number.map((num, index) => (
                <div key={index} className="number-ball key">{num}</div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  if (!isAuthenticated) {
    return (
      <div className="app">
        <div className="login-container">
          <div className="login-header">
            <h1 className="title">{t.title}</h1>
            <p className="subtitle">{t.subtitle}</p>
            <div className="language-selector">
              <button 
                className={currentLanguage === 'pt' ? 'active' : ''}
                onClick={() => setCurrentLanguage('pt')}
              >
                PT
              </button>
              <button 
                className={currentLanguage === 'es' ? 'active' : ''}
                onClick={() => setCurrentLanguage('es')}
              >
                ES
              </button>
            </div>
          </div>

          <div className="login-forms">
            <div className="login-form">
              <h2>{t.loginTitle}</h2>
              <form onSubmit={handleUnifiedLogin}>
                <input
                  type="text"
                  placeholder={t.tokenPlaceholder}
                  value={loginForm.token}
                  onChange={(e) => setLoginForm({...loginForm, token: e.target.value})}
                  required
                />
                <button type="submit" disabled={loading}>
                  {loading ? t.loading : t.login}
                </button>
              </form>
            </div>
          </div>

          <div className="robot-image">
            <img src="https://images.pexels.com/photos/9784235/pexels-photo-9784235.jpeg" alt="Euro Lotobot" className="robot-img" />
          </div>

          <div className="features">
            <div className="feature">
              <div className="feature-icon">🤖</div>
              <h3>{t.aiPowered}</h3>
              <p>{t.lstmModel}</p>
            </div>
            <div className="feature">
              <div className="feature-icon">🚀</div>
              <h3>{t.futuristicDesign}</h3>
              <p>{t.realTimeAnalysis}</p>
            </div>
          </div>

          {error && <div className="error-message">{error}</div>}
          {success && <div className="success-message">{success}</div>}
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>{t.title}</h1>
          <div className="header-controls">
            <div className="language-selector">
              <button 
                className={currentLanguage === 'pt' ? 'active' : ''}
                onClick={() => setCurrentLanguage('pt')}
              >
                PT
              </button>
              <button 
                className={currentLanguage === 'es' ? 'active' : ''}
                onClick={() => setCurrentLanguage('es')}
              >
                ES
              </button>
            </div>
            <button className="logout-btn" onClick={handleLogout}>
              {t.logout}
            </button>
          </div>
        </div>
      </header>

      <nav className="nav">
        <button 
          className={activeTab === 'predict' ? 'active' : ''}
          onClick={() => setActiveTab('predict')}
        >
          {t.predict}
        </button>
        <button 
          className={activeTab === 'predictions' ? 'active' : ''}
          onClick={() => setActiveTab('predictions')}
        >
          {t.predictions}
        </button>
        {isAdmin && (
          <button 
            className={activeTab === 'admin' ? 'active' : ''}
            onClick={() => setActiveTab('admin')}
          >
            {t.admin}
          </button>
        )}
      </nav>

      <main className="main">
        {activeTab === 'predict' && (
          <div className="predict-section">
            <h2>{t.generatePrediction}</h2>
            
            <div className="lottery-selector">
              <label>{t.selectLottery}</label>
              <select 
                value={selectedLottery} 
                onChange={(e) => setSelectedLottery(e.target.value)}
              >
                <option value="euromillones">EuroMilhões</option>
                <option value="la_primitiva">La Primitiva</option>
                <option value="el_gordo">El Gordo</option>
              </select>
            </div>

            <button 
              className="generate-btn"
              onClick={generatePrediction}
              disabled={loading}
            >
              {loading ? t.loading : t.generatePrediction}
            </button>

            {prediction && (
              <div className="prediction-result">
                <h3>{t.generatePrediction}</h3>
                {renderNumbers(prediction.numbers, selectedLottery)}
                
                <div className="prediction-details">
                  <div className="confidence">
                    <span>{t.confidence}: {Math.round(prediction.prediction_confidence * 100)}%</span>
                  </div>
                  <div className="analysis">
                    <h4>{t.analysis}</h4>
                    <p>{prediction.ai_analysis}</p>
                  </div>
                  <div className="prediction-date">
                    <small>{t.predictionDate}: {new Date(prediction.prediction_date).toLocaleString()}</small>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'predictions' && (
          <div className="predictions-section">
            <h2>{t.predictions}</h2>
            
            {predictions.length === 0 ? (
              <p className="no-predictions">{t.noPredictions}</p>
            ) : (
              <div className="predictions-list">
                {predictions.map((pred, index) => (
                  <div key={index} className="prediction-item">
                    <h3>{pred.lottery_type}</h3>
                    {renderNumbers(pred.numbers, pred.lottery_type)}
                    <div className="prediction-meta">
                      <span>{t.confidence}: {Math.round(pred.prediction_confidence * 100)}%</span>
                      <span>{new Date(pred.prediction_date).toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'admin' && isAdmin && (
          <div className="admin-section">
            <h2>{t.userManagement}</h2>
            
            <div className="add-user-form">
              <h3>{t.addUser}</h3>
              <div className="form-group">
                <input
                  type="email"
                  placeholder={t.emailPlaceholder}
                  value={newUser.email}
                  onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                />
                <input
                  type="text"
                  placeholder={t.namePlaceholder}
                  value={newUser.name}
                  onChange={(e) => setNewUser({...newUser, name: e.target.value})}
                />
                <button onClick={createUser} disabled={loading}>
                  {loading ? t.loading : t.create}
                </button>
              </div>
            </div>

            <div className="users-table">
              <h3>{t.userManagement}</h3>
              <table>
                <thead>
                  <tr>
                    <th>{t.email}</th>
                    <th>{t.name}</th>
                    <th>{t.status}</th>
                    <th>{t.actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user, index) => (
                    <tr key={index}>
                      <td>{user.email}</td>
                      <td>{user.name}</td>
                      <td>
                        <span className={user.is_active ? 'status-active' : 'status-inactive'}>
                          {user.is_active ? t.active : t.inactive}
                        </span>
                      </td>
                      <td>
                        <div className="action-buttons">
                          {user.is_active ? (
                            <button 
                              className="revoke-btn"
                              onClick={() => manageUser(user.email, 'revoke_access')}
                            >
                              {t.revoke}
                            </button>
                          ) : (
                            <button 
                              className="activate-btn"
                              onClick={() => manageUser(user.email, 'activate_user')}
                            >
                              {t.activate}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}
    </div>
  );
};

export default App;