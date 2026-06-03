import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import Layout from '../components/Layout';
import api from '../services/api';
import { useAuth } from '../store/authStore';

export default function CreateTicket() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [customers, setCustomers] = useState([]);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    title: '',
    description: '',
    priority: 'medium',
    customer_id: '',
    category: '',
    assigned_agent_id: '',
  });

  useEffect(() => {
    api.get('/customers', { params: { size: 100 } }).then((r) => setCustomers(r.data.items));
    if (user?.role === 'manager') {
      api.get('/users').then((r) => setAgents(r.data.filter((u) => u.role === 'agent')));
    }
  }, [user]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = { ...form };
      if (!payload.category) delete payload.category;
      if (!payload.assigned_agent_id) delete payload.assigned_agent_id;
      const { data } = await api.post('/tickets', payload);
      toast.success('Ticket created! AI is analyzing...');
      setTimeout(() => navigate(`/tickets/${data.id}`), 1000);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create ticket');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout title="New Ticket">
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border p-6 max-w-2xl space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Customer *</label>
          <select
            className="w-full border rounded-lg px-3 py-2"
            value={form.customer_id}
            onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
            required
          >
            <option value="">Select customer</option>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>{c.full_name} ({c.email})</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Title *</label>
          <input
            className="w-full border rounded-lg px-3 py-2"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Description *</label>
          <textarea
            className="w-full border rounded-lg px-3 py-2"
            rows={5}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Priority</label>
          <select
            className="w-full border rounded-lg px-3 py-2"
            value={form.priority}
            onChange={(e) => setForm({ ...form, priority: e.target.value })}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Category (optional)</label>
          <input
            className="w-full border rounded-lg px-3 py-2"
            placeholder="AI will auto-fill if left empty"
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
          />
        </div>
        {user?.role === 'manager' && (
          <div>
            <label className="block text-sm font-medium mb-1">Assign to Agent</label>
            <select
              className="w-full border rounded-lg px-3 py-2"
              value={form.assigned_agent_id}
              onChange={(e) => setForm({ ...form, assigned_agent_id: e.target.value })}
            >
              <option value="">Auto-assign</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
        )}
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Creating...' : 'Create Ticket'}
        </button>
      </form>
    </Layout>
  );
}
