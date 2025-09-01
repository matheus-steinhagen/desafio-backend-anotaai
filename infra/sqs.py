"""
Helpers do SQS
send_catalog_event
    sqs_client, queue_name, owner_id, event_type, entity_id
Assume-se que a fila é do tipo FIFO (queue_name possui a extensão .fifo)
Usa `MessageGroupoId` = `owner_id` e `MessageDeduplicationId` = `sha256(owner+entity+timestamp)[:128]`

"""

from __future__ import annotations
import logging, time, json, hashlib, math
from typing import Any, Dict
from botocore.exceptions import ClientError

log = logging.getLogger(__name__)

def _get_queue_url(sqs_client, queue_name: str) -> str:
    resp = sqs_client.get_queue_url(QueueName=queue_name)
    return resp["QueueUrl"]

def _dedupe_id(owner_id: str, entity_id: str, timestamp: str) -> str:
    raw = f"{owner_id}:{entity_id}:{timestamp}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    # AWS permite até 128 chars para dedupe de ID;
    # Hex sha256 é 64 chars, portantp é seguro
    return h

def send_catalog_event(
    sqs_client,
    queue_name: str,
    owner_id: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload_extra: Dict[str, Any] | None = None,
    max_retries: int = 3,
    base_delay: float = 0.25,
) -> Dict[str, Any]:
    """
    Envia uma mensagem para a fila SQS alvo
    Tentativas em falhas recursivas com backoff exponencial
    Gera um dict response SendMessage se bem sucedido
    """
    queue_url = _get_queue_url(sqs_client, queue_name)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    body = {
        "owner_id": owner_id,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "timestamp": ts
    }
    if payload_extra:
        body["data"] = payload_extra

    dedup_id = _dedupe_id(owner_id, entity_id, ts)
    group_id = owner_id
    message_body = json.dumps(body)

    attempt = 0
    while True:
        try:
            resp = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body,
            MessageGroupId=group_id,
            MessageDeduplicationId=dedup_id,
            )
            log.debug("SQS mensagem enviada owner=%s event=%s msgid=%s", owner_id, event_type, resp.get("MessageId"))
            return resp
        except ClientError as e:
            attempt += 1
            code = e.response.get("Error", {}).get("Code")
            log.exception("SQS send_message falhou (attempt %d) code=%s", attempt, code)
            if attempt > max_retries:
                log.error("Máximo de tentativas atingido para envio de mensagens SQS owner=%s event=%s", owner_id, event_type)
                raise
            # Backoff exponencial com jitter
            backoff = base_delay * (2 ** (attempt - 1))
            jitter = backoff * 0.1 * (0.5 - (time.time() % 1)) # pequeno jitter determinístico
            sleep_for = max(0.05, backoff + jitter)
            time.sleep(sleep_for)