import React, { useState, useEffect } from 'react';
import { Code2, Copy, Check, Download, Play, RefreshCw, FileCode, Edit3 } from 'lucide-react';
import { motion } from 'framer-motion';
import { useCADStore } from '../store/cadStore';

const CodeViewer: React.FC = () => {
  const { currentModel, setCurrentModel } = useCADStore();
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editableCode, setEditableCode] = useState('');

  useEffect(() => {
    if (currentModel?.code) {
      setEditableCode(currentModel.code);
    }
  }, [currentModel?.code]);

  const handleCopy = () => {
    const textToCopy = isEditing ? editableCode : (currentModel?.code || '');
    if (!textToCopy) return;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const textToDownload = isEditing ? editableCode : (currentModel?.code || '');
    if (!textToDownload) return;
    const blob = new Blob([textToDownload], { type: 'text/x-python' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(currentModel?.name || 'model').toLowerCase().replace(/\s+/g, '_')}.py`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleApplyEdit = () => {
    if (currentModel) {
      setCurrentModel({
        ...currentModel,
        code: editableCode,
      });
      setIsEditing(false);
    }
  };

  const codeToShow = isEditing ? editableCode : (currentModel?.code || '');
  const lineCount = codeToShow ? codeToShow.split('\n').length : 0;

  return (
    <div className="flex flex-col h-full bg-slate-900/90 backdrop-blur-md rounded-2xl shadow-2xl border border-slate-700/70 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-800 via-slate-800/90 to-slate-850 px-4 py-3 border-b border-slate-700/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-blue-500/10 border border-blue-500/20 rounded-lg text-blue-400">
            <Code2 className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              Code Viewer
              {currentModel && (
                <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-full bg-slate-700 text-slate-300">
                  Python / Build123d
                </span>
              )}
            </h2>
            <p className="text-[11px] text-slate-400">
              {lineCount > 0 ? `${lineCount} lines` : 'Generated CAD Script'}
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5">
          {currentModel?.code && (
            <>
              <button
                onClick={() => setIsEditing(!isEditing)}
                className={`p-1.5 rounded-lg text-xs font-medium flex items-center gap-1 transition-colors ${
                  isEditing
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
                title={isEditing ? 'View Mode' : 'Edit Code'}
              >
                <Edit3 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{isEditing ? 'Editing' : 'Edit'}</span>
              </button>

              <button
                onClick={handleCopy}
                className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors flex items-center gap-1 text-xs"
                title="Copy Python Code"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span className="hidden sm:inline">{copied ? 'Copied' : 'Copy'}</span>
              </button>

              <button
                onClick={handleDownload}
                className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors flex items-center gap-1 text-xs"
                title="Download .py File"
              >
                <Download className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Export</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Code Editor / Viewer Area */}
      <div className="flex-1 overflow-auto bg-slate-950 font-mono text-xs text-slate-300 relative">
        {currentModel?.code ? (
          isEditing ? (
            <textarea
              value={editableCode}
              onChange={(e) => setEditableCode(e.target.value)}
              className="w-full h-full bg-transparent p-4 text-xs font-mono text-blue-300 focus:outline-none resize-none leading-relaxed border-none selection:bg-blue-600/40"
              spellCheck={false}
            />
          ) : (
            <div className="p-3 overflow-x-auto min-w-full">
              <table className="border-collapse font-mono text-xs w-full">
                <tbody>
                  {currentModel.code.split('\n').map((line, idx) => {
                    let colorClass = 'text-slate-200';
                    if (line.trim().startsWith('#')) colorClass = 'text-slate-500 italic';
                    else if (line.includes('import') || line.includes('from') || line.includes('with') || line.includes('as') || line.includes('def') || line.includes('class') || line.includes('return')) colorClass = 'text-purple-400 font-semibold';
                    else if (line.includes('Box') || line.includes('Cylinder') || line.includes('Sphere') || line.includes('BuildPart') || line.includes('BuildSketch') || line.includes('show_object')) colorClass = 'text-amber-400 font-medium';
                    else if (line.includes('=')) colorClass = 'text-blue-300';

                    return (
                      <tr key={idx} className="hover:bg-slate-900/60 leading-relaxed">
                        <td className="select-none text-slate-600 text-right pr-3 pl-1 align-top w-7 border-r border-slate-800">
                          {idx + 1}
                        </td>
                        <td className={`pl-4 whitespace-pre font-mono align-top ${colorClass}`}>
                          {line || ' '}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )
        ) : (
          <div className="flex flex-col items-center justify-center h-full p-6 text-center text-slate-500">
            <div className="p-4 bg-slate-900/60 rounded-2xl border border-slate-800 mb-3">
              <FileCode className="w-8 h-8 text-slate-600" />
            </div>
            <p className="text-sm font-medium text-slate-400">No CAD Code Generated</p>
            <p className="text-xs text-slate-600 max-w-xs mt-1">
              Ask TextCAD in the chat window to generate a model, and the underlying CadQuery/Build123d script will appear here.
            </p>
          </div>
        )}
      </div>

      {/* Footer bar */}
      <div className="p-2.5 bg-slate-900 border-t border-slate-800 text-[11px] text-slate-500 flex items-center justify-between">
        <span>Format: CadQuery / Build123d Python</span>
        {isEditing && (
          <button
            onClick={handleApplyEdit}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded-md font-medium text-xs flex items-center gap-1 shadow-sm"
          >
            <Play className="w-3 h-3 fill-current" />
            Save Changes
          </button>
        )}
      </div>
    </div>
  );
};

export default CodeViewer;
