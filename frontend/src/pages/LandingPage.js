import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { FileText, Download, TrendingUp, Shield, Clock, Check } from 'lucide-react';
import '../styles/LandingPage.css';

const LandingPage = ({ user }) => {
  const navigate = useNavigate();

  const features = [
    {
      icon: <FileText size={32} />,
      title: 'Conversão Inteligente',
      description: 'IA avançada para extrair dados de PDFs bancários com precisão'
    },
    {
      icon: <Download size={32} />,
      title: 'Múltiplos Formatos',
      description: 'Exporte para CSV ou Excel conforme sua necessidade'
    },
    {
      icon: <Shield size={32} />,
      title: 'Seguro e Privado',
      description: 'Seus dados bancários são processados com máxima segurança'
    },
    {
      icon: <Clock size={32} />,
      title: 'Rápido e Eficiente',
      description: 'Conversão instantânea com categorização fiscal automática'
    }
  ];

  const supportedBanks = ['BPI', 'Millennium BCP', 'Caixa Geral de Depósitos'];

  return (
    <div className="landing-page" data-testid="landing-page">
      {/* Header */}
      <header className="landing-header">
        <div className="container">
          <div className="header-content">
            <div className="logo" data-testid="logo">
              <FileText size={28} />
              <span>Conversor Bancário PT</span>
            </div>
            <nav className="nav-menu">
              {user ? (
                <>
                  <Button variant="ghost" onClick={() => navigate('/dashboard')} data-testid="dashboard-nav-btn">
                    Painel
                  </Button>
                  <Button onClick={() => navigate('/pricing')} data-testid="pricing-nav-btn">
                    Planos
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="ghost" onClick={() => navigate('/login')} data-testid="login-nav-btn">
                    Entrar
                  </Button>
                  <Button onClick={() => navigate('/register')} data-testid="register-nav-btn">
                    Criar Conta
                  </Button>
                </>
              )}
            </nav>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="container">
          <div className="hero-content">
            <h1 className="hero-title" data-testid="hero-title">
              Converta Extratos Bancários para Excel
              <span className="gradient-text"> em Segundos</span>
            </h1>
            <p className="hero-subtitle" data-testid="hero-subtitle">
              Solução portuguesa para converter PDFs bancários em planilhas estruturadas.
              Otimizado para BPI, Millennium e Caixa Geral com categorização fiscal automática.
            </p>
            <div className="hero-actions">
              <Button 
                size="lg" 
                onClick={() => navigate(user ? '/dashboard' : '/register')}
                data-testid="hero-cta-btn"
              >
                Começar Grátis
              </Button>
              <Button 
                size="lg" 
                variant="outline" 
                onClick={() => navigate('/pricing')}
                data-testid="hero-pricing-btn"
              >
                Ver Planos
              </Button>
            </div>
            <div className="hero-badge">
              <Check size={16} />
              <span>50 páginas grátis por mês • Sem cartão de crédito</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div className="container">
          <h2 className="section-title" data-testid="features-title">Por que escolher nosso conversor?</h2>
          <div className="features-grid">
            {features.map((feature, index) => (
              <div key={index} className="feature-card" data-testid={`feature-card-${index}`}>
                <div className="feature-icon">{feature.icon}</div>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Banks Section */}
      <section className="banks-section">
        <div className="container">
          <h2 className="section-title" data-testid="banks-title">Bancos Suportados</h2>
          <p className="section-subtitle">Otimizado para os principais bancos portugueses</p>
          <div className="banks-list">
            {supportedBanks.map((bank, index) => (
              <div key={index} className="bank-card" data-testid={`bank-card-${index}`}>
                <Shield size={24} />
                <span>{bank}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="container">
          <div className="cta-content">
            <h2 data-testid="cta-title">Pronto para simplificar sua contabilidade?</h2>
            <p data-testid="cta-subtitle">Comece agora com 50 páginas grátis por mês</p>
            <Button 
              size="lg" 
              onClick={() => navigate(user ? '/dashboard' : '/register')}
              data-testid="cta-btn"
            >
              Começar Agora
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="container">
          <p>© 2025 Conversor Bancário PT. Todos os direitos reservados.</p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;