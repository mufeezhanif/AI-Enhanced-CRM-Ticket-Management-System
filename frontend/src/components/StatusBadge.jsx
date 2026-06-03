import Badge from './Badge';

const statusMap = {
  open: { variant: 'info', text: 'Open' },
  in_progress: { variant: 'warning', text: 'In Progress' },
  resolved: { variant: 'success', text: 'Resolved' },
  closed: { variant: 'default', text: 'Closed' },
};

const priorityMap = {
  low: { variant: 'default', text: 'Low' },
  medium: { variant: 'info', text: 'Medium' },
  high: { variant: 'warning', text: 'High' },
  critical: { variant: 'danger', text: 'Critical' },
};

const sentimentMap = {
  positive: { variant: 'success', text: '😊 Positive' },
  neutral: { variant: 'default', text: '😐 Neutral' },
  negative: { variant: 'warning', text: '😟 Negative' },
  frustrated: { variant: 'danger', text: '😤 Frustrated' },
};

export function StatusBadge({ status }) {
  const cfg = statusMap[status] || { variant: 'default', text: status };
  return <Badge variant={cfg.variant} text={cfg.text} />;
}

export function PriorityBadge({ priority }) {
  const cfg = priorityMap[priority] || { variant: 'default', text: priority };
  return <Badge variant={cfg.variant} text={cfg.text} />;
}

export function SentimentBadge({ sentiment }) {
  if (!sentiment) return <span className="text-gray-400 text-xs">—</span>;
  const cfg = sentimentMap[sentiment] || { variant: 'default', text: sentiment };
  return <Badge variant={cfg.variant} text={cfg.text} />;
}
