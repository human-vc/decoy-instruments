import json

INTRO = "You are an empirical research assistant. The principal investigator is working on this study:\n\n"
CODEBOOK = "\n\nThe dataset is documented below.\n\nCodebook:\n"
DOCS = "\n\nProgram and data documentation:\n"
PI = "\n\nThe principal investigator writes:"

TOOLS = [
    dict(name="list_files", description="List the files in the project folder.", params={}),
    dict(name="read_file", description="Read lines from a file in the project folder. Long files are returned in chunks; "
         "use start_line to continue.", params={"path": {"type": "string"}, "start_line": {"type": "integer"}}),
]


def split(prompt):
    study = prompt[len(INTRO):prompt.index(CODEBOOK)]
    codebook = prompt[prompt.index(CODEBOOK) + len(CODEBOOK):prompt.index(DOCS)]
    docs = prompt[prompt.index(DOCS) + len(DOCS):prompt.index(PI)]
    task = prompt[prompt.index(PI) + 2:]
    files = {"codebook.txt": codebook.strip() + "\n", "documentation.txt": docs.strip() + "\n"}
    message = (INTRO + study + "\n\nThe dataset's codebook and its program and data documentation are in the project folder. "
               "Use the tools to read them before you plan.\n\n" + task)
    return message, files


class Folder:
    def __init__(self, files, chunk=150):
        self.files, self.chunk, self.opened = files, chunk, []

    def __call__(self, name, args):
        if name == "list_files":
            return "\n".join(f"{k} ({v.count(chr(10))} lines)" for k, v in self.files.items())
        path = str(args.get("path", "")).split("/")[-1]
        if path not in self.files:
            return f"No such file: {path}"
        lines = self.files[path].splitlines()
        start = max(int(args.get("start_line") or 1), 1)
        end = min(start + self.chunk - 1, len(lines))
        self.opened.append((path, start, end))
        more = f"\n[lines {start}-{end} of {len(lines)}; call again with start_line={end + 1} for more]" if end < len(lines) else \
            f"\n[lines {start}-{end} of {len(lines)}; end of file]"
        return "\n".join(lines[start - 1:end]) + more


def saw(case, version, folder, which):
    lines = split(case["prompts"][version])[1]["codebook.txt"].splitlines()
    ln = next(i + 1 for i, l in enumerate(lines) if l.startswith(case[which] + ":"))
    return any(p == "codebook.txt" and a <= ln <= b for p, a, b in folder.opened)


def anthropic_loop(model, max_turns=30, max_tokens=16000, **kw):
    import anthropic
    client = anthropic.Anthropic()
    tools = [dict(name=t["name"], description=t["description"],
                  input_schema={"type": "object", "properties": t["params"]}) for t in TOOLS]

    def cached(msgs):
        out = msgs[:-1]
        last = msgs[-1]
        blocks = [{"type": "text", "text": last["content"]}] if isinstance(last["content"], str) else list(last["content"])
        blocks[-1] = {**blocks[-1], "cache_control": {"type": "ephemeral"}}
        return out + [{"role": last["role"], "content": blocks}]

    def run(message, folder):
        msgs, usage = [{"role": "user", "content": message}], dict(inp=0, out=0, cache_write=0, cache_read=0)
        for _ in range(max_turns):
            r = client.messages.create(model=model, max_tokens=max_tokens, tools=tools, messages=cached(msgs), **kw)
            usage["inp"] += r.usage.input_tokens
            usage["out"] += r.usage.output_tokens
            usage["cache_write"] += r.usage.cache_creation_input_tokens or 0
            usage["cache_read"] += r.usage.cache_read_input_tokens or 0
            msgs.append({"role": "assistant", "content": r.content})
            calls = [b for b in r.content if b.type == "tool_use"]
            if not calls:
                return "".join(b.text for b in r.content if b.type == "text"), usage
            msgs.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": b.id, "content": folder(b.name, b.input)} for b in calls]})
        return "", usage
    return run


def openai_loop(model, base_url=None, api_key=None, max_turns=30, **kw):
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key) if base_url else OpenAI()
    tools = [dict(type="function", function=dict(name=t["name"], description=t["description"],
                                                 parameters={"type": "object", "properties": t["params"]})) for t in TOOLS]

    def run(message, folder):
        msgs, usage = [{"role": "user", "content": message}], dict(inp=0, out=0)
        for _ in range(max_turns):
            r = client.chat.completions.create(model=model, messages=msgs, tools=tools, **kw)
            if r.usage:
                usage["inp"] += r.usage.prompt_tokens
                usage["out"] += r.usage.completion_tokens
            m = r.choices[0].message
            msgs.append(m.model_dump(exclude_none=True))
            if not m.tool_calls:
                return m.content or "", usage
            for c in m.tool_calls:
                try:
                    args = json.loads(c.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                msgs.append({"role": "tool", "tool_call_id": c.id, "content": folder(c.function.name, args)})
        return "", usage
    return run


def loop_from_name(name):
    import os
    provider, _, model = name.partition(":")
    if provider == "anthropic":
        return anthropic_loop(model)
    if provider == "openai":
        return openai_loop(model)
    if provider == "openrouter":
        return openai_loop(model, base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
    raise ValueError("model must look like anthropic:<id>, openai:<id> or openrouter:<id>")
