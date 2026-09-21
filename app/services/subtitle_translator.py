"""LLM-powered SRT subtitle translation."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from math import ceil
from typing import Any, Callable

from loguru import logger

from app.config import config
from app.config.defaults import resolve_text_model_name
from app.services.llm.migration_adapter import _run_async_safely
from app.services.llm.unified_service import UnifiedLLMService
from app.services.subtitle_corrector import (
    _ensure_llm_providers_registered,
    _extract_json_text,
    parse_srt_blocks,
)
from app.services.subtitle_text import read_subtitle_text
from app.utils import utils


class SubtitleTranslationError(RuntimeError):
    """Raised when subtitle translation cannot produce a valid SRT."""


# ============================================================================
# 🎯 FIXED CONFIG — Loop + Language Leak ကာကွယ်ရန်
# ============================================================================
DEFAULT_BATCH_SIZE = 12            # 20 → 12 (Balance — Loop နည်း + Context ကောင်း)
DEFAULT_MAX_WORKERS = 3
DEFAULT_MAX_REPAIR_ATTEMPTS = 3
DEFAULT_MAX_TOKENS = 4096         # Base minimum — Burmese translation ရှည်
MAX_TRANSLATION_LENGTH = 500      # တစ်ခုချင်း စာသား အများဆုံး


TranslationProgressCallback = Callable[[int, int, str], None]


def _get_positive_int(value, default: int, *, minimum: int = 1, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _resolve_batch_size(batch_size: int | None = None) -> int:
    if batch_size is None:
        batch_size = config.app.get("subtitle_translate_batch_size", DEFAULT_BATCH_SIZE)
    return _get_positive_int(batch_size, DEFAULT_BATCH_SIZE, minimum=1, maximum=100)


def _resolve_max_workers(max_workers: int | None = None) -> int:
    if max_workers is None:
        max_workers = config.app.get("subtitle_translate_max_workers", DEFAULT_MAX_WORKERS)
    return _get_positive_int(max_workers, DEFAULT_MAX_WORKERS, minimum=1, maximum=8)


def _resolve_max_tokens(batch_size: int) -> int:
    """Batch Size အလိုက် max_tokens တွက်

    Burmese/Chinese translation — Input ထက် 2-3x ရှည်နိုင်
    → 500 tokens/block + 2000 base — Safe
    """
    estimated = batch_size * 500 + 2000
    return min(8192, max(4096, estimated))


def _split_blocks(blocks, batch_size: int):
    return [blocks[index:index + batch_size] for index in range(0, len(blocks), batch_size)]


# ============================================================================
# 🛡 VALIDATION HELPERS
# ============================================================================
def _has_broken_characters(text: str) -> bool:
    """ပျက်နေတဲ့ Unicode Character ရှိ/မရှိ စစ်"""
    if not text:
        return False
    if "\ufffd" in text:
        return True
    return False


def _detect_wrong_language(text: str, target_language: str = "") -> str:
    """မှားနေတဲ့ ဘာသာစကား ရှာ/မရှာ စစ်"""
    if not text or len(text) < 3:
        return ""

    total_chars = len(text.replace(" ", "").replace("\n", ""))
    if total_chars < 3:
        return ""

    myanmar_chars = sum(1 for c in text if '\u1000' <= c <= '\u109f')
    english_chars = sum(1 for c in text if c.isascii() and c.isalpha())
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

    # --- Target = Burmese ---
    if "မြန်မာ" in target_language or "MYANMAR" in target_language.upper() or "BURMESE" in target_language.upper():
        if myanmar_chars == 0:
            if english_chars / total_chars >= 0.6:
                return "English"
            if chinese_chars / total_chars >= 0.6:
                return "Chinese"
            if english_chars + chinese_chars >= 3:
                return "Unknown"
        if myanmar_chars / total_chars < 0.1:
            if english_chars >= 10:
                return "English"
            if chinese_chars >= 5:
                return "Chinese"
        return ""

    # --- Target = English ---
    if "ENGLISH" in target_language.upper():
        if chinese_chars / total_chars >= 0.5:
            return "Chinese"
        if myanmar_chars / total_chars >= 0.5:
            return "Burmese"
        return ""

    # --- Target = Chinese ---
    if "中文" in target_language or "CHINESE" in target_language.upper():
        if myanmar_chars / total_chars >= 0.5:
            return "Burmese"
        if english_chars / total_chars >= 0.6:
            return "English"
        return ""

    # --- Default ---
    if "ENGLISH" not in target_language.upper():
        if english_chars / total_chars >= 0.7:
            return "English"
    if "中文" not in target_language and "CHINESE" not in target_language.upper():
        if chinese_chars / total_chars >= 0.7:
            return "Chinese"

    return ""


def _has_excessive_repetition(text: str) -> bool:
    """စာသား ထပ်ခါတလဲလဲ ဖြစ်နေသလား စစ်"""
    if not text or len(text) < 40:
        return False

    sample = text[:20]
    if sample and text.count(sample) >= 5:
        return True

    half = len(text) // 2
    first_half = text[:half]
    second_half = text[half:]
    if len(first_half) >= 30 and first_half[:30] in second_half:
        return True

    words = text.split()
    if len(words) >= 30:
        first_10 = " ".join(words[:10])
        if first_10 and text.count(first_10) >= 4:
            return True

    return False


def _build_translation_prompt(blocks, target_language: str) -> str:
    payload = {str(block.order): block.text for block in blocks}
    return f"""
请将以下 SRT 字幕文本翻译为{target_language}。

翻译要求：
1. ⚠️ 所有字幕必须翻译为{target_language}。不能保留原文（中文或英文），必须真实翻译。
2. 结合全部字幕内容理解语境，输出自然、准确、适合字幕阅读的{target_language}。
3. 只翻译字幕文本，不要修改时间轴、序号、条目数量或条目顺序。
4. 保留必要的说话人标记、专有名词、品牌名、代码、数字和换行；除非目标语言中有约定译名。
5. 不要添加解释、注释、剧情信息或 Markdown。
6. 空字幕文本保持为空字符串。
7. ⚠️ 重要：每条字幕翻译长度不超过 500 字符。不要重复同一句话。不要输出循环内容。
8. ⚠️ 重要：每条翻译必须唯一且简洁。如果无法翻译，返回原文本。
9. ⚠️ 不要输出破损字符。不要输出乱码。

只输出严格 JSON 对象，不要输出 Markdown 或解释文字。必须保留所有输入 key，格式必须为：
{{"1":"翻译后的字幕文本","2":"翻译后的字幕文本"}}

⚠️ 警告：
- 如果检测到任何重复或循环模式，请立即停止并只输出已翻译的合法内容。
- 所有翻译必须为{target_language}，不能保留中文或英文原文。

待翻译字幕条目：
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()


def _validate_translation_text(text: str, item_id: int, target_language: str) -> str:
    """တစ်ခုချင်း Translation ကို — Validate — ပြဿနာ ရှိရင် — Skip အတွက် — "" ပြန်"""
    # --- Length Check ---
    if len(text) > MAX_TRANSLATION_LENGTH:
        logger.warning(f"字幕 {item_id} 翻译过长 ({len(text)} 字符)，已截断")
        text = text[:MAX_TRANSLATION_LENGTH]

    # --- Repetition Check ---
    if _has_excessive_repetition(text):
        logger.warning(f"字幕 {item_id} 检测到重复模式")
        return ""

    # --- Broken Character Check ---
    if _has_broken_characters(text):
        logger.warning(f"字幕 {item_id} 检测到破损字符")
        return ""

    # --- Language Leak Check ---
    lang_leak = _detect_wrong_language(text, target_language)
    if lang_leak:
        logger.warning(f"字幕 {item_id} 语言错误: {lang_leak}")
        return ""

    return text


def _parse_translations_partial(
    raw_output: str,
    expected_ids: set[int],
    target_language: str = "",
) -> tuple[dict[int, str], list[int]]:
    """Partial Parsing — ရှိတဲ့ Item တွေ ပြန် — Missing တွေ စာရင်း

    Returns:
        (translations, missing_ids)
    """
    try:
        json_text = _extract_json_text(raw_output)
        data: Any = json.loads(json_text)
    except Exception:
        return {}, sorted(expected_ids)

    if isinstance(data, dict) and "items" in data:
        items = data["items"]
    elif isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = [{"id": key, "text": value} for key, value in data.items()]
    else:
        return {}, sorted(expected_ids)

    if not isinstance(items, list):
        return {}, sorted(expected_ids)

    translations: dict[int, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            item_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        if item_id not in expected_ids:
            continue

        text = str(item.get("text") or "").strip()
        validated = _validate_translation_text(text, item_id, target_language)

        # "" ဆိုရင် — Validate မအောင် — ဒါပေမယ့် empty text ဖြစ်ရင်လည်း — Accept
        if validated or text == "":
            translations[item_id] = validated if validated else text

    missing_ids = sorted(expected_ids - set(translations.keys()))
    return translations, missing_ids


def _parse_translations(raw_output: str, expected_ids: set[int], target_language: str = "") -> dict[int, str]:
    """Full Parsing — Missing ရှိရင် — Error (Partial Version ကို သုံး)"""
    translations, missing_ids = _parse_translations_partial(raw_output, expected_ids, target_language)
    if missing_ids:
        raise SubtitleTranslationError(f"LLM 字幕翻译结果缺少字幕条目: {missing_ids[:10]}")
    return translations


def _build_repair_prompt(
    *,
    blocks,
    target_language: str,
    previous_output: str,
    error_message: str,
) -> str:
    payload = {str(block.order): block.text for block in blocks}
    return f"""
你上一轮返回的字幕翻译 JSON 无法通过校验，请修复后重新输出。

目标语言：{target_language}

校验错误：
{error_message}

⚠️ 重要修正要求：
1. ⚠️ 必须翻译为{target_language}，不能保留原文或翻译为其他语言。
2. ⚠️ 如果原字幕是中文，必须翻译为{target_language}，不能保留中文原文。
3. ⚠️ 如果原字幕是英文，必须翻译为{target_language}，不能保留英文原文。
4. ⚠️ 不要重复同一句话。不要输出循环内容。
5. ⚠️ 每条字幕翻译长度不超过 500 字符。
6. ⚠️ 不要输出破损字符。不要输出乱码。

⚠️ 上一轮你漏掉了以下条目，必须全部包含：
{error_message}

原始字幕条目：
{json.dumps(payload, ensure_ascii=False, indent=2)}

上一轮输出（已被拒绝 — 不要照抄）：
{previous_output[:1000]}

请只输出严格 JSON 对象，必须包含并且只包含原始字幕条目的所有 key。
所有 {target_language} 翻译必须真实翻译，不能保留中文或英文原文。
""".strip()


def _translate_chunk(
    *,
    chunk,
    chunk_index: int,
    total_chunks: int,
    target_language: str,
    provider: str,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    max_repair_attempts: int,
) -> dict[int, str]:
    """Batch တစ်ခုကို Translate — Partial Retry Logic ဖြင့်

    Missing Item ရှိရင် — အဲဒီ Item တွေပဲ — ပြန် စမ်း
    """
    start_order = chunk[0].order
    end_order = chunk[-1].order
    expected_ids = {block.order for block in chunk}
    max_tokens = _resolve_max_tokens(len(chunk))

    logger.info(
        f"字幕翻译批次 {chunk_index}/{total_chunks} 开始: "
        f"条目 {start_order}-{end_order}, 共 {len(chunk)} 条, "
        f"max_tokens={max_tokens}"
    )

    translations: dict[int, str] = {}
    remaining_blocks = list(chunk)
    last_output = ""
    last_error = ""

    for attempt in range(1, max_repair_attempts + 1):
        if not remaining_blocks:
            break

        # --- Prompt ဖန်တီး ---
        if attempt == 1:
            prompt = _build_translation_prompt(remaining_blocks, target_language)
        else:
            prompt = _build_repair_prompt(
                blocks=remaining_blocks,
                target_language=target_language,
                previous_output=last_output,
                error_message=last_error,
            )

        # --- Retry အတွက် — max_tokens ကို — ပိုတိုး ---
        attempt_max_tokens = max_tokens
        if attempt > 1:
            attempt_max_tokens = min(8192, max_tokens + 2000)

        try:
            raw_output = _run_async_safely(
                UnifiedLLMService.generate_text,
                prompt=prompt,
                system_prompt=(
                    f"你是一位专业字幕翻译员，擅长在严格保留 JSON key 一一对应的前提下，"
                    f"将字幕准确翻译为{target_language}。"
                    f"⚠️ 所有翻译必须为{target_language}，不能保留中文或英文原文。"
                    f"⚠️ 绝对不要重复同一句话，绝对不要输出循环内容。"
                    f"每条字幕翻译必须唯一且简洁（不超过 500 字符）。"
                    f"不要输出破损字符。"
                ),
                provider=provider,
                temperature=temperature,
                max_tokens=attempt_max_tokens,
                response_format="json",
                api_key=api_key,
                api_base=base_url,
                model=model_name,
                thinking_level="off",
            )
            last_output = str(raw_output or "")

            # --- Partial Parse ---
            new_translations, missing_ids = _parse_translations_partial(
                last_output,
                {b.order for b in remaining_blocks},
                target_language,
            )

            if new_translations:
                translations.update(new_translations)
                logger.info(
                    f"字幕翻译批次 {chunk_index}/{total_chunks} "
                    f"第 {attempt} 次: +{len(new_translations)} 条, "
                    f"剩余 {len(missing_ids)} 条"
                )

            if not missing_ids:
                logger.info(
                    f"字幕翻译批次 {chunk_index}/{total_chunks} 完成: "
                    f"条目 {start_order}-{end_order}"
                )
                return translations

            # --- Missing Item တွေပဲ — ထပ် စမ်း ---
            remaining_blocks = [b for b in remaining_blocks if b.order in missing_ids]
            last_error = f"缺少以下条目，必须包含: {missing_ids}"

            logger.warning(
                f"字幕翻译批次 {chunk_index}/{total_chunks} "
                f"第 {attempt} 次: 缺少 {len(missing_ids)} 条 — {missing_ids[:10]}"
            )

            # --- Missing များရင် — Batch ခွဲ (Loop ကာကွယ်) ---
            if len(remaining_blocks) > 6 and attempt >= 2:
                mid = len(remaining_blocks) // 2
                remaining_blocks = remaining_blocks[:mid]
                logger.warning(
                    f"字幕翻译批次 {chunk_index}/{total_chunks} "
                    f"Batch ခွဲ — {len(remaining_blocks)} 条 ပဲ ထား"
                )

        except SubtitleTranslationError as exc:
            last_error = str(exc)
            logger.warning(
                f"字幕翻译批次 {chunk_index}/{total_chunks} "
                f"解析失败 (尝试 {attempt}): {exc}"
            )
            continue
        except Exception as exc:
            last_error = f"API 错误: {exc}"
            logger.warning(
                f"字幕翻译批次 {chunk_index}/{total_chunks} "
                f"API 异常 (尝试 {attempt}): {exc}"
            )
            continue

    # --- 🛡 Final Fallback — Missing Items → Original Text ---
    missing_ids = sorted(expected_ids - set(translations.keys()))
    if missing_ids:
        logger.warning(
            f"字幕翻译批次 {chunk_index}/{total_chunks} "
            f"最后使用原文回退: {missing_ids[:10]}"
        )
        # Original Text — Fallback (Failure တော့ မဖြစ်)
        for block in chunk:
            if block.order in missing_ids:
                translations[block.order] = block.text

    logger.info(
        f"字幕翻译批次 {chunk_index}/{total_chunks} 完成: "
        f"条目 {start_order}-{end_order} "
        f"({len(missing_ids)} 条使用原文)"
    )
    return translations


def _call_progress_callback(
    progress_callback: TranslationProgressCallback | None,
    completed: int,
    total: int,
    message: str,
) -> None:
    if not progress_callback:
        return
    try:
        progress_callback(completed, total, message)
    except Exception as exc:
        logger.debug(f"字幕翻译进度回调失败: {exc}")


def _render_translated_srt(blocks, translations: dict[int, str]) -> str:
    rendered_blocks = []
    for block in blocks:
        translated_text = translations.get(block.order, "")
        rendered_blocks.append(f"{block.index_line}\n{block.time_line}\n{translated_text}")
    return "\n\n".join(rendered_blocks).rstrip() + "\n"


def translate_srt_content(
    srt_content: str,
    *,
    target_language: str = "中文",
    provider: str = "",
    api_key: str = "",
    base_url: str = "",
    model_name: str = "",
    temperature: float = 0.2,
    batch_size: int | None = None,
    max_workers: int | None = None,
    progress_callback: TranslationProgressCallback | None = None,
) -> str:
    target_language = str(target_language or "").strip() or "中文"
    blocks = parse_srt_blocks(srt_content)
    _ensure_llm_providers_registered()
    resolved_model_name = str(
        model_name or resolve_text_model_name(config.app, provider, prefer_fast=True)
    ).strip()

    resolved_batch_size = _resolve_batch_size(batch_size)
    chunks = _split_blocks(blocks, resolved_batch_size)
    resolved_max_workers = min(_resolve_max_workers(max_workers), len(chunks))
    total_chunks = len(chunks)
    total_blocks = len(blocks)

    logger.info(
        f"开始批量翻译字幕: 共 {total_blocks} 条, {total_chunks} 批, "
        f"每批最多 {resolved_batch_size} 条, 并发 {resolved_max_workers}, "
        f"目标语言: {target_language}, 模型: {resolved_model_name}"
    )

    translations: dict[int, str] = {}
    completed_blocks = 0
    _call_progress_callback(
        progress_callback,
        0,
        total_blocks,
        f"开始翻译字幕，共 {total_blocks} 条，{total_chunks} 批",
    )

    if total_chunks == 1:
        translations.update(
            _translate_chunk(
                chunk=chunks[0],
                chunk_index=1,
                total_chunks=total_chunks,
                target_language=target_language,
                provider=provider,
                api_key=api_key,
                base_url=base_url,
                model_name=resolved_model_name,
                temperature=temperature,
                max_repair_attempts=DEFAULT_MAX_REPAIR_ATTEMPTS,
            )
        )
        completed_blocks = total_blocks
        _call_progress_callback(progress_callback, completed_blocks, total_blocks, "字幕翻译完成")
    else:
        with ThreadPoolExecutor(max_workers=resolved_max_workers) as executor:
            future_to_meta = {}
            for index, chunk in enumerate(chunks, start=1):
                future = executor.submit(
                    _translate_chunk,
                    chunk=chunk,
                    chunk_index=index,
                    total_chunks=total_chunks,
                    target_language=target_language,
                    provider=provider,
                    api_key=api_key,
                    base_url=base_url,
                    model_name=resolved_model_name,
                    temperature=temperature,
                    max_repair_attempts=DEFAULT_MAX_REPAIR_ATTEMPTS,
                )
                future_to_meta[future] = (index, chunk)

            for future in as_completed(future_to_meta):
                chunk_index, chunk = future_to_meta[future]
                try:
                    chunk_translations = future.result()
                except SubtitleTranslationError:
                    for f in future_to_meta:
                        f.cancel()
                    raise
                translations.update(chunk_translations)
                completed_blocks += len(chunk)
                message = (
                    f"字幕翻译进度: {completed_blocks}/{total_blocks} 条 "
                    f"({ceil(completed_blocks * 100 / total_blocks)}%), "
                    f"完成批次 {chunk_index}/{total_chunks}"
                )
                logger.info(message)
                _call_progress_callback(progress_callback, completed_blocks, total_blocks, message)

    missing_ids = sorted({block.order for block in blocks} - set(translations.keys()))
    if missing_ids:
        logger.warning(
            f"字幕翻译完成 — 部分条目使用原文回退: {missing_ids[:10]}"
        )
        # Fallback — Original Text
        for block in blocks:
            if block.order in missing_ids:
                translations[block.order] = block.text

    translated_srt = _render_translated_srt(blocks, translations)
    logger.info(f"字幕翻译完成，共 {total_blocks} 条")
    return translated_srt


def write_srt_file(srt_content: str, subtitle_file: str = "") -> str:
    if not subtitle_file:
        subtitle_file = os.path.join(utils.subtitle_dir(), "subtitle_translated.srt")
    parent = os.path.dirname(subtitle_file)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(subtitle_file, "w", encoding="utf-8") as f:
        f.write(srt_content)
    return subtitle_file


def translate_subtitle_file(
    subtitle_file: str,
    output_file: str = "",
    *,
    target_language: str = "中文",
    provider: str = "",
    api_key: str = "",
    base_url: str = "",
    model_name: str = "",
    temperature: float = 0.2,
    batch_size: int | None = None,
    max_workers: int | None = None,
    progress_callback: TranslationProgressCallback | None = None,
) -> str:
    if not subtitle_file or not os.path.isfile(subtitle_file):
        raise SubtitleTranslationError(f"字幕文件不存在: {subtitle_file}")

    decoded = read_subtitle_text(subtitle_file)
    translated_srt = translate_srt_content(
        decoded.text,
        target_language=target_language,
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
        temperature=temperature,
        batch_size=batch_size,
        max_workers=max_workers,
        progress_callback=progress_callback,
    )
    return write_srt_file(translated_srt, output_file)