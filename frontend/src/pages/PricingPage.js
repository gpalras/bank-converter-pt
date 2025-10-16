import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { toast } from 'sonner';
import { FileText, Check } from 'lucide-react';
import '../styles/PricingPage.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PricingPage = ({ user }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState({});

  const plans = [
    {
      id: 'free',
      name: 'Grátis',
      price: 0,
      pages: 50,
      features: [
        '50 páginas por mês',
        'Suporte para BPI, Millennium e Caixa Geral',
        'Exportação CSV e Excel',
        'Categorização fiscal básica'
      ],
      current: true
    },
    {
      id: 'starter',
      name: 'Inicial',
      price: 30,
      pages: 400,
      features: [
        '400 páginas por mês',
        'Suporte para todos os bancos',
        'Exportação CSV e Excel',
        'Categorização fiscal avançada',
        'Suporte prioritário'
      ],
      popular: true
    },
    {
      id: 'pro',
      name: 'Profissional',
      price: 99,
      pages: 4000,
      features: [
        '4.000 páginas por mês',
        'Suporte para todos os bancos',
        'Exportação CSV e Excel',
        'Categorização fiscal completa',
        'Suporte prioritário 24/7',
        'API de integração'
      ]
    }
  ];

  const handleSubscribe = async (planId) => {
    if (!user) {
      navigate('/register');
      return;
    }

    if (planId === 'free') {
      toast.info('Você já está no plano gratuito');
      return;
    }

    setLoading({ [planId]: true });

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API}/payments/checkout/session`,
        {
          plan_type: planId,
          origin_url: window.location.origin
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      window.location.href = response.data.url;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao processar pagamento');
      setLoading({});
    }
  };

  return (
    <div className="pricing-page" data-testid="pricing-page">
      {/* Header */}
      <header className="pricing-header">
        <div className="pricing-container">
          <div className="header-content">
            <div className="logo" onClick={() => navigate('/')} data-testid="logo-link">
              <FileText size={28} />
              <span>Conversor Bancário PT</span>
            </div>
            <nav className="nav-menu">
              {user ? (
                <Button onClick={() => navigate('/dashboard')} data-testid="dashboard-btn">Painel</Button>
              ) : (
                <>
                  <Button variant="ghost" onClick={() => navigate('/login')} data-testid="login-btn">Entrar</Button>
                  <Button onClick={() => navigate('/register')} data-testid="register-btn">Criar Conta</Button>
                </>
              )}
            </nav>
          </div>
        </div>
      </header>

      <div className="pricing-container">
        <div className="pricing-content">
          <div className="pricing-hero">
            <h1 className="pricing-title" data-testid="pricing-title">
              Escolha o plano ideal para você
            </h1>
            <p className="pricing-subtitle" data-testid="pricing-subtitle">
              Comece grátis e faça upgrade quando precisar de mais páginas
            </p>
          </div>

          <div className="plans-grid">
            {plans.map((plan) => (
              <Card
                key={plan.id}
                className={`plan-card ${plan.popular ? 'popular' : ''}`}
                data-testid={`plan-card-${plan.id}`}
              >
                {plan.popular && (
                  <div className="popular-badge" data-testid="popular-badge">Mais Popular</div>
                )}
                <CardHeader>
                  <CardTitle className="plan-name" data-testid={`plan-name-${plan.id}`}>{plan.name}</CardTitle>
                  <div className="plan-price" data-testid={`plan-price-${plan.id}`}>
                    <span className="price-amount">€{plan.price}</span>
                    {plan.price > 0 && <span className="price-period">/mês</span>}
                  </div>
                  <CardDescription className="plan-pages" data-testid={`plan-pages-${plan.id}`}>
                    {plan.pages} páginas por mês
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="features-list">
                    {plan.features.map((feature, index) => (
                      <li key={index} className="feature-item" data-testid={`feature-${plan.id}-${index}`}>
                        <Check size={18} />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="subscribe-btn"
                    variant={plan.popular ? 'default' : 'outline'}
                    onClick={() => handleSubscribe(plan.id)}
                    disabled={loading[plan.id]}
                    data-testid={`subscribe-btn-${plan.id}`}
                  >
                    {loading[plan.id] ? 'Processando...' : plan.id === 'free' ? 'Plano Atual' : 'Escolher Plano'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="pricing-faq">
            <h2 className="faq-title" data-testid="faq-title">Perguntas Frequentes</h2>
            <div className="faq-grid">
              <div className="faq-item" data-testid="faq-item-0">
                <h3>Como funciona o limite de páginas?</h3>
                <p>Cada PDF convertido consome páginas do seu limite mensal. O contador reinicia todo mês.</p>
              </div>
              <div className="faq-item" data-testid="faq-item-1">
                <h3>Posso cancelar a qualquer momento?</h3>
                <p>Sim! Você pode cancelar sua assinatura a qualquer momento e continuar usando até o fim do período pago.</p>
              </div>
              <div className="faq-item" data-testid="faq-item-2">
                <h3>Meus dados estão seguros?</h3>
                <p>Sim. Todos os arquivos são processados com criptografia e excluídos após 30 dias.</p>
              </div>
              <div className="faq-item" data-testid="faq-item-3">
                <h3>Que bancos são suportados?</h3>
                <p>Atualmente suportamos BPI, Millennium BCP e Caixa Geral de Depósitos. Mais bancos em breve!</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="pricing-footer">
        <div className="pricing-container">
          <p>© 2025 Conversor Bancário PT. Todos os direitos reservados.</p>
        </div>
      </footer>
    </div>
  );
};

export default PricingPage;