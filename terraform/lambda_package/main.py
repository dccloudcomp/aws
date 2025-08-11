import os, io, json, time, uuid, logging, csv, botocore
from typing import List, Dict
import boto3, requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
HF_MODEL_ID = os.environ.get("HF_MODEL_ID", "cardiffnlp/twitter-roberta-base-sentiment")
INGEST_BUCKET = os.environ["INGEST_BUCKET"]
WEBSITE_BUCKET = os.environ["WEBSITE_BUCKET"]
RESULTS_PREFIX = os.environ.get("RESULTS_PREFIX", "results")
CSV_SUFFIX = os.environ.get("CSV_SUFFIX", ".csv")

logger.info(f"Usando modelo: {HF_MODEL_ID}")
logger.info(f"Token presente: {'sí' if HF_API_TOKEN else 'no'}")

HF_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"} if HF_API_TOKEN else {}

TEXT_COLUMNS_CANDIDATES = ["text", "tweet", "content", "message", "body"]
INDEX_KEY = f"{RESULTS_PREFIX}/index.json"

DEBUG_LOGGED = False

def call_hf(text: str):
    global DEBUG_LOGGED
    payload = {
        "inputs": text,
        "options": {"wait_for_model": True},
        "parameters": {"return_all_scores": True}
    }
    for attempt in range(6):
        try:
            resp = requests.post(HF_URL, headers=HF_HEADERS, json=payload, timeout=30)
            status = resp.status_code
            ctype = resp.headers.get("content-type","")
            body = resp.text
        except Exception as e:
            return {"error": f"exception during request: {e}"}

        # <-- LOG DE DIAGNÓSTICO UNA SOLA VEZ
        if not DEBUG_LOGGED:
            logger.info("HF status=%s ctype=%s body[0:200]=%s", status, ctype, body[:200])
            DEBUG_LOGGED = True
        # -----------------------------------

        if "application/json" not in ctype.lower():
            if status in (429, 503):
                time.sleep(1.5 * (attempt + 1))
                continue
            return {"error": f"HTTP {status} non-JSON: {body[:200]}"}

        try:
            data = resp.json()
        except Exception as e:
            if status in (429, 503):
                time.sleep(1.5 * (attempt + 1))
                continue
            return {"error": f"HTTP {status} invalid JSON: {str(e)}; body={body[:200]}"}

        if status == 200 and isinstance(data, dict) and "error" in data:
            time.sleep(1.5 * (attempt + 1))
            continue

        if status == 200:
            return data

        if status in (429, 503):
            time.sleep(1.5 * (attempt + 1))
            continue

        return {"error": f"HTTP {status}: {str(data)[:200]}"}

    return {"error": "HF did not return a valid response after retries"}

def extract_sentiment(hf_result):
    try:
        if isinstance(hf_result, list):
            if len(hf_result) > 0 and isinstance(hf_result[0], list):
                scores = hf_result[0]
                if scores and isinstance(scores[0], dict):
                    best = max(scores, key=lambda x: x.get("score", 0))
                    return {"label": normalize_label(best.get("label"))}
            elif hf_result and isinstance(hf_result[0], dict):
                best = max(hf_result, key=lambda x: x.get("score", 0))
                return {"label": normalize_label(best.get("label"))}
        if isinstance(hf_result, dict) and "labels" in hf_result and "scores" in hf_result:
            labels = hf_result["labels"]; scores = hf_result["scores"]
            if labels and scores and len(labels) == len(scores):
                best_idx = scores.index(max(scores))
                return {"label": normalize_label(labels[best_idx])}
    except Exception as e:
        logger.warning(f"Error procesando resultado HF: {e}")
    return {"label": "UNKNOWN"}

def normalize_label(label):
    if not label:
        return "UNKNOWN"
    l = str(label).strip().lower()
    if l in ("positive", "pos", "label_2"): return "POSITIVE"
    if l in ("negative", "neg", "label_0"): return "NEGATIVE"
    if l in ("neutral", "neu", "label_1"):  return "NEUTRAL"
    if "pos" in l: return "POSITIVE"
    if "neg" in l: return "NEGATIVE"
    if "neu" in l: return "NEUTRAL"
    return "UNKNOWN"

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
