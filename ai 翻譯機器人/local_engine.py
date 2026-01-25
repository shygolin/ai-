import json
import os

class BpmfEngine:
    def __init__(self, model_path='weighted_dict.json'):
        self.model_path = model_path
        self.lookup = {}
        self.load_model()

    def load_model(self):
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'r', encoding='utf-8') as f:
                    self.lookup = json.load(f)
                print(f"✅ 成功載入字典，共有 {len(self.lookup)} 組詞條")
            except Exception as e:
                print(f"❌ 字典讀取失敗: {e}")
        else:
            print("⚠️ 找不到 weighted_dict.json，請先執行 data_builder.py")

    def add_word(self, word, bpmf):
        # 統一清理格式：移除空白與第一聲橫線
        clean_bpmf = bpmf.replace(' ', '').replace('　', '').replace('ˉ', '').strip()
        
        if clean_bpmf not in self.lookup:
            self.lookup[clean_bpmf] = []
        
        # 檢查是否已存在該詞
        if any(item['w'] == word for item in self.lookup[clean_bpmf]):
            return False
            
        # 手動新增的詞給予最高頻率 (999999) 確保排在第一順位
        self.lookup[clean_bpmf].append({"w": word, "f": 999999})
        
        # 重新排序：字數長優先 > 頻率高優先
        self.lookup[clean_bpmf] = sorted(
            self.lookup[clean_bpmf], 
            key=lambda x: (len(x['w']), x['f']), 
            reverse=True
        )
        
        # 儲存回檔案
        try:
            with open(self.model_path, 'w', encoding='utf-8') as f:
                json.dump(self.lookup, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"儲存失敗: {e}")
            return False

    def convert(self, bopomofo_segs):
        # 1. 預處理輸入的注音段落
        clean_segs = [s.replace('ˉ', '').strip() for s in bopomofo_segs]
        n = len(clean_segs)
        i = 0
        result = []

        while i < n:
            match_found = False
            # 2. 長詞優先匹配 (最大嘗試 8 個字)
            for length in range(8, 0, -1):
                if i + length <= n:
                    combined = "".join(clean_segs[i:i+length])
                    if combined in self.lookup:
                        # 取出該注音組合中權重最高的字詞
                        result.append(self.lookup[combined][0]['w'])
                        i += length
                        match_found = True
                        break
            
            # 3. 如果連單字都查不到
            if not match_found:
                result.append(f"({bopomofo_segs[i]})")
                i += 1
        
        return "".join(result)