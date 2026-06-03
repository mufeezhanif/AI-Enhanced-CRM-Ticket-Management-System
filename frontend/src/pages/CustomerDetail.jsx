import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Layout from '../components/Layout';
import LoadingSpinner from '../components/LoadingSpinner';
import { StatusBadge, PriorityBadge } from '../components/StatusBadge';
import api from '../services/api';

export default function CustomerDetail() {
  const { id } = useParams();

  const { data: customer, isLoading } = useQuery({
    queryKey: ['customer', id],
    queryFn: () => api.get(`/customers/${id}`).then((r) => r.data),
  });

  const { data: tickets } = useQuery({
    queryKey: ['customer-tickets', id],
    queryFn: () => api.get(`/customers/${id}/tickets`).then((r) => r.data),
    enabled: !!id,
  });

  if (isLoading) return <Layout title="Customer"><LoadingSpinner /></Layout>;
  if (!customer) return <Layout title="Customer"><p>Customer not found</p></Layout>;

  return (
    <Layout title={customer.full_name}>
      <nav className="text-sm text-gray-500 mb-4">
        <Link to="/dashboard" className="hover:text-blue-600">Home</Link>
        {' > '}
        <Link to="/customers" className="hover:text-blue-600">Customers</Link>
        {' > '}
        <span className="text-gray-900">{customer.full_name}</span>
      </nav>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border p-4">
          <p className="text-sm text-gray-500">Total Tickets</p>
          <p className="text-2xl font-bold">{customer.ticket_count ?? 0}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-sm text-gray-500">Open Tickets</p>
          <p className="text-2xl font-bold text-blue-600">{customer.open_tickets ?? 0}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-sm text-gray-500">Last Ticket</p>
          <p className="text-lg font-medium">
            {customer.last_ticket_date
              ? new Date(customer.last_ticket_date).toLocaleDateString()
              : '—'}
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl border p-6 mb-6">
        <h3 className="font-semibold mb-4">Customer Info</h3>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div><dt className="text-gray-500">Email</dt><dd>{customer.email}</dd></div>
          <div><dt className="text-gray-500">Phone</dt><dd>{customer.phone || '—'}</dd></div>
          <div><dt className="text-gray-500">Company</dt><dd>{customer.company || '—'}</dd></div>
          <div><dt className="text-gray-500">Agent</dt><dd>{customer.assigned_agent?.name || '—'}</dd></div>
          {customer.notes && (
            <div className="sm:col-span-2"><dt className="text-gray-500">Notes</dt><dd>{customer.notes}</dd></div>
          )}
        </dl>
      </div>

      <div className="bg-white rounded-xl border p-6">
        <h3 className="font-semibold mb-4">Tickets</h3>
        {tickets?.length === 0 ? (
          <p className="text-gray-500 text-sm">No tickets yet</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-gray-500 border-b">
              <tr>
                <th className="text-left pb-2">Title</th>
                <th>Status</th>
                <th>Priority</th>
              </tr>
            </thead>
            <tbody>
              {tickets?.map((t) => (
                <tr key={t.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="py-2">
                    <Link to={`/tickets/${t.id}`} className="text-blue-600 hover:underline">
                      {t.title}
                    </Link>
                  </td>
                  <td><StatusBadge status={t.status} /></td>
                  <td><PriorityBadge priority={t.priority} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  );
}
