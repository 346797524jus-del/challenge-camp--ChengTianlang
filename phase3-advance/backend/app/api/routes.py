"""Xiaoshitou Agent - Main API Routes with File Management, RAG, MCP."""
import json, os, uuid, shutil
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from loguru import logger
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.config import get_settings, UPLOAD_DIR, GENERATED_DIR, BACKUP_DIR
from app.models import Session, Message, Preference, FileRecord, KnowledgeItem
from app.pipeline.pipeline import AgentPipeline
from app.file_processor import FileProcessor

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Request/Response Models
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ChatRequest(BaseModel):
    session_id: str = ""
    message: str
    deep_thinking: bool = False
    guide_mode: bool = False
    user_id: str = "default_user"

class SessionCreate(BaseModel):
    user_id: str = "default_user"

class SessionRename(BaseModel):
    title: str

class SessionStyle(BaseModel):
    assistant_avatar: str = ""
    assistant_nickname: str = "小石头"
    user_avatar: str = ""
    user_nickname: str = "用户"
    is_global: bool = False

class FeedbackRequest(BaseModel):
    message_id: str
    feedback_type: str  # "like" or "dislike"

class PreferenceUpdate(BaseModel):
    tone_style: Optional[str] = None
    response_length: Optional[str] = None
    language_preference: Optional[str] = None
    theme: Optional[str] = None

class KnowledgeUpload(BaseModel):
    title: str
    content: str
    source_url: str = ""
    category: str = "general"
    tags: str = ""

class FileCleanRequest(BaseModel):
    file_id: str
    operations: List[str] = ["deduplicate", "remove_nulls"]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Router Setup
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

router = APIRouter(prefix="/api")
pipeline = AgentPipeline()
file_processor = FileProcessor()


# ══════════ SESSIONS ══════════

@router.get("/sessions")
def list_sessions(user_id: str = "default_user", db: DBSession = Depends(get_db)):
    sessions = (
        db.query(Session)
        .filter(Session.user_id == user_id, Session.is_active == True)
        .order_by(Session.updated_at.desc())
        .all()
    )
    return {"sessions": [s.to_dict() for s in sessions], "total": len(sessions)}


@router.post("/sessions")
def create_session(req: SessionCreate, db: DBSession = Depends(get_db)):
    session = Session(
        user_id=req.user_id, title="新对话",
        assistant_nickname="小石头", user_nickname="用户",
    )
    db.add(session); db.commit(); db.refresh(session)
    return session.to_dict()


@router.get("/sessions/{session_id}")
def get_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session.to_dict()


@router.put("/sessions/{session_id}/rename")
def rename_session(session_id: str, req: SessionRename, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    session.title = req.title
    session.updated_at = datetime.now()
    db.commit()
    return {"status": "ok", "title": req.title}


@router.put("/sessions/{session_id}/style")
def update_session_style(session_id: str, req: SessionStyle, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    if req.assistant_avatar:
        session.assistant_avatar = req.assistant_avatar
    if req.assistant_nickname:
        session.assistant_nickname = req.assistant_nickname
    if req.user_avatar:
        session.user_avatar = req.user_avatar
    if req.user_nickname:
        session.user_nickname = req.user_nickname
    session.is_global_style = req.is_global
    session.updated_at = datetime.now()
    db.commit()
    return {"status": "ok", "session": session.to_dict()}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    session.is_active = False
    session.updated_at = datetime.now()
    db.commit()
    return {"status": "ok"}


# ══════════ MESSAGES ══════════

@router.get("/sessions/{session_id}/messages")
def get_messages(session_id: str, db: DBSession = Depends(get_db)):
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.sequence.asc())
        .all()
    )
    return {"messages": [m.to_dict() for m in messages]}


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, db: DBSession = Depends(get_db)):
    if not req.session_id:
        session = Session(
            user_id=req.user_id, title="新对话", assistant_nickname="小石头",
        )
        db.add(session); db.commit(); db.refresh(session)
        req.session_id = session.id

    session_id = req.session_id
    msg_count = db.query(Message).filter(Message.session_id == session_id).count()
    user_msg = Message(
        session_id=session_id, role="user", content=req.message,
        content_type="text", sequence=msg_count + 1,
    )
    db.add(user_msg); db.commit()

    async def event_generator():
        try:
            async for event in pipeline.run_stream(
                db, req.message, req.user_id, session_id,
                deep_thinking=req.deep_thinking, guide_mode=req.guide_mode
            ):
                evt_type = event.get("event", "message")
                evt_data = event.get("data", "{}")
                yield {
                    "event": evt_type,
                    "data": str(evt_data),
                }
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)[:200]}, ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())


@router.post("/chat")
def chat_sync(req: ChatRequest, db: DBSession = Depends(get_db)):
    if not req.session_id:
        session = Session(
            user_id=req.user_id, title="新对话", assistant_nickname="小石头",
        )
        db.add(session); db.commit(); db.refresh(session)
        req.session_id = session.id

    msg_count = db.query(Message).filter(Message.session_id == req.session_id).count()
    user_msg = Message(
        session_id=req.session_id, role="user", content=req.message,
        content_type="text", sequence=msg_count + 1,
    )
    db.add(user_msg)

    ctx = pipeline.run(db, req.message, req.user_id, req.session_id, req.deep_thinking)
    if ctx.output:
        assistant_msg = Message(
            session_id=req.session_id, role="assistant",
            content=ctx.output.content, content_type=ctx.output.content_type,
            sequence=msg_count + 2,
        )
        db.add(assistant_msg); db.commit()

    return {
        "message": ctx.output.content if ctx.output else "",
        "content_type": ctx.output.content_type if ctx.output else "text",
        "thinking_steps": ctx.thinking_steps,
        "sources": ctx.output.sources if ctx.output else [],
        "error": ctx.error,
    }


# ══════════ FILE MANAGEMENT CENTER ══════════

@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = "",
    db: DBSession = Depends(get_db),
):
    contents = await file.read()
    is_valid, error_msg = file_processor.validate_file(file.filename, len(contents))
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    file_path = file_processor.save_upload(contents, file.filename)
    parsed = file_processor.parse(file_path)

    if not session_id:
        session_id = "global"

    record = FileRecord(
        session_id=session_id,
        filename=Path(file_path).name,
        original_filename=file.filename,
        file_path=file_path,
        file_type=parsed.get("file_type", ""),
        file_size=len(contents),
        purpose="upload",
        content_preview=parsed.get("preview", "")[:5000],
        row_count=parsed.get("rows", 0),
        status="parsed",
    )
    db.add(record); db.commit(); db.refresh(record)

    return {
        "file_id": record.id,
        "filename": file.filename,
        "file_type": parsed.get("file_type", ""),
        "parse_preview": parsed.get("preview", ""),
        "content": parsed.get("content", ""),
        "rows": parsed.get("rows", 0),
        "columns": parsed.get("columns", []),
        "record": record.to_dict(),
    }


@router.get("/files")
def list_all_files(
    sort_by: str = "created_at",
    order: str = "desc",
    file_type: str = "",
    db: DBSession = Depends(get_db),
):
    query = db.query(FileRecord)
    if file_type:
        query = query.filter(FileRecord.file_type == file_type)

    sort_column = getattr(FileRecord, sort_by, FileRecord.created_at)
    if order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    files = query.limit(100).all()
    return {"files": [f.to_dict() for f in files], "total": len(files)}


@router.get("/files/session/{session_id}")
def list_session_files(
    session_id: str,
    sort_by: str = "created_at",
    order: str = "desc",
    file_type: str = "",
    db: DBSession = Depends(get_db),
):
    query = db.query(FileRecord).filter(FileRecord.session_id == session_id)
    if file_type:
        query = query.filter(FileRecord.file_type == file_type)
    sort_column = getattr(FileRecord, sort_by, FileRecord.created_at)
    if order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    files = query.limit(100).all()
    return {"files": [f.to_dict() for f in files], "total": len(files)}


@router.get("/files/download/{file_id}")
def download_file(file_id: str, db: DBSession = Depends(get_db)):
    record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    file_path = Path(record.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件已丢失")
    return FileResponse(
        path=str(file_path),
        filename=record.original_filename,
        media_type="application/octet-stream",
    )


@router.get("/files/download/path")
def download_file_by_path(file: str = ""):
    # Handle unicode and backslash paths from frontend
    import urllib.parse
    decoded = urllib.parse.unquote(file)
    file_path = Path(decoded)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"文件不存在: {file_path.name}")
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@router.get("/files/preview/{file_id}")
def preview_file(file_id: str, db: DBSession = Depends(get_db)):
    record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    file_path = Path(record.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件已丢失")
    if record.file_type in ("png", "jpg", "jpeg", "gif", "bmp"):
        return FileResponse(
            path=str(file_path),
            media_type=f"image/{record.file_type}",
        )
    parsed = file_processor.parse(str(file_path))
    return {
        "filename": record.original_filename,
        "file_type": record.file_type,
        "preview": parsed.get("preview", ""),
        "content": parsed.get("content", ""),
    }


@router.get("/files/preview/path")
def preview_file_by_path(file: str = ""):
    # Handle unicode and backslash paths from frontend
    import urllib.parse
    decoded = urllib.parse.unquote(file)
    file_path = Path(decoded)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"文件不存在: {file_path.name}")
    ext = file_path.suffix.lower().lstrip(".")
    if ext in ("png", "jpg", "jpeg", "gif", "bmp"):
        return FileResponse(path=str(file_path), media_type=f"image/{ext}")
    parsed = file_processor.parse(str(file_path))
    return {
        "filename": file_path.name,
        "file_type": ext,
        "preview": parsed.get("preview", ""),
        "content": parsed.get("content", ""),
    }


@router.delete("/files/{file_id}")
def delete_file(file_id: str, db: DBSession = Depends(get_db)):
    record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    try:
        Path(record.file_path).unlink(missing_ok=True)
    except: pass
    db.delete(record); db.commit()
    return {"status": "ok"}


@router.get("/files/versions/{file_id}")
def get_file_versions(file_id: str, db: DBSession = Depends(get_db)):
    record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    base_name = Path(record.original_filename).stem
    ext = Path(record.original_filename).suffix
    backups = []
    if BACKUP_DIR.exists():
        for f in sorted(
            BACKUP_DIR.glob(f"{base_name}_backup_*{ext}"), reverse=True
        ):
            backups.append({
                "filename": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return {
        "file_id": file_id,
        "current": record.to_dict(),
        "versions": backups,
    }


@router.post("/files/restore/{file_id}")
def restore_file_version(file_id: str, data: dict, db: DBSession = Depends(get_db)):
    backup_path = data.get("backup_path", "")
    if not backup_path or not Path(backup_path).exists():
        raise HTTPException(status_code=404, detail="备份文件不存在")
    record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    file_processor.backup_file(record.file_path)
    shutil.copy2(backup_path, record.file_path)
    record.file_size = Path(record.file_path).stat().st_size
    record.updated_at = datetime.now()
    db.commit()
    return {"status": "ok", "file": record.to_dict()}


@router.post("/files/generated/save")
def save_generated_file(data: dict, db: DBSession = Depends(get_db)):
    file_path = data.get("file_path", "")
    session_id = data.get("session_id", "global")
    purpose = data.get("purpose", "generated")
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    path = Path(file_path)
    record = FileRecord(
        session_id=session_id,
        filename=path.name,
        original_filename=path.name,
        file_path=file_path,
        file_type=path.suffix.lstrip(".").lower(),
        file_size=path.stat().st_size,
        purpose=purpose,
        status="done",
    )
    db.add(record); db.commit(); db.refresh(record)
    return record.to_dict()


# ══════════ FILE CLEANING ══════════

@router.post("/files/clean")
def clean_file(req: FileCleanRequest, db: DBSession = Depends(get_db)):
    record = db.query(FileRecord).filter(FileRecord.id == req.file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    # Backup before cleaning
    file_processor.backup_file(record.file_path)
    result = file_processor.clean_data(record.file_path, req.operations)
    if result.get("cleaned_file"):
        # Create new record for cleaned file
        cleaned_path = Path(result["cleaned_file"])
        new_record = FileRecord(
            session_id=record.session_id,
            filename=cleaned_path.name,
            original_filename=f"cleaned_{record.original_filename}",
            file_path=str(cleaned_path),
            file_type=record.file_type,
            file_size=cleaned_path.stat().st_size,
            purpose="processed",
            status="done",
            row_count=result.get("rows_after", 0),
        )
        db.add(new_record); db.commit(); db.refresh(new_record)
        return {
            "status": "ok",
            "cleaned_file": new_record.to_dict(),
            "operations_performed": result.get("operations_performed", []),
            "rows_before": result.get("rows_before", 0),
            "rows_after": result.get("rows_after", 0),
        }
    return {
        "status": "error",
        "operations_performed": result.get("operations_performed", []),
    }


# ══════════ FILE-BASED CONVERSATION ══════════

@router.post("/files/conversation/start")
def start_file_conversation(data: dict, db: DBSession = Depends(get_db)):
    file_id = data.get("file_id", "")
    user_id = data.get("user_id", "default_user")
    if not file_id:
        raise HTTPException(status_code=400, detail="缺少 file_id")

    record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")

    content_result = file_processor.parse(record.file_path)
    file_content = content_result.get("content", "")[:5000]

    session = Session(
        user_id=user_id,
        title=f"关于{record.original_filename}的对话",
        assistant_nickname="小石头",
    )
    db.add(session); db.commit(); db.refresh(session)

    sys_msg = Message(
        session_id=session.id, role="system",
        content=(
            f"用户上传了文件「{record.original_filename}」({record.file_type})，"
            f"以下是文件内容：\n\n{file_content}\n\n"
            f"请基于此文件内容回答用户的问题。"
        ),
        content_type="text", sequence=1,
    )
    db.add(sys_msg)

    welcome_msg = Message(
        session_id=session.id, role="assistant",
        content=(
            f"已加载文件「{record.original_filename}」"
            f"（{record.file_type}，{record.file_size/1024:.1f}KB）。"
            f"您可以对该文件提问、要求总结或修改。"
        ),
        content_type="text", sequence=2,
    )
    db.add(welcome_msg)
    db.commit()

    return {
        "session": session.to_dict(),
        "file_info": record.to_dict(),
        "content_preview": file_content[:300],
    }


# ══════════ DOCUMENT GENERATION ══════════

@router.post("/documents/generate/word")
def generate_word_document(data: dict, db: DBSession = Depends(get_db)):
    file_path = file_processor.generate_word(
        title=data.get("title", "未命名文档"),
        content=data.get("content", ""),
        author=data.get("author", "小石头"),
    )
    path = Path(file_path)
    record = FileRecord(
        session_id=data.get("session_id", "global"),
        filename=path.name, original_filename=path.name,
        file_path=file_path, file_type="docx",
        file_size=path.stat().st_size,
        purpose="generated", status="done",
    )
    db.add(record); db.commit()
    return {"file_path": file_path, "filename": path.name, "file_id": record.id}


@router.post("/documents/generate/excel")
def generate_excel_document(data: dict, db: DBSession = Depends(get_db)):
    file_path = file_processor.generate_excel(
        sheet_name=data.get("sheet_name", "Sheet1"),
        headers=data.get("headers", []),
        rows=data.get("rows", []),
        title=data.get("title", ""),
        chart_type=data.get("chart_type", ""),
    )
    path = Path(file_path)
    record = FileRecord(
        session_id=data.get("session_id", "global"),
        filename=path.name, original_filename=path.name,
        file_path=file_path, file_type="xlsx",
        file_size=path.stat().st_size,
        purpose="generated", status="done",
    )
    db.add(record); db.commit()
    return {"file_path": file_path, "filename": path.name, "file_id": record.id}


@router.post("/documents/generate/ppt")
def generate_ppt_document(data: dict, db: DBSession = Depends(get_db)):
    file_path = file_processor.generate_ppt(
        title=data.get("title", "未命名"),
        slides_data=data.get("slides", []),
    )
    path = Path(file_path)
    record = FileRecord(
        session_id=data.get("session_id", "global"),
        filename=path.name, original_filename=path.name,
        file_path=file_path, file_type="pptx",
        file_size=path.stat().st_size,
        purpose="generated", status="done",
    )
    db.add(record); db.commit()
    return {"file_path": file_path, "filename": path.name, "file_id": record.id}


# ══════════ SEARCH / FEEDBACK / PREFERENCES / KNOWLEDGE ══════════

@router.post("/search")
def search(data: dict, db: DBSession = Depends(get_db)):
    query = data.get("query", "")
    session_id = data.get("session_id", "")
    user_id = data.get("user_id", "default_user")
    from app.pipeline.input_layer import UserIntent
    intent = UserIntent(
        primary_intent="web_search", requires_search=True, raw_message=query,
    )
    sources = pipeline.data_layer.acquire(db, intent, user_id, session_id)
    processed = pipeline.process_layer.process(intent, sources)
    return {
        "answer": processed.cleaned_content,
        "key_points": processed.key_points,
        "sources": processed.sources,
        "metadata": sources.search_metadata,
    }


@router.post("/feedback")
def send_feedback(req: FeedbackRequest, db: DBSession = Depends(get_db)):
    message = db.query(Message).filter(Message.id == req.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    message.feedback = req.feedback_type

    pref = db.query(Preference).filter(
        Preference.user_id == "default_user"
    ).first()
    if not pref:
        pref = Preference(user_id="default_user")
        db.add(pref)

    if req.feedback_type == "like":
        pref.like_count += 1
    elif req.feedback_type == "dislike":
        pref.dislike_count += 1
    db.commit()
    return {"status": "ok"}


@router.get("/preferences")
def get_preferences(user_id: str = "default_user", db: DBSession = Depends(get_db)):
    pref = db.query(Preference).filter(Preference.user_id == user_id).first()
    if not pref:
        pref = Preference(user_id=user_id)
        db.add(pref); db.commit(); db.refresh(pref)
    return pref.to_dict()


@router.put("/preferences")
def update_preferences(
    req: PreferenceUpdate,
    user_id: str = "default_user",
    db: DBSession = Depends(get_db),
):
    pref = db.query(Preference).filter(Preference.user_id == user_id).first()
    if not pref:
        pref = Preference(user_id=user_id)
        db.add(pref)
    if req.tone_style:
        pref.tone_style = req.tone_style
    if req.response_length:
        pref.response_length = req.response_length
    if req.language_preference:
        pref.language_preference = req.language_preference
    if req.theme:
        pref.theme = req.theme
    pref.updated_at = datetime.now()
    db.commit(); db.refresh(pref)
    return pref.to_dict()


@router.get("/knowledge")
def list_knowledge(category: str = "", db: DBSession = Depends(get_db)):
    query = db.query(KnowledgeItem).filter(KnowledgeItem.is_active == True)
    if category:
        query = query.filter(KnowledgeItem.category == category)
    return {"items": [i.to_dict() for i in query.limit(50).all()], "total": query.count()}


@router.post("/knowledge")
def add_knowledge(req: KnowledgeUpload, db: DBSession = Depends(get_db)):
    item = KnowledgeItem(
        title=req.title, content=req.content,
        source_url=req.source_url, source_type="manual",
        category=req.category, tags=req.tags,
    )
    db.add(item); db.commit(); db.refresh(item)
    return item.to_dict()


@router.delete("/knowledge/{item_id}")
def delete_knowledge(item_id: str, db: DBSession = Depends(get_db)):
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    item.is_active = False
    db.commit()
    return {"status": "ok"}


@router.post("/sessions/{session_id}/branch")
def create_branch(session_id: str, data: dict, db: DBSession = Depends(get_db)):
    parent_message_id = data.get("message_id", "")
    message = db.query(Message).filter(Message.id == parent_message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")

    new_session = Session(
        user_id=message.session.user_id,
        title=f"分支 - {message.session.title}",
        assistant_nickname=message.session.assistant_nickname,
        assistant_avatar=message.session.assistant_avatar,
    )
    db.add(new_session)

    earlier = (
        db.query(Message)
        .filter(
            Message.session_id == session_id,
            Message.sequence <= message.sequence,
        )
        .order_by(Message.sequence.asc())
        .all()
    )
    for m in earlier:
        db.add(Message(
            session_id=new_session.id, role=m.role, content=m.content,
            content_type=m.content_type, parent_message_id=m.parent_message_id,
            sequence=m.sequence,
        ))

    message.branch_session_id = new_session.id
    db.commit(); db.refresh(new_session)
    return {"branch_session_id": new_session.id, "session": new_session.to_dict()}


# ══════════ RAG (Milvus + DashScope) ══════════

from app.rag import VectorDBManager, VectorRetriever

_vector_db = None
_vector_retriever = None


def get_rag():
    global _vector_db, _vector_retriever
    if _vector_db is None:
        _vector_db = VectorDBManager(
            host=os.getenv("MILVUS_HOST", "localhost"),
            port=int(os.getenv("MILVUS_PORT", "19530")),
            collection_name=os.getenv("COLLECTION_NAME", "agent_rag"),
        )
        _vector_retriever = VectorRetriever(
            vector_db=_vector_db, similarity_threshold=0.5,
        )
    return _vector_db, _vector_retriever


@router.post("/vector/upload_document")
async def upload_document_to_rag(file: UploadFile = File(...)):
    contents = await file.read()
    temp_path = UPLOAD_DIR / f"rag_{uuid.uuid4().hex}_{file.filename}"
    temp_path.write_bytes(contents)
    try:
        _, retriever = get_rag()
        result = retriever.upload_document(str(temp_path))
        return {
            "success": result["success"],
            "filename": result["filename"],
            "chunks_inserted": result["chunks_inserted"],
            "error": result.get("error", ""),
        }
    finally:
        try: temp_path.unlink(missing_ok=True)
        except: pass


@router.post("/vector/query")
def query_rag(data: dict):
    question = data.get("question", data.get("query", ""))
    top_k = data.get("top_k", 5)
    threshold = data.get("threshold", 0.5)
    if not question:
        raise HTTPException(status_code=400, detail="Missing question")
    _, retriever = get_rag()
    retriever.threshold = threshold
    result = retriever.query(question, top_k=top_k)
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "chunks_used": result["chunks_used"],
        "from_knowledge_base": result["from_kb"],
    }


@router.get("/vector/stats")
def vector_stats():
    return get_rag()[0].get_stats()


@router.delete("/vector/clear")
def clear_vector_db(source: str = ""):
    if source:
        return {"deleted": get_rag()[0].delete_by_source(source), "source": source}
    return {"error": "Specify ?source="}


# ══════════ MCP STATUS ══════════

@router.get("/mcp/status")
def mcp_status():
    try:
        from app.mcp import get_mcp_manager
        mcp = get_mcp_manager()
        tools = mcp.get_tools()
        return {
            "status": "connected",
            "tools_count": len(tools),
            "tools": [t.to_dict() for t in tools],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/mcp/tools")
def mcp_tools():
    try:
        from app.mcp import get_mcp_manager
        mcp = get_mcp_manager()
        tools = mcp.get_tools()
        return {"tools": [t.to_dict() for t in tools]}
    except Exception as e:
        return {"tools": [], "error": str(e)}


# ══════════ HEALTH ══════════

@router.get("/health")
def health_check():
    rag_stats = {}
    try:
        rag_stats = get_rag()[0].get_stats()
    except Exception:
        pass
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "4.0.0",
        "name": "小石头智能助手",
        "rag": rag_stats,
    }