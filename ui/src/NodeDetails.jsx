import { X, GitCommit, Clock, CheckCircle2, AlertCircle } from 'lucide-react';

const statusConfig = {
  current: { color: 'text-emerald-400', icon: CheckCircle2, label: 'Current' },
  stale: { color: 'text-amber-400', icon: Clock, label: 'Stale' },
  new: { color: 'text-blue-400', icon: AlertCircle, label: 'New' }
};

export default function NodeDetails({ data, onClose }) {
  if (!data) return null;

  const config = statusConfig[data.status] || statusConfig.new;
  const Icon = config.icon;

  return (
    <div className="sidebar details-panel slide-in">
      <div className="panel-header">
        <div className="panel-title">
          <h2>{data.id}</h2>
          <button onClick={onClose} className="close-btn">
            <X size={20} />
          </button>
        </div>
        
        <div className="panel-meta">
          <span className={`meta-badge ${config.color} bg-opacity-20`}>
            <Icon size={14} className="mr-1" />
            {config.label}
          </span>
          <span className="meta-badge text-gray-400 bg-gray-800">
            <GitCommit size={14} className="mr-1" />
            v{data.version}
          </span>
          <span className="meta-badge text-purple-400 bg-purple-900/30">
            {data.approval_status.toUpperCase()}
          </span>
        </div>
        
        {data.cascade_depth > 0 && (
            <div className="cascade-warning">
                <strong>Impact Warning:</strong> Changing this spec will trigger a rebuild cascade depth of {data.cascade_depth} downstream nodes.
            </div>
        )}
      </div>

      <div className="panel-content">
        <div className="content-section">
          <h3>Markdown Source</h3>
          <div className="markdown-viewer">
            <pre>
              <code>{data.content}</code>
            </pre>
          </div>
        </div>

        {data.depends_on && data.depends_on.length > 0 && (
          <div className="content-section mt-6">
            <h3>Depends On</h3>
            <ul className="deps-list">
              {data.depends_on.map(dep => (
                <li key={dep}>{dep}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
