import os


def anthropic_agent(model, max_tokens=16000, **kw):
    import anthropic
    client = anthropic.Anthropic()

    def call(prompt):
        r = client.messages.create(model=model, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}], **kw)
        return "".join(b.text for b in r.content if b.type == "text")
    return call


def openai_agent(model, base_url=None, api_key=None, **kw):
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key) if base_url else OpenAI()

    def call(prompt):
        r = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], **kw)
        return r.choices[0].message.content or ""
    return call


def from_name(name):
    provider, _, model = name.partition(":")
    if provider == "anthropic":
        return anthropic_agent(model)
    if provider == "openai":
        return openai_agent(model)
    if provider == "openrouter":
        return openai_agent(model, base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
    raise ValueError("model must look like anthropic:<id>, openai:<id> or openrouter:<id>")
