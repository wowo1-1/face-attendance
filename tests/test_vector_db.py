from __future__ import annotations

import numpy as np

import app.core.vector_db as vector_db


def _patch_faiss_paths(tmp_path, monkeypatch) -> None:
    # VectorDB 模块在 import 时把 config 常量拷贝到模块变量，这里直接 patch 模块变量，
    # 避免测试污染真实的 data/ 落盘文件。
    monkeypatch.setattr(vector_db, "FAISS_INDEX_PATH", str(tmp_path / "faces.index"))
    monkeypatch.setattr(vector_db, "FAISS_ID_MAP_PATH", str(tmp_path / "id_map.json"))


def test_add_search_remove_and_save_load_are_stable(tmp_path, monkeypatch) -> None:
    _patch_faiss_paths(tmp_path, monkeypatch)

    vdb = vector_db.VectorDB(dim=4)

    e1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    e2 = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
    e3 = np.array([0.0, 0.0, 1.0, 0.0], dtype=np.float32)

    fid1 = vdb.add(e1, student_id=101)
    fid2 = vdb.add(e2, student_id=102)
    fid3 = vdb.add(e3, student_id=103)
    assert [fid1, fid2, fid3] == [0, 1, 2]

    ids, scores = vdb.search(e2, top_k=1)
    assert ids == [102]
    assert len(scores) == 1
    assert scores[0] > 0.99

    assert vdb.remove(102) is True

    # 删除后不会复用旧 fid，避免 DB 里的 face_embedding_id 失效/错配。
    fid4 = vdb.add(e2, student_id=104)
    assert fid4 == 3

    ids2, scores2 = vdb.search(e2, top_k=1)
    assert ids2 == [104]
    assert len(scores2) == 1
    assert scores2[0] > 0.99

    vdb.save()

    vdb2 = vector_db.VectorDB(dim=4)
    _patch_faiss_paths(tmp_path, monkeypatch)
    vdb2.load()

    ids3, scores3 = vdb2.search(e2, top_k=1)
    assert ids3 == [104]
    assert len(scores3) == 1
    assert scores3[0] > 0.99


def test_dim_mismatch_raises_value_error(tmp_path, monkeypatch) -> None:
    _patch_faiss_paths(tmp_path, monkeypatch)

    vdb = vector_db.VectorDB(dim=4)
    bad = np.zeros((5,), dtype=np.float32)
    try:
        vdb.add(bad, student_id=1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on embedding dim mismatch")
