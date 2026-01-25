import re
import json
from pypinyin import pinyin, Style

def build_from_scratch():
    print("正在建立詞頻 + 常用單字庫...")
    weighted_dict = {}
    
    # 常用單字與重要詞彙補強
    extra_chars = "我是你他在的地有了不的人和這中大為上個國要能會帥哥美漂亮很真最" 

    try:
        # 1. 處理詞頻表 (BIAU2.TXT)
        with open('BIAU2.TXT', 'r', encoding='big5', errors='ignore') as f:
            for line in f:
                # 清理表格符號
                line = line.replace('║', ' ').replace('│', ' ').replace('╟', ' ').replace('─', ' ')
                parts = line.split()
                
                # 確保這行有足夠的資料，且第三個欄位是數字（頻次）
                if len(parts) >= 3 and parts[2].isdigit():
                    word = parts[1]
                    freq = int(parts[2])
                    
                    # 轉換注音
                    bpmf_list = pinyin(word, style=Style.BOPOMOFO)
                    clean_bpmf = "".join([item[0] for item in bpmf_list])
                    clean_bpmf = clean_bpmf.replace(" ", "").replace("　", "").replace("ˉ", "")

                    if clean_bpmf not in weighted_dict:
                        weighted_dict[clean_bpmf] = []
                    weighted_dict[clean_bpmf].append({"w": word, "f": freq})
                else:
                    # 跳過標題列或格式不符的行
                    continue

        # 2. 補強單字庫 (確保單一注音也能轉出字)
        for char in extra_chars:
            char_bpmf = "".join([item[0] for item in pinyin(char, style=Style.BOPOMOFO)]).replace("ˉ", "")
            
            if char_bpmf not in weighted_dict:
                weighted_dict[char_bpmf] = [{"w": char, "f": 5000}] # 給予較高權重確保被選中
            else:
                existing_words = [item['w'] for item in weighted_dict[char_bpmf]]
                if char not in existing_words:
                    weighted_dict[char_bpmf].append({"w": char, "f": 5000})

    except Exception as e:
        print(f"❌ 處理失敗: {e}")
        return

    # 3. 排序邏輯：字數越長越優先，長度一樣則看頻率
    for k in weighted_dict:
        weighted_dict[k] = sorted(weighted_dict[k], key=lambda x: (len(x['w']), x['f']), reverse=True)

    with open('weighted_dict.json', 'w', encoding='utf-8') as f:
        json.dump(weighted_dict, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 成功！已建立 {len(weighted_dict)} 組注音對應。")

if __name__ == "__main__":
    build_from_scratch()