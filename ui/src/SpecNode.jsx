import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  GitMerge, 
  FileCode2 
} from 'lucide-react';

const statusConfig = {
  current: {
    color: 'text-emerald-400',
    border: 'border-emerald-500/50',
    bg: 'bg-emerald-500/10',
    icon: CheckCircle2,
    label: 'Current'
  },
  stale: {
    color: 'text-amber-400',
    border: 'border-amber-500/50',
    bg: 'bg-amber-500/10',
    icon: Clock,
    label: 'Stale'
  },
  new: {
    color: 'text-blue-400',
    border: 'border-blue-500/50',
    bg: 'bg-blue-500/10',
    icon: AlertCircle,
    label: 'New'
  }
};

const SpecNode = ({ data, isConnectable }) => {
  const config = statusConfig[data.status] || statusConfig.new;
  const Icon = config.icon;
  
  // Try to determine layer from path (e.g., behaviors/, contracts/, tests/)
  const layer = data.id.split('/')[0] || 'spec';

  return (
    <div className={`spec-node ${config.border} ${config.bg}`}>
      <Handle
        type="target"
        position={Position.Left}
        isConnectable={isConnectable}
        className="handle"
      />
      
      <div className="node-header">
        <div className="node-type-badge">
          <FileCode2 size={12} className="mr-1" />
          {layer.toUpperCase()}
        </div>
        <div className={`status-badge ${config.color}`}>
          <Icon size={14} className="mr-1" />
          {config.label}
        </div>
      </div>

      <div className="node-title">
        {data.id}
      </div>

      <div className="node-footer">
        <span className="version">v{data.version}</span>
        {data.cascade_depth > 0 && (
          <div className="cascade-badge" title="Cascade Depth">
            <GitMerge size={12} className="mr-1" />
            {data.cascade_depth} downstream
          </div>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        isConnectable={isConnectable}
        className="handle"
      />
    </div>
  );
};

export default memo(SpecNode);
