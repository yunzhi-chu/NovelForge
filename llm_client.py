"""多模型客户端：本地 LM Studio + DeepSeek + Claude"""
import subprocess, re, os, json
from openai import OpenAI

LMS = os.path.expanduser("~/.lmstudio/bin/lms.exe")

class LLMClient:
    def __init__(self):
        self.local_model = "google/gemma-4-26b-a4b"
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.claude_key = os.getenv("ANTHROPIC_API_KEY", "")

    def _call_lms(self, prompt, temperature=0.78, max_tokens=6000):
        """通过 lms.exe CLI 调用本地模型（避开 HTTP API 认证问题）"""
        r = subprocess.run(
            [LMS, "chat", self.local_model, "--prompt", prompt],
            capture_output=True, timeout=300
        )
        text = r.stdout.decode("utf-8", errors="replace")
        # 清理终端转义和 think 标签
        text = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]', '', text)
        text = re.sub(r'\x1b\[[0-9;]*[mK]', '', text)
        text = re.sub(r'\r', '', text)
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        return text.strip()

    def _call_openai(self, api_key, base_url, model, prompt, temperature, max_tokens):
        client = OpenAI(api_key=api_key, base_url=base_url)
        r = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}],
            temperature=temperature, max_tokens=max_tokens
        )
        return r.choices[0].message.content

    def _call_claude(self, prompt, temperature, max_tokens):
        from anthropic import Anthropic
        c = Anthropic(api_key=self.claude_key)
        r = c.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        return r.content[0].text

    def generate(self, prompt, model="local", temperature=0.78, max_tokens=6000):
        if model in ("deepseek",) and not self.deepseek_key:
            raise ValueError("DEEPSEEK_API_KEY 未设置")
        if model == "claude" and not self.claude_key:
            raise ValueError("ANTHROPIC_API_KEY 未设置")

        if model == "local":
            return self._call_lms(prompt, temperature, max_tokens)
        elif model == "deepseek":
            return self._call_openai(
                self.deepseek_key, "https://api.deepseek.com",
                "deepseek-chat", prompt, temperature, max_tokens
            )
        elif model == "claude":
            return self._call_claude(prompt, temperature, max_tokens)
        else:
            return self._call_lms(prompt, temperature, max_tokens)
