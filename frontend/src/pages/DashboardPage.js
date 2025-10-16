import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { FileText, Upload, Download, LogOut, CreditCard, FileSpreadsheet } from 'lucide-react';
import '../styles/Dashboard.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DashboardPage = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const [subscription, setSubscription] = useState(null);
  const [conversions, setConversions] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [selectedBank, setSelectedBank] = useState('Millennium');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [subResponse, convResponse] = await Promise.all([
        axios.get(`${API}/subscriptions/current`, { headers }),
        axios.get(`${API}/conversions`, { headers })
      ]);

      setSubscription(subResponse.data);
      setConversions(convResponse.data);
    } catch (error) {
      toast.error('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.type !== 'application/pdf') {
      toast.error('Por favor, selecione um arquivo PDF');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API}/conversions/upload?bank_name=${selectedBank}`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      toast.success('Conversão concluída com sucesso!');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao processar arquivo');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleDownload = async (conversionId, format) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API}/conversions/${conversionId}/download/${format}`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `extrato.${format === 'csv' ? 'csv' : 'xlsx'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      toast.success('Download iniciado');
    } catch (error) {
      toast.error('Erro ao fazer download');
    }
  };

  const isFree = subscription?.plan_type === 'free';
const used = isFree ? (subscription?.conversions_used_this_month || 0)
                    : (subscription?.pages_used_this_month || 0);
const limit = isFree ? (subscription?.conversions_limit ?? 5)
                     : (subscription?.pages_limit || 0);
const usagePercentage = limit ? (used / limit) * 100 : 0;

  if (loading) {
    return <div className="loading-screen">Carregando...</div>;
  }

  return (
    <div className="dashboard-page" data-testid="dashboard-page">
      {/* Header */}
      <header className="dashboard-header">
        <div className="dashboard-container">
          <div className="header-content">
            <div className="logo" onClick={() => navigate('/')} data-testid="logo-link">
              <FileText size={28} />
              <span>Conversor Bancário PT</span>
            </div>
            <div className="header-actions">
              <span className="user-name" data-testid="user-name">Olá, {user.name}</span>
              <Button variant="ghost" onClick={onLogout} data-testid="logout-btn">
                <LogOut size={18} />
                Sair
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="dashboard-container">
        <div className="dashboard-content">
          {/* Subscription Card */}
          <Card className="subscription-card" data-testid="subscription-card">
            <CardHeader>
              <CardTitle>Plano Atual: {subscription?.plan_type === 'free' ? 'Gratuito' : subscription?.plan_type === 'starter' ? 'Inicial' : 'Profissional'}</CardTitle>
              <CardDescription>{isFree ? 'Utilizações gratuitas este mês' : 'Páginas utilizadas este mês'}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="usage-stats">
                <div className="usage-text" data-testid="usage-text">
                  <span className="usage-current">{used}</span>
                  <span className="usage-separator">/</span>
                  <span className="usage-limit">{limit}</span>
                  <span className="usage-label">{isFree ? 'utilizações' : 'páginas'}</span>
                </div>
                <Progress value={usagePercentage} className="usage-progress" data-testid="usage-progress" />
              </div>
              {subscription?.plan_type === 'free' && (
                <Button onClick={() => navigate('/pricing')} className="upgrade-btn" data-testid="upgrade-btn">
                  <CreditCard size={18} />
                  Fazer Upgrade
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Upload Card */}
          <Card className="upload-card" data-testid="upload-card">
            <CardHeader>
              <CardTitle>Converter Extrato Bancário</CardTitle>
              <CardDescription>Faça upload do seu PDF e selecione o banco</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="upload-content">
                <div className="bank-select-group">
                  <label>Selecione o banco:</label>
                  <Select value={selectedBank} onValueChange={setSelectedBank}>
                    <SelectTrigger data-testid="bank-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="BPI" data-testid="bank-option-bpi">BPI</SelectItem>
                      <SelectItem value="Millennium" data-testid="bank-option-millennium">Millennium BCP</SelectItem>
                      <SelectItem value="Caixa Geral" data-testid="bank-option-caixa">Caixa Geral de Depósitos</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <label htmlFor="file-upload" className="upload-area" data-testid="upload-area">
                  <input
                    id="file-upload"
                    type="file"
                    accept=".pdf"
                    onChange={handleFileUpload}
                    disabled={uploading}
                    style={{ display: 'none' }}
                    data-testid="file-input"
                  />
                  <Upload size={48} />
                  <p className="upload-text">
                    {uploading ? 'Processando...' : 'Clique para fazer upload do PDF'}
                  </p>
                  <p className="upload-hint">Apenas arquivos PDF</p>
                </label>
              </div>
            </CardContent>
          </Card>

          {/* Conversions History */}
          <Card className="conversions-card" data-testid="conversions-card">
            <CardHeader>
              <CardTitle>Histórico de Conversões</CardTitle>
              <CardDescription>Seus extratos convertidos</CardDescription>
            </CardHeader>
            <CardContent>
              {conversions.length === 0 ? (
                <p className="empty-state" data-testid="empty-state">Nenhuma conversão ainda. Faça upload do seu primeiro extrato!</p>
              ) : (
                <div className="conversions-list">
                  {conversions.map((conv) => (
                    <div key={conv.id} className="conversion-item" data-testid={`conversion-item-${conv.id}`}>
                      <div className="conversion-info">
                        <FileText size={24} />
                        <div>
                          <p className="conversion-name" data-testid={`conversion-name-${conv.id}`}>{conv.original_filename}</p>
                          <p className="conversion-meta" data-testid={`conversion-meta-${conv.id}`}>
                            {conv.bank_name} • {conv.pages_count} páginas • {new Date(conv.created_at).toLocaleDateString('pt-PT')}
                          </p>
                        </div>
                      </div>
                      {conv.status === 'completed' && (
                        <div className="conversion-actions">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDownload(conv.id, 'csv')}
                            data-testid={`download-csv-btn-${conv.id}`}
                          >
                            <Download size={16} />
                            CSV
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDownload(conv.id, 'excel')}
                            data-testid={`download-excel-btn-${conv.id}`}
                          >
                            <FileSpreadsheet size={16} />
                            Excel
                          </Button>
                        </div>
                      )}
                      {conv.status === 'processing' && (
                        <span className="status-badge processing" data-testid={`status-processing-${conv.id}`}>Processando...</span>
                      )}
                      {conv.status === 'failed' && (
                        <span className="status-badge failed" data-testid={`status-failed-${conv.id}`}>Falhou</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;