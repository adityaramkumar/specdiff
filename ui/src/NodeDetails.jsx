import { X, GitCommit, Clock, CheckCircle2, AlertCircle, BookOpen } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { motion } from 'framer-motion';
import 'highlight.js/styles/github-dark.css';

const MotionDiv = motion.div;
const statusConfig = {
  current: { color: 'text-emerald-400', icon: CheckCircle2, label: 'Current' },
  stale: { color: 'text-amber-400', icon: Clock, label: 'Stale' },
  new: { color: 'text-blue-400', icon: AlertCircle, label: 'New' },
  context: { color: 'text-violet-400', icon: BookOpen, label: 'Context' },
};

function ListSection({ title, items }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="content-section mt-6">
      <h3>{title}</h3>
      <ul className="deps-list">
        {items.map(item => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

export default function NodeDetails({ data, onClose }) {
  if (!data) return null;

  const config = statusConfig[data.status] || statusConfig.new;
  const Icon = config.icon;

  return (
    <MotionDiv 
      className="sidebar details-panel"
      initial={{ x: '100%' }}
      animate={{ x: 0 }}
      exit={{ x: '100%' }}
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
    >
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
        
        {data.stale_reasons && data.stale_reasons.length > 0 && (
            <div className="stale-reasons">
                <strong>Why it will rebuild:</strong> {data.stale_reasons.join('; ')}
            </div>
        )}

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
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]} 
              rehypePlugins={[rehypeHighlight]}
            >
              {data.content || '*No content available*'}
            </ReactMarkdown>
          </div>
        </div>

        <ListSection title="Parent" items={data.parent ? [data.parent] : []} />
        <ListSection title="Depends On" items={data.depends_on} />
        <ListSection title="Acceptance Tests" items={data.acceptance} />
      </div>
    </MotionDiv>
  );
}
