"""向量数据库模块 — 基于 FAISS IndexFlatIP + IndexIDMap2 的轻量向量检索

设计要点：
- 使用 Inner Product + L2 归一化近似 cosine similarity（分数越大越相似）。
- 外层使用 IndexIDMap2：用稳定的 fid 作为向量 ID，可安全落盘到数据库并支持删除。
- 兼容旧版落盘的 IndexFlatIP（内部 ID=插入顺序）：加载时会尝试迁移为 IndexIDMap2。
"""

import json
import os
import numpy as np
import faiss

from config import FAISS_INDEX_PATH, FAISS_ID_MAP_PATH


class VectorDB:
    def __init__(self, dim: int = 512):
        self.dim = int(dim)
        # 用 IndexIDMap2 包一层：用稳定的 fid 作为向量 ID，避免删除/重建导致 fid 变化，
        # 进而让数据库里的 face_embedding_id 失效。
        self.index = self._new_index(self.dim)
        # fid -> student_id
        self._id_map: dict[int, int] = {}
        # 下一个可用 fid（单调递增，不会因删除回退，避免复用导致冲突）
        self._next_id = 0

    @staticmethod
    def _new_index(dim: int) -> faiss.Index:
        base = faiss.IndexFlatIP(dim)
        return faiss.IndexIDMap2(base)

    def _prepare_vec(self, embedding: np.ndarray) -> np.ndarray:
        """转成 (1, dim) 的 float32 且 L2 归一化向量，用于 cosine/inner product 检索。"""
        vec = np.asarray(embedding, dtype=np.float32).reshape(-1)
        if vec.size != self.dim:
            raise ValueError(
                f"embedding dim mismatch: expected {self.dim}, got {vec.size}"
            )

        norm = float(np.linalg.norm(vec))
        if not np.isfinite(norm) or norm <= 0.0:
            # 避免除零/NaN；零向量对 IP 检索贡献为 0，不会误命中高分。
            vec = np.zeros((self.dim,), dtype=np.float32)
        else:
            vec = vec / norm
        return np.ascontiguousarray(vec.reshape(1, self.dim), dtype=np.float32)

    def add(self, embedding: np.ndarray, student_id: int) -> int:
        """添加归一化向量，返回稳定的向量 fid（可落盘到 DB）。"""
        vec = self._prepare_vec(embedding)
        fid = int(self._next_id)
        ids = np.array([fid], dtype=np.int64)
        self.index.add_with_ids(vec, ids)
        self._id_map[fid] = int(student_id)
        self._next_id = fid + 1
        return fid

    def search(
        self, embedding: np.ndarray, top_k: int = 1
    ) -> tuple[list[int], list[float]]:
        """检索最相似的 top_k 个，返回 (student_ids, scores)。

        注意：输出的 ids 与 scores 严格对齐（同一位置的 id/score 属于同一条命中）。
        """
        if self.index.ntotal == 0:
            return [], []
        if int(top_k) <= 0:
            return [], []
        vec = self._prepare_vec(embedding)
        k = min(int(top_k), int(self.index.ntotal))
        scores, fids = self.index.search(vec, k)

        student_ids: list[int] = []
        out_scores: list[float] = []
        for fid, score in zip(fids[0], scores[0]):
            fid_i = int(fid)
            if fid_i < 0:
                continue
            sid = self._id_map.get(fid_i)
            if sid is None:
                continue
            student_ids.append(int(sid))
            out_scores.append(float(score))

        return student_ids, out_scores

    def remove(self, student_id: int) -> bool:
        """删除指定 student_id 的向量（稳定删除，不重建）。

        返回值：
        - True: 至少删除了 1 条
        - False: 未找到该 student_id
        """
        fids = [fid for fid, sid in self._id_map.items() if sid == student_id]
        if not fids:
            return False

        ids = np.ascontiguousarray(fids, dtype=np.int64)
        # faiss Python bindings 新版支持直接传 numpy array；老版本再 fallback 到 selector。
        try:
            self.index.remove_ids(ids)
        except Exception:
            selector = faiss.IDSelectorBatch(int(ids.size), faiss.swig_ptr(ids))
            self.index.remove_ids(selector)
        for fid in fids:
            self._id_map.pop(fid, None)
        return True

    def save(self):
        """持久化索引和 id 映射"""
        faiss.write_index(self.index, FAISS_INDEX_PATH)
        with open(FAISS_ID_MAP_PATH, "w") as f:
            json.dump(
                {
                    "id_map": {str(k): v for k, v in self._id_map.items()},
                    "next_id": self._next_id,
                },
                f,
            )

    def load(self):
        """从文件加载索引和映射（必要时做向后兼容迁移）。"""
        if not os.path.exists(FAISS_INDEX_PATH) or not os.path.exists(
            FAISS_ID_MAP_PATH
        ):
            return

        loaded_index = faiss.read_index(FAISS_INDEX_PATH)
        with open(FAISS_ID_MAP_PATH) as f:
            data = json.load(f)
        id_map = {int(k): int(v) for k, v in data.get("id_map", {}).items()}
        next_id = int(data.get("next_id", 0))

        # 维度不一致时直接忽略旧索引，避免后续 add/search 崩溃。
        if hasattr(loaded_index, "d") and int(loaded_index.d) != self.dim:
            return

        # 兼容旧版：如果落盘的是 IndexFlatIP（内部 ID=插入顺序），迁移为 IndexIDMap2。
        if not isinstance(loaded_index, faiss.IndexIDMap):
            ntotal = int(loaded_index.ntotal)
            expected = list(range(ntotal))
            if sorted(id_map) != expected:
                # id_map 与 index 不一致，无法安全迁移；直接跳过加载避免错配。
                return
            if ntotal > 0:
                vecs = np.vstack(
                    [loaded_index.reconstruct(i) for i in range(ntotal)]
                ).astype(np.float32)
                migrated = self._new_index(self.dim)
                migrated.add_with_ids(vecs, np.arange(ntotal, dtype=np.int64))
                loaded_index = migrated
            else:
                loaded_index = self._new_index(self.dim)

        self.index = loaded_index
        self._id_map = id_map
        max_fid = max(id_map.keys(), default=-1)
        self._next_id = max(next_id, max_fid + 1)
