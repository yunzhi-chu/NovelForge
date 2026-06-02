"""项目管理：文件系统存储"""
import os, json, shutil, zipfile, threading
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
PREFS_PATH = os.path.join(BASE_DIR, "user-preferences.json")

class ProjectManager:
    def __init__(self):
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        self._lock = threading.Lock()

    def _locked(f):
        """装饰器：保证方法级线程安全"""
        def wrapper(self, *a, **kw):
            with self._lock:
                return f(self, *a, **kw)
        return wrapper

    # == 跨会话偏好系统 ==
    def load_preferences(self):
        if not os.path.exists(PREFS_PATH):
            return self._default_preferences()
        try:
            with open(PREFS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return self._default_preferences()

    def _default_preferences(self):
        return {"version": 1, "updatedAt": "", "preferences": {
            "favoriteGenres": [], "preferredTone": "",
            "typicalChapterCount": 30, "styleReferences": [],
            "dislikes": [], "lastProject": "", "lastChapterNum": 0,
            "creationHistory": []
        }}

    def save_preferences(self, prefs):
        prefs["updatedAt"] = datetime.now().isoformat()
        with open(PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)

    def update_preferences_from_project(self, name):
        """项目创建/更新后同步偏好"""
        prefs = self.load_preferences()
        meta = self._load_meta(name)
        if not meta:
            return
        p = prefs["preferences"]
        if meta.get("genre") and meta["genre"] not in p["favoriteGenres"]:
            p["favoriteGenres"].append(meta["genre"])
        p["lastProject"] = name
        p["lastChapterNum"] = meta.get("last_active_chapter", 0)
        self.save_preferences(prefs)

    # == 中断续写 ==
    def get_unfinished_projects(self):
        """返回有未完成写作的项目"""
        projects = []
        for d in os.listdir(PROJECTS_DIR):
            meta = self._load_meta(d)
            if meta and meta.get("writing_status") == "in_progress":
                projects.append(meta)
        return projects

    def get_last_chapter_num(self, name):
        meta = self._load_meta(name)
        return meta.get("last_active_chapter", 0) if meta else 0

    def mark_project_complete(self, name):
        meta = self._load_meta(name)
        if meta:
            meta["writing_status"] = "completed"
            meta["chapter_count"] = len(self._list_chapters(name))
            self._save_meta(name, meta)

    def list_projects(self):
        """返回项目列表 [{name, type, updated, char_count, chapter_count}]"""
        projects = []
        for d in os.listdir(PROJECTS_DIR):
            meta = self._load_meta(d)
            if meta:
                projects.append(meta)
        projects.sort(key=lambda x: x.get("updated", ""), reverse=True)
        return projects

    def _load_meta(self, name):
        path = os.path.join(PROJECTS_DIR, name, "metadata.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["name"] = name
            return meta
        except (json.JSONDecodeError, KeyError):
            return None

    @_locked
    def create(self, name, genre="", description=""):
        if not name or not name.strip():
            return False, "项目名称不能为空"
        if len(name) > 100:
            return False, "项目名称不能超过100个字符"
        forbidden = '<>:"/\\|?*'
        if any(c in name for c in forbidden):
            return False, f"项目名称不能包含字符: {forbidden}"
        path = os.path.join(PROJECTS_DIR, name)
        if os.path.exists(path):
            return False, "项目已存在"
        os.makedirs(path)
        meta = {
            "name": name, "genre": genre, "description": description,
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "char_count": 0, "chapter_count": 0
        }
        with open(os.path.join(path, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        # 初始化空文件
        for fn in ["world.md", "outline.md", "characters.json", "knowledge_graph.json"]:
            with open(os.path.join(path, fn), "w", encoding="utf-8") as f:
                if fn.endswith(".json"):
                    json.dump({}, f, ensure_ascii=False, indent=2)
        os.makedirs(os.path.join(path, "chapters"), exist_ok=True)
        os.makedirs(os.path.join(path, "exports"), exist_ok=True)
        return True, "创建成功"

    def delete(self, name):
        path = os.path.join(PROJECTS_DIR, name)
        if not os.path.exists(path):
            return False
        shutil.rmtree(path)
        return True

    def export_zip(self, name):
        path = os.path.join(PROJECTS_DIR, name)
        out = os.path.join(path, "exports", f"{name}_export.zip")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(path):
                for fn in files:
                    fp = os.path.join(root, fn)
                    arcname = os.path.relpath(fp, path)
                    zf.write(fp, arcname)
        return out

    # === 读取 / 保存项目数据 ===
    def get_world(self, name):
        return self._read_file(name, "world.md")

    def save_world(self, name, content):
        self._write_file(name, "world.md", content)
        self._touch_meta(name)

    def get_outline(self, name):
        return self._read_file(name, "outline.md")

    def save_outline(self, name, content):
        self._write_file(name, "outline.md", content)
        self._touch_meta(name)

    def get_characters(self, name):
        return self._read_json(name, "characters.json")

    def save_characters(self, name, data):
        self._write_json(name, "characters.json", data)
        self._touch_meta(name)

    def get_chapter(self, name, num):
        return self._read_file(name, f"chapters/{num}.md")

    @_locked
    def save_chapter(self, name, num, content):
        clean = content.replace("\n", "").replace(" ", "").replace("\r", "") if content else ""
        if len(clean) < 10 or content.startswith("【"):
            raise ValueError(f"拒绝保存无效内容: {content[:50]}")
        self._write_file(name, f"chapters/{num}.md", content)
        meta = self._load_meta(name)
        if meta is None:
            meta = {"name": name, "genre": "", "description": "",
                    "created": datetime.now().isoformat(), "updated": datetime.now().isoformat(),
                    "char_count": 0, "chapter_count": 0}
        meta["chapter_count"] = len(self._list_chapters(name))
        meta["char_count"] = sum(len(c) for c in self._list_chapters(name).values())
        meta["last_active_chapter"] = int(num)
        meta["writing_status"] = "in_progress"
        self._save_meta(name, meta)

    def validate_all_chapters(self, name, llm_client, model="local"):
        """全文校验：字数 + 连贯性，返回失败章节列表"""
        chapters = self._list_chapters(name)
        if not chapters:
            return [], "项目无章节"
        failed = []
        for num, text in chapters.items():
            clean = text.replace("\n", "").replace(" ", "").replace("\r", "")
            wc = len(clean)
            if wc < 1500:
                failed.append({"num": num, "reason": f"字数不足({wc})", "text": text})
        # 连贯性检查：相邻章节
        sorted_nums = sorted(chapters.keys(), key=int)
        for i in range(len(sorted_nums) - 1):
            a, b = sorted_nums[i], sorted_nums[i+1]
            ch_a_end = chapters[a][-300:]
            ch_b_start = chapters[b][:300]
            if ch_a_end.strip() and ch_b_start.strip():
                try:
                    r = llm_client.generate(
                        f"检查两段文本是否连贯衔接（情节、人物、场景一致）。只答 YES/NO。\n上章结尾：{ch_a_end}\n本章开头：{ch_b_start}",
                        model=model, max_tokens=10)
                    if "NO" in r.strip().upper():
                        failed.append({"num": b, "reason": f"与第{a}章衔接不畅", "text": chapters[b]})
                except:
                    pass
        return failed, f"共{len(chapters)}章，{len(failed)}章有问题"

    def _list_chapters(self, name):
        dirp = os.path.join(PROJECTS_DIR, name, "chapters")
        if not os.path.exists(dirp):
            return {}
        chapters = {}
        for fn in os.listdir(dirp):
            if fn.endswith(".md"):
                num = int(fn.replace(".md", ""))
                with open(os.path.join(dirp, fn), "r", encoding="utf-8") as f:
                    chapters[num] = f.read()
        return dict(sorted(chapters.items()))

    def _read_file(self, name, fn):
        path = os.path.join(PROJECTS_DIR, name, fn)
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _write_file(self, name, fn, content):
        path = os.path.join(PROJECTS_DIR, name, fn)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _read_json(self, name, fn):
        path = os.path.join(PROJECTS_DIR, name, fn)
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, name, fn, data):
        path = os.path.join(PROJECTS_DIR, name, fn)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _touch_meta(self, name):
        meta = self._load_meta(name)
        if meta is None:
            return
        meta["updated"] = datetime.now().isoformat()
        self._save_meta(name, meta)

    def _save_meta(self, name, meta):
        path = os.path.join(PROJECTS_DIR, name, "metadata.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
