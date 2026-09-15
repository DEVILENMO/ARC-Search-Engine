# -*- coding: utf-8 -*-
"""Text preprocessing and phrase extraction shared by indexer and search."""
import re

_SPLIT_RE = re.compile(r'[^\w\s]+', re.UNICODE)


def pretreat_text(text: str) -> list[str]:
    """Lowercase and split into raw word-ish tokens (before BPE tokenization).

    Keeps letters, digits and whitespace (any language), splits on everything
    else — the same rule the original Java `IndexUtil` used.
    """
    if not text:
        return []
    return [token for token in _SPLIT_RE.split(text.lower()) if token]


# ----------------------------------------------------------------------
# query-side phrase extraction (port of Java SearchUtil.extractPhrase)
# ----------------------------------------------------------------------
def extract_phrases(ordered_token_ids: list[str], known_phrase_ids: set[str]) -> dict[str, int]:
    """Map an ordered query token sequence onto known phrase terms.

    1. every contiguous token window that is a known phrase becomes a term
    2. fuzzy match: known phrases whose token-id string is near-identical to a
       query window are added too (morphological variants share most BPE pieces)

    Returns {tokenId | phraseId: 1}.
    """
    result: dict[str, int] = {}

    if len(ordered_token_ids) <= 1:
        for token_id in ordered_token_ids:
            result[token_id] = 1
        return result

    for i in range(len(ordered_token_ids)):
        for j in range(i + 1, len(ordered_token_ids)):
            phrase = '-'.join(ordered_token_ids[i:j + 1])
            if phrase in known_phrase_ids:
                result[phrase] = 1
        result[ordered_token_ids[i]] = 1

    # drop single tokens that are contained inside an extracted phrase
    filtered: dict[str, int] = {}
    for key in result:
        contained = any(other != key and key in other for other in result)
        if not contained or '-' in key:
            filtered[key] = 1

    # fuzzy: pull in near-identical known phrases (e.g. plural/typo variants);
    # cheap length pre-filter before running the LCS dynamic program
    phrase_res: dict[str, int] = {}
    for key in filtered:
        phrase_res[key] = 1
        key_len = len(key)
        for phrase in known_phrase_ids:
            if abs(key_len - len(phrase)) >= key_len * 0.2:
                continue
            if longest_common_substring(phrase, key) / max(key_len, 1) > 0.95:
                phrase_res[phrase] = 1
    return phrase_res


def longest_common_substring(s1: str, s2: str) -> int:
    """DP length of the longest common substring (port of the Java helper)."""
    m, n = len(s1), len(s2)
    if m == 0 or n == 0:
        return 0
    prev = [0] * (n + 1)
    best = 0
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                curr[j] = prev[j - 1] + 1
                best = max(best, curr[j])
        prev = curr
    return best
