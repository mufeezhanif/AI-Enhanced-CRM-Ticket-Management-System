import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import Layout from '../components/Layout';
import LoadingSpinner from '../components/LoadingSpinner';
import Badge from '../components/Badge';
import api from '../services/api';
import { useAuth } from '../store/authStore';

export default function Users() {
  const { user: currentUser } = useAuth();
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'agent' });

  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.get('/users').then((r) => r.data),
  });

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post('/auth/register', form);
      toast.success('User created');
      setModalOpen(false);
      setForm({ name: '', email: '', password: '', role: 'agent' });
      queryClient.invalidateQueries({ queryKey: ['users'] });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create user');
    }
  };

  const deactivate = async (id) => {
    if (id === currentUser.id) {
      toast.error('Cannot deactivate yourself');
      return;
    }
    try {
      await api.delete(`/users/${id}`);
      toast.success('User deactivated');
      queryClient.invalidateQueries({ queryKey: ['users'] });
    } catch {
      toast.error('Failed to deactivate user');
    }
  };

  return (
    <Layout title="Users">
      <div className="flex justify-end mb-4">
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          <Plus size={18} /> Add Agent
        </button>
      </div>

      {isLoading && <LoadingSpinner />}

      {users && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="text-left p-3">Name</th>
                <th className="text-left p-3">Email</th>
                <th className="text-left p-3">Role</th>
                <th className="text-left p-3">Status</th>
                <th className="text-left p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t">
                  <td className="p-3 font-medium">{u.name}</td>
                  <td className="p-3">{u.email}</td>
                  <td className="p-3">
                    <Badge variant={u.role === 'manager' ? 'info' : 'default'} text={u.role} />
                  </td>
                  <td className="p-3">
                    <Badge variant={u.is_active ? 'success' : 'danger'} text={u.is_active ? 'Active' : 'Inactive'} />
                  </td>
                  <td className="p-3">
                    {u.id !== currentUser.id && u.is_active && (
                      <button
                        onClick={() => deactivate(u.id)}
                        className="text-red-600 text-xs hover:underline"
                      >
                        Deactivate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="font-semibold mb-4">Add User</h3>
            <form onSubmit={handleCreate} className="space-y-3">
              <input
                placeholder="Name"
                className="w-full border rounded-lg px-3 py-2"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
              <input
                type="email"
                placeholder="Email"
                className="w-full border rounded-lg px-3 py-2"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
              <input
                type="password"
                placeholder="Password"
                className="w-full border rounded-lg px-3 py-2"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required
              />
              <select
                className="w-full border rounded-lg px-3 py-2"
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
              >
                <option value="agent">Agent</option>
                <option value="manager">Manager</option>
              </select>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setModalOpen(false)} className="px-4 py-2 text-gray-600">
                  Cancel
                </button>
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg">
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  );
}
