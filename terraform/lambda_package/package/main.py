import os, io, json, time, uuid, logging, csv, botocore
from typing import List, Dict
import boto3, requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
HF_MODEL_ID = os.environ.get("HF_MODEL_ID", "cardiffnlp/twitter-roberta-base-sentiment-latest")
INGEST_BUCKET = os.environ["INGEST_BUCKET"]
WEBSITE_BUCKET = os.environ["WEBSITE_BUCKET"]
RESULTS_PREFIX = os.environ.get("RESULTS_PREFIX", "results")
CSV_SUFFIX = os.environ.get("CSV_SUFFIX", ".csv")

HF_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"} if HF_API_TOKEN else {}

TEXT_COLUMNS_CANDIDATES = ["text", "tweet", "content", "message", "body"]
INDEX_KEY = f"{RESULTS_PREFIX}/index.json"

def call_hf(text: str):
    payload = {"inputs": text}
    for attempt in range(4):
        resp = requests.post(HF_URL, headers=HF_HEADERS, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (429, 503):
            wait = 1.5 * (attempt + 1)
            time.sleep(wait)
            continue
    return {"error": f"HF status {resp.status_code} -> {resp.text[:200]}"}

def extract_sentiment(hf_output) -> Dict[str, float | str]:
    try:
        preds = hf_output[0] if isinstance(hf_output, list) and hf_output and isinstance(hf_output[0], list) else hf_output
        if isinstance(preds, list) and preds and isinstance(preds[0], dict) and "label" in preds[0]:
            best = max(preds, key=lambda x: x["score"])
            probs = {p["label"]: float(p["score"]) for p in preds}
            return {"label": best["label"], **probs}
        return {"label": "UNKNOWN"}
    except Exception as e:
        return {"label": "ERROR", "error": str(e)}

def detect_text_column(header: List[str]) -> str | None:
    lower = {c.lower(): c for c in header}
    for cand in TEXT_COLUMNS_CANDIDATES:
        if cand in lower:
            return lower[cand]
    return header[0] if header else None

def process_csv_streaming(bucket: str, key: str):
    resp = s3.get_object(Bucket=bucket, Key=key)
    body = resp["Body"].read()
    text_stream = io.StringIO(body.decode("utf-8", errors="ignore"))
    reader = csv.DictReader(text_stream)
    header = reader.fieldnames or []
    text_col = detect_text_column(header)
    if not text_col:
        raise ValueError("No se encontró columna de texto en el CSV.")

    records = []
    for row in reader:
        txt = (row.get(text_col) or "").strip()
        out = call_hf(txt) if txt else {"label": "EMPTY"}
        norm = extract_sentiment(out)
        row["sentiment"] = norm.get("label", "UNKNOWN")
        for k, v in norm.items():
            if k != "label":
                row[f"score_{k}"] = v
        records.append(row)
    return records

def update_index(upload_id: str):
    """Mantiene results/index.json como lista de upload_ids (últimos 100)."""
    ids = []
    try:
        obj = s3.get_object(Bucket=WEBSITE_BUCKET, Key=INDEX_KEY)
        data = obj["Body"].read().decode("utf-8", errors="ignore")
        current = json.loads(data)
        if isinstance(current, list):
            ids = current
    except botocore.exceptions.ClientError as e:
        if e.response.get("Error", {}).get("Code") != "NoSuchKey":
            # Si falta permiso GetObject u otro error, lo logeamos y seguimos (solo no habrá histórico)
            logger.warning(f"No se pudo leer {INDEX_KEY}: {e}")

    # Inserta al principio, quita duplicados preservando orden, limita a 100
    new_ids = [upload_id] + ids
    seen = set()
    deduped = []
    for x in new_ids:
        if x in seen:
            continue
        seen.add(x)
        deduped.append(x)
        if len(deduped) >= 100:
            break

    s3.put_object(
        Bucket=WEBSITE_BUCKET,
        Key=INDEX_KEY,
        Body=json.dumps(deduped, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
        CacheControl="no-cache"
    )

def save_results(upload_id: str, records: List[Dict]):
    result_dir = f"{RESULTS_PREFIX}/{upload_id}"
    jsonl_key = f"{result_dir}/predictions.jsonl"
    summary_key = f"{result_dir}/summary.json"

    jsonl_bytes = "\n".join(json.dumps(r, ensure_ascii=False) for r in records).encode("utf-8")
    s3.put_object(Bucket=WEBSITE_BUCKET, Key=jsonl_key, Body=jsonl_bytes, ContentType="application/json")

    counts = {}
    for r in records:
        lbl = r.get("sentiment", "UNKNOWN")
        counts[lbl] = counts.get(lbl, 0) + 1

    summary = {
        "upload_id": upload_id,
        "total": len(records),
        "counts": counts,
        "jsonl": jsonl_key,
        "generated_at": int(time.time())
    }
    s3.put_object(
        Bucket=WEBSITE_BUCKET,
        Key=summary_key,
        Body=json.dumps(summary, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
        CacheControl="no-cache"
    )

    # Actualiza/crea el índice de runs
    update_index(upload_id)

def handler(event, context):
    logger.info("Event: %s", json.dumps(event))
    for rec in event.get("Records", []):
        s3info = rec.get("s3", {})
        b = s3info.get("bucket", {}).get("name")
        k = s3info.get("object", {}).get("key")
        if not k.endswith(CSV_SUFFIX):
            continue
        upload_id = uuid.uuid4().hex[:8]
        records = process_csv_streaming(b, k)
        save_results(upload_id, records)
        logger.info(f"Saved results to s3://{WEBSITE_BUCKET}/{RESULTS_PREFIX}/{upload_id}/")
    return {"status": "ok"}
