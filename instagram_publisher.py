#!/usr/bin/env python3
"""Fila auditável e publicador idempotente de imagens no Instagram.

O modo padrão é dry-run. Publicação real exige aprovação de Arthur, a trava de
ambiente e a opção explícita ``run --execute``.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping

EXPECTED_USERNAME = "quero.turismo"
REQUIRED_APPROVER = "Arthur"
DEFAULT_DB = Path(".instagram/queue.sqlite3")
GRAPH_BASE_URL = "https://graph.instagram.com"
BAHIA_TIMEZONE = timezone(timedelta(hours=-3))
CONTENT_POLICIES = {
    "ship_sold_by_quero_abada": ("queroabada", "queronavio"),
    "carnival_lodging": ("queroabada",),
    "ship_not_sold_by_quero_abada": ("queronavio",),
    "other": (),
}
SAFE_FAILURE_CODES = {
    "validation_failed", "container_failed", "publishing_ambiguous",
    "publishing_failed", "operator_cancelled", "test_failure",
}


class PublisherError(Exception):
    """Erro esperado, seguro para exibição ao operador."""


class ItemNotFound(PublisherError):
    pass


class NotApproved(PublisherError):
    pass


class PublishingDisabled(PublisherError):
    pass


class ConcurrentPublishing(PublisherError):
    pass


class ValidationError(PublisherError):
    pass


class InstagramAPIError(PublisherError):
    """Erro sanitizado: nunca inclui cabeçalhos, URL com token ou corpo bruto."""

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        self.http_status = http_status


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def bahia_now() -> str:
    return datetime.now(BAHIA_TIMEZONE).isoformat(timespec="seconds")


def parse_aware_datetime(value: str) -> datetime:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError("horário deve estar no formato ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError("horário deve incluir fuso (por exemplo, -03:00 ou Z)")
    return parsed


@dataclass(frozen=True)
class QueueItem:
    piece_id: str
    media: str
    caption: str
    scheduled_at: str
    content_policy: str
    collaborators: tuple[str, ...]
    status: str
    approved_by: str | None
    approved_at: str | None
    created_at: str
    updated_at: str
    published_at: str | None = None
    failure_reason: str | None = None
    remote_container_id: str | None = None
    remote_media_id: str | None = None
    permalink: str | None = None
    publish_started_at: str | None = None
    publish_lock_owner: str | None = None
    publish_lock_at: str | None = None


@dataclass(frozen=True)
class Credentials:
    user_id: str
    access_token: str

    def __repr__(self) -> str:
        return "Credentials(user_id=<redacted>, access_token=<redacted>)"

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> "Credentials":
        user_id = environment.get("INSTAGRAM_USER_ID", "").strip()
        access_token = environment.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
        missing = [name for name, value in (
            ("INSTAGRAM_USER_ID", user_id),
            ("INSTAGRAM_ACCESS_TOKEN", access_token),
        ) if not value]
        if missing:
            raise ValidationError("credenciais ausentes: " + ", ".join(missing))
        return cls(user_id=user_id, access_token=access_token)


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, url):
        return None


class Queue:
    def __init__(self, database: str | Path = DEFAULT_DB) -> None:
        self.database = str(database)
        if self.database != ":memory:":
            Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database)
        self.connection.row_factory = sqlite3.Row
        self._initialize()

    def close(self) -> None:
        self.connection.close()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS queue_items (
                piece_id TEXT PRIMARY KEY,
                media TEXT NOT NULL,
                caption TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                content_policy TEXT NOT NULL DEFAULT 'other',
                collaborators_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL CHECK(status IN ('draft','approved','published','failed')),
                approved_by TEXT,
                approved_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT,
                failure_reason TEXT,
                remote_container_id TEXT,
                remote_media_id TEXT,
                permalink TEXT,
                publish_started_at TEXT,
                publish_lock_owner TEXT,
                publish_lock_at TEXT,
                CHECK(status NOT IN ('approved','published') OR
                      (approved_by IS NOT NULL AND approved_at IS NOT NULL))
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                occurred_at TEXT NOT NULL,
                piece_id TEXT NOT NULL,
                event TEXT NOT NULL,
                actor TEXT,
                details_json TEXT NOT NULL
            );
            """
        )
        existing = {row["name"] for row in self.connection.execute(
            "PRAGMA table_info(queue_items)"
        ).fetchall()}
        migrations = {
            "content_policy": "TEXT NOT NULL DEFAULT 'other'",
            "collaborators_json": "TEXT NOT NULL DEFAULT '[]'",
            "remote_container_id": "TEXT", "remote_media_id": "TEXT",
            "permalink": "TEXT", "publish_started_at": "TEXT",
            "publish_lock_owner": "TEXT", "publish_lock_at": "TEXT",
        }
        for column, declaration in migrations.items():
            if column not in existing:
                self.connection.execute(
                    f"ALTER TABLE queue_items ADD COLUMN {column} {declaration}"
                )
        self.connection.commit()

    def audit(self, piece_id: str, event: str, *, actor: str | None = None,
              details: Mapping[str, object] | None = None) -> None:
        safe_details = dict(details or {})
        forbidden = {"access_token", "token", "authorization", "secret"}
        if forbidden.intersection(key.lower() for key in safe_details):
            raise ValueError("campo sensível recusado pelo log de auditoria")
        self.connection.execute(
            "INSERT INTO audit_log(occurred_at,piece_id,event,actor,details_json) VALUES(?,?,?,?,?)",
            (utc_now(), piece_id, event, actor, json.dumps(safe_details, sort_keys=True)),
        )
        self.connection.commit()

    def enqueue(self, piece_id: str, media: str, caption: str, scheduled_at: str,
                content_policy: str = "other") -> QueueItem:
        if not piece_id.strip():
            raise ValidationError("identificador da peça é obrigatório")
        if content_policy not in CONTENT_POLICIES:
            raise ValidationError("política de conteúdo inválida")
        validate_payload(media, caption, scheduled_at)
        collaborators = CONTENT_POLICIES[content_policy]
        now = utc_now()
        try:
            self.connection.execute(
                """INSERT INTO queue_items(
                       piece_id,media,caption,scheduled_at,content_policy,
                       collaborators_json,status,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (piece_id, media, caption, scheduled_at, content_policy,
                 json.dumps(collaborators), "draft", now, now),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValidationError(f"a peça {piece_id!r} já existe") from exc
        self.audit(piece_id, "draft_created", details={
            "scheduled_at": scheduled_at, "content_policy": content_policy,
            "collaborators": list(collaborators),
        })
        return self.get(piece_id)

    def approve(self, piece_id: str, approved_by: str) -> QueueItem:
        actor = approved_by.strip()
        if not actor:
            raise ValidationError("approved_by é obrigatório")
        item = self.get(piece_id)
        if item.status not in ("draft", "failed"):
            raise ValidationError(f"estado {item.status!r} não permite aprovação")
        approved_at = bahia_now()
        self.connection.execute(
            """UPDATE queue_items
               SET status='approved',approved_by=?,approved_at=?,updated_at=?,failure_reason=NULL
               WHERE piece_id=?""",
            (actor, approved_at, approved_at, piece_id),
        )
        self.connection.commit()
        self.audit(piece_id, "approved", actor=actor,
                   details={"approved_at": approved_at, "piece_id": piece_id})
        return self.get(piece_id)

    def acquire_publish_lock(self, piece_id: str) -> str:
        owner = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            item = self.get(piece_id)
            if item.publish_lock_owner and item.publish_lock_at:
                if now - parse_aware_datetime(item.publish_lock_at) < timedelta(minutes=15):
                    raise ConcurrentPublishing("já existe uma execução de publicação ativa")
            now_text = now.isoformat()
            self.connection.execute(
                """UPDATE queue_items SET publish_lock_owner=?,publish_lock_at=?,
                   publish_started_at=COALESCE(publish_started_at,?),updated_at=?
                   WHERE piece_id=?""",
                (owner, now_text, now_text, now_text, piece_id),
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        self.audit(piece_id, "publish_lock_acquired")
        return owner

    def release_publish_lock(self, piece_id: str, owner: str) -> None:
        self.connection.execute(
            """UPDATE queue_items SET publish_lock_owner=NULL,publish_lock_at=NULL,updated_at=?
               WHERE piece_id=? AND publish_lock_owner=?""",
            (utc_now(), piece_id, owner),
        )
        self.connection.commit()

    def record_container(self, piece_id: str, container_id: str) -> None:
        self.connection.execute(
            "UPDATE queue_items SET remote_container_id=?,updated_at=? WHERE piece_id=?",
            (container_id, utc_now(), piece_id),
        )
        self.connection.commit()
        self.audit(piece_id, "container_created", details={"container_id": container_id})

    def mark_published(self, piece_id: str, media_id: str, permalink: str | None,
                       *, reconciled: bool) -> QueueItem:
        now = utc_now()
        cursor = self.connection.execute(
            """UPDATE queue_items SET status='published',remote_media_id=?,permalink=?,
               published_at=?,updated_at=?,failure_reason=NULL
               WHERE piece_id=? AND status='approved'""",
            (media_id, permalink, now, now, piece_id),
        )
        self.connection.commit()
        if cursor.rowcount != 1:
            raise ValidationError("transição para published recusada")
        self.audit(piece_id, "published_reconciled" if reconciled else "published",
                   details={"media_id": media_id, "permalink": permalink})
        return self.get(piece_id)

    def mark_failed(self, piece_id: str, reason_code: str) -> QueueItem:
        item = self.get(piece_id)
        if item.status == "published":
            raise ValidationError("item publicado não pode ser marcado como failed")
        if reason_code not in SAFE_FAILURE_CODES:
            raise ValidationError("código de falha inválido")
        now = utc_now()
        self.connection.execute(
            "UPDATE queue_items SET status='failed',failure_reason=?,updated_at=? WHERE piece_id=?",
            (reason_code, now, piece_id),
        )
        self.connection.commit()
        self.audit(piece_id, "failed", details={"reason_code": reason_code})
        return self.get(piece_id)

    def _row_to_item(self, row: sqlite3.Row) -> QueueItem:
        values = dict(row)
        values["collaborators"] = tuple(json.loads(values.pop("collaborators_json")))
        return QueueItem(**values)

    def get(self, piece_id: str) -> QueueItem:
        row = self.connection.execute(
            "SELECT * FROM queue_items WHERE piece_id=?", (piece_id,)
        ).fetchone()
        if row is None:
            raise ItemNotFound(f"peça não encontrada: {piece_id}")
        return self._row_to_item(row)

    def list_items(self) -> list[QueueItem]:
        rows = self.connection.execute(
            "SELECT * FROM queue_items ORDER BY created_at,piece_id"
        ).fetchall()
        return [self._row_to_item(row) for row in rows]

    def audit_entries(self) -> list[dict[str, object]]:
        rows = self.connection.execute(
            "SELECT occurred_at,piece_id,event,actor,details_json FROM audit_log ORDER BY id"
        ).fetchall()
        return [{"occurred_at": row["occurred_at"], "piece_id": row["piece_id"],
                 "event": row["event"], "actor": row["actor"],
                 "details": json.loads(row["details_json"])} for row in rows]


def validate_payload(media: str, caption: str, scheduled_at: str) -> None:
    validate_media_reference(media)
    if not caption.strip():
        raise ValidationError("legenda não pode ser vazia")
    if len(caption) > 2200:
        raise ValidationError("legenda excede 2.200 caracteres")
    parse_aware_datetime(scheduled_at)


def validate_media_reference(media: str) -> None:
    parsed = urllib.parse.urlparse(media)
    if parsed.scheme:
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValidationError("URL da mídia deve usar HTTPS e possuir host")
        if parsed.username or parsed.password:
            raise ValidationError("URL da mídia não pode conter credenciais")
        return
    path = Path(media)
    if not path.is_file():
        raise ValidationError(f"arquivo de mídia não encontrado: {media}")
    validate_jpeg(path.read_bytes(), "arquivo local")


def validate_jpeg(content: bytes, source: str) -> None:
    if (len(content) < 4 or not content.startswith(b"\xff\xd8")
            or not content.endswith(b"\xff\xd9")):
        raise ValidationError(f"{source} não é um JPEG íntegro")


class PublicMediaValidator:
    """GET público sem token, cookie, redirecionamento ou autorização."""

    def validate(self, url: str) -> dict[str, object]:
        request = urllib.request.Request(
            url, headers={
                "Accept": "image/jpeg",
                "User-Agent": "quero-midia-validator/1",
            },
            method="GET",
        )
        try:
            with urllib.request.build_opener(NoRedirects).open(request, timeout=30) as response:
                content_type = response.headers.get_content_type()
                content = response.read(25 * 1024 * 1024 + 1)
                status = response.status
        except urllib.error.HTTPError as exc:
            raise ValidationError(f"mídia pública respondeu HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ValidationError("não foi possível ler a mídia pública") from exc
        if status != 200:
            raise ValidationError(f"mídia pública respondeu HTTP {status}")
        if content_type != "image/jpeg":
            raise ValidationError(f"mídia pública deve ser image/jpeg, recebido {content_type}")
        if len(content) > 25 * 1024 * 1024:
            raise ValidationError("mídia pública excede 25 MiB")
        validate_jpeg(content, "mídia pública")
        return {"http_status": status, "content_type": content_type, "bytes": len(content)}


class InstagramClient:
    def __init__(self, credentials: Credentials) -> None:
        self.credentials = credentials
        self.opener = urllib.request.build_opener(NoRedirects)

    def _request(self, method: str, path: str,
                 parameters: Mapping[str, str] | None = None) -> dict[str, object]:
        encoded = urllib.parse.urlencode(parameters or {})
        if method == "GET":
            url, body = GRAPH_BASE_URL + path + ("?" + encoded if encoded else ""), None
        else:
            url, body = GRAPH_BASE_URL + path, encoded.encode("utf-8")
        request = urllib.request.Request(
            url, data=body, headers={
                "Authorization": f"Bearer {self.credentials.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "quero-midia-publisher/1",
            }, method=method,
        )
        try:
            with self.opener.open(request, timeout=30) as response:
                payload = json.loads(response.read(1024 * 1024))
        except urllib.error.HTTPError as exc:
            try:
                error_payload = json.loads(exc.read(1024 * 1024)).get("error", {})
            except (json.JSONDecodeError, AttributeError):
                error_payload = {}
            code = error_payload.get("code", "unknown")
            error_type = error_payload.get("type", "InstagramAPIError")
            raise InstagramAPIError(
                f"Instagram API recusou a operação (HTTP {exc.code}, {error_type}, código {code})",
                http_status=exc.code,
            ) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise InstagramAPIError("resposta da Instagram API ausente ou inválida") from exc
        if not isinstance(payload, dict):
            raise InstagramAPIError("resposta inesperada da Instagram API")
        return payload

    def get_username(self) -> str:
        payload = self._request("GET", "/" + urllib.parse.quote(
            self.credentials.user_id, safe=""), {"fields": "username"})
        username = payload.get("username")
        if not isinstance(username, str) or not username:
            raise ValidationError("resposta do perfil não contém username")
        return username

    def create_image_container(self, image_url: str, caption: str,
                               collaborators: tuple[str, ...]) -> str:
        parameters = {"image_url": image_url, "caption": caption}
        if collaborators:
            parameters["collaborators"] = json.dumps(list(collaborators))
        payload = self._request(
            "POST", "/" + urllib.parse.quote(self.credentials.user_id, safe="") + "/media",
            parameters,
        )
        container_id = payload.get("id")
        if not isinstance(container_id, str) or not container_id:
            raise InstagramAPIError("criação do contêiner não retornou id")
        return container_id

    def get_container_status(self, container_id: str) -> str:
        payload = self._request("GET", "/" + urllib.parse.quote(container_id, safe=""),
                                {"fields": "status_code"})
        status = payload.get("status_code")
        if not isinstance(status, str):
            raise InstagramAPIError("consulta do contêiner não retornou status_code")
        return status

    def publish_container(self, container_id: str) -> str:
        payload = self._request(
            "POST", "/" + urllib.parse.quote(self.credentials.user_id, safe="") + "/media_publish",
            {"creation_id": container_id},
        )
        media_id = payload.get("id")
        if not isinstance(media_id, str) or not media_id:
            raise InstagramAPIError("media_publish não retornou id")
        return media_id

    def get_media(self, media_id: str) -> dict[str, object]:
        return self._request("GET", "/" + urllib.parse.quote(media_id, safe=""),
                             {"fields": "id,permalink,media_type,timestamp"})

    def find_recent_media(self, caption: str, not_before: str) -> dict[str, object] | None:
        payload = self._request(
            "GET", "/" + urllib.parse.quote(self.credentials.user_id, safe="") + "/media",
            {"fields": "id,caption,permalink,timestamp", "limit": "25"},
        )
        cutoff = parse_aware_datetime(not_before) - timedelta(minutes=5)
        for media in payload.get("data", []):
            if not isinstance(media, dict) or media.get("caption") != caption:
                continue
            timestamp = media.get("timestamp")
            if isinstance(timestamp, str) and parse_aware_datetime(timestamp) >= cutoff:
                return media
        return None


class PublisherService:
    def __init__(self, queue: Queue, client_type=InstagramClient,
                 media_validator: PublicMediaValidator | None = None,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.queue = queue
        self.client_type = client_type
        self.media_validator = media_validator or PublicMediaValidator()
        self.sleep = sleep

    def _approved_item(self, piece_id: str, *, require_arthur: bool = False) -> QueueItem:
        item = self.queue.get(piece_id)
        if item.status != "approved":
            self.queue.audit(piece_id, "blocked_not_approved", details={"status": item.status})
            raise NotApproved(
                f"peça {piece_id!r} está em {item.status!r}; somente 'approved' é publicável"
            )
        if require_arthur and item.approved_by != REQUIRED_APPROVER:
            self.queue.audit(piece_id, "blocked_wrong_approver",
                             details={"approved_by": item.approved_by})
            raise NotApproved("publicação real exige aprovação explícita de Arthur")
        return item

    @staticmethod
    def _confirm_account(client: InstagramClient) -> str:
        username = client.get_username()
        if username != EXPECTED_USERNAME:
            raise ValidationError(
                f"conta divergente: esperado @{EXPECTED_USERNAME}, recebido @{username}"
            )
        return username

    def dry_run(self, piece_id: str,
                environment: Mapping[str, str] = os.environ) -> dict[str, object]:
        item = self._approved_item(piece_id)
        validate_payload(item.media, item.caption, item.scheduled_at)
        username = self._confirm_account(
            self.client_type(Credentials.from_environment(environment))
        )
        self.queue.audit(piece_id, "dry_run_passed",
                         details={"username": username, "scheduled_at": item.scheduled_at})
        return {
            "mode": "dry-run", "piece_id": piece_id, "status": item.status,
            "account": "@" + username, "scheduled_at": item.scheduled_at,
            "collaborators": list(item.collaborators),
            "publishing_enabled": is_publishing_enabled(environment),
            "result": "validated; no media container created and nothing published",
        }

    def _reconcile(self, item: QueueItem, client: InstagramClient) -> QueueItem | None:
        if item.remote_media_id:
            media = client.get_media(item.remote_media_id)
            return self.queue.mark_published(
                item.piece_id, str(media.get("id", item.remote_media_id)),
                media.get("permalink") if isinstance(media.get("permalink"), str) else None,
                reconciled=True,
            )
        not_before = item.publish_started_at or item.approved_at
        if not_before:
            media = client.find_recent_media(item.caption, not_before)
            if media and isinstance(media.get("id"), str):
                return self.queue.mark_published(
                    item.piece_id, media["id"],
                    media.get("permalink") if isinstance(media.get("permalink"), str) else None,
                    reconciled=True,
                )
        return None

    def publish(self, piece_id: str,
                environment: Mapping[str, str] = os.environ) -> QueueItem:
        item = self._approved_item(piece_id, require_arthur=True)
        if not is_publishing_enabled(environment):
            self.queue.audit(piece_id, "blocked_publishing_disabled")
            raise PublishingDisabled(
                "publicação bloqueada: INSTAGRAM_PUBLISHING_ENABLED não é true"
            )
        validate_payload(item.media, item.caption, item.scheduled_at)
        if urllib.parse.urlparse(item.media).scheme != "https":
            raise ValidationError("publicação real exige uma URL HTTPS pública da imagem")
        owner = self.queue.acquire_publish_lock(piece_id)
        try:
            client = self.client_type(Credentials.from_environment(environment))
            self._confirm_account(client)
            self.media_validator.validate(item.media)
            item = self.queue.get(piece_id)
            reconciled = self._reconcile(item, client)
            if reconciled:
                return reconciled
            container_id = item.remote_container_id
            if not container_id:
                # Exatamente uma tentativa; rejeição de colaboradores não tem fallback.
                container_id = client.create_image_container(
                    item.media, item.caption, item.collaborators
                )
                self.queue.record_container(piece_id, container_id)
            for attempt in range(12):
                container_status = client.get_container_status(container_id)
                if container_status == "FINISHED":
                    break
                if container_status in {"ERROR", "EXPIRED"}:
                    self.queue.mark_failed(piece_id, "container_failed")
                    raise InstagramAPIError(
                        f"contêiner terminou com status {container_status}"
                    )
                if attempt == 11:
                    raise InstagramAPIError(
                        "contêiner ainda não ficou pronto; execução interrompida sem publicar"
                    )
                self.sleep(5)
            item = self.queue.get(piece_id)
            reconciled = self._reconcile(item, client)
            if reconciled:
                return reconciled
            try:
                media_id = client.publish_container(container_id)
            except InstagramAPIError:
                # Reconcilia por leitura uma vez; nunca repete media_publish.
                reconciled = self._reconcile(self.queue.get(piece_id), client)
                if reconciled:
                    return reconciled
                self.queue.mark_failed(piece_id, "publishing_ambiguous")
                raise
            media = client.get_media(media_id)
            return self.queue.mark_published(
                piece_id, media_id,
                media.get("permalink") if isinstance(media.get("permalink"), str) else None,
                reconciled=False,
            )
        finally:
            self.queue.release_publish_lock(piece_id, owner)


def is_publishing_enabled(environment: Mapping[str, str]) -> bool:
    return environment.get("INSTAGRAM_PUBLISHING_ENABLED", "false").strip().lower() == "true"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB), help="arquivo SQLite da fila")
    commands = parser.add_subparsers(dest="command", required=True)
    enqueue = commands.add_parser("enqueue", help="cria um item draft")
    enqueue.add_argument("--piece-id", required=True)
    enqueue.add_argument("--media", required=True)
    enqueue.add_argument("--caption", required=True)
    enqueue.add_argument("--scheduled-at", required=True)
    enqueue.add_argument("--content-policy", choices=sorted(CONTENT_POLICIES), default="other")
    approve = commands.add_parser("approve", help="aprova e registra o responsável")
    approve.add_argument("--piece-id", required=True)
    approve.add_argument("--approved-by", required=True)
    run = commands.add_parser("run", help="executa dry-run por padrão")
    run.add_argument("--piece-id", required=True)
    run.add_argument("--execute", action="store_true",
                     help="solicita publicação real explicitamente")
    commands.add_parser("list", help="lista a fila")
    commands.add_parser("audit", help="mostra auditoria sem segredos")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    queue = Queue(arguments.db)
    try:
        if arguments.command == "enqueue":
            result = queue.enqueue(
                arguments.piece_id, arguments.media, arguments.caption,
                arguments.scheduled_at, arguments.content_policy,
            )
        elif arguments.command == "approve":
            result = queue.approve(arguments.piece_id, arguments.approved_by)
        elif arguments.command == "run":
            service = PublisherService(queue)
            result = (service.publish(arguments.piece_id) if arguments.execute
                      else service.dry_run(arguments.piece_id))
        elif arguments.command == "list":
            result = queue.list_items()
        else:
            result = queue.audit_entries()
        if isinstance(result, QueueItem):
            result = asdict(result)
        elif isinstance(result, list) and result and isinstance(result[0], QueueItem):
            result = [asdict(item) for item in result]
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except PublisherError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2
    finally:
        queue.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
