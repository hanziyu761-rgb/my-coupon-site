#!/usr/bin/env python3
"""
统一大模型调用层 —— 支持国产大模型（人民币充值），一处配置全局生效。

所有国产模型都用 OpenAI 兼容接口，切换只需改 LLM_PROVIDER 和对应的 key。

环境变量:
  LLM_PROVIDER   选择服务商：deepseek（默认）| qwen | glm | moonshot | doubao | anthropic
  各家的 key（按你选的那家设一个即可）:
    DEEPSEEK_API_KEY      （DeepSeek，推荐，最便宜）
    DASHSCOPE_API_KEY     （通义千问 Qwen，阿里）
    ZHIPU_API_KEY         （智谱 GLM）
    MOONSHOT_API_KEY      （Kimi）
    ARK_API_KEY + DOUBAO_MODEL  （豆包，model 填你创建的推理接入点ID）
    ANTHROPIC_API_KEY     （Claude，需美元卡）
  可选覆盖:
    LLM_MODEL      自定义模型名
    LLM_BASE_URL   自定义接口地址

注册入口（都能支付宝/微信充值）:
  DeepSeek : https://platform.deepseek.com
  通义千问  : https://bailian.console.aliyun.com
  智谱GLM  : https://open.bigmodel.cn
  Kimi     : https://platform.moonshot.cn
  豆包      : https://console.volcengine.com/ark
"""

import os

PROVIDERS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "key_env": "DEEPSEEK_API_KEY",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "key_env": "DASHSCOPE_API_KEY",
    },
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-plus",
        "key_env": "ZHIPU_API_KEY",
    },
    "moonshot": {
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-32k",
        "key_env": "MOONSHOT_API_KEY",
    },
    "doubao": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": os.environ.get("DOUBAO_MODEL", ""),  # 豆包需填推理接入点ID
        "key_env": "ARK_API_KEY",
    },
    "anthropic": {  # 需要美元卡，国内通常用不了
        "base_url": None,
        "model": "claude-sonnet-4-6",
        "key_env": "ANTHROPIC_API_KEY",
    },
}


def _ensure(pkg):
    import importlib
    import subprocess
    import sys
    try:
        importlib.import_module(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])


def current_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "deepseek").lower()


def has_llm() -> bool:
    """是否已配置可用的大模型 key"""
    prov = current_provider()
    cfg = PROVIDERS.get(prov)
    if not cfg:
        return False
    return bool(os.environ.get(cfg["key_env"]))


def chat(prompt: str, system: str | None = None,
         max_tokens: int = 4096, temperature: float = 0.7) -> str:
    """统一对话接口，返回模型输出文本。"""
    prov = current_provider()
    cfg = PROVIDERS.get(prov)
    if not cfg:
        raise ValueError(f"未知的 LLM_PROVIDER: {prov}，可选: {list(PROVIDERS)}")

    api_key = os.environ.get(cfg["key_env"])
    if not api_key:
        raise EnvironmentError(
            f"未设置 {cfg['key_env']}。请注册 {prov} 并充值后导出该环境变量。\n"
            f"或改用其他服务商：export LLM_PROVIDER=deepseek"
        )

    model = os.environ.get("LLM_MODEL", cfg["model"])

    # ── Anthropic（独立 SDK）──────────────────────────────
    if prov == "anthropic":
        _ensure("anthropic")
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        kwargs = {"model": model, "max_tokens": max_tokens,
                  "messages": [{"role": "user", "content": prompt}]}
        if system:
            kwargs["system"] = system
        msg = client.messages.create(**kwargs)
        return msg.content[0].text

    # ── 国产模型（OpenAI 兼容）────────────────────────────
    _ensure("openai")
    from openai import OpenAI
    base_url = os.environ.get("LLM_BASE_URL", cfg["base_url"])
    client = OpenAI(api_key=api_key, base_url=base_url)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content


if __name__ == "__main__":
    # 自检：python llm.py
    print(f"当前服务商: {current_provider()}  已配置key: {has_llm()}")
    if has_llm():
        print(chat("用一句话夸一下高阳的纺织产业。"))
