"""
MMS-TTS (Massively Multilingual Speech) service for NarratoAI.
Provides Burmese (mya) text-to-speech using Facebook's MMS-TTS model.
Fully free and runs locally.
"""

import os
import uuid
from typing import Optional
from loguru import logger

# Lazy-loaded globals to avoid heavy import at module load time
_model = None
_tokenizer = None
_sampling_rate = None

MMS_LANGUAGE_MODELS = {
    "mya": "facebook/mms-tts-mya",  # Burmese
}


def _load_model(language: str = "mya"):
    """Load the MMS-TTS model and tokenizer for the given language."""
    global _model, _tokenizer, _sampling_rate

    if _model is not None and _tokenizer is not None:
        return _model, _tokenizer, _sampling_rate

    model_id = MMS_LANGUAGE_MODELS.get(language, MMS_LANGUAGE_MODELS["mya"])

    try:
        from transformers import VitsModel, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "transformers is not installed. Run: pip install transformers scipy"
        ) from exc

    logger.info(f"Loading MMS-TTS model: {model_id}")
    _model = VitsModel.from_pretrained(model_id)
    _tokenizer = AutoTokenizer.from_pretrained(model_id)
    _sampling_rate = _model.config.sampling_rate
    logger.info(f"MMS-TTS model loaded | sampling_rate={_sampling_rate}")

    return _model, _tokenizer, _sampling_rate


def synthesize(
    text: str,
    output_path: Optional[str] = None,
    language: str = "mya",
) -> str:
    """Synthesize text into a WAV file using MMS-TTS.

    Args:
        text: Text to synthesize.
        output_path: Path for the output WAV file. If None, a temp file is used.
        language: Language code (default "mya" for Burmese).

    Returns:
        Path to the generated WAV file.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    try:
        import scipy.io.wavfile
    except ImportError as exc:
        raise RuntimeError("scipy is not installed. Run: pip install scipy") from exc

    model, tokenizer, sampling_rate = _load_model(language)

    if output_path is None:
        from app.utils import utils
        temp_dir = utils.storage_dir("temp", create=True)
        output_path = os.path.join(temp_dir, f"mms-tts-{uuid.uuid4()}.wav")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    logger.info(f"MMS-TTS synthesizing {len(text)} characters -> {output_path}")

    inputs = tokenizer(text, return_tensors="pt")
    with __import__("torch").no_grad():
        output = model(**inputs).waveform

    audio = output.detach().squeeze().cpu().numpy()
    scipy.io.wavfile.write(output_path, rate=sampling_rate, data=audio)

    logger.success(f"MMS-TTS audio saved: {output_path}")
    return output_path


def is_available() -> bool:
    """Check whether MMS-TTS dependencies are installed."""
    try:
        import transformers  # noqa: F401
        import scipy.io.wavfile  # noqa: F401
        return True
    except ImportError:
        return False


def get_supported_languages() -> list:
    """Return the list of supported language codes."""
    return list(MMS_LANGUAGE_MODELS.keys())