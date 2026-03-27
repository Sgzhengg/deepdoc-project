import React, { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon,
  Server,
  Cpu,
  Palette,
  Search,
  Save,
  RotateCcw,
  Info,
} from 'lucide-react';
import type { Settings } from '@/types';

interface SettingsPanelProps {
  onClose?: () => void;
}

const DEFAULT_SETTINGS: Settings = {
  api: {
    baseUrl: '/api',
    timeout: 30000,
  },
  model: {
    embeddingModel: 'BAAI/bge-m3',
    llmModel: 'qwen2.5:7b',
    temperature: 0.7,
    maxTokens: 2000,
  },
  ui: {
    theme: 'dark',
    language: 'zh',
    fontSize: 'medium',
  },
  search: {
    defaultTopK: 10,
    fusionMethod: 'rrf',
    vectorWeight: 0.7,
    keywordWeight: 0.3,
  },
};

const SettingsPanel: React.FC<SettingsPanelProps> = ({ onClose }) => {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [hasChanges, setHasChanges] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    // 从localStorage加载设置
    const savedSettings = localStorage.getItem('app-settings');
    if (savedSettings) {
      try {
        setSettings(JSON.parse(savedSettings));
      } catch (e) {
        console.error('加载设置失败:', e);
      }
    }
  }, []);

  const handleSettingChange = (
    category: keyof Settings,
    key: string,
    value: any
  ) => {
    setSettings({
      ...settings,
      [category]: {
        ...settings[category],
        [key]: value,
      },
    });
    setHasChanges(true);
    setSaved(false);
  };

  const handleSave = () => {
    localStorage.setItem('app-settings', JSON.stringify(settings));
    setHasChanges(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = () => {
    if (window.confirm('确定要重置所有设置吗？')) {
      setSettings(DEFAULT_SETTINGS);
      setHasChanges(true);
    }
  };

  return (
    <div className="h-full flex flex-col bg-chat-bg overflow-hidden">
      {/* 标题栏 */}
      <div className="p-4 border-b border-chat-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SettingsIcon size={20} className="text-chat-accent" />
          <h2 className="text-lg font-semibold text-chat-text">系统设置</h2>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-chat-text transition-colors"
          >
            ✕
          </button>
        )}
      </div>

      {/* 设置内容 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* API设置 */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Server size={18} className="text-chat-accent" />
            <h3 className="text-base font-semibold text-chat-text">API 设置</h3>
          </div>
          <div className="space-y-3 ml-6">
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                API 基础路径
              </label>
              <input
                type="text"
                value={settings.api.baseUrl}
                onChange={(e) =>
                  handleSettingChange('api', 'baseUrl', e.target.value)
                }
                className="w-full px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text text-sm focus:outline-none focus:border-chat-accent"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                超时时间 (毫秒)
              </label>
              <input
                type="number"
                value={settings.api.timeout}
                onChange={(e) =>
                  handleSettingChange('api', 'timeout', Number(e.target.value))
                }
                className="w-full px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text text-sm focus:outline-none focus:border-chat-accent"
              />
            </div>
          </div>
        </div>

        {/* 模型设置 */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Cpu size={18} className="text-chat-accent" />
            <h3 className="text-base font-semibold text-chat-text">模型设置</h3>
          </div>
          <div className="space-y-3 ml-6">
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                嵌入模型
              </label>
              <select
                value={settings.model.embeddingModel}
                onChange={(e) =>
                  handleSettingChange('model', 'embeddingModel', e.target.value)
                }
                className="w-full px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text text-sm focus:outline-none focus:border-chat-accent"
              >
                <option value="BAAI/bge-m3">BAAI/bge-m3</option>
                <option value="BAAI/bge-small-zh-v1.5">
                  BAAI/bge-small-zh-v1.5
                </option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                LLM 模型
              </label>
              <input
                type="text"
                value={settings.model.llmModel}
                onChange={(e) =>
                  handleSettingChange('model', 'llmModel', e.target.value)
                }
                className="w-full px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text text-sm focus:outline-none focus:border-chat-accent"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Temperature
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={settings.model.temperature}
                  onChange={(e) =>
                    handleSettingChange(
                      'model',
                      'temperature',
                      Number(e.target.value)
                    )
                  }
                  className="w-full px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text text-sm focus:outline-none focus:border-chat-accent"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  最大Token数
                </label>
                <input
                  type="number"
                  value={settings.model.maxTokens}
                  onChange={(e) =>
                    handleSettingChange(
                      'model',
                      'maxTokens',
                      Number(e.target.value)
                    )
                  }
                  className="w-full px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text text-sm focus:outline-none focus:border-chat-accent"
                />
              </div>
            </div>
          </div>
        </div>

        {/* 界面设置 */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Palette size={18} className="text-chat-accent" />
            <h3 className="text-base font-semibold text-chat-text">界面设置</h3>
          </div>
          <div className="space-y-3 ml-6">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm text-gray-400 mb-2">主题</label>
                <select
                  value={settings.ui.theme}
                  onChange={(e) =>
                    handleSettingChange('ui', 'theme', e.target.value)
                  }
                  className="w-full px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text text-sm focus:outline-none focus:border-chat-accent"
                >
                  <option value="light">浅色</option>
                  <option value="dark">深色</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  语言
                </label>
                <select
                  value={settings.ui.language}
                  onChange={(e) =>
                    handleSettingChange('ui', 'language', e.target.value)
                  }
                  className="w-full px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text text-sm focus:outline-none focus:border-chat-accent"
                >
                  <option value="zh">中文</option>
                  <option value="en">English</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                字体大小
              </label>
              <select
                value={settings.ui.fontSize}
                onChange={(e) =>
                  handleSettingChange('ui', 'fontSize', e.target.value)
                }
                className="w-full px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text text-sm focus:outline-none focus:border-chat-accent"
              >
                <option value="small">小</option>
                <option value="medium">中</option>
                <option value="large">大</option>
              </select>
            </div>
          </div>
        </div>

        {/* 搜索设置 */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Search size={18} className="text-chat-accent" />
            <h3 className="text-base font-semibold text-chat-text">搜索设置</h3>
          </div>
          <div className="space-y-3 ml-6">
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                默认返回数量
              </label>
              <input
                type="number"
                min="1"
                max="50"
                value={settings.search.defaultTopK}
                onChange={(e) =>
                  handleSettingChange('search', 'defaultTopK', Number(e.target.value))
                }
                className="w-full px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text text-sm focus:outline-none focus:border-chat-accent"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                融合算法
              </label>
              <select
                value={settings.search.fusionMethod}
                onChange={(e) =>
                  handleSettingChange('search', 'fusionMethod', e.target.value)
                }
                className="w-full px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text text-sm focus:outline-none focus:border-chat-accent"
              >
                <option value="rrf">RRF (Reciprocal Rank Fusion)</option>
                <option value="weighted">加权融合</option>
                <option value="simple">简单融合</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  向量权重
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={settings.search.vectorWeight}
                  onChange={(e) =>
                    handleSettingChange(
                      'search',
                      'vectorWeight',
                      Number(e.target.value)
                    )
                  }
                  className="w-full px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text text-sm focus:outline-none focus:border-chat-accent"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  关键词权重
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={settings.search.keywordWeight}
                  onChange={(e) =>
                    handleSettingChange(
                      'search',
                      'keywordWeight',
                      Number(e.target.value)
                    )
                  }
                  className="w-full px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text text-sm focus:outline-none focus:border-chat-accent"
                />
              </div>
            </div>
          </div>
        </div>

        {/* 关于 */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Info size={18} className="text-chat-accent" />
            <h3 className="text-base font-semibold text-chat-text">关于</h3>
          </div>
          <div className="ml-6 p-4 bg-chat-bg-secondary rounded-lg border border-chat-border">
            <h4 className="text-sm font-medium text-chat-text mb-2">
              运营商渠道业务AI系统
            </h4>
            <p className="text-xs text-gray-400 mb-1">版本: 1.0.0</p>
            <p className="text-xs text-gray-400 mb-1">
              基于LangGraph的智能文档管理系统
            </p>
            <p className="text-xs text-gray-400">
              支持Agentic RAG和多Agent协作
            </p>
          </div>
        </div>
      </div>

      {/* 底部操作按钮 */}
      <div className="p-4 border-t border-chat-border flex items-center justify-between">
        <button
          onClick={handleReset}
          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-chat-text transition-colors"
        >
          <RotateCcw size={16} />
          <span>重置默认</span>
        </button>
        <div className="flex items-center gap-3">
          {saved && (
            <span className="text-sm text-green-400">设置已保存</span>
          )}
          <button
            onClick={handleSave}
            disabled={!hasChanges}
            className="flex items-center gap-2 px-4 py-2 bg-chat-accent hover:bg-chat-accent/90 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
          >
            <Save size={16} />
            <span>保存设置</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
