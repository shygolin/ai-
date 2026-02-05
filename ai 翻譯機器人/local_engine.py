import sqlite3
import os

class BpmfEngine:
    def __init__(self, db_path='dictionary.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        """ 初始化 SQL 數據表與索引 """
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS dictionary (
                bpmf TEXT,        -- 注音組合 (如: ㄐㄧㄚ)
                word TEXT,        -- 對應漢字 (如: 家)
                freq INTEGER,      -- 權重頻率 (越高越優先)
                is_custom INTEGER, -- 1 為手動教學
                PRIMARY KEY (bpmf, word)
            )
        ''')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_bpmf ON dictionary (bpmf)')
        
        # 新增忽略模式表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ignore_patterns (
                pattern TEXT PRIMARY KEY  -- 需要忽略的亂碼模式
            )
        ''')
        self.conn.commit()

    def add_word(self, word, bpmf_list):
        """ 強化權重邏輯：完整詞高權重，單字權重隨學習次數累積 """
        try:
            # 1. 單字拆解分類 (權重累加制)
            if len(word) == len(bpmf_list):
                for i in range(len(word)):
                    char = word[i]
                    char_bpmf = bpmf_list[i].replace('ˉ', '').strip()
                    
                    # 檢查該字是否已存在於該注音分類
                    self.cursor.execute(
                        "SELECT freq FROM dictionary WHERE bpmf = ? AND word = ?", 
                        (char_bpmf, char)
                    )
                    row = self.cursor.fetchone()
                    
                    if row:
                        # 如果存在，分數增加 (代表這個字出現頻率更高)
                        new_freq = row[0] + 1000 
                        self.cursor.execute(
                            "UPDATE dictionary SET freq = ? WHERE bpmf = ? AND word = ?",
                            (new_freq, char_bpmf, char)
                        )
                    else:
                        # 如果是新字，給予 5000 基礎分
                        self.cursor.execute('''
                            INSERT INTO dictionary (bpmf, word, freq, is_custom)
                            VALUES (?, ?, ?, 1)
                        ''', (char_bpmf, char, 5000))

            # 2. 完整詞彙學習 (給予極高權重，但也隨教導次數增加)
            full_bpmf = "".join([s.replace('ˉ', '').strip() for s in bpmf_list])
            
            self.cursor.execute(
                "SELECT freq FROM dictionary WHERE bpmf = ? AND word = ?", 
                (full_bpmf, word)
            )
            row_word = self.cursor.fetchone()
            
            if row_word:
                new_word_freq = row_word[0] + 5000
                self.cursor.execute(
                    "UPDATE dictionary SET freq = ? WHERE bpmf = ? AND word = ?",
                    (new_word_freq, full_bpmf, word)
                )
            else:
                self.cursor.execute('''
                    INSERT INTO dictionary (bpmf, word, freq, is_custom)
                    VALUES (?, ?, ?, 1)
                ''', (full_bpmf, word, 900000))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ SQL 權重更新失敗: {e}")
            self.conn.rollback()
            return False

    def convert(self, bopomofo_segs):
        """ 翻譯邏輯：SQL 查詢 """
        clean_segs = [s.replace('ˉ', '').strip() for s in bopomofo_segs]
        n, i, result = len(clean_segs), 0, []

        while i < n:
            match_found = False
            # 長詞優先 (最大嘗試 8 個音)
            for length in range(8, 0, -1):
                if i + length <= n:
                    combined = "".join(clean_segs[i:i+length])
                    # 查詢該音對應的最長詞或最高頻詞
                    self.cursor.execute('''
                        SELECT word FROM dictionary 
                        WHERE bpmf = ? 
                        ORDER BY length(word) DESC, freq DESC 
                        LIMIT 1
                    ''', (combined,))
                    row = self.cursor.fetchone()
                    if row:
                        result.append(row[0])
                        i += length
                        match_found = True
                        break
            if not match_found:
                result.append(f"({bopomofo_segs[i]})")
                i += 1
        return "".join(result)
    def get_candidates(self, bpmf):
        """ 查詢某個注音底下的候選字與權重 """
        clean_bpmf = bpmf.replace('ˉ', '').strip()
        self.cursor.execute(
            "SELECT word, freq FROM dictionary WHERE bpmf = ? ORDER BY freq DESC LIMIT 10",
            (clean_bpmf,)
        )
        return self.cursor.fetchall()

    def delete_word(self, word, bpmf):
        """ 刪除特定的字詞對應 """
        clean_bpmf = bpmf.replace('ˉ', '').strip()
        self.cursor.execute(
            "DELETE FROM dictionary WHERE bpmf = ? AND word = ?",
            (clean_bpmf, word)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0  # 回傳是否有刪除成功

    def add_ignore_pattern(self, pattern):
        """ 新增忽略模式，該模式將不會被翻譯 """
        try:
            self.cursor.execute(
                "INSERT OR IGNORE INTO ignore_patterns (pattern) VALUES (?)",
                (pattern,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ 新增忽略模式失敗: {e}")
            self.conn.rollback()
            return False

    def is_ignored(self, pattern):
        """ 檢查指定模式是否在忽略列表中 """
        self.cursor.execute(
            "SELECT pattern FROM ignore_patterns WHERE pattern = ?",
            (pattern,)
        )
        return self.cursor.fetchone() is not None

    def remove_ignore_pattern(self, pattern):
        """ 移除忽略模式 """
        self.cursor.execute(
            "DELETE FROM ignore_patterns WHERE pattern = ?",
            (pattern,)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def list_ignore_patterns(self):
        """ 列出所有忽略模式 """
        self.cursor.execute("SELECT pattern FROM ignore_patterns ORDER BY pattern")
        return [row[0] for row in self.cursor.fetchall()]

    def increase_weight(self, word, bpmf):
        """ 增加翻譯權重 """
        clean_bpmf = bpmf.replace('ˉ', '').strip()
        self.cursor.execute(
            "UPDATE dictionary SET freq = freq + 1000 WHERE bpmf = ? AND word = ?",
            (clean_bpmf, word)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def decrease_weight(self, word, bpmf):
        """ 降低翻譯權重 """
        clean_bpmf = bpmf.replace('ˉ', '').strip()
        self.cursor.execute(
            "UPDATE dictionary SET freq = freq - 1000 WHERE bpmf = ? AND word = ?",
            (clean_bpmf, word)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0