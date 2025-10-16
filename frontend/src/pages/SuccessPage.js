import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { CheckCircle, Loader } from 'lucide-react';
import { toast } from 'sonner';
import '../styles/SuccessPage.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SuccessPage = ({ user }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('checking');
  const [attempts, setAttempts] = useState(0);
  const maxAttempts = 5;

  useEffect(() => {
    const sessionId = searchParams.get('session_id');
    if (sessionId) {
      checkPaymentStatus(sessionId);
    } else {
      navigate('/dashboard');
    }
  }, [searchParams]);

  const checkPaymentStatus = async (sessionId, attemptCount = 0) => {
    if (attemptCount >= maxAttempts) {
      setStatus('timeout');
      toast.error('Tempo esgotado ao verificar pagamento. Verifique seu email.');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API}/payments/checkout/status/${sessionId}`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      if (response.data.payment_status === 'paid') {
        setStatus('success');
        toast.success('Pagamento confirmado! Sua assinatura foi ativada.');
      } else if (response.data.status === 'expired') {
        setStatus('failed');
        toast.error('Sessão de pagamento expirada.');
      } else {
        // Continue polling
        setAttempts(attemptCount + 1);
        setTimeout(() => checkPaymentStatus(sessionId, attemptCount + 1), 2000);
      }
    } catch (error) {
      setStatus('failed');
      toast.error('Erro ao verificar pagamento.');
    }
  };

  return (
    <div className="success-page" data-testid="success-page">
      <div className="success-container">
        <Card className="success-card">
          <CardHeader>
            {status === 'checking' && (
              <>
                <div className="status-icon checking" data-testid="status-checking">
                  <Loader size={48} className="spinning" />
                </div>
                <CardTitle>Verificando Pagamento...</CardTitle>
                <CardDescription>Por favor, aguarde enquanto confirmamos seu pagamento</CardDescription>
              </>
            )}
            {status === 'success' && (
              <>
                <div className="status-icon success" data-testid="status-success">
                  <CheckCircle size={48} />
                </div>
                <CardTitle>Pagamento Confirmado!</CardTitle>
                <CardDescription>Sua assinatura foi ativada com sucesso</CardDescription>
              </>
            )}
            {status === 'failed' && (
              <>
                <div className="status-icon failed" data-testid="status-failed">
                  <CheckCircle size={48} />
                </div>
                <CardTitle>Pagamento Não Confirmado</CardTitle>
                <CardDescription>Houve um problema ao processar seu pagamento</CardDescription>
              </>
            )}
            {status === 'timeout' && (
              <>
                <div className="status-icon timeout" data-testid="status-timeout">
                  <CheckCircle size={48} />
                </div>
                <CardTitle>Verificação em Andamento</CardTitle>
                <CardDescription>A verificação está demorando. Verifique seu email para confirmação.</CardDescription>
              </>
            )}
          </CardHeader>
          <CardContent>
            <div className="success-actions">
              {status === 'success' && (
                <Button onClick={() => navigate('/dashboard')} size="lg" data-testid="go-dashboard-btn">
                  Ir para o Painel
                </Button>
              )}
              {(status === 'failed' || status === 'timeout') && (
                <>
                  <Button onClick={() => navigate('/pricing')} size="lg" data-testid="retry-btn">
                    Tentar Novamente
                  </Button>
                  <Button onClick={() => navigate('/dashboard')} variant="outline" size="lg" data-testid="back-dashboard-btn">
                    Voltar ao Painel
                  </Button>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default SuccessPage;