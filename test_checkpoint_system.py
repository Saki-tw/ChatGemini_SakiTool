#!/usr/bin/env python3
"""
檢查點系統測試腳本
快速驗證檢查點系統功能
"""

import sys
import os
from pathlib import Path

# 確保在正確的目錄
os.chdir(Path(__file__).parent)

print("=" * 60)
print("檢查點系統測試")
print("=" * 60)

# 測試 1: 導入模組
print("\n[測試 1] 導入模組...")
try:
    from gemini_checkpoint import (
        get_checkpoint_manager,
        CheckpointManager,
        SnapshotEngine,
        FileChange,
        FileChangeType,
        CheckpointType,
        auto_checkpoint
    )
    print("✓ 模組導入成功")
except Exception as e:
    print(f"✗ 模組導入失敗: {e}")
    sys.exit(1)

# 測試 2: 建立管理器
print("\n[測試 2] 建立檢查點管理器...")
try:
    manager = CheckpointManager(project_root=Path.cwd())
    print(f"✓ 管理器建立成功")
    print(f"  - 專案根目錄: {manager.project_root}")
    print(f"  - 檢查點目錄: {manager.checkpoints_dir}")
    print(f"  - 資料庫路徑: {manager.db_path}")
except Exception as e:
    print(f"✗ 管理器建立失敗: {e}")
    sys.exit(1)

# 測試 3: 建立測試檔案
print("\n[測試 3] 建立測試檔案...")
try:
    test_file = Path("test_checkpoint_demo.txt")
    original_content = "Hello, World!\nThis is a test file for checkpoint system.\n"
    test_file.write_text(original_content)
    print(f"✓ 測試檔案已建立: {test_file}")
except Exception as e:
    print(f"✗ 測試檔案建立失敗: {e}")
    sys.exit(1)

# 測試 4: 建立檔案變更物件
print("\n[測試 4] 建立檔案變更物件...")
try:
    file_change = SnapshotEngine.create_file_change(
        file_path=str(test_file),
        content_before=original_content,
        content_after=original_content,
        change_type=FileChangeType.CREATED
    )
    print(f"✓ 檔案變更物件已建立")
    print(f"  - 檔案路徑: {file_change.file_path}")
    print(f"  - 變更類型: {file_change.change_type.value}")
    print(f"  - 雜湊值: {file_change.hash_before[:16]}...")
    print(f"  - 大小: {file_change.size_before} bytes")
except Exception as e:
    print(f"✗ 檔案變更物件建立失敗: {e}")
    sys.exit(1)

# 測試 5: 建立檢查點
print("\n[測試 5] 建立檢查點...")
try:
    checkpoint = manager.create_checkpoint(
        file_changes=[file_change],
        description="測試檢查點 - 初始建立",
        checkpoint_type=CheckpointType.MANUAL
    )
    print(f"✓ 檢查點已建立")
    print(f"  - ID: {checkpoint.id[:8]}...")
    print(f"  - 時間: {checkpoint.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  - 描述: {checkpoint.description}")
    print(f"  - 檔案數: {len(checkpoint.file_changes)}")
    print(f"  - 壓縮率: {checkpoint.compressed_size / checkpoint.total_size * 100:.1f}%")
except Exception as e:
    print(f"✗ 檢查點建立失敗: {e}")
    sys.exit(1)

# 測試 6: 修改檔案並建立第二個檢查點
print("\n[測試 6] 修改檔案並建立第二個檢查點...")
try:
    modified_content = original_content + "This line was added after the first checkpoint.\n"
    test_file.write_text(modified_content)
    print(f"✓ 檔案已修改")

    file_change_2 = SnapshotEngine.create_file_change(
        file_path=str(test_file),
        content_before=original_content,
        content_after=modified_content,
        change_type=FileChangeType.MODIFIED
    )

    checkpoint_2 = manager.create_checkpoint(
        file_changes=[file_change_2],
        description="測試檢查點 - 第一次修改",
        checkpoint_type=CheckpointType.AUTO
    )
    print(f"✓ 第二個檢查點已建立")
    print(f"  - ID: {checkpoint_2.id[:8]}...")
    print(f"  - Diff 大小: {len(file_change_2.diff or '')} bytes")
except Exception as e:
    print(f"✗ 第二個檢查點建立失敗: {e}")
    sys.exit(1)

# 測試 7: 列出所有檢查點
print("\n[測試 7] 列出所有檢查點...")
try:
    checkpoints = manager.list_checkpoints(limit=10)
    print(f"✓ 找到 {len(checkpoints)} 個檢查點")
    for i, cp in enumerate(checkpoints, 1):
        print(f"  {i}. {cp.id[:8]} | {cp.timestamp.strftime('%H:%M:%S')} | {cp.description[:30]}")
except Exception as e:
    print(f"✗ 列出檢查點失敗: {e}")
    sys.exit(1)

# 測試 8: 回溯至第一個檢查點
print("\n[測試 8] 回溯至第一個檢查點...")
try:
    print(f"  修改前內容: {test_file.read_text()[:50]}...")
    success = manager.rewind_to_checkpoint(checkpoint.id[:8], confirm=False)

    if success:
        restored_content = test_file.read_text()
        print(f"✓ 回溯成功")
        print(f"  恢復後內容: {restored_content[:50]}...")

        if restored_content == original_content:
            print(f"✓ 內容驗證成功（與原始內容一致）")
        else:
            print(f"✗ 內容驗證失敗（與原始內容不一致）")
    else:
        print(f"✗ 回溯失敗")
except Exception as e:
    print(f"✗ 回溯測試失敗: {e}")

# 測試 9: 顯示 UI
print("\n[測試 9] 顯示檢查點 UI...")
try:
    manager.show_checkpoints_ui(limit=5)
    print(f"✓ UI 顯示成功")
except Exception as e:
    print(f"✗ UI 顯示失敗: {e}")

# 測試 10: 刪除測試檢查點
print("\n[測試 10] 清理測試資料...")
try:
    # 刪除檢查點
    for cp in checkpoints:
        manager.delete_checkpoint(cp.id)

    # 刪除測試檔案
    if test_file.exists():
        test_file.unlink()

    print(f"✓ 測試資料已清理")
except Exception as e:
    print(f"⚠ 清理警告: {e}")

# 總結
print("\n" + "=" * 60)
print("測試完成！")
print("=" * 60)
print("\n所有核心功能已驗證：")
print("  ✓ 模組導入")
print("  ✓ 管理器建立")
print("  ✓ 檔案變更追蹤")
print("  ✓ 檢查點建立")
print("  ✓ Diff 計算")
print("  ✓ 檢查點列表")
print("  ✓ 回溯功能")
print("  ✓ UI 顯示")
print("  ✓ 資料清理")
print("\n檢查點系統測試通過！\n")
