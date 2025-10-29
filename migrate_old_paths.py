#!/usr/bin/env python3
"""
舊路徑遷移工具

自動偵測並遷移以下舊路徑的檔案：
- ~/gemini_videos → ~/Saki_Studio/ChatGemini_SakiTool/OUTPUTS/videos/
- ~/gemini_images → ~/Saki_Studio/ChatGemini_SakiTool/OUTPUTS/images/
- ~/SakiStudio/ChatGemini/ChatLOG → ~/Saki_Studio/ChatGemini_SakiTool/LOGS/

使用方法：
    python migrate_old_paths.py [--dry-run] [--backup]

參數：
    --dry-run: 只顯示要遷移的檔案，不實際執行
    --backup: 遷移前備份原始檔案
"""

import os
import shutil
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

OLD_PATHS = {
    "gemini_videos": Path.home() / "gemini_videos",
    "gemini_images": Path.home() / "gemini_images",
    "saki_studio_old": Path.home() / "SakiStudio" / "ChatGemini" / "ChatLOG",
}

NEW_PATHS = {
    "gemini_videos": Path.home() / "Saki_Studio" / "ChatGemini_SakiTool" / "OUTPUTS" / "videos",
    "gemini_images": Path.home() / "Saki_Studio" / "ChatGemini_SakiTool" / "OUTPUTS" / "images",
    "saki_studio_old": Path.home() / "Saki_Studio" / "ChatGemini_SakiTool" / "LOGS",
}

def scan_old_paths():
    """掃描舊路徑中的檔案"""
    files_to_migrate = {}

    for key, old_path in OLD_PATHS.items():
        if old_path.exists():
            files = list(old_path.rglob('*'))
            files = [f for f in files if f.is_file()]

            if files:
                files_to_migrate[key] = files
                console.print(f"[#DDA0DD]發現舊路徑：{old_path}[/#DDA0DD]")
                console.print(f"  檔案數量：{len(files)}")

    return files_to_migrate

def migrate_files(files_to_migrate, dry_run=False, backup=False):
    """遷移檔案到新路徑"""
    total_files = sum(len(files) for files in files_to_migrate.values())

    if dry_run:
        console.print("\n[#DDA0DD]===== 預覽模式 =====")
        console.print("以下檔案將被遷移：\n")
        for key, files in files_to_migrate.items():
            console.print(f"[#87CEEB]{key}[/#87CEEB]：{len(files)} 個檔案")
            for f in files[:5]:  # 只顯示前 5 個
                console.print(f"  - {f}")
            if len(files) > 5:
                console.print(f"  ... 還有 {len(files) - 5} 個檔案")
        console.print("\n執行遷移請移除 --dry-run 參數")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("遷移中...", total=total_files)

        for key, files in files_to_migrate.items():
            old_path = OLD_PATHS[key]
            new_path = NEW_PATHS[key]

            # 創建新路徑
            new_path.mkdir(parents=True, exist_ok=True)

            for file in files:
                try:
                    # 計算相對路徑
                    rel_path = file.relative_to(old_path)
                    target = new_path / rel_path

                    # 創建目標目錄
                    target.parent.mkdir(parents=True, exist_ok=True)

                    # 備份（如果需要）
                    if backup:
                        backup_path = file.parent / f"{file.name}.backup"
                        shutil.copy2(file, backup_path)

                    # 遷移檔案
                    shutil.move(str(file), str(target))

                    progress.update(task, advance=1)
                except Exception as e:
                    console.print(f"[red]遷移失敗：{file} → {e}[/red]")

        progress.update(task, description="[green]遷移完成！")

    console.print(f"\n[green]✓ 成功遷移 {total_files} 個檔案[/green]")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="舊路徑遷移工具")
    parser.add_argument("--dry-run", action="store_true", help="只預覽，不實際執行")
    parser.add_argument("--backup", action="store_true", help="遷移前備份")
    args = parser.parse_args()

    console.print("\n[#87CEEB]===== 舊路徑遷移工具 =====\n")

    # 掃描舊路徑
    files_to_migrate = scan_old_paths()

    if not files_to_migrate:
        console.print("[green]✓ 未發現需要遷移的檔案[/green]")
        return

    # 執行遷移
    migrate_files(files_to_migrate, dry_run=args.dry_run, backup=args.backup)

if __name__ == "__main__":
    main()
