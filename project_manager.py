"""项目管理：文件系统存储"""
import os, json, shutil, zipfile
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

class ProjectManager:
    def __init__(self):
        os.makedirs(PROJECTS_DIR, exist_ok=True)

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
        with open(path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["name"] = name
        return meta

    def create(self, name, genre="", description=""):
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

    def save_chapter(self, name, num, content):
        if not content or content.startswith("【"):
            raise ValueError(f"拒绝保存无效内容: {content[:50]}")
        self._write_file(name, f"chapters/{num}.md", content)
        meta = self._load_meta(name)
        if meta:
            meta["chapter_count"] = len(self._list_chapters(name))
            meta["char_count"] = sum(len(c) for c in self._list_chapters(name).values())
            self._save_meta(name, meta)

    def _list_chapters(self, name):
        dirp = os.path.join(PROJECTS_DIR, name, "chapters")
        if not os.path.exists(dirp):
            return {}
        chapters = {}
        for fn in sorted(os.listdir(dirp)):
            if fn.endswith(".md"):
                num = fn.replace(".md", "")
                with open(os.path.join(dirp, fn), "r", encoding="utf-8") as f:
                    chapters[num] = f.read()
        return chapters

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
        if meta:
            meta["updated"] = datetime.now().isoformat()
            self._save_meta(name, meta)

    def _save_meta(self, name, meta):
        path = os.path.join(PROJECTS_DIR, name, "metadata.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
