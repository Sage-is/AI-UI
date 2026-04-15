import logging
import shutil
import sqlite3
import zipfile
import markdown

from pathlib import Path
from uuid import uuid4

from sage_is_ai.models.chats import ChatTitleMessagesForm
from sage_is_ai.config import DATA_DIR, ENABLE_ADMIN_EXPORT
from sage_is_ai.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, status
from pydantic import BaseModel
from starlette.responses import FileResponse


from sage_is_ai.utils.misc import get_gravatar_url
from sage_is_ai.utils.pdf_generator import PDFGenerator
from sage_is_ai.utils.auth import get_admin_user, get_verified_user
from sage_is_ai.utils.code_interpreter import execute_code_jupyter
from sage_is_ai.env import SRC_LOG_LEVELS, BACKUP_RESTORE_MAX_SIZE_MB


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


@router.get("/gravatar")
async def get_gravatar(email: str, user=Depends(get_verified_user)):
    return get_gravatar_url(email)


class CodeForm(BaseModel):
    code: str


@router.post("/code/format")
async def format_code(form_data: CodeForm, user=Depends(get_admin_user)):
    try:
        import black

        formatted_code = black.format_str(form_data.code, mode=black.Mode())
        return {"code": formatted_code}
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="black is not installed. Run: pip install black",
        )
    except Exception as e:
        if "NothingChanged" in type(e).__name__:
            return {"code": form_data.code}
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/code/execute")
async def execute_code(
    request: Request, form_data: CodeForm, user=Depends(get_verified_user)
):
    if request.app.state.config.CODE_EXECUTION_ENGINE == "jupyter":
        output = await execute_code_jupyter(
            request.app.state.config.CODE_EXECUTION_JUPYTER_URL,
            form_data.code,
            (
                request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN
                if request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH == "token"
                else None
            ),
            (
                request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD
                if request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH == "password"
                else None
            ),
            request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT,
        )

        return output
    else:
        raise HTTPException(
            status_code=400,
            detail="Code execution engine not supported",
        )


class MarkdownForm(BaseModel):
    md: str


@router.post("/markdown")
async def get_html_from_markdown(
    form_data: MarkdownForm, user=Depends(get_verified_user)
):
    return {"html": markdown.markdown(form_data.md)}


class ChatForm(BaseModel):
    title: str
    messages: list[dict]


@router.post("/pdf")
async def download_chat_as_pdf(
    form_data: ChatTitleMessagesForm, user=Depends(get_verified_user)
):
    try:
        pdf_bytes = PDFGenerator(form_data).generate_chat_pdf()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment;filename=chat.pdf"},
        )
    except Exception as e:
        log.exception(f"Error generating PDF: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/db/download")
async def download_db(user=Depends(get_admin_user)):
    if not ENABLE_ADMIN_EXPORT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    from sage_is_ai.internal.db import engine

    if engine.name != "sqlite":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DB_NOT_SQLITE,
        )
    return FileResponse(
        engine.url.database,
        media_type="application/octet-stream",
        filename="webui.db",
    )


def _validate_sqlite(db_path: Path) -> bool:
    """Validate that a file is a real SQLite DB with at least one user row."""
    try:
        conn = sqlite3.connect(str(db_path))
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if result[0] != "ok":
            return False
        count = conn.execute("SELECT count(*) FROM user").fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def _zip_entry_is_safe(name: str) -> bool:
    """Reject path traversal and absolute paths in ZIP entries."""
    if name.startswith("/") or ".." in name.split("/"):
        return False
    return True


def _allowed_zip_entry(name: str) -> bool:
    """Only allow webui.db and files under uploads/."""
    if name == "webui.db":
        return True
    if name.startswith("uploads/"):
        return True
    return False


@router.post("/db/restore")
async def restore_db(file: UploadFile = File(...)):
    """
    Restore the database (and optionally uploads) from a backup file.
    Only available during onboarding when no users exist.
    Accepts a raw .db file or a .zip containing webui.db + uploads/.
    """
    from sage_is_ai.models.users import Users
    from sage_is_ai.internal.db import engine, handle_peewee_migration
    from sage_is_ai.config import run_migrations
    from sage_is_ai.env import DATABASE_URL

    if Users.get_num_users() != 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.DB_RESTORE_NOT_ALLOWED,
        )

    if engine.name != "sqlite":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DB_NOT_SQLITE,
        )

    # Read header to detect format
    header = await file.read(16)
    if len(header) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DB_RESTORE_INVALID_FILE,
        )

    is_sqlite = header.startswith(b"SQLite format 3\x00")
    is_zip = header[:4] == b"PK\x03\x04"

    if not is_sqlite and not is_zip:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DB_RESTORE_INVALID_FILE,
        )

    # Save uploaded file to a temp path
    tmp_path = DATA_DIR / f"_restore_tmp_{uuid4().hex}"
    backup_path = DATA_DIR / "webui_pre_restore.db"
    db_path = Path(engine.url.database)

    try:
        with open(tmp_path, "wb") as f:
            f.write(header)
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                f.write(chunk)

        # Enforce size limit
        file_size = tmp_path.stat().st_size
        max_bytes = BACKUP_RESTORE_MAX_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=ERROR_MESSAGES.DB_RESTORE_FILE_TOO_LARGE,
            )

        if is_sqlite:
            # Validate the uploaded DB directly
            if not _validate_sqlite(tmp_path):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DB_RESTORE_NO_USERS,
                )

            # Replace the database
            engine.dispose()
            if db_path.exists():
                shutil.copy2(db_path, backup_path)
            shutil.move(str(tmp_path), str(db_path))

        elif is_zip:
            # Validate ZIP contents
            try:
                zf = zipfile.ZipFile(str(tmp_path), "r")
            except zipfile.BadZipFile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DB_RESTORE_INVALID_FILE,
                )

            names = zf.namelist()

            # Security: check for path traversal
            for name in names:
                if not _zip_entry_is_safe(name):
                    zf.close()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=ERROR_MESSAGES.DB_RESTORE_PATH_TRAVERSAL,
                    )

            if "webui.db" not in names:
                zf.close()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DB_RESTORE_INVALID_FILE,
                )

            # Extract webui.db to temp location and validate
            extracted_db = DATA_DIR / f"_restore_db_{uuid4().hex}.db"
            try:
                with zf.open("webui.db") as src, open(extracted_db, "wb") as dst:
                    shutil.copyfileobj(src, dst)

                if not _validate_sqlite(extracted_db):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=ERROR_MESSAGES.DB_RESTORE_NO_USERS,
                    )

                # Replace database
                engine.dispose()
                if db_path.exists():
                    shutil.copy2(db_path, backup_path)
                shutil.move(str(extracted_db), str(db_path))

                # Extract allowed upload files
                for name in names:
                    if name == "webui.db":
                        continue
                    if _allowed_zip_entry(name) and _zip_entry_is_safe(name):
                        target = DATA_DIR / name
                        if name.endswith("/"):
                            target.mkdir(parents=True, exist_ok=True)
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            with zf.open(name) as src, open(target, "wb") as dst:
                                shutil.copyfileobj(src, dst)
            finally:
                zf.close()
                if extracted_db.exists():
                    extracted_db.unlink()

        # Run migrations on the restored database
        try:
            handle_peewee_migration(DATABASE_URL)
            run_migrations()
        except Exception as e:
            log.warning(f"Post-restore migration warning: {e}")

        log.info("Database restored successfully from backup")
        return {"status": True}

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Restore failed: {e}")
        # Attempt rollback
        if backup_path.exists() and not db_path.exists():
            shutil.move(str(backup_path), str(db_path))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restore failed: {str(e)}",
        )
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


