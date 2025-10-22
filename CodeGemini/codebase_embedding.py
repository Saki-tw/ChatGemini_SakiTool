#!/usr/bin/env python3
"""
CodeGemini Codebase Embedding Module
程式碼庫 Embedding 模組 - 提供深度程式碼理解功能

此模組負責：
1. 對整個 codebase 建立 embedding
2. 搜尋相似程式碼
3. 獲取檔案上下文
4. 深度理解程式碼結構

技術棧：
- Gemini Text Embedding API（免費）
- SQLite + NumPy（輕量級向量資料庫）
- 支援 Python 3.14+
"""

import logging
import sqlite3
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib

# 設置 logger
logger = logging.getLogger(__name__)


@dataclass
class CodeChunk:
    """程式碼分塊資料結構"""
    file_path: str
    chunk_id: str
    content: str
    chunk_type: str  # 'function', 'class', 'file', 'conversation'
    start_line: int
    end_line: int
    language: str
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None  # 額外的元數據（如對話時間、用戶 ID 等）

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return asdict(self)


class VectorDatabase:
    """輕量級向量資料庫（基於 SQLite + NumPy）

    替代 ChromaDB，支援 Python 3.14+
    """

    def __init__(self, db_path: str = ".embeddings/vector.db"):
        """初始化向量資料庫

        Args:
            db_path: 資料庫檔案路徑
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self._create_tables()
        logger.info(f"✓ VectorDatabase 已初始化: {self.db_path}")

    def _create_tables(self):
        """建立資料表"""
        cursor = self.conn.cursor()

        # 儲存程式碼分塊與 embedding
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_chunks (
                chunk_id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_type TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                language TEXT NOT NULL,
                embedding BLOB,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 建立索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_path
            ON code_chunks(file_path)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_type
            ON code_chunks(chunk_type)
        """)

        self.conn.commit()

    def add_chunk(self, chunk: CodeChunk):
        """新增程式碼分塊

        Args:
            chunk: CodeChunk 實例
        """
        cursor = self.conn.cursor()

        # 將 embedding 轉換為 numpy array 並序列化
        embedding_blob = None
        if chunk.embedding:
            embedding_blob = np.array(chunk.embedding, dtype=np.float32).tobytes()

        # 將 metadata 序列化為 JSON
        metadata_json = None
        if chunk.metadata:
            metadata_json = json.dumps(chunk.metadata, ensure_ascii=False)

        cursor.execute("""
            INSERT OR REPLACE INTO code_chunks
            (chunk_id, file_path, content, chunk_type, start_line, end_line, language, embedding, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chunk.chunk_id,
            chunk.file_path,
            chunk.content,
            chunk.chunk_type,
            chunk.start_line,
            chunk.end_line,
            chunk.language,
            embedding_blob,
            metadata_json
        ))

        self.conn.commit()

    def get_chunk(self, chunk_id: str) -> Optional[CodeChunk]:
        """獲取程式碼分塊

        Args:
            chunk_id: 分塊 ID

        Returns:
            CodeChunk 實例或 None
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT chunk_id, file_path, content, chunk_type, start_line, end_line, language, embedding, metadata
            FROM code_chunks
            WHERE chunk_id = ?
        """, (chunk_id,))

        row = cursor.fetchone()
        if not row:
            return None

        # 反序列化 embedding
        embedding = None
        if row[7]:
            embedding = np.frombuffer(row[7], dtype=np.float32).tolist()

        # 反序列化 metadata
        metadata = None
        if row[8]:
            metadata = json.loads(row[8])

        return CodeChunk(
            chunk_id=row[0],
            file_path=row[1],
            content=row[2],
            chunk_type=row[3],
            start_line=row[4],
            end_line=row[5],
            language=row[6],
            embedding=embedding,
            metadata=metadata
        )

    def get_all_chunks(self) -> List[CodeChunk]:
        """獲取所有程式碼分塊

        Returns:
            CodeChunk 列表
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT chunk_id, file_path, content, chunk_type, start_line, end_line, language, embedding, metadata
            FROM code_chunks
        """)

        chunks = []
        for row in cursor.fetchall():
            embedding = None
            if row[7]:
                embedding = np.frombuffer(row[7], dtype=np.float32).tolist()

            metadata = None
            if row[8]:
                metadata = json.loads(row[8])

            chunks.append(CodeChunk(
                chunk_id=row[0],
                file_path=row[1],
                content=row[2],
                chunk_type=row[3],
                start_line=row[4],
                end_line=row[5],
                language=row[6],
                embedding=embedding,
                metadata=metadata
            ))

        return chunks

    def search_similar(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[CodeChunk, float]]:
        """搜尋相似程式碼分塊

        Args:
            query_embedding: 查詢向量
            top_k: 返回前 k 個結果

        Returns:
            (CodeChunk, similarity_score) 列表，按相似度排序
        """
        all_chunks = self.get_all_chunks()

        if not all_chunks:
            return []

        # 計算餘弦相似度
        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)

        results = []
        for chunk in all_chunks:
            if not chunk.embedding:
                continue

            chunk_vec = np.array(chunk.embedding, dtype=np.float32)
            chunk_norm = np.linalg.norm(chunk_vec)

            # 餘弦相似度
            if query_norm > 0 and chunk_norm > 0:
                similarity = np.dot(query_vec, chunk_vec) / (query_norm * chunk_norm)
                results.append((chunk, float(similarity)))

        # 排序並返回前 k 個
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def delete_file_chunks(self, file_path: str):
        """刪除指定檔案的所有分塊

        Args:
            file_path: 檔案路徑
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM code_chunks WHERE file_path = ?", (file_path,))
        self.conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """獲取資料庫統計資訊

        Returns:
            統計資訊字典
        """
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM code_chunks")
        total_chunks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT file_path) FROM code_chunks")
        total_files = cursor.fetchone()[0]

        cursor.execute("SELECT chunk_type, COUNT(*) FROM code_chunks GROUP BY chunk_type")
        chunk_type_counts = dict(cursor.fetchall())

        return {
            'total_chunks': total_chunks,
            'total_files': total_files,
            'chunk_type_counts': chunk_type_counts,
            'db_path': str(self.db_path),
            'db_size_mb': round(self.db_path.stat().st_size / 1024 / 1024, 2) if self.db_path.exists() else 0
        }

    def close(self):
        """關閉資料庫連接"""
        self.conn.close()


class CodebaseEmbedding:
    """程式碼庫 Embedding 管理器

    功能：
    - 對整個 codebase 建立 embedding
    - 搜尋相似程式碼
    - 獲取檔案上下文
    - 深度理解程式碼結構

    使用 Gemini Text Embedding API（免費）
    """

    # 支援的程式語言副檔名
    SUPPORTED_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'jsx',
        '.tsx': 'tsx',
        '.go': 'go',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.sh': 'bash',
        '.md': 'markdown'
    }

    def __init__(
        self,
        vector_db_path: str = ".embeddings",
        api_key: Optional[str] = None,
        collection_name: str = "codebase",
        orthogonal_mode: bool = False,
        similarity_threshold: float = 0.85
    ):
        """初始化 Codebase Embedding

        Args:
            vector_db_path: 向量資料庫路徑
            api_key: Gemini API Key
            collection_name: Collection 名稱（保留參數，與 ChromaDB 兼容）
            orthogonal_mode: 是否啟用正交模式（保持內容線性獨立）
            similarity_threshold: 正交模式下的相似度閾值（預設 0.85）
        """
        try:
            import google.generativeai as genai
            self.genai = genai
            self.has_genai = True

            if api_key:
                genai.configure(api_key=api_key)
                logger.info("✓ Gemini API 已配置")

        except ImportError:
            self.genai = None
            self.has_genai = False
            logger.warning("✗ google-generativeai 未安裝，Embedding 功能受限")

        # 初始化向量資料庫
        db_file = Path(vector_db_path) / "vector.db"
        self.vector_db = VectorDatabase(str(db_file))

        # 正交模式設定
        self.orthogonal_mode = orthogonal_mode
        self.similarity_threshold = similarity_threshold

        if orthogonal_mode:
            logger.info(f"✓ 正交模式已啟用（相似度閾值: {similarity_threshold}）")

        logger.info("✓ CodebaseEmbedding 已初始化")

    def _generate_chunk_id(self, file_path: str, start_line: int, end_line: int) -> str:
        """生成程式碼分塊的唯一 ID

        Args:
            file_path: 檔案路徑
            start_line: 起始行
            end_line: 結束行

        Returns:
            chunk_id (SHA256 hash)
        """
        unique_str = f"{file_path}:{start_line}-{end_line}"
        return hashlib.sha256(unique_str.encode()).hexdigest()[:16]

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """使用 Gemini API 生成 embedding

        Args:
            text: 文本內容

        Returns:
            embedding 向量（768維）或 None
        """
        if not self.has_genai:
            logger.warning("✗ Gemini API 未配置，無法生成 embedding")
            return None

        try:
            result = self.genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']

        except Exception as e:
            logger.error(f"✗ 生成 embedding 失敗: {e}")
            return None

    def _check_orthogonality(self, new_embedding: List[float], chunk_type: Optional[str] = None) -> Tuple[bool, float, Optional[str]]:
        """檢查新 embedding 是否與現有內容正交（線性獨立）

        Args:
            new_embedding: 新的 embedding 向量
            chunk_type: 限定檢查的分塊類型（可選，例如只檢查 'conversation'）

        Returns:
            (是否正交, 最高相似度, 最相似的 chunk_id)
        """
        if not self.orthogonal_mode:
            return True, 0.0, None

        # 獲取所有現有 chunks
        all_chunks = self.vector_db.get_all_chunks()

        # 過濾特定類型（如果指定）
        if chunk_type:
            all_chunks = [c for c in all_chunks if c.chunk_type == chunk_type]

        if not all_chunks:
            return True, 0.0, None

        # 計算與所有現有 embedding 的相似度
        new_vec = np.array(new_embedding, dtype=np.float32)
        new_norm = np.linalg.norm(new_vec)

        max_similarity = 0.0
        most_similar_id = None

        for chunk in all_chunks:
            if not chunk.embedding:
                continue

            chunk_vec = np.array(chunk.embedding, dtype=np.float32)
            chunk_norm = np.linalg.norm(chunk_vec)

            # 餘弦相似度
            if new_norm > 0 and chunk_norm > 0:
                similarity = float(np.dot(new_vec, chunk_vec) / (new_norm * chunk_norm))

                if similarity > max_similarity:
                    max_similarity = similarity
                    most_similar_id = chunk.chunk_id

        # 判斷是否正交（相似度低於閾值）
        is_orthogonal = max_similarity < self.similarity_threshold

        return is_orthogonal, max_similarity, most_similar_id

    def _chunk_code_simple(self, file_path: str, content: str, language: str) -> List[CodeChunk]:
        """簡單的程式碼分塊（按行數）

        Args:
            file_path: 檔案路徑
            content: 檔案內容
            language: 程式語言

        Returns:
            CodeChunk 列表
        """
        lines = content.split('\n')
        chunks = []

        # 每 50 行切成一個 chunk
        chunk_size = 50
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i+chunk_size]
            chunk_content = '\n'.join(chunk_lines)

            if not chunk_content.strip():
                continue

            chunk = CodeChunk(
                file_path=file_path,
                chunk_id=self._generate_chunk_id(file_path, i+1, min(i+chunk_size, len(lines))),
                content=chunk_content,
                chunk_type='file',
                start_line=i+1,
                end_line=min(i+chunk_size, len(lines)),
                language=language
            )
            chunks.append(chunk)

        return chunks

    def embed_file(self, file_path: str) -> int:
        """對單個檔案建立 embedding

        Args:
            file_path: 檔案路徑

        Returns:
            成功建立 embedding 的分塊數量
        """
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            logger.error(f"✗ 檔案不存在: {file_path}")
            return 0

        # 檢查檔案副檔名
        ext = file_path_obj.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            logger.warning(f"⚠ 不支援的檔案類型: {ext} ({file_path})")
            return 0

        language = self.SUPPORTED_EXTENSIONS[ext]

        try:
            # 讀取檔案
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 分塊
            chunks = self._chunk_code_simple(str(file_path_obj), content, language)

            # 生成 embedding 並儲存
            success_count = 0
            skipped_count = 0
            for chunk in chunks:
                embedding = self._get_embedding(chunk.content)
                if embedding:
                    # 正交性檢查
                    is_orthogonal, max_sim, similar_id = self._check_orthogonality(
                        embedding,
                        chunk_type='file'
                    )

                    if is_orthogonal:
                        chunk.embedding = embedding
                        self.vector_db.add_chunk(chunk)
                        success_count += 1
                    else:
                        skipped_count += 1
                        logger.info(f"⊥ 跳過相似內容 (相似度: {max_sim:.4f}, 與 {similar_id} 相似)")

            if skipped_count > 0:
                logger.info(f"✓ {file_path}: {success_count}/{len(chunks)} chunks embedded (跳過 {skipped_count} 個重複內容)")
            else:
                logger.info(f"✓ {file_path}: {success_count}/{len(chunks)} chunks embedded")
            return success_count

        except Exception as e:
            logger.error(f"✗ 處理檔案失敗 ({file_path}): {e}")
            return 0

    def embed_codebase(
        self,
        root_path: str,
        extensions: Optional[List[str]] = None,
        exclude_dirs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """對整個 codebase 建立 embedding

        Args:
            root_path: 專案根目錄
            extensions: 要處理的副檔名列表（預設：所有支援的語言）
            exclude_dirs: 要排除的目錄列表（預設：常見的排除目錄）

        Returns:
            統計資訊字典
        """
        root_path_obj = Path(root_path)

        if not root_path_obj.exists():
            logger.error(f"✗ 目錄不存在: {root_path}")
            return {'success': False, 'error': 'Directory not found'}

        # 預設排除目錄
        if exclude_dirs is None:
            exclude_dirs = [
                'node_modules', '__pycache__', '.git', '.venv', 'venv',
                'build', 'dist', '.pytest_cache', '.mypy_cache', 'htmlcov'
            ]

        # 預設處理所有支援的語言
        if extensions is None:
            extensions = list(self.SUPPORTED_EXTENSIONS.keys())

        logger.info(f"🔍 開始掃描 codebase: {root_path}")
        logger.info(f"  支援的副檔名: {', '.join(extensions)}")
        logger.info(f"  排除的目錄: {', '.join(exclude_dirs)}")

        total_files = 0
        total_chunks = 0
        failed_files = []

        # 遍歷目錄
        for ext in extensions:
            for file_path in root_path_obj.rglob(f'*{ext}'):
                # 檢查是否在排除目錄中
                if any(excluded in file_path.parts for excluded in exclude_dirs):
                    continue

                # 處理檔案
                chunks_count = self.embed_file(str(file_path))
                if chunks_count > 0:
                    total_files += 1
                    total_chunks += chunks_count
                else:
                    failed_files.append(str(file_path))

        logger.info(f"✓ Codebase embedding 完成！")
        logger.info(f"  成功: {total_files} 個檔案, {total_chunks} 個分塊")
        if failed_files:
            logger.info(f"  失敗: {len(failed_files)} 個檔案")

        return {
            'success': True,
            'total_files': total_files,
            'total_chunks': total_chunks,
            'failed_files': failed_files,
            'root_path': str(root_path)
        }

    def search_similar_code(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜尋相似程式碼

        Args:
            query: 查詢文本
            top_k: 返回前 k 個結果

        Returns:
            搜尋結果列表
        """
        # 生成查詢 embedding
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            logger.error("✗ 無法生成查詢 embedding")
            return []

        # 搜尋相似分塊
        results = self.vector_db.search_similar(query_embedding, top_k=top_k)

        # 格式化結果
        formatted_results = []
        for chunk, similarity in results:
            formatted_results.append({
                'file_path': chunk.file_path,
                'chunk_id': chunk.chunk_id,
                'content': chunk.content,
                'chunk_type': chunk.chunk_type,
                'start_line': chunk.start_line,
                'end_line': chunk.end_line,
                'language': chunk.language,
                'similarity': round(similarity, 4)
            })

        return formatted_results

    def add_conversation(
        self,
        question: str,
        answer: str,
        timestamp: Optional[str] = None,
        session_id: Optional[str] = None,
        **metadata
    ) -> str:
        """新增對話記錄到向量資料庫

        Args:
            question: 使用者問題
            answer: AI 回答
            timestamp: 時間戳記（可選）
            session_id: 對話 Session ID（可選）
            **metadata: 其他元數據

        Returns:
            chunk_id
        """
        import time
        from datetime import datetime

        # 生成時間戳記
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        # 建立對話內容（問題 + 回答）
        conversation_content = f"Q: {question}\n\nA: {answer}"

        # 生成唯一 ID
        chunk_id = self._generate_chunk_id(
            file_path=f"conversation/{session_id or 'default'}",
            start_line=int(time.time()),
            end_line=0
        )

        # 建立 CodeChunk
        conversation_chunk = CodeChunk(
            file_path=f"conversation/{session_id or 'default'}",
            chunk_id=chunk_id,
            content=conversation_content,
            chunk_type='conversation',
            start_line=0,
            end_line=0,
            language='natural_language',
            metadata={
                'timestamp': timestamp,
                'session_id': session_id,
                'question': question,
                'answer': answer,
                **metadata
            }
        )

        # 生成 embedding
        embedding = self._get_embedding(conversation_content)
        if embedding:
            # 正交性檢查（只檢查對話類型）
            is_orthogonal, max_sim, similar_id = self._check_orthogonality(
                embedding,
                chunk_type='conversation'
            )

            if is_orthogonal:
                conversation_chunk.embedding = embedding
                self.vector_db.add_chunk(conversation_chunk)
                logger.info(f"✓ 對話記錄已新增: {chunk_id}")
                return chunk_id
            else:
                logger.warning(f"⊥ 重複對話內容 (相似度: {max_sim:.4f}, 與 {similar_id} 相似)")
                logger.info(f"  提示：此對話與已存在的對話過於相似，已跳過")
                return ""  # 返回空字串表示未新增
        else:
            logger.error("✗ 無法生成對話 embedding")
            return ""

    def search_conversations(
        self,
        query: str,
        top_k: int = 5,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜尋相關對話記錄

        Args:
            query: 查詢文本
            top_k: 返回前 k 個結果
            session_id: 限定特定 Session（可選）

        Returns:
            搜尋結果列表
        """
        # 生成查詢 embedding
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            logger.error("✗ 無法生成查詢 embedding")
            return []

        # 搜尋相似對話
        all_results = self.vector_db.search_similar(query_embedding, top_k=top_k * 2)

        # 過濾對話類型
        conversation_results = []
        for chunk, similarity in all_results:
            if chunk.chunk_type != 'conversation':
                continue

            # 如果指定了 session_id，則進一步過濾
            if session_id and chunk.metadata:
                if chunk.metadata.get('session_id') != session_id:
                    continue

            conversation_results.append({
                'chunk_id': chunk.chunk_id,
                'question': chunk.metadata.get('question') if chunk.metadata else '',
                'answer': chunk.metadata.get('answer') if chunk.metadata else '',
                'timestamp': chunk.metadata.get('timestamp') if chunk.metadata else '',
                'session_id': chunk.metadata.get('session_id') if chunk.metadata else '',
                'similarity': round(similarity, 4),
                'metadata': chunk.metadata
            })

            if len(conversation_results) >= top_k:
                break

        return conversation_results

    def analyze_orthogonality(self, chunk_type: Optional[str] = None) -> Dict[str, Any]:
        """分析資料庫中向量的正交性（線性獨立性）

        Args:
            chunk_type: 限定分析的分塊類型（可選）

        Returns:
            正交性分析報告
        """
        all_chunks = self.vector_db.get_all_chunks()

        # 過濾特定類型
        if chunk_type:
            all_chunks = [c for c in all_chunks if c.chunk_type == chunk_type]

        if len(all_chunks) < 2:
            return {
                'total_chunks': len(all_chunks),
                'chunk_type': chunk_type or 'all',
                'message': '資料不足（需至少 2 個 chunks）'
            }

        # 提取所有 embeddings
        embeddings = []
        chunk_ids = []
        for chunk in all_chunks:
            if chunk.embedding:
                embeddings.append(np.array(chunk.embedding, dtype=np.float32))
                chunk_ids.append(chunk.chunk_id)

        if len(embeddings) < 2:
            return {
                'total_chunks': len(all_chunks),
                'chunks_with_embedding': len(embeddings),
                'chunk_type': chunk_type or 'all',
                'message': '有效 embedding 不足'
            }

        # 計算所有向量之間的餘弦相似度
        n = len(embeddings)
        similarity_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(i+1, n):
                vec_i = embeddings[i]
                vec_j = embeddings[j]

                norm_i = np.linalg.norm(vec_i)
                norm_j = np.linalg.norm(vec_j)

                if norm_i > 0 and norm_j > 0:
                    similarity = float(np.dot(vec_i, vec_j) / (norm_i * norm_j))
                    similarity_matrix[i, j] = similarity
                    similarity_matrix[j, i] = similarity

        # 統計分析
        upper_triangle = similarity_matrix[np.triu_indices(n, k=1)]
        mean_similarity = float(np.mean(upper_triangle))
        max_similarity = float(np.max(upper_triangle))
        min_similarity = float(np.min(upper_triangle))
        std_similarity = float(np.std(upper_triangle))

        # 找出最相似的向量對
        max_idx = np.unravel_index(np.argmax(similarity_matrix), similarity_matrix.shape)
        most_similar_pair = (chunk_ids[max_idx[0]], chunk_ids[max_idx[1]], max_similarity)

        # 計算正交度（線性獨立性）
        # 正交度 = 1 - 平均相似度（越接近 1 越正交）
        orthogonality_score = 1.0 - mean_similarity

        # 統計相似度分佈
        high_similarity_count = int(np.sum(upper_triangle > 0.85))
        medium_similarity_count = int(np.sum((upper_triangle > 0.5) & (upper_triangle <= 0.85)))
        low_similarity_count = int(np.sum(upper_triangle <= 0.5))

        return {
            'total_chunks': n,
            'chunk_type': chunk_type or 'all',
            'orthogonality_score': round(orthogonality_score, 4),
            'similarity_stats': {
                'mean': round(mean_similarity, 4),
                'max': round(max_similarity, 4),
                'min': round(min_similarity, 4),
                'std': round(std_similarity, 4)
            },
            'most_similar_pair': {
                'chunk_1': most_similar_pair[0],
                'chunk_2': most_similar_pair[1],
                'similarity': round(most_similar_pair[2], 4)
            },
            'similarity_distribution': {
                'high (>0.85)': high_similarity_count,
                'medium (0.5-0.85)': medium_similarity_count,
                'low (<0.5)': low_similarity_count
            },
            'interpretation': self._interpret_orthogonality(orthogonality_score)
        }

    def _interpret_orthogonality(self, score: float) -> str:
        """解釋正交度分數

        Args:
            score: 正交度分數 (0-1)

        Returns:
            解釋文字
        """
        if score > 0.8:
            return "優秀：內容高度線性獨立，幾乎無重複"
        elif score > 0.6:
            return "良好：內容大多獨立，少量相似"
        elif score > 0.4:
            return "中等：存在一定程度的重複內容"
        elif score > 0.2:
            return "較差：重複內容較多，建議清理"
        else:
            return "極差：大量重複內容，強烈建議啟用正交模式"

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計資訊

        Returns:
            統計資訊字典
        """
        stats = self.vector_db.get_stats()
        stats['orthogonal_mode'] = self.orthogonal_mode
        stats['similarity_threshold'] = self.similarity_threshold
        return stats

    def close(self):
        """關閉資源"""
        self.vector_db.close()
        logger.info("✓ CodebaseEmbedding 已關閉")


# 模組級別函數（方便使用）
def create_codebase_embedding(
    root_path: str,
    api_key: Optional[str] = None,
    vector_db_path: str = ".embeddings"
) -> CodebaseEmbedding:
    """建立 Codebase Embedding 實例並處理整個 codebase

    Args:
        root_path: 專案根目錄
        api_key: Gemini API Key
        vector_db_path: 向量資料庫路徑

    Returns:
        CodebaseEmbedding 實例
    """
    embedding = CodebaseEmbedding(vector_db_path=vector_db_path, api_key=api_key)
    embedding.embed_codebase(root_path)
    return embedding


if __name__ == "__main__":
    # 測試用例
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("CodeGemini Codebase Embedding 測試")
    print("=" * 60)

    # 測試 VectorDatabase
    print("\n1. 測試 VectorDatabase")
    db = VectorDatabase(".test_embeddings/vector.db")

    # 建立測試分塊
    test_chunk = CodeChunk(
        file_path="test.py",
        chunk_id="test123",
        content="def hello():\n    print('Hello')",
        chunk_type="function",
        start_line=1,
        end_line=2,
        language="python",
        embedding=[0.1, 0.2, 0.3]
    )

    db.add_chunk(test_chunk)
    print(f"✓ 新增測試分塊: {test_chunk.chunk_id}")

    # 獲取分塊
    retrieved_chunk = db.get_chunk("test123")
    print(f"✓ 獲取分塊: {retrieved_chunk.chunk_id if retrieved_chunk else 'None'}")

    # 統計資訊
    stats = db.get_stats()
    print(f"✓ 統計資訊: {stats}")

    db.close()

    print("\n✓ 所有測試通過！")
