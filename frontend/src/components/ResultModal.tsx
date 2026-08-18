import { X, CheckCircle, Copy } from 'lucide-react';
import { useState } from 'react';

interface ResultModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: {
    status: string;
    output: string;
    graph_id: string;
  } | null;
}

export const ResultModal = ({ isOpen, onClose, result }: ResultModalProps) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen || !result) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(result.output);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg shadow-2xl max-w-3xl w-full mx-4 max-h-[80vh] flex flex-col border border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-6 h-6 text-green-500" />
            <h2 className="text-xl font-bold text-white">Execution Result</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-4">
            {/* Graph ID */}
            <div>
              <label className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
                Graph ID
              </label>
              <div className="mt-1 px-4 py-2 bg-gray-800 rounded-lg text-gray-300 font-mono text-sm">
                {result.graph_id}
              </div>
            </div>

            {/* Output */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
                  Output
                </label>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-2 px-3 py-1 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors text-sm"
                >
                  <Copy className="w-4 h-4" />
                  <span className="text-gray-300">
                    {copied ? 'Copied!' : 'Copy'}
                  </span>
                </button>
              </div>
              <div className="px-4 py-4 bg-gray-800 rounded-lg text-gray-100 whitespace-pre-wrap leading-relaxed">
                {result.output}
              </div>
            </div>

            {/* Status */}
            <div>
              <label className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
                Status
              </label>
              <div className="mt-1 px-4 py-2 bg-green-900 bg-opacity-30 rounded-lg text-green-400 font-semibold">
                ✓ {result.status.toUpperCase()}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-700 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
