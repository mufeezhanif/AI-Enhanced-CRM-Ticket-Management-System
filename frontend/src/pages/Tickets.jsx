import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import Layout from '../components/Layout';
import LoadingSpinner from '../components/LoadingSpinner';
import Pagination from '../components/Pagination';
import { StatusBadge, PriorityBadge, SentimentBadge } from '../components/StatusBadge';
import api from '../services/api';

export default function Tickets() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const page = Number(params.get('page') || 1);
  const status = params.get('status') || '';
  const priority = params.get('priority') || '';
  const search = params.get('search') || '';

  const setFilter = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.set('page', '1');
    setParams(next);
  };

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['tickets', page, status, priority, search],
    queryFn: () =>
      api
        .get('/tickets', {
          params: {
            page,
            size: 20,
            status: status || undefined,
            priority: priority || undefined,
            search: search || undefined,
          },
        })
        .then((r) => r.data),
  });

  return (
    <Layout title="Tickets">
      <div className="flex flex-col lg:flex-row gap-4 justify-between mb-4">
        <div className="flex flex-wrap gap-2">
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={status}
            onChange={(e) => setFilter('status', e.target.value)}
          >
            <option value="">All Status</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={priority}
            onChange={(e) => setFilter('priority', e.target.value)}
          >
            <option value="">All Priority</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <input
            placeholder="Search tickets..."
            className="border rounded-lg px-3 py-2 text-sm"
            value={search}
            onChange={(e) => setFilter('search', e.target.value)}
          />
        </div>
        <Link
          to="/tickets/new"
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 self-start"
        >
          <Plus size={18} /> New Ticket
        </Link>
      </div>

      {isLoading && <LoadingSpinner />}
      {error && (
        <div className="text-center py-8">
          <p className="text-red-600">Failed to load tickets</p>
          <button onClick={() => refetch()} className="mt-2 text-blue-600 underline">Retry</button>
        </div>
      )}

      {data && (
        <div className="bg-white rounded-xl border overflow-x-auto">
          <table className="w-full text-sm min-w-[800px]">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="text-left p-3">ID</th>
                <th className="text-left p-3">Title</th>
                <th className="text-left p-3">Customer</th>
                <th className="text-left p-3">Status</th>
                <th className="text-left p-3">Priority</th>
                <th className="text-left p-3">Sentiment</th>
                <th className="text-left p-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((t) => (
                <tr
                  key={t.id}
                  className="border-t hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/tickets/${t.id}`)}
                >
                  <td className="p-3 font-mono text-xs">{String(t.id).slice(0, 8)}</td>
                  <td className="p-3 font-medium">{t.title}</td>
                  <td className="p-3">{t.customer?.full_name || '—'}</td>
                  <td className="p-3"><StatusBadge status={t.status} /></td>
                  <td className="p-3"><PriorityBadge priority={t.priority} /></td>
                  <td className="p-3"><SentimentBadge sentiment={t.ai_sentiment} /></td>
                  <td className="p-3 text-gray-500">
                    {new Date(t.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="p-4">
            <Pagination
              page={page}
              size={20}
              total={data.total}
              onPageChange={(p) => {
                const next = new URLSearchParams(params);
                next.set('page', String(p));
                setParams(next);
              }}
            />
          </div>
        </div>
      )}
    </Layout>
  );
}
