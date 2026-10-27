"""AI provider adapters: each provider gets the request shape it expects and its answer is read back.
Run: python tests/test_ai_providers.py"""
import json, os, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

tmp = tempfile.mkdtemp()
os.environ.update({"NOTERA_DATA": os.path.join(tmp, "n"), "NOTERA_HOME": os.path.join(tmp, "h")})
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app  # noqa: E402

FAILS, SEEN = [], []


def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        SEEN.append((self.path, {k.lower(): v for k, v in self.headers.items()}, body))
        if "generateContent" in self.path:
            out = {"candidates": [{"content": {"parts": [{"text": "gemini says hi"}]}}]}
        elif self.path.endswith("/chat/completions"):
            out = {"choices": [{"message": {"content": "chat says hi"}}]}
        else:
            out = {"content": [{"type": "text", "text": "claude says hi"}]}
        raw = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


srv = HTTPServer(("127.0.0.1", 5391), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = "http://127.0.0.1:5391"
c = app.app.test_client()

cfg = c.get("/api/ai/config").get_json()
ids = [p["id"] for p in cfg["providers"]]
ok({"anthropic", "openai", "gemini", "openrouter", "custom"} <= set(ids), "providers offered: %s" % ids)
ok(all({m["tier"] for m in p["models"]} <= {"best", "balanced", "cheapest"} for p in cfg["providers"]), "models are grouped into best / balanced / cheapest")
ok(any(m["tier"] == "cheapest" for p in cfg["providers"] if p["id"] == "openai" for m in p["models"]), "a cheapest model is offered")

app.AI_PROVIDERS["openai"]["base"] = base + "/v1"
app.AI_PROVIDERS["gemini"]["base"] = base + "/v1beta"
app.AI_PROVIDERS["groq"]["base"] = base + "/groq"
for prov, key, model, want in [("openai", "sk-o", "gpt-5-nano", "chat says hi"), ("gemini", "g-key", "gemini-2.5-flash-lite", "gemini says hi"), ("groq", "gq", "llama-3.1-8b-instant", "chat says hi")]:
    r = c.post("/api/ai/config", json={"provider": prov, "key": key, "model": model}).get_json()
    ok(r["provider"] == prov and r["configured"] and r["model"] == model, prov + " saved with its own key and model")
    SEEN.clear()
    r = c.post("/api/ai", json={"task": "explain", "text": "x"}).get_json()
    path, hdr, body = SEEN[0]
    ok(r.get("text") == want, prov + " answer is read back: %s" % r)
    if prov == "gemini":
        ok(hdr.get("x-goog-api-key") == "g-key" and "key=" not in path and body["systemInstruction"] and body["contents"][0]["role"] == "user", "gemini: key in a header, system prompt separate")
    else:
        ok(hdr.get("authorization") == "Bearer " + key and body["messages"][0]["role"] == "system" and body["model"] == model, prov + ": bearer key and model sent")
        ok(("max_completion_tokens" in body) == (prov == "openai"), prov + ": correct token-limit field")
c.post("/api/ai/config", json={"provider": "anthropic"})
ok(c.get("/api/ai/config").get_json()["configured"] is False, "each provider keeps its own key; anthropic still has none")
c.post("/api/ai/config", json={"provider": "custom", "key": "k", "model": "m", "base": base + "/custom"})
SEEN.clear()
r = c.post("/api/ai", json={"task": "explain", "text": "x"}).get_json()
ok(r.get("text") == "chat says hi" and SEEN[0][0] == "/custom/chat/completions", "custom OpenAI-compatible address works")
raw = Path(tmp, "h", "ai_config.json").read_text(encoding="utf-8") if Path(tmp, "h", "ai_config.json").exists() else ""
ok("sk-o" not in json.dumps(c.get("/api/ai/config").get_json()), "keys are never sent back to the page")
srv.shutdown()
if FAILS:
    print("\n%d check(s) failed" % len(FAILS))
    sys.exit(1)
print("\nall checks passed")
