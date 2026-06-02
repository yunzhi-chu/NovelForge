"""NovelForge - 小说写作助手 (Streamlit)"""
import streamlit as st
import json, os
from llm_client import LLMClient
from project_manager import ProjectManager

st.set_page_config(page_title="NovelForge - 小说写作助手", layout="wide")
st.title("NovelForge - 小说写作助手")

# 初始化
if "llm" not in st.session_state:
    st.session_state.llm = LLMClient()
if "pm" not in st.session_state:
    st.session_state.pm = ProjectManager()
if "project" not in st.session_state:
    st.session_state.project = None
if "page" not in st.session_state:
    st.session_state.page = "项目管理"

# 侧边栏
with st.sidebar:
    st.header("导航")
    pages = ["项目管理", "世界观设定", "角色管理", "大纲设计", "章节写作", "知识图谱", "模型设置"]
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

pm = st.session_state.pm
llm = st.session_state.llm

# ================================================================
# 1. 项目管理
# ================================================================
if st.session_state.page == "项目管理":
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
                cols = st.columns([3, 1, 1])
                cols[0].write(f"**{p['name']}**")
                if p.get("genre"):
                    cols[0].write(f"类型：{p['genre']}")
                cols[0].write(f"章节：{p.get('chapter_count', 0)} | 最后更新：{p.get('updated', '')[:10]}")
                if cols[1].button("打开", key=f"open_{p['name']}"):
                    st.session_state.project = p["name"]
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
                        if st.button("删除此角色", key=f"del_char_{c.get('name')}"):
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
            ch_dir = os.path.join("projects", st.session_state.project, "chapters")
            saved_chapters = sorted(os.listdir(ch_dir)) if os.path.exists(ch_dir) else []

            chapter_num = st.number_input("章节号", min_value=1, value=1)
            target_words = st.select_slider("目标字数", options=[2000, 2500, 3000, 3500, 4000], value=3000)
            model_choice = st.selectbox("模型", ["local", "deepseek", "claude"], index=0,
                format_func=lambda x: {"local": "本地 Gemma 4 26B", "deepseek": "DeepSeek-v4-flash", "claude": "Claude"}[x])

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
                p += f"""要求：描写生动，对话自然，篇幅约{target_words}字。只输出正文，不要任何解释说明。"""
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
                    status.update(label=f"完成，{current}字", state="complete")

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
                    # 解析简单关系: "A是B的朋友" -> A--朋友-->B
                    for r in rel.split("，"):
                        r = r.strip()
                        if r and name in r:
                            mermaid_lines.append(f'    {name} -- {r} --> {name}')
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
    st.write("本地状态")
    import subprocess
    r = subprocess.run(["lms", "ps"], capture_output=True, text=True)
    st.code(r.stdout or r.stderr)

st.divider()
st.caption("NovelForge v0.1 | 本地 Gemma 4 26B · DeepSeek-v4-flash · Claude")
