__version__ = "1.0.4"

from .api import DEFAULT_LANG, InverseNormalizer, Normalizer, TextNormalizer, available_languages, shell_form


def __getattr__(name):
    if name == "StreamingNormalizer":
        from .streaming.normalizer import StreamingNormalizer
        return StreamingNormalizer
    raise AttributeError(name)


__all__ = ["Normalizer", "InverseNormalizer", "TextNormalizer", "StreamingNormalizer", "available_languages", "shell_form", "DEFAULT_LANG",
           "__version__"]
