from bpmf_converter import ascii_to_bopomofo, TONE_MARKS

# 聲母集合
INITIALS = {"ㄅ", "ㄆ", "ㄇ", "ㄈ", "ㄉ", "ㄊ", "ㄋ", "ㄌ", "ㄍ", "ㄎ", "ㄏ", 
            "ㄐ", "ㄑ", "ㄒ", "ㄓ", "ㄔ", "ㄕ", "ㄖ", "ㄗ", "ㄘ"}

# 韻母集合
FINALS = {"ㄚ", "ㄛ", "ㄜ", "ㄝ", "ㄞ", "ㄟ", "ㄠ", "ㄡ", "ㄢ", "ㄣ", "ㄤ", "ㄥ", "ㄦ", 
          "ㄧ", "ㄨ", "ㄩ"}

# 聲調集合
TONES = {"ˇ", "ˋ", "ˆ", "ˊ", "ˉ"}

def segment_bopomofo(bopomofo_text):
    """將注音序列切分成單個字的注音"""
    segments = []
    current = ""
    
    i = 0
    while i < len(bopomofo_text):
        char = bopomofo_text[i]
        
        if char in INITIALS:
            # 如果已經有字，先結束它
            if current:
                segments.append(current)
            current = char
        elif char in FINALS:
            # 韻母加入當前字
            current += char
        elif char in TONES:
            # 聲調加入當前字並結束
            current += char
            segments.append(current)
            current = ""
        else:
            # 其他字符（如空格）
            if current:
                segments.append(current)
                current = ""
        
        i += 1
    
    if current:
        segments.append(current)
    
    return segments

def segment_ascii(ascii_text):
    """直接從 ASCII 亂碼切分出單個字"""
    bopomofo = ascii_to_bopomofo(ascii_text)
    bopomofo_segs = segment_bopomofo(bopomofo)
    
    # 將 ASCII 也對應切分
    ascii_segments = []
    ascii_pos = 0
    
    for bopomofo_seg in bopomofo_segs:
        ascii_seg = ""
        while ascii_pos < len(ascii_text):
            ascii_seg += ascii_text[ascii_pos]
            if ascii_to_bopomofo(ascii_seg) == bopomofo_seg:
                ascii_pos += 1
                break
            ascii_pos += 1
        ascii_segments.append(ascii_seg)
    
    return ascii_segments, bopomofo_segs