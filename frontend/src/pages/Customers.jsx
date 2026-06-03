import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Eye, Pencil, Trash2, Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import Layout from '../components/Layout';
import LoadingSpinner from '../components/LoadingSpinner';
import Pagination from '../components/Pagination';
import CustomerModal from '../components/CustomerModal';
import ConfirmModal from '../components/ConfirmModal';
import api from '../services/api';
import { useAuth } from '../store/authStore';

export default function Customers() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editCustomer, setEditCustomer] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['customers', page, debouncedSearch],
    queryFn: () =>
      api
        .get('/customers', { params: { page, size: 20, search: debouncedSearch || undefined } })
        .then((r) => r.data),
  });

  const handleDelete = async () => {
    try {
      await api.delete(`/customers/${deleteTarget.id}`);
      toast.success('Customer deleted');
      queryClient.invalidateQueries({ queryKey: ['customers'] });
    } catch {
      toast.error('Failed to delete customer');
    }
    setDeleteTarget(null);
  };

  return (
    <Layout title="Customers">
      <div className="flex flex-col sm:flex-row gap-4 justify-between mb-4">
        <input
          placeholder="Search customers..."
          className="border rounded-lg px-3 py-2 w-full sm:w-80"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
        <button
          onClick={() => { setEditCustomer(null); setModalOpen(true); }}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          <Plus size={18} /> Add Customer
        </button>
      </div>

      {isLoading && <LoadingSpinner />}
      {error && (
        <div className="text-center py-8">
          <p className="text-red-600">Failed to load customers</p>
          <button onClick={() => refetch()} className="mt-2 text-blue-600 underline">Retry</button>
        </div>
      )}

      {data && (
        <div className="bg-white rounded-xl border overflow-hidden">
          {data.items.length === 0 ? (
            <p className="text-center py-12 text-gray-500">No customers found</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="text-left p-3">Name</th>
                  <th className="text-left p-3 hidden md:table-cell">Email</th>
                  <th className="text-left p-3 hidden lg:table-cell">Company</th>
                  <th className="text-left p-3">Open Tickets</th>
                  <th className="text-left p-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((c) => (
                  <tr key={c.id} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-medium">{c.full_name}</td>
                    <td className="p-3 hidden md:table-cell text-gray-600">{c.email}</td>
                    <td className="p-3 hidden lg:table-cell">{c.company || '—'}</td>
                    <td className="p-3">{c.open_tickets ?? 0}</td>
                    <td className="p-3">
                      <div className="flex gap-2">
                        <Link to={`/customers/${c.id}`} className="p-1 text-blue-600 hover:bg-blue-50 rounded">
                          <Eye size={16} />
                        </Link>
                        <button
                          onClick={() => { setEditCustomer(c); setModalOpen(true); }}
                          className="p-1 text-gray-600 hover:bg-gray-100 rounded"
                        >
                          <Pencil size={16} />
                        </button>
                        {user?.role === 'manager' && (
                          <button
                            onClick={() => setDeleteTarget(c)}
                            className="p-1 text-red-600 hover:bg-red-50 rounded"
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="p-4">
            <Pagination page={page} size={20} total={data.total} onPageChange={setPage} />
          </div>
        </div>
      )}

      {modalOpen && (
        <CustomerModal
          customer={editCustomer}
          onClose={() => setModalOpen(false)}
          onSaved={() => {
            queryClient.invalidateQueries({ queryKey: ['customers'] });
            toast.success(editCustomer ? 'Customer updated' : 'Customer created');
          }}
        />
      )}
      {deleteTarget && (
        <ConfirmModal
          title="Delete Customer"
          message={`Delete ${deleteTarget.full_name}? This will also delete all their tickets.`}
          danger
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </Layout>
  );
}
