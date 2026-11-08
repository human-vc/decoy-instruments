import argparse
import hashlib
import json
import os
import random
import sys
import threading
import time
import concurrent.futures as cf
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import scenarios_v2 as V
import estimate_v2 as E
import cost_v2 as C

OUT = ROOT / "out5"
OUT.mkdir(exist_ok=True)

MODELS = {
    "opus-5.5": ("anthropic", "claude-opus-5-5", dict(thinking={"type": "adaptive"}, output_config={"effort": "medium"})),
    "sonnet-5.5": ("anthropic", "claude-sonnet-5-5", dict(thinking={"type": "adaptive"}, output_config={"effort": "high"})),
    "haiku-5.5": ("anthropic", "claude-haiku-5-5", dict(thinking={"type": "adaptive"}, output_config={"effort": "medium"})),
    "haiku-4.5": ("anthropic", "claude-haiku-4-5", {}),
    "fable-5.1": ("anthropic", "claude-fable-5-1", dict(thinking={"type": "adaptive"}, output_config={"effort": "medium"})),
    "haiku-4.5-think": ("anthropic", "claude-haiku-4-5", dict(thinking={"type": "enabled", "budget_tokens": 8000})),
    "gpt-6.1-sol": ("openai", "gpt-6.1-sol", dict(service_tier="flex")),
    "gpt-5-mini": ("openai", "gpt-5-mini", dict(service_tier="flex")),
    "gpt-4o-mini": ("openai", "gpt-4o-mini", {}),
    "gemini-4-argon": ("openrouter", "google/gemini-4-argon",
                       dict(provider={"only": ["google-ai-studio/flex"], "allow_fallbacks": False},
                            reasoning={"effort": "medium"})),
    "gemini-3.8-flash": ("openrouter", "google/gemini-3.8-flash",
                         dict(provider={"only": ["google-ai-studio/flex"], "allow_fallbacks": False},
                              reasoning={"effort": "medium"})),
    "gemma-4-31b": ("openrouter", "google/gemma-4-31b-it",
                    dict(provider={"only": ["crusoe/bf16"], "allow_fallbacks": False})),
    "qwen-3.8-27b": ("openrouter", "qwen/qwen3.8-27b",
                     dict(provider={"only": ["deepinfra/bf16"], "allow_fallbacks": False})),
    "deepseek-v4.1-flash": ("openrouter", "deepseek/deepseek-v4.1-flash",
                            dict(provider={"only": ["deepinfra/fp8/flex"], "allow_fallbacks": False})),
}
MAX_TOKENS = 16000
MAX_TOKENS_BY = {"qwen-3.8-27b": 32768}
ANTHROPIC_BATCH = False
PINNED_PRICE = {
    "gemini-4-argon": dict(i=1.0, r=0.05, o=5.0),
    "gemini-3.8-flash": dict(i=0.375, r=0.0375, o=1.875),
    "gemma-4-31b": dict(i=0.14, r=0.14, o=0.40),
    "qwen-3.8-27b": dict(i=0.15, r=0.15, o=1.875),
    "deepseek-v4.1-flash": dict(i=0.112, r=0.00336, o=0.336),
}
ADDED = {"fable-5.1": "opus-5.5", "haiku-4.5-think": "haiku-4.5"}
ADDED_PRICE = {
    "fable-5.1": dict(i=10.00, w5=12.50, w60=20.00, r=0.25, o=50.0, batch=0.5, cache="explicit"),
    "haiku-4.5-think": dict(C.PRICE["haiku-4.5"]),
}
PRICE = {**C.PRICE, **ADDED_PRICE}
SEED = 20261106
TRUNCATED = {"max_tokens", "length"}
KEPT_STOPS = TRUNCATED | {"refusal", "content_filter"}
FROZEN = ["scenarios_v2.py", "estimate_v2.py", "power_v2.py", "cost_v2.py", "kill3.py", "abs_v2.py", "analyze_v2.py"]


def now():
    return datetime.now(timezone.utc).isoformat()


def manifest(tier):
    rows = C.manifest(tier)
    return rows + [(new,) + r[1:] for new, src in ADDED.items() for r in rows if r[0] == src]


def max_tokens(model):
    return MAX_TOKENS_BY.get(model, MAX_TOKENS)


def logged_params(model):
    be, mid, extra = MODELS[model]
    return dict(backend=be, model_id=mid, max_tokens=max_tokens(model) if be != "openai" else None, **extra)


def row_key(r):
    m, step, key, version, arm, threat, i = r
    return f"{m}|{step}|{key}|{version}|{arm}|{int(threat)}|{i}"


def cid(k):
    return hashlib.sha1(k.encode()).hexdigest()[:40]


_EST = {}
_EST_LOCK = threading.Lock()


def build(r):
    m, step, key, version, arm, threat, i = r
    if step == "agent":
        prefix, middle, tail = V.agent_parts(key, version, arm, threat)
        return dict(parts=[prefix, middle, tail], truth=None)
    if step == "recall":
        return dict(parts=[V.recall_parts(key, version, arm == "named")], truth=None)
    with _EST_LOCK:
        if (key, version) not in _EST:
            _EST[(key, version)] = E.estimate_prompt(key, version)
        p, truth = _EST[(key, version)]
    return dict(parts=[p], truth=truth)


def prompt_sha(parts):
    return hashlib.sha256("".join(parts).encode()).hexdigest()


_CLIENTS = {}
_CLIENT_LOCK = threading.Lock()


def client(backend):
    with _CLIENT_LOCK:
        if backend not in _CLIENTS:
            if backend == "anthropic":
                import anthropic
                _CLIENTS[backend] = anthropic.Anthropic(max_retries=6, timeout=1800)
            elif backend == "openai":
                from openai import OpenAI
                _CLIENTS[backend] = OpenAI(timeout=1800, max_retries=6)
            else:
                from openai import OpenAI
                _CLIENTS[backend] = OpenAI(base_url="https://openrouter.ai/api/v1",
                                           api_key=os.environ["OPENROUTER_API_KEY"], timeout=1800, max_retries=6)
        return _CLIENTS[backend]


def anthropic_content(parts):
    if len(parts) == 1:
        return parts[0]
    blocks = [{"type": "text", "text": t, "cache_control": {"type": "ephemeral"}} for t in parts[:-1]]
    return blocks + [{"type": "text", "text": parts[-1]}]


def anthropic_params(model, parts):
    _, mid, extra = MODELS[model]
    return dict(model=mid, max_tokens=max_tokens(model), messages=[{"role": "user", "content": anthropic_content(parts)}],
                **extra)


def anthropic_record(msg):
    text = "".join(b.text for b in msg.content if b.type == "text")
    u = msg.usage
    usage = dict(inp=u.input_tokens, cache_read=u.cache_read_input_tokens or 0,
                 cache_write=u.cache_creation_input_tokens or 0, out=u.output_tokens)
    sd = getattr(msg, "stop_details", None)
    meta = dict(model_returned=msg.model, request_id=msg.id, stop_reason=msg.stop_reason, provider="anthropic")
    if sd is not None:
        meta["stop_details"] = sd.to_dict() if hasattr(sd, "to_dict") else str(sd)
    return text, usage, meta


def call_sync(model, parts):
    be, mid, extra = MODELS[model]
    if be == "anthropic":
        return anthropic_record(client("anthropic").messages.create(**anthropic_params(model, parts)))
    text_in = "".join(parts)
    content = text_in
    if be == "openrouter" and "gemini" in mid and len(parts) == 3:
        content = [{"type": "text", "text": parts[0], "cache_control": {"type": "ephemeral"}},
                   {"type": "text", "text": parts[1] + parts[2]}]
    if be == "openai":
        r = client("openai").chat.completions.create(model=mid, messages=[{"role": "user", "content": text_in}], **extra)
        prov = "openai"
    else:
        r = client("openrouter").chat.completions.create(model=mid, messages=[{"role": "user", "content": content}],
                                                         max_tokens=max_tokens(model), extra_body=extra)
        prov = getattr(r, "provider", None) or (r.model_extra or {}).get("provider")
    text = r.choices[0].message.content or ""
    u = r.usage
    det = getattr(u, "prompt_tokens_details", None)
    cached = (getattr(det, "cached_tokens", 0) or 0) if det else 0
    cd = getattr(u, "completion_tokens_details", None)
    usage = dict(inp=u.prompt_tokens - cached, cache_read=cached, cache_write=0, out=u.completion_tokens,
                 reasoning=(getattr(cd, "reasoning_tokens", None) if cd else None))
    if be == "openrouter":
        usage["cost_reported"] = (getattr(u, "model_extra", None) or {}).get("cost")
    meta = dict(model_returned=r.model, request_id=r.id, stop_reason=r.choices[0].finish_reason, provider=prov,
                service_tier=getattr(r, "service_tier", None))
    if "</think>" in text:
        print(model, "WARNING: reasoning text inside content", flush=True)
    return text, usage, meta


def price(model, usage, batch=False):
    if usage.get("cost_reported") is not None:
        return float(usage["cost_reported"])
    if model in PINNED_PRICE:
        p = PINNED_PRICE[model]
        return (usage["inp"] * p["i"] + usage["cache_read"] * p["r"] + usage["out"] * p["o"]) / 1e6
    p = PRICE[model]
    d = 0.5 if batch else 1.0
    if MODELS[model][0] == "openai" and "service_tier" in MODELS[model][2]:
        d = 0.5
    return d * (usage["inp"] * p["i"] + usage["cache_read"] * p["r"] + usage["cache_write"] * (p["w60"] if batch else p["w5"]) +
                usage["out"] * p["o"]) / 1e6


class Store:
    def __init__(self, model):
        self.path = OUT / f"{model}.jsonl"
        self.fail_path = OUT / f"fail_{model}.log"
        self.done = {}
        self.spent = 0.0
        self.lock = threading.Lock()
        if self.path.exists():
            for n, line in enumerate(self.path.open()):
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    print(f"{model}: skipping unreadable line {n + 1} of {self.path.name}", flush=True)
                    continue
                if rec["key"] in self.done:
                    continue
                self.done[rec["key"]] = rec
                self.spent += rec["cost"]

    def write(self, rec):
        with self.lock:
            if rec["key"] in self.done:
                return False
            self.done[rec["key"]] = rec
            self.spent += rec["cost"]
            with self.path.open("a") as f:
                f.write(json.dumps(rec) + "\n")
            return True

    def fail(self, key, kind, detail):
        with self.lock:
            with self.fail_path.open("a") as f:
                f.write(json.dumps(dict(key=key, kind=kind, detail=str(detail)[:500], ts=now())) + "\n")


def ordered(rows, model):
    rng = random.Random(f"{SEED}|{model}")
    keys = sorted(sorted({r[2] for r in rows}), key=lambda k: rng.random())
    out = []
    for k in keys:
        block = [r for r in rows if r[2] == k]
        rng.shuffle(block)
        block.sort(key=lambda r: 0 if r[1] == "agent" else 1)
        out += block
    return out


def pick_warms(block, model):
    agent = [r for r in block if r[1] == "agent"]
    if MODELS[model][0] != "anthropic":
        w = pick_warm(block)
        return [w] if w is not None else []
    out, seen = [], set()
    for r in agent:
        if r[3] not in seen:
            seen.add(r[3])
            out.append(r)
    return out


def pick_warm(block):
    agent = [r for r in block if r[1] == "agent"]
    return next((r for r in agent if r[3] != "mono"), agent[0] if agent else None)


def record(r, text, usage, meta, cost, truth, route, sha=None):
    return dict(key=row_key(r), model=r[0], step=r[1], setting=r[2], version=r[3], arm=r[4], threat=r[5], i=r[6],
                text=text, usage=usage, cost=cost, truth=truth, route=route, params=logged_params(r[0]),
                prompt_sha256=sha, ts=now(), **meta)


def usable(st, model, k, text, meta):
    sr = meta.get("stop_reason")
    if sr == "error" or (not text.strip() and sr not in KEPT_STOPS):
        st.fail(k, "empty_or_error", sr)
        print(model, k, "EMPTY/ERROR, not recorded", sr, flush=True)
        return False
    if sr in KEPT_STOPS:
        print(model, k, "recorded with stop reason", sr, flush=True)
    return True


def run_sync(model, rows, cap, workers):
    st = Store(model)
    todo = [r for r in ordered(rows, model) if row_key(r) not in st.done]
    print(f"{model}: {len(st.done)} done, {len(todo)} to run (sync), spent ${st.spent:.2f}, cap ${cap:.2f}", flush=True)
    stop = threading.Event()

    def work(r):
        if stop.is_set():
            return
        k = row_key(r)
        try:
            b = build(r)
            text, usage, meta = call_sync(model, b["parts"])
        except Exception as e:
            status = getattr(e, "status_code", None)
            st.fail(k, "error", f"{status} {e}")
            print(model, k, "ERROR", status, str(e)[:200], flush=True)
            if status == 402:
                stop.set()
                print(f"{model}: out of credit (402); stopping this model, rerun the same command after topping up",
                      flush=True)
            return
        try:
            if not usable(st, model, k, text, meta):
                return
            st.write(record(r, text, usage, meta, price(model, usage), b["truth"], "sync", prompt_sha(b["parts"])))
        except Exception as e:
            st.fail(k, "record", e)
            print(model, k, "RECORD ERROR", str(e)[:200], flush=True)
            return
        if st.spent > cap and not stop.is_set():
            stop.set()
            print(f"{model}: cap reached at ${st.spent:.2f}", flush=True)

    with cf.ThreadPoolExecutor(workers) as ex:
        for key in dict.fromkeys(r[2] for r in todo):
            if stop.is_set():
                break
            block = [r for r in todo if r[2] == key]
            warms = pick_warms(block, model)
            for w in warms:
                work(w)
            block = [r for r in block if not any(r is w for w in warms)]
            list(ex.map(work, block))
    print(f"{model}: finished sync, spent ${st.spent:.2f}, records {len(st.done)} of {len(rows)}", flush=True)


def collect_batch(model, cl, st, bid, ids, by_key, reg):
    while True:
        try:
            if cl.messages.batches.retrieve(bid).processing_status == "ended":
                break
        except Exception as e:
            print(model, bid, "POLL ERROR, retrying in 60s:", str(e)[:200], flush=True)
            time.sleep(60)
            continue
        time.sleep(20)
    results = None
    for _ in range(30):
        try:
            results = list(cl.messages.batches.results(bid))
            break
        except Exception as e:
            print(model, bid, "RESULTS ERROR, retrying in 60s:", str(e)[:200], flush=True)
            time.sleep(60)
    if results is None:
        print(model, bid, "results not collected; rerun to collect them", flush=True)
        return
    for res in results:
        k = ids.get(res.custom_id)
        r = by_key.get(k)
        if r is None or k in st.done:
            continue
        if res.result.type != "succeeded":
            st.fail(k, "batch_" + res.result.type, getattr(res.result, "error", None))
            print(model, k, "BATCH", res.result.type, flush=True)
            continue
        try:
            text, usage, meta = anthropic_record(res.result.message)
            if usable(st, model, k, text, meta):
                b = build(r)
                st.write(record(r, text, usage, meta, price(model, usage, batch=True), b["truth"], "batch",
                                prompt_sha(b["parts"])))
        except Exception as e:
            st.fail(k, "record", e)
            print(model, k, "RECORD ERROR", str(e)[:200], flush=True)
    with reg.open("a") as f:
        f.write(json.dumps(dict(collected=bid, ts=now())) + "\n")


def drain_batches(model, cl, st, by_key, reg):
    if not reg.exists():
        return
    subs, collected = [], set()
    for line in reg.open():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "collected" in e:
            collected.add(e["collected"])
        else:
            subs.append(e)
    for e in subs:
        if e["batch_id"] in collected or all(k in st.done for k in e["ids"].values()):
            continue
        print(f"{model}: collecting batch {e['batch_id']} submitted by an earlier run", flush=True)
        collect_batch(model, cl, st, e["batch_id"], e["ids"], by_key, reg)


def run_anthropic_batch(model, rows, cap):
    cl = client("anthropic")
    st = Store(model)
    reg = OUT / f"batches_{model}.log"
    by_key = {row_key(r): r for r in rows}
    drain_batches(model, cl, st, by_key, reg)
    todo = [r for r in ordered(rows, model) if row_key(r) not in st.done]
    print(f"{model}: {len(st.done)} done, {len(todo)} to run (batch), spent ${st.spent:.2f}, cap ${cap:.2f}", flush=True)
    for key in dict.fromkeys(r[2] for r in todo):
        if st.spent > cap:
            print(f"{model}: cap reached at ${st.spent:.2f}; skipping remaining settings", flush=True)
            break
        block = [r for r in todo if r[2] == key]
        warm = pick_warm(block)
        if warm is not None:
            k = row_key(warm)
            b = build(warm)
            try:
                text, usage, meta = anthropic_record(cl.messages.create(**anthropic_params(model, b["parts"])))
                if usable(st, model, k, text, meta):
                    st.write(record(warm, text, usage, meta, price(model, usage), b["truth"], "sync_warm",
                                    prompt_sha(b["parts"])))
                    block = [r for r in block if r is not warm]
            except Exception as e:
                st.fail(k, "error", f"{getattr(e, 'status_code', None)} {e}")
                print(model, k, "WARM ERROR; the row goes into the batch", str(e)[:200], flush=True)
        if not block:
            continue
        reqs, ids = [], {}
        for r in block:
            b = build(r)
            k = row_key(r)
            ids[cid(k)] = k
            reqs.append({"custom_id": cid(k), "params": anthropic_params(model, b["parts"])})
        try:
            batch = cl.messages.batches.create(requests=reqs)
        except Exception as e:
            st.fail(key, "batch_create", e)
            print(model, key, "BATCH CREATE ERROR; rerun to retry this setting", str(e)[:200], flush=True)
            continue
        with reg.open("a") as f:
            f.write(json.dumps(dict(batch_id=batch.id, setting=key, ids=ids, ts=now())) + "\n")
        print(f"{model}: {key} batch {batch.id} with {len(reqs)} requests", flush=True)
        collect_batch(model, cl, st, batch.id, ids, by_key, reg)
        print(f"{model}: {key} done, spent ${st.spent:.2f}", flush=True)
    print(f"{model}: finished batch, spent ${st.spent:.2f}, records {len(st.done)} of {len(rows)}", flush=True)


def file_hashes():
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FROZEN if (ROOT / f).exists()}


def dry_run(tier):
    rows = C.manifest(tier)
    n_chars, seen = 0, {}
    hashes = []
    for r in rows:
        b = build(r)
        n_chars += sum(len(p) for p in b["parts"])
        hashes.append(f"{row_key(r)}\t{prompt_sha(b['parts'])}")
        if r[1] == "agent":
            m, step, key, version, arm, threat, i = r
            prefix, middle, tail = b["parts"]
            seen.setdefault(("prefix", key, V.alt_present(version)), prefix)
            assert seen[("prefix", key, V.alt_present(version))] == prefix, ("prefix differs", key, version, arm)
            seen.setdefault(("middle", key, version), middle)
            assert seen[("middle", key, version)] == middle, ("middle differs", key, version, arm)
    keys = [row_key(r) for r in rows]
    assert len(set(keys)) == len(keys), "duplicate keys"
    assert len({cid(k) for k in keys}) == len(keys), "custom_id collision"
    for m in {r[0] for r in rows}:
        assert m in MODELS, m
    (OUT / f"prompt_hashes_{tier}.tsv").write_text("\n".join(hashes) + "\n")
    print(f"tier {tier}: {len(rows)} prompts rendered, {n_chars/1e6:.1f}M chars, {len(_EST)} estimate tables, "
          f"prefix/middle identity asserted, keys unique, prompt hashes in {OUT.name}/prompt_hashes_{tier}.tsv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dry", "smoke", "run"])
    ap.add_argument("--tier", default="A")
    ap.add_argument("--models", nargs="*")
    ap.add_argument("--cap-mult", type=float, default=1.5)
    ap.add_argument("--cap", action="append", default=[], metavar="MODEL=USD")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--primary", action="store_true")
    a = ap.parse_args()
    if a.mode == "dry":
        dry_run(a.tier)
        return
    rows = manifest(a.tier)
    if a.primary:
        rows = [r for r in rows if r[1] == "agent" and r[4] == "neutral" and r[5] is True and r[3] in ("silent", "implied", "chain")]
    models = a.models or sorted({r[0] for r in rows})
    unknown = [m for m in models if m not in MODELS or not any(r[0] == m for r in rows)]
    assert not unknown, ("models not in this tier's manifest", unknown)
    for r in rows:
        if r[0] in models and r[1] == "estimate":
            build(r)
    if a.mode == "smoke":
        for m in models:
            base = next(r for r in rows if r[0] == m and r[1] == "agent" and r[3] == "silent")
            for i in (98, 99):
                r = (base[0], base[1], base[2], base[3], base[4], base[5], i)
                b = build(r)
                try:
                    text, usage, meta = call_sync(m, b["parts"])
                except Exception as e:
                    print(json.dumps(dict(model=m, call=i, error=str(e)[:300])), flush=True)
                    break
                print(json.dumps(dict(model=m, call=i, usage=usage, cost=round(price(m, usage), 4), chars=len(text),
                                      **meta)), flush=True)
                print("   tail:", text[-160:].replace("\n", " | "), flush=True)
                with (OUT / "smoke.jsonl").open("a") as f:
                    f.write(json.dumps(record(r, text, usage, meta, price(m, usage), None, "smoke",
                                              prompt_sha(b["parts"]))) + "\n")
        return
    overrides = {}
    for x in a.cap:
        m, v = x.split("=")
        assert m in MODELS, m
        overrides[m] = float(v)
    outs = C.measured_out()
    caps = {}
    for m in models:
        mode = "batch" if MODELS[m][0] == "anthropic" or "flex" in json.dumps(MODELS[m][2]) else "sync"
        if m in overrides:
            caps[m] = overrides[m]
        else:
            assert m not in ADDED, ("set --cap explicitly for added model", m)
            caps[m] = max(1.0, a.cap_mult * C.cost(m, mode, outs, tier=a.tier)[0])
    with (OUT / "run_log.log").open("a") as f:
        f.write(json.dumps(dict(ts=now(), argv=sys.argv, tier=a.tier, models=models, caps=caps,
                                params={m: logged_params(m) for m in models}, hashes=file_hashes(),
                                calls={m: sum(1 for r in rows if r[0] == m) for m in models})) + "\n")
    threads = []
    for m in models:
        mine = [r for r in rows if r[0] == m]
        if MODELS[m][0] == "anthropic" and ANTHROPIC_BATCH:
            t = threading.Thread(target=run_anthropic_batch, args=(m, mine, caps[m]))
        else:
            t = threading.Thread(target=run_sync, args=(m, mine, caps[m], a.workers))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    print("ALLDONE", flush=True)


if __name__ == "__main__":
    main()
