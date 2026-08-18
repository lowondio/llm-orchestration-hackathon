import { useEffect, useState } from 'react';
import { Circle, Rocket, Play, FolderOpen, Save, Copy } from 'lucide-react';
import { useHealthStore } from '../store/healthStore';
import { useGraphStore } from '../store/graphStore';
import { checkHealth, deployAgent, runGraph, saveGraph, updateGraph } from '../api/client';
import { ResultModal } from './ResultModal';
import { MyAgentsModal } from './MyAgentsModal';
import { HITLModal } from './HITLModal';

export const Header = () => {
  const { isHealthy, setHealth } = useHealthStore();
  const { nodes, edges, currentGraphId, setCurrentGraphId, clearCanvas, resetNodeStatuses } = useGraphStore();
  const [isDeploying, setIsDeploying] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [deployMessage, setDeployMessage] = useState('');
  const [runInput, setRunInput] = useState('Hello, world!');
  const [showResultModal, setShowResultModal] = useState(false);
  const [executionResult, setExecutionResult] = useState<any>(null);
  const [graphName, setGraphName] = useState('Untitled Agent');
  const [showMyAgents, setShowMyAgents] = useState(false);
  const [showHITLModal, setShowHITLModal] = useState(false);
  const [hitlData, setHitlData] = useState<any>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await checkHealth();
        setHealth(true, data.timestamp);
      } catch (error) {
        setHealth(false, new Date().toISOString());
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, [setHealth]);

  // New Graph: Save & Deploy
  const handleSaveAndDeploy = async () => {
    if (nodes.length === 0) {
      setDeployMessage('❌ No nodes to deploy');
      setTimeout(() => setDeployMessage(''), 3000);
      return;
    }

    setIsDeploying(true);
    setDeployMessage('');

    try {
      // Save as new graph
      const saveResponse = await saveGraph({
        name: graphName,
        description: '',
        config: { nodes, edges }
      });

      const savedGraphId = saveResponse.id;
      setCurrentGraphId(savedGraphId);

      // Deploy it
      const response = await deployAgent({
        nodes,
        edges,
        graph_id: savedGraphId
      });
      setDeployMessage(`✅ Saved & Deployed: ${graphName}`);
      console.log('Save & Deploy successful:', response);
    } catch (error: any) {
      const errorMsg = error.response?.data?.message || error.message || 'Save/Deploy failed';
      setDeployMessage(`❌ ${errorMsg}`);
      console.error('Save/Deploy error:', error);
    } finally {
      setIsDeploying(false);
      setTimeout(() => setDeployMessage(''), 5000);
    }
  };

  // Existing Graph: Run (without saving)
  const handleRun = async () => {
    if (!currentGraphId) {
      setDeployMessage('❌ No graph loaded');
      setTimeout(() => setDeployMessage(''), 3000);
      return;
    }

    setIsRunning(true);
    setDeployMessage('🚀 Running graph...');
    resetNodeStatuses();

    try {
      const response = await runGraph(currentGraphId, runInput);
      console.log('Execution result:', response);
      handleExecutionResponse(response);
    } catch (error: any) {
      const errorMsg = error.response?.data?.message || error.message || 'Execution failed';
      setDeployMessage(`❌ ${errorMsg}`);
      console.error('Execution error:', error);
      setIsRunning(false);
    }
  };

  const handleExecutionResponse = (response: any) => {
    if (response.status === 'paused') {
      setHitlData({
        graphId: response.graph_id || currentGraphId,
        threadId: response.thread_id,
        nodeId: response.node_id,
        message: response.message,
        llmOutput: response.llm_output,
        timeout: response.timeout,
      });
      setShowHITLModal(true);
      setDeployMessage('⚠️ Paused for human approval');
      setIsRunning(false);
    } else {
      setExecutionResult(response);
      setShowResultModal(true);
      setShowHITLModal(false);
      setDeployMessage('✅ Execution complete!');
      setIsRunning(false);
    }
  };

  // Existing Graph: Save Changes (UPDATE)
  const handleSaveChanges = async () => {
    if (!currentGraphId) {
      setDeployMessage('❌ No graph loaded');
      setTimeout(() => setDeployMessage(''), 3000);
      return;
    }

    if (nodes.length === 0) {
      setDeployMessage('❌ No nodes to save');
      setTimeout(() => setDeployMessage(''), 3000);
      return;
    }

    setIsSaving(true);
    setDeployMessage('💾 Saving changes...');

    try {
      await updateGraph(currentGraphId, {
        name: graphName,
        description: '',
        config: { nodes, edges }
      });

      // Re-deploy with updated config
      await deployAgent({
        nodes,
        edges,
        graph_id: currentGraphId
      });

      setDeployMessage(`✅ Changes saved & deployed`);
    } catch (error: any) {
      const errorMsg = error.response?.data?.message || error.message || 'Save failed';
      setDeployMessage(`❌ ${errorMsg}`);
      console.error('Save error:', error);
    } finally {
      setIsSaving(false);
      setTimeout(() => setDeployMessage(''), 5000);
    }
  };

  // Existing Graph: Save as New (duplicate)
  const handleSaveAsNew = async () => {
    if (nodes.length === 0) {
      setDeployMessage('❌ No nodes to save');
      setTimeout(() => setDeployMessage(''), 3000);
      return;
    }

    setIsDeploying(true);
    setDeployMessage('');

    try {
      const newName = `${graphName} (Copy)`;
      const saveResponse = await saveGraph({
        name: newName,
        description: '',
        config: { nodes, edges }
      });

      const newGraphId = saveResponse.id;
      setCurrentGraphId(newGraphId);
      setGraphName(newName);

      // Deploy the new copy
      await deployAgent({
        nodes,
        edges,
        graph_id: newGraphId
      });

      setDeployMessage(`✅ Saved as new: ${newName}`);
    } catch (error: any) {
      const errorMsg = error.response?.data?.message || error.message || 'Save as new failed';
      setDeployMessage(`❌ ${errorMsg}`);
      console.error('Save as new error:', error);
    } finally {
      setIsDeploying(false);
      setTimeout(() => setDeployMessage(''), 5000);
    }
  };

  // Clear canvas and start fresh
  const handleNewGraph = () => {
    if (confirm('Start a new graph? Current work will be cleared.')) {
      clearCanvas();
      setGraphName('Untitled Agent');
      setDeployMessage('');
    }
  };

  return (
    <header className="bg-gray-900 text-white px-6 py-4 flex items-center justify-between border-b border-gray-700">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold">AI Agent Builder</h1>
        <span className="text-sm text-gray-400">v1.0.0</span>
        {currentGraphId && (
          <span className="text-xs text-gray-500 px-2 py-1 bg-gray-800 rounded">
            ID: {currentGraphId.slice(0, 8)}...
          </span>
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* Graph Name Input */}
        <input
          type="text"
          value={graphName}
          onChange={(e) => setGraphName(e.target.value)}
          placeholder="Graph name..."
          className="px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700 focus:outline-none focus:border-purple-500 text-sm w-48"
        />

        {deployMessage && (
          <span className="text-sm px-3 py-1 bg-gray-800 rounded-lg border border-gray-700">
            {deployMessage}
          </span>
        )}

        {/* Run Input (only show if graph is loaded) */}
        {currentGraphId && (
          <input
            type="text"
            value={runInput}
            onChange={(e) => setRunInput(e.target.value)}
            placeholder="Enter input for execution..."
            className="px-3 py-2 bg-gray-800 text-white rounded-lg border border-gray-700 focus:outline-none focus:border-blue-500 text-sm w-64"
          />
        )}

        {/* My Agents Button */}
        <button
          onClick={() => setShowMyAgents(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm bg-gray-800 hover:bg-gray-700 text-white border border-gray-700 transition-all duration-200"
        >
          <FolderOpen className="w-4 h-4" />
          My Agents
        </button>

        {/* New Graph Button (only show if editing existing) */}
        {currentGraphId && (
          <button
            onClick={handleNewGraph}
            className="flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm bg-gray-800 hover:bg-gray-700 text-white border border-gray-700 transition-all duration-200"
          >
            <Rocket className="w-4 h-4" />
            New
          </button>
        )}

        {/* CONDITIONAL BUTTONS BASED ON currentGraphId */}
        {!currentGraphId ? (
          // NEW GRAPH: Show only "Save & Deploy"
          <button
            onClick={handleSaveAndDeploy}
            disabled={isDeploying || nodes.length === 0}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm
              transition-all duration-200
              ${
                isDeploying || nodes.length === 0
                  ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                  : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white shadow-lg hover:shadow-xl'
              }
            `}
          >
            <Rocket className={`w-4 h-4 ${isDeploying ? 'animate-bounce' : ''}`} />
            {isDeploying ? 'Saving...' : 'Save & Deploy'}
          </button>
        ) : (
          // EXISTING GRAPH: Show "Run", "Save Changes", "Save as New"
          <>
            {/* Run Button (Primary - Green) */}
            <button
              onClick={handleRun}
              disabled={isRunning}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm
                transition-all duration-200
                ${
                  isRunning
                    ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white shadow-lg hover:shadow-xl'
                }
              `}
            >
              <Play className={`w-4 h-4 ${isRunning ? 'animate-pulse' : ''}`} />
              {isRunning ? 'Running...' : 'Run'}
            </button>

            {/* Save Changes Button (Secondary - Blue) */}
            <button
              onClick={handleSaveChanges}
              disabled={isSaving || nodes.length === 0}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm
                transition-all duration-200
                ${
                  isSaving || nodes.length === 0
                    ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white shadow-lg hover:shadow-xl'
                }
              `}
            >
              <Save className={`w-4 h-4 ${isSaving ? 'animate-pulse' : ''}`} />
              {isSaving ? 'Saving...' : 'Save Changes'}
            </button>

            {/* Save as New Button (Ghost/Outline) */}
            <button
              onClick={handleSaveAsNew}
              disabled={isDeploying || nodes.length === 0}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm
                transition-all duration-200 border-2
                ${
                  isDeploying || nodes.length === 0
                    ? 'border-gray-700 text-gray-400 cursor-not-allowed'
                    : 'border-purple-500 text-purple-400 hover:bg-purple-500 hover:text-white'
                }
              `}
            >
              <Copy className={`w-4 h-4 ${isDeploying ? 'animate-pulse' : ''}`} />
              Save as New
            </button>
          </>
        )}

        {/* Health Status */}
        <div className="flex items-center gap-2 px-3 py-2 bg-gray-800 rounded-lg border border-gray-700">
          <Circle
            className={`w-3 h-3 ${isHealthy ? 'fill-green-500 text-green-500' : 'fill-red-500 text-red-500'}`}
          />
          <span className="text-sm text-gray-300">
            {isHealthy ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Result Modal */}
      <ResultModal
        isOpen={showResultModal}
        onClose={() => setShowResultModal(false)}
        result={executionResult}
      />

      {/* HITL Modal */}
      {hitlData && (
        <HITLModal
          isOpen={showHITLModal}
          onClose={() => setShowHITLModal(false)}
          graphId={hitlData.graphId}
          threadId={hitlData.threadId}
          message={hitlData.message}
          llmOutput={hitlData.llmOutput}
          timeout={hitlData.timeout}
          onResumeComplete={handleExecutionResponse}
        />
      )}

      {/* My Agents Modal */}
      <MyAgentsModal
        isOpen={showMyAgents}
        onClose={() => setShowMyAgents(false)}
      />
    </header>
  );
};
