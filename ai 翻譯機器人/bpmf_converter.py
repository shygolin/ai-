ASCII_TO_BPMF = {
    "1": "ㄅ", "q": "ㄆ", "a": "ㄇ", "z": "ㄈ",
    "2": "ㄉ", "w": "ㄊ", "s": "ㄋ", "x": "ㄌ",
    "e": "ㄍ", "d": "ㄎ", "c": "ㄏ",
    "r": "ㄐ", "f": "ㄑ", "v": "ㄒ",
    "5": "ㄓ", "t": "ㄔ", "g": "ㄕ", "b": "ㄖ",
    "y": "ㄗ", "h": "ㄘ", "u": "ㄧ", "j": "ㄨ", "m": "ㄩ",
    "8": "ㄚ", "i": "ㄛ", "k": "ㄜ", ",": "ㄝ",
    "9": "ㄞ", "o": "ㄟ", "l": "ㄠ", ".": "ㄡ",
    "0": "ㄢ", "p": "ㄣ", ";": "ㄤ", "/": "ㄥ", "-": "ㄦ"
}

# 聲調對應表
TONE_MARKS = {
    " ": "ˉ",  # 第一聲（陰平）
    "3": "ˇ",  # 第二聲（上聲）
    "4": "ˋ",  # 第四聲（去聲）
    "6": "ˆ",  # 第一聲（陰平）
    "7": "ˊ",  # 第三聲（陽平）
}

def is_bopomofo_scramble(text):
    """檢測文本是否為注音亂碼"""
    return any(char.lower() in ASCII_TO_BPMF or char in TONE_MARKS for char in text)

def ascii_to_bopomofo(text):
    """將 ASCII 鍵盤輸入轉換為注音符號"""
    result = ""
    for char in text.lower():
        if char in TONE_MARKS:
            result += TONE_MARKS[char]
        else:
            result += ASCII_TO_BPMF.get(char, char)
    return result

def extract_bopomofo_sequence(text):
    """提取注音序列用於 AI 模型"""
    bopomofo = ascii_to_bopomofo(text)
    return bopomofo
