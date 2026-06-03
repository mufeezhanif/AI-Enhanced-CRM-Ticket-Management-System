import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import Layout from '../components/Layout';
import LoadingSpinner from '../components/LoadingSpinner';
import { PriorityBadge, StatusBadge } from '../components/StatusBadge';
import api from '../services/api';
import { useAuth } from '../store/authStore';

const STATUS_COLORS = { open: '#3b82f6', in_progress: '#eab308', resolved: '#22c55e', closed: '#9ca3af' };

export default function Dashboard() {
  const { user } = useAuth();

  const { data: stats, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.get('/dashboard/stats').then((r) => r.data),
  });

  const { data: workloads } = useQuery({
    queryKey: ['agent-workloads'],
    queryFn: () => api.get('/dashboard/agent-workloads').then((r) => r.data),
    enabled: user?.role === 'manager',
  });

  const { data: recentTickets } = useQuery({
    queryKey: ['recent-tickets'],
    queryFn: () =>
      api.get('/tickets', { params: { size: 5, sort_order: 'desc' } }).then((r) => r.data.items),
  });

  if (isLoading) return <Layout title="Dashboard"><LoadingSpinner /></Layout>;
  if (error)
    return (
      <Layout title="Dashboard">
        <div className="text-center py-12">
          <p className="text-red-600">Failed to load dashboard</p>
          <button onClick={() => refetch()} className="mt-2 text-blue-600 underline">
            Retry
          </button>
        </div>
      </Layout>
    );

  const statusData = Object.entries(stats.tickets_by_status || {}).map(([name, value]) => ({
    name: name.replace('_', ' '),
    value,
    fill: STATUS_COLORS[name] || '#6b7280',
  }));

  const priorityData = Object.entries(stats.tickets_by_priority || {}).map(([name, value]) => ({
    name,
    count: value,
  }));

  const cards = [
    { label: 'Open Tickets', value: stats.total_open, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Resolved Today', value: stats.resolved_today, color: 'text-green-600', bg: 'bg-green-50' },
    { label: 'Critical Tickets', value: stats.critical_tickets, color: 'text-red-600', bg: 'bg-red-50' },
    { label: 'Total Customers', value: stats.total_customers, color: 'text-gray-600', bg: 'bg-gray-50' },
  ];

  return (
    <Layout title="Dashboard">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {cards.map((c) => (
          <div key={c.label} className={`${c.bg} rounded-xl p-5 border border-gray-100`}>
            <p className="text-sm text-gray-600">{c.label}</p>
            <p className={`text-3xl font-bold mt-1 ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-xl border p-5">
          <h3 className="font-semibold mb-4">Tickets by Status</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                {statusData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-white rounded-xl border p-5">
          <h3 className="font-semibold mb-4">Tickets by Priority</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={priorityData}>
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {user?.role === 'manager' && workloads && (
        <div className="bg-white rounded-xl border p-5 mb-6">
          <h3 className="font-semibold mb-4">Agent Workload</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-2">Agent</th>
                <th>Total</th>
                <th>Open</th>
                <th>In Progress</th>
                <th>Resolved This Week</th>
              </tr>
            </thead>
            <tbody>
              {workloads.map((w) => (
                <tr key={w.agent_id} className="border-b last:border-0">
                  <td className="py-2 font-medium">{w.agent_name}</td>
                  <td>{w.total}</td>
                  <td>{w.open}</td>
                  <td>{w.in_progress}</td>
                  <td>{w.resolved_this_week}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="bg-white rounded-xl border p-5">
        <h3 className="font-semibold mb-4">
          {user?.role === 'manager' ? 'Recent Tickets' : 'My Recent Tickets'}
        </h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="pb-2">Title</th>
              <th>Status</th>
              <th>Priority</th>
            </tr>
          </thead>
          <tbody>
            {recentTickets?.map((t) => (
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
      </div>
    </Layout>
  );
}
