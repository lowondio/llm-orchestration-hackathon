import { useState } from 'react';
import { X, ShieldAlert, Check, Ban, Loader } from 'lucide-react';
import axios from 'axios';

interface HITLModalProps {
  isOpen: boolean;
  onClose: () => void;
  graphId: string;
  threadId: string;
  message: string;
  llmOutput: string;
  timeout?: number;
  onResumeComplete: (result: any) => void;
}

export const HITLModal = ({
  isOpen,
  onClose,
  graphId,
  threadId,
  message,
  llmOutput,
  onResumeComplete,
}: HITLModalProps) => {
  const [isResuming, setIsResuming] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAction = async (approved: boolean) => {
    setIsResuming(true);
    setErrorMsg(null);

    try {
      const res = await axios.post(`http://localhost:8000/api/run/${graphId}/resume`, {
        thread_id: threadId,
        approved: approved,
      });

      if (res.data.status === 'paused') {
        // Paused again (multiple HITL nodes)
        onResumeComplete(res.data);
      } else if (res.data.status === 'rejected') {
        alert('Execution was rejected and aborted.');
        onClose();
      } else {
        // Complete
        onResumeComplete(res.data);
      }
    } catch (err: any) {
      const msg = err.response?.data?.message || err.message || 'Failed to resume execution';
      setErrorMsg(msg);
      setIsResuming(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg shadow-2xl max-w-2xl w-full mx-4 border border-amber-500/40 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 bg-gradient-to-r from-amber-950/60 to-gray-900 border-b border-amber-500/20">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-6 h-6 text-amber-500 animate-pulse" />
            <h2 className="text-lg font-bold text-white">Human Approval Gate</h2>
          </div>
          {!isResuming && (
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-6 space-y-4 flex-1">
          <div className="bg-amber-950/20 border border-amber-500/20 rounded-lg p-4">
            <p className="text-sm font-semibold text-amber-300 mb-1">Gatekeeper Action Prompt:</p>
            <p className="text-base text-white font-medium">{message || 'Approve this action to proceed?'}</p>
          </div>

          {llmOutput && (
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                Proposed Agent Response / Action Context:
              </label>
              <div className="px-4 py-3 bg-gray-950 border border-gray-800 rounded-lg text-gray-200 text-sm whitespace-pre-wrap font-mono max-h-60 overflow-y-auto leading-relaxed">
                {llmOutput}
              </div>
            </div>
          )}

          {errorMsg && (
            <div className="bg-red-900/20 border border-red-700/50 rounded-lg p-3 text-xs text-red-400 font-medium">
              {errorMsg}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-gray-800 bg-gray-900/60 flex items-center justify-between">
          <div className="text-xs text-gray-500">
            Thread ID: <span className="font-mono">{threadId.slice(0, 15)}...</span>
          </div>

          <div className="flex gap-3">
            {isResuming ? (
              <div className="flex items-center gap-2 px-4 py-2 text-sm text-gray-400 font-medium bg-gray-800 rounded-lg">
                <Loader className="w-4 h-4 animate-spin text-amber-500" />
                Resuming execution...
              </div>
            ) : (
              <>
                <button
                  onClick={() => handleAction(false)}
                  className="flex items-center gap-1.5 px-5 py-2 bg-red-600/90 hover:bg-red-700 text-white font-semibold rounded-lg transition-colors text-sm"
                >
                  <Ban className="w-4 h-4" />
                  Reject
                </button>
                <button
                  onClick={() => handleAction(true)}
                  className="flex items-center gap-1.5 px-5 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors text-sm"
                >
                  <Check className="w-4 h-4" />
                  Approve & Resume
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
