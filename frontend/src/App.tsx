import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { AgentCanvas } from './components/AgentCanvas';
import { LogConsole } from './components/LogConsole';
import { PropertyPanel } from './components/PropertyPanel';
import { useGraphStore } from './store/graphStore';
import './index.css';

function App() {
  const { currentGraphId } = useGraphStore();

  return (
    <div className="w-screen h-screen flex flex-col overflow-hidden">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <div className="flex-1">
          <AgentCanvas />
        </div>
        <PropertyPanel />
      </div>
      <LogConsole graphId={currentGraphId} />
    </div>
  );
}

export default App;
