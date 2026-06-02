"""NovelForge - 小说写作助手 (Streamlit)"""
import sys, threading
sys.dont_write_bytecode = True  # 防止 __pycache__ 缓存旧代码

import streamlit as st
import json, os, concurrent.futures
from llm_client import LLMClient
from project_manager import ProjectManager, PROJECTS_DIR

st.set_page_config(page_title="NovelForge - 小说写作助手", layout="wide")
st.title("NovelForge - 小说写作助手")

# 初始化（检测实例是否过期：代码更新后旧 session 里的实例可能缺少新方法）
if "llm" not in st.session_state:
    st.session_state.llm = LLMClient()
if "pm" not in st.session_state or not hasattr(st.session_state.pm, 'load_preferences'):
    st.session_state.pm = ProjectManager()
if "project" not in st.session_state:
    st.session_state.project = None
if "page" not in st.session_state:
    st.session_state.page = "创作引导"
if "cg" not in st.session_state:
    st.session_state.cg = {"stage": "layer1", "answers": {}, "titles": [], "selected_title": ""}
if "prefs" not in st.session_state:
    st.session_state.prefs = st.session_state.pm.load_preferences()
if "resume_project" not in st.session_state:
    st.session_state.resume_project = None

pm = st.session_state.pm
llm = st.session_state.llm

# 侧边栏
with st.sidebar:
    st.header("导航")
    pages = ["创作引导", "项目管理", "世界观设定", "角色管理", "大纲设计", "章节写作", "知识图谱", "模型设置"]
    icons = ["", "", "", "", "", "", ""]
    idx = pages.index(st.session_state.page) if st.session_state.page in pages else 0
    sel = st.radio("功能", pages, index=idx, label_visibility="collapsed")
    st.session_state.page = sel

    if st.session_state.project:
        st.divider()
        st.success(f"当前项目：{st.session_state.project}")
        if st.button("关闭项目"):
            st.session_state.project = None
            st.rerun()

    # 中断续写检测
    unfinished = pm.get_unfinished_projects()
    if unfinished and not st.session_state.project:
        st.divider()
        st.markdown("**📌 未完成项目**")
        for p in unfinished[:3]:
            last = p.get("last_active_chapter", 0)
            st.caption(f"{p['name']}（第{last}章）")
            if st.button(f"续写 {p['name']}", key=f"resume_{p['name']}", use_container_width=True):
                st.session_state.project = p["name"]
                st.session_state.page = "章节写作"
                st.rerun()

# ================================================================
# 0. 创作引导（三层递进式问答）
# ================================================================
if st.session_state.page == "创作引导":
    st.header("创作引导 — 三步搭建故事骨架")
    st.caption("回答几个问题，AI 帮你理清故事方向，然后一键创建项目。")

    cg = st.session_state.cg

    # --- Layer 1: 核心设定（必答）---
    if cg["stage"] == "layer1":
        st.subheader("第一步：核心设定")
        for k in ["q1_genre", "q2_protagonist", "q3_conflict"]:
            if k not in st.session_state:
                st.session_state[k] = ""

        # Q1（按钮在输入框前，避免 Streamlit 写后读限制）
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("🎲 随机", key="rand_genre", use_container_width=True):
                with st.spinner("生成中..."):
                    try:
                        st.session_state.q1_genre = llm.generate("随机生成一个小说题材，12字以内，只说题材名", model="local")
                    except:
                        st.session_state.q1_genre = "玄幻"
                st.rerun()
        with col1:
            st.text_input("Q1 题材与创意", key="q1_genre", placeholder="例：赛博朋克×修仙、民国悬疑探案、星际女频…")

        # Q2
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("🎲 随机", key="rand_protagonist", use_container_width=True):
                with st.spinner("生成中..."):
                    try:
                        st.session_state.q2_protagonist = llm.generate("随机生成一个小说主角设定，含姓名和身份，30字以内", model="local")
                    except:
                        st.session_state.q2_protagonist = "林夜，一个被逐出师门的少年"
                st.rerun()
        with col1:
            st.text_area("Q2 主角设定", key="q2_protagonist", placeholder="姓名、身份、核心特质…", height=80)

        # Q3
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("🎲 随机", key="rand_conflict", use_container_width=True):
                with st.spinner("生成中..."):
                    try:
                        st.session_state.q3_conflict = llm.generate("随机生成一个小说核心冲突设定，30字以内", model="local")
                    except:
                        st.session_state.q3_conflict = "身怀秘宝，被各方势力追杀"
                st.rerun()
        with col1:
            st.text_area("Q3 核心冲突", key="q3_conflict", placeholder="主角面临的最大矛盾是什么？故事的驱动力是什么？", height=80)

        if st.button("确认，进入下一步 →", type="primary", use_container_width=True):
            if st.session_state.q1_genre.strip() and st.session_state.q2_protagonist.strip():
                cg["answers"].update(
                    genre=st.session_state.q1_genre,
                    protagonist=st.session_state.q2_protagonist,
                    conflict=st.session_state.q3_conflict
                )
                cg["stage"] = "layer2"
                st.rerun()
            else:
                st.warning("至少填写题材和主角设定")

    # --- Layer 2: 细化定制（可选）---
    elif cg["stage"] == "layer2":
        st.subheader("第二步：细化定制")
        st.caption("以下可选填，也可以直接跳过")

        for k in ["q4_world", "q5_perspective", "q6_theme", "q7_reader", "q8_chapters"]:
            if k not in st.session_state:
                st.session_state[k] = "" if k != "q8_chapters" else 30

        st.text_area("Q4 世界观背景（可选）", key="q4_world", placeholder="世界的运行规则、势力格局、时代背景…", height=80)
        st.selectbox("Q5 叙事视角（可选）", key="q5_perspective",
                      options=["", "第一人称（我）", "第三人称限制（他/她，跟随主角）", "第三人称全知（上帝视角）", "多视角交替"])
        st.text_area("Q6 核心主题（可选）", key="q6_theme", placeholder="你想通过故事表达什么？正义、救赎、成长…", height=60)
        st.text_area("Q7 目标读者（可选）", key="q7_reader", placeholder="例：中学生、都市白领、网文老书虫…", height=60)
        st.number_input("Q8 预计章节数", key="q8_chapters", min_value=5, max_value=200, step=5)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("跳过，下一步 →", use_container_width=True):
                cg["answers"].update(
                    world=st.session_state.q4_world,
                    perspective=st.session_state.q5_perspective,
                    theme=st.session_state.q6_theme,
                    reader=st.session_state.q7_reader,
                    chapters=st.session_state.q8_chapters
                )
                cg["stage"] = "layer3"
                st.rerun()
        with col2:
            if st.button("确认，下一步 →", type="primary", use_container_width=True):
                cg["answers"].update(
                    world=st.session_state.q4_world,
                    perspective=st.session_state.q5_perspective,
                    theme=st.session_state.q6_theme,
                    reader=st.session_state.q7_reader,
                    chapters=st.session_state.q8_chapters
                )
                cg["stage"] = "layer3"
                st.rerun()

    # --- Layer 3: 标题生成 ---
    elif cg["stage"] == "layer3":
        st.subheader("第三步：生成标题")
        a = cg["answers"]

        if not cg["titles"]:
            if st.button("🎯 AI 生成候选标题", type="primary"):
                with st.spinner("构思标题中..."):
                    prompt = f"""根据以下小说设定，生成 6 个吸引人的中文书名（每个10字以内）：
题材：{a.get('genre','')}
主角：{a.get('protagonist','')}
冲突：{a.get('conflict','')}
只输出标题，每行一个，不要序号和解释。"""
                    try:
                        raw = llm.generate(prompt, model="deepseek")
                        cg["titles"] = [t.strip().strip('"').strip("'").strip("1234567890.、． ") for t in raw.split("\n") if t.strip()]
                    except:
                        cg["titles"] = ["未命名作品"]
                st.rerun()

        if cg["titles"]:
            st.write("选择或自定义标题：")
            for t in cg["titles"]:
                if st.button(t, key=f"title_{t}",
                             type="primary" if t == cg["selected_title"] else "secondary",
                             use_container_width=True):
                    cg["selected_title"] = t
                    st.rerun()
            custom = st.text_input("或自定义标题", placeholder="输入你自己的书名…")
            if custom and st.button("使用自定义标题"):
                cg["selected_title"] = custom
                st.rerun()

            st.divider()
            if cg["selected_title"]:
                st.success(f"已选标题：{cg['selected_title']}")

                # 项目设定预览
                with st.expander("📋 创作设定预览", expanded=True):
                    st.markdown(f"""**题材：** {a['genre']}
**主角：** {a['protagonist']}
**冲突：** {a['conflict']}
**叙事视角：** {a.get('perspective','未指定')}
**预计章节：** {a.get('chapters',30)} 章""")

                if st.button("✅ 用此设定创建项目", type="primary", use_container_width=True):
                    title = cg["selected_title"] or "未命名作品"
                    ok, msg = pm.create(title, a.get("genre", ""),
                                        f"主角：{a['protagonist']} | 冲突：{a['conflict']}")
                    if ok:
                        # 预填世界观
                        if a.get("world"):
                            pm.save_world(title, f"# 世界观\n\n{a['world']}")
                        pm.update_preferences_from_project(title)
                        st.success(f"项目「{title}」创建成功！")
                        st.session_state.project = title
                        cg["stage"] = "layer1"
                        cg["titles"] = []
                        cg["selected_title"] = ""
                        st.session_state.page = "项目管理"
                        st.rerun()
                    else:
                        st.error(msg)

    # --- 右侧提示区 ---
    with st.sidebar:
        st.divider()
        st.caption("进度")
        stages = {"layer1": "① 核心设定", "layer2": "② 细化定制", "layer3": "③ 选择标题"}
        for s, label in stages.items():
            done = list(stages.keys()).index(s) < list(stages.keys()).index(cg["stage"])
            st.markdown(f"{'✅' if done else '📝' if s == cg['stage'] else '⬜'} {label}")

# ================================================================
# 1. 项目管理
# ================================================================
elif st.session_state.page == "项目管理":
    st.header("项目管理")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("新建项目")
        name = st.text_input("项目名称")
        genre = st.text_input("小说类型（可选）")
        desc = st.text_area("简介（可选）")
        if st.button("创建", type="primary"):
            if name:
                ok, msg = pm.create(name, genre, desc)
                if ok:
                    st.success(f"项目「{name}」创建成功")
                    st.session_state.project = name
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("请输入项目名称")
    with col2:
        st.subheader("已有项目")
        projects = pm.list_projects()
        if not projects:
            st.info("暂无项目，在左侧创建")
        for p in projects:
            with st.container(border=True):
                is_active = p.get("writing_status") == "in_progress"
                cols = st.columns([3, 1, 1])
                status_tag = "📝 " if is_active else ""
                cols[0].write(f"**{status_tag}{p['name']}**")
                if p.get("genre"):
                    cols[0].write(f"类型：{p['genre']}")
                extra = f" | 续写" if is_active else ""
                cols[0].write(f"章节：{p.get('chapter_count', 0)} | 最后更新：{p.get('updated', '')[:10]}{extra}")
                label = "续写" if is_active else "打开"
                if cols[1].button(label, key=f"open_{p['name']}"):
                    st.session_state.project = p["name"]
                    st.session_state.page = "章节写作" if is_active else "项目管理"
                    pm.update_preferences_from_project(p["name"])
                    st.rerun()
                if cols[2].button("删除", key=f"del_{p['name']}"):
                    pm.delete(p["name"])
                    st.rerun()

# ================================================================
# 2. 世界观设定
# ================================================================
elif st.session_state.page == "世界观设定":
    if not st.session_state.project:
        st.warning("请先打开项目")
    else:
        st.header("世界观设定")
        content = pm.get_world(st.session_state.project)
        edited = st.text_area("编辑内容（Markdown）", content, height=500)
        if st.button("保存世界观"):
            pm.save_world(st.session_state.project, edited)
            st.success("已保存")

        st.divider()
        if st.button("一键生成世界观（本地模型）", type="primary"):
            with st.spinner("生成中..."):
                p = f"""你是一位专业世界观构建师。请为以下小说创建一个完整的世界观设定。
项目名称：{st.session_state.project}
请包含：世界基本信息、力量体系、势力分布、历史时间线、文化习俗。
用 Markdown 格式输出。"""
                try:
                    result = llm.generate(p, model="local")
                except Exception as e:
                    st.error(f"生成失败: {e}")
                    st.stop()
                edited = result
                pm.save_world(st.session_state.project, result)
                st.rerun()

# ================================================================
# 3. 角色管理
# ================================================================
elif st.session_state.page == "角色管理":
    if not st.session_state.project:
        st.warning("请先打开项目")
    else:
        st.header("角色管理系统")
        chars = pm.get_characters(st.session_state.project)
        if not isinstance(chars, list):
            chars = []

        # 角色列表
        names = [c.get("name", f"角色{i+1}") for i, c in enumerate(chars)]
        tabs = st.tabs(["角色列表", "新建角色"] + [n for n in names])

        with tabs[0]:
            if not chars:
                st.info("暂无角色")
            else:
                for c in chars:
                    with st.expander(f"{c.get('name','?')} — {c.get('age','')} {c.get('identity','')}"):
                        st.write(f"**外貌：**{c.get('appearance','')}")
                        st.write(f"**性格：**{c.get('personality','')}")
                        st.write(f"**背景：**{c.get('background','')}")
                        st.write(f"**弧光：**{c.get('arc','')}")
                        if st.button("删除此角色", key=f"del_char_{i}"):
                            chars = [x for x in chars if x.get("name") != c.get("name")]
                            pm.save_characters(st.session_state.project, chars)
                            st.rerun()

        with tabs[1]:
            with st.form("new_char"):
                name = st.text_input("姓名")
                age = st.text_input("年龄")
                identity = st.text_input("身份")
                appearance = st.text_area("外貌")
                personality = st.text_area("性格特质")
                background = st.text_area("背景故事")
                arc = st.text_area("角色弧光")
                if st.form_submit_button("添加角色"):
                    chars.append({
                        "name": name, "age": age, "identity": identity,
                        "appearance": appearance, "personality": personality,
                        "background": background, "arc": arc
                    })
                    pm.save_characters(st.session_state.project, chars)
                    st.success("已添加")
                    st.rerun()

        # 编辑已有角色
        for i, c in enumerate(chars):
            idx = i + 2  # tab index: 列表=0, 新建=1, 角色从2开始
            if idx < len(tabs):
                with tabs[idx]:
                    with st.form(f"edit_char_{i}"):
                        c["name"] = st.text_input("姓名", c.get("name",""), key=f"en_{i}")
                        c["age"] = st.text_input("年龄", c.get("age",""), key=f"ea_{i}")
                        c["identity"] = st.text_input("身份", c.get("identity",""), key=f"ei_{i}")
                        c["appearance"] = st.text_area("外貌", c.get("appearance",""), key=f"eap_{i}")
                        c["personality"] = st.text_area("性格", c.get("personality",""), key=f"ep_{i}")
                        c["background"] = st.text_area("背景", c.get("background",""), key=f"eb_{i}")
                        c["arc"] = st.text_area("弧光", c.get("arc",""), key=f"ear_{i}")
                        if st.form_submit_button("保存"):
                            pm.save_characters(st.session_state.project, chars)
                            st.success("已保存")

        st.divider()
        if st.button("批量生成角色（本地模型）", type="primary"):
            world = pm.get_world(st.session_state.project)
            with st.spinner("生成中..."):
                p = f"""根据以下世界观，生成 4-6 个核心角色（主角、反派、配角）。
世界观：{world[:2000]}
每个角色包含：name, age, identity, appearance, personality, background, arc
用 JSON 数组格式输出，只输出 JSON。"""
                try:
                    result = llm.generate(p, model="local")
                except Exception as e:
                    st.error(f"生成失败: {e}")
                    st.stop()
                # 尝试解析 JSON
                result = result.replace("```json", "").replace("```", "").strip()
                try:
                    new_chars = json.loads(result)
                    if isinstance(new_chars, list):
                        chars.extend(new_chars)
                        pm.save_characters(st.session_state.project, chars)
                        st.success("角色已添加")
                        st.rerun()
                except:
                    st.error("模型输出格式不正确，请手动添加")
                    st.code(result)

# ================================================================
# 4. 大纲设计
# ================================================================
elif st.session_state.page == "大纲设计":
    if not st.session_state.project:
        st.warning("请先打开项目")
    else:
        st.header("大纲设计器")
        content = pm.get_outline(st.session_state.project)
        edited = st.text_area("大纲内容（Markdown）", content, height=400)
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("保存大纲"):
                pm.save_outline(st.session_state.project, edited)
                st.success("已保存")
        with col2:
            chapters = st.number_input("章节数", min_value=1, max_value=100, value=12, label_visibility="collapsed")

        st.divider()
        if st.button("一键生成大纲（DeepSeek）", type="primary"):
            with st.spinner("生成中..."):
                world = pm.get_world(st.session_state.project)
                chars = pm.get_characters(st.session_state.project)
                char_text = json.dumps(chars, ensure_ascii=False)[:1000]
                p = f"""你是专业小说结构师。为以下作品创作{chapters}章大纲。
类型：{pm._load_meta(st.session_state.project).get('genre','')}
世界观：{world[:1500]}
角色：{char_text}
格式：每章一行「第N章 | 标题 | 情节概要 | 钩子」"""
                try:
                    result = llm.generate(p, model="deepseek")
                except Exception as e:
                    st.error(f"生成失败: {e}")
                    st.stop()
                pm.save_outline(st.session_state.project, result)
                st.rerun()

# ================================================================
# 5. 章节写作（核心模块）
# ================================================================
elif st.session_state.page == "章节写作":
    if not st.session_state.project:
        st.warning("请先打开项目")
    else:
        st.header("章节写作")
        col_left, col_right = st.columns([2, 3])

        with col_left:
            outline = pm.get_outline(st.session_state.project)
            chars = pm.get_characters(st.session_state.project)

            # 已保存章节列表（用于显示和选择）
            ch_dir = os.path.join(PROJECTS_DIR, st.session_state.project, "chapters")
            saved_chapters = sorted(os.listdir(ch_dir)) if os.path.exists(ch_dir) else []

            chapter_num = st.number_input("章节号", min_value=1, value=1)
            target_words = st.select_slider("目标字数", options=[2000, 2500, 3000, 3500, 4000], value=3000)
            model_choice = st.selectbox("模型", ["local", "deepseek", "claude"], index=0,
                format_func=lambda x: {"local": "本地 Gemma 4 26B", "deepseek": "DeepSeek-v4-flash", "claude": "Claude"}[x])

            # 悬念钩子设置
            hook_options = ["自动匹配", "危机陡现", "惊天秘密", "身份反转", "关键抉择",
                            "故人归来", "前方未知", "倒计时", "伏笔回收", "突如其来的背叛",
                            "真相碎片", "话说到一半", "时空跳跃", "能力觉醒/异变"]
            hook_type = st.selectbox("结尾钩子类型", hook_options, index=0,
                help="悬念钩子十三式——每章结尾留钩子吸引追更。选「自动匹配」由 AI 按章节位置选")

            # 写作模式
            with st.expander("⚡ 写作模式", expanded=False):
                write_mode = st.radio("模式", ["串行（逐章）", "并行（批量）"], horizontal=True, label_visibility="collapsed")
                if write_mode == "并行（批量）":
                    col_a, col_b = st.columns(2)
                    batch_start = col_a.number_input("起始章", min_value=1, value=chapter_num)
                    batch_end = col_b.number_input("结束章", min_value=batch_start, value=min(batch_start + 9, 100))
                    batch_workers = st.number_input("并行数", min_value=1, max_value=8, value=3, help="同时生成的并发数")
                    if st.button("批量并行生成", type="primary", use_container_width=True):
                        ch_range = list(range(batch_start, batch_end + 1))
                        existing = [int(f.replace(".md", "")) for f in saved_chapters]
                        todo = [c for c in ch_range if c not in existing]
                        if not todo:
                            st.warning("所选章节已全部生成")
                        else:
                            bar = st.progress(0, text=f"共 {len(todo)} 章")
                            done = 0
                            _lock = threading.Lock()
                            existing_nums = {int(f.replace('.md','')) for f in saved_chapters}
                            def gen_chapter(cn):
                                is_first = cn == 1 or not any(n < cn for n in existing_nums)
                                bh = "动作开场" if is_first else "悬念回钩"
                                prompt = f"""根据以下内容撰写第{cn}章正文。
大纲：{outline[:2000]}
角色设定：{json.dumps(chars, ensure_ascii=False)[:1500]}
【悬念钩子要求】
章首引子：{bh}
结尾钩子：使用悬念钩子，让读者想追下一章
黄金法则：展示非讲述、冲突驱动、开头即高潮、30%对话
要求：描写生动，篇幅约{target_words}字。只输出正文。"""
                                try:
                                    r = llm.generate(prompt, model=model_choice, temperature=0.85, max_tokens=6000)
                                    with _lock:
                                        pm.save_chapter(st.session_state.project, str(cn), r)
                                    return cn, len(r.replace("\n","").replace(" ","")), True
                                except:
                                    return cn, 0, False
                            with concurrent.futures.ThreadPoolExecutor(max_workers=batch_workers) as ex:
                                fs = {ex.submit(gen_chapter, c): c for c in todo}
                                for f in concurrent.futures.as_completed(fs):
                                    cn, wc, ok = f.result()
                                    done += 1
                                    bar.progress(done / len(todo), text=f"第{cn}章 {'✅' if ok else '❌'}（{wc}字）{done}/{len(todo)}")
                            st.success(f"批量完成：{done}/{len(todo)} 章")
                            st.rerun()

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                gen_btn = st.button("生成本章", type="primary", use_container_width=True)
            with col_btn2:
                next_btn = st.button("生成下一章", use_container_width=True,
                    disabled=str(chapter_num) in [f.replace(".md","") for f in saved_chapters])

            if gen_btn or next_btn:
                if next_btn:
                    chapter_num = max([int(f.replace(".md","")) for f in saved_chapters] + [0]) + 1

                # 收集前文摘要
                prev_summary = ""
                prev_chapters = [f for f in saved_chapters if int(f.replace(".md","")) < chapter_num]
                if prev_chapters:
                    summary_parts = []
                    for f in prev_chapters:
                        num = f.replace(".md", "")
                        text = pm.get_chapter(st.session_state.project, num)
                        # 取末尾500字（章节结尾才是承接关键）
                        summary_parts.append(f"【第{num}章结尾】{text[-500:]}")
                    prev_summary = "\n".join(summary_parts)

                is_first_chapter = chapter_num == 1 or not prev_chapters
                begin_hint = "动作开场" if is_first_chapter else "悬念回钩——从上一章结尾的钩子直接展开"

                p = f"""根据以下内容撰写第{chapter_num}章正文。
大纲：{outline[:2000]}
角色设定：{json.dumps(chars, ensure_ascii=False)[:1500]}
"""
                if prev_summary:
                    p += f"""前文回顾：
{prev_summary}

写作要求：
1. 开头必须承接上一章结尾的情节或氛围，先用一段话衔接过渡，再展开新内容。
2. 如果有时间跳跃（如"数日后"）或场景切换，必须添加过渡段落，交代时间流逝或空间转换的缘由。
3. 转折处要有铺垫，不能生硬跳转。每段结尾为下段留钩子。
4. 保持情节连贯、人物动机一致。新章节要有新进展。
"""
                hook_guide = {"自动匹配": "按章节位置自动选择合适的钩子类型",
                    "危机陡现": "章末突发致命危险", "惊天秘密": "揭示颠覆认知的信息",
                    "身份反转": "某人真实身份揭晓", "关键抉择": "主角面临两难选择",
                    "故人归来": "意想不到的角色重新出现", "前方未知": "即将进入全新场景/险境",
                    "倒计时": "时间紧迫制造紧张感", "伏笔回收": "前文线索突然爆发",
                    "突如其来的背叛": "最信任的人反水", "真相碎片": "展示部分真相引发更多疑问",
                    "话说到一半": "关键信息被意外打断", "时空跳跃": "倒叙/闪回揭示关键信息",
                    "能力觉醒/异变": "出现无法控制的变化"}

                p += f"""
【悬念钩子要求】
章首引子（50-150字）：{begin_hint}
结尾钩子：必须使用「{hook_type if hook_type != '自动匹配' else '自动匹配'}」类型
  - {hook_guide.get(hook_type, '按章节位置自动匹配，确保读者想追下一章')}
黄金法则：
1. 展示而非讲述——用动作和对话表现，不直接陈述
2. 冲突驱动剧情——本章必须有冲突或转折
3. 开头即高潮——前 20% 必须吸引人
4. 至少 30% 对话，对话须有潜台词或推进情节
5. 至少 1 个意外转折

要求：描写生动，对话自然，篇幅约{target_words}字。只输出正文，不要任何解释说明。"""
                with st.status("生成中..."):
                    try:
                        result = llm.generate(p, model=model_choice, temperature=0.85, max_tokens=6000)
                    except Exception as e:
                        st.error(f"模型调用失败: {e}")
                        st.stop()

                    status.update(label="调整字数中...")
                    current = len(result.replace("\n","").replace(" ",""))
                    for _ in range(3):
                        if 2000 <= current <= 4000:
                            break
                        if current < 2000:
                            act = f"扩写下面的正文到约{target_words}字，丰富细节。只输出扩写后的正文，禁止任何解释。\n\n{result}"
                        else:
                            act = f"精简下面的正文到约{target_words}字，保留核心情节。只输出精简后的正文，禁止任何解释。\n\n{result}"
                        try:
                            result = llm.generate(act, model=model_choice, max_tokens=6000)
                        except Exception as e:
                            st.warning(f"字数调整失败: {e}")
                            break
                        current = len(result.replace("\n","").replace(" ",""))
                    st.session_state[f"chapter_{chapter_num}"] = result
                    pm.save_chapter(st.session_state.project, str(chapter_num), result)
                    status.update(label=f"完成，{current}字，校验钩子中…", state="running")

                    # 悬念钩子校验
                    try:
                        hook_check = llm.generate(
                            f"""检查以下章节结尾（最后200字）是否有悬念钩子（悬念、转折、留白、未解之谜等让读者想追下一章的元素）。
章节结尾：\n{result[-200:]}
只回答 YES 或 NO，不要其他内容。""", model=model_choice, max_tokens=10)
                        has_hook = "YES" in hook_check.strip().upper()
                    except:
                        has_hook = True  # 校验失败时默认通过

                    if has_hook:
                        status.update(label=f"✅ 完成，{current}字，钩子已检测", state="complete")
                    else:
                        status.update(label=f"⚠️ 完成，{current}字，但未检测到明显钩子", state="complete")
                        st.info("建议：在结尾添加悬念钩子吸引读者追更。可参考 prompts/hook-techniques.md")

            # 已保存章节列表
            st.divider()
            st.write("已保存章节")
            if saved_chapters:
                for fn in saved_chapters:
                    if fn.endswith(".md"):
                        num = fn.replace(".md", "")
                        if st.button(f"第{num}章", key=f"load_ch{num}"):
                            content = pm.get_chapter(st.session_state.project, num)
                            st.session_state[f"chapter_{num}"] = content
            else:
                st.caption("暂无")

            # 全文校验
            st.divider()
            if st.button("🔍 全文校验", use_container_width=True, type="secondary"):
                with st.spinner("校验中..."):
                    failed, msg = pm.validate_all_chapters(st.session_state.project, llm, model_choice)
                if not failed:
                    st.success(f"✅ {msg}")
                else:
                    st.warning(f"⚠️ {msg}")
                    for f in failed:
                        st.write(f"**第{f['num']}章**：{f['reason']}")
                        if st.button(f"重写第{f['num']}章", key=f"rewrite_{f['num']}"):
                            with st.spinner(f"重写第{f['num']}章..."):
                                rewrite_ok = False
                                for attempt in range(3):
                                    try:
                                        instr = "扩写" if attempt > 0 and "字数不足" in f.get('reason','') else "重写"
                                        p = f"""{instr}第{f['num']}章，修正：{f['reason']}
大纲：{outline[:1500]}
要求：篇幅约{target_words}字，描写生动，对话自然。只输出正文。"""
                                        r = llm.generate(p, model=model_choice, temperature=0.85, max_tokens=6000)
                                        wc = len(r.replace("\n","").replace(" ",""))
                                        if wc >= 1500:
                                            pm.save_chapter(st.session_state.project, f['num'], r)
                                            rewrite_ok = True
                                            st.success(f"第{f['num']}章已重写（{wc}字）")
                                            st.rerun()
                                            break
                                    except:
                                        pass
                                if not rewrite_ok:
                                    st.error(f"重写第{f['num']}章失败（3次尝试后）")

        with col_right:
            # 切换章节号时自动加载已保存内容
            saved = pm.get_chapter(st.session_state.project, str(chapter_num))
            key = f"chapter_{chapter_num}"
            if saved and key not in st.session_state:
                st.session_state[key] = saved
            default = st.session_state.get(key, saved if saved else "")
            edited = st.text_area("正文编辑", default, height=600, key=f"editor_{chapter_num}")

            save_btn = st.button("保存修改", use_container_width=True)
            if save_btn and edited.strip():
                pm.save_chapter(st.session_state.project, str(chapter_num), edited)
                st.session_state[key] = edited
                st.success(f"第{chapter_num}章已保存（{len(edited.replace(chr(10),''))}字）")

# ================================================================
# 6. 知识图谱
# ================================================================
elif st.session_state.page == "知识图谱":
    if not st.session_state.project:
        st.warning("请先打开项目")
    else:
        st.header("知识图谱")
        # 读取角色关系生成 Mermaid
        chars = pm.get_characters(st.session_state.project)
        if not chars:
            st.info("暂无角色数据")
        else:
            mermaid_lines = ["graph LR"]
            for c in chars:
                name = c.get("name", "?")
                mermaid_lines.append(f'    {name}["{name}"]')
            # 简单关系：如果角色有 relations 字段
            for c in chars:
                name = c.get("name", "")
                rel = c.get("relations", "")
                if rel and name:
                    for r in rel.split("，"):
                        r = r.strip()
                        if r and name in r:
                            # 提取关系目标："A是B的朋友" => 目标 B
                            for other in chars:
                                oname = other.get("name", "")
                                if oname and oname != name and oname in r:
                                    rel_label = r.replace(name, "").replace(oname, "").strip("的是")
                                    mermaid_lines.append(f'    {name} -- {rel_label} --> {oname}')
                                    break
            st.markdown("```mermaid\n" + "\n".join(mermaid_lines) + "\n```")

        if st.button("AI 生成关系描述"):
            world = pm.get_world(st.session_state.project)
            with st.spinner("生成中..."):
                p = f"""根据以下角色设定和世界观，描述角色间的核心关系。
角色：{json.dumps(chars, ensure_ascii=False)[:2000]}
世界观：{world[:1000]}
用 Mermaid graph LR 格式输出。只输出 Mermaid 代码。"""
                try:
                    result = llm.generate(p, model="deepseek")
                except Exception as e:
                    st.error(f"生成失败: {e}")
                    st.stop()
                st.code(result, language="mermaid")

# ================================================================
# 7. 模型设置
# ================================================================
elif st.session_state.page == "模型设置":
    st.header("模型设置")
    st.info("当前使用本地 Gemma 4 26B（自动检测）")
    st.write("如需使用 DeepSeek 或 Claude，请在环境变量中设置：")
    st.code("DEEPSEEK_API_KEY=sk-xxx\nANTHROPIC_API_KEY=sk-xxx")

    st.divider()
    st.subheader("创作偏好")
    prefs = st.session_state.prefs
    p = prefs["preferences"]
    with st.form("prefs_form"):
        fav = st.text_input("擅长的题材（逗号分隔）", value=", ".join(p.get("favoriteGenres", [])))
        tone = st.text_input("偏好的文风", value=p.get("preferredTone", ""))
        ch_cnt = st.number_input("默认章节数", min_value=5, max_value=200, value=p.get("typicalChapterCount", 30))
        refs = st.text_input("参考作者/作品（逗号分隔）", value=", ".join(p.get("styleReferences", [])))
        dislikes = st.text_input("不喜欢的元素（逗号分隔）", value=", ".join(p.get("dislikes", [])))
        if st.form_submit_button("保存偏好"):
            p["favoriteGenres"] = [x.strip() for x in fav.split(",") if x.strip()]
            p["preferredTone"] = tone
            p["typicalChapterCount"] = ch_cnt
            p["styleReferences"] = [x.strip() for x in refs.split(",") if x.strip()]
            p["dislikes"] = [x.strip() for x in dislikes.split(",") if x.strip()]
            pm.save_preferences(prefs)
            st.success("偏好已保存")

    with st.expander("创作历史"):
        if p.get("creationHistory"):
            for h in p["creationHistory"]:
                st.caption(h)
        else:
            st.caption("暂无")

    st.divider()
    st.write("本地状态")
    import subprocess
    try:
        r = subprocess.run(["lms", "ps"], capture_output=True, text=True, timeout=5)
        st.code(r.stdout or r.stderr or "无输出")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        st.code(f"无法获取本地模型状态: {e}")

st.divider()
st.caption("NovelForge v0.1 | 本地 Gemma 4 26B · DeepSeek-v4-flash · Claude")
