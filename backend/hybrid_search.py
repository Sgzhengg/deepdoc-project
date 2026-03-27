# hybrid_search.py
"""
混合检索器 - 结合向量检索和关键词检索
实现多种融合排序算法
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import math
import re
from collections import defaultdict

logger = logging.getLogger(__name__)

class HybridRetriever:
    """混合检索器 - 结合向量检索和关键词检索"""

    def __init__(self, vector_storage, embedding_service, config=None):
        """
        初始化混合检索器

        Args:
            vector_storage: 向量存储实例
            embedding_service: 嵌入服务实例
            config: 配置对象
        """
        self.vector_storage = vector_storage
        self.embedding_service = embedding_service
        self.config = config

        # 初始化重排序模型（按需加载）
        self._reranker = None

        logger.info("✅ 混合检索器初始化完成")

    def _is_package_content_query(self, query: str) -> bool:
        """
        检测是否为套餐内容查询

        Args:
            query: 用户查询

        Returns:
            是否为套餐内容查询
        """
        package_keywords = [
            '包含', '有哪些', '有什么', '内容', '包括',
            '套餐', '卡品', '潮玩青春卡', '全家享'
        ]

        # 检查是否包含套餐相关关键词
        has_package_keyword = any(kw in query for kw in package_keywords)

        # 检查是否询问内容
        has_content_keyword = any(kw in query for kw in ['包含', '有哪些', '有什么', '内容'])

        return has_package_keyword and has_content_keyword
    
    def hybrid_search(self, query: str, top_k: int = 20,
                     fusion_method: str = "rrf",
                     vector_weight: float = 0.7,
                     keyword_weight: float = 0.3,
                     use_rerank: bool = False,
                     use_table_retriever: bool = True) -> List[Dict[str, Any]]:
        """
        混合搜索 - 结合向量检索和关键词检索，并智能合并表格片段

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            fusion_method: 融合方法 (rrf, weighted, simple)
            vector_weight: 向量检索权重（仅用于weighted融合）
            keyword_weight: 关键词检索权重（仅用于weighted融合）
            use_rerank: 是否使用重排序
            use_table_retriever: 是否使用表格检索器（P1优化）

        Returns:
            融合后的搜索结果
        """
        logger.debug(f"执行混合搜索: '{query}', 方法: {fusion_method}")

        # 🔧 针对"套餐内容"类问题的优化
        is_package_content_query = self._is_package_content_query(query)
        if is_package_content_query:
            logger.info("🎯 检测到套餐内容查询，优化检索策略")
            top_k = max(top_k * 2, 20)  # 增加检索数量

        # 1. 并行执行两种检索
        vector_results = self._vector_search(query, top_k * 3)
        keyword_results = self._keyword_search(query, top_k * 3)

        logger.debug(f"向量检索结果: {len(vector_results)} 个")
        logger.debug(f"关键词检索结果: {len(keyword_results)} 个")

        # P1优化: 使用表格检索器智能合并表格片段
        if use_table_retriever:
            try:
                from retrieval.table_retriever import TableRetriever
                from retrieval.table_extractor import TableExtractor

                table_retriever = TableRetriever(self.vector_storage)
                table_extractor = TableExtractor()

                # 对向量检索结果应用表格合并
                if vector_results:
                    logger.info("🔄 P1优化: 应用表格检索器合并片段...")
                    merged_tables = table_retriever.retrieve_complete_tables(
                        query,
                        top_k=top_k * 2,
                        retrieval_multiplier=2
                    )

                    if merged_tables:
                        logger.info(f"✅ 表格合并: {len(vector_results)}个片段 -> {len(merged_tables)}个完整表格")

                        # 进一步：提取完整表格内容（方案1优化）
                        logger.info("🔄 方案1优化: 提取完整表格内容...")
                        for table in merged_tables:
                            if table.get('merged', False):  # 只处理合并过的表格
                                original_text = table.get('text', '')
                                complete_text = table_extractor.extract_complete_table(
                                    [{'text': original_text}]  # 包装成chunk格式
                                )
                                table['text'] = complete_text
                                table['original_length'] = len(original_text)
                                table['extracted_length'] = len(complete_text)

                        # 使用合并后的表格替换原始向量结果
                        vector_results = merged_tables
                    else:
                        logger.info("ℹ️ 未检测到表格结构，使用原始检索结果")
            except Exception as e:
                logger.warning(f"⚠️ 表格检索器执行失败（非致命）: {e}")
                import traceback
                logger.warning(traceback.format_exc())

        # 2. 融合结果
        if fusion_method == "rrf":
            fused_results = self._rrf_fusion(vector_results, keyword_results, top_k)
        elif fusion_method == "weighted":
            fused_results = self._weighted_fusion(vector_results, keyword_results, top_k,
                                                 vector_weight, keyword_weight)
        else:  # simple
            fused_results = self._simple_fusion(vector_results, keyword_results, top_k)

        # 3. 可选重排序
        if use_rerank and len(fused_results) > 1:
            logger.info("执行重排序...")
            fused_results = self._rerank_with_cross_encoder(query, fused_results)

        logger.debug(f"融合后结果: {len(fused_results)} 个")

        # 方案3-Beta: 片段补全和限制提取
        fused_results = self._complete_and_extract_restrictions(fused_results)

        return fused_results
    
    def _vector_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """向量检索"""
        try:
            # 向量化查询
            logger.debug(f"🔍 向量化查询: '{query}'")
            query_vector = self.embedding_service.embed_text(query)
            logger.debug(f"✅ 查询向量生成完成，维度: {len(query_vector)}")

            # 执行向量搜索
            results = self.vector_storage.search(
                query_vector=query_vector,
                top_k=top_k,
                score_threshold=0.1  # 降低阈值以提高召回
            )

            logger.debug(f"✅ 向量检索完成，返回 {len(results)} 个结果")

            # 添加检索类型标记
            for result in results:
                result["search_type"] = "vector"
                result["vector_score"] = result.get("score", 0)

            return results

        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _keyword_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        关键词检索 - 针对结构化内容优化
        """
        try:
            # 提取关键词
            keywords = self._extract_keywords(query)
            
            if not keywords:
                logger.warning(f"未提取到关键词: {query}")
                return []
            
            logger.debug(f"提取关键词: {keywords}")
            
            # 获取候选文档（优化：增加候选数量以提高召回）
            candidate_docs = self._get_candidate_documents_for_keywords(keywords, limit=top_k*8)
            
            # 执行关键词匹配和评分
            scored_docs = []
            
            for doc in candidate_docs:
                text = doc.get("text", "")
                metadata = doc.get("metadata", {})
                
                # 计算关键词匹配分数
                keyword_score = self._calculate_keyword_score(text, keywords, metadata)
                
                if keyword_score > 0.05:  # 优化：降低阈值以捕获更多相关结果
                    doc_copy = doc.copy()
                    doc_copy["search_type"] = "keyword"
                    doc_copy["keyword_score"] = keyword_score
                    doc_copy["score"] = keyword_score  # 统一字段
                    scored_docs.append(doc_copy)
            
            # 按分数排序
            scored_docs.sort(key=lambda x: x["keyword_score"], reverse=True)
            
            return scored_docs[:top_k]
            
        except Exception as e:
            logger.error(f"关键词检索失败: {e}")
            return []
    
    def _extract_keywords(self, query: str) -> List[str]:
        """从查询中提取关键词"""
        keywords = []

        # 1. 优先提取长中文短语（4-10个字）- 用于精确匹配
        long_phrases = re.findall(r'[\u4e00-\u9fa5]{4,10}', query)
        keywords.extend(long_phrases)

        # 2. 提取中短中文短语（2-3个字）
        short_phrases = re.findall(r'[\u4e00-\u9fa5]{2,3}', query)
        keywords.extend(short_phrases)

        # 3. 数字+中文组合（如"29元"、"6星"、"129+"等）
        number_chinese = re.findall(r'\d+[元GB级星级月笔C%天]+[A-Z+]?|\d+\+[元天]?|\d+元\s*\+?', query)
        keywords.extend(number_chinese)

        # 4. 产品ID模式（如"prod.10086000050315"）
        product_ids = re.findall(r'(?:prod|product|id)?\.?\s*\d{10,}', query, re.IGNORECASE)
        keywords.extend(product_ids)

        # 5. 时间段模式（如"T3-T12"）
        time_patterns = re.findall(r'T\d+(?:\s*[-~到]\s*T\d+)?', query, re.IGNORECASE)
        keywords.extend(time_patterns)

        # 6. 英文关键词（提取有意义的单词）
        english_words = re.findall(r'\b[a-zA-Z]{3,}\b', query)
        stop_words = {'the', 'and', 'for', 'this', 'that', 'with', 'from', 'have', 'has', 'was', 'were'}
        english_keywords = [word.lower() for word in english_words
                          if word.lower() not in stop_words]
        keywords.extend(english_keywords)

        # 7. 纯数字关键词（3位以上，可能是ID、编号等）
        number_patterns = re.findall(r'\b\d{3,}\b', query)
        keywords.extend(number_patterns)

        # 8. 特殊符号+数字（如"6星C"中的"C"）
        special_patterns = re.findall(r'[A-Z]\d{1,3}|\d+[A-Z]', query)
        keywords.extend(special_patterns)

        # 去重（保持顺序）
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)

        # 按长度排序，优先保留长关键词
        unique_keywords.sort(key=len, reverse=True)

        return unique_keywords[:25]  # 限制关键词数量
    
    def _get_candidate_documents_for_keywords(self, keywords: List[str], limit: int = 100) -> List[Dict[str, Any]]:
        """获取可能包含关键词的候选文档"""
        # 简化版本：使用向量搜索获取相关文档
        # 生产环境应该建立倒排索引
        try:
            # 使用第一个关键词进行向量搜索获取候选集
            if keywords:
                query_vector = self.embedding_service.embed_text(keywords[0])
                results = self.vector_storage.search(
                    query_vector=query_vector,
                    top_k=limit,
                    score_threshold=0.05
                )
                return results
            
            return []
            
        except Exception as e:
            logger.error(f"获取候选文档失败: {e}")
            return []
    
    def _calculate_keyword_score(self, text: str, keywords: List[str],
                                metadata: Dict[str, Any]) -> float:
        """计算关键词匹配分数"""
        if not text or not keywords:
            return 0.0

        text_lower = text.lower()
        total_score = 0.0

        # 按关键词长度排序，先处理长关键词（更精确）
        sorted_keywords = sorted(keywords, key=len, reverse=True)

        for keyword in sorted_keywords:
            keyword_lower = keyword.lower()

            # 1. 精确匹配（权重最高）
            if keyword_lower in text_lower:
                # 计算出现频率
                count = text_lower.count(keyword_lower)

                # 根据关键词长度和类型给予不同权重
                if len(keyword) >= 8:  # 长关键词（如产品ID）
                    weight = 5.0
                elif len(keyword) >= 5:  # 中等长度关键词
                    weight = 3.0
                elif len(keyword) >= 4:  # 短语
                    weight = 2.0
                else:  # 单个词
                    weight = 1.0

                total_score += count * weight

                # 位置权重（开头出现更重要）
                pos = text_lower.find(keyword_lower)
                if pos >= 0 and pos < 100:  # 前100字符
                    total_score += weight * 0.5

            # 2. 部分匹配（针对长关键词，容错）
            elif len(keyword) >= 4:
                # 检查是否包含关键词的主要部分
                for i in range(len(keyword) - 3):
                    substring = keyword[i:i+4].lower()
                    if substring in text_lower:
                        total_score += 0.3
                        break

        # 3. 元数据匹配（针对结构化内容）
        metadata_score = self._calculate_metadata_score(metadata, keywords)
        total_score += metadata_score * 5.0  # 元数据权重更高

        # 归一化到0-1范围（优化：提高归一化系数以允许更高分数）
        normalized_score = min(total_score / 40.0, 1.0)

        return normalized_score
    
    def _calculate_metadata_score(self, metadata: Dict[str, Any], 
                                 keywords: List[str]) -> float:
        """计算元数据匹配分数"""
        if not metadata:
            return 0.0
        
        metadata_score = 0.0
        
        # 检查特定字段（针对Excel等结构化内容）
        relevant_fields = [
            'filename', 'title', 'subject', 'category', 
            'department', 'project', 'id', 'number', 'code',
            'author', 'creator', 'tags', 'keywords'
        ]
        
        for field in relevant_fields:
            if field in metadata:
                field_value = str(metadata[field]).lower()
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower in field_value:
                        metadata_score += 2.0  # 元数据匹配权重更高
                        break  # 每个字段只匹配一次
        
        return min(metadata_score / 10.0, 1.0)
    
    def _rrf_fusion(self, vector_results: List[Dict], 
                   keyword_results: List[Dict], 
                   top_k: int) -> List[Dict[str, Any]]:
        """
        RRF（Reciprocal Rank Fusion）融合
        公式：score = 1 / (k + rank)
        """
        k = 50  # RRF常数（优化：降低k值以提高融合效果）
        
        # 构建文档ID到信息的映射
        doc_info = {}
        
        # 处理向量检索结果
        for rank, result in enumerate(vector_results, 1):
            doc_id = result.get("id")
            if doc_id:
                if doc_id not in doc_info:
                    doc_info[doc_id] = {
                        "data": result,
                        "vector_rank": rank,
                        "keyword_rank": None,
                        "scores": {"vector": result.get("score", 0)}
                    }
                else:
                    doc_info[doc_id]["vector_rank"] = rank
                    doc_info[doc_id]["scores"]["vector"] = result.get("score", 0)
        
        # 处理关键词检索结果
        for rank, result in enumerate(keyword_results, 1):
            doc_id = result.get("id")
            if doc_id:
                if doc_id not in doc_info:
                    doc_info[doc_id] = {
                        "data": result,
                        "vector_rank": None,
                        "keyword_rank": rank,
                        "scores": {"keyword": result.get("score", 0)}
                    }
                else:
                    doc_info[doc_id]["keyword_rank"] = rank
                    doc_info[doc_id]["scores"]["keyword"] = result.get("score", 0)
        
        # 计算RRF分数
        fused_results = []
        for doc_id, info in doc_info.items():
            rrf_score = 0.0
            
            # 向量检索RRF分数
            if info["vector_rank"] is not None:
                rrf_score += 1.0 / (k + info["vector_rank"])
            
            # 关键词检索RRF分数
            if info["keyword_rank"] is not None:
                rrf_score += 1.0 / (k + info["keyword_rank"])
            
            # 构建融合结果
            fused_result = info["data"].copy()
            fused_result["fusion_score"] = rrf_score
            fused_result["original_scores"] = info["scores"]
            fused_result["fusion_method"] = "rrf"
            
            # 添加排名信息
            fused_result["ranks"] = {
                "vector": info["vector_rank"],
                "keyword": info["keyword_rank"]
            }
            
            fused_results.append(fused_result)
        
        # 按融合分数排序
        fused_results.sort(key=lambda x: x.get("fusion_score", 0), reverse=True)
        
        return fused_results[:top_k]
    
    def _weighted_fusion(self, vector_results: List[Dict], 
                        keyword_results: List[Dict], 
                        top_k: int,
                        vector_weight: float,
                        keyword_weight: float) -> List[Dict[str, Any]]:
        """
        加权融合
        公式：score = vector_weight * vector_score + keyword_weight * keyword_score
        """
        # 构建文档ID到分数的映射
        doc_scores = defaultdict(lambda: {"vector": 0.0, "keyword": 0.0, "data": None})
        
        # 处理向量检索结果
        for result in vector_results:
            doc_id = result.get("id")
            if doc_id:
                doc_scores[doc_id]["vector"] = result.get("score", 0)
                doc_scores[doc_id]["data"] = result
        
        # 处理关键词检索结果
        for result in keyword_results:
            doc_id = result.get("id")
            if doc_id:
                doc_scores[doc_id]["keyword"] = result.get("score", 0)
                if doc_scores[doc_id]["data"] is None:
                    doc_scores[doc_id]["data"] = result
        
        # 计算加权分数
        fused_results = []
        for doc_id, scores in doc_scores.items():
            if scores["data"]:
                # 归一化处理
                vector_score_norm = min(scores["vector"] * 2, 1.0)  # 假设向量分数在0-0.5范围
                keyword_score_norm = scores["keyword"]  # 关键词分数已在0-1范围
                
                weighted_score = (
                    vector_weight * vector_score_norm + 
                    keyword_weight * keyword_score_norm
                )
                
                fused_result = scores["data"].copy()
                fused_result["fusion_score"] = weighted_score
                fused_result["original_scores"] = {
                    "vector": scores["vector"],
                    "keyword": scores["keyword"],
                    "vector_norm": vector_score_norm,
                    "keyword_norm": keyword_score_norm
                }
                fused_result["fusion_method"] = "weighted"
                
                fused_results.append(fused_result)
        
        # 按加权分数排序
        fused_results.sort(key=lambda x: x.get("fusion_score", 0), reverse=True)
        
        return fused_results[:top_k]
    
    def _simple_fusion(self, vector_results: List[Dict], 
                      keyword_results: List[Dict], 
                      top_k: int) -> List[Dict[str, Any]]:
        """简单融合（去重合并）"""
        seen_ids = set()
        fused_results = []
        
        # 优先添加向量检索结果
        for result in vector_results:
            doc_id = result.get("id")
            if doc_id and doc_id not in seen_ids:
                result["fusion_method"] = "simple"
                result["fusion_score"] = result.get("score", 0)
                fused_results.append(result)
                seen_ids.add(doc_id)
                if len(fused_results) >= top_k:
                    break
        
        # 补充关键词检索结果
        for result in keyword_results:
            doc_id = result.get("id")
            if doc_id and doc_id not in seen_ids and len(fused_results) < top_k:
                result["fusion_method"] = "simple"
                result["fusion_score"] = result.get("score", 0)
                fused_results.append(result)
                seen_ids.add(doc_id)
        
        return fused_results[:top_k]
    
    def _rerank_with_cross_encoder(self, query: str, 
                                  candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用Cross-Encoder重排序
        """
        try:
            # 按需加载重排序模型
            if self._reranker is None:
                try:
                    from sentence_transformers import CrossEncoder
                    logger.info("加载重排序模型...")
                    # 使用轻量级模型
                    self._reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
                    logger.info("重排序模型加载完成")
                except ImportError:
                    logger.warning("未安装sentence-transformers[cross-encoder]，跳过重排序")
                    return candidates
                except Exception as e:
                    logger.error(f"加载重排序模型失败: {e}")
                    return candidates
            
            # 准备输入对
            pairs = []
            valid_candidates = []
            
            for candidate in candidates:
                text = candidate.get("text", "")
                if text and len(text.strip()) > 10:  # 确保有足够的文本内容
                    pairs.append([query, text])
                    valid_candidates.append(candidate)
            
            if not pairs:
                return candidates
            
            # 预测相关性分数
            scores = self._reranker.predict(pairs)
            
            # 更新分数
            for i, (candidate, score) in enumerate(zip(valid_candidates, scores)):
                original_score = candidate.get("fusion_score", candidate.get("score", 0))
                # 结合原始分数和重排序分数
                candidate["rerank_score"] = float(score)
                candidate["final_score"] = (original_score + float(score)) / 2
                candidate["reranked"] = True
            
            # 按最终分数排序
            valid_candidates.sort(key=lambda x: x.get("final_score", 0), reverse=True)
            
            # 合并结果
            final_results = []
            for candidate in valid_candidates:
                final_results.append(candidate)
            
            # 添加未重排序的结果
            reranked_ids = {c.get("id") for c in valid_candidates if c.get("id")}
            for candidate in candidates:
                if candidate.get("id") not in reranked_ids:
                    candidate["reranked"] = False
                    final_results.append(candidate)
            
            return final_results
            
        except Exception as e:
            logger.error(f"重排序失败: {e}")
            return candidates
    
    def search_with_filters(self, query: str, filters: Dict[str, Any],
                           top_k: int = 10) -> List[Dict[str, Any]]:
        """
        带过滤条件的搜索
        """
        # 先执行混合搜索
        results = self.hybrid_search(query, top_k=top_k*2)
        
        if not results or not filters:
            return results[:top_k]
        
        # 应用过滤器
        filtered_results = []
        for result in results:
            metadata = result.get("metadata", {})
            match = True
            
            for key, value in filters.items():
                if key in metadata:
                    metadata_value = metadata[key]
                    
                    if isinstance(value, list):
                        # 列表匹配：值在列表中
                        if metadata_value not in value:
                            match = False
                            break
                    elif isinstance(value, dict):
                        # 字典匹配：支持范围等操作
                        if 'min' in value and metadata_value < value['min']:
                            match = False
                            break
                        if 'max' in value and metadata_value > value['max']:
                            match = False
                            break
                    else:
                        # 精确匹配
                        if metadata_value != value:
                            match = False
                            break
                else:
                    # 字段不存在
                    match = False
                    break
            
            if match:
                filtered_results.append(result)
                if len(filtered_results) >= top_k:
                    break
        
        return filtered_results

    def _complete_and_extract_restrictions(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        方案3-Beta: 补全被截断的序号并提取限制信息

        处理向量数据库中序号被截断的问题（如"1不可办理" -> "1. 不可办理"）
        """
        logger.info(f"[方案3-Beta] 开始处理 {len(results)} 个检索结果")

        try:
            from services.fragment_completion import get_fragment_processor
            fragment_processor = get_fragment_processor()
            logger.info("[方案3-Beta] 片段处理器加载成功")
        except ImportError:
            logger.warning("片段补全处理器不可用")
            return results

        enhanced_results = []
        total_restrictions = 0

        for i, result in enumerate(results):
            text = result.get('text', '')
            original_text = text

            # 1. 补全被截断的序号
            completed_text = fragment_processor.complete_fragments(text)

            # 2. 提取限制信息
            restrictions = fragment_processor.extract_restrictions_from_text(completed_text)

            # 3. 如果检测到限制信息，添加到结果的末尾
            if restrictions:
                restriction_note = f"\n【重要限制】\n" + "\n".join(f"  • {r}" for r in restrictions[:3])
                completed_text += restriction_note
                total_restrictions += len(restrictions)
                logger.debug(f"为文档 {i} 添加了 {len(restrictions)} 个限制信息")

            # 更新结果
            result['text'] = completed_text
            result['original_text'] = original_text  # 保留原始文本
            if restrictions:
                result['restrictions'] = restrictions

            enhanced_results.append(result)

        if total_restrictions > 0:
            logger.info(f"✅ 方案3-Beta: 片段补全完成，{total_restrictions} 个限制信息被添加")
        else:
            logger.info("[方案3-Beta] 片段补全完成，但未检测到限制信息")

        return enhanced_results