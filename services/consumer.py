# services/consumer.py (versão corrigida)
from __future__ import annotations
from typing import Any, List, Iterable, Dict
import json
import time
import logging

from api.deps import get_aws_clients
from infra.aws_client import put_s3_object
from services.catalog_generator import generate_catalog

log = logging.getLogger(__name__)

class Consumer:
    def __init__(self, max_receive: int = 10):
        clients = get_aws_clients()
        self.sqs = clients["sqs"]
        self.dynamo = clients["dynamo"]
        self.s3 = clients["s3"]
        self.queue_name = clients["settings"].sqs_queue
        self.table_name = clients["settings"].dynamo_table
        self.bucket_name = clients["settings"].s3_bucket
        self.max_receive = max(1, min(10, int(max_receive)))

    def _get_queue_url(self) -> str:
        resp = self.sqs.get_queue_url(QueueName=self.queue_name)
        return resp["QueueUrl"]

    def _process_owner(self, owner_id: str) -> None:
        log.info("Gerando catálogo para owner=%s", owner_id)
        catalog = generate_catalog(self.dynamo, self.table_name, owner_id)
        key = f"catalogs/{owner_id}/catalog.json"
        payload = json.dumps(catalog, indent=2).encode("utf-8")

        # Pode ser útil retry simples aqui para put_s3_object
        try:
            put_s3_object(self.s3, self.bucket_name, key, payload)
            log.info("Catálogo salvo s3://%s/%s (bytes=%d)", self.bucket_name, key, len(payload))
        except Exception:
            log.exception("Falha ao gravar catálogo no S3 para owner=%s", owner_id)
            raise

    def process_batch(self, messages: Iterable[dict]) -> Dict[str, List[str]]:
        """
        Processa mensagens: retorna mapping owner_id -> list(receipt_handles)
        Não deleta mensagens aqui; retorna os receipt handles para deletar apenas os owners com sucesso.
        """
        owner_to_receipts: Dict[str, List[str]] = {}
        for msg in messages:
            body_text = msg.get("Body")
            msg_id = msg.get("MessageId")
            if not body_text:
                log.warning("Ignorando mensagem sem Body (MessageId=%s)", msg_id)
                # Decidir: se é invalida e irreparavel, mover para DLQ ou deletar. Aqui só ignoramos.
                continue
            try:
                body = json.loads(body_text)
            except Exception:
                log.exception("Body JSON inválido (MessageId=%s) - considerar mover para DLQ", msg_id)
                continue

            owner = body.get("owner_id")
            if not owner:
                log.warning("Mensagem sem owner_id (MessageId=%s) - ignorando", msg_id)
                continue

            receipts = owner_to_receipts.setdefault(owner, [])
            receipts.append(msg["ReceiptHandle"])

        # process owners (one pass)
        processed_successfully: List[str] = []
        for owner_id, receipts in owner_to_receipts.items():
            try:
                self._process_owner(owner_id)
                processed_successfully.append(owner_id)
            except Exception:
                log.exception("Erro ao processar owner=%s; deixando mensagens para retry", owner_id)
                # não remover receipts desse owner -> ficará para reentrega/retentativa
        return {owner: owner_to_receipts[owner] for owner in processed_successfully}

    def _delete_receipts_batch(self, queue_url: str, receipt_handles: List[str]) -> None:
        """
        Deleta receipts em batches de até 10 usando delete_message_batch.
        """
        entries = []
        for i, rh in enumerate(receipt_handles):
            entries.append({"Id": str(i), "ReceiptHandle": rh})
            if len(entries) == 10:
                try:
                    self.sqs.delete_message_batch(QueueUrl=queue_url, Entries=entries)
                except Exception:
                    log.exception("Falha delete_message_batch")
                entries = []
        if entries:
            try:
                self.sqs.delete_message_batch(QueueUrl=queue_url, Entries=entries)
            except Exception:
                log.exception("Falha delete_message_batch (final)")

    def run(self, poll_interval: int = 5, wait_time_seconds: int = 10, visibility_timeout: int = 60) -> None:
        queue_url = self._get_queue_url()
        log.info("Consumidor iniciado (queue=%s)", queue_url)
        try:
            while True:
                resp = self.sqs.receive_message(
                    QueueUrl=queue_url,                         # CORREÇÃO: use QueueUrl
                    MaxNumberOfMessages=self.max_receive,
                    WaitTimeSeconds=wait_time_seconds,
                    VisibilityTimeout=visibility_timeout,
                    MessageAttributeNames=["All"],
                )
                messages: List[dict] = resp.get("Messages", []) or []
                if not messages:
                    log.debug("Nenhuma mensagem; sleeping %ds", poll_interval)
                    time.sleep(poll_interval)
                    continue

                log.info("Recebidas %d mensagens", len(messages))
                # processa e recebe mapping dos owners que foram processados com sucesso
                try:
                    owner_to_deleted_receipts = self.process_batch(messages)
                except Exception:
                    log.exception("Erro inesperado processando batch")
                    owner_to_deleted_receipts = {}

                # deletar receipts apenas para owners processados com sucesso
                # consolidar todas receipt handles e deletar em batch
                all_receipts_to_delete: List[str] = []
                for receipts in owner_to_deleted_receipts.values():
                    all_receipts_to_delete.extend(receipts)

                if all_receipts_to_delete:
                    self._delete_receipts_batch(queue_url, all_receipts_to_delete)
        except KeyboardInterrupt:
            log.info("Consumidor interrompido pelo usuário")
        except Exception:
            log.exception("Consumidor parou por erro inesperado")
            raise
