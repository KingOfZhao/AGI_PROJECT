## Summary

Adds a comprehensive Chinese deployment guide for OpenClaw, targeting developers in China who need to:
1. Install OpenClaw behind the Great Firewall (npm mirror, network optimization)
2. Connect domestic LLM providers (Zhipu GLM, Qwen, Doubao) via Anthropic-compatible API
3. Set up WeChat channel using the official `@tencent-weixin/openclaw-weixin` plugin

## Motivation

OpenClaw has 341K+ GitHub stars and 8.7M monthly npm downloads. China is the largest potential growth market, but existing Chinese documentation is scattered across Zhihu, CSDN, and GitHub issues. This guide consolidates everything into one official source.

All WeChat-related issues are verified against real GitHub issues (#57619, #52153, #52099) and the actual plugin source code at `~/.openclaw/extensions/openclaw-weixin/`.

## Related

- #3460 (Internationalization & Localization Support, ★115)
- #52099 (docs: add WeChat channel)
- #52153 (WeChat reply-only limitation)
- #57619 (Subagent/Cron messages not delivered to WeChat)

## Notes

- All issue numbers and configuration commands verified against OpenClaw v2026.3.28 + openclaw-weixin 2.0.x
- WeChat plugin is officially maintained by Tencent (`@tencent-weixin/openclaw-weixin`)
- The guide honestly documents the current reply-only limitation instead of hiding it
