#!/usr/bin/env python3
"""
自動生成翻譯檔案
為所有新增的翻譯鍵生成專業的英文、日文和韓文翻譯
"""

import yaml
import re
from pathlib import Path
from typing import Dict, Any

# 新增模組的翻譯鍵映射
TRANSLATIONS = {
    # ==================== media.clip ====================
    "media.clip.analysis_title": {
        "en": "\\n[bold #E8C4F0]🎬 AI Clip Suggestion Analysis[/bold #E8C4F0]\\n",
        "ja": "\\n[bold #E8C4F0]🎬 AI クリップ提案分析[/bold #E8C4F0]\\n",
        "ko": "\\n[bold #E8C4F0]🎬 AI 클립 제안 분석[/bold #E8C4F0]\\n"
    },
    "media.clip.analyzing_features": {
        "en": "\\n[#E8C4F0]🔍 Analyzing video content features...[/#E8C4F0]",
        "ja": "\\n[#E8C4F0]🔍 動画コンテンツの特徴を分析中...[/#E8C4F0]",
        "ko": "\\n[#E8C4F0]🔍 비디오 콘텐츠 특성 분석 중...[/#E8C4F0]"
    },
    "media.clip.detailed_suggestions": {
        "en": "\\n[bold #E8C4F0]💡 Detailed Suggestions:[/bold #E8C4F0]\\n",
        "ja": "\\n[bold #E8C4F0]💡 詳細な提案：[/bold #E8C4F0]\\n",
        "ko": "\\n[bold #E8C4F0]💡 상세 제안:[/bold #E8C4F0]\\n"
    },
    "media.clip.generating_suggestions": {
        "en": "\\n[#E8C4F0]💡 Generating clip suggestions...[/#E8C4F0]",
        "ja": "\\n[#E8C4F0]💡 クリップ提案を生成中...[/#E8C4F0]",
        "ko": "\\n[#E8C4F0]💡 클립 제안 생성 중...[/#E8C4F0]"
    },
    "media.clip.no_suggestions": {
        "en": "[#E8C4F0]No clip suggestions generated[/#E8C4F0]",
        "ja": "[#E8C4F0]クリップ提案が生成されませんでした[/#E8C4F0]",
        "ko": "[#E8C4F0]클립 제안이 생성되지 않았습니다[/#E8C4F0]"
    },
    "media.clip.scene_detection": {
        "en": "\\n[#E8C4F0]📦 Performing scene detection...[/#E8C4F0]",
        "ja": "\\n[#E8C4F0]📦 シーン検出を実行中...[/#E8C4F0]",
        "ko": "\\n[#E8C4F0]📦 장면 감지 실행 중...[/#E8C4F0]"
    },

    # ==================== file.manager ====================
    "file.manager.cache.initialized": {
        "en": "File cache initialized (max capacity:{maxsize})",
        "ja": "ファイルキャッシュを初期化しました（最大容量：{maxsize}）",
        "ko": "파일 캐시가 초기화되었습니다（최대 용량：{maxsize}）"
    },
    "file.manager.cache.hit": {
        "en": "Cache hit:{file_path} (access count:{count})",
        "ja": "キャッシュヒット：{file_path}（アクセス回数：{count}）",
        "ko": "캐시 히트：{file_path}（액세스 횟수：{count}）"
    },
    "file.manager.cache.evicted": {
        "en": "Cache evicted:{file_path}",
        "ja": "キャッシュを削除しました：{file_path}",
        "ko": "캐시가 제거되었습니다：{file_path}"
    },
    "file.manager.cache.invalidated": {
        "en": "Cache invalidated:{file_path}",
        "ja": "キャッシュが無効化されました：{file_path}",
        "ko": "캐시가 무효화되었습니다：{file_path}"
    },
    "file.manager.cache.cleared": {
        "en": "Cache cleared",
        "ja": "キャッシュをクリアしました",
        "ko": "캐시가 지워졌습니다"
    },
    "file.manager.preloader.initialized": {
        "en": "Smart preloader initialized (minimum confidence:{confidence})",
        "ja": "スマートプリローダーを初期化しました（最小信頼度：{confidence}）",
        "ko": "스마트 프리로더가 초기화되었습니다（최소 신뢰도：{confidence}）"
    },
    "file.manager.preloader.related": {
        "en": "Preloading related files:{file_path} -> {related_files}",
        "ja": "関連ファイルをプリロード中：{file_path} -> {related_files}",
        "ko": "관련 파일 사전 로드 중：{file_path} -> {related_files}"
    },
    "file.manager.preloader.cleared": {
        "en": "Preloader statistics cleared",
        "ja": "プリローダーの統計をクリアしました",
        "ko": "프리로더 통계가 지워졌습니다"
    },
    "file.manager.read.error": {
        "en": "Failed to read file:{file_path}, error:{error}",
        "ja": "ファイルの読み取りに失敗しました：{file_path}、エラー：{error}",
        "ko": "파일 읽기 실패：{file_path}, 오류：{error}"
    },
    "file.manager.read.failed": {
        "en": "Failed to read file:{file_path}, error:{error}",
        "ja": "ファイルの読み取りに失敗しました：{file_path}、エラー：{error}",
        "ko": "파일 읽기 실패：{file_path}, 오류：{error}"
    },
    "file.manager.batch.error": {
        "en": "Batch file processing failed:{file_path}, error:{error}",
        "ja": "バッチファイル処理に失敗しました：{file_path}、エラー：{error}",
        "ko": "배치 파일 처리 실패：{file_path}, 오류：{error}"
    },
    "file.manager.pattern.attach": {
        "en": "attach",
        "ja": "添付",
        "ko": "첨부"
    },
    "file.manager.pattern.read": {
        "en": "read",
        "ja": "読み取り",
        "ko": "읽기"
    },
    "file.manager.pattern.upload": {
        "en": "upload",
        "ja": "アップロード",
        "ko": "업로드"
    },
    "file.manager.file.label": {
        "en": "File",
        "ja": "ファイル",
        "ko": "파일"
    },
    "file.manager.file.not_found": {
        "en": "File not found:{file_path}",
        "ja": "ファイルが見つかりません：{file_path}",
        "ko": "파일을 찾을 수 없습니다：{file_path}"
    },
    "file.manager.file.loaded": {
        "en": "File loaded:{file_path}",
        "ja": "ファイルを読み込みました：{file_path}",
        "ko": "파일이 로드되었습니다：{file_path}"
    },
    "file.manager.text.loaded": {
        "en": "Text file loaded:{file_path}",
        "ja": "テキストファイルを読み込みました：{file_path}",
        "ko": "텍스트 파일이 로드되었습니다：{file_path}"
    },
    "file.manager.text.loaded_latin1": {
        "en": "Text file loaded (Latin-1 encoding):{file_path}",
        "ja": "テキストファイルを読み込みました（Latin-1エンコーディング）：{file_path}",
        "ko": "텍스트 파일이 로드되었습니다（Latin-1 인코딩）：{file_path}"
    },
    "file.manager.media.uploaded": {
        "en": "Media file uploaded:{file_path}",
        "ja": "メディアファイルをアップロードしました：{file_path}",
        "ko": "미디어 파일이 업로드되었습니다：{file_path}"
    },
    "file.manager.media_viewer.error": {
        "en": "Media viewer error:{error}",
        "ja": "メディアビューアーエラー：{error}",
        "ko": "미디어 뷰어 오류：{error}"
    },
    "file.manager.upload.failed": {
        "en": "Upload failed:{file_path}, error:{error}",
        "ja": "アップロードに失敗しました：{file_path}、エラー：{error}",
        "ko": "업로드 실패：{file_path}, 오류：{error}"
    },
    "file.manager.upload.disabled": {
        "en": "File manager not enabled, cannot upload:{file_path}",
        "ja": "ファイルマネージャーが有効ではありません。アップロードできません：{file_path}",
        "ko": "파일 관리자가 활성화되지 않았습니다. 업로드할 수 없습니다：{file_path}"
    },
    "file.manager.unknown_type": {
        "en": "Unknown file type {ext}, attempting to read as text",
        "ja": "未知のファイルタイプ {ext}、テキストとして読み込みを試みます",
        "ko": "알 수 없는 파일 형식 {ext}, 텍스트로 읽기 시도"
    },
    "file.manager.process.failed": {
        "en": "File processing failed:{file_path}, error:{error}",
        "ja": "ファイル処理に失敗しました：{file_path}、エラー：{error}",
        "ko": "파일 처리 실패：{file_path}, 오류：{error}"
    },

    # ==================== flow.engine (部分鍵) ====================
    "flow.engine.analyzing_description": {
        "en": "\n[#E8C4F0]🤖 Analyzing user description...[/#E8C4F0]",
        "ja": "\n[#E8C4F0]🤖 ユーザーの説明を分析中...[/#E8C4F0]",
        "ko": "\n[#E8C4F0]🤖 사용자 설명 분석 중...[/#E8C4F0]"
    },
    "flow.engine.description_label": {
        "en": "  Description: {user_description}",
        "ja": "  説明：{user_description}",
        "ko": "  설명：{user_description}"
    },
    "flow.engine.target_duration_label": {
        "en": "  Target duration: {target_duration}s",
        "ja": "  目標時間：{target_duration}秒",
        "ko": "  목표 시간：{target_duration}초"
    },

    # ==================== upload.helper ====================
    "upload.helper.warning.retry_not_found": {
        "en": "⚠️  api_retry_wrapper not found, will not use automatic retry mechanism",
        "ja": "⚠️  api_retry_wrapper が見つかりません。自動リトライ機能を使用しません",
        "ko": "⚠️  api_retry_wrapper를 찾을 수 없습니다. 자동 재시도 메커니즘을 사용하지 않습니다"
    },
    "upload.helper.warning.error_fix_not_found": {
        "en": "⚠️  error_fix_suggestions not found, will not use intelligent error diagnostics",
        "ja": "⚠️  error_fix_suggestions が見つかりません。スマートエラー診断を使用しません",
        "ko": "⚠️  error_fix_suggestions를 찾을 수 없습니다. 스마트 오류 진단을 사용하지 않습니다"
    },
    "upload.helper.warning.file_modified": {
        "en": "[#E8C4F0]⚠️ File has been modified, cannot resume upload[/#E8C4F0]",
        "ja": "[#E8C4F0]⚠️ ファイルが変更されています。アップロードを再開できません[/#E8C4F0]",
        "ko": "[#E8C4F0]⚠️ 파일이 수정되었습니다. 업로드를 재개할 수 없습니다[/#E8C4F0]"
    },
    "upload.helper.error.load_progress_failed": {
        "en": "[#E8C4F0]⚠️ Failed to load progress file: {e}[/#E8C4F0]",
        "ja": "[#E8C4F0]⚠️ 進行状況ファイルの読み込みに失敗しました：{e}[/#E8C4F0]",
        "ko": "[#E8C4F0]⚠️ 진행 파일 로드 실패: {e}[/#E8C4F0]"
    },
    "upload.helper.error.save_progress_failed": {
        "en": "[#E8C4F0]⚠️ Failed to save progress file: {e}[/#E8C4F0]",
        "ja": "[#E8C4F0]⚠️ 進行状況ファイルの保存に失敗しました：{e}[/#E8C4F0]",
        "ko": "[#E8C4F0]⚠️ 진행 파일 저장 실패: {e}[/#E8C4F0]"
    },
    "upload.helper.error.delete_progress_failed": {
        "en": "[#E8C4F0]⚠️ Failed to delete progress file: {e}[/#E8C4F0]",
        "ja": "[#E8C4F0]⚠️ 進行状況ファイルの削除に失敗しました：{e}[/#E8C4F0]",
        "ko": "[#E8C4F0]⚠️ 진행 파일 삭제 실패: {e}[/#E8C4F0]"
    },
    "upload.helper.progress.uploading_chunks": {
        "en": "Uploading... ({uploaded}/{total} chunks)",
        "ja": "アップロード中...（{uploaded}/{total} チャンク）",
        "ko": "업로드 중... ({uploaded}/{total} 청크)"
    },
    "upload.helper.file_size.large": {
        "en": "large",
        "ja": "大",
        "ko": "대형"
    },
    "upload.helper.file_size.medium": {
        "en": "medium",
        "ja": "中",
        "ko": "중간"
    },

    # ==================== batch.processor ====================
    "batch.processor.status.pending": {
        "en": "Pending",
        "ja": "待機中",
        "ko": "대기 중"
    },
    "batch.processor.status.running": {
        "en": "Running",
        "ja": "実行中",
        "ko": "실행 중"
    },
    "batch.processor.status.completed": {
        "en": "Completed",
        "ja": "完了",
        "ko": "완료"
    },
    "batch.processor.status.failed": {
        "en": "Failed",
        "ja": "失敗",
        "ko": "실패"
    },
    "batch.processor.status.cancelled": {
        "en": "Cancelled",
        "ja": "キャンセル",
        "ko": "취소됨"
    },
    "batch.processor.handler_not_found": {
        "en": "Task handler not found: {task_type}",
        "ja": "タスクハンドラーが見つかりません：{task_type}",
        "ko": "작업 핸들러를 찾을 수 없습니다: {task_type}"
    },
    "batch.processor.processing_tasks": {
        "en": "Processing {total} tasks",
        "ja": "{total} 個のタスクを処理中",
        "ko": "{total}개의 작업 처리 중"
    },
    "batch.processor.no_pending_tasks": {
        "en": "No pending tasks",
        "ja": "待機中のタスクはありません",
        "ko": "대기 중인 작업이 없습니다"
    },
    "batch.processor.no_matching_tasks": {
        "en": "No matching tasks",
        "ja": "一致するタスクはありません",
        "ko": "일치하는 작업이 없습니다"
    },
    "batch.processor.task_not_found": {
        "en": "Task not found: {task_id}",
        "ja": "タスクが見つかりません：{task_id}",
        "ko": "작업을 찾을 수 없습니다: {task_id}"
    },
    "batch.processor.cannot_cancel_running": {
        "en": "Cannot cancel running task: {task_id}",
        "ja": "実行中のタスクはキャンセルできません：{task_id}",
        "ko": "실행 중인 작업은 취소할 수 없습니다: {task_id}"
    },
    "batch.processor.loaded_tasks": {
        "en": "[#E8C4F0]📂 Loaded {tasks_count} tasks[/#E8C4F0]",
        "ja": "[#E8C4F0]📂 {tasks_count} 個のタスクを読み込みました[/#E8C4F0]",
        "ko": "[#E8C4F0]📂 {tasks_count}개의 작업을 로드했습니다[/#E8C4F0]"
    },
    "batch.processor.registered_handler": {
        "en": "[#B565D8]✓ Registered task handler: {task_type}[/#B565D8]",
        "ja": "[#B565D8]✓ タスクハンドラーを登録しました：{task_type}[/#B565D8]",
        "ko": "[#B565D8]✓ 작업 핸들러를 등록했습니다: {task_type}[/#B565D8]"
    },
    "batch.processor.task_added": {
        "en": "[#B565D8]✓ Task added: {task_id}[/#B565D8]",
        "ja": "[#B565D8]✓ タスクを追加しました：{task_id}[/#B565D8]",
        "ko": "[#B565D8]✓ 작업이 추가되었습니다: {task_id}[/#B565D8]"
    },
    "batch.processor.tasks_batch_added": {
        "en": "[#B565D8]✓ Batch added {task_ids_count} tasks[/#B565D8]",
        "ja": "[#B565D8]✓ {task_ids_count} 個のタスクを一括追加しました[/#B565D8]",
        "ko": "[#B565D8]✓ {task_ids_count}개의 작업을 일괄 추가했습니다[/#B565D8]"
    },
    "batch.processor.task_started": {
        "en": "\n[#E8C4F0]▶️  Started task: {task_id}[/#E8C4F0]",
        "ja": "\n[#E8C4F0]▶️  タスクを開始しました：{task_id}[/#E8C4F0]",
        "ko": "\n[#E8C4F0]▶️  작업을 시작했습니다: {task_id}[/#E8C4F0]"
    },
    "batch.processor.task_completed": {
        "en": "[#B565D8]✅ Task completed: {task_id}[/#B565D8]",
        "ja": "[#B565D8]✅ タスクが完了しました：{task_id}[/#B565D8]",
        "ko": "[#B565D8]✅ 작업이 완료되었습니다: {task_id}[/#B565D8]"
    },
    "batch.processor.task_cancelled": {
        "en": "[#B565D8]✓ Task cancelled: {task_id}[/#B565D8]",
        "ja": "[#B565D8]✓ タスクをキャンセルしました：{task_id}[/#B565D8]",
        "ko": "[#B565D8]✓ 작업이 취소되었습니다: {task_id}[/#B565D8]"
    },
    "batch.processor.completed_tasks_cleared": {
        "en": "[#B565D8]✓ Cleared {completed_ids_count} completed tasks[/#B565D8]",
        "ja": "[#B565D8]✓ {completed_ids_count} 個の完了したタスクをクリアしました[/#B565D8]",
        "ko": "[#B565D8]✓ {completed_ids_count}개의 완료된 작업을 정리했습니다[/#B565D8]"
    },
    "batch.processor.batch_completed": {
        "en": "\n[bold green]✅ Batch processing completed![/bold green]",
        "ja": "\n[bold green]✅ バッチ処理が完了しました！[/bold green]",
        "ko": "\n[bold green]✅ 배치 처리가 완료되었습니다![/bold green]"
    },
    "batch.processor.load_tasks_failed": {
        "en": "[#E8C4F0]Failed to load tasks: {e}[/#E8C4F0]",
        "ja": "[#E8C4F0]タスクの読み込みに失敗しました：{e}[/#E8C4F0]",
        "ko": "[#E8C4F0]작업 로드 실패: {e}[/#E8C4F0]"
    },
    "batch.processor.save_tasks_failed": {
        "en": "[dim #E8C4F0]Failed to save tasks: {e}[/dim]",
        "ja": "[dim #E8C4F0]タスクの保存に失敗しました：{e}[/dim]",
        "ko": "[dim #E8C4F0]작업 저장 실패: {e}[/dim]"
    },
    "batch.processor.task_failed": {
        "en": "[dim #E8C4F0]❌ Task failed: {task_id} - {e}[/dim]",
        "ja": "[dim #E8C4F0]❌ タスクが失敗しました：{task_id} - {e}[/dim]",
        "ko": "[dim #E8C4F0]❌ 작업 실패: {task_id} - {e}[/dim]"
    },
    "batch.processor.retrying_task": {
        "en": "[#E8C4F0]🔄 Retrying task ({retry_count}/{max_retries}): {task_id}[/#E8C4F0]",
        "ja": "[#E8C4F0]🔄 タスクを再試行中（{retry_count}/{max_retries}）：{task_id}[/#E8C4F0]",
        "ko": "[#E8C4F0]🔄 작업 재시도 중 ({retry_count}/{max_retries}): {task_id}[/#E8C4F0]"
    },
    "batch.processor.starting_batch": {
        "en": "\n[bold #E8C4F0]🚀 Starting batch processing (max concurrent: {max_concurrent})[/bold #E8C4F0]\n",
        "ja": "\n[bold #E8C4F0]🚀 バッチ処理を開始します（最大並行数：{max_concurrent}）[/bold #E8C4F0]\n",
        "ko": "\n[bold #E8C4F0]🚀 배치 처리를 시작합니다 (최대 동시 실행: {max_concurrent})[/bold #E8C4F0]\n"
    },
    "batch.processor.task_list_title": {
        "en": "Batch Task List (Total: {count})",
        "ja": "バッチタスクリスト（合計：{count} 個）",
        "ko": "배치 작업 목록（총 {count}개）"
    },
    "batch.processor.column.task_id": {
        "en": "Task ID",
        "ja": "タスク ID",
        "ko": "작업 ID"
    },
    "batch.processor.column.type": {
        "en": "Type",
        "ja": "タイプ",
        "ko": "유형"
    },
    "batch.processor.column.status": {
        "en": "Status",
        "ja": "状態",
        "ko": "상태"
    },
    "batch.processor.column.priority": {
        "en": "Priority",
        "ja": "優先度",
        "ko": "우선순위"
    },
    "batch.processor.column.created_at": {
        "en": "Created",
        "ja": "作成日時",
        "ko": "생성 시간"
    },
    "batch.processor.column.retry_count": {
        "en": "Retries",
        "ja": "再試行回数",
        "ko": "재시도 횟수"
    },

    # ==================== async_batch ====================
    "async_batch.async_mode.value": {
        "en": "[dim]Using async processing mode (asyncio)[/dim]\n",
        "ja": "[dim]非同期処理モードを使用しています（asyncio）[/dim]\n",
        "ko": "[dim]비동기 처리 모드 사용 중 (asyncio)[/dim]\n"
    },
    "async_batch.cleared.value": {
        "en": "[#B565D8]✓ Cleared {count} completed tasks[/#B565D8]",
        "ja": "[#B565D8]✓ {count} 個の完了したタスクをクリアしました[/#B565D8]",
        "ko": "[#B565D8]✓ {count}개의 완료된 작업을 정리했습니다[/#B565D8]"
    },
    "async_batch.completed.value": {
        "en": "\n[bold green]✅ Batch processing completed![/bold green]",
        "ja": "\n[bold green]✅ バッチ処理が完了しました！[/bold green]",
        "ko": "\n[bold green]✅ 배치 처리가 완료되었습니다![/bold green]"
    },
    "async_batch.example.completed": {
        "en": "Completed: {prompt}",
        "ja": "完了：{prompt}",
        "ko": "완료: {prompt}"
    },
    "async_batch.example.processing": {
        "en": "[dim]Processing: {prompt_short}...[/dim]",
        "ja": "[dim]処理中：{prompt_short}...[/dim]",
        "ko": "[dim]처리 중: {prompt_short}...[/dim]"
    },
    "async_batch.example.stats": {
        "en": "\nStats: {stats}",
        "ja": "\n統計：{stats}",
        "ko": "\n통계: {stats}"
    },
    "async_batch.example.task": {
        "en": "Task {number}",
        "ja": "タスク {number}",
        "ko": "작업 {number}"
    },
    "async_batch.example.test_start": {
        "en": "Starting async batch processing test",
        "ja": "非同期バッチ処理テストを開始します",
        "ko": "비동기 배치 처리 테스트 시작"
    },
    "async_batch.handler.async": {
        "en": "Async",
        "ja": "非同期",
        "ko": "비동기"
    },
    "async_batch.handler.not_found": {
        "en": "Task handler not found: {task_type}",
        "ja": "タスクハンドラーが見つかりません：{task_type}",
        "ko": "작업 핸들러를 찾을 수 없습니다: {task_type}"
    },
    "async_batch.handler.registered": {
        "en": "[#B565D8]✓ Registered task handler: {task_type} ({handler_type})[/#B565D8]",
        "ja": "[#B565D8]✓ タスクハンドラーを登録しました：{task_type}（{handler_type}）[/#B565D8]",
        "ko": "[#B565D8]✓ 작업 핸들러를 등록했습니다: {task_type} ({handler_type})[/#B565D8]"
    },
    "async_batch.handler.sync": {
        "en": "Sync",
        "ja": "同期",
        "ko": "동기"
    },
    "async_batch.load.failed": {
        "en": "[#E8C4F0]Failed to load tasks: {e}[/#E8C4F0]",
        "ja": "[#E8C4F0]タスクの読み込みに失敗しました：{e}[/#E8C4F0]",
        "ko": "[#E8C4F0]작업 로드 실패: {e}[/#E8C4F0]"
    },
    "async_batch.load.success": {
        "en": "[#E8C4F0]📂 Loaded {tasks_count} tasks[/#E8C4F0]",
        "ja": "[#E8C4F0]📂 {tasks_count} 個のタスクを読み込みました[/#E8C4F0]",
        "ko": "[#E8C4F0]📂 {tasks_count}개의 작업을 로드했습니다[/#E8C4F0]"
    },
    "async_batch.no_matching_tasks.value": {
        "en": "[#E8C4F0]No matching tasks[/#E8C4F0]",
        "ja": "[#E8C4F0]一致するタスクはありません[/#E8C4F0]",
        "ko": "[#E8C4F0]일치하는 작업이 없습니다[/#E8C4F0]"
    },
    "async_batch.no_tasks.value": {
        "en": "[#E8C4F0]No pending tasks[/#E8C4F0]",
        "ja": "[#E8C4F0]待機中のタスクはありません[/#E8C4F0]",
        "ko": "[#E8C4F0]대기 중인 작업이 없습니다[/#E8C4F0]"
    },
    "async_batch.processing.value": {
        "en": "Processing {total_tasks} tasks",
        "ja": "{total_tasks} 個のタスクを処理中",
        "ko": "{total_tasks}개의 작업 처리 중"
    },
    "async_batch.processor.initialized": {
        "en": "[dim]✓ Using async batch processor (optimized)[/dim]",
        "ja": "[dim]✓ 非同期バッチプロセッサーを使用しています（最適化版）[/dim]",
        "ko": "[dim]✓ 비동기 배치 프로세서 사용 중 (최적화)[/dim]"
    },
    "async_batch.save.failed": {
        "en": "[dim #E8C4F0]Failed to save tasks: {e}[/#E8C4F0]",
        "ja": "[dim #E8C4F0]タスクの保存に失敗しました：{e}[/#E8C4F0]",
        "ko": "[dim #E8C4F0]작업 저장 실패: {e}[/#E8C4F0]"
    },
    "async_batch.start.value": {
        "en": "\n[bold #E8C4F0]🚀 Starting batch processing (max concurrent: {max_concurrent})[/bold #E8C4F0]",
        "ja": "\n[bold #E8C4F0]🚀 バッチ処理を開始します（最大並行数：{max_concurrent}）[/bold #E8C4F0]",
        "ko": "\n[bold #E8C4F0]🚀 배치 처리를 시작합니다 (최대 동시 실행: {max_concurrent})[/bold #E8C4F0]"
    },
    "async_batch.stats_summary.value": {
        "en": "[dim]Total time: {overall_time:.2f}s | Average: {avg_task_time:.2f}s/task[/dim]",
        "ja": "[dim]合計時間：{overall_time:.2f}秒 | 平均：{avg_task_time:.2f}秒/タスク[/dim]",
        "ko": "[dim]총 소요 시간: {overall_time:.2f}초 | 평균: {avg_task_time:.2f}초/작업[/dim]"
    },
    "async_batch.table.created_at": {
        "en": "Created",
        "ja": "作成日時",
        "ko": "생성 시간"
    },
    "async_batch.table.priority": {
        "en": "Priority",
        "ja": "優先度",
        "ko": "우선순위"
    },
}


def update_locale_file(locale: str, locale_path: Path):
    """更新指定語言的 locale 檔案"""

    print(f"\n{'='*60}")
    print(f"更新 {locale.upper()} 翻譯檔案...")
    print(f"{'='*60}")

    # 讀取現有檔案
    with open(locale_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 載入 YAML
    data = yaml.safe_load(content)
    if data is None:
        data = {}

    added_count = 0
    updated_count = 0

    # 處理每個翻譯鍵
    for key, translations in TRANSLATIONS.items():
        if locale not in translations:
            continue

        # 分解鍵路徑
        parts = key.split('.')
        current = data

        # 導航到目標位置
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # 設置值
        final_key = parts[-1]
        if final_key in current:
            if current[final_key] != translations[locale]:
                current[final_key] = translations[locale]
                updated_count += 1
        else:
            current[final_key] = translations[locale]
            added_count += 1

    # 寫回檔案（保留原有格式和註解）
    with open(locale_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False,
                  default_flow_style=False, width=float("inf"))

    print(f"✓ 新增: {added_count} 個翻譯鍵")
    print(f"✓ 更新: {updated_count} 個翻譯鍵")

    return added_count, updated_count


def main():
    """主程式"""
    base_dir = Path("/Users/hc1034/Saki_Studio/Claude/ChatGemini_SakiTool/locales")

    # 語言檔案映射
    locales = {
        "en": base_dir / "en.yaml",
        "ja": base_dir / "ja.yaml",
        "ko": base_dir / "ko.yaml"
    }

    print("\n" + "="*60)
    print("自動翻譯生成器")
    print("="*60)
    print(f"總翻譯鍵數: {len(TRANSLATIONS)}")
    print(f"目標語言: 英文、日文、韓文")
    print("="*60)

    total_stats = {
        "en": {"added": 0, "updated": 0},
        "ja": {"added": 0, "updated": 0},
        "ko": {"added": 0, "updated": 0}
    }

    # 更新每個語言檔案
    for locale, path in locales.items():
        added, updated = update_locale_file(locale, path)
        total_stats[locale]["added"] = added
        total_stats[locale]["updated"] = updated

    # 最終統計
    print("\n" + "="*60)
    print("最終統計報告")
    print("="*60)
    print(f"英文 (en.yaml):")
    print(f"  - 新增: {total_stats['en']['added']} 個")
    print(f"  - 更新: {total_stats['en']['updated']} 個")
    print(f"日文 (ja.yaml):")
    print(f"  - 新增: {total_stats['ja']['added']} 個")
    print(f"  - 更新: {total_stats['ja']['updated']} 個")
    print(f"韓文 (ko.yaml):")
    print(f"  - 新增: {total_stats['ko']['added']} 個")
    print(f"  - 更新: {total_stats['ko']['updated']} 個")
    print("="*60)
    print("✅ 所有翻譯檔案已更新完成！")
    print("="*60)


if __name__ == "__main__":
    main()
