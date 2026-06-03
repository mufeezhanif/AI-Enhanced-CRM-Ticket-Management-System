import { useState, useRef } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import Layout from '../components/Layout';
import LoadingSpinner from '../components/LoadingSpinner';
import Badge from '../components/Badge';
import { StatusBadge, PriorityBadge, SentimentBadge } from '../components/StatusBadge';
import api from '../services/api';
import { useAuth } from '../store/authStore';

export default function TicketDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [comment, setComment] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const pollCount = useRef(0);

  const { data: ticket, isLoading, refetch } = useQuery({
    queryKey: ['ticket', id],
    queryFn: () => api.get(`/tickets/${id}`).then((r) => r.data),
    refetchInterval: (query) => {
      const t = query.state.data;
      if (!t?.ai_category && pollCount.current < 6) {
        pollCount.current += 1;
        return 5000;
      }
      return false;
    },
  });

  const { data: comments, refetch: refetchComments } = useQuery({
    queryKey: ['ticket-comments', id],
    queryFn: () => api.get(`/tickets/${id}/comments`).then((r) => r.data),
  });

  const { data: notifications } = useQuery({
    queryKey: ['ticket-notifications', id],
    queryFn: () => api.get(`/tickets/${id}/notifications`).then((r) => r.data),
    enabled: user?.role === 'manager' && showNotifications,
  });

  const updateTicket = async (fields) => {
    try {
      await api.patch(`/tickets/${id}`, fields);
      queryClient.invalidateQueries({ queryKey: ['ticket', id] });
      toast.success('Ticket updated');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Update failed');
    }
  };

  const sendComment = async (e) => {
    e.preventDefault();
    if (!comment.trim()) return;
    try {
      await api.post(`/tickets/${id}/comments`, { message: comment, is_internal: isInternal });
      setComment('');
      refetchComments();
      toast.success('Comment added');
    } catch {
      toast.error('Failed to add comment');
    }
  };

  const rerunAI = async () => {
    await api.post(`/tickets/${id}/analyze`);
    toast.success('AI analysis started');
    pollCount.current = 0;
    refetch();
  };

  if (isLoading) return <Layout title="Ticket"><LoadingSpinner /></Layout>;
  if (!ticket) return <Layout title="Ticket"><p>Not found</p></Layout>;

  return (
    <Layout title={ticket.title}>
      <nav className="text-sm text-gray-500 mb-4">
        <Link to="/tickets" className="hover:text-blue-600">Tickets</Link>
        {' > '}
        <span>{ticket.title}</span>
      </nav>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl border p-6">
            <div className="flex flex-wrap gap-4 justify-between mb-4">
              <div className="flex gap-2">
                <select
                  className="border rounded-lg px-2 py-1 text-sm"
                  value={ticket.status}
                  onChange={(e) => updateTicket({ status: e.target.value })}
                >
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="resolved">Resolved</option>
                  <option value="closed">Closed</option>
                </select>
                <select
                  className="border rounded-lg px-2 py-1 text-sm"
                  value={ticket.priority}
                  onChange={(e) => updateTicket({ priority: e.target.value })}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => updateTicket({ status: 'resolved' })}
                  className="text-sm px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Mark Resolved
                </button>
                <button
                  onClick={() => updateTicket({ priority: 'critical' })}
                  className="text-sm px-3 py-1 bg-red-600 text-white rounded-lg hover:bg-red-700"
                >
                  Escalate
                </button>
                <button
                  onClick={rerunAI}
                  className="text-sm px-3 py-1 border rounded-lg hover:bg-gray-50 flex items-center gap-1"
                >
                  <Sparkles size={14} /> Re-run AI
                </button>
              </div>
            </div>
            <p className="text-gray-700 whitespace-pre-wrap">{ticket.description}</p>
            <div className="mt-4 flex gap-2">
              <StatusBadge status={ticket.status} />
              <PriorityBadge priority={ticket.priority} />
              {ticket.category && <Badge variant="info" text={ticket.category} />}
            </div>
          </div>

          <div className="bg-white rounded-xl border p-6">
            <h3 className="font-semibold mb-4">Activity</h3>
            <div className="space-y-4 mb-4 max-h-96 overflow-y-auto">
              {comments?.map((c) => (
                <div
                  key={c.id}
                  className={`p-3 rounded-lg ${c.is_internal ? 'bg-yellow-50 border border-yellow-200' : 'bg-gray-50'}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="w-8 h-8 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-bold">
                      {c.agent?.name?.charAt(0) || '?'}
                    </span>
                    <span className="font-medium text-sm">{c.agent?.name}</span>
                    <span className="text-xs px-1.5 py-0.5 bg-gray-200 rounded capitalize">{c.agent?.role}</span>
                    {c.is_internal && <span className="text-xs text-yellow-700">Internal</span>}
                    <span className="text-xs text-gray-400 ml-auto">
                      {new Date(c.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 ml-10">{c.message}</p>
                </div>
              ))}
            </div>
            <form onSubmit={sendComment} className="border-t pt-4">
              <textarea
                className="w-full border rounded-lg px-3 py-2 text-sm"
                rows={3}
                placeholder="Add a comment..."
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
              <div className="flex items-center justify-between mt-2">
                <label className="flex items-center gap-2 text-sm text-gray-600">
                  <input
                    type="checkbox"
                    checked={isInternal}
                    onChange={(e) => setIsInternal(e.target.checked)}
                  />
                  Internal note
                </label>
                <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
                  Send
                </button>
              </div>
            </form>
          </div>
        </div>

        <div className="space-y-6">
          {ticket.customer && (
            <div className="bg-white rounded-xl border p-5">
              <h3 className="font-semibold mb-3">Customer</h3>
              <Link to={`/customers/${ticket.customer_id}`} className="text-blue-600 hover:underline font-medium">
                {ticket.customer.full_name}
              </Link>
              <p className="text-sm text-gray-500 mt-1">{ticket.customer.email}</p>
            </div>
          )}

          <div className="bg-white rounded-xl border p-5">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Sparkles size={18} className="text-purple-600" /> AI Analysis
            </h3>
            <div className="space-y-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">AI Category</p>
                {ticket.ai_category ? (
                  <Badge variant="info" text={ticket.ai_category} />
                ) : (
                  <span className="text-sm text-gray-400 flex items-center gap-2">
                    <span className="h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                    Analyzing...
                  </span>
                )}
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Customer Sentiment</p>
                {ticket.ai_sentiment ? (
                  <>
                    <SentimentBadge sentiment={ticket.ai_sentiment} />
                    {ticket.ai_sentiment_score != null && (
                      <p className="text-xs text-gray-500 mt-1">
                        Confidence: {Math.round(ticket.ai_sentiment_score * 100)}%
                      </p>
                    )}
                  </>
                ) : (
                  <span className="text-sm text-gray-400">Pending...</span>
                )}
              </div>
              {ticket.status === 'resolved' && ticket.ai_summary && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Resolution Summary (AI Generated)</p>
                  <p className="text-sm italic text-gray-700">{ticket.ai_summary}</p>
                </div>
              )}
            </div>
          </div>

          {user?.role === 'manager' && (
            <div className="bg-white rounded-xl border p-5">
              <button
                className="flex items-center gap-2 text-sm font-medium w-full"
                onClick={() => setShowNotifications(!showNotifications)}
              >
                {showNotifications ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                Notification Log
              </button>
              {showNotifications && notifications && (
                <table className="w-full text-xs mt-3">
                  <thead>
                    <tr className="text-gray-500">
                      <th className="text-left pb-1">Platform</th>
                      <th>Status</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {notifications.map((n) => (
                      <tr key={n.id} className="border-t">
                        <td className="py-1 capitalize">{n.platform}</td>
                        <td>
                          <span className={n.status === 'sent' ? 'text-green-600' : n.status === 'skipped' ? 'text-gray-500' : 'text-red-600'}>
                            {n.status}
                          </span>
                        </td>
                        <td>{new Date(n.sent_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
