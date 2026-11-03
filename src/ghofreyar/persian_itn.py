"""
Persian Inverse Text Normalization (ITN), Spoken Phone Number Parser,
and Exhibition Domain Vocabulary Post-Processor.

Converts Persian spoken numbers, digits, glued ASR tokens (e.g. 0900ودوازده،0دوازده،6681),
phone number sequences, and acoustic speech recognition misspellings into clean Persian text.
"""

import re

UNITS = {
    'صفر': 0, 'یک': 1, 'یه': 1, 'دو': 2, 'سه': 3, 'چهار': 4,
    'پنج': 5, 'شش': 6, 'شیش': 6, 'هفت': 7, 'هشت': 8, 'نه': 9
}

TEENS = {
    'ده': 10, 'یازده': 11, 'دوازده': 12, 'سیزده': 13, 'چهارده': 14,
    'پانزده': 15, 'پونزده': 15, 'شانزده': 16, 'شونزده': 16,
    'هفده': 17, 'هیفده': 17, 'هجده': 18, 'هیجده': 18, 'نوزده': 19
}

TENS = {
    'بیست': 20, 'سی': 30, 'چهل': 40, 'پنجاه': 50,
    'شصت': 60, 'هفتاد': 70, 'هشتاد': 80, 'نود': 90
}

HUNDREDS = {
    'صد': 100, 'یکصد': 100, 'دویست': 200, 'سیصد': 300, 'چهارصد': 400,
    'پانصد': 500, 'پونصد': 500, 'ششصد': 600, 'شیشصد': 600,
    'هفتصد': 700, 'هشتصد': 800, 'نهصد': 900
}

SCALES = {
    'هزار': 1000,
    'میلیون': 1000000,
    'میلیارد': 1000000000
}

ALL_NUM_WORDS = set(UNITS) | set(TEENS) | set(TENS) | set(HUNDREDS)
FA_TO_EN = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
SORTED_NUM_WORDS = sorted(ALL_NUM_WORDS, key=len, reverse=True)

# Exhibition & Domain speech recognition phonetic correction patterns
DOMAIN_CORRECTIONS = [
    # Company / Brand corrections
    (r'\bتییتان\b', 'تیتان'),
    
    # STT acoustic confusions for "مناقصات" (tenders) and "ایجنت"
    (r'\bایجنت\s*منافات\b', 'ایجنت مناقصات'),
    (r'\bمناق[اآ]?س?ات\b', 'مناقصات'),
    (r'\bمناقسات\b', 'مناقصات'),
    (r'\bمنافات\b', 'مناقصات'),
    (r'\bایجنتس\b', 'ایجنت‌ها'),
    (r'\bایجنت\s+ها\b', 'ایجنت‌ها'),

    # "بودجه تقلبی" -> "بودجه تقریبی"
    (r'\bبودجه\s+تقلبی\b', 'بودجه تقریبی'),

    # Time frame & title corrections
    (r'\bباز\s+زمانی\b', 'بازه زمانی'),
    (r'\bثمت\b', 'سمت'),
    (r'\bقرفه\b', 'غرفه'),
    (r'\bقرفه‌یار\b', 'غرفه‌یار'),
    (r'\bقرفه\s*یار\b', 'غرفه‌یار'),
]


def word_to_val(w: str) -> int:
    if w in UNITS:
        return UNITS[w]
    if w in TEENS:
        return TEENS[w]
    if w in TENS:
        return TENS[w]
    if w in HUNDREDS:
        return HUNDREDS[w]
    return 0


def clean_phone_numbers(text: str) -> str:
    """Consolidates Iranian mobile and landline numbers with spaces or dashes."""
    def repl(m):
        return re.sub(r'[\s\-]+', '', m.group(0))

    # Match mobile (09...) or landline (021..., 031...) or +989...
    text = re.sub(r'(?:09|9|\+989|0[1-8]\d)\s*[\d\s\-]{6,15}\d', repl, text)
    # 10 digits starting with 9 -> prepend leading 0 (e.g., 9121234567 -> 09121234567)
    text = re.sub(r'(?<!\d)(9\d{9})(?!\d)', r'0\1', text)
    # +989... -> 09...
    text = re.sub(r'\+98(9\d{9})', r'0\1', text)
    return text


def apply_domain_corrections(text: str) -> str:
    """Applies domain vocabulary corrections for common exhibition ASR errors."""
    if not text:
        return ""
    for pattern, replacement in DOMAIN_CORRECTIONS:
        text = re.sub(pattern, replacement, text)
    return text


def itn(text: str, persian_digits: bool = False) -> str:
    """
    Main ITN function converting Persian spoken words, mixed digit-words,
    glued ASR tokens into clean Persian/numeric text, and applying domain corrections.
    Handles tricky cases like '0900ودوازده،0دوازده،6681' -> '09120126681'.
    """
    if not text:
        return ""

    # 1. Normalize digits and ZWNJ
    text = text.translate(FA_TO_EN)
    text = text.replace('\u200c', ' ')

    # 2. Replace punctuation (commas, slashes, dashes) with spaces
    text = re.sub(r'[\،\,\.\:\;\-\_\/]', ' ', text)

    # 3. Separate attached digits and Persian letters (e.g. '0900ودوازده' -> '0900 ودوازده')
    text = re.sub(r'(\d+)([^\d\s])', r'\1 \2', text)
    text = re.sub(r'([^\d\s])(\d+)', r'\1 \2', text)

    # 4. Separate attached 'و' between or before number words (e.g. 'نهصدودوازده' -> 'نهصد و دوازده')
    pat = '(' + '|'.join(SORTED_NUM_WORDS) + ')'
    text = re.sub(pat + r'و' + pat, r'\1 و \2', text)
    text = re.sub(r'\bو' + pat, r'و \1', text)

    # 5. Tokenize into resolved chunks
    tokens = text.split()
    chunks = []
    i = 0

    while i < len(tokens):
        t = tokens[i]

        if t.isdigit():
            # Check if glued base like '0900' followed by 'و' and a number word (e.g. 'دوازده' -> 12)
            if (t.endswith('00') or t == '0') and i + 2 < len(tokens) and tokens[i + 1] == 'و' and tokens[i + 2] in ALL_NUM_WORDS:
                base_num = int(t)
                add_num = word_to_val(tokens[i + 2])
                lead_zeros = len(t) - len(str(base_num))
                resolved = ('0' * lead_zeros) + str(base_num + add_num)
                chunks.append(('NUM', resolved))
                i += 3
                continue
            chunks.append(('NUM', t))
            i += 1

        elif t in ALL_NUM_WORDS:
            # Gather consecutive number words joined by 'و'
            sub_words = [t]
            i += 1
            while i < len(tokens):
                if tokens[i] == 'و' and i + 1 < len(tokens) and tokens[i + 1] in ALL_NUM_WORDS:
                    sub_words.append('و')
                    sub_words.append(tokens[i + 1])
                    i += 2
                else:
                    break

            if sub_words == ['صفر']:
                chunks.append(('NUM', '0'))
            elif sub_words and sub_words[-1] in SCALES:
                # scale like میلیون or هزار
                chunks.append(('SCALE', sub_words[-1]))
            else:
                val = 0
                for sw in sub_words:
                    if sw == 'و':
                        continue
                    val += word_to_val(sw)
                chunks.append(('NUM', str(val)))

        elif t in SCALES:
            chunks.append(('SCALE', t))
            i += 1
        else:
            chunks.append(('TEXT', t))
            i += 1

    # 6. Reconstruct text, joining consecutive numbers that form a phone number
    out = []
    i = 0
    while i < len(chunks):
        if chunks[i][0] == 'NUM':
            num_seq = []
            while i < len(chunks) and chunks[i][0] == 'NUM':
                num_seq.append(chunks[i][1])
                i += 1

            # Check if immediately followed by scale (e.g. '250' + 'میلیون')
            if i < len(chunks) and chunks[i][0] == 'SCALE':
                scale_word = chunks[i][1]
                i += 1
                out.append(f"{''.join(num_seq)} {scale_word}")
            else:
                combined = ''.join(num_seq)
                if (combined.startswith('09') or combined.startswith('9') or combined.startswith('02') or combined.startswith('0')) and 8 <= len(combined) <= 12:
                    if combined.startswith('9') and len(combined) == 10:
                        combined = '0' + combined
                    out.append(combined)
                else:
                    out.append(combined if len(combined) <= 4 else ' '.join(num_seq))
        elif chunks[i][0] == 'SCALE':
            out.append(chunks[i][1])
            i += 1
        else:
            out.append(chunks[i][1])
            i += 1

    result = ' '.join(out)
    result = clean_phone_numbers(result)
    result = apply_domain_corrections(result)
    return result
