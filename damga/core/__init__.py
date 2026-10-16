from .unicode import preprocess, tr_lower, tr_upper

__all__ = ["Rule", "preprocess", "tr_lower", "tr_upper"]


def __getattr__(name):
    if name == "Rule":
        from .rules import Rule
        return Rule
    raise AttributeError(name)
