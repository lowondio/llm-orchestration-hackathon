import { useState, useRef, useCallback } from 'react';
import { useGraphStore } from '../store/graphStore';
import { Copy, Check, X, Trash2, Upload, FileText, Database, Loader, AlertCircle, CheckCircle } from 'lucide-react';

export const PropertyPanel = () => {
  const selectedNodeId = useGraphStore((state) => state.selectedNodeId);
  const nodes = useGraphStore((state) => state.nodes);
  const currentGraphId = useGraphStore((state) => state.currentGraphId);
  const updateNodeData = useGraphStore((state) => state.updateNodeData);
  const setSelectedNodeId = useGraphStore((state) => state.setSelectedNodeId);
  const [copied, setCopied] = useState(false);
  const [ragUploading, setRagUploading] = useState(false);
  const [ragError, setRagError] = useState<string | null>(null);
  const [ragSuccess, setRagSuccess] = useState<string | null>(null);
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  const handleCopyWebhook = (url: string) => {
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    setSelectedNodeId(null);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleUploadFile = useCallback(async (file: File) => {
    if (!selectedNodeId) return;
    setRagError(null);
    setRagSuccess(null);

    // Validate file type
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'txt' && ext !== 'pdf') {
      setRagError('Only .txt and .pdf files are supported.');
      return;
    }

    setRagUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('node_id', selectedNodeId);

      const selectedNode = nodes.find((n) => n.id === selectedNodeId);
      const chunkSize = selectedNode?.data?.chunkSize ?? 500;
      const chunkOverlap = selectedNode?.data?.chunkOverlap ?? 50;
      formData.append('chunk_size', String(chunkSize));
      formData.append('chunk_overlap', String(chunkOverlap));

      const res = await fetch('http://localhost:8000/api/rag/upload', {
        method: 'POST',
        body: formData,
      });

      const json = await res.json();

      if (!res.ok || json.status === 'error') {
        throw new Error(json.message || 'Upload failed');
      }

      // Append to ragFiles in store
      const existingFiles: any[] = selectedNode?.data?.ragFiles || [];
      updateNodeData(selectedNodeId, {
        ragFiles: [...existingFiles, json.file],
      });
      setRagSuccess(`"${file.name}" indexed (${json.file.chunks_count} chunks)`);
      setTimeout(() => setRagSuccess(null), 4000);
    } catch (err: any) {
      setRagError(err.message || 'Upload failed. Check backend logs.');
    } finally {
      setRagUploading(false);
    }
  }, [selectedNodeId, nodes, updateNodeData]);

  const handleDeleteFile = useCallback(async (fileId: string, _filename: string) => {
    if (!selectedNodeId) return;
    setRagError(null);

    try {
      const res = await fetch(`http://localhost:8000/api/rag/files/${selectedNodeId}/${fileId}`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        const json = await res.json();
        throw new Error(json.message || 'Delete failed');
      }

      const selectedNode = nodes.find((n) => n.id === selectedNodeId);
      const existingFiles: any[] = selectedNode?.data?.ragFiles || [];
      updateNodeData(selectedNodeId, {
        ragFiles: existingFiles.filter((f: any) => f.id !== fileId),
      });
    } catch (err: any) {
      setRagError(err.message || 'Delete failed.');
    }
  }, [selectedNodeId, nodes, updateNodeData]);

  const handleFileDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUploadFile(file);
  }, [handleUploadFile]);

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDraggingOver(true);
  };

  const handleDragLeave = () => {
    setIsDraggingOver(false);
  };

  if (!selectedNode || !selectedNodeId) {
    return (
      <div className="w-80 bg-gray-900 border-l border-gray-700 p-6 flex items-center justify-center">
        <div className="text-center text-gray-500">
          <p className="text-sm">Select a node to edit its properties</p>
        </div>
      </div>
    );
  }

  const { type, data } = selectedNode;

  return (
    <div className="w-80 bg-gray-900 border-l border-gray-700 flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
        <h3 className="text-white font-semibold text-sm">Node Properties</h3>
        <button
          onClick={handleClose}
          className="text-gray-400 hover:text-white transition-colors"
          title="Close panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Trigger Node */}
        {type === 'trigger' && (
          <>
            <div>
              <label className="text-xs text-gray-400 mb-2 block font-medium">Trigger Type</label>
              <select
                value={data.triggerType || 'manual'}
                onChange={(e) => updateNodeData(selectedNodeId, { triggerType: e.target.value })}
                className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-green-500 transition-colors"
              >
                <option value="manual">Manual</option>
                <option value="webhook">Webhook</option>
                <option value="cron">Cron Schedule</option>
                <option value="interval">Interval</option>
                <option value="telegram">Telegram Bot</option>
                <option value="widget">Website Widget</option>
              </select>
            </div>

            {data.triggerType === 'webhook' && (
              <div className="space-y-2">
                {currentGraphId ? (
                  <>
                    <label className="text-xs text-gray-400 block font-medium">Webhook URL</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={`http://localhost:8000/api/webhook/${currentGraphId}`}
                        readOnly
                        className="flex-1 bg-gray-800 text-white text-xs rounded px-3 py-2 border border-gray-700 font-mono"
                      />
                      <button
                        onClick={() => handleCopyWebhook(`http://localhost:8000/api/webhook/${currentGraphId}`)}
                        className="px-3 py-2 bg-green-600 hover:bg-green-700 rounded transition-colors"
                        title="Copy to clipboard"
                      >
                        {copied ? (
                          <Check className="w-4 h-4 text-white" />
                        ) : (
                          <Copy className="w-4 h-4 text-white" />
                        )}
                      </button>
                    </div>
                    <p className="text-xs text-gray-500">
                      Send POST requests to this URL to trigger the graph
                    </p>
                  </>
                ) : (
                  <div className="bg-gray-800 border border-gray-700 rounded px-3 py-2">
                    <p className="text-xs text-gray-400">
                      💡 Deploy the graph to generate your webhook URL
                    </p>
                  </div>
                )}
              </div>
            )}

            {data.triggerType === 'cron' && (
              <div>
                <label className="text-xs text-gray-400 mb-2 block font-medium">Cron Expression</label>
                <input
                  type="text"
                  value={data.cronExpression || ''}
                  onChange={(e) => updateNodeData(selectedNodeId, { cronExpression: e.target.value })}
                  placeholder="0 0 * * *"
                  className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-green-500 font-mono transition-colors"
                />
                <p className="text-xs text-gray-500 mt-1">Example: 0 0 * * * (daily at midnight)</p>
              </div>
            )}

            {data.triggerType === 'interval' && (
              <div>
                <label className="text-xs text-gray-400 mb-2 block font-medium">Interval</label>
                <select
                  value={data.interval || 60}
                  onChange={(e) => updateNodeData(selectedNodeId, { interval: parseInt(e.target.value) })}
                  className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-green-500 transition-colors"
                >
                  <option value="60">1 minute</option>
                  <option value="300">5 minutes</option>
                  <option value="600">10 minutes</option>
                  <option value="1800">30 minutes</option>
                  <option value="3600">1 hour</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Agent will run automatically at this interval
                </p>
              </div>
            )}

            {data.triggerType === 'telegram' && (
              <div>
                <label className="text-xs text-gray-400 mb-2 block font-medium">Bot Token</label>
                <input
                  type="password"
                  value={data.botToken || ''}
                  onChange={(e) => updateNodeData(selectedNodeId, { botToken: e.target.value })}
                  placeholder="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
                  className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-green-500 font-mono transition-colors"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Get your bot token from @BotFather on Telegram
                </p>
                {data.botToken && (
                  <div className="mt-2 bg-green-900/20 border border-green-700 rounded px-3 py-2">
                    <p className="text-xs text-green-400">
                      ✓ Webhook will be registered when you save the graph
                    </p>
                  </div>
                )}
              </div>
            )}

            {data.triggerType === 'widget' && (
              <div className="space-y-3">
                {currentGraphId ? (
                  <>
                    <div>
                      <label className="text-xs text-gray-400 mb-2 block font-medium">Embed Code</label>
                      <div className="bg-gray-800 border border-gray-700 rounded p-3">
                        <code className="text-xs text-green-400 break-all font-mono">
                          {`<script src="http://localhost:8000/static/widget.js" data-agent-id="${currentGraphId}"></script>`}
                        </code>
                      </div>
                      <button
                        onClick={() => {
                          const embedCode = `<script src="http://localhost:8000/static/widget.js" data-agent-id="${currentGraphId}"></script>`;
                          navigator.clipboard.writeText(embedCode);
                          setCopied(true);
                          setTimeout(() => setCopied(false), 2000);
                        }}
                        className="mt-2 w-full px-3 py-2 bg-green-600 hover:bg-green-700 rounded transition-colors text-white text-sm font-medium flex items-center justify-center gap-2"
                      >
                        {copied ? (
                          <>
                            <Check className="w-4 h-4" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy className="w-4 h-4" />
                            Copy Embed Code
                          </>
                        )}
                      </button>
                    </div>
                    <div className="bg-blue-900/20 border border-blue-700 rounded px-3 py-2">
                      <p className="text-xs text-blue-400 font-medium mb-1">📋 How to use:</p>
                      <ol className="text-xs text-blue-300 space-y-1 list-decimal list-inside">
                        <li>Copy the embed code above</li>
                        <li>Paste it before the closing &lt;/body&gt; tag on your website</li>
                        <li>A chat widget will appear on the bottom-right corner</li>
                        <li>Conversations persist across page refreshes</li>
                      </ol>
                    </div>
                    <div className="bg-gray-800 border border-gray-700 rounded px-3 py-2">
                      <p className="text-xs text-gray-400 font-medium mb-1">⚙️ Optional attributes:</p>
                      <ul className="text-xs text-gray-500 space-y-1">
                        <li><code className="text-green-400">data-api-url</code> - Custom API URL (default: http://localhost:8000)</li>
                      </ul>
                    </div>
                  </>
                ) : (
                  <div className="bg-gray-800 border border-gray-700 rounded px-3 py-2">
                    <p className="text-xs text-gray-400">
                      💡 Deploy the graph to generate your embed code
                    </p>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* LLM Node */}
        {type === 'llm' && (
          <>
            <div>
              <label className="text-xs text-gray-400 mb-2 block font-medium">Model</label>
              <select
                value={data.model || 'gpt-4o-mini'}
                onChange={(e) => updateNodeData(selectedNodeId, { model: e.target.value })}
                className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-purple-500 transition-colors"
              >
                <optgroup label="OpenAI">
                  <option value="gpt-4o">GPT-4o</option>
                  <option value="gpt-4o-mini">GPT-4o-mini</option>
                </optgroup>
                <optgroup label="Nvidia AI (Free)">
                  <option value="meta/llama-3.1-405b-instruct">Llama 3.1 405B</option>
                  <option value="meta/llama-3.1-70b-instruct">Llama 3.1 70B</option>
                  <option value="meta/llama-3.1-8b-instruct">Llama 3.1 8B</option>
                  <option value="mistralai/mixtral-8x22b-instruct-v0.1">Mixtral 8x22B</option>
                  <option value="mistralai/mistral-large-2-instruct">Mistral Large 2</option>
                </optgroup>
              </select>
            </div>

            <div>
              <label className="text-xs text-gray-400 mb-2 block font-medium">System Prompt</label>
              <textarea
                value={data.systemPrompt || ''}
                onChange={(e) => updateNodeData(selectedNodeId, { systemPrompt: e.target.value })}
                placeholder="Enter system prompt..."
                className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-purple-500 resize-none transition-colors"
                rows={8}
              />
              <p className="text-xs text-gray-500 mt-1">
                Define the agent's behavior and capabilities
              </p>
            </div>
          </>
        )}

        {/* Tool Node */}
        {type === 'tool' && (
          <>
            <div>
              <label className="text-xs text-gray-400 mb-2 block font-medium">Tool Type</label>
              <select
                value={data.toolType || 'web_search'}
                onChange={(e) => updateNodeData(selectedNodeId, { toolType: e.target.value })}
                className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-blue-500 transition-colors"
              >
                <option value="web_search">Web Search (DuckDuckGo)</option>
                <option value="calculator">Calculator</option>
                <option value="api_fetcher">API Fetcher (HTTP GET)</option>
              </select>
            </div>

            {data.toolType === 'api_fetcher' && (
              <div>
                <label className="text-xs text-gray-400 mb-2 block font-medium">Target URL</label>
                <input
                  type="text"
                  value={data.config || ''}
                  onChange={(e) => updateNodeData(selectedNodeId, { config: e.target.value })}
                  placeholder="https://api.example.com/endpoint"
                  className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-blue-500 transition-colors"
                />
                <p className="text-xs text-gray-500 mt-1">
                  The API endpoint to fetch data from
                </p>
              </div>
            )}

            {data.toolType !== 'api_fetcher' && (
              <div>
                <label className="text-xs text-gray-400 mb-2 block font-medium">Configuration (JSON)</label>
                <textarea
                  value={data.config || ''}
                  onChange={(e) => updateNodeData(selectedNodeId, { config: e.target.value })}
                  placeholder="Tool configuration (JSON)..."
                  className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-blue-500 resize-none font-mono transition-colors"
                  rows={4}
                />
              </div>
            )}
          </>
        )}

        {/* Action Node */}
        {type === 'action' && (
          <>
            <div>
              <label className="text-xs text-gray-400 mb-2 block font-medium">Action Type</label>
              <select
                value={data.actionType || 'log'}
                onChange={(e) => updateNodeData(selectedNodeId, { actionType: e.target.value })}
                className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-orange-500 transition-colors"
              >
                <option value="log">Log Output</option>
                <option value="http_post">HTTP POST</option>
              </select>
            </div>

            {data.actionType === 'http_post' && (
              <div>
                <label className="text-xs text-gray-400 mb-2 block font-medium">Endpoint URL</label>
                <input
                  type="text"
                  value={data.config || ''}
                  onChange={(e) => updateNodeData(selectedNodeId, { config: e.target.value })}
                  placeholder="https://webhook.site/your-unique-url"
                  className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-orange-500 transition-colors"
                />
                <p className="text-xs text-gray-500 mt-1">
                  The webhook URL to send the result to
                </p>
              </div>
            )}
          </>
        )}

        {/* RAG / Knowledge Base Node */}
        {type === 'rag' && (
          <>
            {/* Knowledge Base Name */}
            <div>
              <label className="text-xs text-gray-400 mb-2 block font-medium">Knowledge Base Name</label>
              <input
                type="text"
                value={data.ragName || ''}
                onChange={(e) => updateNodeData(selectedNodeId, { ragName: e.target.value })}
                placeholder="e.g. Product Docs, FAQ, Policy..."
                className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-teal-500 transition-colors"
              />
              <p className="text-xs text-gray-500 mt-1">
                The LLM will see this name in its tool description
              </p>
            </div>

            {/* Chunking Parameters */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-gray-400 mb-1 block font-medium">Chunk Size</label>
                <input
                  type="number"
                  value={data.chunkSize ?? 500}
                  min={100}
                  max={4000}
                  onChange={(e) => updateNodeData(selectedNodeId, { chunkSize: parseInt(e.target.value) || 500 })}
                  className="w-full bg-gray-800 text-white text-sm rounded px-2 py-2 border border-gray-700 focus:outline-none focus:border-teal-500 transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block font-medium">Overlap</label>
                <input
                  type="number"
                  value={data.chunkOverlap ?? 50}
                  min={0}
                  max={500}
                  onChange={(e) => updateNodeData(selectedNodeId, { chunkOverlap: parseInt(e.target.value) || 50 })}
                  className="w-full bg-gray-800 text-white text-sm rounded px-2 py-2 border border-gray-700 focus:outline-none focus:border-teal-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="text-xs text-gray-400 mb-1 block font-medium">Top-K Results</label>
              <input
                type="number"
                value={data.topK ?? 3}
                min={1}
                max={10}
                onChange={(e) => updateNodeData(selectedNodeId, { topK: parseInt(e.target.value) || 3 })}
                className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-teal-500 transition-colors"
              />
              <p className="text-xs text-gray-500 mt-1">Number of chunks returned per search</p>
            </div>

            {/* Upload Zone */}
            <div>
              <label className="text-xs text-gray-400 mb-2 block font-medium">Upload Documents</label>

              {/* Hidden native file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.pdf"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleUploadFile(file);
                  // Reset so same file can be re-uploaded
                  e.target.value = '';
                }}
              />

              {/* Drag & Drop zone */}
              <div
                onDrop={handleFileDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => !ragUploading && fileInputRef.current?.click()}
                className={`
                  border-2 border-dashed rounded-lg p-4 flex flex-col items-center gap-2 cursor-pointer transition-all duration-200
                  ${isDraggingOver
                    ? 'border-teal-400 bg-teal-900/30 scale-[1.02]'
                    : 'border-gray-600 bg-gray-800/50 hover:border-teal-500 hover:bg-teal-900/10'
                  }
                  ${ragUploading ? 'cursor-not-allowed opacity-60' : ''}
                `}
              >
                {ragUploading ? (
                  <>
                    <Loader className="w-6 h-6 text-teal-400 animate-spin" />
                    <p className="text-xs text-teal-300">Indexing document…</p>
                  </>
                ) : (
                  <>
                    <Upload className="w-6 h-6 text-gray-400" />
                    <p className="text-xs text-gray-400 text-center">
                      <span className="text-teal-400 font-medium">Click to upload</span> or drag & drop
                    </p>
                    <p className="text-xs text-gray-500">PDF or TXT files supported</p>
                  </>
                )}
              </div>

              {/* Error / Success messages */}
              {ragError && (
                <div className="mt-2 flex items-start gap-2 bg-red-900/30 border border-red-700 rounded px-3 py-2">
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <p className="text-xs text-red-300">{ragError}</p>
                </div>
              )}
              {ragSuccess && (
                <div className="mt-2 flex items-start gap-2 bg-teal-900/30 border border-teal-700 rounded px-3 py-2">
                  <CheckCircle className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
                  <p className="text-xs text-teal-300">{ragSuccess}</p>
                </div>
              )}
            </div>

            {/* Indexed Files List */}
            {(data.ragFiles || []).length > 0 && (
              <div>
                <label className="text-xs text-gray-400 mb-2 block font-medium flex items-center gap-1">
                  <Database className="w-3 h-3" />
                  Indexed Files ({(data.ragFiles || []).length})
                </label>
                <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                  {(data.ragFiles || []).map((file: any) => (
                    <div
                      key={file.id}
                      className="bg-gray-800 border border-gray-700 rounded px-3 py-2 flex items-center gap-2 group/file"
                    >
                      <FileText className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-white font-medium truncate" title={file.filename}>
                          {file.filename}
                        </p>
                        <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                      </div>
                      <button
                        onClick={() => handleDeleteFile(file.id, file.filename)}
                        className="opacity-0 group-hover/file:opacity-100 transition-opacity w-5 h-5 bg-red-500/80 hover:bg-red-600 rounded flex items-center justify-center shrink-0"
                        title={`Remove ${file.filename}`}
                      >
                        <Trash2 className="w-3 h-3 text-white" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Empty state hint */}
            {(data.ragFiles || []).length === 0 && !ragUploading && (
              <div className="bg-teal-900/20 border border-teal-800 rounded px-3 py-2">
                <p className="text-xs text-teal-400 font-medium mb-1">💡 How to use:</p>
                <ol className="text-xs text-teal-300/80 space-y-1 list-decimal list-inside">
                  <li>Upload one or more PDF / TXT files above</li>
                  <li>Connect this node to the LLM's left (tools_in) handle</li>
                  <li>The LLM will automatically search the knowledge base when needed</li>
                </ol>
              </div>
            )}
          </>
        )}

        {/* Agent Node */}
        {type === 'agent' && (
          <>
            <div>
              <label className="text-xs text-gray-400 mb-2 block font-medium">Agent Role / Description</label>
              <input
                type="text"
                value={data.agentRole || ''}
                onChange={(e) => updateNodeData(selectedNodeId, { agentRole: e.target.value })}
                placeholder="e.g. Sales Specialist, Support Analyst..."
                className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-indigo-500 transition-colors"
              />
              <p className="text-xs text-gray-500 mt-1">Used to identify this specialist tool for the LLM</p>
            </div>

            <div>
              <label className="text-xs text-gray-400 mb-2 block font-medium">Worker Model</label>
              <select
                value={data.agentModel || 'gpt-4o-mini'}
                onChange={(e) => updateNodeData(selectedNodeId, { agentModel: e.target.value })}
                className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-indigo-500 transition-colors"
              >
                <option value="gpt-4o">GPT-4o</option>
                <option value="gpt-4o-mini">GPT-4o-mini</option>
                <option value="meta/llama-3.1-70b-instruct">Llama 3.1 70B</option>
                <option value="meta/llama-3.1-8b-instruct">Llama 3.1 8B</option>
              </select>
            </div>

            <div>
              <label className="text-xs text-gray-400 mb-2 block font-medium">Worker System Prompt</label>
              <textarea
                value={data.agentSystemPrompt || ''}
                onChange={(e) => updateNodeData(selectedNodeId, { agentSystemPrompt: e.target.value })}
                placeholder="Instructions for this specialist agent..."
                className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-indigo-500 resize-none transition-colors"
                rows={8}
              />
              <p className="text-xs text-gray-500 mt-1">
                Define the specialist agent's precise scope, data formatting, and behaviour.
              </p>
            </div>
          </>
        )}

        {/* HITL Node */}
        {type === 'hitl' && (
          <>
            <div>
              <label className="text-xs text-gray-400 mb-2 block font-medium">Approval Prompt Message</label>
              <textarea
                value={data.hitlMessage || ''}
                onChange={(e) => updateNodeData(selectedNodeId, { hitlMessage: e.target.value })}
                placeholder="e.g. Approve database insertion? or Confirm refund transaction?"
                className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-amber-500 resize-none transition-colors"
                rows={3}
              />
              <p className="text-xs text-gray-500 mt-1">Message displayed to the human in the loop</p>
            </div>

            <div>
              <label className="text-xs text-gray-400 mb-2 block font-medium">Timeout (seconds)</label>
              <input
                type="number"
                value={data.hitlTimeout ?? 60}
                min={10}
                max={3600}
                onChange={(e) => updateNodeData(selectedNodeId, { hitlTimeout: parseInt(e.target.value) || 60 })}
                className="w-full bg-gray-800 text-white text-sm rounded px-3 py-2 border border-gray-700 focus:outline-none focus:border-amber-500 transition-colors"
              />
              <p className="text-xs text-gray-500 mt-1">Time allowed for approval before auto-rejecting</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
