import React, { useState } from 'react';
import { Search, Sliders, FileText, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';

interface SearchResult {
  id: string;
  filename: string;
  chunk: string;
  score: number;
  page?: number;
  metadata?: Record<string, any>;
}

interface HybridSearchProps {
  onSearch?: (query: string, options: SearchOptions) => void;
}

export interface SearchOptions {
  topK: number;
  fusionMethod: 'rrf' | 'weighted' | 'simple';
  vectorWeight: number;
  keywordWeight: number;
}

const HybridSearch: React.FC<HybridSearchProps> = ({ onSearch }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [searchOptions, setSearchOptions] = useState<SearchOptions>({
    topK: 10,
    fusionMethod: 'rrf',
    vectorWeight: 0.7,
    keywordWeight: 0.3,
  });
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());

  const handleSearch = async () => {
    if (!query.trim()) return;

    setSearching(true);
    try {
      // 这里应该调用实际的搜索API
      // const response = await searchApi.hybridSearch(query, searchOptions);

      // 模拟搜索结果
      setTimeout(() => {
        setResults([
          {
            id: '1',
            filename: 'sample.pdf',
            chunk: '这是一个示例搜索结果，展示搜索内容的片段...',
            score: 0.95,
            page: 1,
          },
          {
            id: '2',
            filename: 'document.docx',
            chunk: '另一个匹配的文档片段，包含相关信息...',
            score: 0.87,
            page: 3,
          },
        ]);
        setSearching(false);
      }, 1000);

      if (onSearch) {
        onSearch(query, searchOptions);
      }
    } catch (error) {
      console.error('搜索失败:', error);
      setSearching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  const toggleExpand = (resultId: string) => {
    setExpandedResults((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(resultId)) {
        newSet.delete(resultId);
      } else {
        newSet.add(resultId);
      }
      return newSet;
    });
  };

  const highlightText = (text: string, query: string) => {
    if (!query) return text;
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<mark class="bg-yellow-500/30 text-yellow-200">$1</mark>');
  };

  return (
    <div className="h-full flex flex-col bg-chat-bg overflow-hidden">
      {/* 标题 */}
      <div className="p-4 border-b border-chat-border">
        <div className="flex items-center gap-3">
          <Search size={20} className="text-chat-accent" />
          <h2 className="text-lg font-semibold text-chat-text">混合搜索</h2>
        </div>
      </div>

      {/* 搜索区域 */}
      <div className="p-4 border-b border-chat-border space-y-3">
        {/* 搜索输入框 */}
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入搜索关键词..."
              className="w-full px-4 py-2 pl-10 bg-chat-input border border-chat-border rounded-lg text-chat-text placeholder-gray-500 focus:outline-none focus:border-chat-accent"
            />
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={!query.trim() || searching}
            className="px-4 py-2 bg-chat-accent hover:bg-chat-accent/90 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex-shrink-0"
          >
            {searching ? '搜索中...' : '搜索'}
          </button>
        </div>

        {/* 高级选项切换 */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-chat-text transition-colors"
        >
          <Sliders size={16} />
          <span>高级选项</span>
          {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {/* 高级选项 */}
        {showAdvanced && (
          <div className="p-4 bg-chat-bg-secondary rounded-lg border border-chat-border space-y-4">
            {/* Top K */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                返回数量: {searchOptions.topK}
              </label>
              <input
                type="range"
                min="1"
                max="50"
                value={searchOptions.topK}
                onChange={(e) =>
                  setSearchOptions({ ...searchOptions, topK: Number(e.target.value) })
                }
                className="w-full"
              />
            </div>

            {/* 融合算法 */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                融合算法
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(['rrf', 'weighted', 'simple'] as const).map((method) => (
                  <button
                    key={method}
                    onClick={() =>
                      setSearchOptions({ ...searchOptions, fusionMethod: method })
                    }
                    className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
                      searchOptions.fusionMethod === method
                        ? 'bg-chat-accent border-chat-accent text-white'
                        : 'bg-chat-bg border-chat-border text-gray-300 hover:border-chat-accent'
                    }`}
                  >
                    {method === 'rrf' && 'RRF'}
                    {method === 'weighted' && '加权'}
                    {method === 'simple' && '简单'}
                  </button>
                ))}
              </div>
            </div>

            {/* 权重调整 */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  向量权重: {(searchOptions.vectorWeight * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={searchOptions.vectorWeight}
                  onChange={(e) =>
                    setSearchOptions({
                      ...searchOptions,
                      vectorWeight: Number(e.target.value),
                    })
                  }
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  关键词权重: {(searchOptions.keywordWeight * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={searchOptions.keywordWeight}
                  onChange={(e) =>
                    setSearchOptions({
                      ...searchOptions,
                      keywordWeight: Number(e.target.value),
                    })
                  }
                  className="w-full"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 搜索结果 */}
      <div className="flex-1 overflow-y-auto p-4">
        {results.length === 0 ? (
          <div className="text-center text-gray-400 py-12">
            <Search size={48} className="mx-auto mb-4 text-gray-500" />
            <p className="text-sm">
              {query ? '没有找到匹配的结果' : '输入关键词开始搜索'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-gray-400">
                搜索结果 ({results.length})
              </h3>
            </div>

            {results.map((result) => (
              <div
                key={result.id}
                className="p-4 bg-chat-bg-secondary rounded-lg border border-chat-border hover:border-chat-accent transition-colors"
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <FileText size={16} className="text-chat-accent flex-shrink-0" />
                    <h4 className="text-sm font-medium text-gray-200 truncate">
                      {result.filename}
                    </h4>
                    {result.page && (
                      <span className="text-xs text-gray-500 flex-shrink-0">
                        第 {result.page} 页
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-xs px-2 py-1 bg-chat-accent/20 text-chat-accent rounded">
                      {(result.score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                <div
                  className="text-sm text-gray-300 leading-relaxed"
                  dangerouslySetInnerHTML={{
                    __html: highlightText(result.chunk, query),
                  }}
                />

                <button
                  onClick={() => toggleExpand(result.id)}
                  className="mt-2 flex items-center gap-1 text-xs text-chat-accent hover:underline"
                >
                  {expandedResults.has(result.id) ? (
                    <>
                      <ChevronUp size={14} />
                      收起详情
                    </>
                  ) : (
                    <>
                      <ChevronDown size={14} />
                      查看详情
                    </>
                  )}
                </button>

                {expandedResults.has(result.id) && result.metadata && (
                  <div className="mt-3 p-3 bg-chat-bg rounded border border-chat-border">
                    <h5 className="text-xs font-medium text-gray-400 mb-2">
                      元数据
                    </h5>
                    <pre className="text-xs text-gray-300 overflow-x-auto">
                      {JSON.stringify(result.metadata, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default HybridSearch;
