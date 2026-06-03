import { useEffect, useState } from 'react';
import api from '../services/api';
import { useAuth } from '../store/authStore';

export default function CustomerModal({ customer, onClose, onSaved }) {
  const { user } = useAuth();
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    company: '',
    notes: '',
    assigned_agent_id: '',
  });
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (customer) {
      setForm({
        full_name: customer.full_name || '',
        email: customer.email || '',
        phone: customer.phone || '',
        company: customer.company || '',
        notes: customer.notes || '',
        assigned_agent_id: customer.assigned_agent_id || '',
      });
    }
    if (user?.role === 'manager') {
      api.get('/users').then((res) => {
        setAgents(res.data.filter((u) => u.role === 'agent' && u.is_active));
      });
    }
  }, [customer, user]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.full_name || !form.email) {
      setError('Name and email are required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const payload = { ...form };
      if (!payload.assigned_agent_id) delete payload.assigned_agent_id;
      if (customer) {
        await api.patch(`/customers/${customer.id}`, payload);
      } else {
        await api.post('/customers', payload);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save customer');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">
          {customer ? 'Edit Customer' : 'Add Customer'}
        </h3>
        {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
            <input
              className="w-full border rounded-lg px-3 py-2"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              type="email"
              className="w-full border rounded-lg px-3 py-2"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
            <input
              className="w-full border rounded-lg px-3 py-2"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
            <input
              className="w-full border rounded-lg px-3 py-2"
              value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              className="w-full border rounded-lg px-3 py-2"
              rows={3}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </div>
          {user?.role === 'manager' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Assign to Agent</label>
              <select
                className="w-full border rounded-lg px-3 py-2"
                value={form.assigned_agent_id}
                onChange={(e) => setForm({ ...form, assigned_agent_id: e.target.value })}
              >
                <option value="">Unassigned</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg">
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
